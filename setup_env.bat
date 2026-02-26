@echo off
chcp 65001 >nul 2>&1
title 말표 (Mal-Pyo) 환경 설정

echo ============================================================
echo   🎙️  말표 (Mal-Pyo) — 환경 설정 스크립트
echo   RTX 5080 GPU 로컬 구동을 위한 자동 설치
echo ============================================================
echo.

:: ----------------------------------------------------------
:: 1. Python 버전 확인
:: ----------------------------------------------------------
echo [1/6] Python 버전 확인 중...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python이 설치되지 않았습니다. Python 3.10 이상을 설치해 주세요.
    echo    https://www.python.org/downloads/
    pause
    exit /b 1
)
python --version
echo.

:: ----------------------------------------------------------
:: 2. 가상환경 생성
:: ----------------------------------------------------------
echo [2/6] 가상환경 생성 중...
if not exist ".venv" (
    python -m venv .venv
    echo ✓ 가상환경 생성 완료 (.venv)
) else (
    echo ✓ 기존 가상환경 발견, 재사용합니다.
)
echo.

:: ----------------------------------------------------------
:: 3. 가상환경 활성화
:: ----------------------------------------------------------
echo [3/6] 가상환경 활성화...
call .venv\Scripts\activate.bat
echo ✓ 가상환경 활성화 완료
echo.

:: ----------------------------------------------------------
:: 4. pip 업그레이드 및 기본 패키지 설치
:: ----------------------------------------------------------
echo [4/6] 기본 패키지 설치 중... (시간이 소요될 수 있습니다)
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ 기본 패키지 설치에 실패했습니다. 로그를 확인해 주세요.
    pause
    exit /b 1
)
echo ✓ 기본 패키지 설치 완료
echo.

:: ----------------------------------------------------------
:: 5. MeloTTS 설치 (GPU 음성 합성)
:: ----------------------------------------------------------
echo [5/6] MeloTTS 설치 중... (GPU 음성 합성 엔진)
pip install git+https://github.com/myshell-ai/MeloTTS.git
if errorlevel 1 (
    echo ⚠️ MeloTTS 설치에 실패했습니다. pyttsx3 폴백으로 작동합니다.
    echo    수동 설치: pip install git+https://github.com/myshell-ai/MeloTTS.git
) else (
    echo ✓ MeloTTS 설치 완료
)
echo.

:: ----------------------------------------------------------
:: 6. 환경 변수 파일 생성
:: ----------------------------------------------------------
echo [6/6] 환경 변수 설정...
if not exist ".env" (
    copy .env.example .env >nul 2>&1
    echo ✓ .env 파일이 생성되었습니다. API 키를 입력해 주세요.
) else (
    echo ✓ 기존 .env 파일 발견, 건너뜁니다.
)
echo.

:: ----------------------------------------------------------
:: CUDA 확인
:: ----------------------------------------------------------
echo ============================================================
echo   CUDA 환경 확인
echo ============================================================
nvidia-smi >nul 2>&1
if errorlevel 1 (
    echo ⚠️ nvidia-smi를 실행할 수 없습니다.
    echo    NVIDIA 드라이버가 설치되어 있는지 확인해 주세요.
    echo    https://www.nvidia.com/drivers
) else (
    nvidia-smi
)
echo.

python -c "import torch; print(f'PyTorch CUDA: {torch.cuda.is_available()}, Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')" 2>nul
if errorlevel 1 (
    echo ⚠️ PyTorch가 CUDA를 감지하지 못합니다.
    echo    CUDA 12.x용 PyTorch를 수동 설치해 주세요:
    echo    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
)
echo.

echo ============================================================
echo   ✅ 설치 완료!
echo ============================================================
echo.
echo   실행 방법:
echo     1. .env 파일에 OPENAI_API_KEY를 입력하세요 (GPT-4o 사용 시)
echo     2. 다음 명령으로 실행하세요:
echo.
echo        .venv\Scripts\activate
echo        streamlit run app.py
echo.
echo ============================================================
pause
