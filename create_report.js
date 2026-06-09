const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  ImageRun, Header, Footer, AlignmentType, HeadingLevel, BorderStyle,
  WidthType, ShadingType, VerticalAlign, PageNumber, PageBreak,
  ExternalHyperlink, LevelFormat
} = require("docx");
const fs = require("fs");
const path = require("path");

// ── Renkler ──────────────────────────────────────────────────────────────────
const NAVY   = "1B3A5C";
const TEAL   = "1A7D8E";
const LIGHT  = "EAF4F6";
const GRAY   = "666666";
const WHITE  = "FFFFFF";
const BORDER = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const BORDERS = { top: BORDER, bottom: BORDER, left: BORDER, right: BORDER };
const NO_BORDER = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const NO_BORDERS = { top: NO_BORDER, bottom: NO_BORDER, left: NO_BORDER, right: NO_BORDER };

// ── Yardımcılar ──────────────────────────────────────────────────────────────
const fig = (name, w, h) => new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 120, after: 80 },
  children: [new ImageRun({
    type: "png",
    data: fs.readFileSync(path.join(__dirname, "figures", name)),
    transformation: { width: w, height: h },
    altText: { title: name, description: name, name: name }
  })]
});

const caption = (text) => new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 0, after: 200 },
  children: [new TextRun({ text, font: "Arial", size: 18, italics: true, color: GRAY })]
});

const h1 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_1,
  spacing: { before: 360, after: 120 },
  children: [new TextRun({ text, font: "Arial", size: 32, bold: true, color: NAVY })]
});

const h2 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_2,
  spacing: { before: 240, after: 80 },
  children: [new TextRun({ text, font: "Arial", size: 26, bold: true, color: TEAL })]
});

const body = (text, opts = {}) => new Paragraph({
  spacing: { before: 80, after: 80 },
  children: [new TextRun({ text, font: "Arial", size: 22, color: "222222", ...opts })]
});

const bullet = (text, bold = false) => new Paragraph({
  numbering: { reference: "bullets", level: 0 },
  spacing: { before: 40, after: 40 },
  children: [new TextRun({ text, font: "Arial", size: 22, bold, color: "222222" })]
});

const divider = () => new Paragraph({
  spacing: { before: 160, after: 160 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: TEAL, space: 1 } },
  children: [new TextRun("")]
});

const link = (text, url) => new Paragraph({
  spacing: { before: 60, after: 60 },
  children: [new ExternalHyperlink({
    children: [new TextRun({ text, font: "Arial", size: 22, color: "0563C1", underline: {} })],
    link: url
  })]
});

// ── Kapsam uyarı kutusu ───────────────────────────────────────────────────────
const warningBox = () => new Table({
  width: { size: 9360, type: WidthType.DXA },
  columnWidths: [9360],
  rows: [new TableRow({ children: [new TableCell({
    borders: BORDERS,
    width: { size: 9360, type: WidthType.DXA },
    shading: { fill: "FFF8E1", type: ShadingType.CLEAR },
    margins: { top: 120, bottom: 120, left: 180, right: 180 },
    children: [
      new Paragraph({ spacing: { before: 0, after: 60 }, children: [
        new TextRun({ text: "⚠  Coverage Limitation", font: "Arial", size: 22, bold: true, color: "8B6914" })
      ]}),
      new Paragraph({ spacing: { before: 0, after: 60 }, children: [
        new TextRun({ text: "This dataset represents the Bodrum–Kos–Rhodes open-sea corridor (lat 36–38°N · lon 26.5–29°E), not the full Turkish Aegean coast. AISStream.io receivers are located primarily on Greek islands; as a result, İzmir, Çeşme, Kuşadası, and Çanakkale have zero AIS coverage in this dataset.", font: "Arial", size: 20, color: "555555" })
      ]}),
    ]
  })]})],
});

