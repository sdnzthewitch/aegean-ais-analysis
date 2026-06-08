"""
AIS Live Data Collector — Aegean Sea
Connects to AISStream.io WebSocket API and writes incoming messages to CSV.
"""

import asyncio
import json
import csv
import os
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path

import websockets
from dotenv import load_dotenv

# ── Config ────────────────────────────────────────────────────────────────────

load_dotenv()
API_KEY = os.getenv("AISSTREAM_API_KEY")

# Aegean Sea bounding box: [min_lon, min_lat], [max_lon, max_lat]
# Batı Ege (Yunanistan kıyıları) ile Doğu Ege (Türkiye kıyıları) arası tam kapsam
BOUNDING_BOX = [[36.0, 22.0], [41.5, 29.0]]  # [min_lat, min_lon], [max_lat, max_lon]

WEBSOCKET_URL = "wss://stream.aisstream.io/v0/stream"

# Varsayılan toplama süresi: 20 dakika (test için). Daha uzun için argüman geç.
DEFAULT_DURATION_MINUTES = 20

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# CSV sütunları — her satır bir AIS mesajı
CSV_COLUMNS = [
    "timestamp_utc",
    "mmsi",
    "ship_name",
    "ship_type_code",
    "latitude",
    "longitude",
    "speed_knots",
    "course_deg",
    "heading_deg",
    "nav_status",
    "message_type",
]

# ── Subscription mesajı ───────────────────────────────────────────────────────

def build_subscription():
    """AISStream.io'ya gönderilecek filtre mesajı."""
    return {
        "APIKey": API_KEY,
        "BoundingBoxes": [BOUNDING_BOX],
        # Sadece konum ve statik veri mesajlarını istiyoruz
        "FilterMessageTypes": ["PositionReport", "ShipStaticData"],
    }

# ── Mesaj ayrıştırıcılar ──────────────────────────────────────────────────────

def parse_position_report(msg: dict, metadata: dict) -> dict | None:
    """PositionReport (tip 1/2/3) → düz satır."""
    pr = msg.get("Message", {}).get("PositionReport", {})
    if not pr:
        return None

    lat = pr.get("Latitude")
    lon = pr.get("Longitude")

    # Geçersiz koordinat kontrolü — AIS'te 91.0/181.0 "veri yok" anlamına gelir
    if lat is None or lon is None or abs(lat) > 90 or abs(lon) > 180:
        return None

    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "mmsi": metadata.get("MMSI"),
        "ship_name": metadata.get("ShipName", "").strip(),
        "ship_type_code": None,          # PositionReport'ta tip yok; join edilecek
        "latitude": lat,
        "longitude": lon,
        "speed_knots": pr.get("Sog"),    # Speed Over Ground
        "course_deg": pr.get("Cog"),     # Course Over Ground
        "heading_deg": pr.get("TrueHeading"),
        "nav_status": pr.get("NavigationalStatus"),
        "message_type": "PositionReport",
    }

def parse_ship_static(msg: dict, metadata: dict) -> dict | None:
    """ShipStaticData (tip 5/24) → düz satır (konum içermez)."""
    ss = msg.get("Message", {}).get("ShipStaticData", {})
    if not ss:
        return None

    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "mmsi": metadata.get("MMSI"),
        "ship_name": ss.get("Name", "").strip(),
        "ship_type_code": ss.get("Type"),
        "latitude": None,
        "longitude": None,
        "speed_knots": None,
        "course_deg": None,
        "heading_deg": None,
        "nav_status": None,
        "message_type": "ShipStaticData",
    }

# ── CSV yardımcıları ─────────────────────────────────────────────────────────

def open_csv_writer(filepath: Path):
    """CSV dosyasını aç, başlık satırını yaz."""
    f = open(filepath, "w", newline="", encoding="utf-8")
    writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
    writer.writeheader()
    f.flush()
    return f, writer

