# SAR Search Planner

Generates a lawnmower search route over a circular area and exports it as a GPX file for CalTopo or a drone ground station.

## What it does:
Given a center point, search radius, lane spacing, and drone speed, it outputs a zigzag route covering the circle. It also reports area, waypoint count, path length, and estimated flight time.

## Run:
```
python search_v2.py
```

Prompts:
- Search latitude / longitude (circle center)
- Search radius (m)
- Lane spacing (m): the distance between lanes, i.e. camera swath x (1 - overlap)
- Drone speed (m/s)

Output: 'search_route.gpx'. Import it into CalTopo

Example (radius 200m, spacing 20m): 42 waypoints, 12.6 ha, 6,835 m, ~11.4 min @ 10m/s.

## Screenshot
![Caltopo import](caltopo_circle.png)

## Why
Built while researching drone search and rescue with local responders. Planning a search pattern by hand is slow, so this makes it a few seconds. The next step is a person detector for aerial imagery.

## Limits 
- Flat-earth approx. (fine for areas under a few km)
- No wind, battery or terrain handling.

## Tool 2: Person detector

Finds people in drone images. Uses a YOLOv8s model trained on VisDrone, run with SAHI (sliced inference) so small people are not missed.

Run: `python detect_sahi.py`

**Limits:** tested on 2 images, with settings tuned on the second. Daylight RGB images only. Finds most people in the test images, but misses and false alarms are still possible, so a human must review every result.

## Results

Test image: drone photo of a hiker group (~5 people).

| Setup | Found | False alarms |
|---|---|---|
| YOLOv8n plain / 1280 | 0 | 0 |
| YOLOv8m + SAHI (160px) | 2 | not checked |
| VisDrone n + SAHI (128px, conf 0.3, crop) | 8 boxes | 4 |
| VisDrone s + SAHI (256px, conf 0.15) | 2 | 0 |
| VisDrone s + SAHI (256px, conf 0.15), test3 | 4 of 5 | 2 |
| VisDrone s + SAHI (192px, overlap 0.4, conf 0.2), test3 | 5 of 5 | 0 |

## Credits

- [VisDrone dataset](https://github.com/VisDrone/VisDrone-Dataset) for training data
- [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics) for the model and training code
- [SAHI](https://github.com/obss/sahi) for sliced inference
- Test images: Adobe Stock