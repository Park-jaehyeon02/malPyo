# 🎙️ 말표 (Mal-Pyo)

**대화형 키오스크**







---

## 프로젝트 소개

**말표(Mal-Pyo)** 는 AI agent가 탑재된 키오스크입니다.
터치 없이 대화로 예매를 진행해 보세요.

## 목차

[1. 문제 정의](#1문제-정의)

[2. 해결방안](#2해결방안)

## 1.문제 정의

[![전주MBC 자료](http://img.youtube.com/vi/xGOSdfRZlWw/0.jpg)](https://www.youtube.com/watch?v=xGOSdfRZlWw)



오늘날 무인 단말기(Kiosk)는 일상의 표준이 되었으나, 디지털 소외 계층인 
노인들에게는 **거대한 디지털 장벽**이 되었습니다. 

시력이 안 좋거나 기계가 낯선 분들에게는 이 과정이 큰 장벽임.


## 2.해결방안

프로젝트 **말표**는 복잡한 터치와 검색 과정을 **'일상적인 대화'**로 대체하여 누구나 쉽게 버스 표를 예매할 수 있게 합니다.

### ✅ 자연어 기반 행선지 검색 (Voice Destination Search)
* **구어체 인식:** "내일 아침에 대전 가는 거 제일 빠른 거 줘"와 같이 말하면 시스템이 날짜, 목적지, 시간을 자동으로 추출합니다.
* **유연한 명칭 대응:** "광주 가는 거"라고 말하면 시스템이 현재 위치를 기반으로 가장 적합한 터미널(예: 광주종합버스터미널)을 제안합니다.

### ✅ 대화형 좌석 및 등급 선택
* **음성 가이드:** "현재 10시 30분 우등 버스에 자리가 많이 남았습니다. 예매 해드릴까요?"와 같이 질문을 던져 사용자가 "응, 앞쪽으로 해줘"라고 답하기만 하면 좌석 선택이 완료됩니다.
* **단순화된 시각 피드백:** 선택된 정보(출발 시간, 요금)를 큰 글씨와 그림으로 명확히 보여줍니다.

### ✅ 실시간 확인 및 안심 가이드
* **재확인 절차:** "내일 오전 10시, 대전행 버스 한 명 맞으시죠?"라고 다시 한번 음성으로 확인하여 예매 실수에 대한 불안감을 해소합니다.
* **결제 보조:** "카드로 결제를 진행하겠습니다"와 같이 안내를 결합해 결제 과정을 돕습니다.

---

## 아키텍처

```
┌─────────────────────────────────────────────────────┐
│                    app.py (UI)                      │
│      Mic Input --- Kiosk UI --- Voice Playback      │
└──────────────────────────┬──────────────────────────┘
                           │ audio_bytes + page
┌──────────────────────────▼──────────────────────────┐
│              engine.py (Orchestrator)               │
│                                                     │
│  ┌──────────────┐ ┌─────────────┐ ┌──────────────┐  │
│  │stt_engine.py │ │llm_engine.py│ │tts_engine.py │  │
│  │              │ │             │ │              │  │
│  │faster-whisper│ │   Ollama    │ │   pyttsx3    │  │
│  │ Large-v3-    │ │ Structured  │ │  WAV Audio   │  │
│  │  turbo       │ │ JSON Parse  │ │  Synthesis   │  │
│  │ (GPU/CUDA)   │ │             │ │              │  │
│  └──────┬───────┘ └──────┬──────┘ └──────┬───────┘  │
│         │ text           │ JSON+reply    │ WAV      │
└─────────┼────────────────┼───────────────┼──────────┘
          └────────────────┴───────────────┘
                           │ PipelineResult
┌──────────────────────────▼──────────────────────────┐
│                    app.py (UI)                      │
│     Auto-fill Form + Show Reply + Play Audio        │
└─────────────────────────────────────────────────────┘
```

### Voice Pipeline Flow

```
🎤 Mic Record (st.audio_input)
    ↓
📝 stt_engine.py (faster-whisper, GPU) → Text
    ↓
🧠 llm_engine.py (Ollama) → Structured JSON + Reply
    ↓
🔊 tts_engine.py (pyttsx3) → Voice Synthesis
    ↓
🔈 app.py → Auto-fill Form + Voice Playback
```

---

## 기술 스택


| 구성요소    | 기술                              | 비고                |
| -------- | ------------------------------- | ----------------- |
| **STT**  | faster-whisper (Large-v3-turbo) | GPU float16 추론    |
| **LLM**  | Ollama                          | 로컬 서버, JSON 파싱   |
| **TTS**  | pyttsx3                         | 오프라인 음성 합성       |
| **UI**   | Streamlit                       | 고대비 키오스크 UI      |
| **GPU**  | NVIDIA RTX 5080                 | CUDA 12.x        |   


---

## 설치 방법

### 사전 요구 사항

- Python 3.10 이상
- NVIDIA GPU + CUDA 12.x + cuDNN 9.x
- Ollama 설치 및 모델 다운로드

### 설치

```bash
# 가상환경 생성
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/macOS

# 패키지 설치
pip install -r requirements.txt
```

---

## 실행 방법

```bash
# 가상환경 활성화 후
streamlit run app.py
```

브라우저에서 `http://localhost:8502` 로 접속합니다.

### 사용법

1. 첫 화면에서 **"기존 모드"** 또는 **"대화형 모드"**를 선택합니다.
2. 대화형 모드: 음성 바의 마이크 아이콘을 눌러 말합니다.
3. AI가 음성을 인식하고, 예매 정보를 자동으로 채운 뒤 음성으로 답변합니다.
4. 기존 모드: 직접 터치/클릭으로 예매를 진행합니다.

---

## 프로젝트 구조

```
malPyo/
├── app.py              # Streamlit UI (키오스크 View/Controller)
├── engine.py           # 파이프라인 오케스트레이터 (STT→LLM→TTS)
├── stt_engine.py       # STT 엔진 (faster-whisper)
├── llm_engine.py       # LLM 엔진 (Ollama, 구조화 JSON)
├── tts_engine.py       # TTS 엔진 (pyttsx3)
├── static/
│   └── kiosk.css       # 키오스크 UI 스타일시트
├── .streamlit/
│   └── config.toml     # Streamlit 서버 설정 (포트 8502)
├── requirements.txt    # Python 의존성
└── README.md           # 프로젝트 문서 (현재 파일)
```

---

## Ollama 설정

```bash
# Ollama 설치: https://ollama.ai
ollama pull llama3:8b

# Ollama 서버가 http://localhost:11434 에서 실행 중이어야 합니다.
```

---

## 접근성 (Accessibility)

말표는 시각장애인 사용자를 최우선으로 고려하여 설계되었습니다:

- **고대비 다크 테마**: WCAG AAA 수준의 명암비
- **대형 텍스트**: 최소 1.2rem, 제목은 2.8rem
- **스크린리더 호환**: ARIA 레이블, role 속성 적용
- **키보드 내비게이션**: Tab/Enter/Esc로 전체 조작 가능
- **음성 자동 재생**: 응답을 별도 조작 없이 즉시 들을 수 있음
- **포커스 표시**: 모든 인터랙티브 요소에 3px 골드 아웃라인

---

## 라이선스

MIT License

---

## 기여하기

이슈와 PR을 환영합니다. 접근성 개선 제안은 특히 감사합니다.