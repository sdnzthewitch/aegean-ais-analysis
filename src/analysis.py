"""
AIS Data Analysis — Aegean Sea / Turkish Coastal Waters
Reads ais_clean table from SQLite, produces:
  1. Ship category distribution
  2. Traffic density grid (heatmap data)
  3. Speed distributions by category (median + IQR)
  4. Hourly traffic pattern
  5. Key findings summary
"""

import sqlite3
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")           # GUI olmayan ortamda da çalışır
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from pathlib import Path

# ── Yollar ───────────────────────────────────────────────────────────────────

DATA_DIR    = Path(__file__).parent.parent / "data"
DB_PATH     = DATA_DIR / "ais_aegean.db"
FIGURES_DIR = Path(__file__).parent.parent / "figures"
FIGURES_DIR.mkdir(exist_ok=True)

# Grafik stili — yayın kalitesi
sns.set_theme(style="whitegrid", palette="muted", font_scale=1.1)
COLORS = {
    "Cargo":          "#2196F3",
    "Unknown":        "#9E9E9E",
    "Pleasure Craft": "#FF9800",
    "Passenger":      "#4CAF50",
    "Tanker":         "#F44336",
    "Sailing Yacht":  "#9C27B0",
    "Tug":            "#795548",
    "Other":          "#607D8B",
    "Towing":         "#00BCD4",
    "SAR":            "#E91E63",
    "Pilot":          "#FFEB3B",
}

# ── Veri yükleme ──────────────────────────────────────────────────────────────

def load_data() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM ais_clean", conn, dtype={"mmsi": str})
    conn.close()
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    print(f"Yüklendi: {len(df):,} satır, {df['mmsi'].nunique()} tekil gemi")
    return df

# ── 1. Gemi tipi dağılımı ─────────────────────────────────────────────────────

def plot_ship_distribution(df: pd.DataFrame):
    """
    Neden yatay bar chart?
    Kategori isimleri uzun; yatay yerleşim okunabilirliği artırır.
    İki metrik: tekil gemi sayısı (kim var) + konum raporu (ne kadar aktif).
    """
    summary = (
        df.groupby("ship_category")
        .agg(
            unique_vessels=("mmsi", "nunique"),
            position_reports=("mmsi", "count"),
        )
        .sort_values("unique_vessels", ascending=True)
    )

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # Sol: tekil gemi
    colors_left = [COLORS.get(c, "#607D8B") for c in summary.index]
    axes[0].barh(summary.index, summary["unique_vessels"],
                 color=colors_left, edgecolor="white")
    axes[0].set_xlabel("Number of Unique Vessels")
    axes[0].set_title("Unique Vessels by Category")
    for i, v in enumerate(summary["unique_vessels"]):
        axes[0].text(v + 0.3, i, str(v), va="center", fontsize=9)

    # Sağ: konum raporu sayısı (aktivite)
    axes[1].barh(summary.index, summary["position_reports"],
                 color=colors_left, edgecolor="white")
    axes[1].set_xlabel("Number of Position Reports")
    axes[1].set_title("AIS Position Reports by Category")
    for i, v in enumerate(summary["position_reports"]):
        axes[1].text(v + 2, i, str(v), va="center", fontsize=9)

    fig.suptitle(
        "Ship Traffic in Turkish Aegean Coastal Waters\n"
        "(AIS Live Data · 1-hour snapshot · lon ≥ 26°E)",
        fontsize=12, y=1.01
    )
    plt.tight_layout()
    path = FIGURES_DIR / "01_ship_distribution.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Kaydedildi: {path}")

# ── 2. Hız dağılımları — neden medyan? ───────────────────────────────────────

def plot_speed_distributions(df: pd.DataFrame):
    """
    Ortalama yerine medyan + IQR (çeyrekler arası aralık) kullanıyoruz çünkü:
    - Hız verisi sağa çarpık (çoğu gemi yavaş, birkaçı çok hızlı)
    - Demir atan gemiler (hız=0) ortalamayı aşağı çeker
    - Medyan aykırı değerlerden etkilenmez → daha temsili merkez ölçüsü
    - IQR, veri yayılımını aykırı değer olmaksızın gösterir
    """
    speed_cats = ["Cargo", "Tanker", "Passenger", "Pleasure Craft",
                  "Sailing Yacht", "Tug"]
    df_speed = df[
        (df["ship_category"].isin(speed_cats)) &
        (df["speed_knots"] > 0.5)  # demir atan / liman gemileri hariç
    ].copy()

    if df_speed.empty:
        print("  Hız verisi yetersiz, grafik atlanıyor.")
        return

    fig, ax = plt.subplots(figsize=(11, 5))

    # Violin + box overlay: dağılım şeklini ve medyanı aynı anda gösterir
    order = (
        df_speed.groupby("ship_category")["speed_knots"]
        .median()
        .sort_values(ascending=False)
        .index.tolist()
    )
    palette = {c: COLORS.get(c, "#607D8B") for c in order}

    sns.violinplot(
        data=df_speed, x="ship_category", y="speed_knots",
        order=order, palette=palette,
        inner="box", cut=0, ax=ax
    )

    ax.set_xlabel("Ship Category")
    ax.set_ylabel("Speed Over Ground (knots)")
    ax.set_title(
        "Speed Distribution by Ship Category\n"
        "(vessels under way only · inner box: median + IQR)"
    )

    # Medyan değerini grafiğe yaz
    for i, cat in enumerate(order):
        med = df_speed[df_speed["ship_category"] == cat]["speed_knots"].median()
        ax.text(i, med + 0.3, f"{med:.1f}kn",
                ha="center", fontsize=8.5, fontweight="bold", color="white",
                bbox=dict(boxstyle="round,pad=0.2", fc="black", alpha=0.5))

    plt.tight_layout()
    path = FIGURES_DIR / "02_speed_distributions.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Kaydedildi: {path}")

