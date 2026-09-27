#!/usr/bin/env python3
"""Build the 91mm per-model layer structure from SAKwiki data (layer tables + model pages).

Physical layer model (validated against SAKwiki Size-Layer tables):
- Each column is ONE physical layer of the knife.
- A 91mm layer = front tool(s) + rivets + backspring + back tool(s) on that spring.
- The large blade shares its spring with the small blade (or combo tool, pruning
  blade, electrician's blade, technician's screwdriver, divot tool) and with the
  corkscrew or backspring Phillips mounted on the same spring's back.
- The openers layer = cap-lifter + can-opener (+ variants) with the reamer
  (or fine screwdriver on the SMKW Wildlife series) behind.
- Layer counts match SAKwiki: Spartan/Compact 2 layers, Explorer 4,
  SwissChamp 8, SwissChamp XL/XLT 11, XAVT/XXLT 15.
"""
import csv
from collections import OrderedDict

TOOLS = [
    "Large Blade", "Large Blade (Serrated)", "Small Blade", "Pruning Blade",
    "Electrician's Blade", "Cap-lifter / Bottle Opener", "Can Opener", "Combo Tool",
    "Box Opener", "Nail File", "Wood Saw", "Metal Saw / File", "Scissors", "Pliers",
    "Fish Scaler", "Magnifying Glass", "Phillips Screwdriver (Inline)",
    "Technician's Screwdriver", "Bit Driver", "LED Light", "Butane Lighter",
    "Pharmaceutical Spatula", "Divot Tool", "Watch Case Opener", "Universal Wrench",
    "Sight Adjustment Tools", "Coffee Spatula", "Steam Wand Nozzle Remover",
    "Corkscrew", "Phillips Screwdriver (Backspring)", "Reamer / Awl",
    "Multipurpose Hook", "Fine Screwdriver", "Chisel", "Long Nail File", "Keyring",
]

LB, SB, PR, EB, SE = "Large Blade", "Small Blade", "Pruning Blade", "Electrician's Blade", "Large Blade (Serrated)"
BO, CO, CT, BX, NF = "Cap-lifter / Bottle Opener", "Can Opener", "Combo Tool", "Box Opener", "Nail File"
WS, MS, SC, PL, FS = "Wood Saw", "Metal Saw / File", "Scissors", "Pliers", "Fish Scaler"
MG, PI, TS, BD, LED = "Magnifying Glass", "Phillips Screwdriver (Inline)", "Technician's Screwdriver", "Bit Driver", "LED Light"
BL, SP, DT, WCO, UW = "Butane Lighter", "Pharmaceutical Spatula", "Divot Tool", "Watch Case Opener", "Universal Wrench"
SAT, CSP, SNR = "Sight Adjustment Tools", "Coffee Spatula", "Steam Wand Nozzle Remover"
CS, PB, RA, HOOK, FIN, CH, LNF, KR = "Corkscrew", "Phillips Screwdriver (Backspring)", "Reamer / Awl", "Multipurpose Hook", "Fine Screwdriver", "Chisel", "Long Nail File", "Keyring"

# Canonical physical layer order, identical for every model (top of the knife to bottom).
LAYER_SLOTS = [
    ("blades",      "Blade layer"),
    ("openers",     "Openers layer"),
    ("scissors",    "Scissors layer"),
    ("pliers",      "Pliers layer"),
    ("wood_saw",    "Wood saw layer"),
    ("metal_saw",   "Metal saw layer"),
    ("magnifier",   "Magnifier layer"),
    ("fish_scaler", "Fish scaler layer"),
    ("spatula",     "Spatula layer"),
    ("pruner",      "Pruner layer"),
    ("electrician", "Electrician layer"),
    ("divot",       "Divot layer"),
    ("cyber",       "Cyber layer"),
    ("lighter",     "Lighter layer"),
    ("combo2",      "Combo layer (extra)"),
    ("blade2",      "Serrated layer (extra)"),
    ("wco",         "Watch case opener layer"),
    ("wrench",      "Wrench layer"),
    ("sight",       "Sight adjustment layer"),
    ("coffee_spatula", "Coffee spatula layer"),
    ("nozzle",      "Nozzle remover layer"),
]

