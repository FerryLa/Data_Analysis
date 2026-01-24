"""
Communication Scenario Controller
==================================

통신 환경 시나리오를 제어하고 신호 품질 저하를 시뮬레이션합니다.

기능:
- 신호 지연 주입 (VSAT, LEO 위성, AIS 지상국)
- 패킷 손실 모델링 (Gilbert-Elliott 모델)
- 업데이트 주기 조절
- 지오펜스 활성화/비활성화
- 통신 신뢰성 지수 계산
"""

import numpy as np
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import random


class CommunicationType(Enum):
    """통신 유형"""
    AIS_TERRESTRIAL = "AIS_TERRESTRIAL"  # AIS 지상국
    VSAT = "VSAT"  # 정지궤도 위성
    LEO_SATELLITE = "LEO_SATELLITE"  # 저궤도 위성


class SeaState(Enum):
    """해상 상태 (Douglas Sea Scale)"""
    CALM = 0  # 0-0.1m
    SMOOTH = 1  # 0.1-0.5m
    SLIGHT = 2  # 0.5-1.25m
    MODERATE = 3  # 1.25-2.5m
    ROUGH = 4  # 2.5-4m
    VERY_ROUGH = 5  # 4-6m
    HIGH = 6  # 6-9m


@dataclass
class CommunicationProfile:
    """통신 프로파일 설정"""

    comm_type: CommunicationType

    # 지연 특성 (밀리초)
    latency_mean_ms: float
    latency_std_ms: float

    # 패킷 손실 확률
    packet_loss_good_state: float  # Good 상태에서의 손실률
    packet_loss_bad_state: float   # Bad 상태에서의 손실률

    # Gilbert-Elliott 모델 전이 확률
    prob_good_to_bad: float
    prob_bad_to_good: float

    # 업데이트 주기 (초)
    normal_update_interval_sec: int
    degraded_update_interval_sec: int
    critical_update_interval_sec: int

    @staticmethod
    def get_ais_terrestrial() -> 'CommunicationProfile':
        """AIS 지상국 프로파일"""
        return CommunicationProfile(
            comm_type=CommunicationType.AIS_TERRESTRIAL,
            latency_mean_ms=2000,
            latency_std_ms=500,
            packet_loss_good_state=0.01,
            packet_loss_bad_state=0.30,
            prob_good_to_bad=0.05,
            prob_bad_to_good=0.15,
            normal_update_interval_sec=10,
            degraded_update_interval_sec=30,
            critical_update_interval_sec=120
        )

    @staticmethod
    def get_vsat() -> 'CommunicationProfile':
        """VSAT 위성 프로파일"""
        return CommunicationProfile(
            comm_type=CommunicationType.VSAT,
            latency_mean_ms=500,
            latency_std_ms=100,
            packet_loss_good_state=0.005,
            packet_loss_bad_state=0.20,
            prob_good_to_bad=0.03,
            prob_bad_to_good=0.20,
            normal_update_interval_sec=5,
            degraded_update_interval_sec=20,
            critical_update_interval_sec=60
        )

    @staticmethod
    def get_leo_satellite() -> 'CommunicationProfile':
        """LEO 위성 프로파일 (Starlink, OneWeb 등)"""
        return CommunicationProfile(
            comm_type=CommunicationType.LEO_SATELLITE,
            latency_mean_ms=30,
            latency_std_ms=10,
            packet_loss_good_state=0.002,
            packet_loss_bad_state=0.15,
            prob_good_to_bad=0.02,
            prob_bad_to_good=0.30,
            normal_update_interval_sec=2,
            degraded_update_interval_sec=10,
            critical_update_interval_sec=30
        )


@dataclass
class ScenarioConfig:
    """시나리오 설정"""

    scenario_name: str

    # 통신 프로파일
    communication_profile: CommunicationProfile

    # 환경 조건
    sea_state: SeaState = SeaState.MODERATE
    wind_speed_knots: float = 15.0
    wind_direction_deg: float = 270.0
    current_speed_knots: float = 1.0
    current_direction_deg: float = 180.0

    # 품질 저하 강도 (0.0 = 정상, 1.0 = 최대 저하)
    degradation_level: float = 0.0

    # 지오펜스 활성화
    geofence_enabled: bool = True

    # 강제 블랙아웃 (테스트용)
    force_blackout: bool = False
    blackout_duration_sec: int = 300


