# 사용자 가이드

## 목차

1. [빠른 시작](#빠른-시작)
2. [시스템 요구사항](#시스템-요구사항)
3. [설치](#설치)
4. [API 키 설정](#api-키-설정)
5. [시뮬레이터 실행](#시뮬레이터-실행)
6. [주요 기능 사용법](#주요-기능-사용법)
7. [문제 해결](#문제-해결)

---

## 빠른 시작

### 1분 안에 시작하기

```bash
# 1. 프로젝트 디렉토리로 이동
cd 007_maritime_simulator2030

# 2. 가상 환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 의존성 설치
pip install -r requirements.txt

# 4. 환경 변수 설정
cp .env.example .env
# .env 파일을 열고 AISSTREAM_API_KEY를 입력하세요

# 5. 실행
cd src
streamlit run app.py
```

브라우저에서 자동으로 `http://localhost:8501`이 열립니다.

---

## 시스템 요구사항

### 필수 사항

- **Python**: 3.10 이상
- **운영체제**: Windows, macOS, Linux
- **메모리**: 최소 4GB RAM (8GB 권장)
- **네트워크**: 인터넷 연결 (실시간 AIS 데이터용)

### 권장 환경

- **브라우저**: Chrome, Firefox, Edge (최신 버전)
- **화면 해상도**: 1920x1080 이상

---

## 설치

### Python 패키지 설치

```bash
pip install -r requirements.txt
```

### 설치 확인

```bash
python -c "import streamlit; import folium; import shapely; print('설치 완료!')"
```

---

## API 키 설정

### AISStream API 키 발급

1. https://aisstream.io 접속
2. 무료 계정 생성 (이메일만 필요)
3. API 키 복사

### 환경 변수 설정

`.env` 파일 생성:

```bash
cp .env.example .env
```

`.env` 파일 내용:

```bash
AISSTREAM_API_KEY=여기에_실제_API_키_붙여넣기
ENABLE_REAL_AIS=true
SIMULATION_UPDATE_INTERVAL_SEC=10
LOG_LEVEL=INFO
```

⚠️ **주의**: `.env` 파일은 Git에 커밋하지 마세요!

---

## 시뮬레이터 실행

### 방법 1: 실행 스크립트 사용 (권장)

**Windows:**
```bash
run_simulator.bat
```

**Linux/Mac:**
```bash
chmod +x run_simulator.sh
./run_simulator.sh
```

### 방법 2: 직접 실행

```bash
cd src
streamlit run app.py
```

### 실행 확인

브라우저에서 다음 화면이 보이면 성공:
- 왼쪽 사이드바: 제어 패널
- 중앙: "🚀 시뮬레이션 초기화" 버튼

---

## 주요 기능 사용법

### 1. 시뮬레이션 초기화

1. 왼쪽 사이드바에서 **"🚀 시뮬레이션 초기화"** 버튼 클릭
2. 초기화 완료 후 "초기화 완료!" 메시지 확인

### 2. 시뮬레이션 시작/정지

- **▶️ 시작**: 선박 이동 시작
- **⏸️ 정지**: 선박 이동 일시 정지

### 3. 통신 시나리오 선택

사이드바에서 시나리오 선택:

| 시나리오 | 통신 방식 | 특징 |
|----------|-----------|------|
| 정상 조건 | VSAT | 안정적 통신 |
| 악천후 | VSAT | 신호 품질 저하 60% |
| LEO 위성 핸드오버 | Starlink | 저지연 통신 |

### 4. 저하 수준 조절

슬라이더를 이용해 통신 품질 저하 수준 조정:
- **0.0**: 정상
- **0.5**: 중간 저하
- **1.0**: 최대 저하

### 5. 지도 보기

**실시간 지도** 탭에서:
- 🔵 파란색 = LNG 선박
- 🟢 초록색 = 암모니아 선박
- 🔴 빨간색 = SMR 선박
- 🟠 주황색 원 = Dead Reckoning 오차 반경

### 6. 성능 분석

**성능 분석** 탭에서:
- 총 패킷 수
- 손실 패킷 수
- 신뢰성 지수 (SAI)
- 평균 지연 시간

### 7. 이벤트 로그 확인

**이벤트 로그** 탭에서 SMR 선박의 위반 이벤트 확인:
- 통로 이탈
- 지오펜스 위반
- 속도 위반

---

## 개별 모듈 테스트

각 모듈을 독립적으로 테스트할 수 있습니다:

```bash
cd src

# Dead Reckoning 엔진
python prediction_engine.py

# 암모니아 선박 시뮬레이션
python simulation_ammonia.py

# SMR 선박 시뮬레이션
python simulation_smr.py

# 시나리오 컨트롤러
python scenario_controller.py

# AIS 클라이언트 (API 키 필요)
export AISSTREAM_API_KEY=your_key  # Linux/Mac
set AISSTREAM_API_KEY=your_key     # Windows
python ais_client.py
```

---

## 문제 해결

### Q1: AIS 데이터가 수신되지 않아요

**해결 방법:**

1. `.env` 파일에 API 키가 올바르게 설정되었는지 확인
   ```bash
   cat .env | grep AISSTREAM_API_KEY
   ```

2. 인터넷 연결 확인

3. AISStream 서비스 상태 확인
   - https://status.aisstream.io

4. 로그 레벨을 DEBUG로 변경
   ```bash
   LOG_LEVEL=DEBUG streamlit run app.py
   ```

### Q2: 지도가 표시되지 않아요

**해결 방법:**

1. 인터넷 연결 확인 (Folium은 온라인 지도 타일 사용)

2. 브라우저 콘솔 확인 (F12 키)

3. Streamlit 캐시 삭제
   ```bash
   streamlit cache clear
   ```

### Q3: 시뮬레이션이 느려요

**해결 방법:**

1. 업데이트 간격 증가
   ```bash
   # .env 파일에서
   SIMULATION_UPDATE_INTERVAL_SEC=30
   ```

2. 실시간 AIS 비활성화
   ```bash
   ENABLE_REAL_AIS=false
   ```

### Q4: 모듈을 찾을 수 없다는 오류

**해결 방법:**

```bash
# 올바른 디렉토리에서 실행하는지 확인
pwd  # 현재 위치 확인
cd 007_/maritime_comm_simulator_2030/src

# 의존성 재설치
cd ..
pip install -r requirements.txt --force-reinstall
```

### Q5: Python 버전 오류

**해결 방법:**

Python 3.10 이상 필요:

```bash
python --version  # 버전 확인

# pyenv로 Python 3.10 설치 (권장)
pyenv install 3.10.11
pyenv local 3.10.11
```

### Q6: Windows에서 스크립트 실행 오류

**해결 방법:**

PowerShell 실행 정책 변경:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## 고급 사용

### 데이터 내보내기

```python
from simulation_smr import SMRVesselSimulator

# 위반 로그를 JSON으로 내보내기
simulator.export_violation_log("data/gold/violations.json")
```

### 커스텀 항로 생성

```python
from simulation_ammonia import Route, Waypoint

custom_route = Route(
    route_name="커스텀 항로",
    waypoints=[
        Waypoint(35.0, 129.0, "부산", 15.0),
        Waypoint(37.5, 140.0, "태평양", 17.0),
        Waypoint(40.0, 150.0, "북태평양", 17.0)
    ]
)
```

### 통신 프로파일 커스터마이징

```python
from scenario_controller import CommunicationProfile, CommunicationType

custom_profile = CommunicationProfile(
    comm_type=CommunicationType.VSAT,
    latency_mean_ms=400,
    latency_std_ms=80,
    packet_loss_good_state=0.02,
    packet_loss_bad_state=0.30,
    prob_good_to_bad=0.05,
    prob_bad_to_good=0.20,
    normal_update_interval_sec=10,
    degraded_update_interval_sec=30,
    critical_update_interval_sec=120
)
```

---

## 성능 최적화

### 대용량 처리

```python
# config.py에서 조정
config.simulation_speed_multiplier = 2.0  # 2배속
config.update_interval_sec = 20  # 업데이트 주기 증가
```

### 메모리 절약

히스토리 버퍼 크기 제한 (코드 수정 필요):
```python
MAX_HISTORY_SIZE = 1000  # 최근 1000개만 유지
```

---

## 추가 자료

- **시스템 아키텍처**: `docs/private/시스템_아키텍처.md`
- **릴리스 노트**: `Release.md`
- **데이터 카탈로그**: `governance/catalog/`

---

## 지원

- **기술 문의**: GitHub Issues
- **문서 오류**: Pull Request
- **일반 문의**: 프로젝트 관리자

---

**작성일**: 2026-01-24
**버전**: 1.0.0
