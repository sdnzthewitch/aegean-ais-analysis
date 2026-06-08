"""
AIS Data Cleaner — Aegean Sea / Turkish Coastal Waters
1. CSV oturumlarını SQLite'a import eder
2. Türk karasuları filtresi uygular (lon >= 26.0)
3. Geçersiz / eksik kayıtları temizler
4. ShipType kodlarını okunabilir kategoriye çevirir
5. Temiz veriyi ais_clean tablosuna yazar
"""

import sqlite3
import pandas as pd
from pathlib import Path

# ── Yollar ───────────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DIR  = DATA_DIR / "raw"
DB_PATH  = DATA_DIR / "ais_aegean.db"

# ── Coğrafi kapsam sınırı ─────────────────────────────────────────────────────
# Gerçek AIS kapsam alanı: Bodrum–Marmaris–Datça–Rodos koridoru
#
# NEDEN BU SINIRLAR?
# - AISStream.io ücretsiz planı Türk orta Ege kıyısında (İzmir 38.4°N,
#   Çeşme 38.3°N, Kuşadası 37.8°N) yeterli alıcı kapsamına sahip değil.
#   Bu bölgelerden sinyal gelmiyor — veri boşluğu, kod hatası değil.
# - Kuzey sınırı (lat > 38°N): Marmara Denizi ve Çanakkale Boğazı trafiğini
#   dışarıda bırakır; bu bölge Ege değil, ayrı bir deniz havzasıdır.
# - Boylam alt sınırı (lon >= 26.5°E): Yunanistan anakarası ve büyük Ege
#   adalarının büyük bölümünü eliyor.
#
# GERÇEK KAPSAM: Güney Türk Ege — Bodrum yarımadası, Marmaris körfezi,
# Datça yarımadası ve yakın Yunan adaları (Kos, Rodos, Symi) koridoru.
LON_MIN = 26.5
LAT_MIN = 36.0
LAT_MAX = 38.0

# ── ShipType kod → kategori eşleştirmesi ─────────────────────────────────────
# IMO/ITU AIS standart kodları (0-99)
SHIP_TYPE_MAP = {
    # Özel kategoriler
    0:  "Unknown",
    # Balıkçı
    30: "Fishing",
    # Çekme / römorkaj
    31: "Towing",
    32: "Towing",
    52: "Tug",
    # Dalış / tarama
    33: "Dredging",
    34: "Diving",
    # Askeri / SAR
    35: "Military",
    51: "SAR",
    55: "Law Enforcement",
    58: "Medical",
    # Eğlence / yat
    36: "Sailing Yacht",
    37: "Pleasure Craft",
    # Yüksek hızlı
    40: "High Speed Craft",
    41: "High Speed Craft",
    42: "High Speed Craft",
    43: "High Speed Craft",
    44: "High Speed Craft",
    45: "High Speed Craft",
    46: "High Speed Craft",
    47: "High Speed Craft",
    48: "High Speed Craft",
    49: "High Speed Craft",
    # Pilot / liman
    50: "Pilot",
    53: "Port Tender",
    # Yolcu / feribot
    60: "Passenger",
    61: "Passenger",
    62: "Passenger",
    63: "Passenger",
    64: "Passenger",
    65: "Passenger",
    66: "Passenger",
    67: "Passenger",
    68: "Passenger",
    69: "Passenger",
    # Kargo
    70: "Cargo",
    71: "Cargo",
    72: "Cargo",
    73: "Cargo",
    74: "Cargo",
    75: "Cargo",
    76: "Cargo",
    77: "Cargo",
    78: "Cargo",
    79: "Cargo",
    # Tanker
    80: "Tanker",
    81: "Tanker",
    82: "Tanker",
    83: "Tanker",
    84: "Tanker",
    85: "Tanker",
    86: "Tanker",
    87: "Tanker",
    88: "Tanker",
    89: "Tanker",
    # Diğer
    90: "Other",
    91: "Other",
    92: "Other",
    93: "Other",
    94: "Other",
    95: "Other",
    96: "Other",
    97: "Other",
    98: "Other",
    99: "Other",
}

def map_ship_type(code) -> str:
    """Sayısal kodu kategoriye çevir. Bilinmeyenler 'Unknown'."""
    if pd.isna(code):
        return "Unknown"
    return SHIP_TYPE_MAP.get(int(code), "Unknown")


# ── 1. CSV → SQLite import ────────────────────────────────────────────────────

