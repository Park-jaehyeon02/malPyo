"""
llm_engine.py - Ollama 기반 LLM 엔진

사용자의 자연어 발화를 구조화된 JSON으로 변환한다.
페이지(booking / discount / payment)별로 다른 프롬프트를 적용하여
app.py가 필요로 하는 필드만 정확히 추출한다.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

import requests

logger = logging.getLogger("malpyo.llm")

# Ollama가 반환해야 할 페이지별 JSON 스키마 예시를 프롬프트에 포함
SYSTEM_PROMPTS: dict[str, str] = {
    "booking": (
        "너는 교통 예매 키오스크의 음성 파싱 엔진이야.\n"
        "사용자가 말한 내용에서 출발지, 도착지, 출발시간, 인원수를 추출해.\n"
        "가능한 도시: 서울, 대전, 대구, 부산, 광주, 전주, 강릉, 제주\n"
        "가능한 시간: 08:00, 10:00, 12:00, 14:00, 16:00, 18:00, 20:00\n"
        "반드시 아래 JSON 형식으로만 응답해. 다른 텍스트 금지.\n"
        '{"departure":"서울","arrival":"전주","time":"14:00","passengers":2,'
        '"reply":"서울에서 전주, 오후 2시, 2명으로 예매할게요."}\n'
        "추출할 수 없는 필드는 null로 채워."
    ),
    "discount": (
        "너는 교통 예매 키오스크의 음성 파싱 엔진이야.\n"
        "사용자가 말한 내용에서 탑승객별 할인 유형을 추출해.\n"
        "가능한 할인 id: normal, disabled, senior, child, youth\n"
        "반드시 아래 JSON 형식으로만 응답해. 다른 텍스트 금지.\n"
        '{"discounts":["child","senior"],'
        '"reply":"탑승객 1은 어린이, 탑승객 2는 경로 할인을 적용할게요."}\n'
        "탑승객 수만큼 discounts 배열을 채워. 언급 안 된 탑승객은 normal."
    ),
    "payment": (
        "너는 교통 예매 키오스크의 음성 파싱 엔진이야.\n"
        "사용자가 말한 내용에서 결제 수단을 추출해.\n"
        "가능한 결제 id: card, cash, mobile, transfer\n"
        "card=신용/체크카드, cash=현금, mobile=모바일페이, transfer=계좌이체\n"
        "반드시 아래 JSON 형식으로만 응답해. 다른 텍스트 금지.\n"
        '{"payment":"card","reply":"카드로 결제하겠습니다."}'
    ),
}


@dataclass
class LLMResult:
    """LLM 파싱 결과."""
    raw_json: dict = field(default_factory=dict)
    reply: str = ""
    success: bool = True
    error: str = ""


class LLMEngine:
    """Ollama 전용 LLM 엔진."""

    def __init__(
        self,
        model: str = "llama3:8b",
        base_url: str = "http://localhost:11434",
        timeout: int = 30,
    ) -> None:
        self.model = model
        self.base_url = base_url
        self.timeout = timeout

    def health_check(self) -> bool:
        """Ollama 서버 연결 상태를 확인한다."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def parse(self, user_text: str, page: str, context: dict | None = None) -> LLMResult:
        """사용자 발화를 페이지에 맞는 구조화된 JSON으로 변환한다.

        Args:
            user_text: STT가 인식한 텍스트
            page: 현재 페이지 ("booking", "discount", "payment")
            context: 추가 컨텍스트 (예: 현재 인원수 등)
        """
        system_prompt = SYSTEM_PROMPTS.get(page)
        if not system_prompt:
            return LLMResult(success=False, error=f"알 수 없는 페이지: {page}")

        if context:
            system_prompt += f"\n현재 상태: {json.dumps(context, ensure_ascii=False)}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ]

        try:
            resp = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "format": "json",
                },
                timeout=self.timeout,
            )
            resp.raise_for_status()

            content = resp.json()["message"]["content"].strip()
            parsed = json.loads(content)
            reply = parsed.pop("reply", "")

            return LLMResult(raw_json=parsed, reply=reply)

        except json.JSONDecodeError as e:
            logger.error("LLM JSON 파싱 실패: %s", e)
            return LLMResult(success=False, error=f"JSON 파싱 실패: {e}")
        except requests.RequestException as e:
            logger.error("Ollama 요청 실패: %s", e)
            return LLMResult(success=False, error=f"Ollama 연결 실패: {e}")
        except Exception as e:
            logger.error("LLM 처리 오류: %s", e)
            return LLMResult(success=False, error=str(e))
