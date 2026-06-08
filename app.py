"""
Aegean AIS Traffic Dashboard — Streamlit App
Türk Ege Kıyıları Canlı Gemi Trafiği Analizi

Çalıştırmak için:
    streamlit run app.py
"""

import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── Sayfa yapılandırması ──────────────────────────────────────────────────────

st.set_page_config(
    page_title="Aegean AIS Traffic",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_PATH = Path(__file__).parent / "data" / "ais_aegean.db"

CATEGORY_COLORS = {
    "Cargo":          "#2196F3",
    "Unknown":        "#9E9E9E",
    "Pleasure Craft": "#FF9800",
    "Passenger":      "#4CAF50",
    "Tanker":         "#F44336",
    "Sailing Yacht":  "#9C27B0",
    "Tug":            "#795548",
    "Towing":         "#00BCD4",
    "SAR":            "#E91E63",
    "Pilot":          "#FFEB3B",
    "Other":          "#607D8B",
}

# ── Veri yükleme (cache ile — her yenilemede DB'yi okumaz) ───────────────────

@st.cache_data(ttl=300)   # 5 dakikada bir taze veri çek
def load_data() -> pd.DataFrame:
    if not DB_PATH.exists():
        return pd.DataFrame()
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM ais_clean", conn, dtype={"mmsi": str})
    conn.close()
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    df["hour"] = df["timestamp_utc"].dt.hour
    return df

# ── Sidebar — filtreler ───────────────────────────────────────────────────────

def render_sidebar(df: pd.DataFrame):
    st.sidebar.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b4/"
        "Flag_of_Turkey.svg/320px-Flag_of_Turkey.svg.png",
        width=80,
    )
    st.sidebar.title("🚢 AIS Traffic Filter")
    st.sidebar.caption("Turkish Aegean Coastal Waters · lon ≥ 26°E")

    categories = sorted(df["ship_category"].dropna().unique())
    selected = st.sidebar.multiselect(
        "Ship Category",
        options=categories,
        default=categories,
    )

    speed_min, speed_max = float(df["speed_knots"].min()), float(df["speed_knots"].max())
    speed_range = st.sidebar.slider(
        "Speed Range (knots)",
        min_value=0.0,
        max_value=round(speed_max, 1),
        value=(0.0, round(speed_max, 1)),
        step=0.5,
    )

    show_anchored = st.sidebar.checkbox("Include anchored vessels (speed < 0.5 kn)", value=True)

    st.sidebar.markdown("---")
    st.sidebar.caption(
        "**Data source:** AISStream.io live feed  \n"
        "**Scope:** Bodrum–Kos–Rhodes corridor  \n"
        "**lat** 36–38°N · **lon** 26.5–29°E  \n"
        "**Snapshot:** ~60 min · evening  \n\n"
        "⚠️ İzmir, Çeşme, Kuşadası, Çanakkale: **no coverage**"
    )

    return selected, speed_range, show_anchored


def filter_data(df, selected_cats, speed_range, show_anchored):
    mask = df["ship_category"].isin(selected_cats)
    mask &= df["speed_knots"].between(speed_range[0], speed_range[1])
    if not show_anchored:
        mask &= df["speed_knots"] >= 0.5
    return df[mask]

# ── KPI kartları ──────────────────────────────────────────────────────────────

def render_kpis(df_full: pd.DataFrame, df_filtered: pd.DataFrame):
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Vessels (filtered)", df_filtered["mmsi"].nunique())
    c2.metric("Position Reports", f"{len(df_filtered):,}")
    c3.metric("Median Speed", f"{df_filtered['speed_knots'].median():.1f} kn")
    c4.metric(
        "Leisure Vessels",
        df_filtered[df_filtered["ship_category"].isin(
            ["Pleasure Craft", "Sailing Yacht"]
        )]["mmsi"].nunique(),
    )
    c5.metric("Data Coverage", "~60 min snapshot")

# ── Harita ────────────────────────────────────────────────────────────────────

