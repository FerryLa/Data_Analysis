"""
SMR-Powered Vessel Simulation
==============================

소형 모듈 원자로(SMR) 추진 선박 시뮬레이션 (1척)

특징:
- 통로(corridor) 제약 기반 항해
- 지오펜스(Geo-fence) 경계 강제
- 원자력 안전 규정 준수 구역 모니터링
- 항로 이탈 이벤트 로깅
- 고정밀 위치 추적
"""

import numpy as np
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from shapely.geometry import Point, Polygon, LineString
from shapely.ops import nearest_points
import json

from ais_client import VesselState
from prediction_engine import DeadReckoningEngine


# 실험용 MMSI (SMR 선박)
SMR_MMSI = "999999999"


@dataclass
class GeofenceZone:
    """지오펜스 구역 정의"""

    zone_id: str
    zone_name: str
    zone_type: str  # 'ALLOWED', 'RESTRICTED', 'PROHIBITED'

    # 폴리곤 경계 (위도, 경도 좌표 리스트)
    boundary_coords: List[Tuple[float, float]]

    # 규정
    max_speed_knots: Optional[float] = None  # 최대 허용 속도
    mandatory_reporting: bool = False  # 필수 보고 구역

    def to_polygon(self) -> Polygon:
        """Shapely Polygon 객체로 변환"""
        return Polygon(self.boundary_coords)

    def contains_point(self, latitude: float, longitude: float) -> bool:
        """점이 구역 내에 있는지 확인"""
        point = Point(longitude, latitude)  # Shapely는 (lon, lat) 순서
        polygon = self.to_polygon()
        return polygon.contains(point)

    def distance_to_boundary(self, latitude: float, longitude: float) -> float:
        """점에서 경계까지의 최단 거리 (미터)"""
        point = Point(longitude, latitude)
        polygon = self.to_polygon()

        # 경계까지의 거리 계산
        boundary = polygon.boundary
        nearest = nearest_points(point, boundary)[1]

        # Haversine 거리 계산
        from prediction_engine import DeadReckoningEngine
        dr = DeadReckoningEngine()

        distance_m = dr.calculate_distance_haversine(
            latitude, longitude,
            nearest.y, nearest.x
        )

        return distance_m


@dataclass
class Corridor:
    """항해 통로 정의"""

    corridor_id: str
    corridor_name: str

    # 중심선 (위도, 경도 좌표 리스트)
    centerline_coords: List[Tuple[float, float]]

    # 통로 폭 (미터)
    width_m: float = 10000.0  # 기본 10km 폭

    # 속도 제한
    max_speed_knots: float = 20.0

    def to_linestring(self) -> LineString:
        """Shapely LineString 객체로 변환"""
        # (경도, 위도) 순서로 변환
        coords_lon_lat = [(lon, lat) for lat, lon in self.centerline_coords]
        return LineString(coords_lon_lat)

    def distance_from_centerline(self, latitude: float, longitude: float) -> float:
        """점에서 중심선까지의 거리 (미터)"""
        point = Point(longitude, latitude)
        centerline = self.to_linestring()

        # 중심선에서 가장 가까운 점 찾기
        nearest = nearest_points(point, centerline)[1]

        # Haversine 거리 계산
        from prediction_engine import DeadReckoningEngine
        dr = DeadReckoningEngine()

        distance_m = dr.calculate_distance_haversine(
            latitude, longitude,
            nearest.y, nearest.x
        )

        return distance_m

    def is_within_corridor(self, latitude: float, longitude: float) -> bool:
        """점이 통로 내에 있는지 확인"""
        distance = self.distance_from_centerline(latitude, longitude)
        return distance <= (self.width_m / 2)


