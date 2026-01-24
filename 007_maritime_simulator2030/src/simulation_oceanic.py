"""
Oceanic Ship Prediction Module
===============================

대양 한가운데 있는 자율선박의 예상 위치 시뮬레이션
- Prism Courage (LNG Tanker): US Gulf Coast → Pacific → Korea/Japan
- HMM Algeciras (ULCV): Asia → Suez Canal → Europe

AIS 실시간 데이터가 없을 때 Great Circle 항법으로 예상 위치 계산
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
import math


@dataclass
class Waypoint:
    """항로 웨이포인트"""
    latitude: float
    longitude: float
    name: str


@dataclass
class OceanicVesselConfig:
    """대양 선박 설정"""
    vessel_name: str
    mmsi: str
    imo: str
    vessel_type: str
    route_name: str
    waypoints: List[Waypoint]
    speed_knots: float  # 평균 속도
    current_waypoint_index: int = 0
    start_time: datetime = None


class GreatCircleNavigator:
    """Great Circle 항법 엔진"""

    EARTH_RADIUS_KM = 6371.0
    NAUTICAL_MILES_PER_KM = 0.539957

    @staticmethod
    def calculate_distance_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """두 좌표 사이의 Great Circle 거리 계산 (해리)"""

        # 라디안 변환
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        # Haversine 공식
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

        distance_km = GreatCircleNavigator.EARTH_RADIUS_KM * c
        distance_nm = distance_km * GreatCircleNavigator.NAUTICAL_MILES_PER_KM

        return distance_nm

    @staticmethod
    def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """두 좌표 사이의 초기 방위각 계산 (도)"""

        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        dlon = lon2_rad - lon1_rad

        y = math.sin(dlon) * math.cos(lat2_rad)
        x = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon)

        bearing_rad = math.atan2(y, x)
        bearing_deg = math.degrees(bearing_rad)

        # 0-360 범위로 정규화
        bearing_deg = (bearing_deg + 360) % 360

        return bearing_deg

    @staticmethod
    def calculate_intermediate_point(
        lat1: float, lon1: float,
        lat2: float, lon2: float,
        fraction: float
    ) -> Tuple[float, float]:
        """두 좌표 사이의 중간 지점 계산

        Args:
            fraction: 0.0 (시작점) ~ 1.0 (종료점)

        Returns:
            (latitude, longitude)
        """

        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        # Great Circle 각거리
        distance_rad = math.acos(
            math.sin(lat1_rad) * math.sin(lat2_rad) +
            math.cos(lat1_rad) * math.cos(lat2_rad) * math.cos(lon2_rad - lon1_rad)
        )

        a = math.sin((1 - fraction) * distance_rad) / math.sin(distance_rad)
        b = math.sin(fraction * distance_rad) / math.sin(distance_rad)

        x = a * math.cos(lat1_rad) * math.cos(lon1_rad) + b * math.cos(lat2_rad) * math.cos(lon2_rad)
        y = a * math.cos(lat1_rad) * math.sin(lon1_rad) + b * math.cos(lat2_rad) * math.sin(lon2_rad)
        z = a * math.sin(lat1_rad) + b * math.sin(lat2_rad)

        lat_rad = math.atan2(z, math.sqrt(x**2 + y**2))
        lon_rad = math.atan2(y, x)

        return math.degrees(lat_rad), math.degrees(lon_rad)


class OceanicVesselSimulator:
    """대양 선박 시뮬레이터"""

    def __init__(self, config: OceanicVesselConfig):
        self.config = config
        self.navigator = GreatCircleNavigator()

        if self.config.start_time is None:
            self.config.start_time = datetime.utcnow()

        self.current_time = self.config.start_time
        self.current_position: Optional[Tuple[float, float]] = None
        self.current_bearing: float = 0.0

        # 초기 위치 계산
        self._initialize_position()

    def _initialize_position(self):
        """초기 위치 설정"""
        if len(self.config.waypoints) >= 2:
            wp1 = self.config.waypoints[0]
            self.current_position = (wp1.latitude, wp1.longitude)
            self.current_bearing = self.navigator.calculate_bearing(
                wp1.latitude, wp1.longitude,
                self.config.waypoints[1].latitude,
                self.config.waypoints[1].longitude
            )

    def get_predicted_position(self, elapsed_hours: float) -> Tuple[float, float, float, str]:
        """경과 시간 후 예상 위치 계산

        Args:
            elapsed_hours: 시작 시간으로부터 경과한 시간 (시간)

        Returns:
            (latitude, longitude, bearing, current_leg_name)
        """

        # 이동 거리 계산 (해리)
        distance_traveled_nm = self.config.speed_knots * elapsed_hours

        # 현재 어느 구간에 있는지 찾기
        cumulative_distance = 0.0

        for i in range(len(self.config.waypoints) - 1):
            wp1 = self.config.waypoints[i]
            wp2 = self.config.waypoints[i + 1]

            leg_distance = self.navigator.calculate_distance_nm(
                wp1.latitude, wp1.longitude,
                wp2.latitude, wp2.longitude
            )

            if cumulative_distance + leg_distance >= distance_traveled_nm:
                # 이 구간에 있음
                distance_in_leg = distance_traveled_nm - cumulative_distance
                fraction = distance_in_leg / leg_distance if leg_distance > 0 else 0

                lat, lon = self.navigator.calculate_intermediate_point(
                    wp1.latitude, wp1.longitude,
                    wp2.latitude, wp2.longitude,
                    fraction
                )

                bearing = self.navigator.calculate_bearing(
                    wp1.latitude, wp1.longitude,
                    wp2.latitude, wp2.longitude
                )

                leg_name = f"{wp1.name} → {wp2.name}"

                return lat, lon, bearing, leg_name

            cumulative_distance += leg_distance

        # 마지막 웨이포인트 도달
        last_wp = self.config.waypoints[-1]
        return last_wp.latitude, last_wp.longitude, 0.0, f"Arrived at {last_wp.name}"


# ============================================================================
# 실제 선박 항로 정의
# ============================================================================

def create_prism_courage_route() -> OceanicVesselConfig:
    """Prism Courage (LNG Tanker) 예상 항로

    US Gulf Coast (Sabine Pass) → Panama Canal → Pacific → Korea (Pyeongtaek)
    평균 속도: 19 knots
    """

    waypoints = [
        Waypoint(29.73, -93.87, "Sabine Pass (TX, USA)"),           # 텍사스 LNG 터미널
        Waypoint(9.38, -79.92, "Panama Canal (Atlantic)"),          # 파나마 운하 입구
        Waypoint(8.97, -79.57, "Panama Canal (Pacific)"),           # 파나마 운하 출구
        Waypoint(0.0, -140.0, "Pacific Ocean (Equator)"),           # 태평양 적도
        Waypoint(20.0, 160.0, "Pacific Ocean (North)"),             # 북태평양
        Waypoint(36.99, 126.82, "Pyeongtaek (Korea)")               # 평택항
    ]

    # 2026-01-10 출발 가정 (14일 경과)
    start_time = datetime(2026, 1, 10, 0, 0, 0)

    return OceanicVesselConfig(
        vessel_name="Prism Courage",
        mmsi="352986205",
        imo="9888481",
        vessel_type="LNG Tanker",
        route_name="US Gulf → Korea",
        waypoints=waypoints,
        speed_knots=19.0,
        start_time=start_time
    )


def create_hmm_algeciras_route() -> OceanicVesselConfig:
    """HMM Algeciras (24000 TEU ULCV) 예상 항로

    Busan (Korea) → Suez Canal → Rotterdam (Europe)
    평균 속도: 22 knots
    """

    waypoints = [
        Waypoint(35.10, 129.04, "Busan (Korea)"),                   # 부산항
        Waypoint(1.27, 103.85, "Singapore Strait"),                 # 싱가포르 해협
        Waypoint(6.0, 80.0, "Indian Ocean (Sri Lanka)"),            # 인도양
        Waypoint(12.6, 43.3, "Bab el-Mandeb Strait"),               # 바브엘만데브 해협
        Waypoint(29.92, 32.56, "Suez Canal (South)"),               # 수에즈 운하 입구
        Waypoint(31.26, 32.31, "Suez Canal (North)"),               # 수에즈 운하 출구
        Waypoint(35.0, 25.0, "Mediterranean Sea (Greece)"),         # 지중해
        Waypoint(51.95, 4.14, "Rotterdam (Netherlands)")            # 로테르담항
    ]

    # 2026-01-05 출발 가정 (19일 경과)
    start_time = datetime(2026, 1, 5, 0, 0, 0)

    return OceanicVesselConfig(
        vessel_name="HMM Algeciras",
        mmsi="440326000",
        imo="9863297",
        vessel_type="Container Ship",
        route_name="Asia → Europe",
        waypoints=waypoints,
        speed_knots=22.0,
        start_time=start_time
    )


def get_oceanic_ships_predicted_positions() -> List[dict]:
    """대양 선박들의 현재 예상 위치 반환

    Returns:
        List of dicts with keys: vessel_name, mmsi, latitude, longitude, bearing, leg_name, is_predicted
    """

    prism = create_prism_courage_route()
    hmm = create_hmm_algeciras_route()

    sim_prism = OceanicVesselSimulator(prism)
    sim_hmm = OceanicVesselSimulator(hmm)

    # 현재 시간 기준 경과 시간 계산
    now = datetime.utcnow()

    prism_elapsed_hours = (now - prism.start_time).total_seconds() / 3600
    hmm_elapsed_hours = (now - hmm.start_time).total_seconds() / 3600

    # 예상 위치 계산
    prism_lat, prism_lon, prism_bearing, prism_leg = sim_prism.get_predicted_position(prism_elapsed_hours)
    hmm_lat, hmm_lon, hmm_bearing, hmm_leg = sim_hmm.get_predicted_position(hmm_elapsed_hours)

    return [
        {
            'vessel_name': prism.vessel_name,
            'mmsi': prism.mmsi,
            'imo': prism.imo,
            'vessel_type': prism.vessel_type,
            'latitude': prism_lat,
            'longitude': prism_lon,
            'speed': prism.speed_knots,
            'course': prism_bearing,
            'current_leg': prism_leg,
            'is_predicted': True,
            'data_source': 'PREDICTED'
        },
        {
            'vessel_name': hmm.vessel_name,
            'mmsi': hmm.mmsi,
            'imo': hmm.imo,
            'vessel_type': hmm.vessel_type,
            'latitude': hmm_lat,
            'longitude': hmm_lon,
            'speed': hmm.speed_knots,
            'course': hmm_bearing,
            'current_leg': hmm_leg,
            'is_predicted': True,
            'data_source': 'PREDICTED'
        }
    ]


if __name__ == "__main__":
    # 테스트
    print("=== 대양 선박 예상 위치 테스트 ===\n")

    positions = get_oceanic_ships_predicted_positions()

    for pos in positions:
        print(f"선박: {pos['vessel_name']} (MMSI: {pos['mmsi']})")
        print(f"타입: {pos['vessel_type']}")
        print(f"예상 위치: {pos['latitude']:.4f}°N, {pos['longitude']:.4f}°E")
        print(f"속도: {pos['speed']:.1f} knots")
        print(f"침로: {pos['course']:.1f}°")
        print(f"현재 구간: {pos['current_leg']}")
        print(f"데이터 소스: {pos['data_source']}")
        print()
