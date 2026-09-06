#!/usr/bin/env python3
"""
Wordmark exploration for Integrum Systems. NOTHING HERE IS LOCKED.

Everything is generated so the directions stay comparable: one skeleton per
letter, drawn as monoline centre-lines on a shared grid, then given a
different corner treatment per direction. Change the treatment, not the
letters, and the comparison stays honest.

The brief comes from docs/brand/DESIGN_SYSTEM.md in the site repo:
"widened tracking, slightly squared terminals, tuned letterforms to feel
engineered", monoline, "must work in 1-color black/white". The palette's Ink
and Integrum Teal are used here; the accent stays well under the 10-15%
coverage the design system asks for.

Letters are stroked centre-lines rather than filled outlines, so weight and
tracking are single numbers rather than a redraw. Overshoot past the cap line
(the acute miters on M, N, Y) is trimmed by a clip band at cap height, which
is what gives the flat "cut" terminals the mark already has.

Regenerate with:  python3 prototyping/wordmark_lab.py
"""

import math
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
sys.path.insert(0, str(HERE.parent / "scripts"))

import integrum_is_svg as mk  # noqa: E402  (the locked mark, reused not copied)

INK = "#0B1220"
TEAL = "#0E9AA7"
WHITE = "#FFFFFF"
FOG = "#F4F7FB"

CAP = 700.0  # design cap height; everything else is a ratio of it

# Corner treatments. stroke/track/cut are fractions of cap height.
# cut_h > cut_v tilts the chamfer toward the hexagon's own 30-degree edges.
STYLES = {
    "square": dict(stroke=0.120, track=0.170, cut_h=0.00, cut_v=0.00),
    "chamfer": dict(stroke=0.120, track=0.170, cut_h=0.21, cut_v=0.21),
    "hex": dict(stroke=0.120, track=0.190, cut_h=0.27, cut_v=0.156),
    "label": dict(stroke=0.083, track=0.270, cut_h=0.00, cut_v=0.00),
}

# Ink width of each glyph as a fraction of cap height.
WIDTHS = {
    "I": 0.120, "N": 0.770, "T": 0.715, "E": 0.630, "G": 0.800,
    "R": 0.685, "U": 0.745, "M": 0.945, "S": 0.660, "Y": 0.715,
}


# Optical corrections where two flat sides face each other and the metric
# gap reads too open. Fractions of cap height, negative tightens.
KERN = {
    ("T", "E"): -0.030, ("N", "T"): -0.022, ("G", "R"): -0.014,
    ("R", "U"): -0.012, ("U", "M"): -0.012, ("Y", "S"): -0.038,
    ("T", "S"): -0.030, ("E", "M"): -0.014, ("S", "Y"): -0.028,
}


def skeleton(ch, H, w):
    """Centre-line polylines for one glyph in a box of width WIDTHS[ch]*H."""
    a = w / 2
    W = WIDTHS[ch] * H
    if ch == "I":
        return W, [[(a, 0), (a, H)]]
    if ch == "N":
        return W, [
            [(a, 0), (a, H)],
            [(W - a, 0), (W - a, H)],
            [(a, 0), (W - a, H)],
        ]
    if ch == "T":
        return W, [[(0, a), (W, a)], [(W / 2, 0), (W / 2, H)]]
    if ch == "E":
        return W, [
            [(W, a), (a, a), (a, H - a), (W, H - a)],
            [(a, H / 2), (0.82 * W, H / 2)],
        ]
    if ch == "G":
        return W, [
            [
                (0.95 * W, a), (a, a), (a, H - a), (W - a, H - a),
                (W - a, 0.520 * H), (0.46 * W, 0.520 * H),
            ]
        ]
    if ch == "R":
        return W, [
            [(a, 0), (a, H)],
            [(a, a), (W - a, a), (W - a, 0.435 * H), (a, 0.435 * H)],
            [(a, 0.435 * H), (W - a, H)],
        ]
    if ch == "U":
        return W, [[(a, 0), (a, H - a), (W - a, H - a), (W - a, 0)]]
    if ch == "M":
        return W, [[(a, H), (a, 0), (W / 2, 0.660 * H), (W - a, 0), (W - a, H)]]
    if ch == "S":
        return W, [
            [
                (W, a), (a, a), (a, H / 2), (W - a, H / 2),
                (W - a, H - a), (0, H - a),
            ]
        ]
    if ch == "Y":
        return W, [
            [(a, 0), (W / 2, 0.480 * H), (W - a, 0)],
            [(W / 2, 0.480 * H), (W / 2, H)],
        ]
    raise KeyError(ch)


