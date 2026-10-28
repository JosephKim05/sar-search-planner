# SAR Drone Tools

Two tools for drone search and rescue (SAR): a **search planner** that generates a flight route, and a **person detector** that flags drone photos that may contain people, so responders can decide where to send a ground team.

> The detector **flags candidates to speed up human review**. It cannot declare an area clear, because it still misses people. A human must review every result.

---

## Tool 1: Search planner (`search_v2.py`)

Generates a lawnmower search route over a circular area and exports it as GPX for CalTopo or a drone ground station.

```
python search_v2.py
```

Prompts: center lat/lon, search radius (m), lane spacing (m) = camera swath × (1 − overlap), drone speed (m/s).
Output: `search_route.gpx`. Reports area, waypoint count, path length, and flight time.

Example (radius 200 m, spacing 20 m): 42 waypoints, 12.6 ha, 6,835 m, ~11.4 min @ 10 m/s.

![CalTopo import](caltopo_circle.png)

**Limits:** flat-earth approximation (fine under a few km); no wind, battery, or terrain handling.

---

## Tool 2: Person detector

### `detect_map.py` (main)
Runs on a folder of drone photos, reads each photo's GPS, and outputs:
- `flagged.csv`: every photo, with people found, model used, tile size, top confidence, lat/lon
- `flagged.gpx`: a waypoint per flagged photo (drag into CalTopo)
- `flagged/`: annotated images

**Scale-aware:** the right model and tile size depend on how big a person is in pixels. That size comes from flight altitude and camera, or is given per image for tests:

| Person size | Model | Tile | Box filter |
|---|---|---|---|
| < 50 px | YOLOv8s trained on VisDrone (tiny aerial people) | 3 × person size (128–1024) | keep boxes 0.3–2.5 × person size |
| ≥ 50 px | YOLOv8s pretrained on COCO (normal-size people) | same | same |

```
# real flight: size computed from altitude + camera
python detect_map.py flight_photos --alt 60 --focal 8.8 --sensor-w 13.2
# test images: size per image from a CSV (file,person_px)
python detect_map.py images --scales scales.csv --out outputs_test
```
Fixed settings: overlap 0.4, conf 0.2, person ≈ 1.0 m seen from above (to calibrate in a field test).

### `detect_sahi.py`
Single-image version for quick experiments.

---

## Results

### Development images (settings were adjusted on these, so not a fair test)

| Image | True | Old fixed (VisDrone, 192 px tiles) | Scale-aware |
|---|---|---|---|
| test (group, top-down) | 15 | 3 | 11 |
| test2 (tiny hikers) | 5 | 0 | 2 |
| test3 | 5 | 5 | 6 |
| test4 (oblique, large people) | 6 | 49 (mostly bushes) | 6 |

### Fair test: 5 unseen Pexels images, settings fixed before running

| Image | Scene | True | Scale-aware (auto → COCO) | VisDrone forced |
|---|---|---|---|---|
| test5 | snow, oblique | 2 | 2 | 0 |
| test6 | grass, **top-down** | 4 | 7 (likely shadows) | 0 |
| test7 | snow line, **top-down** | 8 | 3 | 0 |
| test8 | desert + vehicles | ~10 | 9 | 12 |
| test9 | trail, oblique | 2 | 6 | 7 |

Numbers are box counts. Per-person found / false alarm / missed counts are still being verified.

**Conclusion:** scale-aware detection works well for oblique views. **Straight-down views, the actual SAR case, fail with both off-the-shelf models.** From above, a person is mostly head and shoulders, and long shadows look more human than the person does.

### Lessons
- **Tile size must match person size.** At 192 px tiles, large people were split into fragments, and bushes looked like tiny people (49 false alarms).
- **The model must match the viewpoint.** VisDrone found 0 of 6 large oblique hikers; COCO found 6 of 6.
- **Tuning on one image overfits.** The best `test3` settings dropped `test2` from 2 found to 0.
- VisDrone model mAP50 = 0.38, averaged over all 10 VisDrone classes (not people only). Normal for a small model on this dataset.

---

## Limits
- Daylight RGB still images only (no thermal or video).
- Top-down detection is unreliable (see results).
- A GPS pin marks where the **drone** was, not where the person is. That's close enough for a straight-down camera; less so for tilted shots.
- Person size for test images was estimated by hand.

## Next steps
1. Fine-tune on aerial SAR datasets (**HERIDAL**, **SARD**) for top-down people, then rerun the fair test unchanged.
2. Field test: fly the planned route over volunteers, then count found vs. missed and calibrate person size vs. altitude.
3. Fly the route automatically with off-the-shelf waypoint software.

---

## Credits
- [VisDrone dataset](https://github.com/VisDrone/VisDrone-Dataset): training data
- [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics): models (COCO-pretrained `yolov8s.pt`) and training code
- [SAHI](https://github.com/obss/sahi): sliced inference
- Test images: Pexels (test5–test9) and Adobe Stock (not included in repo)