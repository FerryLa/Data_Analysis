# 차세대 암모니아 함대 명명 완료

**날짜**: 2026-01-24
**작업**: 암모니아 시뮬레이션 선박 5척 이름 부여

---

## 변경 내역

### 변경 전
```python
vessel_name=f"AMMONIA-{i+1}"  # AMMONIA-1, AMMONIA-2, ...
```

### 변경 후
```python
ammonia_vessel_names = [
    "SAKIGAKE",      # 선구자 (일본 NEDO 프로젝트)
    "HORIZON",       # 지평선 (NYK 프로젝트)
    "TAURUS",        # 황소자리 (BHP/COSCO)
    "AQUARIUS",      # 물병자리 (Trafigura)
    "PHOENIX"        # 불사조 (현대 EPS-HD)
]
```

---

## 암모니아 함대 5척

| 선박명           | MMSI      | 항로                  | 실제 프로젝트 참고                | 의미        |
| ------------- | --------- | ------------------- | ------------------------- | --------- |
| **SAKIGAKE**  | 900000001 | UAE → Korea         | NEDO Japan Tugboat        | 魁 (선구자)   |
| **HORIZON**   | 900000002 | Australia → Japan   | NYK Medium Gas Carrier    | 지평선       |
| **TAURUS**    | 900000003 | US Gulf → Rotterdam | BHP/COSCO Bulk Carrier    | 황소자리      |
| **AQUARIUS**  | 900000004 | Chile → Shanghai    | Trafigura Gas Carrier     | 물병자리      |
| **PHOENIX**   | 900000005 | Norway → UAE        | Hyundai EPS-HD            | 불사조 (재탄생) |

---

## 선박명 선정 근거