def _cut(direction, ch_, cv_):
    """How far to cut back along a leg: axis-aware so chamfers can tilt."""
    ux, uy = direction
    if abs(uy) < 1e-9:
        return ch_
    if abs(ux) < 1e-9:
        return cv_
    return (ch_ + cv_) / 2


def chamfer(pts, ch_, cv_):
    """Replace each interior corner with a straight cut across it."""
    if ch_ <= 0 and cv_ <= 0:
        return pts
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        (px, py), (qx, qy), (rx, ry) = pts[i - 1], pts[i], pts[i + 1]
        for tx, ty in ((px, py), (rx, ry)):
            dx, dy = tx - qx, ty - qy
            leg = math.hypot(dx, dy)
            if leg < 1e-9:
                continue
            u = (dx / leg, dy / leg)
            d = min(_cut(u, ch_, cv_), 0.45 * leg)
            out.append((qx + u[0] * d, qy + u[1] * d))
    out.append(pts[-1])
    return out


def word(text, H, style):
    """Absolute-coordinate polylines for a word, plus its total ink width."""
    s = STYLES[style]
    w, track = s["stroke"] * H, s["track"] * H
    ch_, cv_ = s["cut_h"] * H, s["cut_v"] * H
    polys, x = [], 0.0
    for i, chx in enumerate(text):
        if chx == " ":
            x += track * 2.2
            continue
        gw, strokes = skeleton(chx, H, w)
        for pl in strokes:
            pl = chamfer(pl, ch_, cv_)
            polys.append([(px + x, py) for px, py in pl])
        if i < len(text) - 1:
            x += gw + track + KERN.get((chx, text[i + 1]), 0.0) * H
        else:
            x += gw
    return x, polys, w


def word_width(text, H, style):
    return word(text, H, style)[0]


def fit_track(text, H, style, target):
    """Tracking that makes `text` measure exactly `target` wide."""
    s = dict(STYLES[style])
    gaps = max(len(text.replace(" ", "")) - 1, 1)
    ink = sum(WIDTHS[c] * H for c in text if c != " ")
    ink += sum(KERN.get((a, b), 0.0) * H for a, b in zip(text, text[1:]))
    spaces = text.count(" ")
    return (target - ink) / (gaps + spaces * 2.2) / H


def poly_svg(polys, w, ink, cap_top, cap_bot, clip_id):
    body = "\n".join(
        '      <polyline points="%s"/>'
        % " ".join(f"{x:.1f},{y:.1f}" for x, y in pl)
        for pl in polys
    )
    return (
        f'    <g clip-path="url(#{clip_id})" fill="none" stroke="{ink}" '
        f'stroke-width="{w:.1f}" stroke-linecap="butt" stroke-linejoin="miter" '
        f'stroke-miterlimit="12">\n{body}\n    </g>'
    )


def clip_def(clip_id, x0, y0, x1, y1):
    return (
        f'  <clipPath id="{clip_id}"><rect x="{x0:.1f}" y="{y0:.1f}" '
        f'width="{x1 - x0:.1f}" height="{y1 - y0:.1f}"/></clipPath>'
    )


def mark_path():
    """The locked mark's path data, taken from the generator, never copied."""
    return " ".join(
        mk.subpath(p)
        for p in [
            mk.hexagon(mk.R),
            mk.upper_counter(),
            mk.lower_counter(),
            mk.right_counter(),
        ]
    )


MARK_BOX = (mk.CX - mk.APOTHEM, mk.CY - mk.R, mk.CX + mk.APOTHEM, mk.CY + mk.R)


def mark_group(x, y, height, ink):
    """Place the mark with its hexagon bbox at (x, y) and the given height."""
    x0, y0, x1, y1 = MARK_BOX
    s = height / (y1 - y0)
    tx, ty = x - x0 * s, y - y0 * s
    return (
        f'    <g transform="translate({tx:.2f},{ty:.2f}) scale({s:.5f})">\n'
        f'      <path d="{mark_path()}" fill="{ink}" fill-rule="evenodd"/>\n'
        f"    </g>"
    ), (x1 - x0) * s


