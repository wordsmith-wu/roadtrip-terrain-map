"""Georeferenced multi-direction hillshade from real elevation, no fake mountains."""
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter
from matplotlib.colors import LinearSegmentedColormap, Normalize
import cartopy.crs as ccrs

ROOT=Path(__file__).resolve().parent
ELEVATION_CMAP=LinearSegmentedColormap.from_list('warm_relief',[
    (0.0,'#d0ddc5'),(.075,'#dce3ca'),(.18,'#e9dfbd'),(.32,'#d5c7a4'),
    (.47,'#c0b59b'),(.63,'#b8b7ad'),(.79,'#d3d7d3'),(1.0,'#fafaf3')])
ELEVATION_NORM=Normalize(-200,7000,clip=True)

def raster(name, exaggeration=2.5):
    data=np.load(ROOT/'data'/'terrain'/f'{name}.npz')
    h=gaussian_filter(data['elevation'],.55)
    extent=data['extent']
    dx=(extent[1]-extent[0])/h.shape[1]
    dy=(extent[3]-extent[2])/h.shape[0]
    rows=extent[3]-(np.arange(h.shape[0])+.5)*dy
    lat=np.arctan(np.sinh(rows/6378137))
    # Correct Mercator scale before calculating true ground slopes.
    gy,gx=np.gradient(h,dy,dx)
    gx=gx/np.cos(lat[:,None])*exaggeration
    gy=-gy/np.cos(lat[:,None])*exaggeration
    norm=np.sqrt(1+gx*gx+gy*gy)
    shade=np.zeros_like(h)
    for az,weight in [(315,.65),(270,.2),(45,.15)]:
        az=np.deg2rad(az); alt=np.deg2rad(38)
        shade+=weight*np.maximum(0,(-gx*np.sin(az)*np.cos(alt)-gy*np.cos(az)*np.cos(alt)+np.sin(alt))/norm)
    colors=ELEVATION_CMAP(ELEVATION_NORM(h))[:,:,:3]
    relief=np.clip(colors*(.52+.80*shade[:,:,None]),0,1)
    relief=.93*relief+.07*np.array([246,240,226])/255
    return relief,extent

def add_terrain(ax,detail=False,exaggeration=2.5):
    rgb,extent=raster('pamir' if detail else 'main', exaggeration=exaggeration)
    ax.imshow(rgb,extent=extent,origin='upper',transform=ccrs.GOOGLE_MERCATOR,
              regrid_shape=(1600,1500) if detail else (3000,2500),
              interpolation='bilinear',zorder=.3)
