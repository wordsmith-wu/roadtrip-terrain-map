"""Reproducible Cartopy + Natural Earth illustrated itinerary map.

Run with the bundled Python. Dependencies are isolated in .packages.
Coordinates are approximate place centres, not navigation waypoints.
"""
from pathlib import Path
import sys
import json
import math
import os

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / '.packages'))
os.environ['MPLCONFIGDIR'] = str(ROOT / '.mplconfig')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager, patheffects
from matplotlib.patches import FancyBboxPatch
import cartopy.crs as ccrs
from shapely.geometry import shape, box
from shapely.ops import unary_union

TERRAIN = '--terrain' in sys.argv
WEATHER_PRINT = '--weather-print' in sys.argv
WEATHER_LABELS = []
WEATHER_ICONS = []
if WEATHER_PRINT:
    from collections import defaultdict
    weather_snapshot = json.loads((ROOT/'output/v11-weather-interactive/weather.json').read_text(encoding='utf-8'))
    weather_places = defaultdict(list)
    for record in weather_snapshot['records']:
        if record not in weather_places[record['place']]:
            weather_places[record['place']].append(record)
    weather_names = {0:'晴',1:'大部晴',2:'多云',3:'阴',45:'雾',48:'雾凇',51:'小毛毛雨',53:'毛毛雨',55:'强毛毛雨',56:'冻毛毛雨',57:'强冻毛毛雨',61:'小雨',63:'中雨',65:'大雨',66:'冻雨',67:'强冻雨',71:'小雪',73:'中雪',75:'大雪',77:'米雪',80:'阵雨',81:'中阵雨',82:'强阵雨',85:'阵雪',86:'强阵雪',95:'雷暴',96:'雷暴冰雹',99:'强雷暴冰雹'}
CHINA_BORDER = '--china-border' in sys.argv
MILEAGE = '--mileage' in sys.argv
LARGE_TEXT = '--large-text' in sys.argv
STRONG_TERRAIN = '--strong-terrain' in sys.argv
# Water is a default basemap layer. Opt out only for reproducing legacy output.
WATER_SYSTEM = '--no-water-system' not in sys.argv
TERRAIN_EXAGGERATION = 5.0 if STRONG_TERRAIN else 2.5
if TERRAIN:
    from terrain_relief import add_terrain, ELEVATION_CMAP, ELEVATION_NORM
OUT = ROOT / 'output' / ('v7-route-mileage' if MILEAGE else ('v5-border' if CHINA_BORDER else ('v4-terrain' if TERRAIN else 'v3')))
if LARGE_TEXT:
    OUT = ROOT / 'output' / 'v8-large-text'
if STRONG_TERRAIN:
    OUT = ROOT / 'output' / 'v9-strong-terrain'
if WATER_SYSTEM:
    OUT = ROOT / 'output' / 'v10-water-system'
if WEATHER_PRINT:
    OUT = ROOT / 'output' / 'v15-weather-complete-icons'
OUT.mkdir(exist_ok=True, parents=True)
for fn in ['msyh.ttc', 'msyhbd.ttc', 'simkai.ttf']:
    font_manager.fontManager.addfont('C:/Windows/Fonts/' + fn)
plt.rcParams.update({'font.family': 'Microsoft YaHei', 'axes.unicode_minus': False,
                     'svg.fonttype': 'path', 'savefig.facecolor': '#f6f0e2'})
INK, PAPER, MUTED = '#343e39', '#f6f0e2', '#7b8072'
COLORS = ['#b76d43'] * 3 + ['#52786c'] * 4 + ['#a1534b'] * 4 + ['#637f94'] * 3
from itinerary_v3 import P, DAYS, DISPLAY, UNVERIFIED, road_stops, cache_path
ROADS = {}
for day in range(1, 15):
    path = cache_path(ROOT, day)
    response = json.loads(path.read_text(encoding='utf-8'))
    assert response['code'] == 'Ok', f'D{day}: route unavailable'
    assert response['requested_stops'] == road_stops(day), f'D{day}: stale road cache'
    assert max(w['distance'] for w in response['waypoints']) < 2500, f'D{day}: large road snap requires review'
    ROADS[day] = response
