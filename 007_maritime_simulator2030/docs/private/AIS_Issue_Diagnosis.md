# AIS Q-Max 선박 추적 문제 진단

**날짜**: 2026-01-24
**문제**: MMSI 번호는 정확하게 찾았으나 Q-Max 선박이 실시간으로 추적되지 않음

---

## 수정 사항

### 1. AIS 클라이언트 코드 수정 (src/ais_client.py)

**변경 전** (클라이언트 측 필터링):
```python
subscribe_message = {
    "APIKey": self.api_key,
    "BoundingBoxes": [[[-90, -180], [90, 180]]],
    "FilterMessageTypes": ["PositionReport", "ShipStaticData"]
}
# 이후 클라이언트에서 MMSI 필터링
```

**변경 후** (서버 측 필터링):
```python
subscribe_message = {
    "APIKey": self.api_key,
    "BoundingBoxes": [[[-90, -180], [90, 180]]],
    "FilterMessageTypes": ["PositionReport", "ShipStaticData"],
    "FiltersShipMMSI": list(self.mmsi_filter)  # 서버 측 MMSI 필터
}
```

---

## 테스트 결과

### 테스트 1: MMSI 필터링 활성화 (60초)
- **수신 메시지**: 0개
- **Q-Max 발견**: 0척
- **결론**: 서버 측 MMSI 필터링 시 아무 메시지도 수신되지 않음

### 테스트 2: MMSI 필터 제거 (실행 예정)
- MMSI 필터 없이 일반 선박 메시지가 수신되는지 확인
- 만약 수신된다면 → Q-Max 선박이 현재 AIS 송출 안함
- 만약 수신 안된다면 → API 키 또는 연결 문제

---

## 가능한 원인

### 1. Q-Max 선박이 현재 AIS를 송출하지 않음 (가능성: 높음)
**증거**:
- 웹 검색으로 MMSI는 확인됨 (MarineTraffic, VesselFinder 등)
- 하지만 실시간 AIS 스트림에서는 감지 안됨

**이유**:
- 선박이 항만에 정박 중 (AIS 송출 중지 또는 감소)
- 선박이 정비/수리 중
- 일시적인 통신 블랙아웃 지역

**확인 방법**:
- MarineTraffic에서 "Last Position Received" 날짜 확인
- 최근 위치 업데이트가 며칠 전이면 → 현재 AIS 송출 안함

### 2. AISStream 무료 플랜의 제한 (가능성: 중간)
**증거**:
- MMSI 필터 사용 시 아무 메시지도 수신 안됨

**가능성**:
- 무료 플랜이 특정 MMSI 필터링을 지원하지 않을 수 있음
- 또는 Marshall Islands 국적 선박(MMSI 538xxx)에 제한이 있을 수 있음

### 3. MMSI가 최근에 변경됨 (가능성: 낮음)
**증거**:
- 웹사이트에서는 확인된 MMSI
- 하지만 MMSI는 거의 변경되지 않음

---

## 해결 방안

### 즉시 실행 가능

#### 방안 1: 실제 Q-Max 위치 확인
MarineTraffic 또는 VesselFinder에서 Q-Max 선박 14척의 현재 상태 확인:
- Last Position Received가 언제인지
- 현재 운항 중인지, 항만에 정박 중인지

#### 방안 2: 시뮬레이션 모드로 전환
Q-Max 선박이 현재 AIS를 송출하지 않는다면, 시뮬레이션 데이터 생성:
- Q-Max의 전형적인 항로: Qatar (Ras Laffan) → Korea/Japan → Qatar
- 예상 속도: 19-20 knots
- 항로: 페르시아만 → 인도양 → 말라카 해협 → 동중국해

**구현 예시**:
```python
def create_qmax_simulated_fleet():
    """실제 Q-Max 항로 기반 시뮬레이션"""
    routes = [
        # Ras Laffan (Qatar) → Pyeongtaek (Korea)
        [(25.91, 51.55), (22.0, 60.0), (1.5, 103.8), (36.0, 126.8)],
        # Ras Laffan → Tokyo Bay
        [(25.91, 51.55), (20.0, 65.0), (1.0, 105.0), (35.4, 139.8)],
        ...
    ]
```

#### 방안 3: LNG 선박 타입 필터링으로 복귀
이전에 작동했던 선박 타입 필터링 (AIS Type 80-89) 사용:
- Q-Max는 아니지만 다른 LNG 탱커 추적
- 실시간 AIS 데이터는 받을 수 있음

---

## 권장 조치

### 단기 (즉시):
1. **Q-Max 현재 상태 웹 확인**: MarineTraffic에서 14척 모두 Last Position Received 날짜 확인
2. **MMSI 필터 제거 테스트**: 일반 선박 메시지라도 수신되는지 확인

### 중기 (1-2일):
1. **시뮬레이션 모드 구현**: Q-Max 실제 항로 기반 시뮬레이션 데이터 생성
2. **하이브리드 모드**: 실시간 AIS(일반 LNG 탱커) + 시뮬레이션(Q-Max)

### 장기 (1주일):
1. **AISStream 유료 플랜 검토**: 더 나은 MMSI 필터링 지원 여부 확인
2. **대체 AIS 데이터 소스**: MarineTraffic API 또는 VesselFinder API 고려

---

## 다음 단계

**즉시 실행**:
1. MMSI 필터 제거 후 일반 선박 메시지 수신 확인
2. 웹에서 Q-Max 14척의 Last Position Received 확인

**결과에 따른 조치**:
- 만약 일반 메시지 수신 O + Q-Max Last Position이 며칠 전 → 시뮬레이션 모드 전환
- 만약 일반 메시지 수신 X → API 키 또는 연결 문제 해결

---

**작성자**: Claude Sonnet 4.5
**문서 버전**: 1.0
**최종 수정**: 2026-01-24 22:37 (KST)
