#!/usr/bin/env python3
"""
Measurements on the generated wordmark. Run after integrum_wordmark.py.

Stroke weight is guaranteed by construction, so there is no point measuring it.
What can go wrong and cannot be seen by eye is checked here instead:

  cap alignment   every letter reaching the cap line and the baseline
  spacing         the white AREA between neighbours, which is what the eye
                  reads as rhythm; a bounding-box gap is not the same thing
  cut family      every corner cut sharing one angle and a similar length
  clots           local ink density where a diagonal lands on a stem
  fill-in         counters surviving at small sizes

    python3 scripts/qa_wordmark.py
"""

import math
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import integrum_wordmark as L  # noqa: E402

STYLE = "hex"
WORDS = ("INTEGRUM", "SYSTEMS")


def raster(svg_text, height=None, width=None):
    with tempfile.TemporaryDirectory() as td:
        s, p = Path(td) / "a.svg", Path(td) / "a.png"
        s.write_text(svg_text, encoding="utf-8")
        arg = ["-h", str(height)] if height else ["-w", str(width)]
        subprocess.run(["rsvg-convert", *arg, str(s), "-o", str(p)], check=True)
        return np.array(Image.open(p).convert("RGBA"))[..., 3] > 128


def letter_masks(text, height=900):
    """One raster per letter on a shared canvas.

    Kerned neighbours overlap horizontally, so slicing a rendered word at
    blank columns silently merges pairs like T and E and mislabels every
    measurement after them. Each letter is rendered on its own instead.
    """
    return [
        raster(L.wordmark(text, STYLE, only=i), height=height)
        for i in range(len(text.replace(" ", "")))
    ]


def band(ink):
    rows = ink.any(axis=1)
    top = rows.argmax()
    bot = len(rows) - rows[::-1].argmax() - 1
    return top, bot, bot - top


def components(mask):
    """Number of connected blobs, so a detached part cannot slip through."""
    seen = np.zeros_like(mask, dtype=bool)
    h, w = mask.shape
    n = 0
    for sy, sx in zip(*np.nonzero(mask)):
        if seen[sy, sx]:
            continue
        n += 1
        stack = [(sy, sx)]
        seen[sy, sx] = True
        while stack:
            y, x = stack.pop()
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
    return n


def check_connectivity(masks, text):
    print("\n-- connectivity (each letter must be one piece) --")
    bad = []
    for ch, m in zip(text, masks):
        n = components(m)
        if n != 1:
            bad.append(f"{ch}={n}")
    print("   all single pieces" if not bad else "   BROKEN: " + ", ".join(bad))


def check_alignment(masks, ink, text):
    top, bot, _ = band(ink)
    print("\n-- cap alignment (px off the line) --")
    # Each letter is rasterised separately, so a 1px disagreement is the
    # alpha threshold, not the geometry.
    bad, worst = [], 0
    for ch, m in zip(text, masks):
        r = m.any(axis=1)
        t = r.argmax() - top
        b = (len(r) - r[::-1].argmax() - 1) - bot
        worst = max(worst, abs(t), abs(b))
        if abs(t) > 1 or abs(b) > 1:
            bad.append(f"{ch} top{t:+d} bottom{b:+d}")
    print(
        f"   all flush (worst {worst}px, within rasterising tolerance)"
        if not bad
        else "   OFF: " + ", ".join(bad)
    )


def check_spacing(masks, ink, text):
    """White area and clearance between neighbours, from exact letter masks."""
    top, bot, cap = band(ink)
    stroke = L.STYLES[STYLE]["stroke"] * cap
    reach = 0.30 * cap
    print("\n-- spacing (area x1000 of cap^2, clearance in strokes) --")
    rows = []
    for i in range(len(masks) - 1):
        a, b = masks[i], masks[i + 1]
        total, closest = 0, 1e9
        for y in range(top, bot + 1):
            la, lb = np.flatnonzero(a[y]), np.flatnonzero(b[y])
            if not len(la) or not len(lb):
                continue
            d = lb[0] - la[-1]
            total += min(max(0, d), reach)
            closest = min(closest, d)
        rows.append((text[i : i + 2], total / cap**2 * 1000, closest / stroke))
    mean = sum(r[1] for r in rows) / len(rows)
    for pair, area, clear in rows:
        dev = (area - mean) / mean * 100
        flag = "  <-- uneven" if abs(dev) > 12 else ""
        tight = "  <-- tight" if clear < 0.70 else ""
        print(f"   {pair}  area {area:6.1f} ({dev:+5.1f}%)  clear {clear:4.2f}{flag}{tight}")
    spread = (max(r[1] for r in rows) - min(r[1] for r in rows)) / mean * 100
    print(f"   spread {spread:.0f}% of mean, tightest clearance "
          f"{min(r[2] for r in rows):.2f} x stroke")


