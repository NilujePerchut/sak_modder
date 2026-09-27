#!/usr/bin/env python3
"""Build the 91mm per-layer thickness & weight table.

Method: SAKwiki publishes total width (thickness) and weight for most 91mm
models. Each model is a known sum of physical layers (see
victorinox_91mm_model_layers.csv). Total = sum(layer contributions), so the
layer contributions solve an overdetermined linear system, solved by least
squares (normal equations, pure Python).

Data-quality rules (documented, not guessed):
- The blade layer and the scales/rivets are present in every model; their
  contributions are inseparable in the data. The blade-layer value therefore
  INCLUDES the fixed scales/rivets contribution.
- Layers that always co-occur in every published model (spatula+electrician,
  combo-extra+serrated+watch-case-opener, coffee-spatula+nozzle-remover)
  cannot be individually resolved: they are fitted as one group and the group
  value is split evenly across members.
- Models with electronic scale modules (clock/altimeter/barometer) are excluded
  from the fit: the module thickness varies by model and is a scale feature,
  not a layer (TimeKeeper, Altimeter, Traveller, Voyager, + their variants).
- Baker's Knife (Alox, single layer) and Modeler (no published width) are
  excluded. Divot layer appears only in SwissChamp XL, which has no published
  width/weight: it needs a physical measurement.
- Scale tools (toothpick/tweezers/pen/pin) are out of scope.

Widths & weights below were taken verbatim from each model's SAKwiki page
(Physical Specifications, first spec block, regular Cellidor configuration).
"""

import csv

# ---------------------------------------------------------------------------
# SAKwiki verified specs: model -> (width_mm, weight_g)
# ---------------------------------------------------------------------------
SAKWIKI_SPECS = {
    # 2 layers
    "American Eagle":         (13.9, 61.7),
    "Compact":                (15.0, 64.5),
    "DofE Pocket Tool":       (14.0, 65.0),
    "Scientist":              (15.0, 63.2),
    "Spartan":                (13.8, 59.64),
    "Special Mechanic":       (15.6, 81.7),
    "Tinker":                 (13.7, 60.5),
    "Lumberjack Big":         (15.0, 64.5),
    "Golfer":                 (14.8, 67.0),    # divot tool version
    # 3 layers
    "Automobile":             (16.6, 85.0),
    "Automobile Special":     (16.6, 81.0),
    "Camper":                 (16.2, 73.9),
    "Climber":                (17.0, 82.7),
    "Companion":              (18.0, 82.0),    # Cellidor scales
    "Clipper":                (16.5, 77.4),
    "Cybertool S (29)":       (21.0, 96.1),
    "FASS 90":                (19.5, 87.2),
    "Hiker":                  (16.6, 77.0),
    "Mechanic":               (18.1, 99.4),
    "Passenger":              (17.3, 80.3),
    "Picnicker":              (16.4, 77.6),
    "Spartan Lite":           (19.5, 84.0),
    "Super Tinker":           (17.0, 84.6),
    "Trail Guide":            (17.4, 83.4),
    "Wild Turkey":            (16.4, 76.7),
    "Yeoman":                 (18.35, 86.2),
    # 4 layers
    "Angler":                 (20.8, 112.5),
    "Bass Fishing":           (20.8, 115.0),
    "CampFlame":              (26.8, 135.5),
    "Climber Lite":           (22.0, 100.0),
    "Cybertool M (34)":       (28.0, 153.7),
    "CyberYeoman":            (24.5, 112.0),
    "Deluxe Tinker":          (21.9, 125.0),
    "Explorer":               (20.7, 101.0),
    "Fieldmaster":            (19.4, 101.0),
    "Fisherman":              (19.5, 99.0),
    "Grand Prix":             (19.7, 105.5),   # later model with keyring
    "Huntsman":               (19.6, 97.0),
    "Master Electrician":     (24.0, 124.0),
    "Master Gardener":        (22.0, 101.0),
    "Mountaineer":            (20.5, 109.1),
    "SwissFlame":             (27.7, 142.0),
    # 5 layers
    "Barista Tool":           (24.0, 136.0),
    "Deluxe Angler / Waterman": (24.0, 137.0),
    "Handyman 7236maU":       (22.0, 121.0),
    "Huntsman Lite":          (24.8, 121.5),
    "Luxury Automobile":      (22.0, 127.0),
    "Master Craftsman":       (22.0, 119.0),
    "Motorist":               (24.4, 135.0),
    "Outdoorsman-Original":   (22.6, 118.0),
    "Ranger":                 (22.0, 117.4),
    "Troubleshooter":         (24.5, 141.5),
    # 6+ layers
    "Craftsman":              (27.0, 159.0),
    "Expedition Lite":        (30.3, 143.0),
    "Handyman":               (27.5, 155.4),
    "Outdoorsman":            (25.0, 133.0),
    "Champion Plus":          (28.0, 148.9),
    "Cybertool L (41)":       (33.0, 188.0),
    "Cybertool Lite":         (33.5, 173.9),
    "SwissChamp":             (33.0, 185.0),
    "SwissChamp XLT":         (42.0, 247.0),
    "SwissChamp XAVT":        (64.6, 351.0),
    "SwissChamp XXL":         (62.0, 353.0),
    "SwissChamp XXLT":        (65.8, 384.0),
}

