from sahi import AutoDetectionModel
from sahi.predict import get_sliced_prediction

model = AutoDetectionModel.from_pretrained(
    model_type="ultralytics",
    model_path="visdrone_yolov8s.pt",
    confidence_threshold=0.15,
    device="cpu",
)

result = get_sliced_prediction(
    "images/test3.jpg",
    model,
    slice_height=256,
    slice_width=256,
    overlap_height_ratio=0.3,
    overlap_width_ratio=0.3,
)

result.object_prediction_list = [
    p for p in result.object_prediction_list if p.category.id in (0,1)
]

scores = sorted((p.score.value for p in result.object_prediction_list), reverse=True)
print(scores[:10])

print("People found:", len(result.object_prediction_list))
result.export_visuals(export_dir="outputs/", file_name="sahi_s_test3")