if MILEAGE:
    from decimal import Decimal, ROUND_HALF_UP
    daily_km = [(Decimal(str(ROADS[d]['routes'][0]['distance']))/1000).quantize(Decimal('0.1'),rounding=ROUND_HALF_UP)
                for d in range(1,15)]
    cumulative_km = [sum(daily_km[:d],Decimal('0')) for d in range(1,15)]

def load_geo(name):
    obj = json.loads((ROOT / 'data' / name).read_text(encoding='utf-8'))
    region = box(70, 27, 111, 53)
    return [shape(f['geometry']).intersection(region) for f in obj['features']
            if f['geometry'] and shape(f['geometry']).intersects(region)]

COUNTRIES = load_geo('ne_50m_admin_0_countries.geojson')
if CHINA_BORDER:
    raw_countries=json.loads((ROOT/'data'/'ne_50m_admin_0_countries.geojson').read_text(encoding='utf-8'))
    china=next(shape(f['geometry']) for f in raw_countries['features'] if f['properties'].get('ADM0_A3')=='CHN')
    # Extract the genuine polygon boundary BEFORE clipping, to avoid drawing
    # the rectangular geographic crop as if it were a national boundary.
    china_border=china.boundary.intersection(box(65,24,118,55))
    assert not china_border.is_empty
PROVINCES = load_geo('ne_50m_admin_1_states_provinces_lines.geojson')
LAKES = load_geo('ne_50m_lakes.geojson')
RIVERS = load_geo('ne_50m_rivers_lake_centerlines.geojson') if WATER_SYSTEM else []
MAP_REGION = box(70, 27, 111, 53)
OCEAN = MAP_REGION.difference(unary_union(COUNTRIES)) if WATER_SYSTEM else None
GEO = ccrs.PlateCarree()
PROJ = ccrs.LambertConformal(central_longitude=90, central_latitude=40,
                            standard_parallels=(30, 50))
fig = plt.figure(figsize=(30, 22), facecolor=PAPER)

# Very restrained paper grain, not a substitute for the geographic data.
rng = np.random.default_rng(24)
bg = fig.add_axes([0, 0, 1, 1], zorder=-10)
grain = rng.normal(0, .007, (900, 1250, 1))
base = np.array([246, 240, 226])[None, None, :] / 255
bg.imshow(np.clip(base + grain, 0, 1), aspect='auto', extent=[0, 1, 0, 1])
bg.axis('off')

def ft(x, y, s, size=14, color=INK, **kw):
    return fig.text(x, y, s, fontsize=size*(1.25 if LARGE_TEXT else 1), color=color, **kw)

ft(.046, .948, '成都出发 · 新疆十四日环线', 40, fontfamily='KaiTi')
ft(.048, .914, '9月24日—10月7日   /   '+('立体地形晕渲 · 公路路网' if TERRAIN else '公路路网版')+'   /   托格伦夏村 · 乌红线', 15, color=MUTED)
ft(.95, .951, f'{cumulative_km[-1]:,.1f}' if MILEAGE else '14', 40 if MILEAGE else 49, color='#b76d43', ha='right')
ft(.95, .922, 'km · 14天已计算路网' if MILEAGE else '天 · 山河之间', 13, color=MUTED, ha='right')

ax = fig.add_axes([.035, .235, .68, .655], projection=PROJ)
ax.set_extent([73.2, 107.2, 29.0, 50.0], crs=GEO)

