"""Level 4: run the SAHI person detector on a folder of drone photos,
read each photo's GPS from EXIF, and output:
  outputs/flagged.csv   - every photo: people found, top confidence, lat/lon
  outputs/flagged.gpx   - waypoints for flagged photos (open in CalTopo)
  outputs/flagged/      - annotated images of flagged photos

Usage:  python detect_map.py [image_folder]   (default: images)
"""
import csv
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image
from sahi import AutoDetectionModel
from sahi.predict import get_sliced_prediction

# Fixed settings (best so far; keep constant for fair tests)
MODEL_PATH = "visdrone_yolov8s.pt"
TILE, OVERLAP, CONF = 192, 0.4, 0.2
PERSON_IDS = (0, 1)  # VisDrone: pedestrian, people
EXTS = {".jpg", ".jpeg", ".png"}

IMG_DIR = Path(sys.argv[1] if len(sys.argv) > 1 else "images")
OUT = Path("outputs")
FLAG_DIR = OUT / "flagged"
FLAG_DIR.mkdir(parents=True, exist_ok=True)


def read_gps(path):
    """Return (lat, lon) from EXIF, or None if the photo has no GPS."""
    try:
        g = Image.open(path).getexif().get_ifd(0x8825)  # GPSInfo
    except Exception:
        return None
    if not g or 2 not in g or 4 not in g:
        return None

    def to_deg(dms, ref):
        d, m, s = (float(x) for x in dms)
        v = d + m / 60 + s / 3600
        return -v if ref in ("S", "W") else v

    return to_deg(g[2], g.get(1, "N")), to_deg(g[4], g.get(3, "E"))


model = AutoDetectionModel.from_pretrained(
    model_type="ultralytics",
    model_path=MODEL_PATH,
    confidence_threshold=CONF,
    device="cpu",
)

images = sorted(p for p in IMG_DIR.iterdir() if p.suffix.lower() in EXTS)
if not images:
    sys.exit(f"No images found in {IMG_DIR}")

rows = []
for path in images:
    result = get_sliced_prediction(
        str(path), model,
        slice_height=TILE, slice_width=TILE,
        overlap_height_ratio=OVERLAP, overlap_width_ratio=OVERLAP,
        verbose=0,
    )
    result.object_prediction_list = [
        p for p in result.object_prediction_list if p.category.id in PERSON_IDS
    ]
    n = len(result.object_prediction_list)
    top = max((p.score.value for p in result.object_prediction_list), default=0.0)
    gps = read_gps(path)

    if n:
        result.export_visuals(export_dir=str(FLAG_DIR), file_name=path.stem)

    rows.append({
        "file": path.name,
        "people": n,
        "top_conf": round(top, 3),
        "lat": round(gps[0], 7) if gps else "",
        "lon": round(gps[1], 7) if gps else "",
    })
    print(f"{path.name}: {n} people, top {top:.2f}, GPS {'yes' if gps else 'NO'}")

# CSV of all photos
with open(OUT / "flagged.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader()
    w.writerows(rows)

# GPX waypoints for flagged photos that have GPS
wpts = [r for r in rows if r["people"] and r["lat"] != ""]
with open(OUT / "flagged.gpx", "w", encoding="utf-8") as f:
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<gpx version="1.1" creator="sar-search-planner" '
            'xmlns="http://www.topografix.com/GPX/1/1">\n')
    for r in wpts:
        f.write(f'  <wpt lat="{r["lat"]}" lon="{r["lon"]}">'
                f'<name>{escape(r["file"])}</name>'
                f'<desc>{r["people"]} people, top conf {r["top_conf"]}</desc>'
                f'</wpt>\n')
    f.write('</gpx>\n')

flagged = sum(1 for r in rows if r["people"])
print(f"\n{len(rows)} photos, {flagged} flagged, {len(wpts)} mapped -> outputs/flagged.gpx")
