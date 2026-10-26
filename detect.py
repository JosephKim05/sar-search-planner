from ultralytics import YOLO

model = YOLO("yolov8n.pt")
results = model("images/test2.jpg", classes=[0], conf=0.15, imgsz=1280, iou=0.5)
print("People found:", len(results[0].boxes))
results[0].save("outputs/out.jpg")