def basemap(a, grid=True):
    a.set_facecolor('#b9d5d4' if WATER_SYSTEM else '#eee9dc')
    a.add_geometries(COUNTRIES, GEO, facecolor='#f4efdf', edgecolor='#b5b09d', linewidth=.7, zorder=0)
    if TERRAIN:
        add_terrain(a, detail=not grid, exaggeration=TERRAIN_EXAGGERATION)
        a.add_geometries(COUNTRIES, GEO, facecolor='none', edgecolor='#918875', linewidth=.6, zorder=.8)
    if WATER_SYSTEM and not OCEAN.is_empty:
        # DEM seabed otherwise blends into coastal plains at the low end of the elevation ramp.
        a.add_geometries([OCEAN], GEO, facecolor='#c3d8e2', edgecolor='none', zorder=.85)
        a.add_geometries(COUNTRIES, GEO, facecolor='none', edgecolor='#918875', linewidth=.6, zorder=.9)
    a.add_geometries(PROVINCES, GEO, facecolor='none', edgecolor='#c8c0ad', linewidth=.6, linestyle='--', zorder=1)
    a.add_geometries(LAKES, GEO, facecolor='#91bdc1' if WATER_SYSTEM else '#a6c5c4',
                     edgecolor='#668f96', linewidth=.48 if WATER_SYSTEM else .35, zorder=2)
    if WATER_SYSTEM:
        a.add_geometries(RIVERS, GEO, facecolor='none', edgecolor='#6f9fa6',
                         linewidth=.48 if grid else .65, alpha=.88, zorder=2.05)
    if CHINA_BORDER:
        a.add_geometries([china_border],GEO,facecolor='none',edgecolor=PAPER,linewidth=4.0,zorder=2.7)
        a.add_geometries([china_border],GEO,facecolor='none',edgecolor='#674e64',linewidth=2.0,
                        linestyle=(0,(7,2,1.5,2)),zorder=2.8)
    a.spines['geo'].set_visible(False)
    if grid:
        gl = a.gridlines(crs=GEO, draw_labels={'bottom': 'x', 'left': 'y'},
                         xlocs=range(75, 111, 5), ylocs=range(30, 51, 5),
                         color='#a9aa96', alpha=.3, linewidth=.6, linestyle=(0, (2, 7)))
        gl.xlabel_style = {'size': 10, 'color': MUTED}
        gl.ylabel_style = {'size': 10, 'color': MUTED}

basemap(ax)
if CHINA_BORDER:
    from matplotlib.lines import Line2D
    legend_handles=[Line2D([0],[0],color='#674e64',lw=2,
                    linestyle=(0,(7,2,1.5,2)),label='中国国境线（底图口径）')]
    if WATER_SYSTEM:
        legend_handles += [Line2D([0],[0],color='#6f9fa6',lw=2,label='河流'),
                           Line2D([0],[0],color='#c3d8e2',lw=7,label='海洋'),
                           Line2D([0],[0],color='#91bdc1',lw=7,label='湖泊')]
    border_legend=ax.legend(handles=legend_handles,
                            loc='upper left',bbox_to_anchor=(.022,.972),fontsize=16 if LARGE_TEXT else 12,
                            frameon=True,facecolor=PAPER,edgecolor='#c8beae',framealpha=.94,
                            borderpad=.75,handlelength=3.8)
    border_legend.set_zorder(20)

def maptext(a, lon, lat, text, size=14, color=INK, **kw):
    return a.text(lon, lat, text, transform=GEO, fontsize=size*(1.2 if LARGE_TEXT else 1), color=color, zorder=9, **kw)

for lon, lat, s in [(88.7, 45.7, '新 疆'), (96.2, 36.1, '青 海'),
                    (100.2, 40.1, '甘 肃'), (103.4, 29.8, '四 川')]:
    maptext(ax, lon, lat, s, 23, '#696e61' if TERRAIN else '#a5a48c', fontfamily='KaiTi', ha='center',
            path_effects=[patheffects.withStroke(linewidth=2,foreground=PAPER,alpha=.65)] if TERRAIN else [])
maptext(ax, 83.6, 40.1, '塔 克 拉 玛 干 沙 漠', 15, '#b1a383', ha='center')
maptext(ax, 93.7, 33.8, '青 藏 高 原', 18, '#b2b29e', fontfamily='KaiTi', ha='center')

# Decorative mountain sketches only; explicitly not elevation/terrain data.
for cx, cy, n in ([] if TERRAIN else [(82.9, 42.7, 8), (85.6, 49.35, 5), (91.0, 35.7, 8)]):
    for j in range(n):
        x = cx + (j - n/2) * .46
        h = .20 + rng.random() * .16
        line, = ax.plot([x-.28, x, x+.3], [cy, cy+h, cy], transform=GEO,
                        color='#9ca38c', lw=.8, alpha=.6, zorder=2)
        line.set_sketch_params(.65, 80, 2)

