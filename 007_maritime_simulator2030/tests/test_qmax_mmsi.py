"""
Q-Max MMSI 리스트로 실제 선박 추적 테스트
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

# Q-Max MMSI 리스트 (src/ais_client.py와 동일)
QMAX_MMSI_LIST = [
    "538003212",  # Mozah
    "538003354",  # Aamira
    "538003295",  # Al Samriya
    "538003301",  # Bu Samra
    "538003356",  # Al Mayeda
    "538003365",  # Mekaines
    "538003357",  # Al Mafyar
    "538003300",  # Umm Slal
    "538003293",  # Al Ghuwairiya
    "538003294",  # Lijmiliya
    "538003355",  # Al Dafna
    "538003348",  # Shagra
    "538003346",  # Zarga
    "538003362",  # Rasheeda
]

async def test_qmax_tracking():
    """Q-Max 선박 추적 테스트"""

    api_key = os.getenv('AISSTREAM_API_KEY')

    if not api_key or api_key == "your_api_key_here":
        print("❌ API 키가 설정되지 않았습니다!")
        return

    print(f"✅ API 키 로드됨: {api_key[:10]}...")

    uri = "wss://stream.aisstream.io/v0/stream"

    print(f"\n🔍 추적 대상 Q-Max 선박: {len(QMAX_MMSI_LIST)}척")
    print(f"MMSI 리스트: {', '.join(QMAX_MMSI_LIST[:5])}... (총 {len(QMAX_MMSI_LIST)}척)")

    try:
        print(f"\n🔌 WebSocket 연결 시도: {uri}")

        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket 연결 성공!")

            # 구독 메시지 전송
            subscribe_message = {
                "APIKey": api_key,
                "BoundingBoxes": [[[-90, -180], [90, 180]]],  # 전 세계
                "FilterMessageTypes": ["PositionReport", "ShipStaticData"]
            }

            print(f"\n📡 구독 메시지 전송:")
            print(f"  - BoundingBox: 전 세계")
            print(f"  - MessageTypes: PositionReport, ShipStaticData")

            subscribe_message_json = json.dumps(subscribe_message)
            await websocket.send(subscribe_message_json)
            print("✅ 구독 메시지 전송 완료!")

            print("\n⏳ Q-Max 선박 탐지 중... (90초 동안 모니터링)")
            print("=" * 80)

            message_count = 0
            qmax_found = {}  # MMSI -> vessel info
            qmax_message_count = 0
            other_count = 0

            # 90초 동안 메시지 수신
            try:
                async with asyncio.timeout(90):
                    async for message_json in websocket:
                        message_count += 1

                        try:
                            message = json.loads(message_json)

                            msg_type = message.get("MessageType", "Unknown")
                            mmsi = None

                            if "MetaData" in message and "MMSI" in message["MetaData"]:
                                mmsi = str(message["MetaData"]["MMSI"])

                            # Q-Max 선박인지 확인
                            if mmsi and mmsi in QMAX_MMSI_LIST:
                                qmax_message_count += 1

                                # 처음 발견한 선박
                                if mmsi not in qmax_found:
                                    name = "Unknown"

                                    if msg_type == "PositionReport":
                                        name = message.get("MetaData", {}).get("ShipName", "Unknown")
                                    elif msg_type == "ShipStaticData" and "Message" in message and "ShipStaticData" in message["Message"]:
                                        name = message["Message"]["ShipStaticData"].get("Name", "Unknown").strip()

                                    qmax_found[mmsi] = {
                                        'name': name,
                                        'first_seen': msg_type
                                    }

                                    print(f"\n🎯 Q-Max 발견! #{len(qmax_found)}/14")
                                    print(f"  ⏰ 시각: {datetime.now().strftime('%H:%M:%S')}")
                                    print(f"  🆔 MMSI: {mmsi}")
                                    print(f"  🚢 선명: {name}")
                                    print(f"  📋 메시지 타입: {msg_type}")

                                    # 위치 정보 출력 (PositionReport인 경우)
                                    if msg_type == "PositionReport" and "Message" in message and "PositionReport" in message["Message"]:
                                        pos = message["Message"]["PositionReport"]
                                        lat = pos.get("Latitude")
                                        lon = pos.get("Longitude")
                                        sog = pos.get("Sog")
                                        cog = pos.get("Cog")

                                        if lat and lon:
                                            print(f"  📍 위치: ({lat:.4f}, {lon:.4f})")
                                            print(f"  🧭 COG: {cog:.1f}° | SOG: {sog:.1f} knots")

                                    print("-" * 80)

                                    # 14척 모두 발견하면 종료
                                    if len(qmax_found) >= 14:
                                        print("\n✅ 모든 Q-Max 선박 발견! 테스트 종료")
                                        break
                            else:
                                other_count += 1

                            # 진행 상황 (1000개마다)
                            if message_count % 1000 == 0:
                                print(f"\n📊 진행 상황: 총 {message_count}개 메시지 (Q-Max 발견: {len(qmax_found)}/14척, Q-Max 메시지: {qmax_message_count}개)")

                        except json.JSONDecodeError:
                            print(f"⚠️  JSON 파싱 실패")
                        except Exception as e:
                            print(f"⚠️  메시지 처리 오류: {e}")

            except asyncio.TimeoutError:
                print("\n⏱️  90초 타임아웃 - 테스트 종료")

            # 최종 통계
            print("\n" + "=" * 80)
            print("📊 최종 통계")
            print("=" * 80)
            print(f"총 수신 메시지: {message_count}개")
            print(f"발견된 Q-Max 선박: {len(qmax_found)}/14척")
            print(f"Q-Max 메시지 수: {qmax_message_count}개")
            print(f"기타 선박 메시지: {other_count}개")

            # 발견된 Q-Max 선박 목록
            if len(qmax_found) > 0:
                print(f"\n✅ 발견된 Q-Max 선박:")
                for i, (mmsi, info) in enumerate(qmax_found.items(), 1):
                    print(f"  {i}. {info['name']} (MMSI: {mmsi})")
            else:
                print(f"\n⚠️  Q-Max 선박을 찾지 못했습니다.")
                print(f"가능한 원인:")
                print(f"  1. Q-Max 선박이 현재 AIS 신호를 송출하지 않음")
                print(f"  2. 선박이 항만에 정박 중이거나 통신 범위 밖")
                print(f"  3. 일시적인 통신 장애")

            # 발견하지 못한 선박 목록
            if len(qmax_found) < 14:
                print(f"\n❌ 발견하지 못한 Q-Max 선박:")
                found_mmsi = set(qmax_found.keys())
                missing = set(QMAX_MMSI_LIST) - found_mmsi
                for mmsi in missing:
                    print(f"  - MMSI: {mmsi}")

    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ WebSocket 연결 실패: {e}")
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
    print("🧪 Q-Max 선박 실시간 추적 테스트")
    print("=" * 80)

    asyncio.run(test_qmax_tracking())
