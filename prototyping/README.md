# Wordmark prototyping

**Nothing in this directory is locked.** It exists so wordmark directions can be
compared side by side before one is chosen. The mark in `../assets/` is settled;
this is the type that goes next to it.

Once a direction is picked, the chosen generator moves to `../scripts/` and its
output to `../assets/`, and this directory goes away.

```
python3 prototyping/wordmark_lab.py
```

## Where to look

**Start in `out/00-COMPARE-THESE/`.** Those seven sheets each show the same
piece of artwork across all four directions, labelled A to D, which is the only
way to actually judge a corner treatment. Read them in order:

| Sheet | Answers |
|---|---|
| `1-wordmark.png` | Which direction reads best as INTEGRUM alone. |
| `2-letter-detail.png` | What the treatment actually does, at EGUM size. |
| `3-lockup-horizontal.png` | How each sits next to the mark. |
| `4-lockup-descriptor.png` | Same, with the SYSTEMS descriptor. |
| `5-lockup-twoline.png` | INTEGRUM over SYSTEMS at equal size, no mark. |
| `6-scale.png` | Where each direction stops working, 560px down to 110px. |
| `7-colour.png` | Mono, teal accent and reversed. Direction C only. |

Then `out/A-square/`, `B-chamfer/`, `C-hex/` and `D-label/` hold that
direction's ten SVGs under identical filenames, so any two directions can be
opened side by side.

Regenerating rewrites `out/` from scratch. Needs `rsvg-convert` for the sheets;
the SVGs themselves are dependency-free.

## Brief

From `docs/brand/DESIGN_SYSTEM.md` in the site repo: primary logo is a
wordmark, "widened tracking, slightly squared terminals, tuned letterforms to
feel engineered", monoline, and it must work in one colour. Palette is Ink
`#0B1220` with Integrum Teal `#0E9AA7` as the only accent, held under 10-15%
coverage.

## How it is built

Every letter is one skeleton of centre-lines on a shared grid, stroked rather
than drawn as an outline. Weight and tracking are therefore single numbers, and
the four directions differ **only** in corner treatment - so the comparison is
about the treatment, not about eight separate redraws.

Overshoot past the cap line, which is what the acute miters on M, N and Y
produce, is trimmed by a clip band at cap height. That is what gives the flat
cut terminals the hexagon mark already has.

The mark is imported from `scripts/integrum_is_svg.py` rather than copied, so
lockups cannot drift from the locked artwork.

## Directions

| | Treatment |
|---|---|
| **A square** | Right angles throughout. Closest to a plain instrumentation label. |
| **B chamfer** | Corners cut at 45 degrees. |
| **C hex** | Corners cut at 30 degrees, the angle of the hexagon's own slanted edges. The only direction with a geometric argument tying it to the mark. |
| **D label** | Square skeleton, lighter stroke, wider tracking. |

## Findings so far

- **The mark's frame is light for a lockup.** At cap height its 47-unit frame
  reads about half the weight of a wordmark stroke that works on its own, so
  the mark is sized from the type's stroke rather than from cap height:
  `mark_height()` targets a frame at 0.8x the stroke. That is why D's mark is
  visibly smaller than C's. The alternative is thickening the mark's frame,
  which would change the locked artwork.
- **A justified descriptor does not work.** INTEGRUM and SYSTEMS are 8 and 7
  letters, so forcing SYSTEMS to the wordmark's width needs either enormous
  tracking or a descriptor nearly as large as the wordmark. Left aligned at
  0.42x cap is the better default; sheet 2 shows both.
- **Minimum sizes**, from `6-scale.png`: the wordmark alone holds to about
  110px wide and the horizontal lockup to about 160px, with the descriptor
  lockup needing about 240px before SYSTEMS closes up. D fills in earliest,
  because a lighter stroke means a smaller mark at the same lockup width.
- Spacing is metric with a small optical kern table (`KERN`), not full optical
  spacing. `TE`, `YS` and `TS` are the pairs that needed it.

## Open

- Which direction, A to D.
- Which lockups become official artwork.
- The mark is `#000000` and the wordmark is Ink `#0B1220`. These should agree.
- Whether the geometric mark stays primary, which the current design system does
  not say - it scopes a geometric mark to favicon and social, with the wordmark
  as the primary logo.
