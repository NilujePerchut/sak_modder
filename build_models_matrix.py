#!/usr/bin/env python3
"""Build the 91mm model x tool matrix from the layer script's model data.

The model toolsets live in build_model_layers.py (single source of truth);
this script reuses them to emit the model x tool presence matrix.
"""
import csv
import os

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build_model_layers.py")
with open(path, encoding="utf-8") as f:
    source = f.read()
data_section = source.split("def assign_layers")[0]

namespace = {}
exec(compile(data_section, path, "exec"), namespace)

TOOLS = namespace["TOOLS"]
M = namespace["M"]

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "victorinox_91mm_models_tools.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["model"] + TOOLS)
    for model, tools in M.items():
        w.writerow([model] + ["X" if t in tools else "" for t in TOOLS])

print(f"models: {len(M)}, tool columns: {len(TOOLS)}")