def check_cuts():
    """Every corner cut should share one angle and sit in one length band."""
    H = L.CAP
    s = L.STYLES[STYLE]
    w = s["stroke"] * H
    ch_, cv_ = s["cut_h"] * H, s["cut_v"] * H
    print("\n-- corner cuts (skeleton chord, angle from horizontal) --")
    seen = []
    for letter in "INTEGRUMSY":
        _, strokes = L.skeleton(letter, H, w, ch_, cv_)
        for pl in strokes:
            cut = L.chamfer(pl, ch_, cv_)
            if len(cut) == len(pl):
                continue
            for i in range(1, len(cut) - 2, 2):
                (x0, y0), (x1, y1) = cut[i], cut[i + 1]
                d = math.hypot(x1 - x0, y1 - y0)
                if d < 1e-6:
                    continue
                ang = abs(math.degrees(math.atan2(y1 - y0, x1 - x0)))
                ang = min(ang, 180 - ang)
                seen.append((letter, d, ang))
    for letter, d, ang in seen:
        print(f"   {letter}  chord {d:6.1f}  ({d / w:4.2f} x stroke)  {ang:5.1f} deg")
    angs = [a for _, _, a in seen]
    print(f"   angles {min(angs):.1f} to {max(angs):.1f} deg")


def check_clots(masks, ink, text):
    top, bot, cap = band(ink)
    w = L.STYLES[STYLE]["stroke"] * cap
    r = max(2, int(0.7 * w))
    integral = np.pad(ink.astype(np.int32), ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    H_, W_ = ink.shape
    print("\n-- junction density (1.0 = a solid disc of ink) --")
    out = []
    for ch, m in zip(text, masks):
        best = 0.0
        for y, x in zip(*np.nonzero(m)):
            a, b = max(0, y - r), min(H_, y + r + 1)
            c, d = max(0, x - r), min(W_, x + r + 1)
            v = (
                integral[b, d] - integral[a, d] - integral[b, c] + integral[a, c]
            ) / ((b - a) * (d - c))
            best = max(best, v)
        out.append((best, ch))
    for v, ch in sorted(out, reverse=True):
        print(f"   {ch}  {v:.3f}{'   <-- clot' if v > 0.95 else ''}")


def check_fill(text):
    """Narrowest white channel at small sizes: what closes up first."""
    print("\n-- fill-in risk (narrowest counters, px) --")
    for px in (240, 160, 110):
        ink = raster(L.wordmark(text, STYLE), width=px)
        top, bot, cap = band(ink)
        widths = []
        for y in range(top, bot + 1):
            row = ink[y]
            idx = np.flatnonzero(row)
            if len(idx) < 2:
                continue
            n = 0
            for v in row[idx[0] : idx[-1] + 1]:
                if not v:
                    n += 1
                elif n:
                    widths.append(n)
                    n = 0
        widths.sort()
        p10 = widths[len(widths) // 10] if widths else 0
        med = widths[len(widths) // 2] if widths else 0
        verdict = "closing" if p10 < 2 else ("tight" if p10 < 3 else "open")
        print(
            f"   {px:>4}px wide (cap {cap}px): 10th pct {p10}px, "
            f"median {med}px  -> {verdict}"
        )


def main():
    for text in WORDS:
        masks = letter_masks(text)
        ink = np.logical_or.reduce(masks)
        print(f"\n=== {text} ===")
        check_connectivity(masks, text)
        check_alignment(masks, ink, text)
        check_spacing(masks, ink, text)
        check_clots(masks, ink, text)
        check_fill(text)
    check_cuts()


if __name__ == "__main__":
    main()
