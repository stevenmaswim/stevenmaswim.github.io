"""Draw the market-data figure as an SVG, with no third-party libraries.

Data: tes_lgd_2026-08-29.csv, extracted read-only from the platform's archived
SQLite snapshot of the data platform (taken 2026-08-31) with:

    SELECT ts, bid, ask, mid FROM market_snapshots
    WHERE market_key = '<Top Esports series market>' AND source = 'live'
      AND ts BETWEEN '2026-08-29T08:30' AND '2026-08-29T14:30' ORDER BY ts;

Map-end times come from the same database's map_events table (score API).

Run:  python3 tools/make_market_chart.py   ->  img/market-tes-lgd.svg
"""

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
CSV = HERE / "tes_lgd_2026-08-29.csv"
OUT = HERE.parent / "img" / "market-tes-lgd.svg"

# map_events rows for this series (series_key 0x7df1d4ec...), times in UTC.
MAP_ENDS = [
    ("2026-08-29T09:49:35", "Map 1", "LGD"),
    ("2026-08-29T10:44:04", "Map 2", "LGD"),
    ("2026-08-29T11:38:25", "Map 3", "TES"),
    ("2026-08-29T12:44:39", "Map 4", "TES"),
]
ET = timezone(timedelta(hours=-4))  # EDT on Aug 29

# Canvas and plot area (SVG units). 16:10 to match the card thumbnails.
W, H = 800, 500
L, R, T, B = 64, 24, 72, 52
PW, PH = W - L - R, H - T - B

# Early-desktop palette to match the site (2026-11-05). Ink line on putty, grey markers.
BG, GRID, TEXT, DIM, HEAD = "#e5e3d4", "#cfcdbb", "#55554a", "#7d7c6c", "#2c2c26"
TEAL, BAND, ROSE = "#2c2c26", "rgba(44,44,38,0.12)", "#7d7c6c"   # line, bid-ask band, LGD markers
FONT = "IBM Plex Sans, -apple-system, Helvetica, Arial, sans-serif"
GAP = timedelta(minutes=2)  # a longer gap between polls breaks the line


def parse(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


rows = []
with open(CSV, newline="") as f:
    for ts, bid, ask, mid in csv.reader(f):
        rows.append((parse(ts), float(bid), float(ask), float(mid)))

t0, t1 = rows[0][0], rows[-1][0]
span = (t1 - t0).total_seconds()


def x(t):
    return L + (t - t0).total_seconds() / span * PW


def y(p):
    return T + (1 - p) * PH


# Split into runs wherever polling paused, so a gap is not drawn as a line.
runs, cur = [], [rows[0]]
for prev, row in zip(rows, rows[1:]):
    if row[0] - prev[0] > GAP:
        runs.append(cur)
        cur = []
    cur.append(row)
runs.append(cur)

svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="{FONT}">',
       f'<rect width="{W}" height="{H}" fill="{BG}"/>',
       f'<text x="{L}" y="30" fill="{HEAD}" font-size="17" font-weight="600">Top Esports vs LGD Gaming · LPL Playoffs, best of 5</text>',
       f'<text x="{L}" y="52" fill="{DIM}" font-size="13">Price that Top Esports wins the series (bid-ask band, mid line), polled every 15 s · Aug 29, 2026</text>']

# Horizontal grid: 0%, 25%, 50%, 75%, 100%.
for p in (0, 0.25, 0.5, 0.75, 1):
    yy = y(p)
    svg.append(f'<line x1="{L}" x2="{L + PW}" y1="{yy:.1f}" y2="{yy:.1f}" stroke="{GRID}" stroke-width="1"/>')
    svg.append(f'<text x="{L - 10}" y="{yy + 4:.1f}" fill="{DIM}" font-size="12" text-anchor="end">{int(p * 100)}%</text>')

# Hourly ticks in Eastern time.
tick = t0.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
while tick < t1:
    xx = x(tick)
    label = tick.astimezone(ET).strftime("%-I %p").replace("AM", "am").replace("PM", "pm")
    svg.append(f'<text x="{xx:.1f}" y="{T + PH + 22}" fill="{DIM}" font-size="12" text-anchor="middle">{label}</text>')
    tick += timedelta(hours=1)
svg.append(f'<text x="{L + PW}" y="{T + PH + 40}" fill="{DIM}" font-size="11" text-anchor="end">Eastern time</text>')

# Map-end markers from the score API.
for ts, name, winner in MAP_ENDS:
    xx = x(parse(ts + "Z"))
    colour = TEAL if winner == "TES" else ROSE
    svg.append(f'<line x1="{xx:.1f}" x2="{xx:.1f}" y1="{T}" y2="{T + PH}" stroke="{colour}" stroke-width="1" stroke-dasharray="3 4" opacity="0.7"/>')
    svg.append(f'<text x="{xx + 5:.1f}" y="{T + 14}" fill="{colour}" font-size="12" font-weight="600">{name}</text>')
    svg.append(f'<text x="{xx + 5:.1f}" y="{T + 29}" fill="{colour}" font-size="11">{winner}</text>')

# Bid-ask band and mid line, one path per run.
for run in runs:
    top = " ".join(f"{x(t):.1f},{y(a):.1f}" for t, b, a, m in run)
    bot = " ".join(f"{x(t):.1f},{y(b):.1f}" for t, b, a, m in reversed(run))
    svg.append(f'<polygon points="{top} {bot}" fill="{BAND}"/>')
    mid = " ".join(f"{x(t):.1f},{y(m):.1f}" for t, b, a, m in run)
    svg.append(f'<polyline points="{mid}" fill="none" stroke="{TEAL}" stroke-width="2" stroke-linejoin="round"/>')

svg.append("</svg>")
OUT.write_text("\n".join(svg) + "\n")
print(f"{len(rows)} snapshots, {len(runs)} run(s), {t0:%H:%M}-{t1:%H:%M} UTC -> {OUT}")