// ── KPI tablosu ───────────────────────────────────────────────────────────────
const kpiTable = () => {
  const cell = (label, value, bg = LIGHT) => new TableCell({
    borders: BORDERS,
    width: { size: 2340, type: WidthType.DXA },
    shading: { fill: bg, type: ShadingType.CLEAR },
    margins: { top: 120, bottom: 120, left: 120, right: 120 },
    verticalAlign: VerticalAlign.CENTER,
    children: [
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 40 }, children: [
        new TextRun({ text: value, font: "Arial", size: 36, bold: true, color: NAVY })
      ]}),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 0 }, children: [
        new TextRun({ text: label, font: "Arial", size: 18, color: GRAY })
      ]}),
    ]
  });
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [2340, 2340, 2340, 2340],
    rows: [new TableRow({ children: [
      cell("Unique Vessels", "118"),
      cell("Position Reports", "2,267"),
      cell("Leisure Share*", "29.7%"),
      cell("Median Cargo Speed", "11.0 kn"),
    ]})]
  });
};

// ── Bulgular tablosu ──────────────────────────────────────────────────────────
const findingsTable = () => {
  const hdrCell = (text, w) => new TableCell({
    borders: BORDERS,
    width: { size: w, type: WidthType.DXA },
    shading: { fill: NAVY, type: ShadingType.CLEAR },
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    children: [new Paragraph({ children: [
      new TextRun({ text, font: "Arial", size: 20, bold: true, color: WHITE })
    ]})]
  });
  const dataCell = (text, w, bg = WHITE, bold = false) => new TableCell({
    borders: BORDERS,
    width: { size: w, type: WidthType.DXA },
    shading: { fill: bg, type: ShadingType.CLEAR },
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    children: [new Paragraph({ children: [
      new TextRun({ text, font: "Arial", size: 20, color: "222222", bold })
    ]})]
  });

  const rows = [
    new TableRow({ children: [hdrCell("Ship Category", 2600), hdrCell("Vessels", 1200), hdrCell("Reports", 1200), hdrCell("Median Speed", 2000), hdrCell("Note", 2360)] }),
    new TableRow({ children: [dataCell("Pleasure Craft", 2600, LIGHT, true), dataCell("28", 1200, LIGHT), dataCell("498", 1200, LIGHT), dataCell("10.3 kn", 2000, LIGHT), dataCell("Dominant category — Bodrum charter hub", 2360, LIGHT)] }),
    new TableRow({ children: [dataCell("Passenger", 2600), dataCell("21", 1200), dataCell("570", 1200), dataCell("15.0 kn", 2000), dataCell("Morning 13→15 (+15%); high-speed ferries", 2360)] }),
    new TableRow({ children: [dataCell("Cargo", 2600, LIGHT), dataCell("22", 1200, LIGHT), dataCell("468", 1200, LIGHT), dataCell("11.0 kn", 2000, LIGHT), dataCell("Consistent across sessions (12→12)", 2360, LIGHT)] }),
    new TableRow({ children: [dataCell("Tanker", 2600), dataCell("8", 1200), dataCell("164", 1200), dataCell("10.5 kn", 2000), dataCell("", 2360)] }),
    new TableRow({ children: [dataCell("Sailing Yacht", 2600, LIGHT), dataCell("7", 1200, LIGHT), dataCell("127", 1200, LIGHT), dataCell("8.7 kn", 2000, LIGHT), dataCell("Evening 4 → Morning 6", 2360, LIGHT)] }),
    new TableRow({ children: [dataCell("Unknown", 2600), dataCell("25", 1200), dataCell("284", 1200), dataCell("—", 2000), dataCell("21% — no ShipStaticData received", 2360)] }),
  ];
  return new Table({ width: { size: 9360, type: WidthType.DXA }, columnWidths: [2600, 1200, 1200, 2000, 2360], rows });
};