def svg(width, height, parts, defs, ground=None):
    plate = (
        f'  <rect width="{width:.0f}" height="{height:.0f}" fill="{ground}"/>\n'
        if ground
        else ""
    )
    d = "<defs>\n" + "\n".join(defs) + "\n</defs>\n" if defs else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" '
        f'height="{height:.0f}" viewBox="0 0 {width:.0f} {height:.0f}" '
        f'role="img" aria-label="Integrum Systems">\n{d}{plate}'
        + "\n".join(parts)
        + "\n</svg>\n"
    )


PAD = 0.28  # margin around artwork, as a fraction of cap height


def wordmark(text, style, ink=INK, ground=None, cap=CAP):
    w_total, polys, w = word(text, cap, style)
    p = PAD * cap
    polys = [[(x + p, y + p) for x, y in pl] for pl in polys]
    cid = f"cap-{style}"
    W, H = w_total + 2 * p, cap + 2 * p
    defs = [clip_def(cid, 0, p, W, p + cap)]
    return svg(W, H, [poly_svg(polys, w, ink, p, p + cap, cid)], defs, ground)


def lockup(kind, style, ink=INK, accent=None, ground=None, cap=CAP):
    """Lockup layouts.

    'h'    mark + INTEGRUM
    'hd'   mark + INTEGRUM over a SYSTEMS descriptor, left aligned
    'hj'   as 'hd' but the descriptor justified to the wordmark's width
    'v'    mark above INTEGRUM, centred
    'two'  INTEGRUM over SYSTEMS at equal size, no mark

    The mark is sized so its 47-unit frame lands near the wordmark's stroke
    weight; at cap height it would read about half as heavy, which is the one
    thing that makes a naive lockup look wrong.
    """
    accent = accent or ink
    p = PAD * cap
    parts, defs = [], []
    main_w = word_width("INTEGRUM", cap, style)
    stroke = STYLES[style]["stroke"] * cap

    desc_cap = 0.42 * cap
    desc_gap = 0.34 * cap
    two_gap = 0.30 * cap

    def place(text, x, y, c, ink_, tag, track=None):
        st = style
        if track is not None:
            STYLES["_fit"] = {**STYLES[style], "track": track}
            st = "_fit"
        _, pls, w = word(text, c, st)
        pls = [[(px + x, py + y) for px, py in pl] for pl in pls]
        defs.append(clip_def(tag, 0, y, 1e5, y + c))
        parts.append(poly_svg(pls, w, ink_, y, y + c, tag))

    if kind == "two":
        d_track = fit_track("SYSTEMS", cap, style, main_w)
        W, H = main_w + 2 * p, 2 * cap + two_gap + 2 * p
        place("INTEGRUM", p, p, cap, ink, "c1")
        place("SYSTEMS", p, p + cap + two_gap, cap, accent, "c2", track=d_track)
        return svg(W, H, parts, defs, ground)

    if kind == "v":
        mark_h = 2.30 * cap
        g, mark_w = mark_group(0, 0, mark_h, ink)
        W = max(main_w, mark_w) + 2 * p
        g, _ = mark_group(p + (W - 2 * p - mark_w) / 2, p, mark_h, ink)
        parts.append(g)
        wy = p + mark_h + 0.50 * cap
        place("INTEGRUM", p + (W - 2 * p - main_w) / 2, wy, cap, ink, "c1")
        return svg(W, wy + cap + p, parts, defs, ground)

    mark_h = 1.95 * cap
    two_line = kind in ("hd", "hj")
    block_h = cap + (desc_gap + desc_cap if two_line else 0)
    total_h = max(mark_h, block_h)
    g, mark_w = mark_group(p, p + (total_h - mark_h) / 2, mark_h, ink)
    parts.append(g)
    wx = p + mark_w + 0.52 * cap
    wy = p + (total_h - block_h) / 2
    place("INTEGRUM", wx, wy, cap, ink, "c1")
    if two_line:
        dy = wy + cap + desc_gap
        track = (
            fit_track("SYSTEMS", desc_cap, style, main_w)
            if kind == "hj"
            else STYLES[style]["track"] * 1.9
        )
        place("SYSTEMS", wx, dy, desc_cap, accent, "c2", track=track)
    return svg(wx + main_w + p, total_h + 2 * p, parts, defs, ground)


