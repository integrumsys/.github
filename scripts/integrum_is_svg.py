#!/usr/bin/env python3
"""
Generate the Integrum Systems IS mark as a clean SVG.

This reproduces the hand-drawn v2 of the mark, with its coordinates rebuilt on
exact construction instead of traced by eye:

  * the outline is a true regular pointy-top hexagon (vertices top and bottom,
    vertical left and right edges), centred in the viewBox;
  * the frame is a uniform perpendicular inset of that hexagon, so every corner
    miters correctly instead of drifting a few units per vertex;
  * every point that sat on a hexagon edge in the drawing is computed from the
    hexagon rather than restated, so the mark stays welded together at any size;
  * the five diagonal "cut" edges (the two counters flanking the I's serif, the
    two undersides of the S's arms, and the top of the S's wedge) were drawn at
    slopes ranging 0.38-0.44; they are regularized to a single SLANT.

Nothing else is changed. The remaining constants are the drawn values.

Writes four colourways into assets/, relative to the repo root. The default is
black ink on a transparent ground - the most reusable, and what "the mark"
means when a filename carries no qualifier. The other three are variations of
it: the same geometry, differing only in ink and ground.

Each colourway is also rasterized to PNG at PNG_SIZES, for the places that
will not take an SVG (GitHub avatars among them). That step needs
rsvg-convert on PATH and is skipped with a warning if it is missing; the SVGs
are always written.
"""

import math
import shutil
import subprocess
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"

# Ink and White are the design system's own tokens. The mark was drawn in
# pure black; it uses Ink here so it can sit beside the wordmark without the
# two reading as a printing error.
INK = "#0B1220"
WHITE = "#FFFFFF"

# filename stem -> (ink, ground); ground None means transparent.
VARIANTS = {
    "integrumsys-mark": (INK, None),
    "integrumsys-mark-inverse": (WHITE, None),
    "integrumsys-mark-on-white": (INK, WHITE),
    "integrumsys-mark-on-black": (WHITE, INK),
}

SIZE = 1254

# GitHub wants an avatar of at least 500px and crops it to a rounded square;
# the hexagon sits well inside that crop at these sizes.
PNG_SIZES = (512, 1024)

# Hexagon: regular, pointy-top, centred in the viewBox.
CX = CY = SIZE / 2
R = 500.0
APOTHEM = R * math.sqrt(3) / 2

FRAME = 47.0  # perpendicular thickness of the outline
A_IN = APOTHEM - FRAME
R_IN = A_IN * 2 / math.sqrt(3)

LEFT_IN = CX - A_IN
RIGHT_IN = CX + A_IN

SLANT = 0.39  # shared slope of the diagonal cuts, positive = down to the right

# The I, on the left third.
STEM_L = 470.0  # right edge of both left-hand counters
STEM_R = 492.0  # right edge of the stem
SERIF_TOP = 394.0  # underside of the upper counter, measured at STEM_L
SERIF_H = 104.0  # thickness of the serif slab

# The S, on the right two thirds.
ARM_X = 634.0  # vertical left edge of the two arm cuts
ARM_TOP = 359.0  # underside of the top arm, measured at ARM_X
ARM_H = 126.0  # gap between the two arm cuts
WEDGE_Y = 832.0  # top of the wedge's tail, measured at STEM_R
WEDGE_KX = 631.0  # x of the wedge's lower point
WEDGE_LX = 884.0  # x of the wedge's right point

RT3 = math.sqrt(3)


def hexagon(r):
    """Regular pointy-top hexagon of circumradius r, clockwise from the top."""
    h = r * RT3 / 2
    return [
        (CX, CY - r),
        (CX + h, CY - r / 2),
        (CX + h, CY + r / 2),
        (CX, CY + r),
        (CX - h, CY + r / 2),
        (CX - h, CY - r / 2),
    ]


def upper_left_y(x):
    """y on the inner hexagon's upper-left edge."""
    return CY - R_IN / 2 - (x - LEFT_IN) / RT3


def lower_left_y(x):
    """y on the inner hexagon's lower-left edge."""
    return CY + R_IN / 2 + (x - LEFT_IN) / RT3


def upper_counter():
    """White notch above the I's serif, cutting it free of the frame."""
    return [
        (LEFT_IN, CY - R_IN / 2),
        (STEM_L, upper_left_y(STEM_L)),
        (STEM_L, SERIF_TOP),
        (LEFT_IN, SERIF_TOP + SLANT * (STEM_L - LEFT_IN)),
    ]


def lower_counter():
    """White field below the I's serif, left of the stem."""
    top = SERIF_TOP + SERIF_H
    return [
        (STEM_L, top),
        (STEM_L, lower_left_y(STEM_L)),
        (LEFT_IN, CY + R_IN / 2),
        (LEFT_IN, top + SLANT * (STEM_L - LEFT_IN)),
    ]


def right_counter():
    """White field around the S, right of the stem."""
    reach = SLANT * (RIGHT_IN - ARM_X)
    kx, ky = WEDGE_KX, WEDGE_Y + (WEDGE_KX - STEM_R) / RT3
    lx, ly = WEDGE_LX, ky - (WEDGE_LX - WEDGE_KX) / RT3
    return [
        (CX, CY - R_IN),
        (RIGHT_IN, CY - R_IN / 2),
        (RIGHT_IN, ARM_TOP + reach),
        (ARM_X, ARM_TOP),
        (ARM_X, ARM_TOP + ARM_H),
        (RIGHT_IN, ARM_TOP + ARM_H + reach),
        (RIGHT_IN, CY + R_IN / 2),
        (CX, CY + R_IN),
        (STEM_R, lower_left_y(STEM_R)),
        (STEM_R, WEDGE_Y),
        (kx, ky),
        (lx, ly),
        (STEM_R, ly - SLANT * (WEDGE_LX - STEM_R)),
        (STEM_R, upper_left_y(STEM_R)),
    ]


def subpath(pts):
    head, *rest = pts
    moves = " ".join(f"L {x:.1f} {y:.1f}" for x, y in rest)
    return f"M {head[0]:.1f} {head[1]:.1f} {moves} Z"


def build(ink, ground):
    parts = [hexagon(R), upper_counter(), lower_counter(), right_counter()]
    d = " ".join(subpath(p) for p in parts)
    plate = f'\n  <rect width="{SIZE}" height="{SIZE}" fill="{ground}"/>' if ground else ""
    return f"""\
<svg xmlns="http://www.w3.org/2000/svg"
     width="{SIZE}" height="{SIZE}" viewBox="0 0 {SIZE} {SIZE}"
     role="img" aria-label="Integrum Systems">{plate}
  <path d="{d}" fill="{ink}" fill-rule="evenodd" clip-rule="evenodd"/>
</svg>
"""


def rasterize(svg, png, size):
    subprocess.run(
        ["rsvg-convert", "-w", str(size), "-h", str(size), str(svg), "-o", str(png)],
        check=True,
    )


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    written = []
    for stem, (ink, ground) in VARIANTS.items():
        out = ASSETS / f"{stem}.svg"
        out.write_text(build(ink, ground), encoding="utf-8")
        written.append(out)

    if shutil.which("rsvg-convert"):
        for svg in list(written):
            for size in PNG_SIZES:
                png = svg.with_name(f"{svg.stem}-{size}.png")
                rasterize(svg, png, size)
                written.append(png)
    else:
        print("warning: rsvg-convert not on PATH, skipping PNG export")

    for out in written:
        print(f"Wrote {out}")


if __name__ == "__main__":
    main()