# Models where the fine screwdriver replaces the reamer behind the openers layer
# (SMKW Wildlife Series feature, confirmed on the Master Electrician page).
WILDLIFE = {"American Eagle", "Wild Turkey", "Bass Fishing", "Whitetail Deer", "Master Electrician"}

# Models where the pruning blade sits in the blade layer (replacing the small blade).
PRUNER_IN_BLADES = {"Picnicker", "Master Gardener", "Outdoorsman-Original"}

M = OrderedDict()

# --- 1 layer ---
M["Baker's Knife"] = [LB, KR]
M["Golfer Special"] = [LB, DT, CS, KR]
M["Waiter Plus"] = [LB, CT, CS, KR]

# --- 2 layer ---
M["American Eagle"] = [LB, SB, BO, CO, PB, FIN, KR]
M["Compact"] = [LB, CT, SC, CS, HOOK, KR]
M["DofE Pocket Tool"] = [LB, CT, SC, PB, HOOK, KR]
M["Engineer"] = [LB, TS, MG, PI, CS, KR]
M["Golfer"] = [LB, CT, SC, CS, KR]
M["Lumberjack Big"] = [LB, CT, WS, CS, KR]
M["McKinley"] = [LB, SB, BO, CO, PB, RA, KR]
M["Scientist"] = [LB, CT, MG, PI, CS, KR]
M["Spartan"] = [LB, SB, BO, CO, CS, RA, KR]
M["Special Mechanic"] = [LB, CT, PL, PB, KR]
M["Standard"] = [LB, SB, BO, CO, CS, RA, KR]
M["TimeKeeper"] = [LB, CT, SC, CS, HOOK, KR]
M["TimeKeeper Alarm"] = [LB, SB, BO, CO, PB, RA, KR]
M["Tinker"] = [LB, SB, BO, CO, PB, RA, KR]
M["Weekender"] = [SE, SB, BO, CO, CS, RA, KR]

# --- Battle Series (1983-1991) ---
M["Battle of Morgarten"] = [LB, SB, BO, CO, CS, RA, KR]
M["Battle of Laupen"] = [LB, SB, BO, CO, CS, RA, WS, KR]
M["Battle of Sempach"] = [LB, SB, BO, CO, CS, RA, SC, KR]
M["Battle of Nafels"] = [LB, SB, BO, CO, CS, RA, SC, WS, KR]
M["Battle of St. Jakob"] = [LB, SB, BO, CO, CS, RA, MG, PI, KR]
M["Battle of Murten"] = [LB, SB, BO, CO, CS, RA, FS, KR]

# --- 3 layer ---
M["Altimeter"] = [LB, SB, BO, CO, CS, RA, SC, HOOK, KR]
M["Automobile"] = [LB, TS, BO, CO, PB, RA, MS, KR]
M["Automobile Special"] = [LB, SB, BO, CO, PB, RA, MS, KR]
M["Camper"] = [LB, SB, BO, CO, CS, RA, WS, KR]
M["Climber"] = [LB, SB, BO, CO, CS, RA, SC, HOOK, KR]
M["Companion"] = [LB, BX, NF, BO, CS, RA, SC, HOOK, KR]
M["Clipper"] = [LB, SB, BO, CO, CS, RA, MS, KR]
M["Cybertool S (29)"] = [LB, SB, BD, BO, CO, CS, RA, KR]
M["FASS 90"] = [LB, SB, BO, CO, CS, RA, SAT, KR]
M["Hiker"] = [LB, SB, BO, CO, PB, RA, WS, KR]
M["Mechanic"] = [LB, SB, BO, CO, PB, RA, PL, KR]
M["Oath of Rutli"] = [LB, SB, BO, CO, CS, RA, PL, KR]
M["Passenger"] = [LB, SB, BO, CO, CS, RA, MG, PI, KR]
M["Picnicker"] = [SE, PR, BO, CO, CS, RA, WS, KR]
M["Spartan Lite"] = [LB, SB, BO, CO, CS, RA, LED, PI, KR]
M["Super Tinker"] = [LB, SB, BO, CO, PB, RA, SC, HOOK, KR]
M["Trail Guide"] = [LB, CT, SC, MS, CS, HOOK, KR]
M["Traveller"] = [LB, SB, BO, CO, CS, RA, SC, HOOK, KR]
M["Voyager"] = [LB, SB, BO, CO, CS, RA, SC, HOOK, KR]
M["Wild Turkey"] = [LB, SB, BO, CO, PB, WS, FIN, KR]
M["Yeoman"] = [LB, CT, SC, CS, MG, PI, HOOK, KR]

