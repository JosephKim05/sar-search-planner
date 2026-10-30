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

**Scale-aware:** the model and tile size must match how big a person is in pixels. That size comes from flight altitude and camera, or is given per image for tests. Tiles are cut so each person appears at the size the model was trained on, and boxes far too small or large for a person (0.3–2.5 × expected size) are dropped.

| Model (`--model`) | Trained on | Best for | Tile |
|---|---|---|---|
| `heridal` | HERIDAL: wilderness, straight down, 40–65 m | **Real SAR flights (camera pointed down)** | 14 × person size |
| `coco` | COCO: everyday photos | Tilted / oblique views | 3 × person size |
| `visdrone` | VisDrone: urban drone footage | Very small people (< 50 px) | 3 × person size |
| `auto` (default) | – | VisDrone if person < 50 px, else COCO | – |

```
# real flight, camera pointed down: size computed from altitude + camera
python detect_map.py flight_photos --model heridal --alt 60 --focal 8.8 --sensor-w 13.2
# test images: size per image from a CSV (file,person_px)
python detect_map.py images --scales scales.csv --model heridal --out outputs_heridal
```
Fixed settings: overlap 0.4, conf 0.2, person ≈ 1.0 m seen from above (to calibrate in a field test).

### `train_heridal.ipynb`
Colab notebook that fine-tunes YOLOv8s (COCO-pretrained) on HERIDAL. Full 4000 × 3000 images are cut into 640 px tiles so small people aren't shrunk away; 10% of empty tiles are kept so the model learns "no person." 40 epochs, ~2 h on a T4 GPU.

**HERIDAL held-out test set (scored on 640 px tiles):** precision **0.919**, recall **0.863**, mAP50 **0.926**.
Same cameras and terrain as training, so expect lower numbers on other images. Recall 0.863 means about 1 in 7 people is missed.

### `detect_sahi.py`
Single-image version for quick experiments.

---

## Results

### Fair test: 5 unseen Pexels images, settings fixed before running

Each box checked by eye. **found / people** (false alarms incl. duplicates).

| Image | View | People | COCO (auto) | VisDrone | HERIDAL |
|---|---|---|---|---|---|
| test5 trail pair | oblique | 2 | **2/2** (0) | 0/2 (0) | 0/2 (0) |
| test6 snow pair | oblique | 2 | 0/2 (1) | 0/2 (0) | 1/2 (3) |
| test7 grass | **top-down** | 4 | 3/4 (1, shadow) | 0/4 (0) | **4/4 (0)** |
| test8 snow line | **top-down** | 8 | 7/8 (0) | 8/8 (4, bushes) | **8/8** (3) |
| test9 desert + jeeps | oblique | ~10 | **10/10** (4) | 6/10 (1) | 6/10 (11, mostly jeeps) |
| **Top-down total** | | 12 | 10/12 (1) | 8/12 (4) | **12/12 (3)** |
| **Oblique total** | | 14 | **12/14 (5)** | 6/14 (1) | 7/14 (14) |
| **All** | | 26 | **22/26 = 85% (6)** | 14/26 = 54% (5) | 19/26 = 73% (17) |

**Conclusion:**
- **Top-down, the real SAR camera view: HERIDAL found all 12 people** (grass and snow) with 3 false alarms, better than COCO (10/12) and VisDrone (8/12).
- **Oblique views: COCO is best** (12/14). HERIDAL only saw straight-down training images and confuses vehicles and gear for people.
- Use HERIDAL for real flights with the camera pointed down, and COCO for tilted shots.
- **Small sample:** only 2 top-down images (12 people). A field test is needed before trusting these numbers.

### Development images (settings were adjusted on these, so not a fair test)

| Image | True | Old fixed (VisDrone, 192 px) | Scale-aware (auto) | HERIDAL |
|---|---|---|---|---|
| test (group, top-down, close) | 15 | 3 | 11 | 3 |
| test2 (tiny hikers, low-res) | 5 | 0 | 2 | 0 |
| test3 | 5 | 5 | 6 | 5 |
| test4 (oblique, large people) | 6 | 49 (mostly bushes) | 6 | 2 |

### Lessons
- **Tile size must match person size.** At 192 px tiles, large people were split into fragments, and bushes looked like tiny people (49 false alarms).
- **The model must match the viewpoint.** VisDrone found 0 of 6 large oblique hikers; COCO found 6 of 6. HERIDAL was best top-down but worst on oblique shots.
- **Check the test labels.** A first run used the wrong person size and true count for each fair-test image (file order mixed up), which made HERIDAL look like it failed on grass and snow. Every result is now checked box by box.
- **Tuning on one image overfits.** The best `test3` settings dropped `test2` from 2 found to 0.
- VisDrone model mAP50 = 0.38 over all 10 VisDrone classes (not people only); not comparable with the HERIDAL score.

---

## Limits
- Daylight RGB still images only (no thermal or video).
- Oblique views, vehicles, and very low-resolution images are weak spots for the HERIDAL model.
- Fair test is small (5 images, 26 people).
- A GPS pin marks where the **drone** was, not where the person is. That's close enough for a straight-down camera; less so for tilted shots.
- Person size for test images was estimated by hand.
- Model weights (`.pt`) are not included in the repo.

## Next steps
1. Field test: fly the planned route over volunteers with the camera pointed down, then count found vs. missed and calibrate person size vs. altitude.
2. Bigger test set: more top-down images, incl. forest, partly hidden, and lying-down people. Then fine-tune further on SARD (incl. its "Corr" set: fog, snow, blur) if needed.
3. Fly the route automatically with off-the-shelf waypoint software.

---

## Credits
- [HERIDAL dataset](https://zenodo.org/records/5662351): Božić-Štulić, Marušić & Gotovac, "Deep Learning Approach in Aerial Imagery for Supporting Land Search and Rescue Missions," *IJCV* 2019; VOC version by P. Pyrrö (Aalto University, AIR project)
- [VisDrone dataset](https://github.com/VisDrone/VisDrone-Dataset): training data
- [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics): models (COCO-pretrained `yolov8s.pt`) and training code
- [SAHI](https://github.com/obss/sahi): sliced inference
- Test images: Pexels (test5–test9) and Adobe Stock (test–test4). Adobe Stock images and their annotated outputs are not included in this repo for licensing reasons.