// ── Oturum tablosu ────────────────────────────────────────────────────────────
const sessionTable = () => {
  const hdr = (text, w) => new TableCell({
    borders: BORDERS, width: { size: w, type: WidthType.DXA },
    shading: { fill: TEAL, type: ShadingType.CLEAR },
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    children: [new Paragraph({ children: [new TextRun({ text, font: "Arial", size: 20, bold: true, color: WHITE })] })]
  });
  const dat = (text, w, bg = WHITE) => new TableCell({
    borders: BORDERS, width: { size: w, type: WidthType.DXA },
    shading: { fill: bg, type: ShadingType.CLEAR },
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    children: [new Paragraph({ children: [new TextRun({ text, font: "Arial", size: 20, color: "222222" })] })]
  });
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [2000, 2500, 2500, 2360],
    rows: [
      new TableRow({ children: [hdr("Session", 2000), hdr("Date & Time (UTC+3)", 2500), hdr("Raw Messages", 2500), hdr("Purpose", 2360)] }),
      new TableRow({ children: [dat("Evening", 2000, LIGHT), dat("8 June 2026 · 22:55–23:55", 2500, LIGHT), dat("12,059", 2500, LIGHT), dat("Baseline — cargo & yachts", 2360, LIGHT)] }),
      new TableRow({ children: [dat("Morning", 2000), dat("9 June 2026 · 10:31–11:27", 2500), dat("11,381", 2500), dat("Ferry & leisure peak", 2360)] }),
    ]
  });
};

// ── Hız istatistikleri tablosu ────────────────────────────────────────────────
const speedTable = () => {
  const hdr = (text, w) => new TableCell({
    borders: BORDERS, width: { size: w, type: WidthType.DXA },
    shading: { fill: NAVY, type: ShadingType.CLEAR },
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    children: [new Paragraph({ children: [new TextRun({ text, font: "Arial", size: 20, bold: true, color: WHITE })] })]
  });
  const dat = (text, w, bg = WHITE, bold = false) => new TableCell({
    borders: BORDERS, width: { size: w, type: WidthType.DXA },
    shading: { fill: bg, type: ShadingType.CLEAR },
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    children: [new Paragraph({ children: [new TextRun({ text, font: "Arial", size: 20, color: "222222", bold })] })]
  });
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [2600, 1690, 1690, 1690, 1690],
    rows: [
      new TableRow({ children: [hdr("Category", 2600), hdr("Median", 1690), hdr("Q25", 1690), hdr("Q75", 1690), hdr("Max", 1690)] }),
      new TableRow({ children: [dat("Cargo", 2600, LIGHT, true), dat("11.0 kn", 1690, LIGHT), dat("8.7 kn", 1690, LIGHT), dat("12.0 kn", 1690, LIGHT), dat("14.9 kn", 1690, LIGHT)] }),
      new TableRow({ children: [dat("Tanker", 2600), dat("10.5 kn", 1690), dat("10.2 kn", 1690), dat("11.5 kn", 1690), dat("12.0 kn", 1690)] }),
      new TableRow({ children: [dat("Passenger", 2600, LIGHT), dat("15.0 kn", 1690, LIGHT), dat("10.2 kn", 1690, LIGHT), dat("17.2 kn", 1690, LIGHT), dat("27.9 kn", 1690, LIGHT)] }),
      new TableRow({ children: [dat("Pleasure Craft", 2600), dat("10.3 kn", 1690), dat("7.6 kn", 1690), dat("10.7 kn", 1690), dat("18.9 kn", 1690)] }),
      new TableRow({ children: [dat("Sailing Yacht", 2600, LIGHT), dat("8.7 kn", 1690, LIGHT), dat("8.3 kn", 1690, LIGHT), dat("9.0 kn", 1690, LIGHT), dat("9.5 kn", 1690, LIGHT)] }),
      new TableRow({ children: [dat("Tug", 2600), dat("2.7 kn", 1690), dat("1.7 kn", 1690), dat("4.4 kn", 1690), dat("7.1 kn", 1690)] }),
    ]
  });
};