def import_csv_sessions(conn: sqlite3.Connection):
    """data/raw/ altındaki tüm CSV'leri ais_raw tablosuna yükle."""
    csv_files = list(RAW_DIR.glob("ais_aegean_*.csv"))
    if not csv_files:
        print("Import edilecek CSV bulunamadı — atlanıyor.")
        return

    for csv_path in csv_files:
        session_id = csv_path.stem.replace("ais_aegean_", "")
        # Aynı session zaten DB'de var mı?
        cur = conn.execute(
            "SELECT COUNT(*) FROM ais_raw WHERE session_id = ?", (session_id,)
        )
        if cur.fetchone()[0] > 0:
            print(f"  {session_id} zaten DB'de, atlanıyor.")
            continue

        try:
            df = pd.read_csv(csv_path, dtype={"mmsi": str})
        except pd.errors.EmptyDataError:
            print(f"  {session_id}: boş dosya, atlanıyor.")
            continue

        if len(df) == 0:
            print(f"  {session_id}: veri yok, atlanıyor.")
            continue

        df["session_id"] = session_id
        df.to_sql("ais_raw", conn, if_exists="append", index=False)
        conn.commit()
        print(f"  {session_id}: {len(df)} satır import edildi.")


# ── 2. Temizleme ──────────────────────────────────────────────────────────────

