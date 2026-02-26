"""
engine.py - 말표(Mal-Pyo) 핵심 엔진 모듈

시각장애인을 위한 음성 기반 프레젠테이션 도우미의 핵심 모델 계층.
STT, TTS, LLM을 로컬 GPU 기반으로 구동하여 개인정보 보호 및 저지연을 실현한다.
"""

from __future__ import annotations

import io
import os
import wave
import tempfile
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generator

import numpy as np

# ---------------------------------------------------------------------------
# 로깅 설정
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("malpyo.engine")


# ═══════════════════════════════════════════════════════════════════════════
# 1. STT (Speech-To-Text) — faster-whisper Large-v3-turbo, GPU 가속
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class STTResult:
    """음성 인식 결과를 담는 데이터 클래스."""
    text: str
    language: str = "ko"
    confidence: float = 0.0
    segments: list = field(default_factory=list)


class STTEngine:
    """faster-whisper 기반 로컬 STT 엔진.

    RTX 5080 GPU에서 float16 추론으로 실시간 음성 인식을 수행한다.
    """

    def __init__(
        self,
        model_size: str = "large-v3-turbo",
        device: str = "cuda",
        compute_type: str = "float16",
    ) -> None:
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None

    def _load_model(self):
        """모델을 지연 로딩(lazy load)하여 메모리 효율을 높인다."""
        if self._model is not None:
            return
        try:
            from faster_whisper import WhisperModel

            logger.info(
                "STT 모델 로딩 중: %s (device=%s, compute=%s)",
                self.model_size, self.device, self.compute_type,
            )
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
            logger.info("STT 모델 로딩 완료")
        except Exception as e:
            logger.error("STT 모델 로딩 실패: %s", e)
            raise RuntimeError(
                f"faster-whisper 모델 로딩에 실패했습니다. "
                f"CUDA 및 cuDNN이 올바르게 설치되었는지 확인하세요.\n{e}"
            ) from e

    def transcribe(self, audio_data: np.ndarray | bytes | str, sample_rate: int = 16000) -> STTResult:
        """오디오 데이터를 텍스트로 변환한다.

        Args:
            audio_data: numpy 배열, WAV 바이트, 또는 파일 경로
            sample_rate: 샘플링 레이트 (기본 16kHz)

        Returns:
            STTResult: 인식 결과
        """
        self._load_model()

        audio_input = self._prepare_audio(audio_data, sample_rate)

        segments_gen, info = self._model.transcribe(
            audio_input,
            language="ko",
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=500,
                speech_pad_ms=300,
            ),
        )

        segments = list(segments_gen)
        full_text = " ".join(seg.text.strip() for seg in segments)

        avg_confidence = 0.0
        if segments:
            avg_confidence = sum(
                seg.avg_log_prob for seg in segments
            ) / len(segments)

        return STTResult(
            text=full_text,
            language=info.language,
            confidence=avg_confidence,
            segments=[
                {"start": s.start, "end": s.end, "text": s.text.strip()}
                for s in segments
            ],
        )

    def transcribe_stream(
        self, audio_chunks: Generator[np.ndarray, None, None]
    ) -> Generator[str, None, None]:
        """스트리밍 방식으로 오디오를 실시간 인식한다."""
        self._load_model()
        buffer = np.array([], dtype=np.float32)
        # 약 2초 분량씩 버퍼링 후 인식
        chunk_threshold = 32000

        for chunk in audio_chunks:
            if chunk.dtype != np.float32:
                chunk = chunk.astype(np.float32) / 32768.0
            buffer = np.concatenate([buffer, chunk])

            if len(buffer) >= chunk_threshold:
                result = self.transcribe(buffer)
                if result.text.strip():
                    yield result.text.strip()
                buffer = np.array([], dtype=np.float32)

        # 잔여 버퍼 처리
        if len(buffer) > 0:
            result = self.transcribe(buffer)
            if result.text.strip():
                yield result.text.strip()

    @staticmethod
    def _prepare_audio(audio_data, sample_rate: int):
        """다양한 오디오 입력 형식을 faster-whisper가 인식할 수 있는 형태로 변환."""
        if isinstance(audio_data, str):
            return audio_data
        if isinstance(audio_data, (bytes, bytearray)):
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmp.write(audio_data)
            tmp.close()
            return tmp.name
        if isinstance(audio_data, np.ndarray):
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32) / 32768.0
            return audio_data
        raise ValueError(f"지원하지 않는 오디오 형식입니다: {type(audio_data)}")


# ═══════════════════════════════════════════════════════════════════════════
# 2. TTS (Text-To-Speech) — 로컬 전용, GPU 가속
# ═══════════════════════════════════════════════════════════════════════════

