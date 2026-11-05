"""Draw the order-book depth figure as an SVG in the site's style. No libraries.

Data: order_book_depth.json, from one run of the order-book repo's demo traders
(3 threads, seeds 42-44, 4,000 orders each), then engine.depth_snapshot(25).
The three threads interleave differently on every run, so the exact book differs
from run to run; the shape does not.

Bids and asks are told apart the 1-bit way: a dotted fill and a hatched fill,
both in ink, instead of green and red.

Run:  python3 tools/make_depth_chart.py   ->  img/order-book-depth.svg
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = json.loads((HERE / "order_book_depth.json").read_text())
OUT = HERE.parent / "img" / "order-book-depth.svg"

# Same palette and frame as make_market_chart.py.
BG, GRID, TEXT, DIM, INK = "#e5e3d4", "#cfcdbb", "#55554a", "#7d7c6c", "#2c2c26"
FONT = "IBM Plex Sans, -apple-system, Helvetica, Arial, sans-serif"
W, H = 800, 500
L, R, T, B = 72, 24, 72, 56
PW, PH = W - L - R, H - T - B


def cumulative(levels):
    out, total = [], 0
    for price, qty in levels:
        total += qty
        out.append((price, total))
    return out


bids = cumulative(DATA["bids"])   # best (highest) first
asks = cumulative(DATA["asks"])   # best (lowest) first
prices = [p for p, _ in bids + asks]
x0, x1 = min(prices) - 0.01, max(prices) + 0.01
ymax = max(c for _, c in bids + asks)
step = 10_000 if ymax > 30_000 else 5_000
ytop = (int(ymax / step) + 1) * step


def x(p):
    return L + (p - x0) / (x1 - x0) * PW


def y(q):
    return T + (1 - q / ytop) * PH


def step_polygon(levels):
    """Staircase from the best price outward, closed down to the baseline."""
    pts = [(x(levels[0][0]), y(0))]
    for i, (p, c) in enumerate(levels):
        pts.append((x(p), y(c)))
        nxt = levels[i + 1][0] if i + 1 < len(levels) else p
        pts.append((x(nxt), y(c)))
    pts.append((x(levels[-1][0]), y(0)))
    return " ".join(f"{a:.1f},{b:.1f}" for a, b in pts)


svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="{FONT}">',
       "<defs>",
       f'<pattern id="dots" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="4" fill="{BG}"/><rect width="1.5" height="1.5" fill="{INK}"/></pattern>',
       f'<pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" fill="{BG}"/><rect width="1.5" height="6" fill="{INK}"/></pattern>',
       "</defs>",
       f'<rect width="{W}" height="{H}" fill="{BG}"/>',
       f'<text x="{L}" y="30" fill="{INK}" font-size="17" font-weight="600">Order book depth</text>',
       f'<text x="{L}" y="52" fill="{DIM}" font-size="13">Cumulative resting quantity by price after {DATA["orders"]:,} seeded orders from 3 threads (one run of demo.py)</text>']

# Grid and y labels.
q = 0
while q <= ytop:
    yy = y(q)
    svg.append(f'<line x1="{L}" x2="{L + PW}" y1="{yy:.1f}" y2="{yy:.1f}" stroke="{GRID}"/>')
    svg.append(f'<text x="{L - 10}" y="{yy + 4:.1f}" fill="{DIM}" font-size="12" text-anchor="end">{q:,}</text>')
    q += step

# x labels every 10 cents.
tick = round(x0 * 10 + 0.999) / 10
while tick <= x1:
    xx = x(tick)
    svg.append(f'<text x="{xx:.1f}" y="{T + PH + 22}" fill="{DIM}" font-size="12" text-anchor="middle">{tick:.2f}</text>')
    tick = round(tick + 0.10, 2)
svg.append(f'<text x="{L + PW}" y="{T + PH + 42}" fill="{DIM}" font-size="11" text-anchor="end">Price</text>')

# The spread.
mid = (DATA["best_bid"] + DATA["best_ask"]) / 2
svg.append(f'<line x1="{x(mid):.1f}" x2="{x(mid):.1f}" y1="{T}" y2="{T + PH}" stroke="{DIM}" stroke-dasharray="3 4"/>')
svg.append(f'<text x="{x(mid) + 6:.1f}" y="{T + 14}" fill="{DIM}" font-size="11">bid {DATA["best_bid"]:.2f} / ask {DATA["best_ask"]:.2f}</text>')

# The two sides.
for levels, fill in ((bids, "url(#dots)"), (asks, "url(#hatch)")):
    svg.append(f'<polygon points="{step_polygon(levels)}" fill="{fill}" stroke="{INK}" stroke-width="2" stroke-linejoin="miter"/>')

# Legend.
lx, ly = L + 12, T + 34
for i, (name, fill) in enumerate((("Bids", "url(#dots)"), ("Asks", "url(#hatch)"))):
    yy = ly + i * 22
    svg.append(f'<rect x="{lx}" y="{yy - 11}" width="22" height="14" fill="{fill}" stroke="{INK}" stroke-width="1.5"/>')
    svg.append(f'<text x="{lx + 30}" y="{yy}" fill="{INK}" font-size="13">{name}</text>')

svg.append(f'<line x1="{L}" x2="{L + PW}" y1="{y(0):.1f}" y2="{y(0):.1f}" stroke="{INK}" stroke-width="1.5"/>')
svg.append("</svg>")
OUT.write_text("\n".join(svg) + "\n")
print(f"{len(bids)} bid / {len(asks)} ask levels, y to {ytop:,} -> {OUT}")
