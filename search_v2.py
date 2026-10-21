import math

START_LAT = float(input("Start latitude: "))
START_LON = float(input("Start longitude: "))
RADIUS_M = float(input("Search radius in meters: "))
LANE_SPACING_M = float(input("Lane spacing in meters: "))
SPEED_MPS = float(input("Drone speed (m/s): "))
OUTPUT_FILE = "search_route.gpx"

METERS_PER_DEG_LAT = 111_320

def make_lawnmower(radius, spacing):
    width = 2 * radius
    lanes = math.ceil(width / spacing) + 1
    points = []
    for i in range(lanes):
        east = min(i * spacing, width)
        dx = east - radius
        half = math.sqrt(max(0, radius**2 - dx**2))
        south = radius - half
        north = radius + half
        if i % 2 == 0:
            points.append((east, south))
            points.append((east, north))
        else:
            points.append((east, north))
            points.append((east, south))
    return points

def to_lat_lon(east_m, north_m, start_lat, start_lon):
    lat = start_lat + north_m / METERS_PER_DEG_LAT
    meters_per_deg_lon = METERS_PER_DEG_LAT * math.cos(math.radians(start_lat))
    lon = start_lon + east_m / meters_per_deg_lon
    return lat, lon

def path_length(points):
    total = 0
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        total += math.hypot(x2 - x1, y2 - y1)
    return total

def save_gpx(points, filename):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<gpx version="1.1" creator="search_pattern.py" '
             'xmlns="http://www.topografix.com/GPX/1/1">',
             ' <rte>',
             ' <name>Lawnmower search</name>']
    for east, north in points:
        lat, lon = to_lat_lon(east, north, START_LAT, START_LON)
        lines.append(f' <rtept lat="{lat:.6f}" lon="{lon:.6f}"/>')
    lines += [' </rte>', '</gpx>']
    with open(filename, "w") as f:
        f.write("\n".join(lines))

if __name__ == "__main__":
    route = make_lawnmower(RADIUS_M, LANE_SPACING_M)
    distance = path_length(route)
    minutes = distance / SPEED_MPS / 60
    area_hectares = math.pi * RADIUS_M**2 / 10_000

    save_gpx(route, OUTPUT_FILE)
    print(f"Area: {area_hectares:.1f} hectares")
    print(f"Waypoints: {len(route)}")
    print(f"Path length: {distance:.0f} m")
    print(f"Estimated flight time: {minutes:.1f} minutes")
    print(f"Saved route to {OUTPUT_FILE}")