"""
AIS Live Data Collector — Aegean Sea
Connects to AISStream.io WebSocket API and writes incoming messages
directly to a SQLite database (ais_aegean.db).
"""

import asyncio
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import websockets
from dotenv import load_dotenv

# ── Config ────────────────────────────────────────────────────────────────────

load_dotenv()
API_KEY = os.getenv("AISSTREAM_API_KEY")

# AISStream format: [min_lat, min_lon], [max_lat, max_lon]
#
# GENİŞ TOPLAMA ALANI — cleaner.py hassas filtreyi uygular.
# Dar bounding box AISStream'den yeterli mesaj gelmemesine yol açar;
# bu nedenle tüm Ege toplanır, analiz koridoru cleaner'da kesilir:
#   → lat 36.0–38.0°N, lon 26.5–29.0°E (Bodrum–Kos–Rodos)
BOUNDING_BOX = [[36.0, 22.0], [42.0, 30.0]]

WEBSOCKET_URL = "wss://stream.aisstream.io/v0/stream"

DEFAULT_DURATION_MINUTES = 20

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "ais_aegean.db"

# ── SQLite kurulumu ───────────────────────────────────────────────────────────

def init_db(conn: sqlite3.Connection):
    """
    Tablo yoksa oluştur. IF NOT EXISTS sayesinde her çalıştırmada
    mevcut verinin üstüne yazmaz — oturumlar birikerek büyür.
    """
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ais_raw (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp_utc    TEXT    NOT NULL,
            session_id       TEXT    NOT NULL,
            mmsi             TEXT,
            ship_name        TEXT,
            ship_type_code   INTEGER,
            latitude         REAL,
            longitude        REAL,
            speed_knots      REAL,
            course_deg       REAL,
            heading_deg      REAL,
            nav_status       INTEGER,
            message_type     TEXT
        )
    """)
    # MMSI'ya index: join ve filtre sorgularını hızlandırır
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_mmsi
        ON ais_raw (mmsi)
    """)
    # Zaman sorgularına index
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_timestamp
        ON ais_raw (timestamp_utc)
    """)
    conn.commit()


def insert_row(conn: sqlite3.Connection, row: dict):
    conn.execute("""
        INSERT INTO ais_raw (
            timestamp_utc, session_id, mmsi, ship_name, ship_type_code,
            latitude, longitude, speed_knots, course_deg,
            heading_deg, nav_status, message_type
        ) VALUES (
            :timestamp_utc, :session_id, :mmsi, :ship_name, :ship_type_code,
            :latitude, :longitude, :speed_knots, :course_deg,
            :heading_deg, :nav_status, :message_type
        )
    """, row)

# ── Subscription mesajı ───────────────────────────────────────────────────────

def build_subscription():
    return {
        "APIKey": API_KEY,
        "BoundingBoxes": [BOUNDING_BOX],
        "FilterMessageTypes": ["PositionReport", "ShipStaticData"],
    }

# ── Mesaj ayrıştırıcılar ──────────────────────────────────────────────────────

def parse_position_report(msg: dict, metadata: dict, session_id: str) -> dict | None:
    pr = msg.get("Message", {}).get("PositionReport", {})
    if not pr:
        return None

    lat = pr.get("Latitude")
    lon = pr.get("Longitude")

    # AIS'te 91.0 / 181.0 "bilinmiyor" anlamına gelir
    if lat is None or lon is None or abs(lat) > 90 or abs(lon) > 180:
        return None

    return {
        "timestamp_utc":  datetime.now(timezone.utc).isoformat(),
        "session_id":     session_id,
        "mmsi":           str(metadata.get("MMSI", "")),
        "ship_name":      metadata.get("ShipName", "").strip(),
        "ship_type_code": None,
        "latitude":       lat,
        "longitude":      lon,
        "speed_knots":    pr.get("Sog"),
        "course_deg":     pr.get("Cog"),
        "heading_deg":    pr.get("TrueHeading"),
        "nav_status":     pr.get("NavigationalStatus"),
        "message_type":   "PositionReport",
    }


def parse_ship_static(msg: dict, metadata: dict, session_id: str) -> dict | None:
    ss = msg.get("Message", {}).get("ShipStaticData", {})
    if not ss:
        return None

    return {
        "timestamp_utc":  datetime.now(timezone.utc).isoformat(),
        "session_id":     session_id,
        "mmsi":           str(metadata.get("MMSI", "")),
        "ship_name":      ss.get("Name", "").strip(),
        "ship_type_code": ss.get("Type"),
        "latitude":       None,
        "longitude":      None,
        "speed_knots":    None,
        "course_deg":     None,
        "heading_deg":    None,
        "nav_status":     None,
        "message_type":   "ShipStaticData",
    }

# ── Ana toplama döngüsü ───────────────────────────────────────────────────────

async def collect(duration_minutes: int):
    if not API_KEY:
        print("HATA: AISSTREAM_API_KEY bulunamadı. .env dosyasını kontrol et.")
        sys.exit(1)

    session_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    end_time   = asyncio.get_event_loop().time() + duration_minutes * 60

    print(f"[{session_id}] Toplama başlıyor — süre: {duration_minutes} dakika")
    print(f"Bounding box : {BOUNDING_BOX}")
    print(f"Veritabanı   : {DB_PATH}\n")

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    total_messages = 0
    unique_mmsi: set[str] = set()

    try:
        while asyncio.get_event_loop().time() < end_time:
            try:
                async with websockets.connect(WEBSOCKET_URL) as ws:
                    await ws.send(json.dumps(build_subscription()))
                    print("WebSocket bağlantısı kuruldu. Veri bekleniyor...")

                    batch: list[dict] = []

                    async for raw in ws:
                        if asyncio.get_event_loop().time() >= end_time:
                            break

                        try:
                            msg = json.loads(raw)
                        except json.JSONDecodeError:
                            continue

                        msg_type = msg.get("MessageType")
                        metadata = msg.get("MetaData", {})

                        if msg_type == "PositionReport":
                            row = parse_position_report(msg, metadata, session_id)
                        elif msg_type == "ShipStaticData":
                            row = parse_ship_static(msg, metadata, session_id)
                        else:
                            continue

                        if row is None:
                            continue

                        batch.append(row)
                        total_messages += 1
                        if row["mmsi"]:
                            unique_mmsi.add(row["mmsi"])

                        # Her 50 mesajda toplu yazma (disk I/O azaltır)
                        if len(batch) >= 50:
                            for r in batch:
                                insert_row(conn, r)
                            conn.commit()
                            batch.clear()

                        if total_messages % 100 == 0:
                            elapsed = duration_minutes * 60 - (
                                end_time - asyncio.get_event_loop().time()
                            )
                            print(
                                f"  [{int(elapsed):>4}s] "
                                f"Mesaj: {total_messages:>6} | "
                                f"Tekil gemi: {len(unique_mmsi):>4} | "
                                f"Son: {row.get('ship_name') or row.get('mmsi')}"
                            )

                    # Döngü bitti — kalan batch'i yaz
                    for r in batch:
                        insert_row(conn, r)
                    conn.commit()

            except (
                websockets.exceptions.ConnectionClosed,
                websockets.exceptions.WebSocketException,
                OSError,
            ) as e:
                remaining = end_time - asyncio.get_event_loop().time()
                if remaining <= 0:
                    break
                print(f"Bağlantı kesildi ({e}). 5 saniye sonra yeniden denenecek...")
                await asyncio.sleep(5)

    finally:
        # Son kontrol sorgusu
        cursor = conn.execute("SELECT COUNT(*) FROM ais_raw WHERE session_id = ?",
                              (session_id,))
        db_count = cursor.fetchone()[0]
        conn.close()

        print(f"\nToplama tamamlandı.")
        print(f"  Toplam mesaj      : {total_messages}")
        print(f"  Tekil gemi        : {len(unique_mmsi)}")
        print(f"  DB'ye yazılan satır: {db_count}")
        print(f"  Veritabanı         : {DB_PATH}")
        print(f"  Session ID         : {session_id}")

# ── Giriş noktası ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DURATION_MINUTES

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(collect(duration))
    except KeyboardInterrupt:
        print("\nKullanıcı tarafından durduruldu.")
    finally:
        loop.close()