class BaseTTSEngine(ABC):
    """TTS 엔진의 공통 인터페이스.

    향후 다른 로컬 TTS 엔진(MeloTTS, Coqui 등)으로 교체 가능하도록 추상화.
    """

    @abstractmethod
    def synthesize(self, text: str) -> bytes:
        """텍스트를 WAV 바이트로 변환한다."""
        ...

    @abstractmethod
    def get_engine_name(self) -> str:
        """현재 엔진 이름을 반환한다."""
        ...


class MeloTTSEngine(BaseTTSEngine):
    """MeloTTS 기반 로컬 GPU TTS 엔진.

    한국어 음성 합성을 GPU에서 수행하여 저지연 응답을 제공한다.
    """

    def __init__(self, device: str = "cuda", speed: float = 1.0) -> None:
        self.device = device
        self.speed = speed
        self._model = None
        self._speaker_ids = None

    def _load_model(self):
        if self._model is not None:
            return
        try:
            from melo.api import TTS as MeloTTS

            logger.info("MeloTTS 모델 로딩 중 (device=%s)", self.device)
            self._model = MeloTTS(language="KR", device=self.device)
            self._speaker_ids = self._model.hps.data.spk2id
            logger.info("MeloTTS 모델 로딩 완료")
        except Exception as e:
            logger.error("MeloTTS 로딩 실패: %s", e)
            raise RuntimeError(
                f"MeloTTS 로딩에 실패했습니다. 설치 상태를 확인하세요.\n{e}"
            ) from e

    def synthesize(self, text: str) -> bytes:
        """텍스트를 WAV 바이트로 변환한다."""
        self._load_model()

        tmp_path = tempfile.mktemp(suffix=".wav")
        speaker_id = list(self._speaker_ids.values())[0]

        self._model.tts_to_file(
            text,
            speaker_id,
            tmp_path,
            speed=self.speed,
        )

        with open(tmp_path, "rb") as f:
            wav_bytes = f.read()

        os.unlink(tmp_path)
        return wav_bytes

    def get_engine_name(self) -> str:
        return "MeloTTS (Local GPU)"


class Pyttsx3TTSEngine(BaseTTSEngine):
    """pyttsx3 기반 오프라인 TTS 폴백 엔진.

    GPU가 없거나 MeloTTS 설치에 실패한 경우 사용하는 완전 오프라인 폴백.
    Windows SAPI5 / Linux espeak 백엔드를 활용한다.
    """

    def __init__(self, rate: int = 150, volume: float = 1.0) -> None:
        self.rate = rate
        self.volume = volume
        self._engine = None

    def _load_engine(self):
        if self._engine is not None:
            return
        try:
            import pyttsx3

            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", self.rate)
            self._engine.setProperty("volume", self.volume)

            # 한국어 음성이 있으면 선택
            voices = self._engine.getProperty("voices")
            for voice in voices:
                if "korean" in voice.name.lower() or "ko" in voice.id.lower():
                    self._engine.setProperty("voice", voice.id)
                    break

            logger.info("pyttsx3 TTS 엔진 초기화 완료")
        except Exception as e:
            logger.error("pyttsx3 초기화 실패: %s", e)
            raise

    def synthesize(self, text: str) -> bytes:
        """텍스트를 WAV 바이트로 변환한다."""
        self._load_engine()

        tmp_path = tempfile.mktemp(suffix=".wav")
        self._engine.save_to_file(text, tmp_path)
        self._engine.runAndWait()

        with open(tmp_path, "rb") as f:
            wav_bytes = f.read()

        os.unlink(tmp_path)
        return wav_bytes

    def get_engine_name(self) -> str:
        return "pyttsx3 (Offline Fallback)"


def create_tts_engine(preferred: str = "melo", device: str = "cuda") -> BaseTTSEngine:
    """사용 가능한 최적의 TTS 엔진을 생성하는 팩토리 함수.

    MeloTTS → pyttsx3 순서로 폴백하여 항상 음성 출력이 가능하도록 보장한다.
    """
    if preferred == "melo":
        try:
            engine = MeloTTSEngine(device=device)
            engine._load_model()
            return engine
        except Exception:
            logger.warning("MeloTTS 사용 불가, pyttsx3로 폴백합니다.")

    try:
        engine = Pyttsx3TTSEngine()
        engine._load_engine()
        return engine
    except Exception:
        logger.warning("pyttsx3도 사용 불가합니다.")

    raise RuntimeError(
        "사용 가능한 TTS 엔진이 없습니다. "
        "MeloTTS 또는 pyttsx3를 설치해주세요."
    )


# ═══════════════════════════════════════════════════════════════════════════
# 3. LLM (Large Language Model) — 모듈화 설계
# ═══════════════════════════════════════════════════════════════════════════

