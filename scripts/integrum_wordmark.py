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
OUT = HERE.parent / "assets"
sys.path.insert(0, str(HERE))

import integrum_is_svg as mk  # noqa: E402  (the mark, imported not copied)

INK = mk.INK
WHITE = mk.WHITE
TEAL = "#0E9AA7"  # available via `accent`, not shipped as an asset

CAP = 700.0  # design cap height; everything else is a ratio of it
STYLE = "hex"

# Corner treatments. stroke/track/cut are fractions of cap height.
# cut_h > cut_v tilts the chamfer toward the hexagon's own 30-degree edges.
STYLES = {
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
    ("E", "G"): -0.1082,
    ("E", "M"): +0.0023,
    ("G", "R"): +0.0354,
    ("I", "N"): +0.0853,
    ("M", "S"): +0.0409,
    ("N", "T"): -0.0641,
    ("R", "U"): -0.0046,
    ("S", "T"): -0.0641,
    ("S", "Y"): +0.0661,
    ("T", "E"): -0.1634,
    ("U", "M"): +0.0808,
    ("Y", "S"): +0.0375,
}


def skeleton(ch, H, w, ch_=0.0, cv_=0.0):
    """Centre-line polylines for one glyph in a box of width WIDTHS[ch]*H.

    The cut sizes are passed in because Y's stem has to meet the cut across
    its vertex, not the uncut vertex underneath it.
    """
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
            [(0.28 * W, 0.435 * H), (W - a, H)],
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
        # The vertex sits low so that once the cut is taken across it, the
        # chord lands near 0.48H. The stem starts at that chord: attached to
        # the uncut vertex it would hang below the cut, detached.
        vy = 0.675 * H
        leg = math.hypot(W / 2 - a, vy)
        d = min((ch_ + cv_) / 2, 0.45 * leg)
        return W, [
            [(a, 0), (W / 2, vy), (W - a, 0)],
            [(W / 2, vy * (1 - d / leg)), (W / 2, H)],
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
        legs = []
        for tx, ty in ((px, py), (rx, ry)):
            dx, dy = tx - qx, ty - qy
            length = math.hypot(dx, dy)
            if length < 1e-9:
                continue
            u = (dx / length, dy / length)
            legs.append((u, _cut(u, ch_, cv_), length))
        if len(legs) < 2:
            continue
        # Clamp both cutbacks by one factor. Clamping them independently
        # shortens one leg only, which tilts the cut off the family angle.
        scale = min(1.0, *(0.45 * ln / d for _, d, ln in legs if d > 0))
        for u, d, _ in legs:
            out.append((qx + u[0] * d * scale, qy + u[1] * d * scale))
    out.append(pts[-1])
    return out


def word_parts(text, H, style):
    """Per-letter polylines in absolute coordinates, plus total width.

    Kerned letters can overlap horizontally, so a rendered word cannot be cut
    back into letters by looking for blank columns. Anything measuring one
    letter against its neighbour has to come from here.
    """
    s = STYLES[style]
    w, track = s["stroke"] * H, s["track"] * H
    ch_, cv_ = s["cut_h"] * H, s["cut_v"] * H
    parts, x = [], 0.0
    for i, chx in enumerate(text):
        if chx == " ":
            x += track * 2.2
            continue
        gw, strokes = skeleton(chx, H, w, ch_, cv_)
        parts.append(
            (chx, [[(px + x, py) for px, py in chamfer(pl, ch_, cv_)] for pl in strokes])
        )
        if i < len(text) - 1:
            x += gw + track + KERN.get((chx, text[i + 1]), 0.0) * H
        else:
            x += gw
    return x, parts, w


def word(text, H, style):
    """Absolute-coordinate polylines for a word, plus its total ink width."""
    total, parts, w = word_parts(text, H, style)
    return total, [pl for _, pls in parts for pl in pls], w


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


def wordmark(text, style, ink=INK, ground=None, cap=CAP, only=None):
    """`only` renders just that letter index on the full canvas, for QA."""
    w_total, parts, w = word_parts(text, cap, style)
    if only is None:
        polys = [pl for _, pls in parts for pl in pls]
    else:
        polys = list(parts[only][1])
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
        # Carrying the descriptor makes the stacked block far less wide than
        # it is tall, which a 6.7:1 wordmark under a mark otherwise is not.
        mark_h = mark_height(stroke, 1.18)
        g, mark_w = mark_group(0, 0, mark_h, ink)
        W = max(main_w, mark_w) + 2 * p
        g, _ = mark_group(p + (W - 2 * p - mark_w) / 2, p, mark_h, ink)
        parts.append(g)
        wy = p + mark_h + 0.50 * cap
        left = p + (W - 2 * p - main_w) / 2
        place("INTEGRUM", left, wy, cap, ink, "c1")
        dy = wy + cap + desc_gap
        place(
            "SYSTEMS",
            left,
            dy,
            desc_cap,
            accent,
            "c2",
            track=fit_track("SYSTEMS", desc_cap, style, main_w),
        )
        return svg(W, dy + desc_cap + p, parts, defs, ground)

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


# filename suffix -> (ink, ground); ground None means transparent.
GROUNDS = {
    "": (INK, None),
    "-inverse": (WHITE, None),
    "-on-white": (INK, WHITE),
    "-on-black": (WHITE, INK),
}

# filename stem -> builder taking (ink, ground).
PIECES = {
    "integrumsys-wordmark": lambda i, g: wordmark("INTEGRUM", STYLE, ink=i, ground=g),
    "integrumsys-lockup": lambda i, g: lockup("h", STYLE, ink=i, ground=g),
    "integrumsys-lockup-stacked": lambda i, g: lockup("v", STYLE, ink=i, ground=g),
    "integrumsys-lockup-descriptor": lambda i, g: lockup("hd", STYLE, ink=i, ground=g),
}

# Lockups are wide, so avatar sizes do not apply; these are slide and
# signature widths. Only the transparent colourways get raster copies.
PNG_PIECES = ("integrumsys-lockup", "integrumsys-lockup-stacked")
PNG_GROUNDS = ("", "-inverse")
PNG_WIDTHS = (1200, 2400)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    written = []
    for stem, build_piece in PIECES.items():
        for suffix, (ink, ground) in GROUNDS.items():
            out = OUT / f"{stem}{suffix}.svg"
            out.write_text(build_piece(ink, ground), encoding="utf-8")
            written.append(out)

    if shutil.which("rsvg-convert"):
        for stem in PNG_PIECES:
            for suffix in PNG_GROUNDS:
                svg_path = OUT / f"{stem}{suffix}.svg"
                for width in PNG_WIDTHS:
                    png = OUT / f"{stem}{suffix}-{width}.png"
                    render(svg_path, png, width)
                    written.append(png)
    else:
        print("warning: rsvg-convert not on PATH, skipping PNG export")

    for out in written:
        print(f"Wrote {out}")


if __name__ == "__main__":
    main()
