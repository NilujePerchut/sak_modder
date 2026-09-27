#!/usr/bin/env python3
"""Build a single-file HTML web app from the three generated CSVs.

Reads:
  - victorinox_91mm_tools.csv          (tool, location, description)
  - victorinox_91mm_models_tools.csv   (model x tool matrix)
  - victorinox_91mm_model_layers.csv    (model -> layer slot -> tools)
  - victorinox_91mm_layer_specs.csv     (layer -> thickness & weight)

Derives the observed layer configurations ("archetypes") per slot across the 99
reference models, and injects everything as JSON into a static HTML app that
lets the user assemble a custom knife layer per layer with a live preview.
"""
import csv
import json
import os
from collections import OrderedDict, defaultdict

WS = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- load inputs
with open(f"{WS}/victorinox_91mm_tools.csv", encoding="utf-8") as f:
    tools = list(csv.DictReader(f))
TOOL_LIST = [r["tool_name"] for r in tools]
TOOL_INFO = {r["tool_name"]: {"location": r["location"], "description": r["description"]} for r in tools}

with open(f"{WS}/victorinox_91mm_models_tools.csv", encoding="utf-8") as f:
    matrix_rows = list(csv.DictReader(f))
MODELS = OrderedDict()
for r in matrix_rows:
    MODELS[r["model"]] = {k for k, v in r.items() if k != "model" and v == "X"}

with open(f"{WS}/victorinox_91mm_model_layers.csv", encoding="utf-8") as f:
    layer_rows = list(csv.DictReader(f))
SLOT_IDS = [k for k in layer_rows[0].keys() if k not in ("model", "layer_order")]

def _slug(label):
    s = label.lower().replace("'", "").replace("(", "").replace(")", "").replace("/", " ")
    return "_".join(s.split())


SLOT_LABELS = {s: s for s in SLOT_IDS}
SLOT_KEYS = {s: _slug(s) for s in SLOT_IDS}

# ------------------------------------------------- derive layer archetypes
# archetype per slot = a distinct set of tools observed in that slot column
arch = defaultdict(lambda: defaultdict(list))   # slot -> frozenset(tools) -> [models]
for r in layer_rows:
    model = r["model"]
    for slot in SLOT_IDS:
        cell = (r.get(slot) or "").strip()
        if not cell:
            continue
        tset = frozenset(t.strip() for t in cell.split(" + ") if t.strip())
        arch[SLOT_KEYS[slot]][tset].append(model)

ARCHETYPES = OrderedDict()
for slot in SLOT_IDS:
    variants = []
    for tset, models in sorted(arch[SLOT_KEYS[slot]].items(), key=lambda kv: (-len(kv[0]), sorted(kv[0]))):
        variants.append({
            "tools": sorted(tset, key=TOOL_LIST.index),
            "models": models,
        })
    ARCHETYPES[SLOT_KEYS[slot]] = variants

# --------------------------------------- per-model slot -> archetype index
models_layers = OrderedDict()
for r in layer_rows:
    mlay = {}
    for slot in SLOT_IDS:
        cell = (r.get(slot) or "").strip()
        if not cell:
            continue
        tset = frozenset(t.strip() for t in cell.split(" + ") if t.strip())
        idx = next((i for i, v in enumerate(ARCHETYPES[SLOT_KEYS[slot]])
                    if frozenset(v["tools"]) == tset), None)
        assert idx is not None, f"no archetype found for {r['model']} slot {slot}: {sorted(tset)}"
        mlay[SLOT_KEYS[slot]] = idx
    order = [s for s in (r.get("layer_order") or "").split(",") if s]
    mlay["order"] = order
    models_layers[r["model"]] = mlay

# ------------------------------------------------------- per-layer specs (mm/g)
with open(f"{WS}/victorinox_91mm_layer_specs.csv", encoding="utf-8") as f:
    spec_rows = list(csv.DictReader(f))
LAYER_SPECS = {}
for r in spec_rows:
    key = _slug(r["layer"])
    LAYER_SPECS[key] = {
        "mm": float(r["thickness_mm"]) if r["thickness_mm"].strip() else None,
        "g": float(r["weight_g"]) if r["weight_g"].strip() else None,
    }
# slot label -> spec row label where slugs differ
SPEC_KEY_ALIASES = {
    "Blade layer": "blade_layer_incl._scales_&_rivets",
}
SLOT_SPECS = {}
for s in SLOT_IDS:
    key = SPEC_KEY_ALIASES.get(s, SLOT_KEYS[s])
    # unused slots (no reference model) may have no measured spec: mark unknown
    SLOT_SPECS[SLOT_KEYS[s]] = LAYER_SPECS.get(key, {"mm": None, "g": None})

