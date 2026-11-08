#!/usr/bin/env python3
"""Hot Wheels tracker: auto-sync release lists, track TH / STH, browse by genre.

Setup:  pip install anthropic requests beautifulsoup4
        export ANTHROPIC_API_KEY=your_key
Usage:
  python hotwheels.py sync                 # pull sources below, add anything new
  python hotwheels.py hunts                # only Treasure Hunts / Super Treasure Hunts
  python hotwheels.py list [genre]         # everything, grouped by genre
  python hotwheels.py add [--th|--sth] "Car Name" ...   # manual add
"""
import json
import sys
from pathlib import Path

import anthropic
import requests
from bs4 import BeautifulSoup

DB = Path("hotwheels.json")
MODEL = "claude-sonnet-5-5"
GENRES = [
    "Muscle", "Exotic/Supercar", "JDM", "Euro", "Truck/Off-road",
    "Classic/Hot Rod", "Racing", "Fantasy/Novelty", "Movie/TV", "Other",
]

# (label, url). Edit the year in these URLs each season, or add new sources.
# Pages may be incomplete early in the year; re-run `sync` as lists fill in.
SOURCES = [
    ("STH", "https://164custom.com/hot-wheels/super-treasure-hunt/2026.html"),
    ("TH", "https://hotwheels.fandom.com/wiki/2026_Treasure_Hunts_Series"),
    ("MAINLINE", "https://munclemikes.com/pages/hot-wheels-complete-casting-list-of-cars-2026"),
]
LABELS = {
    "STH": "a Super Treasure Hunt",
    "TH": "a regular Treasure Hunt",
    "MAINLINE": "part of the mainline lineup",
}


def load():
    db = json.loads(DB.read_text()) if DB.exists() else {}
    # migrate entries from the first version (name -> genre string)
    return {
        k: v if isinstance(v, dict) else {"name": k, "genre": v, "hunt": "MAINLINE"}
        for k, v in db.items()
    }


def save(db):
    DB.write_text(json.dumps(db, indent=2, sort_keys=True))


def ask(prompt):
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=MODEL, max_tokens=8000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)


def fetch_text(url):
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (personal hobby tracker)"}, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    return " ".join(soup.get_text(" ").split())[:60000]


def extract(text, hunt):
    """Pull car names + genres out of a page's text."""
    return ask(
        f"Below is text from a Hot Wheels web page. List every Hot Wheels casting it presents "
        f"as {LABELS[hunt]}. Use the car name only (no year, color, or series). Assign each one "
        f"genre from: {GENRES}. Reply with ONLY a JSON list of "
        '{"name": ..., "genre": ...} objects. Skip anything unrelated.\n\n' + text
    )


def key_for(name, hunt):
    return name if hunt == "MAINLINE" else f"{name} [{hunt}]"


def add_entries(db, entries, hunt):
    """Add entries not already stored. Returns the list of new keys."""
    new = []
    for e in entries:
        name = e["name"].strip()
        key = key_for(name, hunt)
        if key in db:
            continue
        genre = e.get("genre") if e.get("genre") in GENRES else "Other"
        db[key] = {"name": name, "genre": genre, "hunt": hunt}
        new.append(key)
    return new


def sync():
    db = load()
    found_hunts = []
    for hunt, url in SOURCES:
        try:
            entries = extract(fetch_text(url), hunt)
        except Exception as err:  # keep going if one source is down or changes layout
            print(f"[{hunt}] skipped {url}: {err}")
            continue
        new = add_entries(db, entries, hunt)
        print(f"[{hunt}] {len(entries)} found, {len(new)} new")
        if hunt != "MAINLINE":
            found_hunts += new
    save(db)
    if found_hunts:
        print("\nNew hunts:")
        for k in found_hunts:
            print(f"  * {k} ({db[k]['genre']})")


def add(args):
    hunt = "STH" if "--sth" in args else "TH" if "--th" in args else "MAINLINE"
    names = [a for a in args if not a.startswith("--")]
    entries = ask(
        f"Assign each Hot Wheels casting one genre from: {GENRES}. Reply with ONLY a JSON list "
        f'of {{"name": ..., "genre": ...}} objects. Names: {json.dumps(names)}'
    )
    db = load()
    for k in add_entries(db, entries, hunt):
        print(f"{k} -> {db[k]['genre']}")
    save(db)


def show(genre=None, hunts_only=False):
    by_genre = {}
    for key, v in load().items():
        if hunts_only and v["hunt"] == "MAINLINE":
            continue
        by_genre.setdefault(v["genre"], []).append(key)
    for g in sorted(by_genre):
        if genre and g.lower() != genre.lower():
            continue
        print(f"\n{g} ({len(by_genre[g])})")
        for key in sorted(by_genre[g]):
            print(f"  - {key}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["sync"]:
        sync()
    elif a[:1] == ["hunts"]:
        show(hunts_only=True)
    elif a[:1] == ["list"]:
        show(a[1] if len(a) > 1 else None)
    elif a[:1] == ["add"] and len(a) > 1:
        add(a[1:])
    else:
        print(__doc__)