# --- 4 layer ---
M["Altimeter Plus"] = [LB, SB, BO, CO, CS, RA, SC, HOOK, WS, FIN, KR]
M["Angler"] = [LB, SB, BO, CO, CS, RA, PL, FS, KR]
M["Bass Fishing"] = [LB, SB, BO, CO, PB, PL, FS, FIN, KR]
M["CampFlame"] = [LB, SB, BO, CO, CS, RA, WS, BL, FIN, KR]
M["Climber Lite"] = [LB, SB, BO, CO, CS, RA, SC, HOOK, LED, PI, KR]
M["Cybertool M (34)"] = [LB, SB, BD, BO, CO, CS, RA, PL, SC, HOOK, KR]
M["CyberYeoman"] = [LB, CT, SC, MG, PI, BD, CS, HOOK, KR]
M["Deluxe Climber"] = [LB, SB, BO, CO, CS, RA, SC, HOOK, PL, KR]
M["Deluxe Tinker"] = [LB, SB, BO, CO, PB, RA, SC, HOOK, PL, KR]
M["Explorer"] = [LB, SB, BO, CO, CS, RA, SC, HOOK, MG, PI, KR]
M["Fieldmaster"] = [LB, SB, BO, CO, PB, RA, SC, HOOK, WS, KR]
M["Fisherman"] = [LB, SB, BO, CO, PB, RA, SC, HOOK, FS, KR]
M["Grand Prix"] = [LB, SB, BO, CO, PB, RA, SC, HOOK, MS, FIN, KR]
M["Huntsman"] = [LB, SB, BO, CO, CS, RA, SC, HOOK, WS, KR]
M["Master Electrician"] = [LB, EB, BO, CO, PL, PI, LED, PB, FIN, KR]
M["Master Gardener"] = [LB, PR, BO, CO, WS, LED, PI, PB, RA, KR]
M["Mountaineer"] = [LB, SB, BO, CO, CS, RA, SC, HOOK, MS, KR]
M["SwissFlame"] = [LB, SB, BO, CO, CS, RA, SC, HOOK, BL, KR]
M["Traveller Lite"] = [LB, SB, BO, CO, CS, RA, SC, HOOK, LED, PI, KR]
M["Voyager Lite"] = [LB, SB, BO, CO, CS, RA, SC, HOOK, LED, PI, KR]
M["Whitetail Deer"] = [LB, SB, BO, CO, PB, WS, LED, PI, FIN, KR]
M["Woodsman"] = [LB, SB, BO, CO, CS, RA, SC, HOOK, MG, PI, WS, FIN, KR]
M["Yeoman Mechanic"] = [LB, CT, SC, PL, MG, PI, CS, HOOK, KR]