### 1. SAKIGAKE (魁 - 선구자)
**참고**: [NEDO Green Innovation Fund - Ammonia-Fueled Tugboat](https://green-innovation.nedo.go.jp/en/article/ammonia-fueled-tugboat/)

- **일본 최초 암모니아 추진 예인선** (2024년 시범 운항 완료)
- CO2 배출 90% 이상 감소 달성
- 일본어 "魁(사키가케)"는 "선구자", "개척자"를 의미
- 차세대 친환경 해운의 **첫걸음**을 상징

**항로**: UAE (Abu Dhabi) → Korea (Busan)
- 중동 암모니아 생산 → 한국 수입 주요 항로

---

### 2. HORIZON (지평선)
**참고**: [NYK Line - Choosing Ammonia for Future Fleet](https://www.marinelink.com/news/shipowners-choosing-ammonia-518509)

- **NYK의 차세대 암모니아 가스선 프로젝트** (2026-2027년 건조 예정)
- "Horizon"은 새로운 **미래를 향한 전망**을 상징
- 탄소 중립 목표 달성을 위한 NYK의 비전

**항로**: Australia (Western Australia) → Japan (Tokyo)
- 호주 그린 암모니아 생산 → 일본 수입 루트

---

### 3. TAURUS (황소자리)
**참고**: [BHP & COSCO Ammonia Dual-Fuelled Vessels](https://www.reuters.com/sustainability/climate-energy/bhp-inks-charter-contracts-with-cosco-ammonia-dual-fuelled-vessels-2025-07-02/)

- **BHP의 COSCO와 암모니아 듀얼 퓨얼 선박 계약** (2025년 7월)
- "Taurus" (황소자리)는 **힘과 지구력**을 상징
- 대서양 횡단 장거리 벌크 운송에 적합한 이름

**항로**: US Gulf (Houston) → Europe (Rotterdam)
- 미국 걸프 → 유럽 주요 무역 루트

---

### 4. AQUARIUS (물병자리)
**참고**: [Trafigura Medium Ammonia Gas Carrier](https://www.marinelink.com/news/shipowners-choosing-ammonia-518509)

- **Trafigura의 중형 암모니아 가스선 프로젝트**
- "Aquarius" (물병자리)는 **혁신과 진보**를 상징
- 암모니아는 **물(H2O)과 질소(N2)**로 구성된 친환경 연료

**항로**: Chile (Valparaiso) → China (Shanghai)
- 태평양 횡단 남미 → 아시아 루트

---

### 5. PHOENIX (불사조)
**참고**: [Hyundai EPS-HD Ammonia Vessels](https://www.marinelink.com/news/shipowners-choosing-ammonia-518509)

- **현대중공업의 EPS-HD (Environmental Performance System - High Definition)**
- "Phoenix" (불사조)는 **재탄생과 부활**을 상징
- 기존 화석연료 시대에서 친환경 시대로의 **전환**을 의미

**항로**: Norway (Oslo) → UAE (Abu Dhabi)
- 유럽 → 중동 암모니아 수송 (케이프타운 경유)

---

## 실제 프로젝트 배경

### Sakigake (魁) - 일본 NEDO
- 2024년 시범 운항 완료
- 세계 최초 암모니아 추진 예인선
- CO2 배출 90% 이상 감소 실증

### NYK Line - 중형 암모니아 가스선
- 2026-2027년 건조 예정
- 일본 탄소 중립 목표 달성 핵심 프로젝트

### BHP/COSCO - 암모니아 듀얼 퓨얼 벌크선
- 2025년 7월 계약 체결
- 철광석 운송에 암모니아 연료 사용

### Trafigura - 중형 가스선
- 글로벌 트레이딩 회사의 친환경 선박 투자
- 암모니아 무역 활성화 기대

### Hyundai EPS-HD - 환경 성능 시스템
- 현대중공업의 차세대 친환경 선박 기술
- 다목적 암모니아 듀얼 퓨얼 선박

---

## 수정된 파일

### 1. `src/simulation_ammonia.py`
- `create_ammonia_fleet()` 함수 수정
- 선박명 리스트 추가 및 docstring 작성
- 실제 프로젝트 참고 사항 명시

### 2. `README.md`
- 선박 구성 섹션 업데이트
- 차세대 암모니아 함대 상세 정보 추가
- 5척 선박명 및 항로, 프로젝트 참고 정보 기재

### 3. `data/bronze/Ammonia_Fleet.csv`
- 암모니아 함대 5척 정보 CSV 생성
- 선박명, MMSI, 항로, 참고 프로젝트, 건조 연도, 엔진 타입

---

## 명명 철학

### 다양성
- **일본어** (Sakigake): 아시아 해운 강국 대표
- **영어** (Horizon, Phoenix): 국제적 범용성
- **별자리** (Taurus, Aquarius): 해양 항해 전통

### 상징성
- **선구자** (Sakigake): 첫걸음
- **지평선** (Horizon): 미래 전망
- **황소** (Taurus): 힘과 지구력
- **물병** (Aquarius): 혁신과 진보
- **불사조** (Phoenix): 재탄생

### 실용성
- 모두 영어 발음 가능 (국제 통신 호환)
- 짧고 기억하기 쉬움 (3-4음절)
- 중복 없는 고유한 이름

---

## 데이터 카탈로그 업데이트 필요

`governance/catalog/데이터_카탈로그.md`에 다음 추가 권장:

### Bronze 레이어
- **데이터셋**: `data/bronze/Ammonia_Fleet.csv`
- **소스**: NEDO, NYK, BHP/COSCO, Trafigura, Hyundai 프로젝트 참고
- **형식**: CSV
- **크기**: 5 rows
- **보존 기간**: 영구

---

## 시뮬레이션 효과

### 전
- 지도에 "AMMONIA-1", "AMMONIA-2" 등 숫자 기반 라벨 표시
- 단조로운 식별자

### 후
- "SAKIGAKE", "HORIZON", "TAURUS" 등 의미 있는 선박명 표시
- 실제 프로젝트와 연결되어 몰입감 향상
- 연구 발표 시 프로페셔널한 인상

---

## 참고 자료

1. [NEDO Green Innovation Fund - Ammonia Tugboat](https://green-innovation.nedo.go.jp/en/article/ammonia-fueled-tugboat/)
2. [Marine Link - Shipowners Choosing Ammonia](https://www.marinelink.com/news/shipowners-choosing-ammonia-518509)
3. [Reuters - BHP COSCO Ammonia Vessels](https://www.reuters.com/sustainability/climate-energy/bhp-inks-charter-contracts-with-cosco-ammonia-dual-fuelled-vessels-2025-07-02/)

---

**작업 완료**: 2026-01-24 22:35 (KST)
**Streamlit**: http://localhost:8501 에서 새 선박명 확인 가능
