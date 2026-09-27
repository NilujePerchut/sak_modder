#!/usr/bin/env python3
"""Fetch current Victorinox prices from the official victorinox.com storefront.

Uses the public Frontastic data-source endpoint that powers the victorinox.com
product listing: POST /frontastic/data-source/products/list with a
Frontastic-Locale header selecting the country/price zone.

Prices are the official manufacturer prices (all taxes included as shown on
the site) for the base variant of each matched model, in three currencies:
USD (locale en_US), CHF (locale de_CH), EUR (locale de_DE / fr_FR).

Output: victorinox_91mm_model_prices.csv (model,price_usd,price_chf,price_eur,victorinox_id,fetched_at)
Only models currently sold (per victorinox_91mm_model_availability.csv) are priced.
Matching is done by hand-curated alias + Victorinox product id (see ALIASES).
"""
import csv
import datetime
import json
import re
import sys
import time
import urllib.request

API = "https://b2cstore-victorinox.frontastic.live/frontastic/data-source/products/list"
PAGE = 30

LOCALES = {"USD": "en_US", "CHF": "de_CH", "EUR": "de_DE"}

# model name (our CSV) -> search strings and/or Victorinox product id
# ids are the base article numbers shown on victorinox.com product pages
ALIASES = {
    "Golfer Special": None,
    "Waiter Plus": "0.3303",
    "Compact": "1.3405",
    "Spartan": "1.3603",
    "Tinker": "1.4603",
    "Weekender": None,
    "Camper": "1.3613",
    "Climber": "1.3703",
    "Companion": "1.3909",
    "FASS 90": None,
    "Hiker": "1.4613",
    "Super Tinker": "1.4703",
    "Angler": "1.3653.72",
    "Bass Fishing": None,
    "Climber Lite": None,
    "Cybertool M (34)": "1.7725.T",
    "Cyber": None,
    "Yeoman": None,
    "Deluxe Tinker": "1.4723",
    "Explorer": "1.6703",
    "Fieldmaster": "1.4713",
    "Fisherman": "1.4733.72",
    "Huntsman": "1.3713",
    "Master Electrician": None,
    "Master Gardener": None,
    "Mountaineer": "1.3743",
    "Whitetail Deer": None,
    "Yeoman Mechanic": None,
    "Barista Tool": "1.5924.LMA",
    "Huntsman Lite": "1.7915.T",
    "Ranger": "1.3763",
    "Handyman": "1.3773",
    "Cybertool L (41)": "1.7775.T",
    "SwissChamp": "1.6795",
    "SwissChamp XXL": "1.6795.XXL",
}


def fetch_catalog(locale):
    """Fetch the whole catalog (name, id, price, slug) for one locale."""
    catalog = []
    start = 0
    while True:
        payload = {"maxResults": PAGE}
        req = urllib.request.Request(
            f"{API}?startFrom={start}&maxResults={PAGE}",
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Frontastic-Locale": locale,
                "Origin": "https://www.victorinox.com",
            },
            data=json.dumps(payload).encode(),
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8"))
        docs = data["dataSourcePayload"]["data"]["response"]["docs"]
        if not docs:
            break
        for d in docs:
            c = d.get("commerce") or {}
            if not c.get("id"):
                continue
            price = (c.get("price") or {}).get("formattedValue")
            catalog.append(
                {
                    "name": c.get("name") or "",
                    "id": c["id"],
                    "price": price,
                    "seoPath": c.get("seoPath") or "",
                }
            )
        start += PAGE
        if start >= 900:
            break
        time.sleep(0.25)
    return catalog


def price_value(formatted):
    """'$ 34.00' / 'CHF 25.00' / 'EUR 27,00' -> 34.0 / 25.0 / 27.0"""
    if not formatted:
        return None
    m = re.search(r"[\d]+(?:[.,]\d+)?", formatted.replace("\u00a0", " "))
    if not m:
        return None
    return float(m.group(0).replace(",", "."))


def main():
    rows = list(csv.DictReader(open("victorinox_91mm_model_availability.csv", encoding="utf-8")))
    available = [r["model"] for r in rows if r["retired"].strip().upper() not in ("Y", "SR")]
    missing = [m for m in available if m not in ALIASES]
    assert not missing, f"aliases missing for: {missing}"

    catalogs = {}
    for cur, loc in LOCALES.items():
        print(f"fetching catalog ({cur}, locale {loc}) ...", file=sys.stderr)
        catalogs[cur] = fetch_catalog(loc)
        print(f"  {len(catalogs[cur])} products", file=sys.stderr)

    by_id = {cur: {} for cur in catalogs}
    for cur, cat in catalogs.items():
        for p in cat:
            by_id[cur][p["id"]] = p

    out = []
    today = datetime.date.today().isoformat()
    unmatched = []
    for model in available:
        pid = ALIASES[model]
        row = {"model": model, "price_usd": "", "price_chf": "", "price_eur": "", "victorinox_id": pid or "", "fetched_at": today}
        if pid is None:
            unmatched.append(model)
            continue
        matched = {cur: by_id[cur].get(pid) for cur in catalogs}
        for cur, p in matched.items():
            if p:
                row[f"price_{cur.lower()}"] = price_value(p["price"])
        if row["price_usd"] or row["price_chf"] or row["price_eur"]:
            out.append(row)
        else:
            unmatched.append(model)
    # keep only rows with at least one price
    out = [r for r in out if r["price_usd"] or r["price_chf"] or r["price_eur"]]

    with open("victorinox_91mm_model_prices.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["model", "price_usd", "price_chf", "price_eur", "victorinox_id", "fetched_at"])
        for r in out:
            w.writerow([r["model"], r["price_usd"], r["price_chf"], r["price_eur"], r["victorinox_id"], r["fetched_at"]])
    print(f"wrote {len(out)} priced models to victorinox_91mm_model_prices.csv", file=sys.stderr)
    if unmatched:
        print("no price found for: " + ", ".join(unmatched), file=sys.stderr)


if __name__ == "__main__":
    main()