class BaseLLMEngine(ABC):
    """LLM 엔진의 공통 인터페이스.

    GPT-4o → 로컬 LLM(Llama-3 등) 교체가 가능하도록 추상화.
    """

    @abstractmethod
    def chat(self, user_message: str, system_prompt: str = "", history: list | None = None) -> str:
        """사용자 메시지에 대한 응답을 생성한다."""
        ...

    @abstractmethod
    def get_engine_name(self) -> str:
        ...


# 시각장애인 프레젠테이션 도우미를 위한 시스템 프롬프트
DEFAULT_SYSTEM_PROMPT = """당신은 '말표(Mal-Pyo)'라는 이름의 시각장애인용 프레젠테이션 도우미입니다.
사용자는 음성으로 질문하며, 당신은 친절하고 명확하게 음성으로 답변합니다.

핵심 규칙:
1. 모든 답변은 음성으로 읽히므로, 짧고 명료하게 작성하세요.
2. 시각적 요소(차트, 이미지 등)는 말로 설명하세요.
3. 프레젠테이션 슬라이드 내용을 요약하거나 설명할 수 있습니다.
4. 발표 연습, 대본 작성, Q&A 대비를 도울 수 있습니다.
5. 사용자가 명령하면 슬라이드 넘김, 타이머 등 보조 기능을 수행합니다.
6. 항상 존댓말을 사용하고, 따뜻하고 격려하는 톤을 유지하세요.
"""


class GPT4oEngine(BaseLLMEngine):
    """OpenAI GPT-4o 기반 LLM 엔진.

    의도 파악 정확도를 위해 현재 GPT-4o를 사용하며,
    추후 로컬 LLM으로 교체할 수 있도록 BaseLLMEngine을 상속한다.
    """

    def __init__(self, api_key: str | None = None, model: str = "gpt-4o") -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY가 설정되지 않았습니다. "
                ".env 파일 또는 환경변수를 확인하세요."
            )
        from openai import OpenAI

        self._client = OpenAI(api_key=self.api_key)
        return self._client

    def chat(
        self,
        user_message: str,
        system_prompt: str = "",
        history: list | None = None,
    ) -> str:
        client = self._get_client()
        system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1024,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error("GPT-4o 호출 실패: %s", e)
            return f"죄송합니다, 응답 생성 중 오류가 발생했습니다: {e}"

    def get_engine_name(self) -> str:
        return f"OpenAI {self.model}"


