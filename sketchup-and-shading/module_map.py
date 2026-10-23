"""Roof plan map of the 36 modules, each coloured by the share of its clear-sky direct sun lost to
shading over a year (annual-beam-loss-by-module.csv from shading_check.py). Writes module-map.svg.

Plan orientation matches the SketchUp roof plan: the long side of the roof runs left to right,
the front of the house (south east, where the rows face) is on the right, the north east side is at the top.
"""
import csv
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
S = 52                     # px per metre
ML, MT = 70, 120           # margins
HW, HL = 11.7, 17.7        # house X (across rows), Y (along roof)
W = int(ML * 2 + HL * S)
H = int(MT + HW * S + 150)

def sx(y):                 # house-local Y -> screen x (front, Y = 0, on the right)
    return ML + (HL - y) * S

def sy(x):                 # house-local X -> screen y (north east, X = 11.7, at the top)
    return MT + (HW - x) * S

loss = {}
with open(os.path.join(HERE, "annual-beam-loss-by-module.csv")) as f:
    r = csv.reader(f)
    next(r)
    for row, mod, val in r:
        loss[(int(row) - 1, int(mod) - 1)] = float(val)

def colour(v):
    # 0 % pale green, 5 % amber, 15 % and above deep red
    stops = [(0.0, (198, 232, 196)), (2.0, (236, 236, 170)), (6.0, (247, 196, 120)), (15.0, (214, 96, 77))]
    v = max(0.0, min(v, stops[-1][0]))
    for (a, ca), (b, cb) in zip(stops, stops[1:]):
        if v <= b:
            t = (v - a) / (b - a)
            return "#%02x%02x%02x" % tuple(round(ca[i] + t * (cb[i] - ca[i])) for i in range(3))
    return "#%02x%02x%02x" % stops[-1][1]

out = []
add = out.append
add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
    'font-family="Segoe UI, Arial, sans-serif">')
add(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')
add(f'<text x="{ML}" y="44" font-size="26" font-weight="700" fill="#1d2939">Direct sun lost to shading over a year, module by module</text>')
add(f'<text x="{ML}" y="72" font-size="17" fill="#475467">Clear-sky direct sun on each module, ray traced from 30 points per module on the SketchUp model\'s</text>')
add(f'<text x="{ML}" y="95" font-size="17" fill="#475467">dimensions, every 7th day of the year at 15 minute steps</text>')
# roof, parapet, stair room
add(f'<rect x="{sx(HL)}" y="{sy(HW)}" width="{HL * S}" height="{HW * S}" fill="#e7e5e1" stroke="#344054" stroke-width="2"/>')
add(f'<rect x="{sx(HL - 0.2)}" y="{sy(HW - 0.2)}" width="{(HL - 0.4) * S}" height="{(HW - 0.4) * S}" fill="#f4f3f1" stroke="#98a2b3" stroke-width="1"/>')
add(f'<rect x="{sx(6.95)}" y="{sy(10.95)}" width="{2.5 * S}" height="{2.5 * S}" fill="#b9a27a" stroke="#344054" stroke-width="1.5"/>')
add(f'<text x="{sx(5.7)}" y="{sy(9.7) - 4}" font-size="15" font-weight="600" text-anchor="middle" fill="#1d2939">Stair</text>')
add(f'<text x="{sx(5.7)}" y="{sy(9.7) + 15}" font-size="15" font-weight="600" text-anchor="middle" fill="#1d2939">room</text>')
# modules: plan footprint of each tilted module is 1.134 m (X) by 1.87 m (Y)
plan_d = 1.99 * math.cos(math.radians(20))
for (r, c), v in sorted(loss.items()):
    x0 = 0.80 + c * 1.154
    y0 = 0.915 + r * 2.80
    left, right = sx(y0 + plan_d), sx(y0)
    top, bottom = sy(x0 + 1.134), sy(x0)
    add(f'<rect x="{left:.1f}" y="{top:.1f}" width="{right - left:.1f}" height="{bottom - top:.1f}" '
        f'fill="{colour(v)}" stroke="#344054" stroke-width="1"/>')
    add(f'<text x="{(left + right) / 2:.1f}" y="{(top + bottom) / 2 + 6:.1f}" font-size="17" font-weight="600" '
        f'text-anchor="middle" fill="#1d2939">{v:.1f}%</text>')
# low edge marks: a thick line on the front (low) edge of each row
for r in range(6):
    y0 = 0.915 + r * 2.80
    add(f'<line x1="{sx(y0):.1f}" y1="{sy(0.80 + 5 * 1.154 + 1.134):.1f}" x2="{sx(y0):.1f}" y2="{sy(0.80):.1f}" '
        'stroke="#1d2939" stroke-width="3"/>')
# north arrow: true north in this plan points up and to the left
nx, ny = W - 120, 175
dx, dy = -math.cos(math.radians(32)), -math.sin(math.radians(32))
L = 46
add(f'<line x1="{nx - dx * L / 2:.1f}" y1="{ny - dy * L / 2:.1f}" x2="{nx + dx * L / 2:.1f}" y2="{ny + dy * L / 2:.1f}" '
    'stroke="#1d2939" stroke-width="3" marker-end="url(#a)"/>')
add('<defs><marker id="a" markerWidth="10" markerHeight="10" refX="6" refY="5" orient="auto">'
    '<path d="M0,0 L10,5 L0,10 z" fill="#1d2939"/></marker></defs>')
add(f'<text x="{nx + dx * L / 2 - 6:.1f}" y="{ny + dy * L / 2 - 10:.1f}" font-size="18" font-weight="700" fill="#1d2939">N</text>')
# side labels
add(f'<text x="{sx(0) + 12}" y="{sy(HW / 2)}" font-size="16" fill="#475467" transform="rotate(90 {sx(0) + 12} {sy(HW / 2)})" '
    'text-anchor="middle">Front of the house, rows face this way (148°)</text>')
add(f'<text x="{(sx(0) + sx(HL)) / 2}" y="{sy(0) + 30}" font-size="16" fill="#475467" text-anchor="middle">South west parapet</text>')
# legend
lx, ly = ML, sy(0) + 62
add(f'<text x="{lx}" y="{ly + 16}" font-size="16" fill="#344054">Share lost:</text>')
for i, v in enumerate([0, 1, 2, 4, 6, 10, 15]):
    add(f'<rect x="{lx + 100 + i * 82}" y="{ly}" width="74" height="24" fill="{colour(v)}" stroke="#344054" stroke-width="1"/>')
    add(f'<text x="{lx + 137 + i * 82}" y="{ly + 17}" font-size="15" text-anchor="middle" fill="#1d2939">{v}%{"+" if v == 15 else ""}</text>')
add(f'<text x="{lx + 100 + 7 * 82 + 14}" y="{ly + 17}" font-size="15" fill="#475467">Thick line: low front edge of each row</text>')
add('</svg>')
with open(os.path.join(HERE, "module-map.svg"), "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print(W, H)
