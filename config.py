"""Sampling frame and runtime settings for the Deezer extraction.

Nothing here filters data. The release-year window, the strata and the quotas
are applied downstream in dbt.
"""

from pathlib import Path

API = "https://api.deezer.com"

# Festivals whose Deezer account publishes official line-up playlists.
# `creator` is matched against the playlist owner's name, which is what keeps
# fan wishlists such as "Wishlist Hellfest 2027" out of the frame.

FESTIVALS = [
    {"name": "Les Ardentes",           "query": "les ardentes",          "creator": "ardentes"},
    {"name": "Garorock",               "query": "garorock",              "creator": "garorock"},
    {"name": "Musilac",                "query": "musilac",               "creator": "musilac"},
    {"name": "Francofolies",           "query": "francofolies",          "creator": "francofolies"},
    {"name": "We Love Green",          "query": "we love green",         "creator": "welovegreen"},
    {"name": "Rock en Seine",          "query": "rock en seine",         "creator": "rockenseine"},
    {"name": "Nancy Jazz Pulsations",  "query": "nancy jazz pulsations", "creator": "nancyjazz"},
    {"name": "Printemps de Bourges",   "query": "printemps de bourges",  "creator": "printempsdebourges"},
]

# Smaller playlists are themed side-selections rather than line-ups.
MIN_PLAYLIST_TRACKS = 40

RAW_DIR = Path("data/raw")

# Ultra simple rate limiter : Deezer has a hard 50req/5s so we time each request to fire a little bit over every 0.1s
DELAY = 0.11

WORKERS = 8
TIMEOUT = 25
