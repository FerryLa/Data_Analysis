"""
AIS WebSocket 연결 테스트 스크립트
실제 AISStream에서 데이터를 받아오는지 확인
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

async def test_ais_stream():
    """AISStream WebSocket 연결 테스트"""

    api_key = os.getenv('AISSTREAM_API_KEY')

    if not api_key or api_key == "your_api_key_here":
        print("❌ API 키가 설정되지 않았습니다!")
        print(f"현재 API 키: {api_key}")
        return

    print(f"✅ API 키 로드됨: {api_key[:10]}...")

    uri = "wss://stream.aisstream.io/v0/stream"

    # Q-Max MMSI 리스트 (2026-01-24 웹 검색으로 확인된 실제 MMSI)
    qmax_mmsi = [
        "538003212",  # Mozah (IMO: 9337755)
        "538003354",  # Aamira (IMO: 9443401)
        "538003295",  # Al Samriya (IMO: 9388821)
        "538003301",  # Bu Samra (IMO: 9388833)
        "538003356",  # Al Mayeda (IMO: 9397298)
        "538003365",  # Mekaines (IMO: 9397303)
        "538003357",  # Al Mafyar (IMO: 9397315)
        "538003300",  # Umm Slal (IMO: 9372731)
        "538003293",  # Al Ghuwairiya (IMO: 9372743)
        "538003294",  # Lijmiliya (IMO: 9388819)
        "538003355",  # Al Dafna (IMO: 9443683)
        "538003348",  # Shagra (IMO: 9418365)
        "538003346",  # Zarga (IMO: 9431214)
        "538003362",  # Rasheeda (IMO: 9443413)
    ]

    print(f"\n🔍 추적 대상 MMSI: {len(qmax_mmsi)}척")
    print(f"MMSI 리스트: {', '.join(qmax_mmsi[:5])}...")

    try:
        print(f"\n🔌 WebSocket 연결 시도: {uri}")

        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket 연결 성공!")

            # 구독 메시지 전송 (MMSI 필터 제거 테스트)
            subscribe_message = {
                "APIKey": api_key,
                "BoundingBoxes": [[[-90, -180], [90, 180]]],  # 전 세계
                "FilterMessageTypes": ["PositionReport", "ShipStaticData"],
                # "FiltersShipMMSI": qmax_mmsi  # 테스트용으로 주석 처리
            }

            print(f"\n📡 구독 메시지 전송:")
            print(f"  - BoundingBox: 전 세계 (-90,-180) ~ (90,180)")
            print(f"  - MessageTypes: PositionReport, ShipStaticData")
            print(f"  - MMSI 필터: 없음 (모든 선박 수신 테스트)")

            subscribe_message_json = json.dumps(subscribe_message)
            await websocket.send(subscribe_message_json)
            print("✅ 구독 메시지 전송 완료!")

            print("\n⏳ 메시지 수신 대기 중... (60초 동안 모니터링)")
            print("=" * 80)

            message_count = 0
            qmax_count = 0
            other_count = 0
            vessel_mmsi_seen = set()

            # 60초 동안 메시지 수신
            try:
                async with asyncio.timeout(60):
                    async for message_json in websocket:
                        message_count += 1

                        try:
                            message = json.loads(message_json)

                            # 메시지 타입 확인
                            msg_type = message.get("MessageType", "Unknown")

                            # MMSI 추출
                            mmsi = None
                            if "MetaData" in message and "MMSI" in message["MetaData"]:
                                mmsi = str(message["MetaData"]["MMSI"])
                            elif "Message" in message and "UserID" in message["Message"]:
                                mmsi = str(message["Message"]["UserID"])

                            vessel_mmsi_seen.add(mmsi)

                            # Q-Max 선박인지 확인
                            is_qmax = mmsi in qmax_mmsi

                            if is_qmax:
                                qmax_count += 1
                                print(f"\n🎯 Q-Max 발견! #{qmax_count}")
                                print(f"  ⏰ 시각: {datetime.now().strftime('%H:%M:%S')}")
                                print(f"  🆔 MMSI: {mmsi}")
                                print(f"  📋 메시지 타입: {msg_type}")

                                # Position Report 상세 정보
                                if msg_type == "PositionReport" and "Message" in message and "PositionReport" in message["Message"]:
                                    pos = message["Message"]["PositionReport"]
                                    lat = pos.get("Latitude")
                                    lon = pos.get("Longitude")
                                    cog = pos.get("Cog")
                                    sog = pos.get("Sog")

                                    print(f"  📍 위치: ({lat:.4f}, {lon:.4f})")
                                    print(f"  🧭 COG: {cog:.1f}° | SOG: {sog:.1f} knots")

                                # Ship Static Data 상세 정보
                                elif msg_type == "ShipStaticData" and "Message" in message and "ShipStaticData" in message["Message"]:
                                    static = message["Message"]["ShipStaticData"]
                                    name = static.get("Name", "").strip()
                                    callsign = static.get("CallSign", "").strip()

                                    print(f"  🚢 선명: {name}")
                                    print(f"  📞 호출부호: {callsign}")

                                print("-" * 80)
                            else:
                                other_count += 1

                                # 처음 10개 메시지는 상세 출력
                                if message_count <= 10:
                                    print(f"\n📦 메시지 #{message_count} (기타 선박)")
                                    print(f"  🆔 MMSI: {mmsi}")
                                    print(f"  📋 타입: {msg_type}")

                                # 이후는 100개마다 요약
                                elif message_count % 100 == 0:
                                    print(f"\n📊 진행 상황: 총 {message_count}개 메시지 수신 (Q-Max: {qmax_count}, 기타: {other_count})")

                        except json.JSONDecodeError:
                            print(f"⚠️  JSON 파싱 실패: {message_json[:100]}")
                        except Exception as e:
                            print(f"⚠️  메시지 처리 오류: {e}")

            except asyncio.TimeoutError:
                print("\n⏱️  60초 타임아웃 - 테스트 종료")

            # 최종 통계
            print("\n" + "=" * 80)
            print("📊 최종 통계")
            print("=" * 80)
            print(f"총 수신 메시지: {message_count}개")
            print(f"Q-Max 선박 메시지: {qmax_count}개")
            print(f"기타 선박 메시지: {other_count}개")
            print(f"고유 MMSI 수: {len(vessel_mmsi_seen)}개")

            if qmax_count > 0:
                print(f"\n✅ Q-Max 선박 추적 성공!")
            else:
                print(f"\n⚠️  Q-Max 선박을 찾지 못했습니다.")
                print(f"가능한 원인:")
                print(f"  1. Q-Max 선박이 현재 AIS 신호를 송출하지 않음")
                print(f"  2. MMSI 번호가 변경되었을 수 있음")
                print(f"  3. 선박이 항만에 정박 중이거나 통신 범위 밖")

                if len(vessel_mmsi_seen) > 0:
                    print(f"\n💡 수신된 MMSI 샘플 (처음 10개):")
                    for i, mmsi in enumerate(list(vessel_mmsi_seen)[:10], 1):
                        print(f"  {i}. {mmsi}")

    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ WebSocket 연결 실패 - 잘못된 상태 코드: {e}")
        print(f"API 키가 올바른지 확인하세요!")

    except websockets.exceptions.WebSocketException as e:
        print(f"❌ WebSocket 오류: {e}")

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
    print("🧪 AISStream WebSocket 연결 테스트")
    print("=" * 80)

    asyncio.run(test_ais_stream())