def route(a, day, col, dashed=False, width=2.4, arrows=True):
    pts = np.array(ROADS[day]['routes'][0]['geometry']['coordinates'])
    a.plot(pts[:, 0], pts[:, 1], transform=GEO, color=PAPER, lw=width+2.5, zorder=4)
    a.plot(pts[:, 0], pts[:, 1], transform=GEO, color=col, lw=width,
           linestyle=(0, (3, 3)) if dashed else '-', solid_capstyle='round', zorder=5)
    if arrows:
        # Place a few directional arrows ON the polyline, never on chord lines.
        lengths = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts,axis=0),axis=1))]
        for f in [.3, .7]:
            ix = np.searchsorted(lengths, lengths[-1]*f)
            jx = min(len(pts)-1, np.searchsorted(lengths, lengths[ix]+.07))
            start, end = pts[ix], pts[jx]
            a.annotate('', xy=end, xytext=start, xycoords=GEO._as_mpl_transform(a),
                       annotation_clip=True,
                       arrowprops=dict(arrowstyle='-|>', color=col, lw=1.6,
                                       mutation_scale=13, clip_on=True), zorder=6)

for day in range(1,15):
    route(ax, day, COLORS[day-1])

OFF = {'成都': (12,-12), '广元': (10,8), '瓜州': (10,10), '艾丁湖': (12,-7),
       '乌鲁木齐': (14,7), '白哈巴': (-58,17), '喀纳斯': (15,24), '布尔津': (16,0),
       '魔鬼城': (13,8), '赛里木湖': (-79,13), '伊宁': (-45,-13),
       '巴音布鲁克': (17,-12), '温宿大峡谷': (-101,9), '阿克苏': (12,-16),
       '喀什': (-45,10), '和田': (-15,-22), '塔中镇': (10,8), '若羌': (12,-20),
       '门堂': (-48,14)}

def point(a, name, offset, label=None, size=14, marker='o'):
    if LARGE_TEXT:
        size *= 1.4
        if offset[0] < 0:
            offset = (offset[0]*1.35,offset[1])
    lon, lat = P[name]
    a.plot(lon, lat, marker=marker, ms=5.5, mec=INK, mfc=PAPER, mew=1.1,
           transform=GEO, zorder=8)
    label_text = label or name
    if WEATHER_PRINT and name in weather_places:
        if name == '白哈巴':
            offset = (-185,-25)
        for record in weather_places[name]:
            low, high = record.get('temperature_2m_min'), record.get('temperature_2m_max')
            temperature = f'{low:.0f}～{high:.0f}℃' if low is not None and high is not None else '暂无数据'
            label_text += f"\n{record['date'][5:].replace('-', '/')}          {temperature}"
        size = 13 if a is ax else 11
    annotation = a.annotate(label_text, xy=(lon,lat), xycoords=GEO._as_mpl_transform(a),
               xytext=offset, textcoords='offset points', fontsize=size, color=INK,
               arrowprops=dict(arrowstyle='-', lw=.55, color='#9a9d89'),
               path_effects=[patheffects.withStroke(linewidth=3, foreground=PAPER)], zorder=10)
    if WEATHER_PRINT:
        WEATHER_LABELS.append((a, annotation))
        WEATHER_ICONS.append((a, annotation, name, (label or name).count('\n')+1, size))

for name, off in OFF.items():
    point(ax, name, off, '门堂乡\n（青海久治）' if name == '门堂' else None,
          marker='*' if name == '成都' else 'o')
maptext(ax, 73.6, 36.5, '帕米尔段\n见下方放大图', 11, '#a1534b')
for name, off in [('尼雅遗址',(-86,0)),('楼兰遗址',(10,15))]:
    point(ax, name, off, name+'\n接入待核实', size=12, marker='D')
    # A light leader is a callout, not a fabricated road through the desert.
    if name == '楼兰遗址':
        a, b = P['若羌'], P[name]
    else:
        pts = np.array(ROADS[11]['routes'][0]['geometry']['coordinates'])
        b = P[name]
        a = pts[np.argmin(np.linalg.norm(pts-np.array(b),axis=1))]
    ax.plot([a[0],b[0]],[a[1],b[1]],transform=GEO,color='#aa956d',
            linestyle=(0,(1,5)),lw=1.2,zorder=3)