class GilbertElliotModel:
    """
    Gilbert-Elliott 패킷 손실 모델

    2-상태 마르코프 체인을 사용하여 버스트성 패킷 손실을 모델링합니다.
    """

    def __init__(
        self,
        p_loss_good: float,
        p_loss_bad: float,
        p_gb: float,  # Good → Bad 전이 확률
        p_bg: float   # Bad → Good 전이 확률
    ):
        self.p_loss_good = p_loss_good
        self.p_loss_bad = p_loss_bad
        self.p_gb = p_gb
        self.p_bg = p_bg

        # 초기 상태 (Good)
        self.current_state = 'GOOD'

    def step(self) -> bool:
        """
        한 스텝을 진행하고 패킷 손실 여부를 반환합니다.

        Returns:
            True if packet is lost, False otherwise
        """

        # 상태 전이
        if self.current_state == 'GOOD':
            if random.random() < self.p_gb:
                self.current_state = 'BAD'
        else:  # BAD
            if random.random() < self.p_bg:
                self.current_state = 'GOOD'

        # 패킷 손실 여부 결정
        if self.current_state == 'GOOD':
            return random.random() < self.p_loss_good
        else:
            return random.random() < self.p_loss_bad

    def get_current_state(self) -> str:
        return self.current_state


class ScenarioController:
    """
    통신 시나리오 컨트롤러

    다양한 통신 환경을 시뮬레이션하고 성능 지표를 수집합니다.
    """

    def __init__(self, config: ScenarioConfig):
        """
        Args:
            config: 시나리오 설정
        """
        self.config = config

        # Gilbert-Elliott 모델 초기화
        self.ge_model = GilbertElliotModel(
            p_loss_good=config.communication_profile.packet_loss_good_state,
            p_loss_bad=config.communication_profile.packet_loss_bad_state,
            p_gb=config.communication_profile.prob_good_to_bad,
            p_bg=config.communication_profile.prob_bad_to_good
        )

        # 통계
        self.stats = {
            'total_packets': 0,
            'lost_packets': 0,
            'total_delay_ms': 0.0,
            'blackout_events': 0,
            'total_blackout_duration_sec': 0.0
        }

        # 현재 블랙아웃 상태
        self.in_blackout = False
        self.blackout_start_time: Optional[datetime] = None
        self.blackout_end_time: Optional[datetime] = None

        # 시뮬레이션 시간
        self.simulation_time = datetime.utcnow()

    def process_transmission(
        self,
        current_time: Optional[datetime] = None
    ) -> Dict:
        """
        데이터 전송을 처리하고 결과를 반환합니다.

        Args:
            current_time: 현재 시뮬레이션 시간

        Returns:
            전송 결과 딕셔너리
        """

        if current_time:
            self.simulation_time = current_time

        self.stats['total_packets'] += 1

        # ===================================================================
        # 1. 블랙아웃 확인
        # ===================================================================

        if self.config.force_blackout:
            if not self.in_blackout:
                # 블랙아웃 시작
                self.in_blackout = True
                self.blackout_start_time = self.simulation_time
                self.blackout_end_time = self.simulation_time + timedelta(
                    seconds=self.config.blackout_duration_sec
                )
                self.stats['blackout_events'] += 1

        if self.in_blackout:
            if self.simulation_time >= self.blackout_end_time:
                # 블랙아웃 종료
                duration = (self.blackout_end_time - self.blackout_start_time).total_seconds()
                self.stats['total_blackout_duration_sec'] += duration

                self.in_blackout = False
                self.blackout_start_time = None
                self.blackout_end_time = None

            else:
                # 블랙아웃 중 - 전송 실패
                self.stats['lost_packets'] += 1
                return {
                    'success': False,
                    'reason': 'BLACKOUT',
                    'latency_ms': None,
                    'in_blackout': True
                }

        # ===================================================================
        # 2. 패킷 손실 확인 (Gilbert-Elliott 모델)
        # ===================================================================

        # 저하 수준에 따른 손실률 증가
        degradation_factor = 1.0 + self.config.degradation_level * 2.0

        # 임시로 손실률 조정
        original_p_loss_good = self.ge_model.p_loss_good
        original_p_loss_bad = self.ge_model.p_loss_bad

        self.ge_model.p_loss_good = min(original_p_loss_good * degradation_factor, 0.5)
        self.ge_model.p_loss_bad = min(original_p_loss_bad * degradation_factor, 0.9)

        packet_lost = self.ge_model.step()

        # 원래 값 복원
        self.ge_model.p_loss_good = original_p_loss_good
        self.ge_model.p_loss_bad = original_p_loss_bad

        if packet_lost:
            self.stats['lost_packets'] += 1
            return {
                'success': False,
                'reason': 'PACKET_LOSS',
                'latency_ms': None,
                'channel_state': self.ge_model.get_current_state()
            }

        # ===================================================================
        # 3. 지연 계산
        # ===================================================================

        # 기본 지연 (정규분포)
        base_latency = np.random.normal(
            self.config.communication_profile.latency_mean_ms,
            self.config.communication_profile.latency_std_ms
        )

        # 해상 상태에 따른 지연 증가
        sea_state_latency = self._calculate_sea_state_impact()

        # 저하 수준에 따른 지연 증가
        degradation_latency = (
            self.config.communication_profile.latency_mean_ms *
            self.config.degradation_level * 0.5
        )

        total_latency = max(0, base_latency + sea_state_latency + degradation_latency)

        self.stats['total_delay_ms'] += total_latency

        # ===================================================================
        # 4. 전송 성공
        # ===================================================================

        return {
            'success': True,
            'latency_ms': total_latency,
            'channel_state': self.ge_model.get_current_state(),
            'sea_state_impact_ms': sea_state_latency,
            'degradation_impact_ms': degradation_latency
        }

    def _calculate_sea_state_impact(self) -> float:
        """
        해상 상태에 따른 통신 지연 영향을 계산합니다.

        Returns:
            추가 지연 (밀리초)
        """

        # 해상 상태별 지연 계수
        sea_state_factors = {
            SeaState.CALM: 0.0,
            SeaState.SMOOTH: 0.05,
            SeaState.SLIGHT: 0.10,
            SeaState.MODERATE: 0.20,
            SeaState.ROUGH: 0.40,
            SeaState.VERY_ROUGH: 0.70,
            SeaState.HIGH: 1.20
        }

        factor = sea_state_factors.get(self.config.sea_state, 0.0)

        # 기본 지연에 비례하여 증가
        additional_delay = (
            self.config.communication_profile.latency_mean_ms * factor
        )

        return additional_delay

    def get_update_interval(self) -> int:
        """
        현재 저하 수준에 따른 업데이트 주기를 반환합니다.

        Returns:
            업데이트 주기 (초)
        """

        if self.config.degradation_level < 0.3:
            return self.config.communication_profile.normal_update_interval_sec
        elif self.config.degradation_level < 0.7:
            return self.config.communication_profile.degraded_update_interval_sec
        else:
            return self.config.communication_profile.critical_update_interval_sec

    def calculate_reliability_index(self) -> float:
        """
        통신 신뢰성 지수를 계산합니다 (0-100).

        SAI (Signal Availability Index):
        SAI = (successful_packets / total_packets) × 100

        Returns:
            신뢰성 지수 (0-100)
        """

        if self.stats['total_packets'] == 0:
            return 100.0

        successful_packets = self.stats['total_packets'] - self.stats['lost_packets']

        sai = (successful_packets / self.stats['total_packets']) * 100.0

        return sai

    def calculate_average_latency(self) -> float:
        """
        평균 지연을 계산합니다.

        Returns:
            평균 지연 (밀리초)
        """

        successful_packets = self.stats['total_packets'] - self.stats['lost_packets']

        if successful_packets == 0:
            return 0.0

        return self.stats['total_delay_ms'] / successful_packets

    def get_statistics(self) -> Dict:
        """통계 반환"""
        return {
            **self.stats,
            'reliability_index': self.calculate_reliability_index(),
            'average_latency_ms': self.calculate_average_latency(),
            'packet_loss_rate': (
                self.stats['lost_packets'] / self.stats['total_packets']
                if self.stats['total_packets'] > 0 else 0.0
            )
        }

    def reset_statistics(self):
        """통계 초기화"""
        self.stats = {
            'total_packets': 0,
            'lost_packets': 0,
            'total_delay_ms': 0.0,
            'blackout_events': 0,
            'total_blackout_duration_sec': 0.0
        }


