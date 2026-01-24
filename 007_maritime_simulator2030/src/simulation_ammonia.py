"""
Ammonia Vessel Simulation
==========================

경로 기반 암모니아 연료 선박 시뮬레이션 (5척)

특징:
- 웨이포인트 기반 항로 계획
- 대권항법 (Great Circle) 경로 추종
- 현실적인 속도 프로파일
- 확률적 신호 블랙아웃 주입
- 풍향/해류 영향 모델링
"""

import numpy as np
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import random
from ais_client import VesselState
from prediction_engine import DeadReckoningEngine


# 실험용 MMSI 범위 (9XX XXX XXX)
AMMONIA_MMSI_BASE = 900000000


@dataclass
class Waypoint:
    """항로 웨이포인트"""
    latitude: float
    longitude: float
    name: str = ""
    arrival_speed_knots: float = 15.0  # 도착 시 목표 속도


@dataclass
class Route:
    """선박 항로"""
    waypoints: List[Waypoint]
    route_name: str = "Unnamed Route"

    def get_total_waypoints(self) -> int:
        return len(self.waypoints)


@dataclass
class AmmoniaVesselConfig:
    """암모니아 선박 설정"""

    vessel_id: int  # 1-5
    vessel_name: str
    route: Route

    # 선박 제원
    length_m: float = 230.0
    width_m: float = 36.0
    draught_m: float = 12.5

    # 성능 특성
    max_speed_knots: float = 19.5
    cruise_speed_knots: float = 16.0
    min_speed_knots: float = 10.0

    # 통신 특성
    signal_blackout_probability: float = 0.05  # 5% 확률로 신호 손실
    blackout_min_duration_sec: int = 60  # 최소 블랙아웃 시간
    blackout_max_duration_sec: int = 600  # 최대 블랙아웃 시간

    # 환경 민감도
    wind_sensitivity: float = 0.03  # 바람 영향 계수
    current_sensitivity: float = 0.8  # 해류 영향 계수