# Day badges are positioned by longitude/latitude, not pixel geography.
MILEAGE_OFFSETS={1:(-150,35),2:(25,-38),3:(40,30),4:(-120,55),5:(40,-20),
                 6:(-125,42),7:(35,-35),8:(10,-45),9:(-100,-40),10:(-45,-55),
                 11:(25,30),12:(30,25),13:(-175,65),14:(-175,-5)}
if LARGE_TEXT:
    MILEAGE_OFFSETS.update({1:(-150,100),2:(30,-55),3:(50,45),4:(-175,65),
                           5:(45,-30),6:(-200,50),7:(30,-55),8:(-65,-45),9:(-135,-55),
                           10:(-65,-65),11:(30,40),12:(45,40),13:(-235,85),14:(-255,-5)})
for day in range(1,15):
    pts = np.array(ROADS[day]['routes'][0]['geometry']['coordinates'])
    if MILEAGE:
        lon,lat=pts[-1]
        ax.annotate(f'D{day} · {cumulative_km[day-1]:,.1f} km',
                    xy=(lon,lat),xycoords=GEO._as_mpl_transform(ax),
                    xytext=MILEAGE_OFFSETS[day],textcoords='offset points',
                    fontsize=15.5 if LARGE_TEXT else 11,color=COLORS[day-1],weight='bold',zorder=15,
                    bbox=dict(boxstyle='round,pad=.45',fc=PAPER,ec=COLORS[day-1],lw=.9,alpha=.96),
                    arrowprops=dict(arrowstyle='-',color=COLORS[day-1],lw=.9))
        ax.plot(lon,lat,'o',ms=5,mfc=PAPER,mec=COLORS[day-1],transform=GEO,zorder=14)
        continue
    lengths = np.r_[0,np.cumsum(np.linalg.norm(np.diff(pts,axis=0),axis=1))]
    lon,lat = pts[np.searchsorted(lengths,lengths[-1]*.55)]
    ax.annotate(f'D{day}', xy=(lon,lat), xycoords=GEO._as_mpl_transform(ax),
                xytext=(8,10),textcoords='offset points',fontsize=10,color='white',
                zorder=12,bbox=dict(boxstyle='round,pad=.32',fc=COLORS[day-1],ec=PAPER,lw=1))
if MILEAGE:
    ax.annotate('成都出发 · 0 km',xy=P['成都'],xycoords=GEO._as_mpl_transform(ax),
                xytext=(15,-45) if LARGE_TEXT else (25,-35),textcoords='offset points',fontsize=14 if LARGE_TEXT else 11,color=INK,zorder=15,
                bbox=dict(boxstyle='round,pad=.35',fc=PAPER,ec='#aaa18c'),
                arrowprops=dict(arrowstyle='-',color=INK,lw=.8))

# North direction is computed in the projection instead of assuming page-up.
ax.annotate('北', xy=(106, 48.8), xytext=(106, 47.1),
            xycoords=GEO._as_mpl_transform(ax), fontsize=12, ha='center', color=MUTED,
            arrowprops=dict(arrowstyle='-|>', color=MUTED, lw=1.1))

# Separate inset keeps the dense southwest section readable.
inset = fig.add_axes([.054, .075, .285, .248], projection=PROJ)
inset.set_extent([74.65, 77.75, 37.35, 39.75], crs=GEO)
basemap(inset, grid=False)
inset.spines['geo'].set_visible(True)
inset.spines['geo'].set_edgecolor('#b8b4a3')
inset.spines['geo'].set_linewidth(.9)
route(inset, 9, COLORS[8], width=2.0)
route(inset, 10, '#b78d53', width=1.5, dashed=True)
for name, off in {'喀什': (7,8), '白沙湖南岸邮局': (-27,18), '托格伦夏村': (-75,-5),
                  '班迪尔湖': (13,14), '盘龙古道': (18,-18),
                  '泽普胡杨林': (0,-25)}.items():
    point(inset, name, off, size=11)
inset.set_title('帕米尔局部 · D9 / D10', loc='left', fontsize=17 if LARGE_TEXT else 13, color=INK, pad=10)

