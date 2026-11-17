# Style proposals — 91mm SAK Builder

Static mockups proposing four visual directions for a more elaborate/realistic knife
rendering and a more modern layout. Each file is standalone (open it directly in a
browser, works from `file://`, no build step).

Start at [index.html](index.html) (gallery), or open a mockup directly:

| # | File | Direction | Highlights |
|---|------|-----------|------------|
| 1 | [style-1-atelier.html](style-1-atelier.html) | **Atelier** — realistic product render | gradient Cellidor scales, brushed-steel layers, rivets, glossy cross emblem, soft shadows; warm background, rounded cards, big stat numerals |
| 2 | [style-2-blueprint.html](style-2-blueprint.html) | **Blueprint** — dark technical sheet | grid background, hatched layers, dashed centerlines, dimension arrows (91.0 mm / 17.2 mm), title block, monospace |
| 3 | [style-3-swiss.html](style-3-swiss.html) | **Swiss editorial** — typographic | white/black/red only, hairline rules, strict 3-column grid, sharp chips, grotesque numerals |
| 4 | [style-4-tactical.html](style-4-tactical.html) | **Tactical** — rugged outdoor | dark knurled scales, hard offset shadows, amber accent, condensed uppercase type |
| 5 | [style-5-3d.html](style-5-3d.html) | **3D orbit** — interactive CSS 3D (no library) | knife as CSS-3D cuboids (red scales + rivets + emblem, steel layers with tool chips); drag to orbit, wheel to zoom, explode slider; Blueprint/Tactical UI toggle |

All four mockups show the same demo content: a Climber-like stack
(blade + openers + scissors layers), front and back previews, thickness/weight
stats (17.2 mm / 84.1 g from `victorinox_91mm_layer_specs.csv`), matching models
and a shopping list.

Once a direction is picked, it will be ported into the `build_webapp.py` template
(CSS + the `renderSide()` SVG generator), then `sak_builder.html` regenerated.