def render(svg_path, png_path, width):
    subprocess.run(
        ["rsvg-convert", "-w", str(width), str(svg_path), "-o", str(png_path)],
        check=True,
    )


def write(name, content):
    path = OUT / f"{name}.svg"
    path.write_text(content, encoding="utf-8")
    return path


def sheet(rows, out_name, label_h=34, pad=26):
    """Contact sheet for review. Transparent art is flattened onto white."""
    from PIL import Image, ImageDraw, ImageFont

    tiles = []
    for label, name, width in rows:
        tmp = OUT / f".tmp-{name}-{width}.png"
        render(OUT / f"{name}.svg", tmp, width)
        im = Image.open(tmp).convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        bg.alpha_composite(im)
        tiles.append((label, bg.convert("RGB")))
        tmp.unlink()

    W = max(i.width for _, i in tiles) + 2 * pad
    H = sum(i.height for _, i in tiles) + len(tiles) * (label_h + pad) + pad
    canvas = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 19)
    except OSError:
        font = ImageFont.load_default()
    y = pad
    for label, im in tiles:
        draw.text((pad, y), label, fill=(110, 122, 140), font=font)
        y += label_h
        canvas.paste(im, (pad, y))
        y += im.height + pad
    canvas.save(OUT / out_name)
    return OUT / out_name


SHEETS = [
    (
        "sheet-1-directions.png",
        [
            ("A - SQUARE   right angles, instrumentation label", "wordmark-square", 1400),
            ("B - CHAMFER  45 degree corner cuts", "wordmark-chamfer", 1400),
            ("C - HEX      30 degree cuts, matched to the mark's edges", "wordmark-hex", 1400),
            ("D - LABEL    lighter stroke, wider tracking", "wordmark-label", 1400),
        ],
    ),
    (
        "sheet-2-lockups.png",
        [
            ("1 horizontal", "lockup-horizontal-hex", 1050),
            ("2 descriptor, left aligned", "lockup-descriptor-hex", 1050),
            ("3 descriptor, justified", "lockup-descriptor-justified-hex", 1050),
            ("4 two line, equal size", "lockup-twoline-hex", 800),
            ("5 stacked", "lockup-stacked-hex", 540),
        ],
    ),
    (
        "sheet-3-colour.png",
        [
            ("mono, Ink #0B1220", "lockup-descriptor-hex", 980),
            ("accent, descriptor in Integrum Teal", "lockup-descriptor-hex-teal", 980),
            ("reversed, white on Ink", "lockup-descriptor-hex-reversed", 980),
            ("two line in teal - over the 10-15% accent budget", "lockup-twoline-hex-teal", 740),
        ],
    ),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for f in OUT.glob("*"):
        f.unlink()

    made = []
    for style in STYLES:
        made.append(write(f"wordmark-{style}", wordmark("INTEGRUM", style)))
    for style in ("square", "chamfer", "hex"):
        for kind, tag in (
            ("h", "horizontal"),
            ("hd", "descriptor"),
            ("hj", "descriptor-justified"),
            ("v", "stacked"),
            ("two", "twoline"),
        ):
            made.append(write(f"lockup-{tag}-{style}", lockup(kind, style)))
        made.append(write(f"lockup-descriptor-{style}-teal", lockup("hd", style, accent=TEAL)))
        made.append(write(f"lockup-twoline-{style}-teal", lockup("two", style, accent=TEAL)))
        made.append(
            write(
                f"lockup-descriptor-{style}-reversed",
                lockup("hd", style, ink=WHITE, accent=TEAL, ground=INK),
            )
        )

    if not shutil.which("rsvg-convert"):
        print("warning: rsvg-convert not on PATH, SVGs only, no sheets")
        return
    for name, rows in SHEETS:
        sheet(rows, name)
    print(f"Wrote {len(made)} SVGs and {len(SHEETS)} sheets to "
          f"{OUT.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
