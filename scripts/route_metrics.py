"""Validate normalized road segments and derive route-anchored cumulative km."""
import argparse
from decimal import Decimal, ROUND_HALF_UP
import json
import math
from pathlib import Path


def require(condition, message):
    if not condition:
        raise ValueError(message)


def calculate(document):
    days = document.get('days', [])
    require(isinstance(days, list) and bool(days), 'days must be a nonempty list')
    total = Decimal('0.0')
    rows, points = [], []
    incomplete = False
    for index, day in enumerate(days, 1):
        require(type(day.get('day')) is int and day['day'] == index, 'day must be sequential from 1')
        status = day.get('route_status')
        require(status in {'complete', 'partial', 'unavailable'}, f'D{index}: invalid status')
        missing = day.get('unmodelled', [])
        require(isinstance(missing, list) and all(isinstance(s, str) and s.strip() for s in missing), 'invalid unmodelled list')
        require((status == 'complete' and not missing) or (status != 'complete' and bool(missing)), 'status/exclusions mismatch')
        segments = day.get('segments')
        require(isinstance(segments, list), 'segments must be a list')
        require((status == 'unavailable' and not segments) or (status != 'unavailable' and bool(segments)), 'status/segments mismatch')
        endpoint_modelled = day.get('endpoint_modelled', status != 'unavailable')
        require(type(endpoint_modelled) is bool, 'endpoint_modelled must be boolean')
        require(status != 'complete' or endpoint_modelled, 'complete route must have modelled endpoint')
        require(status != 'unavailable' or not endpoint_modelled, 'unavailable route cannot have modelled endpoint')
        meters = Decimal('0')
        for segment in segments:
            distance = Decimal(str(segment['distance_m']))
            require(distance.is_finite() and distance >= 0, 'distance must be finite and nonnegative')
            geometry = segment['geometry']
            require(geometry.get('type') == 'LineString', 'geometry must be LineString')
            coords = geometry.get('coordinates', [])
            require(isinstance(coords, list) and len(coords) >= 2, 'LineString requires two or more coordinates')
            for coord in coords:
                require(isinstance(coord, (list, tuple)) and len(coord) == 2, 'use lon/lat pairs')
                require(all(type(v) in (int, float) and math.isfinite(v) for v in coord), 'invalid coordinate')
                require(-180 <= coord[0] <= 180 and -90 <= coord[1] <= 90, 'coordinate out of range')
            meters += distance
        incomplete |= status != 'complete'
        km = (meters / 1000).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)
        total += km
        rows.append({'day': index, 'date': day.get('date'), 'route_status': status,
                     'daily_km': str(km) if segments else None, 'cumulative_modelled_km': str(total),
                     'unmodelled': missing})
        if index == 1 and segments:
            points.append(feature(0, Decimal('0.0'), segments[0]['geometry']['coordinates'][0]))
        if segments and endpoint_modelled:
            points.append(feature(index, total, segments[-1]['geometry']['coordinates'][-1]))
    scope = 'modelled_roads_only' if incomplete else 'complete_modelled_itinerary'
    for point in points:
        point['properties']['scope'] = scope
    return ({'unit': 'km', 'scope': scope, 'total_km': str(total),
             'rounding': 'sum segments per day, round daily half-up to 0.1 km, then accumulate displayed daily values',
             'days': rows}, {'type': 'FeatureCollection', 'features': points})


def feature(day, distance, coords):
    return {'type': 'Feature', 'properties': {'day': day, 'cumulative_km': float(distance), 'unit': 'km'},
            'geometry': {'type': 'Point', 'coordinates': coords}}


def self_test():
    def segment(meters, coords):
        return {'distance_m': meters, 'geometry': {'type': 'LineString', 'coordinates': coords}}
    document = {'days': [
        {'day': 1, 'route_status': 'complete', 'segments': [segment(1050, [[100,30],[101,31]])]},
        {'day': 2, 'route_status': 'partial', 'unmodelled': ['unverified access'],
         'segments': [segment(1050, [[101,31],[100,30]])]},
        {'day': 3, 'route_status': 'unavailable', 'unmodelled': ['no route'], 'segments': []}]}
    metrics, markers = calculate(document)
    assert metrics['total_km'] == '2.2'
    assert metrics['scope'] == 'modelled_roads_only'
    assert metrics['days'][2]['daily_km'] is None
    assert len(markers['features']) == 3
    assert markers['features'][-1]['geometry']['coordinates'] == [100,30]
    document['days'][1]['endpoint_modelled'] = False
    assert len(calculate(document)[1]['features']) == 2
    for mutation in ('negative', 'coordinate', 'day', 'status'):
        bad = json.loads(json.dumps(document))
        if mutation == 'negative':
            bad['days'][0]['segments'][0]['distance_m'] = -1
        elif mutation == 'coordinate':
            bad['days'][0]['segments'][0]['geometry']['coordinates'][0] = [200,30]
        elif mutation == 'day':
            bad['days'][0]['day'] = 9
        else:
            bad['days'][2]['route_status'] = 'complete'
        try:
            calculate(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f'accepted {mutation}')
    print('PASS: rounding, cumulative, round-trip endpoints, missing route, invalid inputs')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', nargs='?', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if not args.input or not args.out:
        parser.error('input and --out are required')
    metrics, markers = calculate(json.loads(args.input.read_text(encoding='utf-8-sig')))
    args.out.mkdir(parents=True, exist_ok=True)
    for name, content in [('mileage.json', metrics), ('route-mileposts.geojson', markers)]:
        (args.out / name).write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"{metrics['total_km']} km ({metrics['scope']})")


if __name__ == '__main__':
    main()