# Original itinerary, preserved exactly in meaning and date order.
panel = FancyBboxPatch((.731, .073), .244, .812, transform=fig.transFigure,
                       boxstyle='round,pad=.012,rounding_size=.006',
                       fc='#fbf7ed', ec='#d7cfbd', lw=.8, zorder=-1)
fig.add_artist(panel)
ft(.742, .858, '每日行程', 22, fontfamily='KaiTi')
ft(.954, .86, '路线 / 住宿', 10, color=MUTED, ha='right')
y = .822
for i, ((date, stops, lodging, note), description) in enumerate(zip(DAYS, DISPLAY)):
    ft(.744, y, f'D{i+1:02}', 15, color=COLORS[i], weight='bold')
    ft(.775, y, date, 10, color=MUTED)
    ft(.801, y, description, 14 if LARGE_TEXT else 12.5, linespacing=1.4, va='top')
    extra = (.016 if LARGE_TEXT else .012) * description.count('\n')
    ft(.801, y-(.023 if LARGE_TEXT else .020)-extra, ('宿 ' + lodging) if lodging else '返回成都 · 环线结束',
       12, color=MUTED)
    if note:
        ft(.801, y-(.038 if LARGE_TEXT else .033)-extra, note, 10, color=COLORS[i])
    y -= .044 + extra + (.010 if note else 0)
assert y > .075, f'Itinerary overflow: {y}'

ft(.365, .23, '读图说明', 18, fontfamily='KaiTi')
ft(.365, .20, '彩色实线：OSRM 路网计算路径；非实测 GPS 轨迹。', 11, color=MUTED)
ft(.365, .175, '点线：遗址位置引线，不代表道路。局部金色虚线：D10。', 11)
ft(.365, .15, '尼雅、楼兰遗址仅定位；接入路线与可达性需另行确认。', 11)
ft(.365, .125, '邮局按白沙湖南岸近似定位；服务区、酒店未精确定位。', 11)
ft(.365, .10, '路由不含实时封路 / 景区通行限制，出行前请再核实。', 11, color='#a1534b')
ft(.365, .075, '里程按当前路网累计，不含尼雅接入、楼兰往返及其他未建模路段。' if MILEAGE else 'D10 按乌红线（G314）方向绕行，非上一版塔莎方向。', 10, color=MUTED)
if TERRAIN:
    ft(.046,.031,f'高程 Mapzen / AWS · SRTM、GMTED2010: USGS；ETOPO1: NOAA · 路网 © OpenStreetMap contributors / ODbL\n底图及水系 Natural Earth · 2.5D 晕渲，光照坡度增强 {TERRAIN_EXAGGERATION:g} 倍；非可旋转三维模型。点位近似；边界仅作旅行示意。',9,color=MUTED)
    # Key placed in the lower explanatory area, separate from the route map.
    cbax=fig.add_axes([.382,.263,.225,.009])
    cb=fig.colorbar(plt.cm.ScalarMappable(norm=ELEVATION_NORM,cmap=ELEVATION_CMAP),
                   cax=cbax,orientation='horizontal',ticks=[0,1000,3000,5000,7000])
    cb.ax.tick_params(labelsize=12 if LARGE_TEXT else 9,length=2,colors=MUTED)
    cb.outline.set_edgecolor('#b5af9e')
    ft(.382,.282,'高程 / 米   ·   分层设色，不代表植被或积雪',10,color=INK)
else:
    ft(.046, .031, '底图 Natural Earth 1:50m · 路网 © OpenStreetMap contributors / ODbL · OSRM\nLambert 等角圆锥投影 · 山形为装饰；点位近似；边界仅作旅行示意。', 9, color=MUTED)
ft(.967, .034, '程 序 制 图  /  CARTOPY + GEOJSON', 10, color=MUTED, ha='right')
if CHINA_BORDER:
    ft(.046,.015,'国境线按 Natural Earth 数据表示；非官方标准地图，不用于边界认定。',9,color='#674e64')

features = []
for name, coords in P.items():
    if name in {'塔县','乌红线途经点'}:
        continue
    features.append({'type': 'Feature', 'properties': {'name': name, 'precision': 'approximate waypoint',
                     'access_status': 'unverified_no_road_routed' if name in UNVERIFIED else 'not_live_verified'},
                     'geometry': {'type': 'Point', 'coordinates': coords}})
