#!/bin/bash
# Maritime Communication Simulator 2030 - Linux/Mac 실행 스크립트
# ================================================================

echo ""
echo "========================================"
echo "Maritime Communication Simulator 2030"
echo "========================================"
echo ""

# 환경 변수 확인
if [ ! -f .env ]; then
    echo "[경고] .env 파일이 없습니다!"
    echo ".env.example을 .env로 복사하고 API 키를 설정하세요."
    echo ""
    read -p "계속하시겠습니까? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Python 버전 확인
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED_VERSION="3.10"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null; then
    echo "[오류] Python 3.10 이상이 필요합니다."
    echo "현재 버전: $PYTHON_VERSION"
    exit 1
fi

# 의존성 확인
if ! python3 -c "import streamlit" 2>/dev/null; then
    echo "[정보] 의존성을 설치합니다..."
    pip3 install -r requirements.txt
fi

# 시뮬레이터 실행
echo ""
echo "[정보] 시뮬레이터를 시작합니다..."
echo "브라우저에서 http://localhost:8501 이 자동으로 열립니다."
echo ""

streamlit run app.py
