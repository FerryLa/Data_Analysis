"""
Dead Reckoning Prediction Engine
=================================

AIS 신호 손실 중 선박 위치를 예측하고 오차 반경을 계산합니다.

수학적 기반:
- Great Circle Navigation (대권항법)
- Circular Error Probable (원형 오차 확률)
- 환경 드리프트 모델링 (바람, 해류)
"""

import numpy as np
from typing import Tuple, Optional, Dict
from dataclasses import dataclass
from datetime import datetime, timedelta
import math


# 지구 반경 (미터)
EARTH_RADIUS_M = 6371000.0

# AIS Class A 센서 정확도 (미터)
AIS_SENSOR_ACCURACY = 10.0

# 각도 변환 상수
DEG_TO_RAD = np.pi / 180.0
RAD_TO_DEG = 180.0 / np.pi


@dataclass
class PredictionResult:
    """예측 결과를 담는 데이터 구조"""

    # 예측 위치
    predicted_latitude: float
    predicted_longitude: float

    # 오차 추정
    error_radius_95: float  # 95% 신뢰 반경 (미터)
    error_radius_50: float  # 50% 신뢰 반경 (미터)

    # 메타데이터
    time_since_last_fix: float  # 마지막 위치 수정 이후 경과 시간 (초)
    prediction_confidence: float  # 예측 신뢰도 (0-1)

    # 환경 영향
    wind_drift_m: Optional[Tuple[float, float]] = None  # (동-서, 남-북) 드리프트
    current_drift_m: Optional[Tuple[float, float]] = None

    def to_dict(self) -> Dict:
        """JSON 직렬화를 위한 딕셔너리 변환"""
        return {
            'predicted_latitude': self.predicted_latitude,
            'predicted_longitude': self.predicted_longitude,
            'error_radius_95': self.error_radius_95,
            'error_radius_50': self.error_radius_50,
            'time_since_last_fix': self.time_since_last_fix,
            'prediction_confidence': self.prediction_confidence,
            'wind_drift_m': self.wind_drift_m,
            'current_drift_m': self.current_drift_m
        }