# ============================================================================
# 사전 정의된 시나리오
# ============================================================================

def create_scenario_normal_conditions() -> ScenarioConfig:
    """정상 조건 시나리오"""
    return ScenarioConfig(
        scenario_name="Normal Conditions",
        communication_profile=CommunicationProfile.get_vsat(),
        sea_state=SeaState.MODERATE,
        degradation_level=0.0
    )


def create_scenario_heavy_weather() -> ScenarioConfig:
    """악천후 시나리오"""
    return ScenarioConfig(
        scenario_name="Heavy Weather",
        communication_profile=CommunicationProfile.get_vsat(),
        sea_state=SeaState.VERY_ROUGH,
        wind_speed_knots=45.0,
        degradation_level=0.6
    )


def create_scenario_satellite_handover() -> ScenarioConfig:
    """위성 핸드오버 시나리오 (LEO)"""
    return ScenarioConfig(
        scenario_name="LEO Satellite Handover",
        communication_profile=CommunicationProfile.get_leo_satellite(),
        sea_state=SeaState.SLIGHT,
        degradation_level=0.3
    )


def create_scenario_critical_failure() -> ScenarioConfig:
    """중대 장애 시나리오"""
    return ScenarioConfig(
        scenario_name="Critical Communication Failure",
        communication_profile=CommunicationProfile.get_ais_terrestrial(),
        sea_state=SeaState.HIGH,
        degradation_level=0.9,
        force_blackout=True,
        blackout_duration_sec=600
    )


