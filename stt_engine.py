"""
stt_engine.py - faster-whisper 기반 STT 엔진

RTX 5080 GPU에서 float16 추론으로 한국어 음성을 텍스트로 변환한다.
app.py에서 녹음된 오디오 바이트를 받아 처리한다.
"""

from __future__ import annotations

import os
import tempfile
import logging
from dataclasses import dataclass, field

logger = logging.getLogger("malpyo.stt")


@dataclass
class STTResult:
    text: str
    language: str = "ko"
    confidence: float = 0.0
    segments: list = field(default_factory=list)


class STTEngine:
    """faster-whisper 기반 로컬 STT 엔진."""

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
        if self._model is not None:
            return
        try:
            from faster_whisper import WhisperModel

            logger.info(
                "STT 모델 로딩: %s (device=%s, compute=%s)",
                self.model_size, self.device, self.compute_type,
            )
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
            logger.info("STT 모델 로딩 완료")
        except ImportError:
            raise RuntimeError(
                "faster-whisper가 설치되지 않았습니다.\n"
                "pip install faster-whisper 로 설치해주세요."
            )
        except Exception as e:
            logger.error("STT 모델 로딩 실패: %s", e)
            raise RuntimeError(
                f"faster-whisper 모델 로딩 실패.\n"
                f"CUDA/cuDNN 설치를 확인하세요.\n{e}"
            ) from e

    def transcribe(self, audio_data: bytes | str) -> STTResult:
        """오디오 데이터(WAV bytes 또는 파일 경로)를 텍스트로 변환한다."""
        self._load_model()

        audio_input = self._prepare_audio(audio_data)

        try:
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
                avg_confidence = sum(s.avg_log_prob for s in segments) / len(segments)

            return STTResult(
                text=full_text,
                language=info.language,
                confidence=avg_confidence,
                segments=[
                    {"start": s.start, "end": s.end, "text": s.text.strip()}
                    for s in segments
                ],
            )
        finally:
            # 임시 파일 정리
            if isinstance(audio_data, (bytes, bytearray)) and isinstance(audio_input, str):
                try:
                    os.unlink(audio_input)
                except OSError:
                    pass

    @staticmethod
    def _prepare_audio(audio_data) -> str:
        """오디오 입력을 faster-whisper가 인식할 수 있는 파일 경로로 변환."""
        if isinstance(audio_data, str):
            return audio_data
        if isinstance(audio_data, (bytes, bytearray)):
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmp.write(audio_data)
            tmp.close()
            return tmp.name
        raise ValueError(f"지원하지 않는 오디오 형식: {type(audio_data)}")