# ── 3. Trafik yoğunluk grid'i ─────────────────────────────────────────────────

def plot_traffic_density(df: pd.DataFrame):
    """
    Ege'yi 0.25° x 0.25° grid hücrelerine bölerek her hücredeki
    tekil gemi sayısını hesaplıyoruz.
    Neden 0.25°? ~27 km çözünürlük — liman / ada / boğaz gibi
    coğrafi odak noktaları ayrışır, fazla granüler olmaz.
    """
    df = df.dropna(subset=["latitude", "longitude"])

    RES = 0.25
    df["lat_bin"] = (df["latitude"]  / RES).round() * RES
    df["lon_bin"] = (df["longitude"] / RES).round() * RES

    grid = (
        df.groupby(["lat_bin", "lon_bin"])
        .agg(vessels=("mmsi", "nunique"))
        .reset_index()
    )

    # Pivot → ısı haritası matrisi
    pivot = grid.pivot(index="lat_bin", columns="lon_bin", values="vessels")

    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(
        pivot,
        cmap="YlOrRd",
        linewidths=0,
        ax=ax,
        cbar_kws={"label": "Unique Vessels per 0.25° Cell"},
    )
    ax.set_title(
        "AIS Traffic Density — Turkish Aegean Coastal Zone\n"
        "(0.25° × 0.25° grid · unique vessel count)"
    )
    ax.set_xlabel("Longitude (°E)")
    ax.set_ylabel("Latitude (°N)")

    # Eksen etiketlerini sadeleştir
    ax.xaxis.set_major_locator(mticker.MaxNLocator(8))
    ax.yaxis.set_major_locator(mticker.MaxNLocator(8))
    plt.xticks(rotation=45)
    plt.yticks(rotation=0)

    plt.tight_layout()
    path = FIGURES_DIR / "03_traffic_density.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Kaydedildi: {path}")

# ── 4. İstatistiksel özet ─────────────────────────────────────────────────────

def print_key_findings(df: pd.DataFrame):
    """
    Yazıya ve README'ye girecek 4-5 çarpıcı bulgu.
    Her bulgu yanına örneklem sınırı notu ekliyoruz.
    """
    print("\n" + "="*60)
    print("ANA BULGULAR  (örneklem: ~60 dk, Türk Ege kıyıları)")
    print("="*60)

    # 1. Dominant kategori
    top_cat = df.groupby("ship_category")["mmsi"].nunique().idxmax()
    top_n   = df.groupby("ship_category")["mmsi"].nunique().max()
    total_v = df["mmsi"].nunique()
    print(f"\n[1] Dominant gemi tipi: {top_cat} "
          f"({top_n}/{total_v} gemi, %{top_n/total_v*100:.0f})")

    # 2. Yat + eğlence oranı
    leisure = df[df["ship_category"].isin(["Pleasure Craft", "Sailing Yacht"])]["mmsi"].nunique()
    print(f"[2] Yat / eğlence teknesi: {leisure} gemi "
          f"(%{leisure/total_v*100:.0f} — yaz sezonu sinyali)")

    # 3. Medyan hızlar
    print("\n[3] Medyan hız (seyir halindeki gemiler, speed > 0.5 kn):")
    spd = (
        df[df["speed_knots"] > 0.5]
        .groupby("ship_category")["speed_knots"]
        .agg(median="median", q25=lambda x: x.quantile(0.25),
             q75=lambda x: x.quantile(0.75), n="count")
        .sort_values("median", ascending=False)
    )
    print(spd.round(2).to_string())
    print("  → Neden medyan? Demir atan gemiler (hız=0) ortalamayı çarpıtır.")

    # 4. Türk / Yunan tarafı oranı
    conn = sqlite3.connect(DB_PATH)
    total_raw = pd.read_sql(
        "SELECT COUNT(*) as n FROM ais_raw WHERE message_type='PositionReport'",
        conn
    ).iloc[0, 0]
    conn.close()
    turkish = len(df)
    greek   = total_raw - turkish
    print(f"\n[4] Ege trafiği coğrafi dağılımı (lon < / ≥ 26°E):")
    print(f"    Yunan tarafı  : {greek:,}  pozisyon raporu (%{greek/total_raw*100:.0f})")
    print(f"    Türk tarafı   : {turkish:,}  pozisyon raporu (%{turkish/total_raw*100:.0f})")
    print(f"    ⚠ Örneklem sınırı: tek günlük, tek saatlik aralık. "
          f"Mevsimsel ve günlük örüntü için ek oturum gerekli.")

    # 5. Hız IQR özeti
    cargo_spd = df[
        (df["ship_category"] == "Cargo") & (df["speed_knots"] > 0.5)
    ]["speed_knots"]
    if len(cargo_spd) > 0:
        print(f"\n[5] Kargo hız istatistikleri:")
        print(f"    Medyan : {cargo_spd.median():.1f} kn")
        print(f"    IQR    : {cargo_spd.quantile(0.25):.1f} – {cargo_spd.quantile(0.75):.1f} kn")
        print(f"    Max    : {cargo_spd.max():.1f} kn")

# ── Ana akış ─────────────────────────────────────────────────────────────────

def main():
    print("── Veri yükleniyor ─────────────────────────────────")
    df = load_data()

    print("\n── Grafikler üretiliyor ────────────────────────────")
    plot_ship_distribution(df)
    plot_speed_distributions(df)
    plot_traffic_density(df)

    print_key_findings(df)

    print(f"\nTüm grafikler: {FIGURES_DIR}/")
    print("Aşama 3 tamamlandı. Sırada: src/app.py (Streamlit dashboard)")

if __name__ == "__main__":
    main()