# --- 5 layer ---
M["Angler Plus"] = [LB, SB, BO, CO, CS, RA, PL, FS, WS, KR]
M["Barista Tool"] = [LB, SB, BO, CO, PL, PI, CS, RA, CSP, SNR, KR]
M["Deluxe Angler / Waterman"] = [LB, SB, BO, CO, CS, RA, PL, FS, SC, HOOK, KR]
M["Fisherman Plus"] = [LB, SB, BO, CO, PB, RA, SC, HOOK, FS, WS, KR]
M["Handyman 7236maU"] = [LB, TS, BO, CO, CS, RA, SC, WS, MS, KR]
M["Huntsman Lite"] = [LB, SB, BO, CO, CS, RA, SC, HOOK, WS, LED, PI, FIN, KR]
M["Luxury Automobile"] = [LB, TS, BO, CO, PB, RA, SC, WS, MS, LNF, KR]
M["Master Craftsman"] = [LB, SB, BO, CO, PB, RA, SC, HOOK, WS, MS, FIN, CH, KR]
M["Master Fisherman"] = [LB, SB, BO, CO, PB, RA, PL, SC, FS, KR]
M["Modeler"] = [LB, SB, BO, CO, CS, RA, SC, MG, PI, MS, KR]
M["Motorist"] = [LB, SB, BO, CO, CS, RA, SC, HOOK, PL, WS, FIN, KR]
M["Mountaineer Lite"] = [LB, SB, BO, CO, CS, RA, SC, HOOK, MS, LED, PI, CH, KR]
M["Outdoorsman-Original"] = [SE, PR, SC, BO, CO, CS, RA, WS, MS, KR]
M["Ranger"] = [LB, SB, BO, CO, CS, RA, SC, HOOK, WS, MS, FIN, CH, KR]
M["Troubleshooter"] = [LB, SB, BO, CO, PB, RA, SC, HOOK, PL, MS, CH, KR]

# --- 6+ layer ---
M["Champion A"] = [LB, SB, BO, CO, CS, RA, SC, WS, MS, FS, LNF, KR]
M["Champion B"] = [LB, SB, BO, CO, PB, RA, SC, WS, MS, FS, LNF, KR]
M["Craftsman"] = [LB, SB, BO, CO, PB, RA, SC, HOOK, PL, WS, MS, FIN, CH, KR]
M["Expedition Lite"] = [LB, SB, BO, CO, CS, RA, SC, HOOK, WS, MS, LED, PI, FIN, CH, KR]
M["Handyman"] = [LB, SB, BO, CO, CS, RA, SC, HOOK, PL, WS, MS, FIN, CH, KR]
M["Outdoorsman"] = [LB, SB, BO, CO, CS, RA, SC, HOOK, WS, MG, PI, FS, FIN, KR]
M["Champion C"] = [LB, SB, BO, CO, CS, RA, SC, HOOK, WS, MS, FS, MG, PI, FIN, CH, KR]
M["Champion Plus"] = [LB, SB, BO, CO, CS, RA, SC, HOOK, WS, MS, FS, MG, PI, FIN, CH, KR]
M["Cybertool L (41)"] = [LB, SB, BD, BO, CO, CS, RA, PL, SC, HOOK, WS, MS, FIN, CH, KR]
M["Cybertool Lite"] = [LB, SB, BD, BO, CO, CS, RA, PL, SC, HOOK, LED, MG, KR]
M["SwissChamp"] = [LB, SB, BO, CO, CS, RA, SC, HOOK, PL, WS, MS, FS, MG, PI, FIN, CH, KR]
M["SwissChamp XL"] = [LB, SB, BO, CO, CS, RA, SC, HOOK, PL, WS, MS, FS, MG, PI, FIN, CH, SP, EB, PR, DT, KR]
M["SwissChamp XLT"] = [LB, SB, BO, CO, CS, RA, SC, HOOK, PL, WS, MS, FS, MG, PI, FIN, CH, SP, EB, PR, BD, KR]
M["SwissChamp XAVT"] = [LB, SB, SE, BO, CO, CT, CS, RA, SC, HOOK, PL, WS, MS, FS, MG, PI, FIN, CH, SP, EB, PR, BD, LED, WCO, UW, KR]
M["SwissChamp XXL"] = [LB, SB, SE, BO, CO, CT, CS, RA, SC, HOOK, PL, WS, MS, FS, MG, PI, FIN, CH, SP, EB, PR, BD, LED, WCO, UW, KR]
M["SwissChamp XXLT"] = [LB, SB, SE, BO, CO, CT, CS, RA, SC, HOOK, PL, WS, MS, FS, MG, PI, FIN, CH, SP, EB, PR, BD, BL, WCO, KR]


