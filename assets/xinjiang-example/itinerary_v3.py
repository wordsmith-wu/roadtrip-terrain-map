"""Latest itinerary: Toghrak/Tuogelunxia overnight, G314 return, no bookings."""
from copy import deepcopy
from pathlib import Path
from itinerary_v2 import P as OLD_P, DAYS as OLD_DAYS, DISPLAY as OLD_DISPLAY, UNVERIFIED

P = deepcopy(OLD_P)
P.pop('莎车')
P['托格伦夏村'] = (75.273889, 37.776944)
# Existing OSRM geometry point on the G314 corridor. Routing-only, not a stop.
P['乌红线途经点'] = (75.044946, 38.447191)
DAYS = [(date,deepcopy(stops),lodging,'') for date,stops,lodging,_ in OLD_DAYS]
DAYS[8] = ('10/2',['阿克苏','喀什','白沙湖南岸邮局','盘龙古道','班迪尔湖','托格伦夏村'],'托格伦夏村','')
DAYS[9] = ('10/3',['托格伦夏村','泽普胡杨林','和田'],'和田','经乌红线（G314） · 和田夜市')
DAYS[10] = (*DAYS[10][:3], '尼雅遗址接入待核实')
DAYS[11] = (*DAYS[11][:3], '楼兰遗址往返待核实')
DISPLAY = deepcopy(OLD_DISPLAY)
DISPLAY[8] = '阿克苏 → 喀什 → 白沙湖南岸邮局\n→ 盘龙古道 → 班迪尔湖\n→ 塔县托格伦夏村'
DISPLAY[9] = '托格伦夏村 → 泽普胡杨林\n→ 和田夜市'

def road_stops(day):
    if day == 10:
        # G314 northbound to Kashgar, then onward to Zepu; Kashgar here is only
        # a corridor shaping point, not an added sightseeing visit.
        return ['托格伦夏村','乌红线途经点','喀什','泽普胡杨林','和田']
    out=[]
    for name in DAYS[day-1][1]:
        if name not in UNVERIFIED and (not out or name != out[-1]):
            out.append(name)
    return out

def cache_path(root, day):
    return Path(root)/'data'/('roads-v3' if day in (9,10) else 'roads-v2')/f'day-{day:02}.json'
