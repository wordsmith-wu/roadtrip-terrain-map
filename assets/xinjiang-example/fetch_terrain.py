"""Download real Terrarium elevation tiles, decode, and cache geographic grids."""
from pathlib import Path
import sys, math, json, urllib.request, io
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'.packages'))
import numpy as np
from PIL import Image

CACHE=ROOT/'data'/'terrain'
CACHE.mkdir(parents=True,exist_ok=True)
BASE='https://s3.amazonaws.com/elevation-tiles-prod/terrarium'

def tilexy(lon,lat,z):
    n=2**z
    return int((lon+180)/360*n),int((1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n)

def tile(item):
    z,x,y=item
    path=CACHE/f'{z}-{x}-{y}.png'
    if not path.exists():
        url=f'{BASE}/{z}/{x}/{y}.png'
        for attempt in range(3):
            try:
                with urllib.request.urlopen(url,timeout=35) as r:
                    blob=r.read()
                with Image.open(io.BytesIO(blob)) as check:
                    assert check.size==(256,256)
                path.write_bytes(blob)
                break
            except Exception:
                if attempt==2:
                    raise
    with Image.open(path) as im:
        rgb=np.array(im.convert('RGB'),dtype=np.float32)
    return x,y,rgb[:,:,0]*256+rgb[:,:,1]+rgb[:,:,2]/256-32768

for name,z,bounds in [('main',6,(67.5,118,24,55)),('pamir',9,(74.1,78.3,37.0,40.1))]:
    west,east,south,north=bounds
    xmin,ymin=tilexy(west,north,z)
    xmax,ymax=tilexy(east,south,z)
    jobs=[(z,x,y) for y in range(ymin,ymax+1) for x in range(xmin,xmax+1)]
    dem=np.empty(((ymax-ymin+1)*256,(xmax-xmin+1)*256),dtype=np.float32)
    with ThreadPoolExecutor(max_workers=4) as pool:
        for k,(x,y,data) in enumerate(pool.map(tile,jobs),1):
            dem[(y-ymin)*256:(y-ymin+1)*256,(x-xmin)*256:(x-xmin+1)*256]=data
            if k%10==0 or k==len(jobs):
                print(f'{name}: {k}/{len(jobs)} tiles',flush=True)
    half=math.pi*6378137
    span=2*half/(2**z)
    extent=np.array([-half+xmin*span,-half+(xmax+1)*span,half-(ymax+1)*span,half-ymin*span])
    assert np.isfinite(dem).all()
    assert dem.max()>5000
    np.savez_compressed(CACHE/f'{name}.npz',elevation=dem,extent=extent,zoom=z)
    meta={'source':BASE,'dataset':'Mapzen Terrain Tiles on AWS','projection':'EPSG:3857',
          'zoom':z,'tile_count':len(jobs),'shape':list(dem.shape),'extent':extent.tolist(),
          'range_m':[float(dem.min()),float(dem.max())],
          'retrieved_utc':datetime.now(timezone.utc).isoformat(),
          'decode':'R*256+G+B/256-32768; metres',
          'attribution':'https://github.com/tilezen/joerd/blob/master/docs/attribution.md'}
    (CACHE/f'{name}-metadata.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    print(f'{name}: {dem.shape}; elevation {dem.min():.0f}..{dem.max():.0f} m',flush=True)