class DeadReckoningEngine:
    """
    Dead Reckoning 예측 엔진

    마지막 알려진 위치, 속도, 침로를 기반으로 현재 위치를 추정합니다.
    """

    def __init__(
        self,
        course_uncertainty_deg: float = 2.0,  # 침로 불확실성 (도)
        speed_uncertainty_knots: float = 0.1,  # 속도 불확실성 (노트)
        wind_drift_coefficient: float = 0.03,  # 바람 드리프트 계수
        current_drift_coefficient: float = 1.0  # 해류 드리프트 계수
    ):
        """
        Args:
            course_uncertainty_deg: 침로 측정 불확실성 (표준편차, 도)
            speed_uncertainty_knots: 속도 측정 불확실성 (표준편차, 노트)
            wind_drift_coefficient: 바람에 의한 드리프트 계수
            current_drift_coefficient: 해류에 의한 드리프트 계수
        """
        self.course_uncertainty_deg = course_uncertainty_deg
        self.speed_uncertainty_knots = speed_uncertainty_knots
        self.wind_drift_coef = wind_drift_coefficient
        self.current_drift_coef = current_drift_coefficient

    def predict_position(
        self,
        last_latitude: float,
        last_longitude: float,
        course_deg: float,  # Course Over Ground (도, 0=북, 90=동)
        speed_knots: float,  # Speed Over Ground (노트)
        time_elapsed_seconds: float,  # 경과 시간 (초)
        wind_speed_knots: Optional[float] = None,
        wind_direction_deg: Optional[float] = None,
        current_speed_knots: Optional[float] = None,
        current_direction_deg: Optional[float] = None
    ) -> PredictionResult:
        """
        Dead Reckoning을 사용하여 선박 위치를 예측합니다.

        수학적 배경:
        ============

        1. 대권항법 (Great Circle Navigation)
        -------------------------------------
        구면 삼각법을 사용하여 지구 표면에서의 최단 거리 계산:

        φ₂ = asin(sin(φ₁)·cos(δ) + cos(φ₁)·sin(δ)·cos(θ))
        λ₂ = λ₁ + atan2(sin(θ)·sin(δ)·cos(φ₁), cos(δ) - sin(φ₁)·sin(φ₂))

        여기서:
          φ = 위도 (라디안)
          λ = 경도 (라디안)
          δ = 각거리 = d/R (d=거리, R=지구 반경)
          θ = 진침로 (라디안)

        2. 오차 누적 모델 (Error Accumulation)
        ---------------------------------------
        시간에 따른 위치 오차 증가:

        σ_total(t) = √(σ_sensor² + σ_course² · t² + σ_speed² · t²)

        구성 요소:
          σ_sensor: 기본 AIS 센서 정확도 (~10m for Class A)
          σ_course: 침로 불확실성에 의한 오차
          σ_speed: 속도 불확실성에 의한 오차
          t: 마지막 위치 수정 이후 경과 시간

        3. 신뢰 구간 (Confidence Intervals)
        ------------------------------------
        정규분포 가정 하 신뢰 반경:

          50% 신뢰: r₅₀ = 0.67 · σ_total  (CEP)
          95% 신뢰: r₉₅ = 2.45 · σ_total

        Args:
            last_latitude: 마지막 알려진 위도 (도)
            last_longitude: 마지막 알려진 경도 (도)
            course_deg: 대지 침로 (도, 0=북쪽)
            speed_knots: 대지 속도 (노트)
            time_elapsed_seconds: 경과 시간 (초)
            wind_speed_knots: 풍속 (노트, 선택)
            wind_direction_deg: 풍향 (도, 선택)
            current_speed_knots: 해류 속도 (노트, 선택)
            current_direction_deg: 해류 방향 (도, 선택)

        Returns:
            PredictionResult: 예측된 위치 및 오차 정보
        """

        # ===================================================================
        # 1. 기본 Dead Reckoning (바람/해류 없이)
        # ===================================================================

        # 노트를 m/s로 변환 (1 knot = 0.514444 m/s)
        speed_ms = speed_knots * 0.514444

        # 이동 거리 계산 (미터)
        distance_traveled_m = speed_ms * time_elapsed_seconds

        # 각거리 계산 (라디안)
        angular_distance = distance_traveled_m / EARTH_RADIUS_M

        # 위도/경도를 라디안으로 변환
        lat1_rad = last_latitude * DEG_TO_RAD
        lon1_rad = last_longitude * DEG_TO_RAD

        # 침로를 라디안으로 변환 (북쪽 기준)
        course_rad = course_deg * DEG_TO_RAD

        # 대권항법 공식으로 새 위치 계산
        lat2_rad = np.arcsin(
            np.sin(lat1_rad) * np.cos(angular_distance) +
            np.cos(lat1_rad) * np.sin(angular_distance) * np.cos(course_rad)
        )

        lon2_rad = lon1_rad + np.arctan2(
            np.sin(course_rad) * np.sin(angular_distance) * np.cos(lat1_rad),
            np.cos(angular_distance) - np.sin(lat1_rad) * np.sin(lat2_rad)
        )

        # 라디안을 도로 변환
        predicted_lat = lat2_rad * RAD_TO_DEG
        predicted_lon = lon2_rad * RAD_TO_DEG

        # 경도 정규화 (-180 ~ 180)
        predicted_lon = ((predicted_lon + 180) % 360) - 180

        # ===================================================================
        # 2. 환경 드리프트 추가 (바람, 해류)
        # ===================================================================

        wind_drift_m = None
        current_drift_m = None

        total_drift_east_m = 0.0
        total_drift_north_m = 0.0

        # 바람 드리프트 계산
        if wind_speed_knots is not None and wind_direction_deg is not None:
            wind_ms = wind_speed_knots * 0.514444
            wind_drift_speed = wind_ms * self.wind_drift_coef

            # 바람 방향 (기상학적: 바람이 불어오는 방향)
            # → 드리프트 방향으로 변환 (바람이 불어가는 방향)
            drift_direction_rad = (wind_direction_deg + 180) * DEG_TO_RAD

            drift_east = wind_drift_speed * np.sin(drift_direction_rad) * time_elapsed_seconds
            drift_north = wind_drift_speed * np.cos(drift_direction_rad) * time_elapsed_seconds

            total_drift_east_m += drift_east
            total_drift_north_m += drift_north

            wind_drift_m = (drift_east, drift_north)

        # 해류 드리프트 계산
        if current_speed_knots is not None and current_direction_deg is not None:
            current_ms = current_speed_knots * 0.514444 * self.current_drift_coef

            current_rad = current_direction_deg * DEG_TO_RAD

            drift_east = current_ms * np.sin(current_rad) * time_elapsed_seconds
            drift_north = current_ms * np.cos(current_rad) * time_elapsed_seconds

            total_drift_east_m += drift_east
            total_drift_north_m += drift_north

            current_drift_m = (drift_east, drift_north)

        # 드리프트를 위도/경도 오프셋으로 변환
        if total_drift_east_m != 0.0 or total_drift_north_m != 0.0:
            # 위도 오프셋 (미터 → 도)
            lat_offset = total_drift_north_m / EARTH_RADIUS_M * RAD_TO_DEG

            # 경도 오프셋 (위도에 따라 조정)
            lon_offset = total_drift_east_m / (
                EARTH_RADIUS_M * np.cos(predicted_lat * DEG_TO_RAD)
            ) * RAD_TO_DEG

            predicted_lat += lat_offset
            predicted_lon += lon_offset

        # ===================================================================
        # 3. 오차 반경 계산
        # ===================================================================

        # 시간을 분 단위로 변환
        time_elapsed_minutes = time_elapsed_seconds / 60.0

        # 센서 기본 오차
        sigma_sensor = AIS_SENSOR_ACCURACY

        # 침로 불확실성에 의한 오차 (미터)
        # σ_course = distance × sin(course_uncertainty)
        sigma_course = distance_traveled_m * np.sin(
            self.course_uncertainty_deg * DEG_TO_RAD
        )

        # 속도 불확실성에 의한 오차 (미터)
        # σ_speed = speed_uncertainty × time
        sigma_speed = (
            self.speed_uncertainty_knots * 0.514444 * time_elapsed_seconds
        )

        # 총 오차 (RSS - Root Sum Square)
        sigma_total = np.sqrt(
            sigma_sensor**2 +
            sigma_course**2 +
            sigma_speed**2
        )

        # 50% 신뢰 반경 (CEP - Circular Error Probable)
        error_radius_50 = 0.67 * sigma_total

        # 95% 신뢰 반경 (2.45σ)
        error_radius_95 = 2.45 * sigma_total

        # ===================================================================
        # 4. 예측 신뢰도 계산
        # ===================================================================

        # 신뢰도는 시간에 따라 지수적으로 감소
        # λ = 0.1 per minute (10분 후 ~37% 신뢰도)
        decay_constant = 0.1
        confidence = np.exp(-decay_constant * time_elapsed_minutes)

        # ===================================================================
        # 5. 결과 반환
        # ===================================================================

        return PredictionResult(
            predicted_latitude=predicted_lat,
            predicted_longitude=predicted_lon,
            error_radius_95=error_radius_95,
            error_radius_50=error_radius_50,
            time_since_last_fix=time_elapsed_seconds,
            prediction_confidence=confidence,
            wind_drift_m=wind_drift_m,
            current_drift_m=current_drift_m
        )

    @staticmethod
    def calculate_distance_haversine(
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """
        Haversine 공식을 사용하여 두 지점 간 거리를 계산합니다.

        공식:
        -----
        a = sin²(Δφ/2) + cos(φ₁)·cos(φ₂)·sin²(Δλ/2)
        c = 2·atan2(√a, √(1-a))
        d = R·c

        Args:
            lat1, lon1: 첫 번째 지점 (도)
            lat2, lon2: 두 번째 지점 (도)

        Returns:
            거리 (미터)
        """
        lat1_rad = lat1 * DEG_TO_RAD
        lat2_rad = lat2 * DEG_TO_RAD
        delta_lat = (lat2 - lat1) * DEG_TO_RAD
        delta_lon = (lon2 - lon1) * DEG_TO_RAD

        a = (
            np.sin(delta_lat / 2)**2 +
            np.cos(lat1_rad) * np.cos(lat2_rad) *
            np.sin(delta_lon / 2)**2
        )

        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

        distance_m = EARTH_RADIUS_M * c

        return distance_m

    @staticmethod
    def calculate_bearing(
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """
        두 지점 간 초기 방위각을 계산합니다.

        공식:
        -----
        θ = atan2(sin(Δλ)·cos(φ₂), cos(φ₁)·sin(φ₂) - sin(φ₁)·cos(φ₂)·cos(Δλ))

        Args:
            lat1, lon1: 시작 지점 (도)
            lat2, lon2: 도착 지점 (도)

        Returns:
            방위각 (도, 0=북쪽, 90=동쪽)
        """
        lat1_rad = lat1 * DEG_TO_RAD
        lat2_rad = lat2 * DEG_TO_RAD
        delta_lon = (lon2 - lon1) * DEG_TO_RAD

        y = np.sin(delta_lon) * np.cos(lat2_rad)
        x = (
            np.cos(lat1_rad) * np.sin(lat2_rad) -
            np.sin(lat1_rad) * np.cos(lat2_rad) * np.cos(delta_lon)
        )

        bearing_rad = np.arctan2(y, x)
        bearing_deg = bearing_rad * RAD_TO_DEG

        # 정규화 (0-360)
        bearing_deg = (bearing_deg + 360) % 360

        return bearing_deg

    def validate_prediction(
        self,
        predicted_lat: float,
        predicted_lon: float,
        actual_lat: float,
        actual_lon: float,
        error_radius_95: float
    ) -> Dict[str, any]:
        """
        예측 정확도를 검증합니다.

        Args:
            predicted_lat, predicted_lon: 예측 위치 (도)
            actual_lat, actual_lon: 실제 위치 (도)
            error_radius_95: 95% 신뢰 반경 (미터)

        Returns:
            검증 결과 딕셔너리
        """
        # 실제 오차 계산
        actual_error_m = self.calculate_distance_haversine(
            predicted_lat, predicted_lon,
            actual_lat, actual_lon
        )

        # 오차가 신뢰 반경 내에 있는지 확인
        within_confidence = actual_error_m <= error_radius_95

        # 정규화된 오차 (0 = 완벽, 1 = 신뢰 반경 경계, >1 = 신뢰 반경 초과)
        normalized_error = actual_error_m / error_radius_95 if error_radius_95 > 0 else 0

        return {
            'actual_error_m': actual_error_m,
            'within_confidence_interval': within_confidence,
            'normalized_error': normalized_error,
            'error_radius_95': error_radius_95
        }


# ============================================================================
# 사용 예시
# ============================================================================

if __name__ == "__main__":

    # Dead Reckoning 엔진 생성
    engine = DeadReckoningEngine(
        course_uncertainty_deg=2.0,
        speed_uncertainty_knots=0.1
    )

    print("=" * 70)
    print("Dead Reckoning Prediction Engine - 테스트")
    print("=" * 70)

    # 시나리오 1: 기본 예측 (환경 영향 없음)
    print("\n[시나리오 1] 기본 Dead Reckoning")
    print("-" * 70)

    last_lat = 25.0  # 위도 (북위 25도)
    last_lon = 55.0  # 경도 (동경 55도)
    course = 45.0    # 북동쪽으로 이동
    speed = 20.0     # 20 노트
    elapsed_time = 600  # 10분 (600초)

    result = engine.predict_position(
        last_latitude=last_lat,
        last_longitude=last_lon,
        course_deg=course,
        speed_knots=speed,
        time_elapsed_seconds=elapsed_time
    )

    print(f"시작 위치: {last_lat:.4f}°N, {last_lon:.4f}°E")
    print(f"침로: {course:.1f}°, 속도: {speed:.1f} knots")
    print(f"경과 시간: {elapsed_time/60:.1f}분")
    print(f"\n예측 위치: {result.predicted_latitude:.4f}°N, "
          f"{result.predicted_longitude:.4f}°E")
    print(f"50% 신뢰 반경: {result.error_radius_50:.1f}m")
    print(f"95% 신뢰 반경: {result.error_radius_95:.1f}m")
    print(f"예측 신뢰도: {result.prediction_confidence:.2%}")

    # 시나리오 2: 바람/해류 포함
    print("\n[시나리오 2] 바람 + 해류 영향 포함")
    print("-" * 70)

    result_with_env = engine.predict_position(
        last_latitude=last_lat,
        last_longitude=last_lon,
        course_deg=course,
        speed_knots=speed,
        time_elapsed_seconds=elapsed_time,
        wind_speed_knots=25.0,  # 25 knots 풍속
        wind_direction_deg=270.0,  # 서풍 (동쪽으로 드리프트)
        current_speed_knots=2.0,  # 2 knots 해류
        current_direction_deg=180.0  # 남향 해류
    )

    print(f"풍속: 25 knots (서풍)")
    print(f"해류: 2 knots (남향)")
    print(f"\n예측 위치 (환경 영향 포함): "
          f"{result_with_env.predicted_latitude:.4f}°N, "
          f"{result_with_env.predicted_longitude:.4f}°E")
    print(f"바람 드리프트: 동쪽 {result_with_env.wind_drift_m[0]:.1f}m, "
          f"북쪽 {result_with_env.wind_drift_m[1]:.1f}m")
    print(f"해류 드리프트: 동쪽 {result_with_env.current_drift_m[0]:.1f}m, "
          f"북쪽 {result_with_env.current_drift_m[1]:.1f}m")

    # 시나리오 3: 장시간 예측 (오차 증가 시연)
    print("\n[시나리오 3] 시간에 따른 오차 증가")
    print("-" * 70)

    time_steps = [60, 300, 600, 1800, 3600]  # 1분, 5분, 10분, 30분, 1시간

    print(f"{'시간':>10} {'오차 반경(50%)':>15} {'오차 반경(95%)':>15} {'신뢰도':>10}")
    print("-" * 70)

    for t in time_steps:
        r = engine.predict_position(
            last_latitude=last_lat,
            last_longitude=last_lon,
            course_deg=course,
            speed_knots=speed,
            time_elapsed_seconds=t
        )

        print(f"{t/60:>8.1f}분 {r.error_radius_50:>13.1f}m "
              f"{r.error_radius_95:>13.1f}m {r.prediction_confidence:>9.1%}")

    # 시나리오 4: 예측 검증
    print("\n[시나리오 4] 예측 정확도 검증")
    print("-" * 70)

    # 실제 위치 (시뮬레이션)
    actual_lat = result.predicted_latitude + 0.001  # 약간 다른 실제 위치
    actual_lon = result.predicted_longitude + 0.001

    validation = engine.validate_prediction(
        predicted_lat=result.predicted_latitude,
        predicted_lon=result.predicted_longitude,
        actual_lat=actual_lat,
        actual_lon=actual_lon,
        error_radius_95=result.error_radius_95
    )

    print(f"예측 위치: {result.predicted_latitude:.4f}°N, "
          f"{result.predicted_longitude:.4f}°E")
    print(f"실제 위치: {actual_lat:.4f}°N, {actual_lon:.4f}°E")
    print(f"실제 오차: {validation['actual_error_m']:.1f}m")
    print(f"95% 신뢰 반경: {validation['error_radius_95']:.1f}m")
    print(f"신뢰 구간 내: {validation['within_confidence_interval']}")
    print(f"정규화된 오차: {validation['normalized_error']:.2f}")

    print("\n" + "=" * 70)
    print("테스트 완료")
    print("=" * 70)
