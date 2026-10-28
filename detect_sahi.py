from sahi import AutoDetectionModel
from sahi.predict import get_sliced_prediction

model = AutoDetectionModel.from_pretrained(
    model_type="ultralytics",
    model_path="visdrone_yolov8s.pt",
    confidence_threshold=0.2,
    device="cpu",
)

result = get_sliced_prediction(
    "images/test4.jpg",
    model,
    slice_height=640,
    slice_width=640,
    overlap_height_ratio=0.4,
    overlap_width_ratio=0.4,
)

result.object_prediction_list = [
    p for p in result.object_prediction_list if p.category.id in (0,1)
]

scores = sorted((p.score.value for p in result.object_prediction_list), reverse=True)
print(scores[:10])

print("People found:", len(result.object_prediction_list))
result.export_visuals(export_dir="outputs/", file_name="sahi_s_test4_192_020")