class LocalLLMEngine(BaseLLMEngine):
    """로컬 LLM 엔진 (Llama-3, Mistral 등).

    llama-cpp-python 또는 Ollama API를 통해 로컬에서 LLM을 구동한다.
    GPU 오프로딩으로 RTX 5080의 VRAM을 최대한 활용한다.
    """

    def __init__(
        self,
        model_path: str = "",
        backend: str = "ollama",
        ollama_model: str = "llama3:8b",
        ollama_url: str = "http://localhost:11434",
        n_gpu_layers: int = -1,
    ) -> None:
        self.model_path = model_path
        self.backend = backend
        self.ollama_model = ollama_model
        self.ollama_url = ollama_url
        self.n_gpu_layers = n_gpu_layers
        self._llm = None

    def _load_model(self):
        if self._llm is not None:
            return

        if self.backend == "ollama":
            # Ollama는 별도 서버이므로 연결만 확인
            import requests

            try:
                resp = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
                resp.raise_for_status()
                logger.info("Ollama 서버 연결 성공")
            except Exception as e:
                raise RuntimeError(
                    f"Ollama 서버({self.ollama_url})에 연결할 수 없습니다.\n{e}"
                ) from e
        elif self.backend == "llama_cpp":
            from llama_cpp import Llama

            logger.info("llama-cpp 모델 로딩: %s", self.model_path)
            self._llm = Llama(
                model_path=self.model_path,
                n_gpu_layers=self.n_gpu_layers,
                n_ctx=4096,
                verbose=False,
            )
            logger.info("llama-cpp 모델 로딩 완료")

    def chat(
        self,
        user_message: str,
        system_prompt: str = "",
        history: list | None = None,
    ) -> str:
        self._load_model()
        system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT

        if self.backend == "ollama":
            return self._chat_ollama(user_message, system_prompt, history)
        return self._chat_llama_cpp(user_message, system_prompt, history)

    def _chat_ollama(self, user_message: str, system_prompt: str, history: list | None) -> str:
        import requests

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        try:
            resp = requests.post(
                f"{self.ollama_url}/api/chat",
                json={"model": self.ollama_model, "messages": messages, "stream": False},
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()["message"]["content"].strip()
        except Exception as e:
            logger.error("Ollama 호출 실패: %s", e)
            return f"죄송합니다, 로컬 LLM 응답 생성 중 오류가 발생했습니다: {e}"

    def _chat_llama_cpp(self, user_message: str, system_prompt: str, history: list | None) -> str:
        prompt = f"<|system|>\n{system_prompt}\n"
        if history:
            for msg in history:
                prompt += f"<|{msg['role']}|>\n{msg['content']}\n"
        prompt += f"<|user|>\n{user_message}\n<|assistant|>\n"

        try:
            output = self._llm(prompt, max_tokens=1024, temperature=0.7, stop=["<|user|>", "<|system|>"])
            return output["choices"][0]["text"].strip()
        except Exception as e:
            logger.error("llama-cpp 추론 실패: %s", e)
            return f"죄송합니다, 로컬 LLM 응답 생성 중 오류가 발생했습니다: {e}"

    def get_engine_name(self) -> str:
        if self.backend == "ollama":
            return f"Ollama ({self.ollama_model})"
        return f"llama-cpp ({Path(self.model_path).stem})"


def create_llm_engine(
    backend: str = "gpt4o",
    **kwargs,
) -> BaseLLMEngine:
    """LLM 엔진 팩토리 함수.

    backend 값에 따라 적절한 엔진을 생성한다:
    - "gpt4o": OpenAI GPT-4o (기본값, 인터넷 필요)
    - "ollama": Ollama 로컬 서버
    - "llama_cpp": llama-cpp-python 직접 추론
    """
    if backend == "gpt4o":
        return GPT4oEngine(**kwargs)
    if backend in ("ollama", "llama_cpp"):
        return LocalLLMEngine(backend=backend, **kwargs)
    raise ValueError(f"지원하지 않는 LLM 백엔드입니다: {backend}")


# ═══════════════════════════════════════════════════════════════════════════
# 4. 통합 파이프라인 — 음성 대화 전체 흐름을 하나로 묶는다
# ═══════════════════════════════════════════════════════════════════════════

class MalPyoEngine:
    """말표 통합 엔진.

    STT → LLM → TTS 파이프라인을 하나의 인터페이스로 제공하여
    app.py에서 간단하게 호출할 수 있도록 한다.
    """

    def __init__(
        self,
        stt: STTEngine | None = None,
        tts: BaseTTSEngine | None = None,
        llm: BaseLLMEngine | None = None,
    ) -> None:
        self.stt = stt or STTEngine()
        self.tts = tts
        self.llm = llm
        self.conversation_history: list[dict] = []

    def initialize(
        self,
        tts_preferred: str = "melo",
        llm_backend: str = "gpt4o",
        device: str = "cuda",
        **llm_kwargs,
    ) -> dict[str, str]:
        """모든 엔진을 초기화하고 상태를 반환한다."""
        status = {}

        try:
            self.stt._load_model()
            status["stt"] = f"✓ {self.stt.model_size}"
        except Exception as e:
            status["stt"] = f"✗ 실패: {e}"

        try:
            self.tts = create_tts_engine(preferred=tts_preferred, device=device)
            status["tts"] = f"✓ {self.tts.get_engine_name()}"
        except Exception as e:
            status["tts"] = f"✗ 실패: {e}"

        try:
            self.llm = create_llm_engine(backend=llm_backend, **llm_kwargs)
            status["llm"] = f"✓ {self.llm.get_engine_name()}"
        except Exception as e:
            status["llm"] = f"✗ 실패: {e}"

        return status

    def process_voice(self, audio_data: np.ndarray | bytes | str) -> tuple[str, str, bytes | None]:
        """음성 입력을 받아 (인식 텍스트, 응답 텍스트, 응답 음성 WAV) 튜플을 반환한다.

        이 메서드 하나로 STT → LLM → TTS 전체 파이프라인이 실행된다.
        """
        # Step 1: 음성 → 텍스트
        stt_result = self.stt.transcribe(audio_data)
        recognized_text = stt_result.text

        if not recognized_text.strip():
            return "", "음성이 인식되지 않았습니다. 다시 말씀해 주세요.", None

        # Step 2: 텍스트 → LLM 응답
        response_text = ""
        if self.llm:
            response_text = self.llm.chat(
                recognized_text,
                history=self.conversation_history,
            )
            # 대화 이력 업데이트
            self.conversation_history.append({"role": "user", "content": recognized_text})
            self.conversation_history.append({"role": "assistant", "content": response_text})
            # 이력 길이 제한 (최근 20턴)
            if len(self.conversation_history) > 40:
                self.conversation_history = self.conversation_history[-40:]
        else:
            response_text = recognized_text

        # Step 3: 응답 텍스트 → 음성
        wav_bytes = None
        if self.tts and response_text:
            try:
                wav_bytes = self.tts.synthesize(response_text)
            except Exception as e:
                logger.error("TTS 합성 실패: %s", e)

        return recognized_text, response_text, wav_bytes

    def reset_history(self) -> None:
        """대화 이력을 초기화한다."""
        self.conversation_history.clear()
        logger.info("대화 이력이 초기화되었습니다.")