# ------------------------------------------------------- model prices (optional)
# victorinox_91mm_model_prices.csv: model,price_usd,price_chf,price_eur,
# victorinox_id,fetched_at — official prices scraped from victorinox.com
# (fetch_prices.py). A missing currency column falls back to conversion via
# the exchange-rate CSV; a fully missing row falls back to a layer-count proxy.
PRICES = {}          # model -> {USD, CHF, EUR} (native prices, may be partial)
_prices_path = f"{WS}/victorinox_91mm_model_prices.csv"
if os.path.exists(_prices_path):
    with open(_prices_path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if not r.get("model"):
                continue
            entry = {}
            for cur in ("usd", "chf", "eur"):
                v = (r.get(f"price_{cur}") or "").strip()
                if v:
                    try:
                        entry[cur.upper()] = float(v)
                    except ValueError:
                        pass
            if entry:
                PRICES[r["model"]] = entry

# ------------------------------------------- exchange rates (optional, CHF base)
# victorinox_exchange_rates.csv: base,quote,rate,date — written by fetch_prices.py
# companion run or manually. Used to convert a native price to the display
# currency when the model has no price published in that currency.
RATES = {}           # quote currency -> rate per 1 CHF
RATES_DATE = ""
_rates_path = f"{WS}/victorinox_exchange_rates.csv"
if os.path.exists(_rates_path):
    with open(_rates_path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("base") == "CHF" and r.get("quote") and r.get("rate"):
                try:
                    RATES[r["quote"]] = float(r["rate"])
                    RATES_DATE = r.get("date", "")
                except ValueError:
                    pass
RATES["CHF"] = 1.0
PRICES_FETCHED_AT = ""
VX_IDS = {}
if os.path.exists(_prices_path):
    with open(_prices_path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            dates = [d for d in (r.get("fetched_at") or "").split(";") if d]
            if dates and not PRICES_FETCHED_AT:
                PRICES_FETCHED_AT = max(dates)
            if r.get("model") and r.get("victorinox_id"):
                VX_IDS[r["model"]] = r["victorinox_id"]

# ------------------------------------------------- model availability (retired)
# victorinox_91mm_model_availability.csv: model,retired,source
# retired=Y means the model is no longer sold -> excluded as a donor knife.
RETIRED = set()
_avail_path = f"{WS}/victorinox_91mm_model_availability.csv"
if os.path.exists(_avail_path):
    with open(_avail_path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if (r.get("retired") or "").strip().upper() in ("Y", "SR", "TRUE", "1"):
                RETIRED.add(r["model"])

# ---------------------------------------------------------------- verify data
toolset_union = set().union(*MODELS.values())
unknown = toolset_union - set(TOOL_LIST)
assert not unknown, f"tools in matrix not in tool list: {unknown}"
for slot, variants in ARCHETYPES.items():
    for v in variants:
        for t in v["tools"]:
            assert t in TOOL_INFO, f"unknown tool {t} in slot {slot}"

print(f"tools: {len(TOOL_LIST)}, models: {len(MODELS)}, slots: {len(SLOT_IDS)}")
for slot in SLOT_IDS:
    print(f"  {slot}: {len(ARCHETYPES[SLOT_KEYS[slot]])} configurations")

# ---------------------------------------------------------------- HTML template
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>91mm SAK Builder</title>
<style>
:root {
  --bg:#f4f1ec; --panel:#fffdf8; --line:#d8d2c6; --ink:#2b2620; --dim:#7a7263;
  --red:#d43518; --accent:#b3451f; --ok:#3d7a3d; --sel:#f0e0c0;
  --input:#ffffff; --hover:#f7f2e6; --hover-accent:#fffaf0; --exact-bg:#e4efe4;
  --band:#efe9dc; --band-line:#b7ad98; --band-ctl:#ffffff; --band-ctl-line:#c4b9a4;
  --band-text:#9a8f79; --keyring:#555555;
  color-scheme:light;
}
html[data-theme="dark"] {
  --bg:#191614; --panel:#211d1a; --line:#3d362f; --ink:#e9e3d8; --dim:#a79d8d;
  --red:#a92a17; --accent:#d98a5f; --ok:#5a9a5a; --sel:#4a3a24;
  --input:#2a2521; --hover:#2c2722; --hover-accent:#332b24; --exact-bg:#24322a;
  --band:#2b2622; --band-line:#4a443c; --band-ctl:#35302a; --band-ctl-line:#57503f;
  --band-text:#8f8574; --keyring:#9a948a;
  color-scheme:dark;
}
* { box-sizing:border-box; }
body { margin:0; font:14px/1.45 "Segoe UI",system-ui,sans-serif; background:var(--bg); color:var(--ink); }
header { background:var(--red); color:#fff; padding:10px 18px; display:flex; align-items:center; gap:14px; }
header h1 { font-size:19px; margin:0; font-weight:700; letter-spacing:.5px; }
header .sub { font-size:12px; opacity:.85; }
main { display:grid; grid-template-columns: 320px 1fr 340px; gap:14px; padding:14px; max-width:1500px; margin:0 auto; }
.panel { background:var(--panel); border:1px solid var(--line); border-radius:10px; box-shadow:0 1px 3px rgba(0,0,0,.06); }
.panel h2 { font-size:13px; text-transform:uppercase; letter-spacing:.8px; color:var(--dim); margin:0; padding:10px 12px 6px; border-bottom:1px solid var(--line); }
/* ------- tool palette ------- */
#palette .search { padding:8px 10px; position:sticky; top:0; background:var(--panel); }
#palette input { width:100%; padding:7px 10px; border:1px solid var(--line); border-radius:7px; font-size:13px; background:var(--input); color:var(--ink); }
#toolList { max-height:calc(100vh - 170px); overflow-y:auto; padding:6px; }
.tool-item { display:flex; align-items:center; gap:9px; padding:7px 8px; border-radius:8px; cursor:pointer; border:1px solid transparent; }
.tool-item:hover { background:var(--hover); }
.tool-item.selected { background:var(--sel); border-color:var(--accent); }
.tool-ico { width:30px; height:30px; border-radius:7px; display:flex; align-items:center; justify-content:center; font-size:16px; color:#fff; flex:none; }
.tool-name { font-weight:600; font-size:13px; }
.tool-meta { font-size:11px; color:var(--dim); }
.tool-desc { font-size:11px; color:var(--dim); display:none; }
.tool-item.selected .tool-desc { display:block; }
/* ------- candidates ------- */
#candidates .inner { padding:10px 12px; }
.hint { color:var(--dim); font-size:13px; padding:16px 12px; }
.slot-group { margin-bottom:12px; }
.slot-group h3 { margin:0 0 6px; font-size:12px; color:var(--accent); text-transform:uppercase; letter-spacing:.6px; }
.card { display:flex; align-items:center; gap:10px; width:100%; text-align:left; background:var(--input); color:var(--ink); border:1px solid var(--line); border-radius:9px; padding:9px 11px; margin-bottom:6px; cursor:pointer; transition:all .12s; }
.card:hover { border-color:var(--accent); background:var(--hover-accent); transform:translateX(2px); }
.card .ctools { font-weight:600; font-size:13px; }
.card .cmodels { font-size:11px; color:var(--dim); margin-top:2px; }
.card .badge { margin-left:auto; background:var(--ok); color:#fff; font-size:11px; padding:2px 9px; border-radius:10px; flex:none; }
.card .badge.swap { background:#a3742a; }
/* ------- preview ------- */
#previewSlot .inner { padding:12px; }
#knifeWrap { display:flex; gap:12px; align-items:flex-start; }
.previewCol { flex:1; min-width:0; }
.pvHead { display:flex; align-items:center; justify-content:space-between; font-size:11px; color:var(--dim); font-weight:700; text-transform:uppercase; letter-spacing:.6px; padding:0 2px 4px; }
.pvHead button { font-size:11px; padding:2px 8px; border:1px solid var(--line); background:var(--input); color:var(--dim); border-radius:6px; cursor:pointer; }
.pvHead button:hover { border-color:var(--accent); color:var(--accent); }
#knifeWrap svg { width:100%; height:auto; }
#status { text-align:center; font-size:13px; padding:6px 0 2px; color:var(--dim); min-height:20px; }
#stackStats { display:flex; justify-content:center; gap:10px; padding:8px 0 0; flex-wrap:wrap; }
#stackStats .stat { display:inline-flex; align-items:baseline; gap:5px; background:var(--input); border:1px solid var(--line); border-radius:8px; padding:4px 12px; }
#stackStats .stat .k { font-size:10.5px; color:var(--dim); text-transform:uppercase; letter-spacing:.6px; font-weight:700; }
#stackStats .stat .v { font-size:15px; font-weight:700; color:var(--ink); }
#stackStats .stat .u { font-size:11px; color:var(--dim); }
#statsNote { text-align:center; font-size:10.5px; color:var(--dim); padding:3px 0 0; font-style:italic; }
#status.warn { color:var(--accent); font-weight:600; }
/* ------- build state ------- */
.toolbar { display:flex; gap:8px; padding:8px 12px 2px; }
.toolbar select { flex:1; min-width:0; padding:6px 8px; border:1px solid var(--line); border-radius:7px; background:var(--input); color:var(--ink); font-size:12.5px; }
.toolbar button { padding:6px 12px; border:1px solid var(--line); background:var(--input); color:var(--ink); border-radius:7px; cursor:pointer; font-size:12.5px; font-weight:600; }
.toolbar button:hover { border-color:var(--accent); background:var(--hover-accent); }
#buildPanel .inner { padding:10px 12px; }
.chip { display:inline-flex; align-items:center; gap:5px; font-size:11.5px; font-weight:600; color:#fff; padding:2px 8px; border-radius:10px; }
.chip.back { outline:1.5px solid rgba(255,255,255,.55); }
#matches { padding:8px 12px 12px; }
.match { display:flex; justify-content:space-between; font-size:12.5px; padding:4px 6px; border-radius:6px; }
.match:hover { background:var(--hover); }
.match .pct { color:var(--dim); font-weight:600; }
.match.exact { background:var(--exact-bg); font-weight:700; }
#exportBtns { display:flex; gap:8px; padding:0 12px 12px; }
#exportBtns button { flex:1; padding:7px; border:1px solid var(--line); background:var(--input); color:var(--ink); border-radius:7px; cursor:pointer; font-size:12.5px; font-weight:600; }
#exportBtns button:hover { border-color:var(--accent); background:var(--hover-accent); }
#shopPanel .item { display:flex; justify-content:space-between; align-items:baseline; font-size:13px; padding:5px 12px; }
#shopPanel .item .take { font-size:11px; color:var(--dim); }
#shopPanel .price { font-weight:700; }
#shopPanel .total { border-top:1px solid var(--line); margin-top:4px; padding:6px 12px 8px; display:flex; justify-content:space-between; font-size:13px; font-weight:700; }
#shopPanel .hint { padding:10px 12px 12px; font-size:12.5px; color:var(--dim); }
#shopPanel .alt { border:none; background:none; color:var(--accent); font-size:11.5px; cursor:pointer; padding:2px 12px 8px; text-decoration:underline; }
#shopPanel #liveWrap { display:flex; align-items:center; gap:6px; font-size:12.5px; font-weight:600; padding:6px 10px; border:1px solid var(--line); border-radius:7px; background:var(--input); cursor:pointer; }
#shopPanel #shopNote { border-top:1px dashed var(--line); margin-top:4px; }
footer { text-align:center; color:var(--dim); font-size:11px; padding:8px; }
header #themeBtn { margin-left:auto; padding:5px 12px; border:1px solid rgba(255,255,255,.5); background:rgba(255,255,255,.12); color:#fff; border-radius:8px; cursor:pointer; font-size:12.5px; font-weight:600; }
header #themeBtn:hover { background:rgba(255,255,255,.22); }
#candidates { position:fixed; left:352px; top:64px; width:330px; z-index:50; display:none; box-shadow:0 6px 24px rgba(0,0,0,.18); }
#frontSvg g[data-band] { cursor:grab; touch-action:none; }
#frontSvg line#dropLine { pointer-events:none; }
@media (max-width:1100px) {
  main { grid-template-columns:1fr; }
  #candidates { left:12px; right:12px; top:12px; width:auto; max-height:70vh; overflow-y:auto; }
  #toolList { max-height:40vh; }
}
@media (max-width:640px) {
  main { padding:10px; gap:10px; }
  header { padding:8px 12px; gap:8px; }
  header h1 { font-size:16px; }
  header .sub { font-size:10.5px; }
  #knifeWrap { flex-direction:column; }
  #toolList { max-height:34vh; }
}
</style>
</head>
<body>
<header>
  <div style="font-size:26px">🔪</div>
  <div>
    <h1>91mm SAK Builder</h1>
    <div class="sub">Assemble a custom Victorinox 91mm Swiss Army Knife, layer by layer — data from SAKwiki</div>
  </div>
  <button id="themeBtn" title="Switch theme (auto / light / dark)">◐ theme</button>
</header>
<main>
  <section class="panel" id="palette">
    <h2>Tools</h2>
    <div class="search"><input id="search" type="search" placeholder="Search a tool… e.g. corkscrew"></div>
    <div id="toolList"></div>
  </section>
  <section class="panel" id="previewSlot">
    <h2>Preview</h2>
    <div class="inner">
      <div id="knifeWrap">
        <div class="previewCol">
          <div class="pvHead"><span>Front side</span><button id="resetOrder" title="Restore standard layer order">↺ order</button></div>
          <svg id="frontSvg" viewBox="0 0 420 300"></svg>
        </div>
        <div class="previewCol">
          <div class="pvHead"><span>Back side</span></div>
          <svg id="backSvg" viewBox="0 0 420 300"></svg>
        </div>
      </div>
      <div id="stackStats"></div>
      <div id="statsNote"></div>
      <div id="status"></div>
    </div>
  </section>
  <section>
    <div class="panel" id="buildPanel">
      <h2>Layers</h2>
      <div class="toolbar">
        <select id="modelSelect"><option value="">Load layers from a model…</option></select>
        <button id="clearBtn" title="Remove all layers">Clear</button>
      </div>
    </div>
    <div class="panel" style="margin-top:14px">
      <h2>Matching Models</h2>
      <div id="matches"></div>
      <div id="exportBtns">
        <button id="dlJson">⬇ Build JSON</button>
        <button id="dlCsv">⬇ Build CSV</button>
      </div>
    </div>
    <div class="panel" id="shopPanel" style="margin-top:14px">
      <h2>Shopping List</h2>
      <div class="toolbar" style="padding-top:10px">
        <select id="currencySelect" title="Display currency">
          <option value="EUR">EUR €</option>
          <option value="USD">USD $</option>
          <option value="CHF">CHF</option>
        </select>
        <label id="liveWrap" title="Fetch current prices and exchange rates from victorinox.com and frankfurter.app while online">
          <input type="checkbox" id="liveChk"> live
        </label>
      </div>
      <div id="shopList"></div>
      <div id="shopNote" class="hint"></div>
    </div>
  </section>
</main>
<div class="panel" id="candidates">
  <h2 id="candTitle">Layer configurations</h2>
  <div class="inner" id="candBody"></div>
</div>
<footer>Data: SAKwiki (91mm layer tables & model pages) — __MODEL_COUNT__ reference models, __TOOL_COUNT__ tools, __ARCH_COUNT__ layer configurations.</footer>
<script>
"use strict";
// ================== DATA (injected) ==================
const TOOLS = __TOOLS_JSON__;
const TOOL_INFO = __TOOL_INFO_JSON__;
const SLOTS = __SLOTS_JSON__;
const ARCHETYPES = __ARCHETYPES_JSON__;
const MODELS = __MODELS_JSON__;
const MODELS_LAYERS = __MODELS_LAYERS_JSON__;
const SLOT_SPECS = __SLOT_SPECS_JSON__;
const PRICES = __PRICES_JSON__;
const RATES = __RATES_JSON__;
const RATES_DATE = __RATES_DATE_JSON__;
const RETIRED = __RETIRED_JSON__;
let CURRENCY = "EUR";   // display currency for the shopping list
let PRICES_FETCHED_AT = __PRICES_FETCHED_AT_JSON__;   // date of the embedded price snapshot
let liveRates = null;    // when set: {USD, EUR, ...} live rates per 1 CHF

// ================== constants ==================
const CAT = {
  "Large Blade":"blade", "Large Blade (Serrated)":"blade", "Small Blade":"blade",
  "Pruning Blade":"blade", "Electrician's Blade":"blade",
  "Cap-lifter / Bottle Opener":"opener", "Can Opener":"opener", "Combo Tool":"opener",
  "Box Opener":"opener", "Nail File":"grooming",
  "Wood Saw":"saw", "Metal Saw / File":"saw",
  "Scissors":"scissor", "Pliers":"plier", "Fish Scaler":"fishing",
  "Magnifying Glass":"optic", "Phillips Screwdriver (Inline)":"driver",
  "Technician's Screwdriver":"driver", "Bit Driver":"driver",
  "Phillips Screwdriver (Backspring)":"driver", "Fine Screwdriver":"driver",
  "LED Light":"elec", "Butane Lighter":"elec", "Universal Wrench":"driver",
  "Pharmaceutical Spatula":"other", "Divot Tool":"other", "Watch Case Opener":"other",
  "Corkscrew":"corkscrew", "Reamer / Awl":"punch", "Multipurpose Hook":"hook",
  "Chisel":"chisel", "Long Nail File":"grooming", "Keyring":"other",
  "Sight Adjustment Tools":"other", "Coffee Spatula":"other", "Steam Wand Nozzle Remover":"driver",
};
const COLORS = { blade:"#c0392b", opener:"#2471a3", grooming:"#8e6e9e", saw:"#7d5f36",
  scissor:"#6c3483", plier:"#4a6b8a", fishing:"#1f7a5a", optic:"#b7791f",
  driver:"#2e7d32", elec:"#c9860b", corkscrew:"#8d3b3b", punch:"#5d6d7e",
  hook:"#943126", chisel:"#5d4037", other:"#616a6b" };
const ICONS = {
  "Large Blade":"🔪", "Large Blade (Serrated)":"🔪", "Small Blade":"🔪", "Pruning Blade":"🌿",
  "Electrician's Blade":"⚡", "Cap-lifter / Bottle Opener":"🍺", "Can Opener":"🥫",
  "Combo Tool":"🧰", "Box Opener":"📦", "Nail File":"💅", "Wood Saw":"🪚",
  "Metal Saw / File":"🪚", "Scissors":"✂️", "Pliers":"🔧", "Fish Scaler":"🐟",
  "Magnifying Glass":"🔍", "Phillips Screwdriver (Inline)":"🪛",
  "Technician's Screwdriver":"🪛", "Bit Driver":"🪛", "Phillips Screwdriver (Backspring)":"🪛",
  "Fine Screwdriver":"🪛", "LED Light":"🔦", "Butane Lighter":"🔥", "Universal Wrench":"🔩",
  "Pharmaceutical Spatula":"🥄", "Divot Tool":"⛳", "Watch Case Opener":"⌚",
  "Corkscrew":"🍾", "Reamer / Awl":"🪡", "Multipurpose Hook":"🪝", "Chisel":"🔨",
  "Long Nail File":"💅", "Keyring":"🔑",
  "Sight Adjustment Tools":"🎯", "Coffee Spatula":"☕", "Steam Wand Nozzle Remover":"🔩",
};
const colorOf = t => COLORS[CAT[t]] || "#616a6b";
const iconOf = t => ICONS[t] || "🔧";

// ================== state ==================
// build: slotId -> archetype index (into ARCHETYPES[slotId])
const build = {};
let layerOrder = [];   // custom display order of the filled slots (front preview controls)
let selectedTool = null;
let candSlotFocus = null;   // when set, candidate panel scoped to one slot
let frontGeom = null;        // geometry of the front SVG bands, set by renderSide

// ================== palette ==================
function renderPalette() {
  const q = document.getElementById("search").value.trim().toLowerCase();
  const box = document.getElementById("toolList");
  box.innerHTML = "";
  for (const loc of ["Front", "Back"]) {
    const items = TOOLS.filter(t => TOOL_INFO[t].location === loc &&
      (!q || t.toLowerCase().includes(q)));
    if (!items.length) continue;
    const h = document.createElement("div");
    h.style.cssText = "font-size:11px;color:var(--dim);padding:6px 8px 2px;font-weight:700;text-transform:uppercase";
    h.textContent = loc === "Front" ? "Front layer tools" : "Back layer tools";
    box.appendChild(h);
    for (const t of items) {
      const d = document.createElement("div");
      d.className = "tool-item" + (t === selectedTool ? " selected" : "");
      d.innerHTML = `
        <div class="tool-ico" style="background:${colorOf(t)}">${iconOf(t)}</div>
        <div>
          <div class="tool-name">${t}</div>
          <div class="tool-meta">${TOOL_INFO[t].location} · in ${countConfigs(t)} layer config${countConfigs(t)!==1?"s":""}</div>
          <div class="tool-desc">${TOOL_INFO[t].description}</div>
        </div>`;
      d.onclick = () => selectTool(t === selectedTool ? null : t);
      box.appendChild(d);
    }
  }
}
function countConfigs(tool) {
  let n = 0;
  for (const slot of SLOTS) for (const a of ARCHETYPES[slot.id])
    if (a.tools.includes(tool)) n++;
  return n;
}

// ================== candidates ==================
function selectTool(t) {
  selectedTool = t;
  candSlotFocus = null;
  renderPalette();
  renderCandidates();
}
function renderCandidates() {
  const panel = document.getElementById("candidates");
  const body = document.getElementById("candBody");
  const title = document.getElementById("candTitle");
  if (!selectedTool && !candSlotFocus) { panel.style.display = "none"; return; }
  panel.style.display = "block";
  body.innerHTML = "";
  if (candSlotFocus) {
    title.textContent = SLOTS.find(s=>s.id===candSlotFocus).label;
    const g = document.createElement("div");
    g.className = "slot-group";
    for (const a of ARCHETYPES[candSlotFocus]) g.appendChild(configCard(candSlotFocus, a));
    body.appendChild(g);
  } else {
    title.textContent = `Layers containing: ${selectedTool}`;
    let any = false;
    for (const slot of SLOTS) {
      const variants = ARCHETYPES[slot.id].filter(a => a.tools.includes(selectedTool));
      if (!variants.length) continue;
      any = true;
      const g = document.createElement("div");
      g.className = "slot-group";
      const h = document.createElement("h3");
      h.textContent = slot.label;
      g.appendChild(h);
      for (const a of variants) g.appendChild(configCard(slot.id, a));
      body.appendChild(g);
    }
    if (!any) body.innerHTML = `<div class="hint">No observed layer configuration uses this tool together with the current selection.</div>`;
  }
}
function configCard(slotId, a) {
  const c = document.createElement("button");
  c.className = "card";
  const filled = build[slotId] !== undefined;
  const idx = ARCHETYPES[slotId].indexOf(a);
  const same = build[slotId] === idx;
  const chipRow = a.tools.map(t =>
    `<span class="chip ${TOOL_INFO[t].location==="Back"?"back":""}" style="background:${colorOf(t)}">${iconOf(t)} ${t}</span>`).join(" ");
  const ex = a.models.length <= 3 ? a.models.join(", ")
    : a.models.slice(0,3).join(", ") + ` +${a.models.length-3} more`;
  c.innerHTML = `<div><div class="ctools">${chipRow}</div>
    <div class="cmodels">as in: ${ex}</div></div>
    <span class="badge ${filled && !same ? "swap" : ""}">${same ? "✓ in build" : filled ? "swap" : "add"}</span>`;
  c.onclick = () => {
    build[slotId] = idx;
    if (!layerOrder.includes(slotId)) layerOrder.push(slotId);
    // layer chosen: close the configuration panel (also drops the pending
    // tool selection so the panel does not reappear on the next render)
    selectedTool = null; candSlotFocus = null;
    renderAll();
  };
  return c;
}

function removeLayer(slotId) { delete build[slotId]; layerOrder = layerOrder.filter(s => s !== slotId); renderAll(); }
function moveLayer(slotId, dir) {
  const i = layerOrder.indexOf(slotId);
  const j = i + dir;
  if (i < 0 || j < 0 || j >= layerOrder.length) return;
  [layerOrder[i], layerOrder[j]] = [layerOrder[j], layerOrder[i]];
  renderAll();
}
function loadModel(name) {
  const lay = MODELS_LAYERS[name];
  if (!lay) return;
  for (const k of Object.keys(build)) delete build[k];
  layerOrder = [];
  for (const s of SLOTS) {
    if (lay[s.id] !== undefined) build[s.id] = lay[s.id];
  }
  layerOrder = (lay.order && lay.order.length ? lay.order : SLOTS.map(s => s.id))
    .filter(id => build[id] !== undefined);
  selectedTool = null; candSlotFocus = null;
  renderAll();
}

// ================== preview (SVG) ==================
function orderedSlots() {
  const inOrder = layerOrder.filter(id => build[id] !== undefined);
  const rest = SLOTS.filter(s => build[s.id] !== undefined && !inOrder.includes(s.id)).map(s => s.id);
  return [...inOrder, ...rest].map(id => SLOTS.find(s => s.id === id));
}
function renderKnife() {
  const filled = orderedSlots();
  const nL = filled.length;
  const status = document.getElementById("status");
  if (!("blade_layer" in build)) {
    status.className = "warn";
    status.textContent = "⚠ Select a main blade layer to start (click “Large Blade” in the Tools list)";
  } else {
    status.className = "";
    status.textContent = `${nL} layer${nL!==1?"s":""} · ${builtTools().size} tools (incl. keyring)`;
  }
  renderSide("frontSvg", "front", filled);
  renderSide("backSvg", "back", filled);
}
function renderSide(svgId, side, filled) {
  const svg = document.getElementById(svgId);
  const nL = filled.length;
  const W = 420, pad = 30;
  const scaleH = 20, gap = 3;
  const bodyH = Math.max(90, Math.min(nL, 12) * (26 + gap));
  const H = Math.max(200, bodyH + 2*scaleH + 60);
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  let y = (H - bodyH) / 2 - scaleH - 2;
  let geomY0 = 0;
  let out = "";
  // top scale
  out += `<rect x="${pad}" y="${y}" width="${W-2*pad}" height="${scaleH}" rx="6" fill="var(--red)" stroke="rgba(0,0,0,.35)"/>
          <rect x="${pad+18}" y="${y+4}" width="34" height="12" rx="2" fill="#fff" opacity=".92"/>
          <text x="${pad+35}" y="${y+13.5}" font-size="9" text-anchor="middle" fill="var(--red)" font-weight="700">✚</text>`;
  y += scaleH + 2;
  // layers
  const bandH = Math.min(26, (bodyH - (nL-1)*gap) / Math.max(nL,1));
  const maxChip = side === "front" ? 92 : 118;
  const chipW = t => Math.min(9 + t.length*6.3, maxChip);
  const chip = (t, x0) => `
      <rect x="${x0}" y="${y+4}" rx="8" height="${bandH-8}" width="${chipW(t)}" fill="${colorOf(t)}"/>
      <text x="${x0+8}" y="${y+bandH-8.5}" font-size="9.5" fill="#fff" font-weight="600">${iconOf(t)} ${t.length>15? t.slice(0,14)+"…" : t}</text>`;
  filled.forEach((slot, i) => {
    const a = ARCHETYPES[slot.id][build[slot.id]];
    const tools = a.tools.filter(t => TOOL_INFO[t].location === (side === "front" ? "Front" : "Back"));
    if (side === "front" && i === 0) geomY0 = y;
    let row = `<rect x="${pad}" y="${y}" width="${W-2*pad}" height="${bandH}" fill="var(--band)" stroke="var(--band-line)" rx="3"/>`;
    let x = pad + 8;
    let chips = "";
    for (const t of tools) { chips += chip(t, x); x += chipW(t) + 4; }
    row += chips;
    row += `<text x="${W/2}" y="${y - 1}" font-size="7.5" text-anchor="middle" fill="var(--band-text)">${slot.label}</text>`;
    if (side === "front") out += `<g data-band="${slot.id}">${row}</g>`;
    else out += row;
    if (side === "front") {
      // per-band controls: ✕ remove, ▼ down, ▲ up (front preview only)
      const cy = y + bandH/2;
      let bx = W - pad - 10;
      for (const [c, glyph, col] of [["rm","✕","var(--accent)"],["down","▼","var(--dim)"],["up","▲","var(--dim)"]]) {
        out += `<g data-ctl="${c}" data-slot="${slot.id}" style="cursor:pointer">
          <rect x="${bx-9}" y="${cy-9}" width="18" height="18" rx="4" fill="var(--band-ctl)" stroke="var(--band-ctl-line)"/>
          <text x="${bx}" y="${cy+3.5}" font-size="9" text-anchor="middle" fill="${col}" font-weight="700" pointer-events="none">${glyph}</text></g>`;
        bx -= 21;
      }
    }
    y += bandH + gap;
  });
  if (!nL) {
    out += `<rect x="${pad}" y="${y}" width="${W-2*pad}" height="${bodyH}" fill="var(--band)" stroke="var(--band-line)" rx="3"/>
            <text x="${W/2}" y="${y + bodyH/2}" font-size="13" text-anchor="middle" fill="var(--band-text)">no layers yet — pick a tool on the left</text>`;
    y += bodyH;
  }
  y += 2;
  // bottom scale
  out += `<rect x="${pad}" y="${y}" width="${W-2*pad}" height="${scaleH}" rx="6" fill="var(--red)" stroke="rgba(0,0,0,.35)"/>`;
  if (side === "front") {
    out += `<circle cx="${pad+8}" cy="${y+scaleH+14}" r="8" fill="none" stroke="var(--keyring)" stroke-width="2.5"/>`;
  }
  svg.innerHTML = out;
  if (side === "front") {
    frontGeom = { y0: geomY0, bandH, gap, W, H, pad, svg };
  }
}

// ================== matching models ==================
function builtTools() {
  const s = new Set();
  for (const slotId in build) for (const t of ARCHETYPES[slotId][build[slotId]].tools) s.add(t);
  if (s.size) s.add("Keyring");
  return s;
}
function renderMatches() {
  const mine = builtTools();
  const box = document.getElementById("matches");
  box.innerHTML = "";
  const scored = Object.entries(MODELS).map(([name, set]) => {
    let inter = 0; for (const t of set) if (mine.has(t)) inter++;
    const union = set.size + mine.size - inter;
    return { name, score: union ? inter / union : 1, inter, size: set.size };
  }).sort((a,b) => b.score - a.score || b.inter - a.inter).slice(0, 8);
  if (!mine.size) { box.innerHTML = `<div class="hint">Your build will be compared with 99 reference models here.</div>`; return; }
  for (const m of scored) {
    const d = document.createElement("div");
    d.className = "match" + (m.score === 1 ? " exact" : "");
    d.innerHTML = `<span>${m.score===1?"⭐ ":""}${m.name}</span><span class="pct">${Math.round(m.score*100)}%</span>`;
    d.title = `${m.inter}/${m.size} tools shared`;
    box.appendChild(d);
  }
}

// ================== export ==================
function download(name, text, type) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([text], {type}));
  a.download = name; a.click(); URL.revokeObjectURL(a.href);
}
document.getElementById("dlJson").onclick = () => {
  const layers = {};
  for (const slotId in build) layers[slotId] = ARCHETYPES[slotId][build[slotId]].tools;
  download("custom_sak.json", JSON.stringify({ layers, order: layerOrder.filter(id => build[id] !== undefined), tools: [...builtTools()].sort() }, null, 2), "application/json");
};
document.getElementById("dlCsv").onclick = () => {
  const mine = [...builtTools()].sort();
  const lines = ["tool,location,in_build"];
  for (const t of TOOLS) lines.push(`"${t}",${TOOL_INFO[t].location},${mine.includes(t)?"X":""}`);
  download("custom_sak.csv", lines.join("\n"), "text/csv");
};

// ================== theme ==================
const THEMES = ["auto", "light", "dark"];
const themeBtn = document.getElementById("themeBtn");
function applyTheme(mode) {
  const dark = mode === "dark" || (mode === "auto" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.dataset.theme = dark ? "dark" : "light";
  themeBtn.textContent = { auto: "◐ auto", light: "☀ light", dark: "☾ dark" }[mode];
  themeBtn.dataset.mode = mode;
  try { localStorage.setItem("sak_theme", mode); } catch (err) {}
}
let themeMode = "auto";
try { themeMode = localStorage.getItem("sak_theme") || "auto"; } catch (err) {}
applyTheme(themeMode);
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
  if (themeBtn.dataset.mode === "auto") applyTheme("auto");
});
themeBtn.onclick = () => {
  applyTheme(THEMES[(THEMES.indexOf(themeBtn.dataset.mode) + 1) % THEMES.length]);
};

// ================== drag & drop layer reorder ==================
function dragInit(e) {
  const band = e.target instanceof Element && e.target.closest("[data-band]");
  if (!band) return;
  if (e.target instanceof Element && e.target.closest("[data-ctl]")) return;
  const g = frontGeom;
  if (!g) return;
  if (e.button !== undefined && e.button !== 0) return;
  g.svg.setPointerCapture(e.pointerId);
  const pt = svgPoint(e, g.svg);
  const drag = { id: band.getAttribute("data-band"), svg: g.svg, moved: false, startX: pt.x, startY: pt.y };
  const proceed = ev => {
    if (!drag.moved) {
      const p = svgPoint(ev, drag.svg);
      if (Math.abs(p.y - drag.startY) < 5 && Math.abs(p.x - drag.startX) < 5) return;
      drag.moved = true;
      selectedTool = null; candSlotFocus = null;
      document.getElementById("candidates").style.display = "none";
      band.setAttribute("opacity", ".45");
    }
    ev.preventDefault();
    const p = svgPoint(ev, drag.svg);
    drag.y = p.y;
    let line = drag.svg.querySelector("#dropLine");
    if (!line) {
      line = document.createElementNS("http://www.w3.org/2000/svg", "line");
      line.id = "dropLine";
      line.setAttribute("stroke", "var(--accent)");
      line.setAttribute("stroke-width", "2.5");
      drag.svg.appendChild(line);
    }
    const idx = dropIndex(drag.y, drag.id);
    drag.insertAt = idx;
    const yLine = geomYForIndex(idx, drag.id);
    line.setAttribute("x1", g.pad); line.setAttribute("x2", g.W - g.pad);
    line.setAttribute("y1", yLine); line.setAttribute("y2", yLine);
    line.style.display = "";
  };
  const finish = () => {
    g.svg.removeEventListener("pointermove", proceed);
    g.svg.removeEventListener("pointerup", finish);
    g.svg.removeEventListener("pointercancel", finish);
    const line = g.svg.querySelector("#dropLine");
    if (line) line.remove();
    band.setAttribute("opacity", "");
    if (drag.moved && drag.insertAt !== undefined) {
      const from = layerOrder.indexOf(drag.id);
      if (from >= 0) {
        layerOrder.splice(from, 1);
        layerOrder.splice(drag.insertAt, 0, drag.id);
        renderAll();
      }
    }
  };
  g.svg.addEventListener("pointermove", proceed);
  g.svg.addEventListener("pointerup", finish);
  g.svg.addEventListener("pointercancel", finish);
}
function svgPoint(ev, svg) {
  const r = svg.getBoundingClientRect();
  const vb = svg.viewBox.baseVal;
  return { x: vb.x + (ev.clientX - r.left) / r.width * vb.width, y: vb.y + (ev.clientY - r.top) / r.height * vb.height };
}
function dropIndex(y, draggedId) {
  const g = frontGeom;
  const slots = orderedSlots().map(s => s.id);
  let above = 0;
  for (let i = 0; i < slots.length; i++) {
    if (slots[i] === draggedId) continue;
    const cy = g.y0 + i * (g.bandH + g.gap) + g.bandH / 2;
    if (y > cy) above++;
  }
  return above;
}
function geomYForIndex(idx, draggedId) {
  const g = frontGeom;
  return g.y0 + idx * (g.bandH + g.gap) - g.gap / 2;
}

// ================== wire up ==================
document.getElementById("search").addEventListener("input", renderPalette);
document.getElementById("frontSvg").addEventListener("pointerdown", dragInit);
document.getElementById("frontSvg").addEventListener("click", e => {
  const g = e.target.closest("[data-ctl]");
  if (!g) return;
  const slotId = g.getAttribute("data-slot");
  const ctl = g.getAttribute("data-ctl");
  // preview controls only act on the stack: drop any pending tool selection
  // so the layer-configuration panel does not pop up on reorder/remove
  selectedTool = null; candSlotFocus = null;
  if (ctl === "up") moveLayer(slotId, -1);
  else if (ctl === "down") moveLayer(slotId, 1);
  else removeLayer(slotId);
});
document.getElementById("resetOrder").onclick = () => {
  layerOrder = SLOTS.filter(s => build[s.id] !== undefined).map(s => s.id);
  renderAll();
};
document.getElementById("clearBtn").onclick = () => {
  for (const k of Object.keys(build)) delete build[k];
  layerOrder = [];
  renderAll();
};
const modelSelect = document.getElementById("modelSelect");
for (const name of Object.keys(MODELS).sort((a,b) => a.localeCompare(b))) {
  const o = document.createElement("option");
  o.value = name; o.textContent = name;
  modelSelect.appendChild(o);
}
modelSelect.onchange = () => { loadModel(modelSelect.value); modelSelect.value = ""; };
document.addEventListener("click", e => {
  const panel = document.getElementById("candidates");
  if (panel.style.display !== "block") return;
  if (panel.contains(e.target)) return;
  const inPalette = e.target instanceof Element && e.target.closest("#palette");
  if (inPalette) return;
  const inBuild = e.target instanceof Element && e.target.closest("#buildPanel");
  if (inBuild) return;
  if (!(e.target instanceof Element)) return;
  if (!e.target.isConnected) return;   // detached by our own re-render: ignore
  panel.style.display = "none"; candSlotFocus = null;
});
function renderStats() {
  const box = document.getElementById("stackStats");
  let mm = 0, g = 0, known = true;
  const nL = Object.keys(build).length;
  for (const slotId in build) {
    const sp = SLOT_SPECS[slotId];
    if (!sp) { known = false; continue; }
    if (sp.mm !== null) mm += sp.mm; else known = false;
    if (sp.g !== null) g += sp.g; else known = false;
  }
  const note = document.getElementById("statsNote");
  if (!nL) { box.innerHTML = ""; note.textContent = ""; return; }
  note.textContent = "Estimated values \u2014 deduced from SAKwiki model specifications (least squares over published model totals).";
  box.innerHTML = `
    <div class="stat" title="Sum of the per-layer thickness (blade layer includes scales & rivets)">
      <span class="k">Thickness</span><span class="v">${known ? mm.toFixed(1) : "≥ " + mm.toFixed(1)}</span><span class="u">mm</span></div>
    <div class="stat" title="Sum of the per-layer weights (blade layer includes scales & rivets)">
      <span class="k">Weight</span><span class="v">${known ? g.toFixed(0) : "≈ " + g.toFixed(0)}</span><span class="u">g</span></div>
    <div class="stat"><span class="k">Layers</span><span class="v">${nL}</span><span class="u">/</span></div>`;
}
// ================== prices & currency ==================
// Effective rates per 1 CHF for the display currency (live rates take
// priority over the CSV snapshot embedded at build time).
function rateOf(cur) {
  if (liveRates && liveRates[cur] !== undefined) return liveRates[cur];
  if (RATES[cur] !== undefined) return RATES[cur];
  return null;
}
// Price of a model in the display currency. Native price preferred; otherwise
// converted from another currency with the exchange rates. null = no data.
function priceOf(name) {
  const p = PRICES[name];
  if (!p) return null;
  if (p[CURRENCY] !== undefined) return p[CURRENCY];
  for (const cur of Object.keys(p)) {
    const rFrom = rateOf(cur);
    const rTo = rateOf(CURRENCY);
    if (rFrom && rTo) return p[cur] / rFrom * rTo;
  }
  return null;
}
// ================== shopping list ==================
// Cost of a donor model: the official Victorinox price (possibly converted to
// the display currency) if available, otherwise a layer-count proxy (a rough
// monotone scale: 1 layer = 10, + 3 per extra layer).
function modelCost(name) {
  const p = priceOf(name);
  if (p !== null) return p;
  const lay = MODELS_LAYERS[name];
  const n = Object.keys(lay).filter(k => k !== "order").length;
  return 10 + 3 * (n - 1);
}
function pricedModelsUseProxy(names) {
  return names.filter(n => priceOf(n) === null);
}
// k-th cheapest solutions of the set-cover DP: state = subset of required
// layer slots still uncovered. Each model can be bought at most once (one
// physical knife per donor). Iterate models, knapsack-style over subsets.
// requirements: [{slot, idx}] — a donor must contain the EXACT layer
// configuration (archetype idx) in that slot, not just any variant of it.
function findDonorSolutions(requirements, k) {
  const req = requirements.map(r => `${r.slot}:${r.idx}`);
  const n = req.length;
  if (!n) return [];
  const full = (1 << n) - 1;
  // coverage mask per model: which exact (slot, archetype) pairs it supplies
  const cands = [];
  for (const name of Object.keys(MODELS_LAYERS)) {
    if (RETIRED.includes(name)) continue;   // no longer sold: not a donor
    const lay = MODELS_LAYERS[name];
    let mask = 0;
    for (let i = 0; i < n; i++) {
      const [slot, idx] = req[i].split(":");
      if (lay[slot] === Number(idx)) mask |= (1 << i);
    }
    if (mask) cands.push({ name, mask, cost: modelCost(name) });
  }
  cands.sort((a, b) => a.cost - b.cost || b.mask - a.mask || a.name.localeCompare(b.name));
  // DP over subsets: keep up to k best (cheapest, tie-break: fewer knives)
  const dp = new Map();   // mask -> [{cost, knives:[names]}] (sorted, <= k entries)
  dp.set(full, [{ cost: 0, knives: [] }]);
  for (const c of cands) {
    const entries = [...dp.entries()];
    for (const [mask, list] of entries) {
      const nm = mask & ~c.mask;
      if (nm === mask) continue;
      const cur = dp.get(nm) || [];
      for (const sol of list) {
        if (sol.knives.includes(c.name)) continue;   // one knife per donor
        const nsol = { cost: sol.cost + c.cost, knives: [...sol.knives, c.name] };
        cur.push(nsol);
      }
      const byCost = (a, b) => (a.cost - b.cost) ||
        (a.knives.length - b.knives.length) ||
        a.knives.join("|").localeCompare(b.knives.join("|"));
      cur.sort(byCost);
      dp.set(nm, cur.slice(0, k));
    }
  }
  const res = dp.get(0) || [];
  return res.map(s => ({ cost: s.cost, knives: s.knives }));
}
function renderShoppingList() {
  const box = document.getElementById("shopList");
  const slots = Object.keys(build);
  if (!slots.length) {
    box.innerHTML = `<div class="hint">Add layers to your build — the cheapest set of donor knives to harvest them from will appear here.</div>`;
    return;
  }
  const reqs = slots.map(s => ({ slot: s, idx: build[s] }));
  const sols = findDonorSolutions(reqs, 3);
  if (!sols.length) {
    box.innerHTML = `<div class="hint">No reference model provides every layer of this build — one layer has no observed donor.</div>`;
    return;
  }
  box.innerHTML = "";
  const names = sols[0].knives.map(n => n);
  // per-donor: which layers it supplies
  const items = names.map(name => {
    const take = reqs.filter(r => MODELS_LAYERS[name][r.slot] === r.idx)
      .map(r => SLOTS.find(x => x.id === r.slot).label);
    return { name, take };
  });
  const sym = { EUR: "€", USD: "$", CHF: "CHF " }[CURRENCY];
  for (const it of items) {
    const d = document.createElement("div");
    d.className = "item";
    const p = priceOf(it.name);
    d.innerHTML = `<span><b>${it.name}</b><div class="take">take: ${it.take.join(", ")}</div></span>
      <span class="price">${p !== null ? sym + p.toFixed(2) : "no price"}</span>`;
    box.appendChild(d);
  }
  const tot = document.createElement("div");
  tot.className = "total";
  tot.innerHTML = `<span>Total \u2014 ${names.length} knife${names.length!==1?"s":""}${pricedModelsUseProxy(names).length ? " *" : ""}</span>
    <span>${sym}${sols[0].cost.toFixed(2)}</span>`;
  box.appendChild(tot);
  if (sols.length > 1) {
    const alt = document.createElement("button");
    alt.className = "alt";
    alt.textContent = `alternative${sols.length > 2 ? "s" : ""}: ${sols.length - 1} more`;
    alt.onclick = () => {
      let h = "";
      for (const s of sols) {
        h += `<div class="item"><span>${s.knives.join(" + ")}</span><span class="price">${{ EUR: "€", USD: "$", CHF: "CHF " }[CURRENCY]}${s.cost.toFixed(2)}</span></div>`;
      }
      box.innerHTML = h + `<button class="alt" onclick="renderShoppingList()">⬅ back</button>`;
    };
    box.appendChild(alt);
  }
  renderShopNote(names);
}
function renderShopNote(names) {
  const note = document.getElementById("shopNote");
  const unpriced = names ? pricedModelsUseProxy(names) : [];
  const ratesSrc = liveRates ? "live exchange rates (frankfurter.app)" : `exchange rates of ${RATES_DATE || "n/a"} (CSV snapshot)`;
  note.innerHTML =
    `Official Victorinox prices (victorinox.com), ${livePrices ? "fetched live" : `fetched on ${PRICES_FETCHED_AT || "n/a"}`}. ` +
    `Amounts in ${CURRENCY} use ${ratesSrc}. ` +
    (unpriced.length ? `* No price found for ${unpriced.join(", ")} \u2014 a layer-count proxy stands in, so totals involving them are estimates.` : "");
}
// ================== live prices & rates ==================
let livePrices = null;      // fetched from victorinox.com when the box is checked
const VX_API = "https://b2cstore-victorinox.frontastic.live/frontastic/data-source/products/list";
const VX_IDS = __VX_IDS_JSON__;
const VX_LOCALES = { USD: "en_US", CHF: "de_CH", EUR: "de_DE" };
async function fetchLiveRates() {
  const r = await fetch("https://api.frankfurter.app/latest?from=CHF&to=USD,EUR");
  const d = await r.json();
  liveRates = { CHF: 1, USD: d.rates.USD, EUR: d.rates.EUR };
}
async function fetchLivePrices() {
  const need = {};
  for (const [model, id] of Object.entries(VX_IDS)) {
    if (RETIRED.includes(model)) continue;
    need[id] = true;
  }
  const out = { USD: {}, CHF: {}, EUR: {} };
  for (const cur of Object.keys(VX_LOCALES)) {
    let start = 0;
    while (start < 1200) {
      const r = await fetch(`${VX_API}?startFrom=${start}&maxResults=100`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Frontastic-Locale": VX_LOCALES[cur] },
        body: JSON.stringify({ maxResults: 100 }),
      });
      const d = await r.json();
      const docs = (((d.dataSourcePayload || {}).data || {}).response || {}).docs || [];
      if (!docs.length) break;
      for (const doc of docs) {
        const c = doc.commerce;
        if (!c || !c.id || !need[c.id]) continue;
        const fv = (c.price || {}).formattedValue;
        const m = fv && fv.match(/[\d]+(?:[.,]\d+)?/);
        if (m) out[cur][c.id] = parseFloat(m[0].replace(",", "."));
      }
      start += 100;
    }
  }
  for (const [model, id] of Object.entries(VX_IDS)) {
    for (const cur of Object.keys(out)) {
      if (out[cur][id] !== undefined) {
        (PRICES[model] = PRICES[model] || {})[cur] = out[cur][id];
      }
    }
  }
  livePrices = out;
}
let liveBusy = false;
async function ensureLive() {
  if (liveBusy || (livePrices && liveRates)) return;
  liveBusy = true;
  document.getElementById("shopNote").textContent = "Fetching live prices and exchange rates\u2026";
  try {
    await Promise.all([fetchLiveRates(), fetchLivePrices()]);
    PRICES_FETCHED_AT = new Date().toISOString().slice(0, 10);
  } catch (err) {
    document.getElementById("shopNote").textContent = "Live fetch failed (offline or blocked) \u2014 using embedded prices.";
  }
  liveBusy = false;
}
const liveChk = document.getElementById("liveChk");
const currencySelect = document.getElementById("currencySelect");
currencySelect.onchange = async () => {
  CURRENCY = currencySelect.value;
  if (liveChk.checked) await ensureLive();
  renderShoppingList();
};
liveChk.onchange = async () => {
  if (liveChk.checked) await ensureLive();
  renderShoppingList();
};
function renderAll() { renderPalette(); renderCandidates(); renderKnife(); renderMatches(); renderStats(); renderShoppingList(); }
renderAll();
</script>
</body>
</html>
"""

# ---------------------------------------------------------------- inject data
slots_json = [
    {"id": SLOT_KEYS[s], "label": SLOT_LABELS[s], "required": s == "Blade layer"}
    for s in SLOT_IDS
]
html = (HTML
        .replace("__TOOLS_JSON__", json.dumps(TOOL_LIST))
        .replace("__TOOL_INFO_JSON__", json.dumps(TOOL_INFO))
        .replace("__SLOTS_JSON__", json.dumps(slots_json))
        .replace("__ARCHETYPES_JSON__", json.dumps(ARCHETYPES))
        .replace("__MODELS_JSON__", json.dumps({m: sorted(t) for m, t in MODELS.items()}))
        .replace("__MODELS_LAYERS_JSON__", json.dumps(models_layers))
        .replace("__SLOT_SPECS_JSON__", json.dumps(SLOT_SPECS))
        .replace("__PRICES_JSON__", json.dumps(PRICES))
        .replace("__RATES_JSON__", json.dumps(RATES))
        .replace("__RATES_DATE_JSON__", json.dumps(RATES_DATE))
        .replace("__PRICES_FETCHED_AT_JSON__", json.dumps(PRICES_FETCHED_AT))
        .replace("__VX_IDS_JSON__", json.dumps(VX_IDS))
        .replace("__RETIRED_JSON__", json.dumps(sorted(RETIRED)))
        .replace("__MODEL_COUNT__", str(len(MODELS)))
        .replace("__TOOL_COUNT__", str(len(TOOL_LIST)))
        .replace("__ARCH_COUNT__", str(sum(len(v) for v in ARCHETYPES.values()))))

out = f"{WS}/sak_builder.html"
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print(f"wrote {out} ({len(html)} bytes)")