# ── Ana toplama döngüsü ───────────────────────────────────────────────────────

async def collect(duration_minutes: int):
    if not API_KEY:
        print("HATA: AISSTREAM_API_KEY bulunamadı. .env dosyasını kontrol et.")
        sys.exit(1)

    session_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    csv_path = OUTPUT_DIR / f"ais_aegean_{session_id}.csv"

    print(f"[{session_id}] Toplama başlıyor — süre: {duration_minutes} dakika")
    print(f"Bounding box: {BOUNDING_BOX}")
    print(f"Çıktı dosyası: {csv_path}\n")

    end_time = asyncio.get_event_loop().time() + duration_minutes * 60

    total_messages = 0
    unique_mmsi: set[str] = set()

    csv_file, writer = open_csv_writer(csv_path)

    try:
        while asyncio.get_event_loop().time() < end_time:
            try:
                async with websockets.connect(WEBSOCKET_URL) as ws:
                    await ws.send(json.dumps(build_subscription()))
                    print("WebSocket bağlantısı kuruldu. Veri bekleniyor...")

                    last_message_time = asyncio.get_event_loop().time()
                    first_timeout = True

                    while asyncio.get_event_loop().time() < end_time:
                        try:
                            raw = await asyncio.wait_for(ws.recv(), timeout=15)
                        except asyncio.TimeoutError:
                            if total_messages == 0 and first_timeout:
                                print("Henüz Aegean bölgesinden veri gelmedi; bağlantı kurulmuş, izleme sürüyor...")
                                first_timeout = False
                            elif total_messages > 0:
                                print("15 saniyede yeni mesaj gelmedi; bağlantı açık, bekleniyor...")
                            continue

                        # Süre doldu mu?
                        if asyncio.get_event_loop().time() >= end_time:
                            break

                        try:
                            msg = json.loads(raw)
                        except json.JSONDecodeError:
                            continue

                        msg_type = msg.get("MessageType")
                        metadata = msg.get("MetaData", {})

                        if msg_type == "PositionReport":
                            row = parse_position_report(msg, metadata)
                        elif msg_type == "ShipStaticData":
                            row = parse_ship_static(msg, metadata)
                        else:
                            continue

                        if row is None:
                            continue

                        writer.writerow(row)
                        total_messages += 1
                        csv_file.flush()
                        last_message_time = asyncio.get_event_loop().time()

                        mmsi = str(row["mmsi"] or "")
                        if mmsi:
                            unique_mmsi.add(mmsi)

                        # Her 100 mesajda bir canlı log
                        if total_messages % 100 == 0:
                            elapsed = duration_minutes * 60 - (end_time - asyncio.get_event_loop().time())
                            print(
                                f"  [{int(elapsed):>4}s] "
                                f"Mesaj: {total_messages:>6} | "
                                f"Tekil gemi: {len(unique_mmsi):>4} | "
                                f"Son: {row.get('ship_name') or row.get('mmsi')}"
                            )

            except (websockets.exceptions.ConnectionClosed,
                    websockets.exceptions.WebSocketException,
                    OSError) as e:
                remaining = end_time - asyncio.get_event_loop().time()
                if remaining <= 0:
                    break
                print(f"Bağlantı kesildi ({e}). 5 saniye sonra yeniden denenecek...")
                await asyncio.sleep(5)

    finally:
        csv_file.flush()
        csv_file.close()
        print(f"\nToplama tamamlandı.")
        print(f"  Toplam mesaj : {total_messages}")
        print(f"  Tekil gemi   : {len(unique_mmsi)}")
        print(f"  Dosya        : {csv_path}")

# ── Giriş noktası ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # İsteğe bağlı: python collector.py 60  → 60 dakika topla
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DURATION_MINUTES

    # Ctrl+C ile temiz kapanma
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(collect(duration))
    except KeyboardInterrupt:
        print("\nKullanıcı tarafından durduruldu.")
    finally:
        loop.close()
