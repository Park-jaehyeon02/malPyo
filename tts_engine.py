"""
tts_engine.py - TTS 엔진

LLM이 생성한 응답 텍스트를 음성(WAV bytes)으로 변환하여
app.py에서 사용자에게 재생할 수 있게 한다.

pyttsx3(오프라인, 추가 모델 불필요) 기본 사용.
향후 MeloTTS 등 GPU TTS로 교체 가능하도록 설계.
"""

from __future__ import annotations

import io
import tempfile
import os
import logging

logger = logging.getLogger("malpyo.tts")


class TTSEngine:
    """pyttsx3 기반 오프라인 TTS 엔진."""

    def __init__(self, rate: int = 170, volume: float = 1.0) -> None:
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

            voices = self._engine.getProperty("voices")
            for voice in voices:
                if "korean" in voice.name.lower() or "ko" in voice.id.lower():
                    self._engine.setProperty("voice", voice.id)
                    break

            logger.info("TTS 엔진 초기화 완료 (pyttsx3)")
        except ImportError:
            raise RuntimeError(
                "pyttsx3가 설치되지 않았습니다.\n"
                "pip install pyttsx3 로 설치해주세요."
            )
        except Exception as e:
            logger.error("TTS 초기화 실패: %s", e)
            raise RuntimeError(f"TTS 초기화 실패: {e}") from e

    def synthesize(self, text: str) -> bytes:
        """텍스트를 WAV 바이트로 변환한다."""
        self._load_engine()

        tmp_path = tempfile.mktemp(suffix=".wav")
        try:
            self._engine.save_to_file(text, tmp_path)
            self._engine.runAndWait()

            with open(tmp_path, "rb") as f:
                wav_bytes = f.read()
            return wav_bytes
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