// ── Belge ─────────────────────────────────────────────────────────────────────
const doc = new Document({
  numbering: {
    config: [{ reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•",
      alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] }]
  },
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Arial", color: NAVY },
        paragraph: { spacing: { before: 360, after: 120 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: "Arial", color: TEAL },
        paragraph: { spacing: { before: 240, after: 80 }, outlineLevel: 1 } },
    ]
  },
  sections: [{
    properties: {
      page: { size: { width: 12240, height: 15840 }, margin: { top: 1080, right: 1080, bottom: 1080, left: 1080 } }
    },
    headers: {
      default: new Header({ children: [new Paragraph({
        alignment: AlignmentType.RIGHT,
        border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: TEAL, space: 4 } },
        children: [new TextRun({ text: "Bodrum–Kos–Rhodes · AIS Traffic Analysis · June 2026", font: "Arial", size: 18, color: GRAY })]
      })] })
    },
    footers: {
      default: new Footer({ children: [new Paragraph({
        alignment: AlignmentType.CENTER,
        border: { top: { style: BorderStyle.SINGLE, size: 4, color: TEAL, space: 4 } },
        children: [
          new TextRun({ text: "Page ", font: "Arial", size: 18, color: GRAY }),
          new TextRun({ children: [PageNumber.CURRENT], font: "Arial", size: 18, color: GRAY }),
          new TextRun({ text: " · github.com/sdnzthewitch/aegean-ais-analysis", font: "Arial", size: 18, color: GRAY }),
        ]
      })] })
    },
    children: [

      // ── KAPAK ─────────────────────────────────────────────────────────────
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 1440, after: 80 }, children: [
        new TextRun({ text: "BODRUM–KOS–RHODES SEA CORRIDOR", font: "Arial", size: 52, bold: true, color: NAVY })
      ]}),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 80 }, children: [
        new TextRun({ text: "AIS Live Traffic Analysis", font: "Arial", size: 36, color: TEAL })
      ]}),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 80, after: 80 }, children: [
        new TextRun({ text: "Turkish–Greek Aegean Boundary Sea Lane", font: "Arial", size: 26, italics: true, color: GRAY })
      ]}),
      divider(),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 80, after: 40 }, children: [
        new TextRun({ text: "Data Collection: 8–9 June 2026  ·  lat 36–38°N, lon 26.5–29°E", font: "Arial", size: 22, color: GRAY })
      ]}),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 0, after: 40 }, children: [
        new TextRun({ text: "Source: AISStream.io WebSocket API (live feed)", font: "Arial", size: 22, color: GRAY })
      ]}),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 80, after: 80 }, children: [
        new ExternalHyperlink({
          children: [new TextRun({ text: "Live Dashboard → aegean-ais-analysis.streamlit.app", font: "Arial", size: 22, color: "0563C1", underline: {} })],
          link: "https://aegean-ais-analysis-drkhjf4q8jslmuxyn9clae.streamlit.app/"
        })
      ]}),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 80, after: 1440 }, children: [
        new TextRun({ text: "Pilot Study · Version 1.0 · June 2026", font: "Arial", size: 20, italics: true, color: GRAY })
      ]}),
      new Paragraph({ children: [new PageBreak()] }),

      // ── 1. EXECUTIVE SUMMARY ──────────────────────────────────────────────
      h1("1. Executive Summary"),
      body("This report presents a live AIS (Automatic Identification System) traffic analysis of the Bodrum–Kos–Rhodes sea corridor, conducted on 8–9 June 2026. Data were collected in two one-hour sessions — evening and morning — via the AISStream.io WebSocket API, yielding 118 unique vessels and 2,267 clean position reports after geographic and quality filtering."),
      new Paragraph({ spacing: { before: 120, after: 120 }, children: [] }),
      kpiTable(),
      new Paragraph({ spacing: { before: 160, after: 80 }, children: [] }),

      body("Four headline findings emerged from the analysis:"),
      bullet("Pleasure Craft is the dominant vessel category (28 vessels, 24%), consistent with the Bodrum peninsula’s status as one of the Aegean’s premier yacht charter hubs.", true),
      bullet("Leisure traffic (Pleasure Craft + Sailing Yacht) accounts for 29.7% of all observed vessels — or 37.6% of vessels with an identified type — a strong early-summer signal ahead of the August peak season.", true),
      bullet("Passenger ferry activity is time-dependent: morning session recorded 15 ferry vessels vs. 13 in the evening (+15%), consistent with Bodrum–Kos and Marmaris–Rhodes morning departure schedules.", true),
      bullet("Cargo vessels transit the corridor at a median speed of 11.0 knots (IQR 8.7–12.0 kn); passenger vessels lead all categories at 15.0 kn median, reflecting high-speed catamaran services.", true),

      new Paragraph({ children: [new PageBreak()] }),

      // ── 2. METHODOLOGY ────────────────────────────────────────────────────
      h1("2. Methodology"),

      h2("2.1 Data Source"),
      body("AIS (Automatic Identification System) is an IMO-mandated VHF radio transponder system. Class A transponders (commercial vessels) broadcast position reports every 2–10 seconds underway and every 3 minutes at anchor; static data (Type 5) is broadcast every 6 minutes. AISStream.io aggregates these broadcasts from a network of terrestrial receivers, exposing a real-time WebSocket API."),
      body("Unlike historical AIS providers, AISStream.io’s free tier delivers only a live stream — data collection must occur in real time. This is a design choice, not a limitation of this study."),

      h2("2.2 Collection Sessions"),
      new Paragraph({ spacing: { before: 80, after: 120 }, children: [] }),
      sessionTable(),
      new Paragraph({ spacing: { before: 120, after: 80 }, children: [] }),
      body("Each session used a Python asyncio WebSocket client (src/collector.py) with automatic reconnection on connection drops. Messages were written to SQLite in batches of 50. The wider Aegean bounding box (lat 36–42°N, lon 22–30°E) was used for collection to ensure sufficient signal volume; geographic filtering to the study corridor was applied at the cleaning stage."),

      h2("2.3 Geographic Scope"),
      new Paragraph({ spacing: { before: 80, after: 120 }, children: [] }),
      warningBox(),
      new Paragraph({ spacing: { before: 120, after: 80 }, children: [] }),
      body("Raw data exploration revealed that AISStream.io receivers are concentrated on the Greek island arc (Kos, Rhodes, Samos). As a result, usable signal coverage is limited to:"),
      bullet("Bodrum peninsula and outer anchorages"),
      bullet("Marmaris bay entrance"),
      bullet("Open sea lanes between Turkey and the Dodecanese islands"),
      bullet("Kos and Rhodes port approaches"),
      body("The study area is therefore defined as the Bodrum–Kos–Rhodes sea corridor (lat 36–38°N, lon 26.5–29°E), not the full Turkish Aegean coast. This framing is scientifically honest and aligns with the actual data coverage."),

      h2("2.4 Data Pipeline"),
      bullet("collector.py — WebSocket client, SQLite writer, auto-reconnect"),
      bullet("cleaner.py — geographic filter, coordinate validation, speed filter (>50 kn removed), ShipStaticData JOIN for vessel names and type codes"),
      bullet("analysis.py — statistical analysis, figure generation"),
      bullet("app.py — Streamlit interactive dashboard"),
      body("ShipType numeric codes (IMO/ITU standard, 0–99) were mapped to eight readable categories. Median and IQR were used for speed statistics rather than mean and standard deviation because speed distributions are right-skewed: anchored vessels broadcast zero speed, pulling the mean down disproportionately."),

      new Paragraph({ children: [new PageBreak()] }),

      // ── 3. FINDINGS ───────────────────────────────────────────────────────
      h1("3. Key Findings"),

      h2("3.1 Vessel Category Distribution"),
      body("Figure 1 shows the distribution of vessel categories by unique MMSI count and total position reports. Pleasure Craft leads both metrics in the filtered corridor dataset."),
      new Paragraph({ spacing: { before: 80, after: 0 }, children: [] }),
      fig("01_ship_distribution.png", 600, 230),
      caption("Figure 1 — Vessel distribution by category (left: unique vessels · right: position reports)"),
      new Paragraph({ spacing: { before: 120, after: 80 }, children: [] }),
      findingsTable(),
      new Paragraph({ spacing: { before: 80, after: 80 }, children: [] }),
      body("The ‘Unknown’ count (25 vessels, 21%) reflects vessels for which ShipStaticData (Type 5/24 messages) were not received during the collection window. This is expected for one-hour sessions; static messages are broadcast only every 6 minutes, so some vessels will not have broadcast a static message during the collection period."),

      new Paragraph({ children: [new PageBreak()] }),

      h2("3.2 Speed Distributions"),
      body("Figure 2 presents violin plots of speed over ground (SOG) for each category, restricted to vessels under way (SOG > 0.5 knots). The inner box shows the median and IQR."),
      fig("02_speed_distributions.png", 620, 240),
      caption("Figure 2 — Speed distributions by vessel category (under-way vessels only · inner box: median + IQR)"),
      new Paragraph({ spacing: { before: 120, after: 80 }, children: [] }),
      speedTable(),
      new Paragraph({ spacing: { before: 120, after: 80 }, children: [] }),
      body("Why median instead of mean? Speed distributions are right-skewed: most vessels cruise at moderate speeds, but a few transit at full speed, creating a long right tail. The median is resistant to these extremes and provides a more representative central measure. IQR is preferred over standard deviation for the same reason."),
      body("Note: The relatively narrow IQR for Tankers (10.2–11.5 kn) and Sailing Yachts (8.3–9.0 kn) suggests operationally constrained speed profiles — tankers may follow fuel-optimal engine settings, while sailing yachts are wind-limited. Passenger vessels show the widest range (10.2–17.2 kn), consistent with a mix of slow car ferries and fast catamaran services."),

      h2("3.3 Traffic Density"),
      body("Figure 3 maps vessel density across the study area using a 0.25° × 0.25° grid (~27 km resolution). Hot spots identify the primary sea lanes and anchorage areas within the corridor."),
      fig("03_traffic_density.png", 480, 380),
      caption("Figure 3 — Traffic density heatmap (0.25° × 0.25° grid · unique vessel count per cell)"),

      new Paragraph({ children: [new PageBreak()] }),

      h2("3.4 Evening vs. Morning Comparison"),
      body("Figure 4 compares vessel counts between the two collection sessions. The most notable shift is in the Passenger category. The modest increase (13→15, +15%) is consistent with scheduled morning departures on routes such as Bodrum–Kos and Marmaris–Rhodes, though the two-session sample is insufficient to confirm causal attribution."),
      fig("04_session_comparison.png", 600, 230),
      caption("Figure 4 — Evening (Jun 8) vs Morning (Jun 9) vessel counts by category"),
      new Paragraph({ spacing: { before: 120, after: 80 }, children: [] }),
      body("Key changes from evening to morning:"),
      bullet("Passenger: 13 → 15 vessels (+15%) — morning ferry departures on Bodrum–Kos and Marmaris–Rhodes routes"),
      bullet("Cargo: 12 → 12 vessels (no change) — consistent transit traffic through the corridor"),
      bullet("Pleasure Craft: 25 → 21 vessels (−16%) — slightly less leisure activity in the morning session"),
      bullet("Sailing Yacht: 4 → 6 vessels — morning departures from anchorages"),

      new Paragraph({ children: [new PageBreak()] }),

      // ── 4. LIMITATIONS ────────────────────────────────────────────────────
      h1("4. Limitations & Methodological Notes"),
      bullet("Single early-summer snapshot: Two one-hour sessions in June cannot capture seasonal, weekly, or daily traffic patterns. August peak-season data will be collected for comparison."),
      bullet("AIS coverage gaps: İzmir, Çeşme, Kuşadası, and Çanakkale have no AISStream.io terrestrial receiver coverage. Findings cannot be generalized to the northern Turkish Aegean coast."),
      bullet("Unknown vessel type (21%): Vessels without received ShipStaticData are classified as Unknown. In a longer collection window, most would be identified as static messages accumulate."),
      bullet("AIS non-participation: Small recreational craft under 300 GT are not required to carry AIS. Actual leisure traffic density is likely higher than reported."),
      bullet("Position accuracy: AIS messages include a position accuracy flag (0 = >10 m, 1 = <10 m GNSS). Positional error is not analyzed in this study."),

      // ── 5. FUTURE WORK ────────────────────────────────────────────────────
      h1("5. Future Work"),
      body("This study will be replicated in August 2026 to enable a seasonal comparison between early summer (June) and peak summer (August) traffic patterns. The same pipeline (collector.py → cleaner.py → analysis.py) will be reused; new sessions will automatically merge into the existing SQLite database."),
      body("Planned extensions:"),
      bullet("August 2026 replication — peak season comparison"),
      bullet("Multi-day collection — capture weekly patterns (weekday vs weekend)"),
      bullet("AIS Class B filter — isolate leisure craft sub-analysis"),
      bullet("Route reconstruction — connect sequential positions per MMSI to visualize vessel trajectories"),

      // ── 6. TECHNICAL INFRASTRUCTURE ──────────────────────────────────────
      h1("6. Technical Infrastructure"),
      h2("Live Dashboard"),
      new Paragraph({ spacing: { before: 80, after: 40 }, children: [
        new TextRun({ text: "Interactive Streamlit dashboard: ", font: "Arial", size: 22 }),
        new ExternalHyperlink({
          children: [new TextRun({ text: "aegean-ais-analysis-drkhjf4q8jslmuxyn9clae.streamlit.app", font: "Arial", size: 22, color: "0563C1", underline: {} })],
          link: "https://aegean-ais-analysis-drkhjf4q8jslmuxyn9clae.streamlit.app/"
        })
      ]}),
      body("Features: vessel category filter, speed range slider, scatter map, density heatmap, bar/box/pie charts, summary statistics table."),

      h2("Source Code"),
      new Paragraph({ spacing: { before: 80, after: 40 }, children: [
        new TextRun({ text: "GitHub repository: ", font: "Arial", size: 22 }),
        new ExternalHyperlink({
          children: [new TextRun({ text: "github.com/sdnzthewitch/aegean-ais-analysis", font: "Arial", size: 22, color: "0563C1", underline: {} })],
          link: "https://github.com/sdnzthewitch/aegean-ais-analysis"
        })
      ]}),

      h2("Technology Stack"),
      bullet("Python 3.13 — websockets, pandas, sqlite3, matplotlib, seaborn, plotly, streamlit"),
      bullet("SQLite — lightweight embedded database; sessions accumulate without schema changes"),
      bullet("AISStream.io — real-time AIS WebSocket API (free tier)"),
      bullet("Streamlit Community Cloud — free dashboard hosting"),
      bullet("GitHub — version control; .env excluded via .gitignore"),

      // ── DATA SOURCE ───────────────────────────────────────────────────────
      divider(),
      body("Data source: AISStream.io real-time AIS WebSocket API. AIS data is publicly broadcast by vessels under IMO SOLAS regulations Chapter V. Collection date: 8–9 June 2026.", { color: GRAY, size: 18 }),
    ]
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("AIS_Traffic_Report_Aegean.docx", buffer);
  console.log("Rapor oluşturuldu: AIS_Traffic_Report_Aegean.docx");
});
