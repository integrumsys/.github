#!/usr/bin/env python3
"""
Generate the Integrum Systems favicon.

The mark itself is not a favicon. Measured at 16px, 65% of its non-empty
pixels are partial alpha: the I stem and the S merge into a grey block. So
this is a reduced device drawn for the size, not a scaled-down mark - the
hexagon silhouette plus a single bar standing in for the S's middle arm.

Everything sits on the mark's own grid: a regular pointy-top hexagon with a
uniform perpendicular frame inset, and one band clipped to the interior.

Outputs, relative to the repo root:

  assets/integrumsys-favicon.svg      adapts to the tab bar's colour scheme
  assets/integrumsys-favicon.ico      16, 32 and 48px
  assets/integrumsys-favicon-180.png  apple-touch-icon, plated, no transparency
"""

import math
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"

INK = "#0B1220"
WHITE = "#FFFFFF"

SIZE = 100.0
CX = CY = SIZE / 2
R = 48.0  # circumradius; height fills the frame, width is R*sqrt(3)
APOTHEM = R * math.sqrt(3) / 2

FRAME = 13.0  # perpendicular frame thickness
BAR = 14.0  # bar thickness
SLOPE = 0.18  # shallow: a steeper bar pinches the counters shut at 16px

ICO_SIZES = (16, 32, 48)
TOUCH = 180  # apple-touch-icon, which wants a plate rather than transparency


def hexagon(r):
    h = r * math.sqrt(3) / 2
    return [
        (CX, CY - r), (CX + h, CY - r / 2), (CX + h, CY + r / 2),
        (CX, CY + r), (CX - h, CY + r / 2), (CX - h, CY - r / 2),
    ]


def clip(poly, convex):
    """Sutherland-Hodgman. The band must end up wholly inside the hexagon:
    with fill-rule evenodd, any part outside it would fill instead of cut."""
    out = poly
    for i in range(len(convex)):
        a, b = convex[i], convex[(i + 1) % len(convex)]
        ex, ey = b[0] - a[0], b[1] - a[1]

        def inside(p):
            return ex * (p[1] - a[1]) - ey * (p[0] - a[0]) >= 0

        src, out = out, []
        for j in range(len(src)):
            cur, prev = src[j], src[j - 1]
            ci, pi = inside(cur), inside(prev)
            if ci != pi:
                dx, dy = cur[0] - prev[0], cur[1] - prev[1]
                den = ex * dy - ey * dx
                if abs(den) > 1e-12:
                    t = (ex * (prev[1] - a[1]) - ey * (prev[0] - a[0])) / -den
                    out.append((prev[0] + t * dx, prev[1] + t * dy))
            if ci:
                out.append(cur)
        if not out:
            return []
    return out


def device(scale=1.0):
    """Ring plus bar: outer hexagon, inner hexagon, then the band."""
    r = R * scale
    inner = (r * math.sqrt(3) / 2 - FRAME * scale) * 2 / math.sqrt(3)
    x0, x1 = -60.0, 160.0

    def edge(x, off):
        return CY + SLOPE * (x - CX) + off

    half = BAR * scale / 2
    band = [
        (x0, edge(x0, -half)), (x1, edge(x1, -half)),
        (x1, edge(x1, half)), (x0, edge(x0, half)),
    ]
    return [hexagon(r), hexagon(inner), clip(band, hexagon(inner))]


def path_data(polys):
    return " ".join(
        "M " + " L ".join(f"{x:.2f} {y:.2f}" for x, y in p) + " Z"
        for p in polys
        if p
    )


def svg_adaptive():
    """A tab bar can be light or dark, and the icon has to survive both."""
    return f"""\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" \
height="100" role="img" aria-label="Integrum Systems">
  <style>
    .m {{ fill: {INK}; }}
    @media (prefers-color-scheme: dark) {{ .m {{ fill: {WHITE}; }} }}
  </style>
  <path class="m" d="{path_data(device())}" fill-rule="evenodd"/>
</svg>
"""


def svg_plated():
    return f"""\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" \
height="100" role="img" aria-label="Integrum Systems">
  <rect width="100" height="100" rx="22" fill="{INK}"/>
  <path d="{path_data(device(0.78))}" fill="{WHITE}" fill-rule="evenodd"/>
</svg>
"""


def svg_flat(ink):
    return f"""\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" \
height="100" role="img" aria-label="Integrum Systems">
  <path d="{path_data(device())}" fill="{ink}" fill-rule="evenodd"/>
</svg>
"""


def rasterize(svg_text, size, out):
    with tempfile.TemporaryDirectory() as td:
        src = Path(td) / "a.svg"
        src.write_text(svg_text, encoding="utf-8")
        subprocess.run(
            ["rsvg-convert", "-w", str(size), "-h", str(size), str(src), "-o", str(out)],
            check=True,
        )


def build_ico(frames):
    """Assemble a multi-size .ico from PNG bytes.

    Each size is rendered natively rather than downsampled from one large
    image, which is what a resave through an image library would do and what
    makes a 16px icon mushy. ICO entries may hold PNG data directly.
    """
    header = struct.pack("<HHH", 0, 1, len(frames))
    offset = len(header) + 16 * len(frames)
    entries, blobs = b"", b""
    for px, data in frames:
        entries += struct.pack(
            "<BBBBHHII", px if px < 256 else 0, px if px < 256 else 0,
            0, 0, 1, 32, len(data), offset,
        )
        blobs += data
        offset += len(data)
    return header + entries + blobs


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    written = []

    for name, text in (
        ("integrumsys-favicon.svg", svg_adaptive()),
        ("integrumsys-favicon-inverse.svg", svg_flat(WHITE)),
    ):
        (ASSETS / name).write_text(text, encoding="utf-8")
        written.append(ASSETS / name)

    if not shutil.which("rsvg-convert"):
        print("warning: rsvg-convert not on PATH, SVG only")
    else:
        touch = ASSETS / f"integrumsys-favicon-{TOUCH}.png"
        rasterize(svg_plated(), TOUCH, touch)
        written.append(touch)

        ico = ASSETS / "integrumsys-favicon.ico"
        with tempfile.TemporaryDirectory() as td:
            frames = []
            for px in ICO_SIZES:
                png = Path(td) / f"{px}.png"
                rasterize(svg_flat(INK), px, png)
                frames.append((px, png.read_bytes()))
            ico.write_bytes(build_ico(frames))
        written.append(ico)

    for path in written:
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
