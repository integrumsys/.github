# Wordmark prototyping

**Direction C is chosen. Nothing here is merged yet.** When it is, the
generator moves to `../scripts/`, its output to `../assets/`, and this
directory goes away.

```
python3 prototyping/wordmark_lab.py   # artwork + review sheets
python3 prototyping/qa.py             # measurements
```

`out/00-REVIEW/` holds five sheets: the wordmark, the ten glyphs, the lockups,
the colourways, and a size ladder. The ten SVGs sit beside them in `out/`.

## Brief

From `docs/brand/DESIGN_SYSTEM.md` in the site repo: primary logo is a
wordmark, "widened tracking, slightly squared terminals, tuned letterforms to
feel engineered", monoline, and it must work in one colour. Palette is Ink
`#0B1220` with Integrum Teal `#0E9AA7` as the only accent, held under 10-15%
coverage. The brief's "squared terminals" is why stroke ends stay flat while
corners are cut.

## How it is built

Each letter is one skeleton of centre-lines on a shared grid, stroked rather
than drawn as an outline, so weight and tracking are single numbers. Corners
are cut at 30 degrees, the angle of the hexagon mark's own slanted edges. The
mark is imported from `scripts/integrum_is_svg.py`, never copied, so a lockup
cannot drift from the locked artwork.

Two rules hold the letterforms together, both of them learned the hard way:

- **Stems terminate flat at the cap line. A corner treatment applies only to
  interior corners that do not sit on it.** Otherwise the cut shortens the
  letter, which is what put M below the cap line in the first pass.
- **A cut is clamped by scaling both legs together.** Clamping each leg
  independently shortens one of them only, which tilts the cut off the family
  angle. Before this, G had a corner at 43 degrees among cuts at 30.

The mark is sized from the wordmark's stroke, not from cap height:
`mark_height()` targets a frame at 0.8x the stroke, because at cap height the
mark's 47-unit frame reads about half the weight of the type beside it.

## Second pass

Four defects, all found by measuring rather than looking:

- **Y was in two pieces.** The cut across its vertex removed the V's bottom
  above where the stem attached, so the stem floated. Y's vertex now sits at
  0.675 of cap height and the stem starts at the cut, not at the vertex under
  it. `qa.py` grows a connectivity check that reports the old Y as 2
  components and the new one as 1.
- **Spacing was solved against mislabeled pairs.** Kerned neighbours overlap
  horizontally, so cutting a rendered word at blank columns silently merged T
  and E and shifted every pair after them. Letters are now rendered one at a
  time onto a shared canvas (`wordmark(..., only=i)`) and measured from exact
  masks.
- **Equal white area is not a sufficient spacing target.** Solving for it
  alone collided T with E and S with Y. The solver now equalises area subject
  to a clearance floor, and weights near-field white by capping each row's
  contribution, so an open-sided letter like E is not read as loose.
- **G's corner cut sat at 43 degrees**, from the independent clamp above.

Measured after the pass, both words:

```
connectivity   every letter one piece
cap alignment  all flush (1px, rasterising tolerance)
spacing        spread 5% of mean (INTEGRUM), 9% (SYSTEMS)
clearance      never below 1.01 x stroke
corner cuts    every cut at 30.0 degrees
fill-in        counters open at 110px wide, 10th pct 3px
```

## Known and accepted

- **N, M and R read 0.97-1.00 on junction density.** A diagonal landing on a
  stem makes a solid patch; the alternative is thinning the join, which this
  face's flat monoline logic does not have a vocabulary for. Reviewed at size
  and left alone.
- **Cut lengths vary from 1.6x to 2.6x stroke.** The family is defined by
  angle, not length: where a leg is short, as on G's spur, the clamp scales
  the cut down while holding 30 degrees.
- **Spacing is solved for these two words only.** Any third word needs the
  kern table extended.

## Open before merge

- The mark is `#000000`, the wordmark Ink `#0B1220`. These should agree.
- Which lockups become official artwork, and their filenames in `assets/`.
- Whether the geometric mark stays primary. The current design system does not
  say so; it scopes a geometric mark to favicon and social, with the wordmark
  as the primary logo. That document needs updating either way.
