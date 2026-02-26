# 🎙️ 말표 (Mal-Pyo)
**대화형 키오스크**

<p align="center">

  <img src="/kiosk_horse.png" width="400"/>

</p>

---

## 프로젝트 소개
**말표(Mal-Pyo)** 는 AI agent가 탑재된 키오스크입니다.
터치 없이 대화로 예매를 진행해 보세요.

## 목차
[1. 문제 정의](#1문제-정의)

[2. 해결방안](#2해결방안)

## 1.문제 정의
[![전주MBC 자료](http://img.youtube.com/vi/xGOSdfRZlWw/0.jpg)](https://www.youtube.com/watch?v=xGOSdfRZlWw)

오늘날 무인 단말기(Kiosk)는 일상의 표준이 되었으나, 디지털 소외 계층인 노인들에게는 **'거대한 디지털 장벽'**이 되었습니다. 기존 키오스크는 다음과 같은 치명적인 문제점을 안고 있습니다.

기존 키오스크는 사용자가 기계의 '동선(UI)'을 학습해야 함. 
시력이 안 좋거나 기계가 낯선 분들에게는 이 과정이 큰 장벽임.

### 1. 새로운 방식으로 

### 2. 복잡한 목적지 검색 체계
* **지역명 혼동:** '동서울', '서울경부', '센트럴시티' 등 복잡한 터미널 명칭 구분이 어렵습니다.

### 3. 시각적 정보 과부하 (Information Overload)
* **복잡한 배차 표:** 수많은 시간대, 잔여 좌석, 등급(우등/일반) 정보가 한 화면에 쏟아지면 필요한 정보를 찾기 힘듭니다.
* **좌석 선택의 난관:** 작은 사각형으로 표시된 좌석 배치도에서 원하는 자리를 정확히 터치하는 것은 매우 정교한 작업을 요구합니다.

##  2.해결방안


---

## 아키텍처

```
┌──────────────────────────────────────────────────┐
│                 app.py (View/Controller)         │
│                    UI                            │
│     마이크 입력 ─── 채팅 UI ─── 음성 자동재생        │
└────────────────────┬─────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────┐
│               engine.py (Model)                  │
│                                                  │
│  ┌──────────────┐ ┌──────────┐ ┌───────────────┐ │
│  │ STT Engine   │ │LLM Engine│ │  TTS Engine   │ │
│  │faster-whisper│ │          │ │  MeloTTS      │ │
│  │ Large-v3-    │ │          │ │               │ │
│  │  turbo       │ │ Ollama   │ │  pyttsx3      │ │
│  │ (GPU/CUDA)   │ │ llama-cpp│ │  (폴백) ㅁ     │ │
│  └──────────────┘ └──────────┘ └───────────────┘ │
└──────────────────────────────────────────────────┘
```

### 음성 대화 흐름

```
🎤 마이크 입력
    ↓
📝 STT (faster-whisper, GPU) → 텍스트 변환
    ↓
🧠 LLM (GPT-4o / 로컬 LLM) → 의도 파악 & 응답 생성
    ↓
🔊 TTS (MeloTTS, GPU) → 음성 합성
    ↓
🔈 자동 재생 → 사용자에게 음성 전달
```

---

## 기술 스택


| 구성요소         | 기술                              | 비고              |
| ------------ | ------------------------------- | --------------- |
| **STT**      | faster-whisper (Large-v3-turbo) | GPU float16 추론  |
| **TTS (주)**  | MeloTTS                         | 한국어 GPU 음성 합성   |
| **TTS (폴백)** | pyttsx3                         | 완전 오프라인         |
| **LLM (기본)** | OpenAI GPT-4o                   | 클라우드 (추후 교체 가능) |
| **LLM (로컬)** | Ollama / llama-cpp-python       | Llama-3 등       |
| **UI**       | Streamlit                       | 고대비 배리어프리       |
| **GPU**      | NVIDIA RTX 5080                 | CUDA 12.x       |


---

## 설치 방법

### 사전 요구 사항

- Python 3.10 이상
- NVIDIA GPU + CUDA 12.x + cuDNN 9.x
- (선택) Ollama — 로컬 LLM 사용 시

### 1. 자동 설치 (권장)

```bash
# Windows
setup_env.bat

# Linux / macOS
chmod +x setup_env.sh && ./setup_env.sh
```

### 2. 수동 설치

```bash
# 가상환경 생성
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/macOS

# 기본 패키지 설치
pip install -r requirements.txt

# MeloTTS 설치 (GPU 음성 합성)
pip install git+https://github.com/myshell-ai/MeloTTS.git

# (선택) llama-cpp-python GPU 빌드
set CMAKE_ARGS=-DGGML_CUDA=on
pip install llama-cpp-python
```

### 3. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일을 편집하여 API 키를 입력하세요
```

---

## 실행 방법

```bash
# 가상환경 활성화 후
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 로 접속합니다.

### 사용법

1. 사이드바에서 원하는 엔진(TTS, LLM, GPU/CPU)을 선택합니다.
2. **"엔진 시작"** 버튼을 클릭합니다.
3. 마이크 버튼을 눌러 음성으로 질문합니다.
4. AI가 음성으로 답변합니다 (자동 재생).

---

## 프로젝트 구조

```
malPyo/
├── app.py              # Streamlit UI (View/Controller)
├── engine.py           # AI 엔진 (STT/TTS/LLM Model)
├── requirements.txt    # Python 의존성
├── setup_env.bat       # Windows 자동 설치 스크립트
├── setup_env.sh        # Linux/macOS 자동 설치 스크립트
├── .env.example        # 환경변수 템플릿
└── README.md           # 프로젝트 문서 (현재 파일)
```

---

## 로컬 LLM 전환 가이드

GPT-4o 대신 완전 로컬 LLM을 사용하려면:

### Ollama 방식 (권장)

```bash
# Ollama 설치: https://ollama.ai
ollama pull llama3:8b

# app.py 사이드바에서 LLM을 "Ollama (로컬 서버)"로 변경
```

### llama-cpp-python 방식

```bash
# GGUF 모델 다운로드 후 경로 지정
# engine.py에서 LocalLLMEngine(backend="llama_cpp", model_path="./model.gguf")
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