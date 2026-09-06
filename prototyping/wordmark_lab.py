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
        # Stems are separate strokes, exactly as N's are. Drawn as one
        # polyline the two peaks become interior corners, and a corner
        # treatment then cuts them back below the cap line.
        return W, [
            [(a, 0), (a, H)],
            [(W - a, 0), (W - a, H)],
            [(a, 0), (W / 2, 0.660 * H), (W - a, 0)],
        ]
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


# The mark's frame is 47 units on a 1000-unit hexagon. Sizing the mark so the
# frame lands near the wordmark's stroke keeps the two from fighting; a lighter
# wordmark therefore wants a smaller mark, which a fixed ratio would miss.
FRAME_RATIO = mk.FRAME / (mk.R * 2)


def mark_height(stroke, boost=1.0):
    return (0.80 * stroke / FRAME_RATIO) * boost


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
        mark_h = mark_height(stroke, 1.18)
        g, mark_w = mark_group(0, 0, mark_h, ink)
        W = max(main_w, mark_w) + 2 * p
        g, _ = mark_group(p + (W - 2 * p - mark_w) / 2, p, mark_h, ink)
        parts.append(g)
        wy = p + mark_h + 0.50 * cap
        place("INTEGRUM", p + (W - 2 * p - main_w) / 2, wy, cap, ink, "c1")
        return svg(W, wy + cap + p, parts, defs, ground)

    mark_h = mark_height(stroke)
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


def sheet(rows, out_path, label_h=34, pad=26, cols=1):
    """Contact sheet for review. Transparent art is flattened onto white."""
    from PIL import Image, ImageDraw, ImageFont

    tiles = []
    for label, name, width in rows:
        src = OUT / f"{name}.svg"
        tmp = OUT / ".tmp.png"
        render(src, tmp, width)
        im = Image.open(tmp).convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        bg.alpha_composite(im)
        tiles.append((label, bg.convert("RGB")))
        tmp.unlink()

    W = max(i.width for _, i in tiles) + 2 * pad
    H = sum(i.height for _, i in tiles) + len(tiles) * (label_h + pad) + pad
    canvas = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(canvas)
    font = _font(20)
    y = pad
    for label, im in tiles:
        draw.text((pad, y), label, fill=(96, 110, 130), font=font)
        y += label_h
        canvas.paste(im, (pad, y))
        y += im.height + pad
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path)


def _font(size):
    from PIL import ImageFont

    try:
        return ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size
        )
    except OSError:
        return ImageFont.load_default()


def scale_grid(names, widths, out_path, pad=24):
    """One row per direction, one column per render width."""
    from PIL import Image, ImageDraw

    def tile(name, w):
        tmp = OUT / ".tmp.png"
        render(OUT / f"{name}.svg", tmp, w)
        im = Image.open(tmp).convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        bg.alpha_composite(im)
        tmp.unlink()
        return bg.convert("RGB")

    grid = [[tile(n, w) for w in widths] for _, n in names]
    row_h = [max(i.height for i in r) for r in grid]
    W = max(sum(i.width for i in r) for r in grid) + pad * (len(widths) + 1)
    H = sum(row_h) + len(grid) * (34 + pad) + pad + 24
    canvas = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(canvas)
    f, fs = _font(20), _font(13)
    y = pad
    for (label, _), row, rh in zip(names, grid, row_h):
        draw.text((pad, y), label, fill=(96, 110, 130), font=f)
        y += 32
        x = pad
        for im, w in zip(row, widths):
            canvas.paste(im, (x, y + (rh - im.height) // 2))
            draw.text((x, y + rh + 4), f"{w}px", fill=(170, 180, 195), font=fs)
            x += im.width + pad
        y += rh + 24 + pad
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path)


DIRECTIONS = [
    ("A", "square", "right angles throughout"),
    ("B", "chamfer", "corners cut at 45 degrees"),
    ("C", "hex", "corners cut at 30 degrees, the mark's own edge angle"),
]

PIECES = [
    ("wordmark", lambda st: wordmark("INTEGRUM", st)),
    ("detail-EGUM", lambda st: wordmark("EGUM", st)),
    ("lockup-horizontal", lambda st: lockup("h", st)),
    ("lockup-descriptor", lambda st: lockup("hd", st)),
    ("lockup-descriptor-justified", lambda st: lockup("hj", st)),
    ("lockup-twoline", lambda st: lockup("two", st)),
    ("lockup-stacked", lambda st: lockup("v", st)),
    ("colour-teal-descriptor", lambda st: lockup("hd", st, accent=TEAL)),
    ("colour-teal-twoline", lambda st: lockup("two", st, accent=TEAL)),
    (
        "colour-reversed",
        lambda st: lockup("hd", st, ink=WHITE, accent=TEAL, ground=INK),
    ),
]


def main() -> None:
    if OUT.exists():
        for f in sorted(OUT.rglob("*"), reverse=True):
            f.unlink() if f.is_file() else f.rmdir()
    OUT.mkdir(parents=True, exist_ok=True)

    n = 0
    for letter, style, _ in DIRECTIONS:
        folder = OUT / f"{letter}-{style}"
        folder.mkdir(parents=True, exist_ok=True)
        for piece, fn in PIECES:
            (folder / f"{piece}.svg").write_text(fn(style), encoding="utf-8")
            n += 1

    if not shutil.which("rsvg-convert"):
        print(f"Wrote {n} SVGs. rsvg-convert missing, no comparison sheets.")
        return

    cmp_dir = OUT / "00-COMPARE-THESE"
    tag = {ltr: f"{ltr}-{st}" for ltr, st, _ in DIRECTIONS}

    def rows(piece):
        return [
            (f"{ltr}  {st.upper():<8} {note}", f"{tag[ltr]}/{piece}", width)
            for ltr, st, note in DIRECTIONS
        ]

    for piece, width, name in (
        ("wordmark", 1400, "1-wordmark.png"),
        ("detail-EGUM", 1000, "2-letter-detail.png"),
        ("lockup-horizontal", 1050, "3-lockup-horizontal.png"),
        ("lockup-descriptor", 1050, "4-lockup-descriptor.png"),
        ("lockup-twoline", 800, "5-lockup-twoline.png"),
    ):
        sheet([(l, n_, width) for l, n_, width in rows(piece)], cmp_dir / name)

    scale_grid(
        [(f"{ltr}  {st.upper()}", f"{tag[ltr]}/lockup-horizontal") for ltr, st, _ in DIRECTIONS],
        [560, 360, 240, 160, 110],
        cmp_dir / "6-scale.png",
    )
    sheet(
        [
            ("mono, Ink #0B1220", f"{tag['C']}/lockup-descriptor", 980),
            ("accent, descriptor in Integrum Teal", f"{tag['C']}/colour-teal-descriptor", 980),
            ("reversed, white on Ink", f"{tag['C']}/colour-reversed", 980),
            ("two line in teal, over the 10-15% accent budget", f"{tag['C']}/colour-teal-twoline", 740),
        ],
        cmp_dir / "7-colour.png",
    )
    print(f"Wrote {n} SVGs and 7 comparison sheets to {OUT.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
