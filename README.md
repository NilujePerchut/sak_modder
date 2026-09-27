# sak_modder

Data-driven tool suite for designing custom 91mm Victorinox Swiss Army Knives, layer by layer.

`sak_builder.html` is a single-file web app: pick tools, stack layers, preview the front and back of the knife, see estimated thickness/weight, matching existing models, and the cheapest donor knives to buy for harvesting the layers you designed.

- Data source: [SAKwiki](https://sakwiki.com) (tools, models, layer compositions) and victorinox.com (official prices).
- CSV files hold the reference data; Python scripts generate the web app from them.

## Usage

1. Run `python3 build_webapp.py` (only needed after changing a CSV), then open `sak_builder.html` in any browser — no server required, it works offline from `file://`.
2. Click a tool on the left, pick a layer configuration, then drag rows (or use ▲/▼) to reorder and ✕ to remove a layer.
3. Read the thickness/weight estimates, matching models and shopping list on the right; use Export/Import to save or restore a stackup as JSON.

⚠️ **Disclaimer:** this project was entirely coded with AI and must not be taken seriously. Verify everything before buying or disassembling actual knives.

Licensed under the BSD 2-Clause License — see [LICENSE](LICENSE).