for i, (date, stops, lodging, note) in enumerate(DAYS):
    features.append({'type': 'Feature', 'properties': {'day': i+1, 'date': date, 'lodging': lodging,
                     'note': note, 'route_type': 'osrm_road_route_not_gps', 'requested_stops': stops,
                     'routed_stops': road_stops(i+1), 'source': 'OpenStreetMap / OSRM',
                     'request_url': ROADS[i+1]['request_url'], 'retrieved_utc': ROADS[i+1]['retrieved_utc'],
                     'road_distance_m_excluding_ruins': ROADS[i+1]['routes'][0]['distance'],
                     'excluded_access': [s for s in stops if s in UNVERIFIED]},
                     'geometry': ROADS[i+1]['routes'][0]['geometry']})
(OUT / 'itinerary.geojson').write_text(json.dumps({'type': 'FeatureCollection', 'features': features},
                                                ensure_ascii=False, indent=2), encoding='utf-8')
if MILEAGE:
    import csv
    rows=[{'day':i+1,'date':DAYS[i][0],'daily_km':str(daily_km[i]),
           'cumulative_km':str(cumulative_km[i]),'source_distance_m':ROADS[i+1]['routes'][0]['distance'],
           'excluded_access':';'.join(s for s in DAYS[i][1] if s in UNVERIFIED)} for i in range(14)]
    with (OUT/'mileage.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    (OUT/'mileage.json').write_text(json.dumps({'unit':'km','rounding':'daily rounded half-up to 0.1 km; cumulative sums displayed daily values',
        'total_km':str(cumulative_km[-1]),'excluded':'Niya access, Loulan round trip, and other unmodelled local driving',
        'days':rows},ensure_ascii=False,indent=2),encoding='utf-8')
    milepoints=[{'type':'Feature','properties':{'day':0,'cumulative_km':0,'label':'成都出发'},
                'geometry':{'type':'Point','coordinates':list(P['成都'])}}]
    milepoints += [{'type':'Feature','properties':{'day':i+1,'cumulative_km':float(cumulative_km[i]),'unit':'km'},
                   'geometry':{'type':'Point','coordinates':ROADS[i+1]['routes'][0]['geometry']['coordinates'][-1]}}
                  for i in range(14)]
    (OUT/'route-mileposts.geojson').write_text(json.dumps({'type':'FeatureCollection','features':milepoints},
        ensure_ascii=False,indent=2),encoding='utf-8')
if CHINA_BORDER:
    from shapely.geometry import mapping
    (OUT/'china-border.geojson').write_text(json.dumps({'type':'FeatureCollection','features':[
        {'type':'Feature','properties':{'name':'China boundary as represented by Natural Earth',
        'source':'Natural Earth 1:50m admin_0_countries','not_official_standard_map':True},
        'geometry':mapping(china_border)}]},ensure_ascii=False),encoding='utf-8')
