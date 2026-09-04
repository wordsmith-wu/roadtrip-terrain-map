"""Fetch and cache OSRM road geometries; no invented curves or silent fallback."""
from pathlib import Path
from datetime import datetime, timezone
import json
import time
import urllib.request
import sys
from itinerary_v3 import P, DAYS, road_stops, cache_path

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / 'data' / 'roads-v3'
CACHE.mkdir(exist_ok=True)
ENDPOINT = 'https://router.project-osrm.org/route/v1/driving/'
selected = [int(s) for s in sys.argv[1:]] or range(1,15)
for day in selected:
    names = road_stops(day)
    coords = ';'.join(f'{P[n][0]},{P[n][1]}' for n in names)
    steps = 'true' if day == 10 else 'false'
    url = ENDPOINT + coords + f'?overview=full&geometries=geojson&steps={steps}&continue_straight=false'
    path = cache_path(ROOT, day)
    if path.exists():
        cached = json.loads(path.read_text(encoding='utf-8'))
        if cached.get('request_url') == url and cached.get('code') == 'Ok':
            print(f'D{day:02}: cached', flush=True)
            continue
    try:
        req = urllib.request.Request(url, headers={'User-Agent':'TravelRoutePoster/1.0'})
        with urllib.request.urlopen(req, timeout=55) as response:
            data = json.load(response)
        if data.get('code') != 'Ok':
            raise ValueError(data)
        data['request_url'] = url
        data['retrieved_utc'] = datetime.now(timezone.utc).isoformat()
        data['requested_stops'] = names
        path.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
        r = data['routes'][0]
        print(f'D{day:02}: {r["distance"]/1000:.0f} km, {len(r["geometry"]["coordinates"])} vertices; snaps: '
              + ', '.join(f'{n}={w["distance"]:.0f}m' for n,w in zip(names,data['waypoints'])),flush=True)
    except Exception as e:
        print(f'D{day:02}: FAILED {e}',flush=True)
    time.sleep(1.1)
