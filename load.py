"""Extract Deezer data into raw JSONL on the local disk.

Does only extract part of the assignment. Uses the Deezer API to 
1) search for specific festival playlists
2) download the festivals setlists from the playlists
3) Hydrate metadata relative to each song in the setlist (album, artist)
"""

import json
import re
import shutil
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.parse import quote

import requests

import config

QUOTA_EXCEEDED = 4
ATTEMPTS = 4

session = requests.Session()
lock = threading.Lock()
next_call = 0.0


def throttle():
    """Very simple rate limiter to stay under deezer 50req/5s limit, see config"""
    global next_call
    with lock:
        slot = max(time.time(), next_call)
        next_call = slot + config.DELAY
    time.sleep(max(0.0, slot - time.time()))


def fetch(url):
    """One throttled GET. None means the call failed and may be retried."""
    throttle()
    try:
        return session.get(url, timeout=config.TIMEOUT).json()
    except Exception:
        return None


def get(url):
    """GET on the Deezer API, backing off on transient failures.

    Returns the payload, or {} when there is nothing to fetch.
    """
    for attempt in range(ATTEMPTS):
        body = fetch(url)
        if body is None:
            time.sleep(1 + attempt)
        elif "error" not in body:
            return body


        elif body["error"].get("code") == QUOTA_EXCEEDED:
            time.sleep(1 + attempt)
        else:
            return {} 
    return {}


def write(entity, rows):
    """One JSONL object per line, saved in data/raw/XXXX/data.jsonl."""
    path = config.RAW_DIR / entity / "data.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def find_playlists(festival):
    """
    Find all relevant playlists. defined in config.
    For each festival we first query the deezer api for the relevant keyword (festival name)
    and then filter that for the official festival accont only and if there is a 20XX year in name
    """

    url = f"{config.API}/search/playlist?q={quote(festival['query'])}&limit=100"
    found = []
    for p in get(url).get("data", []):
        owner = re.sub(r"[^a-z0-9]", "", (p.get("user") or {}).get("name", "").lower())
        year = re.search(r"20(2[2-6])", p.get("title", ""))

        # check if playlist is official and full set 
        if festival["creator"] in owner and year and p.get("nb_tracks", 0) >= config.MIN_PLAYLIST_TRACKS:
            found.append(dict(p, _festival=festival["name"], _edition=year.group(0)))
    return found


def linked_ids(tracks, key):
    """ Minly used to get feat artists/single albums for each track that are not the main metadata info"""
    return {t[key]["id"] for t in tracks if (t.get(key) or {}).get("id")}


def hydrate(endpoint, ids):
    """
    Main method to fetch album/artist metadata 
    given a specific track id found in playlists
    """
    urls = [f"{config.API}/{endpoint}/{i}" for i in sorted(ids)]
    found = []
    with ThreadPoolExecutor(config.WORKERS) as pool:
        for i, obj in enumerate(pool.map(get, urls), 1):
            if obj.get("id"):
                found.append(obj)
            if i % 500 == 0:
                print(f"  {endpoint} {i}/{len(urls)}", flush=True)
    write(endpoint + "s", found)
    print(f"{endpoint + 's':9} {len(found)}/{len(urls)}")
    return len(found)


def main():
    start = time.time()
    # clean the folder
    #shutil.rmtree(config.RAW_DIR, ignore_errors=True)

    playlists = []
    for festival in config.FESTIVALS:
        found = find_playlists(festival)
        print(f"{festival['name']:24} {len(found):2} playlists")
        playlists += found
    write("playlists", playlists)

    # Playlist payloads are occasionally incomplete, hence the guards below.
    tracks = []
    for p in playlists:
        for t in get(f"{config.API}/playlist/{p['id']}/tracks?limit=1000").get("data", []):
            if t.get("id"):
                tracks.append(dict(t, _festival=p["_festival"], _edition=p["_edition"],
                                   _playlist_id=p["id"]))
    write("playlist_tracks", tracks)

    track_ids = {t["id"] for t in tracks}
    album_ids = linked_ids(tracks, "album")
    artist_ids = linked_ids(tracks, "artist")
    print(f"\n{len(tracks)} rows | {len(track_ids)} tracks, "
          f"{len(album_ids)} albums, {len(artist_ids)} artists")

    counts = {"playlists": len(playlists), "playlist_tracks": len(tracks)}
    counts["albums"] = hydrate("album", album_ids)
    counts["tracks"] = hydrate("track", track_ids)
    counts["artists"] = hydrate("artist", artist_ids)


    # Write nice metadata.json
    (config.RAW_DIR / "_manifest.json").write_text(json.dumps({
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": round(time.time() - start, 1),
        "counts": counts,
    }, indent=2))
    print(f"\ndone in {(time.time() - start) / 60:.1f} min")


if __name__ == "__main__":
    main()