assert len(DAYS) == 14
assert DAYS[0][1][0] == DAYS[-1][1][-1] == '成都'
if WEATHER_PRINT:
    from matplotlib.text import Text, Annotation
    from datetime import datetime
    stamp = datetime.fromisoformat(weather_snapshot['retrieved_utc']).strftime('%Y-%m-%d %H:%M UTC')
    ft(.365,.052,'天气：2026年行程当日预报 · 最低～最高温（℃）',10,color='#426c79')
    ft(.365,.037,f'Open-Meteo · {stamp} 快照；远期预报需复核。',9,color='#426c79')
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    for axes in (ax, inset):
        labels = [label for owner,label in WEATHER_LABELS if owner is axes]
        obstacles = [Text.get_window_extent(t,renderer).expanded(1.03,1.1)
                     for t in axes.texts if t not in labels and isinstance(t,Annotation)]
        for label in labels:
            original = label.get_position()
            best, best_score = original, float('inf')
            candidates = [original] + [(original[0]+dx,original[1]+dy)
                for radius in (25,50,80,115,155,200)
                for dx,dy in ((radius,0),(-radius,0),(0,radius),(0,-radius),
                              (radius,radius),(-radius,radius),(radius,-radius),(-radius,-radius))]
            for candidate in candidates:
                label.set_position(candidate)
                label.update_positions(renderer)
                bounds = Text.get_window_extent(label,renderer).expanded(1.07,1.15)
                area = sum(max(0,min(bounds.x1,b.x1)-max(bounds.x0,b.x0))*max(0,min(bounds.y1,b.y1)-max(bounds.y0,b.y0)) for b in obstacles)
                outside = max(0,axes.bbox.x0-bounds.x0)+max(0,bounds.x1-axes.bbox.x1)+max(0,axes.bbox.y0-bounds.y0)+max(0,bounds.y1-axes.bbox.y1)
                score = area*100 + outside*10000 + (candidate[0]-original[0])**2 + (candidate[1]-original[1])**2
                if score < best_score:
                    best,best_score = candidate,score
            label.set_position(best)
            label.update_positions(renderer)
            obstacles.append(Text.get_window_extent(label,renderer).expanded(1.07,1.15))
    (OUT/'weather.json').write_text(json.dumps(weather_snapshot,ensure_ascii=False,indent=2),encoding='utf-8')
    # Use the same Unicode weather emoji as the HTML, rendered with Windows' color emoji font.
    from PIL import Image, ImageDraw, ImageFont
    from matplotlib.offsetbox import OffsetImage, AnnotationBbox
    emoji_font = ImageFont.truetype('C:/Windows/Fonts/seguiemj.ttf',96)
    emoji_codes = {0:'☀️',1:'🌤️',2:'⛅',3:'☁️',45:'🌫️',48:'🌫️',51:'🌦️',53:'🌦️',55:'🌧️',56:'🌧️',57:'🌧️',61:'🌦️',63:'🌧️',65:'🌧️',66:'🌧️',67:'🌧️',71:'🌨️',73:'🌨️',75:'❄️',77:'❄️',80:'🌦️',81:'🌧️',82:'⛈️',85:'🌨️',86:'❄️',95:'⛈️',96:'⛈️',99:'⛈️'}
    for axes, label, name, heading_lines, size in WEATHER_ICONS:
        # Match Matplotlib's computed multiline baselines exactly.
        label.update_positions(renderer)
        _, line_info, _ = label._get_layout(renderer)
        for row, record in enumerate(weather_places.get(name,[])):
            if record.get('weather_code') not in emoji_codes:
                continue  # Missing/unknown code is not a sunny forecast.
            # Segoe UI Emoji's color layers are clipped with Pillow's centered
            # anchor. Render at a padded default origin before alpha-cropping.
            canvas = Image.new('RGBA',(256,256))
            ImageDraw.Draw(canvas).text((40,40),emoji_codes.get(record['weather_code'],'🌡️'),font=emoji_font,embedded_color=True)
            bounds = canvas.getbbox()
            assert bounds and bounds[0] > 0 and bounds[1] > 0 and bounds[2] < 256 and bounds[3] < 256
            cropped = canvas.crop(bounds)
            line = line_info[heading_lines+row]
            dx, dy = label.get_position()
            # Measure the actual font rather than assuming a fixed date width.
            # Reserve a full slot, and constrain BOTH icon dimensions to avoid adjacent rows.
            date_text = record['date'][5:].replace('-', '/')
            date_width = renderer.get_text_width_height_descent(date_text,label.get_fontproperties(),False)[0]*72/fig.dpi
            slot_width = renderer.get_text_width_height_descent('          ',label.get_fontproperties(),False)[0]*72/fig.dpi
            icon_size = min(size*.9, slot_width-6)
            icon = OffsetImage(np.asarray(cropped),zoom=icon_size/max(cropped.width,cropped.height))
            axes.add_artist(AnnotationBbox(icon,label.xy,xycoords=GEO._as_mpl_transform(axes),
                xybox=(dx+date_width+slot_width/2,dy+line[2][1]*72/fig.dpi+size*.35),boxcoords='offset points',
                frameon=False,box_alignment=(.5,.5),zorder=12))
fig.savefig(OUT / 'xinjiang-route-map.png', dpi=300)
fig.savefig(OUT / 'xinjiang-route-map.svg')
fig.savefig(OUT / 'preview.png', dpi=65)
print('Saved 9000 × 6600 PNG, outlined-text SVG, preview and itinerary GeoJSON.')
