"""Level 4: scale-aware person detection on drone photos + GPS map.

Core idea: tiles and model must match how big a person is in pixels.
  expected person size (px)  ->  model choice, tile size, box-size filter

Person size comes from one of:
  --scales scales.csv          per-image sizes (for test photos; columns: file,person_px)
  --person-px N                one size for every photo
  --alt M --focal MM --sensor-w MM   real flight: computed from altitude + camera

Outputs (in --out, default outputs/):
  flagged.csv   every photo: people found, model, tile, top conf, lat/lon
  flagged.gpx   waypoints for flagged photos with GPS (open in CalTopo)
  flagged/      annotated images of flagged photos

Examples:
  python detect_map.py images --scales scales.csv
  python detect_map.py flight1 --alt 60 --focal 8.8 --sensor-w 13.2
"""
import argparse
import csv
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image
from sahi import AutoDetectionModel
from sahi.predict import get_sliced_prediction

# ---- Settings (fixed; do not tune per image) ----
MODELS = {
    "visdrone": ("visdrone_yolov8s.pt", (0, 1)),  # trained on tiny aerial people
    "coco": ("yolov8s.pt", (0,)),                 # trained on normal-size people
}
SMALL_PX = 50        # people smaller than this -> VisDrone model, else COCO
PERSON_M = 1.0       # rough size of a person seen from above (m); calibrate in field test
TILE_MULT = 3        # tile ~ 3x person size, so a whole person fits in a tile
TILE_MIN, TILE_MAX = 128, 1024
OVERLAP, CONF = 0.4, 0.2
SIZE_MIN, SIZE_MAX = 0.3, 2.5  # keep boxes whose long side is 0.3x-2.5x expected size
EXTS = {".jpg", ".jpeg", ".png"}


def read_gps(path):
    """(lat, lon) from EXIF, or None."""
    try:
        g = Image.open(path).getexif().get_ifd(0x8825)
    except Exception:
        return None
    if not g or 2 not in g or 4 not in g:
        return None

    def to_deg(dms, ref):
        d, m, s = (float(x) for x in dms)
        v = d + m / 60 + s / 3600
        return -v if ref in ("S", "W") else v

    return to_deg(g[2], g.get(1, "N")), to_deg(g[4], g.get(3, "E"))


def person_px_from_alt(alt, focal, sensor_w, img_w):
    """Expected person size in pixels for a straight-down camera."""
    gsd = sensor_w * alt / (focal * img_w)  # metres per pixel
    return PERSON_M / gsd


_models = {}
def get_model(name):
    if name not in _models:
        path, _ = MODELS[name]
        _models[name] = AutoDetectionModel.from_pretrained(
            model_type="ultralytics", model_path=path,
            confidence_threshold=CONF, device="cpu",
        )
    return _models[name], MODELS[name][1]


ap = argparse.ArgumentParser()
ap.add_argument("path", nargs="?", default="images", help="image file or folder")
ap.add_argument("--scales", help="CSV with columns file,person_px")
ap.add_argument("--person-px", type=float)
ap.add_argument("--alt", type=float, help="altitude above ground, m")
ap.add_argument("--focal", type=float, help="real focal length, mm (not 35mm-equivalent)")
ap.add_argument("--sensor-w", type=float, help="sensor width, mm")
ap.add_argument("--model", choices=["auto", "visdrone", "coco"], default="auto")
ap.add_argument("--out", default="outputs")
args = ap.parse_args()

scales = {}
if args.scales:
    with open(args.scales, newline="") as f:
        scales = {r["file"].strip(): float(r["person_px"]) for r in csv.DictReader(f)}
use_alt = None not in (args.alt, args.focal, args.sensor_w)
if not (scales or args.person_px or use_alt):
    sys.exit("Need --scales, --person-px, or --alt with --focal and --sensor-w")

src = Path(args.path)
images = [src] if src.is_file() else sorted(p for p in src.iterdir() if p.suffix.lower() in EXTS)
out = Path(args.out)
flag_dir = out / "flagged"
flag_dir.mkdir(parents=True, exist_ok=True)

rows = []
for path in images:
    img_w, _ = Image.open(path).size
    if path.name in scales:
        px = scales[path.name]
    elif args.person_px:
        px = args.person_px
    elif use_alt:
        px = person_px_from_alt(args.alt, args.focal, args.sensor_w, img_w)
    else:
        print(f"{path.name}: skipped (no person size given)")
        continue

    name = args.model if args.model != "auto" else ("visdrone" if px < SMALL_PX else "coco")
    model, ids = get_model(name)
    tile = int(min(max(TILE_MULT * px, TILE_MIN), TILE_MAX))

    result = get_sliced_prediction(
        str(path), model,
        slice_height=tile, slice_width=tile,
        overlap_height_ratio=OVERLAP, overlap_width_ratio=OVERLAP,
        verbose=0,
    )

    keep = []
    for p in result.object_prediction_list:
        if p.category.id not in ids:
            continue
        b = p.bbox
        side = max(b.maxx - b.minx, b.maxy - b.miny)
        if SIZE_MIN * px <= side <= SIZE_MAX * px:  # drop fragments and wrong-size blobs
            keep.append(p)
    result.object_prediction_list = keep

    n = len(keep)
    top = max((p.score.value for p in keep), default=0.0)
    gps = read_gps(path)
    if n:
        result.export_visuals(export_dir=str(flag_dir), file_name=path.stem)

    rows.append({
        "file": path.name, "people": n, "model": name, "person_px": round(px),
        "tile": tile, "top_conf": round(top, 3),
        "lat": round(gps[0], 7) if gps else "", "lon": round(gps[1], 7) if gps else "",
    })
    print(f"{path.name}: {n} people | {name}, person {px:.0f}px, tile {tile} | "
          f"top {top:.2f} | GPS {'yes' if gps else 'NO'}")

if not rows:
    sys.exit("No images processed")

with open(out / "flagged.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader()
    w.writerows(rows)

wpts = [r for r in rows if r["people"] and r["lat"] != ""]
with open(out / "flagged.gpx", "w", encoding="utf-8") as f:
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<gpx version="1.1" creator="sar-search-planner" '
            'xmlns="http://www.topografix.com/GPX/1/1">\n')
    for r in wpts:
        f.write(f'  <wpt lat="{r["lat"]}" lon="{r["lon"]}"><name>{escape(r["file"])}</name>'
                f'<desc>{r["people"]} people, top conf {r["top_conf"]}</desc></wpt>\n')
    f.write("</gpx>\n")

flagged = sum(1 for r in rows if r["people"])
print(f"\n{len(rows)} photos, {flagged} flagged, {len(wpts)} mapped -> {out / 'flagged.gpx'}")