# Excluded from the fit (see module docstring)
EXCLUDE = {
    "Baker's Knife",          # Alox scales, single layer
    "TimeKeeper",             # clock bulge in scales
    "Altimeter", "Altimeter Plus",
    "Traveller", "Voyager", "Traveller Lite", "Voyager Lite",
    "Modeler",                # no published width
    "SwissChamp XL",          # no published width/weight
}

# CSV column -> fit key for victorinox_91mm_model_layers.csv
CSV_COL_TO_KEY = {
    "Blade layer": "blade",
    "Openers layer": "openers",
    "Scissors layer": "scissors",
    "Pliers layer": "pliers",
    "Wood saw layer": "wood_saw",
    "Metal saw layer": "metal_saw",
    "Magnifier layer": "magnifier",
    "Fish scaler layer": "fish_scaler",
    "Spatula layer": "grp_spatula_electrician",
    "Electrician layer": "grp_spatula_electrician",
    "Divot layer": "divot",
    "Cyber layer": "cyber",
    "Lighter layer": "lighter",
    "Combo layer (extra)": "grp_extra3",
    "Serrated layer (extra)": "grp_extra3",
    "Watch case opener layer": "grp_extra3",
    "Wrench layer": "wrench",
    "Sight adjustment layer": "sight_adjustment",
    "Coffee spatula layer": "grp_barista",
    "Nozzle remover layer": "grp_barista",
}

# Output rows: (fit key or None, label, note)
OUTPUT_ROWS = [
    ("blade", "Blade layer (incl. scales & rivets)",
     "Includes fixed scales/rivets contribution - inseparable in SAKwiki model data"),
    ("openers", "Openers layer",
     "Deduced from SAKwiki model totals (least squares)"),
    ("scissors", "Scissors layer",
     "Deduced from SAKwiki model totals (least squares)"),
    ("pliers", "Pliers layer",
     "Deduced from SAKwiki model totals (least squares)"),
    ("wood_saw", "Wood saw layer",
     "Deduced from SAKwiki model totals (least squares)"),
    ("metal_saw", "Metal saw layer",
     "Deduced from SAKwiki model totals (least squares)"),
    ("magnifier", "Magnifier layer",
     "Deduced from SAKwiki model totals (least squares)"),
    ("fish_scaler", "Fish scaler layer",
     "Deduced from SAKwiki model totals (least squares)"),
    ("grp_spatula_electrician", "Spatula layer",
     "Always co-occurring pair (spatula+electrician); group value split evenly"),
    ("grp_spatula_electrician", "Electrician layer",
     "Always co-occurring pair (spatula+electrician); group value split evenly"),
    (None, "Divot layer",
     "No SAKwiki data (only in SwissChamp XL, unpublished specs) - needs physical measurement"),
    ("cyber", "Cyber layer",
     "Deduced from SAKwiki model totals (least squares)"),
    ("lighter", "Lighter layer",
     "Deduced from SAKwiki model totals (least squares)"),
    ("grp_extra3", "Combo layer (extra)",
     "Always co-occurring trio (combo+serrated+watch-case-opener); split evenly"),
    ("grp_extra3", "Serrated layer (extra)",
     "Always co-occurring trio (combo+serrated+watch-case-opener); split evenly"),
    ("grp_extra3", "Watch case opener layer",
     "Always co-occurring trio (combo+serrated+watch-case-opener); split evenly"),
    ("wrench", "Wrench layer",
     "Deduced from SAKwiki model totals (least squares)"),
    ("sight_adjustment", "Sight adjustment layer",
     "Deduced from SAKwiki model totals (least squares)"),
    ("grp_barista", "Coffee spatula layer",
     "Always co-occurring pair (coffee-spatula+nozzle-remover); split evenly"),
    ("grp_barista", "Nozzle remover layer",
     "Always co-occurring pair (coffee-spatula+nozzle-remover); split evenly"),
]