@dataclass
class ViolationEvent:
    """항로 이탈 이벤트"""

    timestamp: datetime
    event_type: str  # 'GEOFENCE_EXIT', 'CORRIDOR_DEVIATION', 'SPEED_VIOLATION'
    severity: str  # 'INFO', 'WARNING', 'CRITICAL'

    latitude: float
    longitude: float

    details: Dict

    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp.isoformat(),
            'event_type': self.event_type,
            'severity': self.severity,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'details': self.details
        }


@dataclass
class SMRVesselConfig:
    """SMR 선박 설정"""

    vessel_name: str = "SMR-PIONEER"

    # 선박 제원 (대형 컨테이너선급)
    length_m: float = 400.0
    width_m: float = 59.0
    draught_m: float = 16.0

    # 성능 특성
    max_speed_knots: float = 25.0
    cruise_speed_knots: float = 22.0

    # 원자력 안전 특성
    radiation_monitoring_interval_sec: int = 300  # 5분마다 방사선 모니터링
    mandatory_position_reporting_interval_sec: int = 60  # 1분마다 위치 보고

    # 통로 이탈 허용 오차
    corridor_deviation_threshold_m: float = 2000.0  # 2km


class SMRVesselSimulator:
    """
    SMR 추진 선박 시뮬레이터

    엄격한 통로 제약 및 지오펜스 규정을 준수하며 항해합니다.
    """

    def __init__(
        self,
        config: SMRVesselConfig,
        corridor: Corridor,
        geofence_zones: Optional[List[GeofenceZone]] = None,
        update_interval_sec: int = 10
    ):
        """
        Args:
            config: SMR 선박 설정
            corridor: 항해 통로
            geofence_zones: 지오펜스 구역 리스트
            update_interval_sec: 업데이트 주기 (초)
        """
        self.config = config
        self.corridor = corridor
        self.geofence_zones = geofence_zones or []
        self.update_interval = update_interval_sec

        # 현재 상태
        self.vessel_state: Optional[VesselState] = None
        self.current_centerline_index = 0  # 현재 추종 중인 중심선 세그먼트

        # 시뮬레이션 시간
        self.simulation_time = datetime.utcnow()

        # 이벤트 로그
        self.violation_log: List[ViolationEvent] = []

        # Dead Reckoning 엔진
        self.dr_engine = DeadReckoningEngine()

        # 통계
        self.stats = {
            'total_distance_traveled_m': 0.0,
            'corridor_deviations': 0,
            'geofence_violations': 0,
            'speed_violations': 0
        }

        # 초기 위치를 통로 시작점으로 설정
        self._initialize_position()

    def _initialize_position(self):
        """선박을 통로 시작점에 배치"""

        if len(self.corridor.centerline_coords) < 2:
            raise ValueError("통로 중심선에 최소 2개의 좌표가 필요합니다.")

        start_point = self.corridor.centerline_coords[0]
        next_point = self.corridor.centerline_coords[1]

        # 초기 침로 계산
        initial_course = self.dr_engine.calculate_bearing(
            start_point[0], start_point[1],
            next_point[0], next_point[1]
        )

        # 초기 VesselState 생성
        self.vessel_state = VesselState(
            mmsi=SMR_MMSI,
            vessel_name=self.config.vessel_name,
            vessel_type="SMR",
            latitude=start_point[0],
            longitude=start_point[1],
            course=initial_course,
            speed=self.config.cruise_speed_knots,
            heading=initial_course,
            timestamp=self.simulation_time,
            length=self.config.length_m,
            width=self.config.width_m,
            draught=self.config.draught_m,
            destination=self.corridor.corridor_name,
            is_simulated=True,
            data_source="SIMULATED_SMR"
        )

        self.current_centerline_index = 1

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
            delta_time_sec: 시간 증분
            wind_speed_knots: 풍속
            wind_direction_deg: 풍향
            current_speed_knots: 해류 속도
            current_direction_deg: 해류 방향

        Returns:
            업데이트된 VesselState
        """

        dt = delta_time_sec or self.update_interval

        # 시뮬레이션 시간 진행
        self.simulation_time += timedelta(seconds=dt)

        # ===================================================================
        # 1. 현재 목표 중심선 포인트 확인
        # ===================================================================

        if self.current_centerline_index >= len(self.corridor.centerline_coords):
            # 통로 끝에 도달 → 순환 또는 정지
            self.current_centerline_index = 0

        target_point = self.corridor.centerline_coords[self.current_centerline_index]

        # ===================================================================
        # 2. 목표 방향 및 거리 계산
        # ===================================================================

        target_course = self.dr_engine.calculate_bearing(
            self.vessel_state.latitude,
            self.vessel_state.longitude,
            target_point[0],
            target_point[1]
        )

        distance_to_target = self.dr_engine.calculate_distance_haversine(
            self.vessel_state.latitude,
            self.vessel_state.longitude,
            target_point[0],
            target_point[1]
        )

        # ===================================================================
        # 3. 통로 중심선 추종 (Path Following)
        # ===================================================================

        # 중심선으로부터의 거리 계산
        cross_track_error = self.corridor.distance_from_centerline(
            self.vessel_state.latitude,
            self.vessel_state.longitude
        )

        # 중심선으로 복귀하기 위한 침로 수정
        # 간단한 비례 제어 (P 컨트롤러)
        K_p = 0.05  # 비례 게인
        course_correction = K_p * cross_track_error

        # 목표 침로에 수정값 추가
        desired_course = target_course + np.sign(cross_track_error) * min(course_correction, 10.0)

        # ===================================================================
        # 4. 침로 및 속도 조정
        # ===================================================================

        max_turn_rate_deg_per_sec = 1.5  # SMR 선박은 대형선박이므로 선회율 낮음

        course_diff = (desired_course - self.vessel_state.course + 180) % 360 - 180
        max_course_change = max_turn_rate_deg_per_sec * dt

        if abs(course_diff) > max_course_change:
            self.vessel_state.course += np.sign(course_diff) * max_course_change
        else:
            self.vessel_state.course = desired_course

        self.vessel_state.course = self.vessel_state.course % 360
        self.vessel_state.heading = self.vessel_state.course

        # 속도: 통로 내 최대 속도 준수
        target_speed = min(self.config.cruise_speed_knots, self.corridor.max_speed_knots)
        self.vessel_state.speed = target_speed

        # ===================================================================
        # 5. Dead Reckoning으로 새 위치 계산
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

        # 이동 거리 기록
        distance_moved = self.dr_engine.calculate_distance_haversine(
            self.vessel_state.latitude,
            self.vessel_state.longitude,
            prediction.predicted_latitude,
            prediction.predicted_longitude
        )
        self.stats['total_distance_traveled_m'] += distance_moved

        # 위치 업데이트
        self.vessel_state.latitude = prediction.predicted_latitude
        self.vessel_state.longitude = prediction.predicted_longitude
        self.vessel_state.timestamp = self.simulation_time

        # ===================================================================
        # 6. 통로 이탈 감지
        # ===================================================================

        if not self.corridor.is_within_corridor(
            self.vessel_state.latitude,
            self.vessel_state.longitude
        ):
            deviation_distance = self.corridor.distance_from_centerline(
                self.vessel_state.latitude,
                self.vessel_state.longitude
            )

            if deviation_distance > self.config.corridor_deviation_threshold_m:
                # 중대한 통로 이탈
                self._log_violation(
                    event_type='CORRIDOR_DEVIATION',
                    severity='CRITICAL',
                    details={
                        'deviation_distance_m': deviation_distance,
                        'corridor_width_m': self.corridor.width_m,
                        'threshold_m': self.config.corridor_deviation_threshold_m
                    }
                )
                self.stats['corridor_deviations'] += 1

        # ===================================================================
        # 7. 지오펜스 검사
        # ===================================================================

        for zone in self.geofence_zones:
            in_zone = zone.contains_point(
                self.vessel_state.latitude,
                self.vessel_state.longitude
            )

            if zone.zone_type == 'PROHIBITED' and in_zone:
                # 금지 구역 진입
                self._log_violation(
                    event_type='GEOFENCE_VIOLATION',
                    severity='CRITICAL',
                    details={
                        'zone_id': zone.zone_id,
                        'zone_name': zone.zone_name,
                        'zone_type': zone.zone_type
                    }
                )
                self.stats['geofence_violations'] += 1

            elif zone.zone_type == 'RESTRICTED' and in_zone:
                # 제한 구역 진입 (속도 제한 확인)
                if zone.max_speed_knots and self.vessel_state.speed > zone.max_speed_knots:
                    self._log_violation(
                        event_type='SPEED_VIOLATION',
                        severity='WARNING',
                        details={
                            'zone_id': zone.zone_id,
                            'zone_name': zone.zone_name,
                            'current_speed_knots': self.vessel_state.speed,
                            'max_allowed_speed_knots': zone.max_speed_knots
                        }
                    )
                    self.stats['speed_violations'] += 1

        # ===================================================================
        # 8. 중심선 포인트 도달 확인
        # ===================================================================

        waypoint_arrival_threshold = 1000.0  # 1km

        if distance_to_target < waypoint_arrival_threshold:
            self.current_centerline_index += 1

        return self.vessel_state

    def _log_violation(self, event_type: str, severity: str, details: Dict):
        """위반 이벤트를 로그에 기록"""

        event = ViolationEvent(
            timestamp=self.simulation_time,
            event_type=event_type,
            severity=severity,
            latitude=self.vessel_state.latitude,
            longitude=self.vessel_state.longitude,
            details=details
        )

        self.violation_log.append(event)

    def get_current_state(self) -> VesselState:
        """현재 선박 상태 반환"""
        return self.vessel_state

    def get_violation_log(self) -> List[ViolationEvent]:
        """위반 이벤트 로그 반환"""
        return self.violation_log

    def get_statistics(self) -> Dict:
        """통계 반환"""
        return self.stats.copy()

    def export_violation_log(self, filepath: str):
        """위반 로그를 JSON 파일로 내보내기"""
        log_data = [event.to_dict() for event in self.violation_log]

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)


# ============================================================================
# 사전 정의된 통로 및 지오펜스
# ============================================================================

def create_sample_corridor() -> Corridor:
    """샘플 SMR 항해 통로 생성 (한국 → 미국 서부)"""

    return Corridor(
        corridor_id="SMR_TRANSPACIFIC_01",
        corridor_name="Korea to US West Coast (SMR Route)",
        centerline_coords=[
            (35.1, 129.0),   # Busan, Korea
            (38.0, 140.0),   # East of Japan
            (42.0, 155.0),   # North Pacific
            (45.0, 170.0),   # Mid Pacific
            (48.0, -175.0),  # Aleutian Route
            (50.0, -160.0),  # North of Aleutians
            (48.0, -145.0),  # Gulf of Alaska Approach
            (47.6, -122.3)   # Seattle, USA
        ],
        width_m=20000.0,  # 20km 폭
        max_speed_knots=23.0
    )


def create_sample_geofences() -> List[GeofenceZone]:
    """샘플 지오펜스 구역 생성"""

    zones = []

    # 금지 구역 1: 북태평양 해양 보호구역 (가상)
    zones.append(GeofenceZone(
        zone_id="PROHIBITED_01",
        zone_name="North Pacific Marine Reserve",
        zone_type="PROHIBITED",
        boundary_coords=[
            (44.0, 175.0),
            (44.0, 178.0),
            (46.0, 178.0),
            (46.0, 175.0),
            (44.0, 175.0)
        ]
    ))

    # 제한 구역 1: 알류샨 열도 인근 (속도 제한)
    zones.append(GeofenceZone(
        zone_id="RESTRICTED_01",
        zone_name="Aleutian Islands Slow Zone",
        zone_type="RESTRICTED",
        boundary_coords=[
            (50.0, -165.0),
            (50.0, -155.0),
            (53.0, -155.0),
            (53.0, -165.0),
            (50.0, -165.0)
        ],
        max_speed_knots=15.0,
        mandatory_reporting=True
    ))

    # 제한 구역 2: 시애틀 접근 해역
    zones.append(GeofenceZone(
        zone_id="RESTRICTED_02",
        zone_name="Seattle Approach Zone",
        zone_type="RESTRICTED",
        boundary_coords=[
            (47.0, -123.0),
            (47.0, -122.0),
            (48.0, -122.0),
            (48.0, -123.0),
            (47.0, -123.0)
        ],
        max_speed_knots=12.0,
        mandatory_reporting=True
    ))

    return zones


# ============================================================================
# 사용 예시
# ============================================================================

if __name__ == "__main__":

    import time

    print("=" * 70)
    print("SMR Vessel Simulation - 테스트")
    print("=" * 70)

    # SMR 선박 생성
    config = SMRVesselConfig(
        vessel_name="SMR-PACIFIC-PIONEER"
    )

    corridor = create_sample_corridor()
    geofences = create_sample_geofences()

    simulator = SMRVesselSimulator(
        config=config,
        corridor=corridor,
        geofence_zones=geofences,
        update_interval_sec=60
    )

    print(f"\n선박: {config.vessel_name}")
    print(f"통로: {corridor.corridor_name}")
    print(f"통로 폭: {corridor.width_m/1000:.1f}km")
    print(f"지오펜스 구역: {len(geofences)}개")
    print(f"\n시뮬레이션 시작...\n")

    # 20 스텝 시뮬레이션
    for step in range(20):
        # 환경 조건
        wind_speed = 15.0
        wind_direction = 270.0  # 서풍
        current_speed = 1.5
        current_direction = 180.0  # 남향 해류

        # 시뮬레이션 스텝
        state = simulator.step(
            delta_time_sec=300,  # 5분
            wind_speed_knots=wind_speed,
            wind_direction_deg=wind_direction,
            current_speed_knots=current_speed,
            current_direction_deg=current_direction
        )

        # 통로 이탈 거리 계산
        deviation = corridor.distance_from_centerline(
            state.latitude,
            state.longitude
        )

        # 출력
        print(f"[스텝 {step+1}] 시간: {state.timestamp.strftime('%H:%M:%S')}")
        print(f"  위치: {state.latitude:.4f}°N, {state.longitude:.4f}°E")
        print(f"  속도: {state.speed:.1f} knots, 침로: {state.course:.1f}°")
        print(f"  통로 이탈: {deviation:.0f}m (폭: {corridor.width_m/1000:.1f}km)")

        # 위반 확인
        recent_violations = simulator.get_violation_log()
        if recent_violations:
            latest = recent_violations[-1]
            if (simulator.simulation_time - latest.timestamp).total_seconds() < 301:
                print(f"  ⚠️ 위반 감지: {latest.event_type} ({latest.severity})")

        time.sleep(0.3)

    # 최종 통계
    print("\n" + "=" * 70)
    print("시뮬레이션 완료")
    print("=" * 70)

    stats = simulator.get_statistics()
    print(f"총 이동 거리: {stats['total_distance_traveled_m']/1000:.1f} km")
    print(f"통로 이탈 횟수: {stats['corridor_deviations']}")
    print(f"지오펜스 위반: {stats['geofence_violations']}")
    print(f"속도 위반: {stats['speed_violations']}")

    violations = simulator.get_violation_log()
    if violations:
        print(f"\n위반 이벤트 로그 ({len(violations)}건):")
        for i, v in enumerate(violations[:5], 1):  # 처음 5건만 출력
            print(f"  {i}. [{v.severity}] {v.event_type} @ {v.timestamp.strftime('%H:%M:%S')}")