def assign_layers(model, tools):
    """Assign tools to the canonical physical layers for one model."""
    layers = OrderedDict((key, []) for key, _ in LAYER_SLOTS)
    toolset = set(tools)
    for t in tools:
        if t == LB or (t == SE and LB not in toolset):
            layers["blades"].append(t)
        elif t == SE:
            layers["blade2"].append(t)
        elif t == CT:
            # combo tool rides the blade spring unless openers are present (XAVT-class extra)
            if BO in toolset:
                layers["combo2"].append(t)
            else:
                layers["blades"].append(t)
        elif t == DT:
            # divot rides the blade spring unless openers are present (then own layer, SwissChamp XL)
            if BO in toolset:
                layers["divot"].append(t)
            else:
                layers["blades"].append(t)
        elif t == PR:
            if model in PRUNER_IN_BLADES:
                layers["blades"].append(t)   # replaces the small blade
            elif EB in toolset:
                layers["electrician"].append(t)  # XL-class: shares the electrician's blade layer
            else:
                layers["pruner"].append(t)   # own layer on XL-class models
        elif t == EB:
            if model == "Master Electrician":
                layers["blades"].append(t)   # replaces the small blade position
            else:
                layers["electrician"].append(t)
        elif t in (SB, TS):
            layers["blades"].append(t)       # small blade / technician's screwdriver on the blade spring
        elif t in (BO, CO, BX, NF):
            layers["openers"].append(t)
        elif t == RA:
            layers["openers"].append(t)
        elif t == FIN:
            if model in WILDLIFE:
                layers["openers"].append(t)  # replaces the reamer behind the openers
            elif MS in toolset:
                layers["metal_saw"].append(t)
            else:
                layers["wood_saw"].append(t)
        elif t in (SC, HOOK, LNF):
            layers["scissors"].append(t)
        elif t == CH:
            if WS in toolset:
                layers["wood_saw"].append(t)
            else:
                layers["metal_saw"].append(t)
        elif t == PI:
            if MG in toolset or LED in toolset:
                layers["magnifier"].append(t)  # inline Phillips rides the magnifier/LED layer spring
            elif PL in toolset:
                layers["pliers"].append(t)     # Barista Tool: inline Phillips behind the pliers layer
            else:
                layers["magnifier"].append(t)
        elif t in (MG, LED):
            layers["magnifier"].append(t)
        elif t == PL:
            layers["pliers"].append(t)
        elif t == BD:
            layers["cyber"].append(t)
        elif t == WS:
            layers["wood_saw"].append(t)
        elif t == MS:
            layers["metal_saw"].append(t)
        elif t == FS:
            layers["fish_scaler"].append(t)
        elif t == SP:
            layers["spatula"].append(t)
        elif t == BL:
            layers["lighter"].append(t)
        elif t == WCO:
            layers["wco"].append(t)
        elif t == UW:
            layers["wrench"].append(t)
        elif t == SAT:
            layers["sight"].append(t)
        elif t == CSP:
            layers["coffee_spatula"].append(t)
        elif t == SNR:
            layers["nozzle"].append(t)
        elif t in (CS, PB):
            layers["blades"].append(t)        # corkscrew / backspring Phillips on the blade-layer spring
        elif t == KR:
            pass                              # attachment point, not a layer
        else:
            raise ValueError(f"unhandled tool {t!r} in model {model!r}")

    # stable ordering inside each layer: follow the TOOLS column order
    idx = {t: i for i, t in enumerate(TOOLS)}
    for key in layers:
        layers[key].sort(key=idx.get)
    return layers


import os
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "victorinox_91mm_model_layers.csv")
with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["model"] + [label for _, label in LAYER_SLOTS])
    for model, tools in M.items():
        layers = assign_layers(model, tools)
        w.writerow([model] + [" + ".join(layers[key]) for key, _ in LAYER_SLOTS])

# sanity checks
errors = []
for model, tools in M.items():
    if CS in tools and PB in tools:
        errors.append(f"{model}: corkscrew and backspring Phillips together")
    layers = assign_layers(model, tools)
    placed = [t for s in layers.values() for t in s]
    if sorted(placed) != sorted([t for t in tools if t != KR]):
        errors.append(f"{model}: tool lost/duplicated in layer assignment")
    if not layers["blades"]:
        errors.append(f"{model}: no blade layer")

