from ultralytics import YOLO

model = YOLO("yolov8n.pt")
results = model("test.jpg", classes=[0], conf=0.15, imgsz=1280)
results[0].save("out.jpg")
print("People found:", len(results[0].boxes))
results[0].save("out_m1280.jpg")