"""
engine.py - 말표(Mal-Pyo) 파이프라인 오케스트레이터

app.py에서 녹음된 음성 파일을 받아 아래 순서로 처리한다:
  1) stt_engine  : 음성 → 텍스트
  2) llm_engine  : 텍스트 → 구조화 JSON + 응답 문장
  3) tts_engine  : 응답 문장 → 음성(WAV bytes)

app.py는 이 모듈의 MalPyoEngine.process() 하나만 호출하면 된다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from stt_engine import STTEngine
from llm_engine import LLMEngine, LLMResult
from tts_engine import TTSEngine

logger = logging.getLogger("malpyo.engine")


@dataclass
class PipelineResult:
    """파이프라인 전체 결과."""
    recognized_text: str = ""          # STT 인식 텍스트
    parsed: dict = field(default_factory=dict)  # LLM이 추출한 구조화 데이터
    reply_text: str = ""               # LLM이 생성한 응답 문장
    reply_audio: bytes | None = None   # TTS가 생성한 WAV bytes
    success: bool = True
    error: str = ""


class MalPyoEngine:
    """STT → LLM → TTS 파이프라인 통합 엔진.

    app.py에서는 이 클래스만 사용한다.
    """

    def __init__(
        self,
        stt: STTEngine | None = None,
        llm: LLMEngine | None = None,
        tts: TTSEngine | None = None,
    ) -> None:
        self.stt = stt or STTEngine()
        self.llm = llm or LLMEngine()
        self.tts = tts or TTSEngine()

    def process(
        self,
        audio_bytes: bytes,
        page: str,
        context: dict | None = None,
    ) -> PipelineResult:
        """음성 → 텍스트 → 구조화 파싱 → 응답 음성까지 한 번에 처리.

        Args:
            audio_bytes: 녹음된 WAV 바이트
            page: 현재 페이지 ("booking", "discount", "payment")
            context: LLM에 전달할 추가 컨텍스트
        """
        result = PipelineResult()

        # ── 1단계: STT ──
        try:
            stt_result = self.stt.transcribe(audio_bytes)
            result.recognized_text = stt_result.text.strip()
        except Exception as e:
            logger.error("STT 실패: %s", e)
            result.success = False
            result.error = f"음성 인식 실패: {e}"
            return result

        if not result.recognized_text:
            result.success = False
            result.error = "음성이 인식되지 않았습니다. 다시 말씀해 주세요."
            return result

        logger.info("STT 결과: %s", result.recognized_text)

        # ── 2단계: LLM (Ollama) ──
        try:
            llm_result: LLMResult = self.llm.parse(
                result.recognized_text, page, context
            )

            if llm_result.success:
                result.parsed = llm_result.raw_json
                result.reply_text = llm_result.reply
            else:
                logger.warning("LLM 파싱 실패, STT 텍스트만 반환: %s", llm_result.error)
                result.reply_text = result.recognized_text
        except Exception as e:
            logger.error("LLM 처리 실패: %s", e)
            result.reply_text = result.recognized_text

        logger.info("LLM 파싱: %s", result.parsed)
        logger.info("LLM 응답: %s", result.reply_text)

        # ── 3단계: TTS ──
        if result.reply_text:
            try:
                result.reply_audio = self.tts.synthesize(result.reply_text)
            except Exception as e:
                logger.error("TTS 실패: %s", e)
                # TTS 실패해도 텍스트 결과는 유효하므로 계속 진행

        return result

    def health_check(self) -> dict[str, bool | str]:
        """각 엔진의 상태를 확인한다."""
        status: dict[str, bool | str] = {}

        # STT
        try:
            self.stt._load_model()
            status["stt"] = True
        except Exception as e:
            status["stt"] = f"오류: {e}"

        # LLM (Ollama)
        status["llm"] = self.llm.health_check()

        # TTS
        try:
            self.tts._load_engine()
            status["tts"] = True
        except Exception as e:
            status["tts"] = f"오류: {e}"

        return status
