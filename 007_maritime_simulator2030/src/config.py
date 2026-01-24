"""
Configuration Management
=========================

시뮬레이터 전역 설정을 관리합니다.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class SimulatorConfig:
    """시뮬레이터 전역 설정"""

    # AIS 설정
    aisstream_api_key: Optional[str] = None
    enable_real_ais: bool = True

    # 시뮬레이션 설정
    update_interval_sec: int = 10
    simulation_speed_multiplier: float = 1.0  # 1.0 = 실시간

    # 로깅 설정
    log_level: str = "INFO"
    log_file: Optional[str] = None

    # Dead Reckoning 설정
    course_uncertainty_deg: float = 2.0
    speed_uncertainty_knots: float = 0.1

    # 통신 설정
    default_comm_type: str = "VSAT"  # 'AIS_TERRESTRIAL', 'VSAT', 'LEO_SATELLITE'

    @classmethod
    def from_env(cls) -> 'SimulatorConfig':
        """환경 변수에서 설정 로드"""

        return cls(
            aisstream_api_key=os.getenv("AISSTREAM_API_KEY"),
            enable_real_ais=os.getenv("ENABLE_REAL_AIS", "true").lower() == "true",
            update_interval_sec=int(os.getenv("SIMULATION_UPDATE_INTERVAL_SEC", "10")),
            log_level=os.getenv("LOG_LEVEL", "INFO")
        )


# 전역 설정 인스턴스
config = SimulatorConfig.from_env()
