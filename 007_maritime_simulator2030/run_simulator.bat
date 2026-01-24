@echo off
REM Maritime Communication Simulator 2030 - Windows 실행 스크립트
REM ============================================================

echo.
echo ========================================
echo Maritime Communication Simulator 2030
echo ========================================
echo.

REM 환경 변수 확인
if not exist .env (
    echo [경고] .env 파일이 없습니다!
    echo .env.example을 .env로 복사하고 API 키를 설정하세요.
    echo.
    pause
    exit /b 1
)

REM Python 버전 확인
python --version 2>&1 | findstr /R "3\.1[0-9]" >nul
if errorlevel 1 (
    echo [오류] Python 3.10 이상이 필요합니다.
    python --version
    pause
    exit /b 1
)

REM 의존성 확인
python -c "import streamlit" 2>nul
if errorlevel 1 (
    echo [정보] 의존성을 설치합니다...
    pip install -r requirements.txt
)

REM 시뮬레이터 실행
echo.
echo [정보] 시뮬레이터를 시작합니다...
echo 브라우저에서 http://localhost:8501 이 자동으로 열립니다.
echo.

streamlit run app.py

pause