class AmmoniaVesselSimulator:
    """
    암모니아 선박 시뮬레이터

    웨이포인트 기반 경로를 따라 선박을 시뮬레이션합니다.
    """

    def __init__(self, config: AmmoniaVesselConfig, update_interval_sec: int = 10):
        """
        Args:
            config: 선박 설정
            update_interval_sec: AIS 업데이트 주기 (초)
        """
        self.config = config
        self.update_interval = update_interval_sec

        # MMSI 생성 (실험용 범위)
        self.mmsi = str(AMMONIA_MMSI_BASE + config.vessel_id)

        # 현재 상태
        self.current_waypoint_idx = 0
        self.vessel_state: Optional[VesselState] = None

        # 시뮬레이션 시간
        self.simulation_time = datetime.utcnow()

        # 블랙아웃 상태
        self.in_blackout = False
        self.blackout_start_time: Optional[datetime] = None
        self.blackout_duration_sec: int = 0

        # Dead Reckoning 엔진
        self.dr_engine = DeadReckoningEngine()

        # 초기 위치를 첫 웨이포인트로 설정
        self._initialize_position()

    def _initialize_position(self):
        """선박을 첫 웨이포인트 위치에 배치"""

        if self.config.route.get_total_waypoints() == 0:
            raise ValueError("경로에 웨이포인트가 없습니다.")

        start_waypoint = self.config.route.waypoints[0]

        # 다음 웨이포인트 방향 계산
        if self.config.route.get_total_waypoints() > 1:
            next_waypoint = self.config.route.waypoints[1]
            initial_course = self.dr_engine.calculate_bearing(
                start_waypoint.latitude, start_waypoint.longitude,
                next_waypoint.latitude, next_waypoint.longitude
            )
        else:
            initial_course = 0.0  # 북쪽

        # 초기 VesselState 생성
        self.vessel_state = VesselState(
            mmsi=self.mmsi,
            vessel_name=self.config.vessel_name,
            vessel_type="AMMONIA",
            latitude=start_waypoint.latitude,
            longitude=start_waypoint.longitude,
            course=initial_course,
            speed=self.config.cruise_speed_knots,
            heading=initial_course,
            timestamp=self.simulation_time,
            length=self.config.length_m,
            width=self.config.width_m,
            draught=self.config.draught_m,
            destination=self.config.route.route_name,
            is_simulated=True,
            data_source="SIMULATED_AMMONIA"
        )

        self.current_waypoint_idx = 1  # 다음 목표는 두 번째 웨이포인트

    def step(
        self,
        delta_time_sec: Optional[int] = None,
        wind_speed_knots: Optional[float] = None,
        wind_direction_deg: Optional[float] = None,
        current_speed_knots: Optional[float] = None,
        current_direction_deg: Optional[float] = None
    ) -> VesselState:
        """
        시뮬레이션을 한 스텝 진행합니다.

        Args:
            delta_time_sec: 시간 증분 (None이면 update_interval 사용)
            wind_speed_knots: 풍속 (노트)
            wind_direction_deg: 풍향 (도)
            current_speed_knots: 해류 속도 (노트)
            current_direction_deg: 해류 방향 (도)

        Returns:
            업데이트된 VesselState
        """

        dt = delta_time_sec or self.update_interval

        # 시뮬레이션 시간 진행
        self.simulation_time += timedelta(seconds=dt)

        # ===================================================================
        # 1. 블랙아웃 상태 확인 및 업데이트
        # ===================================================================

        if self.in_blackout:
            # 블랙아웃 지속 시간 확인
            elapsed = (self.simulation_time - self.blackout_start_time).total_seconds()

            if elapsed >= self.blackout_duration_sec:
                # 블랙아웃 종료
                self.in_blackout = False
                self.blackout_start_time = None
                # 실제 위치로 복귀 (신호 복구)

        else:
            # 블랙아웃 발생 확률 체크
            if random.random() < self.config.signal_blackout_probability:
                self.in_blackout = True
                self.blackout_start_time = self.simulation_time
                self.blackout_duration_sec = random.randint(
                    self.config.blackout_min_duration_sec,
                    self.config.blackout_max_duration_sec
                )

        # ===================================================================
        # 2. 현재 목표 웨이포인트 확인
        # ===================================================================

        if self.current_waypoint_idx >= self.config.route.get_total_waypoints():
            # 모든 웨이포인트 통과 → 경로 순환
            self.current_waypoint_idx = 0

        target_waypoint = self.config.route.waypoints[self.current_waypoint_idx]

        # ===================================================================
        # 3. 목표 방향 및 거리 계산
        # ===================================================================

        target_course = self.dr_engine.calculate_bearing(
            self.vessel_state.latitude,
            self.vessel_state.longitude,
            target_waypoint.latitude,
            target_waypoint.longitude
        )

        distance_to_target = self.dr_engine.calculate_distance_haversine(
            self.vessel_state.latitude,
            self.vessel_state.longitude,
            target_waypoint.latitude,
            target_waypoint.longitude
        )

        # ===================================================================
        # 4. 속도 프로파일 계산 (거리 기반 감속)
        # ===================================================================

        # 웨이포인트 접근 시 감속 (마지막 5km)
        deceleration_distance = 5000.0  # 5km

        if distance_to_target < deceleration_distance:
            # 선형 감속
            speed_factor = distance_to_target / deceleration_distance
            target_speed = (
                self.config.min_speed_knots +
                (target_waypoint.arrival_speed_knots - self.config.min_speed_knots) * speed_factor
            )
        else:
            target_speed = self.config.cruise_speed_knots

        # 현재 속도를 목표 속도로 점진적 조정 (가속도 제한)
        max_acceleration_knots_per_sec = 0.05  # 0.05 knots/sec
        speed_diff = target_speed - self.vessel_state.speed
        max_speed_change = max_acceleration_knots_per_sec * dt

        if abs(speed_diff) > max_speed_change:
            self.vessel_state.speed += np.sign(speed_diff) * max_speed_change
        else:
            self.vessel_state.speed = target_speed

        # ===================================================================
        # 5. 침로 조정 (선회율 제한)
        # ===================================================================

        max_turn_rate_deg_per_sec = 2.0  # 2도/초

        course_diff = (target_course - self.vessel_state.course + 180) % 360 - 180
        max_course_change = max_turn_rate_deg_per_sec * dt

        if abs(course_diff) > max_course_change:
            self.vessel_state.course += np.sign(course_diff) * max_course_change
        else:
            self.vessel_state.course = target_course

        # 침로 정규화 (0-360)
        self.vessel_state.course = self.vessel_state.course % 360
        self.vessel_state.heading = self.vessel_state.course

        # ===================================================================
        # 6. Dead Reckoning으로 새 위치 계산
        # ===================================================================

        prediction = self.dr_engine.predict_position(
            last_latitude=self.vessel_state.latitude,
            last_longitude=self.vessel_state.longitude,
            course_deg=self.vessel_state.course,
            speed_knots=self.vessel_state.speed,
            time_elapsed_seconds=dt,
            wind_speed_knots=wind_speed_knots,
            wind_direction_deg=wind_direction_deg,
            current_speed_knots=current_speed_knots,
            current_direction_deg=current_direction_deg
        )

        # 위치 업데이트
        self.vessel_state.latitude = prediction.predicted_latitude
        self.vessel_state.longitude = prediction.predicted_longitude
        self.vessel_state.timestamp = self.simulation_time

        # ===================================================================
        # 7. 웨이포인트 도달 확인
        # ===================================================================

        # 웨이포인트 도달 기준: 500m 이내
        waypoint_arrival_threshold = 500.0

        if distance_to_target < waypoint_arrival_threshold:
            # 다음 웨이포인트로 전환
            self.current_waypoint_idx += 1

        # ===================================================================
        # 8. 블랙아웃 중이면 상태 반환하지 않음 (선택)
        # ===================================================================

        # 블랙아웃 시뮬레이션: 실제로는 상태를 반환하지 않거나
        # 마지막 알려진 위치를 반환할 수 있음
        # 여기서는 내부적으로는 계속 업데이트하되, 플래그만 설정

        return self.vessel_state

    def get_current_state(self) -> VesselState:
        """현재 선박 상태 반환"""
        return self.vessel_state

    def is_in_blackout(self) -> bool:
        """현재 블랙아웃 상태인지 확인"""
        return self.in_blackout

    def get_blackout_info(self) -> Dict:
        """블랙아웃 정보 반환"""
        if self.in_blackout:
            elapsed = (self.simulation_time - self.blackout_start_time).total_seconds()
            remaining = self.blackout_duration_sec - elapsed
            return {
                'in_blackout': True,
                'elapsed_sec': elapsed,
                'remaining_sec': max(0, remaining),
                'total_duration_sec': self.blackout_duration_sec
            }
        else:
            return {'in_blackout': False}


