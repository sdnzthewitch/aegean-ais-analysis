# Bodrum–Kos–Rhodes Sea Corridor · AIS Traffic Analysis

Live AIS vessel traffic analysis for the Turkish–Greek Aegean boundary
sea lane, collected via the [AISStream.io](https://aisstream.io) WebSocket API.

---

## Geographic Scope

**Coverage area:** Bodrum–Kos–Rhodes open-sea corridor
`lat 36.0–38.0°N · lon 26.5–29.0°E`

AISStream.io receivers are located primarily on Greek islands (Kos, Rhodes),
so reliable signal coverage is limited to this corridor and the nearby ports
of Bodrum and Marmaris.

| Location | Coverage |
|---|---|
| Bodrum, Marmaris | ✅ Captured (close to island receivers) |
| Kos, Rhodes sea lane | ✅ Captured |
| İzmir, Çeşme, Kuşadası | ❌ No AISStream receiver coverage |
| Çanakkale, Datça inner bay | ❌ No signal |
| Istanbul / Marmara Sea | ❌ Excluded (separate maritime basin) |

> This is a data-source constraint, not a code limitation.
> The dataset represents the sea lane between Turkey and the Dodecanese
> islands, not the full Turkish Aegean coastline.

---

## Dataset

- **Source:** AISStream.io live WebSocket feed
- **Collection window:** ~60 minutes, evening hours (19:00–20:00 UTC+3)
- **Vessels captured:** 80 unique MMSI
- **Position reports:** 1,263 (after geographic and quality filters)
- **Message types:** `PositionReport` (Type 1/2/3) + `ShipStaticData` (Type 5/24)

---

## Key Findings

1. **Cargo vessels dominate** the corridor — the largest category by both
   vessel count and position reports, reflecting the İzmir–Piraeus and
   Asia–Europe container routes passing through the Dodecanese.

2. **~16% leisure traffic** (Pleasure Craft + Sailing Yacht) — consistent
   with the Bodrum peninsula being a major Aegean charter hub in summer.

3. **Median cargo speed: 10.9 kn** (IQR 7.7–12.6 kn). Median used instead
   of mean because speed distributions are right-skewed; anchored vessels
   (speed = 0) would pull the mean down disproportionately.

4. **Single evening snapshot caveat:** Passenger ferry counts are likely
   underrepresented — daily routes (Bodrum–Kos, Marmaris–Rhodes) typically
   depart in the morning and return in the afternoon.

---

## Setup

```bash
# 1. Clone and create virtual environment
git clone <repo-url>
cd aegean-ais-analysis
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure API key
cp .env.example .env
# Edit .env and set AISSTREAM_API_KEY=your_key_here
```

---

## Usage

### Collect live AIS data
```bash
python src/collector.py 60   # collect for 60 minutes
```
Output: `data/ais_aegean.db` (SQLite, appends across sessions)

### Clean and process
```bash
python src/cleaner.py
```
Imports any raw CSV sessions, applies geographic and quality filters,
maps ShipType codes to readable categories, writes `ais_clean` table.

### Run analysis
```bash
python src/analysis.py
```
Produces figures in `figures/` and prints key statistics.

### Launch dashboard
```bash
python -m streamlit run app.py
```

---

## Project Structure

```
aegean-ais-analysis/
├── data/               # SQLite database (git-ignored)
├── figures/            # Generated charts
├── src/
│   ├── collector.py    # WebSocket AIS collector → SQLite
│   ├── cleaner.py      # Data cleaning, filtering, type mapping
│   └── analysis.py     # Statistical analysis + visualizations
├── app.py              # Streamlit dashboard
├── .env.example        # API key template
├── .gitignore
└── requirements.txt
```

---

## Methodology

1. **Collection:** WebSocket subscription to AISStream.io filtered to
   `PositionReport` and `ShipStaticData` message types within the bounding box.
   Auto-reconnects on dropped connections. Writes directly to SQLite in
   batches of 50 messages.

2. **Cleaning:** Invalid coordinates (AIS sentinel values 91°/181°),
   implausible speeds (>50 kn), and out-of-scope geographic areas removed.
   `ShipStaticData` joined to position reports via MMSI to enrich with
   vessel name and type.

3. **Analysis:** Median + IQR used for speed statistics (right-skewed
   distributions). Traffic density computed on a 0.25° × 0.25° grid.

---

## Limitations

- Single evening snapshot — diurnal and seasonal patterns not captured
- ~39% of vessels classified as "Unknown" (no ShipStaticData received)
- Geographic coverage limited to Bodrum–Kos–Rhodes corridor
- Free-tier AISStream.io; satellite AIS coverage not included

---

## Data Source

[AISStream.io](https://aisstream.io) — real-time AIS WebSocket API.
AIS data is publicly broadcast by vessels under IMO SOLAS regulations.