# ============================================================================
# 사용 예시
# ============================================================================

if __name__ == "__main__":

    import time

    print("=" * 70)
    print("Communication Scenario Controller - 테스트")
    print("=" * 70)

    # 시나리오 리스트
    scenarios = [
        create_scenario_normal_conditions(),
        create_scenario_heavy_weather(),
        create_scenario_satellite_handover(),
        create_scenario_critical_failure()
    ]

    for scenario_config in scenarios:
        print(f"\n[시나리오: {scenario_config.scenario_name}]")
        print(f"통신 유형: {scenario_config.communication_profile.comm_type.value}")
        print(f"해상 상태: {scenario_config.sea_state.name}")
        print(f"저하 수준: {scenario_config.degradation_level:.1%}")
        print("-" * 70)

        controller = ScenarioController(scenario_config)

        # 100번 전송 시뮬레이션
        for i in range(100):
            result = controller.process_transmission()

            # 10번마다 통계 출력
            if (i + 1) % 20 == 0:
                stats = controller.get_statistics()
                print(f"  [{i+1}/100] 신뢰성: {stats['reliability_index']:.1f}%, "
                      f"평균 지연: {stats['average_latency_ms']:.1f}ms, "
                      f"손실률: {stats['packet_loss_rate']:.2%}")

        # 최종 통계
        final_stats = controller.get_statistics()
        print(f"\n최종 결과:")
        print(f"  총 패킷: {final_stats['total_packets']}")
        print(f"  손실 패킷: {final_stats['lost_packets']}")
        print(f"  신뢰성 지수: {final_stats['reliability_index']:.2f}%")
        print(f"  평균 지연: {final_stats['average_latency_ms']:.2f}ms")
        print(f"  패킷 손실률: {final_stats['packet_loss_rate']:.2%}")
        print(f"  블랙아웃 이벤트: {final_stats['blackout_events']}")
        print(f"  총 블랙아웃 시간: {final_stats['total_blackout_duration_sec']:.0f}초")

    print("\n" + "=" * 70)
    print("테스트 완료")
    print("=" * 70)