# ============================================================================
# 사전 정의된 항로
# ============================================================================

def create_sample_routes() -> Dict[str, Route]:
    """샘플 항로 생성 (주요 암모니아 무역 항로)"""

    routes = {}

    # 항로 1: 중동 → 동북아시아 (UAE → 한국)
    routes['middle_east_to_korea'] = Route(
        route_name="UAE to Korea",
        waypoints=[
            Waypoint(24.5, 54.4, "Abu Dhabi", 15.0),
            Waypoint(22.3, 59.5, "Oman Sea", 17.0),
            Waypoint(18.0, 68.0, "Arabian Sea", 17.0),
            Waypoint(8.0, 78.0, "Indian Ocean", 17.0),
            Waypoint(1.3, 95.0, "Malacca Strait North", 12.0),
            Waypoint(6.0, 102.0, "South China Sea", 17.0),
            Waypoint(22.0, 118.0, "Taiwan Strait", 15.0),
            Waypoint(33.0, 126.0, "Yellow Sea", 15.0),
            Waypoint(35.1, 129.0, "Busan", 10.0)
        ]
    )

    # 항로 2: 호주 → 일본 (북서부 호주 → 도쿄)
    routes['australia_to_japan'] = Route(
        route_name="Australia to Japan",
        waypoints=[
            Waypoint(-20.0, 118.0, "Western Australia", 15.0),
            Waypoint(-10.0, 125.0, "Timor Sea", 17.0),
            Waypoint(0.0, 130.0, "Equator Crossing", 17.0),
            Waypoint(10.0, 135.0, "Philippine Sea", 17.0),
            Waypoint(25.0, 138.0, "Pacific Ocean", 17.0),
            Waypoint(35.0, 140.0, "Tokyo Bay", 12.0)
        ]
    )

    # 항로 3: 북미 → 유럽 (미국 걸프 → 네덜란드)
    routes['us_gulf_to_europe'] = Route(
        route_name="US Gulf to Rotterdam",
        waypoints=[
            Waypoint(29.3, -94.8, "Houston", 15.0),
            Waypoint(27.0, -90.0, "Gulf of Mexico", 17.0),
            Waypoint(24.0, -82.0, "Florida Strait", 15.0),
            Waypoint(26.0, -78.0, "Atlantic Ocean", 17.0),
            Waypoint(32.0, -64.0, "Mid Atlantic", 17.0),
            Waypoint(40.0, -40.0, "North Atlantic", 17.0),
            Waypoint(48.0, -15.0, "Approach Europe", 17.0),
            Waypoint(51.9, 4.1, "Rotterdam", 10.0)
        ]
    )

    # 항로 4: 남미 → 아시아 (칠레 → 중국)
    routes['chile_to_china'] = Route(
        route_name="Chile to China",
        waypoints=[
            Waypoint(-33.0, -71.6, "Valparaiso", 15.0),
            Waypoint(-30.0, -85.0, "Pacific West", 17.0),
            Waypoint(-20.0, -110.0, "South Pacific", 17.0),
            Waypoint(-10.0, -140.0, "Equator Approach", 17.0),
            Waypoint(0.0, -170.0, "Equator Crossing", 17.0),
            Waypoint(10.0, 160.0, "North Pacific", 17.0),
            Waypoint(20.0, 140.0, "Philippine Sea", 17.0),
            Waypoint(30.0, 125.0, "East China Sea", 15.0),
            Waypoint(31.2, 121.5, "Shanghai", 10.0)
        ]
    )

    # 항로 5: 북유럽 → 중동 (노르웨이 → UAE)
    routes['norway_to_uae'] = Route(
        route_name="Norway to UAE",
        waypoints=[
            Waypoint(59.9, 10.7, "Oslo Fjord", 15.0),
            Waypoint(58.0, 7.0, "North Sea", 17.0),
            Waypoint(51.0, 2.0, "English Channel", 15.0),
            Waypoint(48.0, -5.0, "Bay of Biscay", 17.0),
            Waypoint(36.0, -9.0, "Portugal Coast", 17.0),
            Waypoint(28.0, -15.0, "Northwest Africa", 17.0),
            Waypoint(15.0, -20.0, "West Africa", 17.0),
            Waypoint(0.0, -10.0, "Equator West", 17.0),
            Waypoint(-20.0, 10.0, "South Atlantic", 17.0),
            Waypoint(-35.0, 20.0, "Cape of Good Hope", 15.0),
            Waypoint(-30.0, 35.0, "Indian Ocean", 17.0),
            Waypoint(-10.0, 50.0, "Central Indian Ocean", 17.0),
            Waypoint(10.0, 60.0, "Arabian Sea", 17.0),
            Waypoint(24.5, 54.4, "Abu Dhabi", 10.0)
        ]
    )

    return routes


