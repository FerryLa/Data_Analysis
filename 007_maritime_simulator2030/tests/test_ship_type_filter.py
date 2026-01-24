"""
선박 타입 필터링 테스트
LNG 탱커를 자동으로 감지하는지 확인
"""
import asyncio
import websockets
import json
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

async def test_ship_type_filtering():
    """선박 타입 필터링 테스트"""

    api_key = os.getenv('AISSTREAM_API_KEY')

    if not api_key or api_key == "your_api_key_here":
        print("❌ API 키가 설정되지 않았습니다!")
        return

    print(f"✅ API 키 로드됨: {api_key[:10]}...")

    uri = "wss://stream.aisstream.io/v0/stream"

    # LNG/Tanker 선박 타입 코드
    LNG_SHIP_TYPES = {80, 81, 82, 83, 84, 85, 86, 87, 88, 89}

    print(f"\n🔍 탐지 대상 선박 타입 코드: {LNG_SHIP_TYPES}")
    print(f"  (80-89: Tanker, 특히 84: Liquefied Gas Tanker)")

    try:
        print(f"\n🔌 WebSocket 연결 시도: {uri}")

        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket 연결 성공!")

            # 구독 메시지 전송
            subscribe_message = {
                "APIKey": api_key,
                "BoundingBoxes": [[[-90, -180], [90, 180]]],  # 전 세계
                "FilterMessageTypes": ["ShipStaticData"]  # Static Data만 수신
            }

            print(f"\n📡 구독 메시지 전송:")
            print(f"  - BoundingBox: 전 세계")
            print(f"  - MessageTypes: ShipStaticData만")

            subscribe_message_json = json.dumps(subscribe_message)
            await websocket.send(subscribe_message_json)
            print("✅ 구독 메시지 전송 완료!")

            print("\n⏳ LNG 탱커 탐지 중... (60초 동안 모니터링)")
            print("=" * 80)

            message_count = 0
            lng_count = 0
            other_count = 0
            lng_vessels = {}  # MMSI -> vessel info
            ship_type_stats = {}  # ship_type -> count

            # 60초 동안 메시지 수신
            try:
                async with asyncio.timeout(60):
                    async for message_json in websocket:
                        message_count += 1

                        try:
                            message = json.loads(message_json)

                            if "Message" in message and "ShipStaticData" in message["Message"]:
                                static = message["Message"]["ShipStaticData"]
                                mmsi = str(message["MetaData"]["MMSI"])
                                ship_type = static.get("Type", 0)
                                name = static.get("Name", "").strip()
                                callsign = static.get("CallSign", "").strip()

                                # 통계
                                ship_type_stats[ship_type] = ship_type_stats.get(ship_type, 0) + 1

                                # LNG 탱커인지 확인
                                if ship_type in LNG_SHIP_TYPES:
                                    lng_count += 1

                                    # 중복 제거 (MMSI로)
                                    if mmsi not in lng_vessels:
                                        lng_vessels[mmsi] = {
                                            'name': name,
                                            'callsign': callsign,
                                            'ship_type': ship_type
                                        }

                                        print(f"\n🎯 LNG 탱커 발견! #{len(lng_vessels)}")
                                        print(f"  ⏰ 시각: {datetime.now().strftime('%H:%M:%S')}")
                                        print(f"  🆔 MMSI: {mmsi}")
                                        print(f"  🚢 선명: {name}")
                                        print(f"  📞 호출부호: {callsign}")
                                        print(f"  🔢 선박 타입: {ship_type}")
                                        print("-" * 80)

                                        # 14척 도달 시 종료
                                        if len(lng_vessels) >= 14:
                                            print("\n✅ 목표 14척 도달! 테스트 종료")
                                            break
                                else:
                                    other_count += 1

                                # 진행 상황 (100개마다)
                                if message_count % 100 == 0:
                                    print(f"\n📊 진행 상황: 총 {message_count}개 메시지 (LNG: {len(lng_vessels)}척, 기타: {other_count}개)")

                        except json.JSONDecodeError:
                            print(f"⚠️  JSON 파싱 실패")
                        except Exception as e:
                            print(f"⚠️  메시지 처리 오류: {e}")

            except asyncio.TimeoutError:
                print("\n⏱️  60초 타임아웃 - 테스트 종료")

            # 최종 통계
            print("\n" + "=" * 80)
            print("📊 최종 통계")
            print("=" * 80)
            print(f"총 수신 메시지: {message_count}개")
            print(f"발견된 LNG 탱커: {len(lng_vessels)}척")
            print(f"LNG 타입 메시지: {lng_count}개")
            print(f"기타 타입 메시지: {other_count}개")

            # 발견된 LNG 탱커 목록
            if len(lng_vessels) > 0:
                print(f"\n✅ 발견된 LNG 탱커 목록:")
                for i, (mmsi, info) in enumerate(lng_vessels.items(), 1):
                    print(f"  {i}. {info['name']} (MMSI: {mmsi}, Type: {info['ship_type']})")
            else:
                print(f"\n⚠️  LNG 탱커를 찾지 못했습니다.")

            # 선박 타입 분포 (상위 10개)
            print(f"\n📈 선박 타입 분포 (상위 10개):")
            sorted_types = sorted(ship_type_stats.items(), key=lambda x: x[1], reverse=True)[:10]
            for ship_type, count in sorted_types:
                type_desc = "🎯 LNG/Tanker" if ship_type in LNG_SHIP_TYPES else ""
                print(f"  Type {ship_type}: {count}개 {type_desc}")

    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ WebSocket 연결 실패 - 잘못된 상태 코드: {e}")
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import sys
    import io

    # Windows 콘솔 인코딩 설정
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("=" * 80)
    print("🧪 선박 타입 필터링 테스트 - LNG 탱커 자동 감지")
    print("=" * 80)

    asyncio.run(test_ship_type_filtering())