def clean_data(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Ham veriyi çek, temizle, zenginleştir.
    Neden bu adımlar:
    - lon >= 26.0 → Türk karasuları (Yunan adaları ve anakarası elenir)
    - Koordinat sınırları → AIS "bilinmiyor" değerleri (91/181) ve fiziksel imkânsız değerler
    - speed <= 50 → 50 knot üstü AIS hatasıdır (ticari gemi max ~30 knot)
    - PositionReport filtresi → sadece koordinatı olan satırlar
    """
    df = pd.read_sql("""
        SELECT *
        FROM ais_raw
        WHERE message_type = 'PositionReport'
          AND latitude  IS NOT NULL
          AND longitude IS NOT NULL
    """, conn, dtype={"mmsi": str})

    print(f"\nHam PositionReport satırı : {len(df):,}")

    # Koordinat geçerlilik kontrolü
    df = df[
        (df["latitude"].between(-90, 90)) &
        (df["longitude"].between(-180, 180))
    ]
    print(f"Koordinat filtresi sonrası : {len(df):,}")

    # Coğrafi kapsam filtresi — gerçek AIS kapsam alanı
    df = df[
        (df["longitude"] >= LON_MIN) &
        (df["latitude"].between(LAT_MIN, LAT_MAX))
    ]
    print(f"Kapsam filtresi sonrası    : {len(df):,}  "
          f"(lon≥{LON_MIN}°E, lat {LAT_MIN}–{LAT_MAX}°N)")

    # Fiziksel olarak imkânsız hız değerleri
    df = df[df["speed_knots"].isna() | (df["speed_knots"] <= 50)]
    print(f"Hız filtresi sonrası       : {len(df):,}")

    # ShipType bilgisini ShipStaticData kayıtlarından getir (MMSI ile join)
    static = pd.read_sql("""
        SELECT mmsi, ship_type_code, ship_name
        FROM ais_raw
        WHERE message_type = 'ShipStaticData'
          AND ship_type_code IS NOT NULL
        GROUP BY mmsi          -- her MMSI için tek kayıt al
    """, conn, dtype={"mmsi": str})

    # PositionReport'ta ship_type_code genelde NULL — static'ten doldur
    df = df.drop(columns=["ship_type_code"], errors="ignore")
    df = df.merge(
        static[["mmsi", "ship_type_code"]],
        on="mmsi", how="left"
    )
    # İsim de static'ten dolduralım (daha güvenilir)
    df = df.drop(columns=["ship_name"], errors="ignore")
    df = df.merge(
        static[["mmsi", "ship_name"]],
        on="mmsi", how="left"
    )

    # Tip kodu → okunabilir kategori
    df["ship_category"] = df["ship_type_code"].apply(map_ship_type)

    # timestamp → datetime (zaman analizleri için)
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    df["hour"] = df["timestamp_utc"].dt.hour

    print(f"\nTemiz veri satır sayısı    : {len(df):,}")
    print(f"Tekil gemi (MMSI)          : {df['mmsi'].nunique():,}")
    print(f"Gemi kategorisi dağılımı   :")
    print(df["ship_category"].value_counts().to_string())

    return df


# ── 3. Temiz tabloyu SQLite'a yaz ────────────────────────────────────────────

def write_clean_table(conn: sqlite3.Connection, df: pd.DataFrame):
    """
    ais_clean tablosunu (yeniden) oluştur.
    replace → scripti tekrar çalıştırınca eski tablo silinip yenisi yazılır.
    """
    df.to_sql("ais_clean", conn, if_exists="replace", index=False)
    conn.commit()
    print(f"\nais_clean tablosu güncellendi: {len(df):,} satır → {DB_PATH}")


# ── 4. Örnek SQL sorguları ────────────────────────────────────────────────────

def run_sample_queries(conn: sqlite3.Connection):
    """
    Portfolyo için örnek SQL sorguları — her biri bir analitik soruyu yanıtlıyor.
    """
    print("\n" + "="*55)
    print("ÖRNEK SQL SORGULARI")
    print("="*55)

    # Sorgu 1: Gemi tipi dağılımı
    print("\n[1] Gemi kategorisi dağılımı:")
    q1 = pd.read_sql("""
        SELECT
            ship_category,
            COUNT(DISTINCT mmsi)          AS unique_vessels,
            COUNT(*)                      AS position_reports,
            ROUND(AVG(speed_knots), 2)    AS avg_speed_knots
        FROM ais_clean
        GROUP BY ship_category
        ORDER BY unique_vessels DESC
    """, conn)
    print(q1.to_string(index=False))

    # Sorgu 2: En yoğun saatler
    print("\n[2] Saatlik trafik yoğunluğu:")
    q2 = pd.read_sql("""
        SELECT
            hour,
            COUNT(DISTINCT mmsi)  AS active_vessels,
            COUNT(*)              AS total_positions
        FROM ais_clean
        GROUP BY hour
        ORDER BY hour
    """, conn)
    print(q2.to_string(index=False))

    # Sorgu 3: En hızlı 10 gemi
    print("\n[3] En yüksek medyan hıza sahip 10 gemi:")
    q3 = pd.read_sql("""
        SELECT
            ship_name,
            ship_category,
            ROUND(AVG(speed_knots), 1)    AS avg_speed,
            COUNT(*)                       AS obs_count
        FROM ais_clean
        WHERE speed_knots > 0
          AND ship_name IS NOT NULL
          AND ship_name != ''
        GROUP BY mmsi
        HAVING obs_count >= 5
        ORDER BY avg_speed DESC
        LIMIT 10
    """, conn)
    print(q3.to_string(index=False))

    # Sorgu 4: Demirli vs seyir halindeki gemiler
    print("\n[4] Navigasyon durumu dağılımı:")
    q4 = pd.read_sql("""
        SELECT
            CASE nav_status
                WHEN 0 THEN 'Under way (engine)'
                WHEN 1 THEN 'At anchor'
                WHEN 5 THEN 'Moored'
                WHEN 8 THEN 'Under way (sailing)'
                ELSE 'Other/Unknown'
            END AS status_label,
            COUNT(DISTINCT mmsi) AS vessels
        FROM ais_clean
        GROUP BY nav_status
        ORDER BY vessels DESC
    """, conn)
    print(q4.to_string(index=False))


# ── Ana akış ─────────────────────────────────────────────────────────────────

def main():
    conn = sqlite3.connect(DB_PATH)

    # ais_raw tablosu yoksa oluştur (collector çalışmadıysa)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ais_raw (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp_utc TEXT, session_id TEXT, mmsi TEXT,
            ship_name TEXT, ship_type_code INTEGER,
            latitude REAL, longitude REAL, speed_knots REAL,
            course_deg REAL, heading_deg REAL,
            nav_status INTEGER, message_type TEXT
        )
    """)
    conn.commit()

    print("── Adım 1: CSV import ──────────────────────────────")
    import_csv_sessions(conn)

    print("\n── Adım 2: Temizleme ───────────────────────────────")
    df_clean = clean_data(conn)

    print("\n── Adım 3: Temiz tablo yazılıyor ───────────────────")
    write_clean_table(conn, df_clean)

    print("\n── Adım 4: Örnek SQL sorguları ─────────────────────")
    run_sample_queries(conn)

    conn.close()
    print("\nAşama 2 tamamlandı. Analiz için src/analysis.py çalıştırılabilir.")


if __name__ == "__main__":
    main()