def create_ammonia_fleet() -> List[AmmoniaVesselSimulator]:
    """
    암모니아 선박 5척 생성

    선박명은 실제 암모니아 프로젝트와 일본 명명 전통을 참고:
    - Sakigake (魁): 일본 최초 암모니아 예인선 (NEDO 프로젝트)
    - Horizon: NYK의 차세대 암모니아 가스선 프로젝트
    - Taurus: BHP/COSCO 암모니아 듀얼 퓨얼 벌크선 (황소자리)
    - Aquarius: Trafigura 중형 암모니아 가스선 (물병자리)
    - Phoenix: 현대 EPS-HD 암모니아 선박 프로젝트 (불사조)
    """

    routes = create_sample_routes()
    route_list = list(routes.values())

    # 차세대 암모니아 선박 이름 (2025-2030년 실제 프로젝트 참고)
    ammonia_vessel_names = [
        "SAKIGAKE",      # 선구자 (일본 NEDO 프로젝트)
        "HORIZON",       # 지평선 (NYK 프로젝트)
        "TAURUS",        # 황소자리 (BHP/COSCO)
        "AQUARIUS",      # 물병자리 (Trafigura)
        "PHOENIX"        # 불사조 (현대 EPS-HD)
    ]

    fleet = []

    for i in range(5):
        config = AmmoniaVesselConfig(
            vessel_id=i + 1,
            vessel_name=ammonia_vessel_names[i],
            route=route_list[i],
            signal_blackout_probability=0.02 + i * 0.01,  # 2-6% 확률
        )

        simulator = AmmoniaVesselSimulator(config, update_interval_sec=10)
        fleet.append(simulator)

    return fleet