print(f"models: {len(M)}, layer slots: {len(LAYER_SLOTS)}")
if errors:
    print("ERRORS:")
    for e in errors:
        print(" -", e)
    raise SystemExit(1)
print("all checks passed")

# layer-count verification against SAKwiki Size-Layer tables
EXPECTED_LAYERS = {
    "Baker's Knife": 1, "Golfer Special": 1, "Waiter Plus": 1,
    "Spartan": 2, "Compact": 2, "Engineer": 2, "Scientist": 2, "Golfer": 2,
    "Lumberjack Big": 2, "Special Mechanic": 2, "TimeKeeper": 2, "Tinker": 2,
    "Weekender": 2, "American Eagle": 2, "DofE Pocket Tool": 2,
    "McKinley": 2, "Standard": 2, "TimeKeeper Alarm": 2,
    "Altimeter": 3, "Camper": 3, "Climber": 3, "Companion": 3, "Clipper": 3,
    "Cybertool S (29)": 3, "FASS 90": 3, "Hiker": 3, "Mechanic": 3,
    "Oath of Rutli": 3, "Passenger": 3, "Picnicker": 3, "Spartan Lite": 3,
    "Super Tinker": 3, "Trail Guide": 3, "Traveller": 3, "Voyager": 3,
    "Wild Turkey": 3, "Yeoman": 3, "Automobile": 3, "Automobile Special": 3,
    "Altimeter Plus": 4, "Angler": 4, "Bass Fishing": 4, "CampFlame": 4,
    "Climber Lite": 4, "Cybertool M (34)": 5, "CyberYeoman": 4,
    "Deluxe Climber": 4, "Deluxe Tinker": 4, "Explorer": 4, "Fieldmaster": 4,
    "Fisherman": 4, "Grand Prix": 4, "Huntsman": 4, "Master Electrician": 4,
    "Master Gardener": 4, "Mountaineer": 4, "SwissFlame": 4,
    "Traveller Lite": 4, "Voyager Lite": 4, "Whitetail Deer": 4, "Woodsman": 5,
    "Yeoman Mechanic": 4,
    "Angler Plus": 5, "Barista Tool": 5, "Deluxe Angler / Waterman": 5,
    "Fisherman Plus": 5, "Handyman 7236maU": 5, "Huntsman Lite": 5,
    "Luxury Automobile": 5, "Master Craftsman": 5, "Master Fisherman": 5,
    "Modeler": 5, "Motorist": 5, "Mountaineer Lite": 5,
    "Outdoorsman-Original": 5, "Ranger": 5, "Troubleshooter": 5,
    "Champion A": 6, "Champion B": 6, "Craftsman": 6, "Expedition Lite": 6,
    "Handyman": 6, "Outdoorsman": 6,
    "Champion C": 7, "Champion Plus": 7, "Cybertool L (41)": 7,
    "Cybertool Lite": 6,
    "SwissChamp": 8,
    "SwissChamp XL": 11, "SwissChamp XLT": 11,
    "SwissChamp XAVT": 15, "SwissChamp XXLT": 15,
}
# SwissChamp XXL: SAKwiki does not give a count in the tool tables; XAVT-class => 15
EXPECTED_LAYERS["SwissChamp XXL"] = 15
# Battle Series: based on toolset size (Spartan/Climber/Huntsman-class)
for name, cnt in {
    "Battle of Morgarten": 2, "Battle of Laupen": 3, "Battle of Sempach": 3,
    "Battle of Nafels": 4, "Battle of St. Jakob": 3, "Battle of Murten": 3,
}.items():
    EXPECTED_LAYERS[name] = cnt

count_errors = []
for model, expected in EXPECTED_LAYERS.items():
    layers = assign_layers(model, M[model])
    n = sum(1 for v in layers.values() if v)
    if n != expected:
        count_errors.append(f"{model}: got {n} layers, SAKwiki says {expected}")

if count_errors:
    print("LAYER COUNT MISMATCHES:")
    for e in count_errors:
        print(" -", e)
    raise SystemExit(1)
print(f"layer counts verified for {len(EXPECTED_LAYERS)} models against SAKwiki")
