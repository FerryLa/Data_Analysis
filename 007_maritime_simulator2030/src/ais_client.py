"""
AIS Stream WebSocket Client
============================

실시간 AIS 데이터를 AISStream.io로부터 수신하고 자율선박을 필터링합니다.

자율선박 5척:
- Yara Birkeland (노르웨이 완전 자율 컨테이너선)
- Marit & Therese (노르웨이 ASKO 전기 자율선)
- Prism Courage (한국 Avikus HiNAS 시험 LNG선)
- HMM Algeciras (한국 24000 TEU ULCV, 비교군)

Features:
- 비동기 WebSocket 연결 (자동 재연결)
- MMSI 기반 화이트리스트 필터링
- AIS 메시지 정규화 (Type 1, 2, 3, 5)
- 스레드 세이프 메시지 큐
- 지수 백오프 재연결 전략
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from queue import Queue
import threading
import websockets
from websockets.exceptions import ConnectionClosed
import time

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class VesselState:
    """선박 상태를 나타내는 표준화된 데이터 구조"""

    mmsi: str
    vessel_name: str
    vessel_type: str  # 'LNG', 'AMMONIA', 'SMR'

    # 위치 정보
    latitude: float
    longitude: float
    course: float  # Course Over Ground (degrees, 0-360)
    speed: float   # Speed Over Ground (knots)
    heading: Optional[float] = None  # True heading (degrees, 0-360)

    # 시간 정보
    timestamp: datetime = field(default_factory=datetime.utcnow)
    position_accuracy: int = 1  # 0=low, 1=high (from AIS)

    # 선박 제원
    length: Optional[float] = None  # meters
    width: Optional[float] = None   # meters
    draught: Optional[float] = None # meters

    # 항해 정보
    destination: Optional[str] = None
    eta: Optional[datetime] = None
    nav_status: Optional[int] = None  # 0=under way, 1=at anchor, etc.

    # 메타데이터
    is_simulated: bool = False  # True면 시뮬레이션 데이터
    data_source: str = "AIS"    # 'AIS', 'SIMULATED_AMMONIA', 'SIMULATED_SMR'

    def to_dict(self) -> Dict:
        """JSON 직렬화를 위한 딕셔너리 변환"""
        return {
            'mmsi': self.mmsi,
            'vessel_name': self.vessel_name,
            'vessel_type': self.vessel_type,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'course': self.course,
            'speed': self.speed,
            'heading': self.heading,
            'timestamp': self.timestamp.isoformat(),
            'position_accuracy': self.position_accuracy,
            'length': self.length,
            'width': self.width,
            'draught': self.draught,
            'destination': self.destination,
            'eta': self.eta.isoformat() if self.eta else None,
            'nav_status': self.nav_status,
            'is_simulated': self.is_simulated,
            'data_source': self.data_source
        }


class AISStreamClient:
    """
    AISStream WebSocket 클라이언트

    자율선박 5척의 실시간 AIS 데이터를 수신하고 정규화합니다.
    (Yara Birkeland, Marit, Therese, Prism Courage, HMM Algeciras)
    """

    # 자율선박 MMSI 리스트 (실제 선박 5척 - 2026-01-24 확인)
    # 출처: MarineTraffic, VesselFinder (2026-01-24 확인)
    AUTONOMOUS_SHIP_MMSI_LIST = [
        "257646000",  # Yara Birkeland (IMO: 9865049) - 노르웨이 완전 자율 컨테이너선
        "259005610",  # Therese (IMO: 9921788) - 노르웨이 ASKO 전기 자율선
        "258022650",  # Marit (IMO: 9921776) - 노르웨이 ASKO 전기 자율선
        "352986205",  # Prism Courage (IMO: 9888481) - 한국 Avikus HiNAS 시험 LNG선
        "440326000",  # HMM Algeciras (IMO: 9863297) - 한국 24000 TEU ULCV (비교군)
    ]

    # AIS Ship Type codes for Container/Cargo/Tanker (백업용)
    # 70-79: Cargo
    # 80-89: Tanker (including LNG, LPG)
    AUTONOMOUS_SHIP_TYPES = {70, 71, 72, 73, 74, 75, 76, 77, 78, 79,  # Cargo
                             80, 81, 82, 83, 84, 85, 86, 87, 88, 89}  # Tanker

    def __init__(
        self,
        api_key: str,
        mmsi_filter: Optional[List[str]] = None,
        message_callback: Optional[Callable[[VesselState], None]] = None,
        max_queue_size: int = 1000,
        max_vessels: int = 20,  # LNG 탱커 최대 수 (Q-Max 우선)
        use_ship_type_fallback: bool = False  # 자율선박 5척만 추적
    ):
        """
        Args:
            api_key: AISStream API 키
            mmsi_filter: 필터링할 MMSI 리스트 (None이면 AUTONOMOUS_SHIP_MMSI_LIST 사용)
            message_callback: 새 메시지 수신 시 호출될 콜백 함수
            max_queue_size: 메시지 큐 최대 크기
            max_vessels: 추적할 최대 선박 수
            use_ship_type_fallback: 자율선박 MMSI 없을 시 Cargo/Tanker 타입 필터링 사용
        """
        self.api_key = api_key
        self.autonomous_mmsi_set = set(self.AUTONOMOUS_SHIP_MMSI_LIST)  # 자율선박 MMSI (우선순위)
        self.mmsi_filter = set(mmsi_filter) if mmsi_filter else None
        self.use_ship_type_fallback = use_ship_type_fallback
        self.max_vessels = max_vessels
        self.message_callback = message_callback

        # 메시지 큐 (스레드 세이프)
        self.message_queue = Queue(maxsize=max_queue_size)

        # 연결 상태
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10

        # 선박 정보 캐시 (MMSI -> VesselState)
        self.vessel_cache: Dict[str, VesselState] = {}

        # 통계
        self.stats = {
            'messages_received': 0,
            'messages_filtered': 0,
            'parse_errors': 0,
            'last_update': None
        }

        # WebSocket 연결
        self.websocket = None
        self.running = False

    async def connect(self):
        """AISStream WebSocket 서버에 연결"""

        uri = "wss://stream.aisstream.io/v0/stream"

        # 구독 메시지 생성 (LNG 타입 필터링 - 서버 측 MMSI 필터는 작동 안함)
        subscribe_message = {
            "APIKey": self.api_key,
            "BoundingBoxes": [
                # 전 세계 범위 (필요시 특정 해역으로 제한 가능)
                [[-90, -180], [90, 180]]
            ],
            "FilterMessageTypes": ["PositionReport", "ShipStaticData"]
            # FiltersShipMMSI는 작동하지 않으므로 클라이언트 측에서 필터링
        }

        try:
            logger.info(f"AISStream 서버에 연결 중... {uri}")

            async with websockets.connect(uri) as websocket:
                self.websocket = websocket
                self.is_connected = True
                self.reconnect_attempts = 0

                # 구독 메시지 전송
                await websocket.send(json.dumps(subscribe_message))
                logger.info(f"✅ 자율선박 추적 시작 (최대 {self.max_vessels}척)")
                logger.info(f"📡 우선 추적: 자율선박 {len(self.autonomous_mmsi_set)}척")
                logger.info(f"   - Yara Birkeland (257646000), Marit (258022650), Therese (259005610)")
                logger.info(f"   - Prism Courage (352986205), HMM Algeciras (440326000)")
                logger.info(f"📡 백업 필터: Cargo/Tanker 타입 (70-89) - 자율선박 없을 시 일반 화물선/탱커 추적")

                # 메시지 수신 루프
                async for message in websocket:
                    if not self.running:
                        break

                    try:
                        await self._process_message(message)
                    except Exception as e:
                        logger.error(f"메시지 처리 중 오류: {e}")
                        self.stats['parse_errors'] += 1

        except ConnectionClosed as e:
            logger.warning(f"WebSocket 연결 종료: {e}")
            self.is_connected = False

        except Exception as e:
            logger.error(f"WebSocket 연결 오류: {e}")
            self.is_connected = False

    async def _process_message(self, raw_message: str):
        """수신된 AIS 메시지를 처리하고 정규화"""

        self.stats['messages_received'] += 1

        try:
            data = json.loads(raw_message)

            # 메시지 타입 확인
            message_type = data.get("MessageType")

            if message_type == "PositionReport":
                await self._handle_position_report(data)

            elif message_type == "ShipStaticData":
                await self._handle_static_data(data)

        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 실패: {e}")
            self.stats['parse_errors'] += 1

    async def _handle_position_report(self, data: Dict):
        """위치 보고 메시지 처리 (AIS Type 1, 2, 3)"""

        try:
            metadata = data.get("MetaData", {})
            message = data.get("Message", {}).get("PositionReport", {})

            mmsi = str(metadata.get("MMSI", ""))
            ship_type = message.get("Type", 0)  # AIS Ship Type code

            # 필터링 로직: 자율선박 우선, 없으면 Cargo/Tanker 타입
            is_autonomous = mmsi in self.autonomous_mmsi_set
            is_cargo_tanker_type = ship_type in self.AUTONOMOUS_SHIP_TYPES if self.use_ship_type_fallback else False

            # 자율선박이 아니고 Cargo/Tanker 타입도 아니면 필터링
            if not is_autonomous and not is_cargo_tanker_type:
                self.stats['messages_filtered'] += 1
                return

            # 최대 선박 수 제한 (자율선박은 항상 허용)
            if not is_autonomous and len(self.vessel_cache) >= self.max_vessels:
                self.stats['messages_filtered'] += 1
                return

            # VesselState 객체 생성 또는 업데이트
            if mmsi in self.vessel_cache:
                vessel = self.vessel_cache[mmsi]
            else:
                vessel_name = metadata.get("ShipName", f"Unknown-{mmsi}").strip()
                vessel = VesselState(
                    mmsi=mmsi,
                    vessel_name=vessel_name,
                    vessel_type="Autonomous Ship" if is_autonomous else "Cargo/Tanker",
                    latitude=0.0,
                    longitude=0.0,
                    course=0.0,
                    speed=0.0,
                    data_source="AIS"
                )
                self.vessel_cache[mmsi] = vessel

                # 자율선박 발견 시 특별 로그
                if is_autonomous:
                    logger.info(f"🎯 자율선박 발견: {vessel_name} (MMSI: {mmsi}) - 총 {len([v for v in self.vessel_cache.values() if 'Autonomous' in v.vessel_type])}/5척")
                else:
                    logger.info(f"📦 화물선/탱커 발견: {vessel_name} (MMSI: {mmsi}, Type: {ship_type})")

            # 위치 정보 업데이트
            new_latitude = message.get("Latitude", vessel.latitude)
            new_longitude = message.get("Longitude", vessel.longitude)

            # 유효하지 않은 위치 데이터 필터링 (0.0, 0.0은 무효한 좌표)
            if new_latitude == 0.0 and new_longitude == 0.0:
                self.stats['messages_filtered'] += 1
                return

            vessel.latitude = new_latitude
            vessel.longitude = new_longitude
            vessel.course = message.get("Cog", vessel.course)  # Course Over Ground
            vessel.speed = message.get("Sog", vessel.speed)    # Speed Over Ground
            vessel.heading = message.get("TrueHeading")
            vessel.nav_status = message.get("NavigationalStatus")
            vessel.position_accuracy = message.get("PositionAccuracy", 1)
            vessel.timestamp = datetime.utcnow()

            # 메시지 큐에 추가
            if not self.message_queue.full():
                self.message_queue.put(vessel)
            else:
                logger.warning("메시지 큐가 가득 참. 오래된 메시지 삭제 중...")
                self.message_queue.get()  # 가장 오래된 메시지 제거
                self.message_queue.put(vessel)

            # 콜백 호출
            if self.message_callback:
                self.message_callback(vessel)

            self.stats['last_update'] = datetime.utcnow()

            logger.debug(
                f"위치 업데이트: {vessel.vessel_name} ({mmsi}) - "
                f"Lat: {vessel.latitude:.4f}, Lon: {vessel.longitude:.4f}, "
                f"Speed: {vessel.speed:.1f}kts, Course: {vessel.course:.1f}°"
            )

        except Exception as e:
            logger.error(f"위치 보고 처리 중 오류: {e}")

    async def _handle_static_data(self, data: Dict):
        """선박 정적 데이터 처리 (AIS Type 5)"""

        try:
            metadata = data.get("MetaData", {})
            message = data.get("Message", {}).get("ShipStaticData", {})

            mmsi = str(metadata.get("MMSI", ""))
            ship_type = message.get("Type", 0)  # AIS Ship Type code

            # 필터링 로직: 자율선박 우선, 없으면 Cargo/Tanker 타입
            is_autonomous = mmsi in self.autonomous_mmsi_set
            is_cargo_tanker_type = ship_type in self.AUTONOMOUS_SHIP_TYPES if self.use_ship_type_fallback else False

            # 자율선박이 아니고 Cargo/Tanker 타입도 아니면 필터링
            if not is_autonomous and not is_cargo_tanker_type:
                return

            # 최대 선박 수 제한 (자율선박은 항상 허용)
            if not is_autonomous and len(self.vessel_cache) >= self.max_vessels:
                return

            # 선박 정보 업데이트
            if mmsi in self.vessel_cache:
                vessel = self.vessel_cache[mmsi]
            else:
                # 새 선박 생성
                ship_name = message.get("Name", f"Unknown-{mmsi}").strip()
                vessel = VesselState(
                    mmsi=mmsi,
                    vessel_name=ship_name,
                    vessel_type="Autonomous Ship" if is_autonomous else "Cargo/Tanker",
                    latitude=0.0,
                    longitude=0.0,
                    course=0.0,
                    speed=0.0,
                    data_source="AIS"
                )
                self.vessel_cache[mmsi] = vessel

                # 자율선박 발견 시 특별 로그
                if is_autonomous:
                    auto_count = len([v for v in self.vessel_cache.values() if 'Autonomous' in v.vessel_type])
                    logger.info(f"🎯 자율선박 정보 수신: {ship_name} (MMSI: {mmsi}, IMO: {message.get('Imo', 'N/A')}) - 총 {auto_count}/5척")
                else:
                    logger.info(f"📦 화물선/탱커 정보 수신: {ship_name} (MMSI: {mmsi}, Type: {ship_type})")

            # 선박 제원 업데이트
            dim = message.get("Dimension", {})
            vessel.length = dim.get("A", 0) + dim.get("B", 0) if dim else None
            vessel.width = dim.get("C", 0) + dim.get("D", 0) if dim else None
            vessel.draught = message.get("Draught")
            vessel.destination = message.get("Destination", "").strip()

            # ETA 파싱 (MMDDHHMM 형식)
            eta_raw = message.get("Eta")
            if eta_raw:
                try:
                    month = eta_raw.get("Month", 0)
                    day = eta_raw.get("Day", 0)
                    hour = eta_raw.get("Hour", 0)
                    minute = eta_raw.get("Minute", 0)

                    if month > 0 and day > 0:
                        now = datetime.utcnow()
                        vessel.eta = datetime(
                            year=now.year,
                            month=month,
                            day=day,
                            hour=hour,
                            minute=minute
                        )
                except Exception as e:
                    logger.warning(f"ETA 파싱 실패: {e}")

            logger.info(
                f"선박 정보 업데이트: {vessel.vessel_name} ({mmsi}) - "
                f"목적지: {vessel.destination}, ETA: {vessel.eta}"
            )

        except Exception as e:
            logger.error(f"정적 데이터 처리 중 오류: {e}")

    async def reconnect_with_backoff(self):
        """지수 백오프를 사용한 재연결 로직"""

        while self.running and self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1

            # 지수 백오프 계산 (최대 60초)
            backoff_time = min(2 ** self.reconnect_attempts, 60)

            logger.warning(
                f"재연결 시도 {self.reconnect_attempts}/{self.max_reconnect_attempts} "
                f"({backoff_time}초 후)"
            )

            await asyncio.sleep(backoff_time)

            try:
                await self.connect()
                if self.is_connected:
                    logger.info("재연결 성공!")
                    return
            except Exception as e:
                logger.error(f"재연결 실패: {e}")

        logger.error("최대 재연결 시도 횟수 초과. 클라이언트 종료.")
        self.running = False

    def start(self):
        """비동기 클라이언트를 별도 스레드에서 시작"""

        self.running = True

        def run_async_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            while self.running:
                try:
                    loop.run_until_complete(self.connect())
                except Exception as e:
                    logger.error(f"WebSocket 실행 오류: {e}")

                # 연결이 끊어졌을 때 재연결 시도
                if self.running and not self.is_connected:
                    loop.run_until_complete(self.reconnect_with_backoff())

            loop.close()

        # 백그라운드 스레드에서 실행
        thread = threading.Thread(target=run_async_loop, daemon=True)
        thread.start()

        logger.info("AIS 클라이언트 시작됨 (백그라운드 스레드)")

    def stop(self):
        """클라이언트 종료"""
        logger.info("AIS 클라이언트 종료 중...")
        self.running = False
        self.is_connected = False

    def get_latest_vessels(self) -> Dict[str, VesselState]:
        """현재 캐시된 모든 선박 상태 반환"""
        return self.vessel_cache.copy()

    def get_vessel_by_mmsi(self, mmsi: str) -> Optional[VesselState]:
        """특정 MMSI의 선박 상태 반환"""
        return self.vessel_cache.get(mmsi)

    def get_statistics(self) -> Dict:
        """클라이언트 통계 반환"""
        return {
            **self.stats,
            'is_connected': self.is_connected,
            'reconnect_attempts': self.reconnect_attempts,
            'vessels_tracked': len(self.vessel_cache),
            'queue_size': self.message_queue.qsize()
        }


# ============================================================================
# 사용 예시
# ============================================================================

if __name__ == "__main__":

    import os

    # 환경 변수에서 API 키 로드
    API_KEY = os.getenv("AISSTREAM_API_KEY", "YOUR_API_KEY_HERE")

    if API_KEY == "YOUR_API_KEY_HERE":
        logger.error("AISStream API 키를 설정해주세요!")
        logger.error("export AISSTREAM_API_KEY='your-actual-key'")
        exit(1)

    # 콜백 함수 정의
    def on_vessel_update(vessel: VesselState):
        print(f"\n[새 업데이트] {vessel.vessel_name}")
        print(f"  위치: {vessel.latitude:.4f}°N, {vessel.longitude:.4f}°E")
        print(f"  속도: {vessel.speed:.1f} knots")
        print(f"  침로: {vessel.course:.1f}°")
        print(f"  시간: {vessel.timestamp.isoformat()}")

    # 클라이언트 생성 및 시작
    client = AISStreamClient(
        api_key=API_KEY,
        message_callback=on_vessel_update
    )

    client.start()

    try:
        # 메인 루프 (60초 동안 실행 후 통계 출력)
        logger.info("AIS 데이터 수신 중... (Ctrl+C로 종료)")

        for i in range(60):
            time.sleep(1)

            # 10초마다 통계 출력
            if i % 10 == 0:
                stats = client.get_statistics()
                logger.info(
                    f"통계 - 수신: {stats['messages_received']}, "
                    f"필터링: {stats['messages_filtered']}, "
                    f"추적 중: {stats['vessels_tracked']}척"
                )

        # 최종 선박 목록 출력
        vessels = client.get_latest_vessels()
        logger.info(f"\n추적 중인 선박 {len(vessels)}척:")
        for mmsi, vessel in vessels.items():
            logger.info(f"  {vessel.vessel_name} ({mmsi})")

    except KeyboardInterrupt:
        logger.info("\n사용자에 의해 중단됨")

    finally:
        client.stop()
        logger.info("프로그램 종료")