# ============================================================================
# 사용 예시
# ============================================================================

if __name__ == "__main__":

    import time

    print("=" * 70)
    print("Ammonia Vessel Simulation - 테스트")
    print("=" * 70)

    # 암모니아 선박 1척 생성
    routes = create_sample_routes()
    test_route = routes['middle_east_to_korea']

    config = AmmoniaVesselConfig(
        vessel_id=1,
        vessel_name="AMMONIA-TEST",
        route=test_route,
        signal_blackout_probability=0.1  # 10% 블랙아웃 확률 (테스트용)
    )

    simulator = AmmoniaVesselSimulator(config, update_interval_sec=60)

    print(f"\n선박: {config.vessel_name}")
    print(f"항로: {test_route.route_name}")
    print(f"총 웨이포인트: {test_route.get_total_waypoints()}개")
    print(f"\n시뮬레이션 시작...\n")

    # 10 스텝 시뮬레이션
    for step in range(10):
        # 환경 조건 (랜덤)
        wind_speed = random.uniform(5, 25)  # 5-25 knots
        wind_direction = random.uniform(0, 360)
        current_speed = random.uniform(0.5, 2.5)
        current_direction = random.uniform(0, 360)

        # 시뮬레이션 스텝
        state = simulator.step(
            delta_time_sec=60,  # 1분
            wind_speed_knots=wind_speed,
            wind_direction_deg=wind_direction,
            current_speed_knots=current_speed,
            current_direction_deg=current_direction
        )

        # 블랙아웃 정보
        blackout_info = simulator.get_blackout_info()

        # 출력
        print(f"[스텝 {step+1}] 시간: {state.timestamp.strftime('%H:%M:%S')}")
        print(f"  위치: {state.latitude:.4f}°N, {state.longitude:.4f}°E")
        print(f"  속도: {state.speed:.1f} knots, 침로: {state.course:.1f}°")

        if blackout_info['in_blackout']:
            print(f"  ⚠️ 블랙아웃 중! (남은 시간: {blackout_info['remaining_sec']:.0f}초)")
        else:
            print(f"  ✓ 신호 정상")

        print(f"  환경: 풍속 {wind_speed:.1f}kts, 해류 {current_speed:.1f}kts")
        print()

        time.sleep(0.5)  # 출력 딜레이

    print("=" * 70)
    print("시뮬레이션 완료")
    print("=" * 70)

    # 전체 함대 생성 테스트
    print("\n[함대 생성 테스트]")
    fleet = create_ammonia_fleet()
    print(f"암모니아 선박 {len(fleet)}척 생성 완료:")
    for vessel_sim in fleet:
        state = vessel_sim.get_current_state()
        print(f"  - {state.vessel_name} ({state.mmsi}): {state.destination}")
