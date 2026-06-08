# Aegean AIS Analysis

This repository collects live AIS position reports and static ship data from Turkish and Greekcoastal waters using the AISStream.io WebSocket API.

## Setup

1. Copy `.env.example` to `.env`.
2. Set your AISStream API key:

```env
AISSTREAM_API_KEY=your_api_key_here
```

3. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

## Collecting AIS Data

Run the collector from the repository root:

```bash
python src/collector.py 60
```

The script will collect live AIS data for the specified number of minutes and save it to `data/raw/`.

- `60` is the duration in minutes. If omitted, the default is 20 minutes.
- The bounding box covers the Aegean Sea region including Turkish coastal waters.
- If no rows appear immediately, the feed may be sparse in the selected area; run longer or broaden the region.
- Output CSV columns:
  - `timestamp_utc`
  - `mmsi`
  - `ship_name`
  - `ship_type_code`
  - `latitude`
  - `longitude`
  - `speed_knots`
  - `course_deg`
  - `heading_deg`
  - `nav_status`
  - `message_type`

## Notes

- The collector subscribes to `PositionReport` and `ShipStaticData` messages.
- If the WebSocket connection drops, the script will retry after 5 seconds until the specified duration completes.