def load_layers(path):
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    per_model = {}
    for r in rows:
        keys = sorted({k for c, k in CSV_COL_TO_KEY.items() if r[c].strip()} - {"divot"})
        per_model[r["model"]] = keys
    return per_model


def solve_lstsq(A, b):
    """Least squares via normal equations with Gaussian elimination."""
    n = len(A[0])
    ata = [[sum(A[r][i] * A[r][j] for r in range(len(A))) for j in range(n)]
           for i in range(n)]
    atb = [sum(A[r][i] * b[r] for r in range(len(A))) for i in range(n)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(ata[r][col]))
        if abs(ata[piv][col]) < 1e-12:
            continue
        ata[col], ata[piv] = ata[piv], ata[col]
        atb[col], atb[piv] = atb[piv], atb[col]
        for r in range(col + 1, n):
            f = ata[r][col] / ata[col][col]
            for c in range(col, n):
                ata[r][c] -= f * ata[col][c]
            atb[r] -= f * atb[col]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        if abs(ata[i][i]) < 1e-12:
            continue
        x[i] = (atb[i] - sum(ata[i][j] * x[j] for j in range(i + 1, n))) / ata[i][i]
    return x


def main():
    layers = load_layers("victorinox_91mm_model_layers.csv")
    keys = sorted({k for m in layers for k in layers[m]})
    idx = {k: i for i, k in enumerate(keys)}

    models = [m for m in SAKWIKI_SPECS
              if m in layers and m not in EXCLUDE]
    A, bw, bg = [], [], []
    for m in models:
        row = [0.0] * len(keys)
        for k in layers[m]:
            row[idx[k]] = 1.0
        A.append(row)
        bw.append(SAKWIKI_SPECS[m][0])
        bg.append(SAKWIKI_SPECS[m][1])

    w = solve_lstsq(A, bw)
    g = solve_lstsq(A, bg)

    print(f"Fit on {len(models)} models, {len(keys)} variables")
    print("Worst residuals (fitted - SAKwiki):")
    res = []
    for r, m in enumerate(models):
        fw = sum(A[r][i] * w[i] for i in range(len(keys)))
        fg = sum(A[r][i] * g[i] for i in range(len(keys)))
        res.append((abs(fw - bw[r]) + abs(fg - bg[r]) / 20, m, fw - bw[r], fg - bg[r]))
    res.sort(reverse=True)
    for _, m, dw, dg in res[:10]:
        print(f"  {m:28s} width {dw:+5.2f}mm  weight {dg:+6.1f}g")

    out = "victorinox_91mm_layer_specs.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["layer", "thickness_mm", "weight_g", "notes"])
        for key, label, note in OUTPUT_ROWS:
            if key is None:
                wr.writerow([label, "", "", note])
            else:
                # group keys hold the full group value; split evenly per member
                members = sum(1 for k, _, _ in OUTPUT_ROWS if k == key)
                wr.writerow([label, f"{w[idx[key]] / members:.2f}",
                             f"{g[idx[key]] / members:.1f}", note])
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
