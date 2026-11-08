
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