def render_map(df: pd.DataFrame):
    st.subheader("🗺️ Vessel Positions — Turkish Aegean Coast")

    df_map = df.dropna(subset=["latitude", "longitude"])
    if df_map.empty:
        st.info("No position data for selected filters.")
        return

    tab_scatter, tab_density = st.tabs(["Vessel Positions", "Traffic Density"])

    with tab_scatter:
        fig = px.scatter_mapbox(
            df_map,
            lat="latitude",
            lon="longitude",
            color="ship_category",
            color_discrete_map=CATEGORY_COLORS,
            hover_data={
                "ship_name": True,
                "ship_category": True,
                "speed_knots": ":.1f",
                "latitude": ":.3f",
                "longitude": ":.3f",
            },
            zoom=6,
            center={"lat": 38.5, "lon": 27.0},
            mapbox_style="carto-positron",
            height=520,
            title="AIS Position Reports — Turkish Aegean Coastal Zone",
        )
        fig.update_traces(marker=dict(size=6, opacity=0.75))
        fig.update_layout(
            legend_title_text="Ship Category",
            margin=dict(l=0, r=0, t=40, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab_density:
        fig2 = px.density_mapbox(
            df_map,
            lat="latitude",
            lon="longitude",
            radius=18,
            zoom=6,
            center={"lat": 38.5, "lon": 27.0},
            mapbox_style="carto-darkmatter",
            color_continuous_scale="YlOrRd",
            height=520,
            title="Traffic Density Heatmap — Turkish Aegean",
        )
        fig2.update_layout(margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig2, use_container_width=True)

# ── Grafikler ─────────────────────────────────────────────────────────────────

def render_charts(df: pd.DataFrame, df_full: pd.DataFrame):
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("📊 Vessel Count by Category")
        summary = (
            df.groupby("ship_category")["mmsi"]
            .nunique()
            .reset_index()
            .rename(columns={"mmsi": "unique_vessels"})
            .sort_values("unique_vessels", ascending=True)
        )
        fig = px.bar(
            summary,
            x="unique_vessels",
            y="ship_category",
            orientation="h",
            color="ship_category",
            color_discrete_map=CATEGORY_COLORS,
            labels={"unique_vessels": "Unique Vessels", "ship_category": ""},
            height=380,
        )
        fig.update_layout(showlegend=False, margin=dict(l=0, r=10, t=10, b=0))
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("⚡ Speed Distribution by Category")
        df_speed = df[df["speed_knots"] > 0.5].copy()
        if df_speed.empty:
            st.info("No underway vessels in selection.")
        else:
            order = (
                df_speed.groupby("ship_category")["speed_knots"]
                .median()
                .sort_values(ascending=False)
                .index.tolist()
            )
            fig2 = px.box(
                df_speed,
                x="ship_category",
                y="speed_knots",
                color="ship_category",
                color_discrete_map=CATEGORY_COLORS,
                category_orders={"ship_category": order},
                labels={"speed_knots": "Speed (knots)", "ship_category": ""},
                height=380,
                points=False,
            )
            fig2.update_layout(showlegend=False, margin=dict(l=0, r=10, t=10, b=0))
            st.plotly_chart(fig2, use_container_width=True)

    # Ege trafik dağılımı pasta grafik
    st.subheader("🌊 Aegean Traffic Split: Greek vs Turkish Waters")
    conn = sqlite3.connect(DB_PATH)
    total_raw = pd.read_sql(
        "SELECT COUNT(*) as n FROM ais_raw WHERE message_type='PositionReport'", conn
    ).iloc[0, 0]
    conn.close()

    turkish = len(df_full)
    greek   = max(total_raw - turkish, 0)
    pie_df  = pd.DataFrame({
        "Zone":    ["Greek side (lon < 26°E)", "Turkish side (lon ≥ 26°E)"],
        "Reports": [greek, turkish],
    })
    fig3 = px.pie(
        pie_df, values="Reports", names="Zone",
        color_discrete_sequence=["#42A5F5", "#EF5350"],
        height=320,
    )
    fig3.update_traces(textinfo="percent+label")
    fig3.update_layout(margin=dict(l=0, r=0, t=10, b=0), showlegend=False)
    st.plotly_chart(fig3, use_container_width=True)


# ── İstatistik tablosu ────────────────────────────────────────────────────────

def render_stats_table(df: pd.DataFrame):
    st.subheader("📋 Summary Statistics by Category")
    stats = (
        df[df["speed_knots"] > 0.5]
        .groupby("ship_category")["speed_knots"]
        .agg(
            Vessels=lambda x: df.loc[x.index, "mmsi"].nunique(),
            Median=lambda x: round(x.median(), 1),
            Q25=lambda x: round(x.quantile(0.25), 1),
            Q75=lambda x: round(x.quantile(0.75), 1),
            Max=lambda x: round(x.max(), 1),
            Observations="count",
        )
        .sort_values("Median", ascending=False)
        .reset_index()
        .rename(columns={"ship_category": "Category"})
    )
    st.dataframe(stats, use_container_width=True, hide_index=True)
    st.caption(
        "Speed stats include only underway vessels (SOG > 0.5 kn). "
        "Median and IQR (Q25–Q75) used instead of mean ± std "
        "because speed distributions are right-skewed."
    )

# ── Ana layout ────────────────────────────────────────────────────────────────

def main():
    st.title("🚢 Bodrum–Kos–Rhodes Sea Corridor · AIS Traffic Analysis")
    st.markdown(
        "Live AIS data collected via [AISStream.io](https://aisstream.io) WebSocket API · "
        "Turkish–Greek Aegean boundary sea lane"
    )
    st.warning(
        "**Coverage note:** This dataset captures the **Bodrum–Kos–Rhodes open-sea corridor** "
        "(lat 36–38°N, lon 26.5–29°E), not the full Turkish Aegean coast. "
        "AISStream.io receivers are located primarily on Greek islands (Kos, Rhodes), so signals "
        "reach nearby sea lanes and the ports of Bodrum and Marmaris — but **İzmir, Çeşme, "
        "Kuşadası, and Çanakkale have zero coverage** in this dataset. "
        "Istanbul/Marmara traffic (lat ~41°N) was excluded as a separate maritime basin. "
        "Single ~60-minute evening snapshot (19:00–20:00 local time).",
    )

    df_full = load_data()

    if df_full.empty:
        st.error(
            "Database not found or empty. "
            "Run `python src/collector.py` then `python src/cleaner.py` first."
        )
        return

    selected_cats, speed_range, show_anchored = render_sidebar(df_full)
    df = filter_data(df_full, selected_cats, speed_range, show_anchored)

    if df.empty:
        st.warning("No vessels match the current filters.")
        return

    render_kpis(df_full, df)
    st.markdown("---")
    render_map(df)
    st.markdown("---")
    render_charts(df, df_full)
    st.markdown("---")
    render_stats_table(df)

    st.markdown(
        "---\n"
        "**Methodological note:** Single ~60-minute evening snapshot. "
        "Passenger ferry and leisure vessel counts may be underrepresented "
        "compared to morning/afternoon hours. "
        "Additional collection sessions planned for diurnal comparison."
    )


if __name__ == "__main__":
    main()
