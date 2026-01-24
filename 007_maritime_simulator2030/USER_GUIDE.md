# 🚢 2030 해상 통신 시뮬레이션 플랫폼 - 사용자 가이드

## 프로젝트 개요

본 프로젝트는 **AIS + 위성 통신 인프라가 2030년 혼합 차세대 선박 환경을 안정적으로 지원할 수 있는지 평가**하기 위한 연구용 시뮬레이터입니다.

실제 AIS 스트림과 합성 시뮬레이션을 결합하여 다음을 분석합니다:
- 실시간 자율선박 추적 (AIS 기반)
- 대양 선박 예상 위치 계산 (Great Circle 항법)
- 차세대 연료선 시뮬레이션 (암모니아, SMR)
- 통신 신뢰성 및 Dead Reckoning 정확도 평가

---

## 빠른 시작

### 1. 환경 준비

**필수 요구사항:**
- Python 3.10 이상
- AISStream API 키 (무료: https://aisstream.io)

### 2. 설치

```bash
# 프로젝트 폴더로 이동
cd 007_maritime_simulator2030

# 가상환경 생성
python -m venv venv

# 가상환경 활성화
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### 3. API 키 설정

`.env` 파일을 열어 AISStream API 키를 입력합니다:

```env
AISSTREAM_API_KEY=your_actual_api_key_here
```

### 4. 실행

**Windows:**
```bash
run_simulator.bat
```

**Linux/Mac:**
```bash
bash run_simulator.sh
```

또는 직접 실행:
```bash
streamlit run src/app.py
```

### 5. 웹 브라우저 접속

자동으로 브라우저가 열리거나 http://localhost:8501 로 접속합니다.

---

## 선박 구성

### 실시간 AIS 추적 선박 (5척)

| 선박명 | MMSI | IMO | 역할 | 마커 색상 |
|--------|------|-----|------|-----------|
| **Yara Birkeland** | 257646000 | 9865049 | 완전 자율 상징 | ⚫ 검은색 |
| **Therese** | 259005610 | 9921788 | 전기/연안 시험 | ⚫ 검은색 |
| **Marit** | 258022650 | 9921776 | 전기/연안 시험 | ⚫ 검은색 |
| **Prism Courage** | 352986205 | 9888481 | AI 항해 보조 (Avikus HiNAS) | 🔵 하늘색 (예상) |
| **HMM Algeciras** | 440326000 | 9863297 | 일반 대형 상선 (비교군) | 🔵 하늘색 (예상) |

**특징:**
- Yara Birkeland, Marit, Therese: 노르웨이 연안에서 실시간 추적 (AIS)
- Prism Courage, HMM Algeciras: 대양 항해 중 → 예상 위치로 표시

### 시뮬레이션 선박

#### 차세대 암모니아 함대 (5척) - 🟢 녹색

| 선박명 | 항로 | 참고 프로젝트 |
|--------|------|--------------|
| **SAKIGAKE** (魁) | UAE → Korea | 일본 NEDO 프로젝트 |
| **HORIZON** | Australia → Japan | NYK 프로젝트 |
| **TAURUS** | US Gulf → Rotterdam | BHP/COSCO 프로젝트 |
| **AQUARIUS** | Chile → Shanghai | Trafigura 프로젝트 |
| **PHOENIX** | Norway → UAE | 현대 EPS-HD 프로젝트 |

#### SMR 추진 선박 (1척) - 🔴 빨간색

| 선박명 | 경로 | 특징 |
|--------|------|------|
| **SMR-PACIFIC-PIONEER** | Seattle → Tokyo | 통로 제약 시뮬레이션 |

---

## 사용 방법

### 초기 설정

1. 왼쪽 사이드바에서 **"🚀 시뮬레이션 초기화"** 버튼 클릭
2. AIS 클라이언트가 자동으로 연결됩니다
3. 암모니아 선박과 SMR 선박이 자동 생성됩니다

### 시뮬레이션 제어

- **▶️ 시작**: 시뮬레이션 시작
- **⏸️ 정지**: 시뮬레이션 일시 정지
- **🔄 지도 새로고침**: 수동으로 지도 업데이트

### 시나리오 선택

사이드바에서 통신 시나리오를 선택할 수 있습니다:
- **정상 조건**: AIS 지상국 정상 작동
- **악천후**: 통신 지연 및 패킷 손실 증가
- **LEO 위성 핸드오버**: Starlink/OneWeb 핸드오버 시뮬레이션

### 통신 저하 수준 조절

슬라이더로 통신 저하 수준을 0.0 (정상) ~ 1.0 (심각) 범위로 조절할 수 있습니다.

---

## 지도 보기

### 마커 색상 의미

- ⚫ **검은색**: 실시간 AIS 데이터 (자율선박)
- 🟢 **녹색**: 암모니아 연료 선박 (시뮬레이션)
- 🔴 **빨간색**: SMR 추진 선박 (시뮬레이션)
- 🔵 **하늘색**: 예상 위치 (대양 선박, 실시간 AIS 없음)

### 선박 정보 확인

- 마커를 클릭하면 선박 상세 정보가 팝업으로 표시됩니다
- 침로 방향은 삼각형 화살표로 표시됩니다 (예상 위치 제외)

### 오차 반경 (주황색 원)

시뮬레이션 선박 주변의 주황색 원은 Dead Reckoning 95% 신뢰 오차 반경입니다.

---

## 탭별 기능

### 🗺️ 실시간 지도

- 모든 선박의 현재 위치를 지도에 표시
- 선박 목록 테이블로 상세 정보 확인
- 실시간 AIS와 예상 위치 구분 표시

### 📈 성능 분석

- 통신 신뢰성 지수
- 패킷 손실률
- 평균 지연 시간
- Dead Reckoning 예측 오차 시계열 그래프

### ⚠️ 이벤트 로그

- SMR 선박의 항로 이탈 및 위반 이벤트
- 지오펜스 위반 기록
- 최근 20건 이벤트 표시

### ℹ️ 시스템 정보

- 통신 프로파일 (AIS, VSAT, LEO 위성)
- 선박 구성 요약
- 수학적 모델 설명

---

## 예상 위치 계산 방식

### Prism Courage (LNG 탱커)

**항로**: 텍사스 Sabine Pass → 파나마 운하 → 태평양 → 한국 평택항

**출발 시간**: 2026-01-10 (가정)
**평균 속도**: 19 knots
**항법**: Great Circle Navigation

### HMM Algeciras (컨테이너선)

**항로**: 부산 → 싱가포르 → 인도양 → 수에즈 운하 → 로테르담

**출발 시간**: 2026-01-05 (가정)
**평균 속도**: 22 knots
**항법**: Great Circle Navigation

**참고**: 실시간 AIS 데이터가 수신되면 자동으로 검은색 마커로 전환됩니다.

---

## 프로젝트 구조

```
007_maritime_simulator2030/
│
├── src/                          # 소스 코드
│   ├── ais_client.py            # AIS WebSocket 클라이언트
│   ├── prediction_engine.py     # Dead Reckoning 엔진
│   ├── simulation_ammonia.py    # 암모니아 선박 시뮬레이터
│   ├── simulation_smr.py        # SMR 선박 시뮬레이터
│   ├── simulation_oceanic.py    # 대양 선박 예상 위치 계산
│   ├── scenario_controller.py   # 통신 시나리오 컨트롤러
│   ├── app.py                   # Streamlit 웹 앱
│   └── config.py                # 설정 관리
│
├── data/                         # 데이터 저장소
│   ├── bronze/                  # 원시 AIS 데이터
│   │   └── Autonomous_Fleet.csv # 자율선박 목록
│   ├── silver/                  # 전처리된 데이터
│   └── gold/                    # 최종 분석 데이터
│
├── governance/                   # 데이터 거버넌스
│   ├── catalog/                 # 데이터 카탈로그
│   ├── lineage/                 # 데이터 계보
│   ├── quality/                 # 품질 검증
│   └── policy/                  # 정책 문서
│
├── notebooks/                    # Databricks 노트북
│   ├── 01_data_ingestion_bronze.py
│   ├── 02_data_processing_silver.py
│   └── 03_eta_calculation_gold.py
│
├── docs/                         # 문서
│   └── private/                 # 내부 문서
│       ├── AIS_Issue_Diagnosis.md
│       └── ...
│
├── tests/                        # 테스트 파일
│
├── requirements.txt              # Python 의존성
├── .env                          # 환경 변수 (API 키)
├── run_simulator.bat            # Windows 실행 스크립트
├── run_simulator.sh             # Linux/Mac 실행 스크립트
│
└── USER_GUIDE.md                # 본 문서
```

---

## 기술 스택

| 구분 | 기술 |
|------|------|
| **언어** | Python 3.10+ |
| **웹 프레임워크** | Streamlit |
| **지도 시각화** | Folium |
| **지리 공간** | Shapely, Geopy |
| **수치 계산** | NumPy, SciPy |
| **비동기 통신** | WebSockets, asyncio |
| **AIS 데이터** | AISStream.io API |

---

## 수학적 기반

### Great Circle Navigation (대권항법)

두 지점 사이의 최단 거리 계산:

```
Haversine 거리 공식:
a = sin²(Δφ/2) + cos(φ₁)·cos(φ₂)·sin²(Δλ/2)
c = 2·atan2(√a, √(1-a))
d = R·c

여기서:
- φ: 위도 (라디안)
- λ: 경도 (라디안)
- R: 지구 반지름 (6371 km)
- d: 거리 (km)
```

### Dead Reckoning (추측항법)

현재 위치에서 침로와 속도로 미래 위치 예측:

```
위도 예측:
φ₂ = asin(sin(φ₁)·cos(δ) + cos(φ₁)·sin(δ)·cos(θ))

경도 예측:
λ₂ = λ₁ + atan2(sin(θ)·sin(δ)·cos(φ₁), cos(δ) - sin(φ₁)·sin(φ₂))

여기서:
- θ: 침로 (라디안)
- δ: 각거리 = 거리 / 지구반지름
- (φ₁, λ₁): 시작 위치
- (φ₂, λ₂): 예측 위치
```

### 오차 반경 (95% 신뢰)

```
σ_total(t) = √(σ_센서² + σ_침로²·t² + σ_속도²·t²)
r₉₅(t) = 2.45 · σ_total(t)

여기서:
- σ_센서: GPS 센서 오차 (5-10m)
- σ_침로: 침로 오차 (±2°)
- σ_속도: 속도 오차 (±0.5 knots)
- t: 경과 시간 (초)
```

---

## 통신 프로파일

### AIS 지상국
- **지연**: 2000 ± 500 ms
- **업데이트 간격**: 10초 (항해 중)
- **커버리지**: 연안 ~50 해리

### VSAT 위성
- **지연**: 500 ± 100 ms
- **업데이트 간격**: 5초
- **커버리지**: 전 해역 (GEO 위성)

### LEO 위성 (Starlink, OneWeb)
- **지연**: 30 ± 10 ms
- **업데이트 간격**: 2초
- **커버리지**: 전 해역 (극지 포함)

---

## 문제 해결

### AIS 연결이 안 될 때

1. API 키가 올바른지 확인 (.env 파일)
2. 인터넷 연결 확인
3. AISStream 서비스 상태 확인: https://aisstream.io/status

### 자율선박이 표시되지 않을 때

- Prism Courage와 HMM Algeciras는 대양 항해 중이므로 예상 위치(하늘색)로 표시됩니다
- 실시간 AIS는 연안 ~50 해리 범위에서만 수신 가능
- 위성 AIS는 무료 플랜에서 제한적

### 지도가 깜빡일 때

- 자동 새로고침 대신 "🔄 지도 새로고침" 버튼을 수동으로 클릭하세요
- 시뮬레이션 중에는 자동 rerun이 비활성화되어 있습니다

---

## 데이터 소스 및 출처

### 실시간 AIS 데이터
- **출처**: AISStream.io
- **라이선스**: 무료 티어 (연구/교육 목적)
- **업데이트**: 실시간 (WebSocket)

### 자율선박 정보
- **출처**: MarineTraffic, VesselFinder
- **검증 날짜**: 2026-01-24
- **파일**: `data/bronze/Autonomous_Fleet.csv`

### 시뮬레이션 데이터
- 암모니아 및 SMR 선박은 **완전 합성** 데이터
- 실제 선박이나 운영을 나타내지 않음

---

## 면책 및 한계

⚠️ **본 시뮬레이터는 연구 프로토타입입니다**

### 사용 제한
- ❌ 실제 항해 의사결정에 사용 금지
- ❌ 상업적 선박 추적 금지
- ✅ 학술 연구 및 교육 목적만 사용

### 기술적 제약
- SMR 선박은 가상 시나리오 (현재 상용화 안됨)
- Dead Reckoning은 실제 환경 (조류, 해류)을 완벽히 반영하지 못함
- 예상 위치는 실제 항로와 다를 수 있음
- 무료 AIS 플랜은 데이터 제한이 있음

---

## 향후 계획

- [ ] 머신러닝 기반 궤적 예측 (LSTM)
- [ ] 다중 선박 충돌 회피 시뮬레이션
- [ ] 위성 커버리지 히트맵
- [ ] 실시간 기상 데이터 통합
- [ ] Power BI 대시보드 연동
- [ ] 사이버 보안 시나리오 (AIS 스푸핑)

---

## 참고 자료

### 자율선박 프로젝트
- **Yara Birkeland**: https://www.yara.com/knowledge-grows/game-changer-for-the-environment/
- **ASKO (Marit, Therese)**: https://asko.no/en/
- **Avikus HiNAS**: https://www.avikus.ai/en/hinas

### AIS 및 해양 통신
- **AISStream**: https://aisstream.io
- **MarineTraffic**: https://www.marinetraffic.com
- **IMO AIS 표준**: https://www.imo.org

### 암모니아 연료선 프로젝트
- **NYK**: https://www.nyk.com
- **BHP/COSCO**: https://www.bhp.com

---

## 라이선스

MIT License - 연구 및 교육 목적으로만 사용

---

## 버전 정보

**개발 완료**: 2026-01-24
**현재 버전**: 1.0.0
**개발자**: Claude Sonnet 4.5

---

## 지원

문제가 발생하거나 질문이 있으신 경우:
1. `docs/private/AIS_Issue_Diagnosis.md` 참조
2. GitHub Issues (프로젝트 저장소)
3. 프로젝트 담당자 문의

---

**즐거운 시뮬레이션 되세요! 🚢**
