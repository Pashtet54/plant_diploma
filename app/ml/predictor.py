import json
import numpy as np
from PIL import Image
import tensorflow as tf

MODEL_PATH = "model/plant_classifier.keras"
CLASS_NAMES_PATH = "model/class_names.json"
IMG_SIZE = (224, 224)



model = tf.keras.models.load_model(MODEL_PATH)

with open(CLASS_NAMES_PATH, "r", encoding="utf-8") as f:
    class_names = json.load(f)


def preprocess_image(image: Image.Image):
    image = image.convert("RGB")
    image = image.resize(IMG_SIZE)
    image_array = np.array(image, dtype=np.float32)
    image_array = np.expand_dims(image_array, axis=0)
    return image_array


def predict_plant(image):
    processed = preprocess_image(image)
    predictions = model.predict(processed, verbose=0)[0]

    
    sorted_indices = np.argsort(predictions)[::-1]

    top1_idx = int(sorted_indices[0])
    top2_idx = int(sorted_indices[1])

    top1_conf = float(predictions[top1_idx])
    top2_conf = float(predictions[top2_idx])

    
    CONFIDENCE_THRESHOLD = 0.65
    GAP_THRESHOLD = 0.20 

    #
    top_candidates = []
    for idx in sorted_indices[:3]:
        top_candidates.append({
            "display_name": class_names[int(idx)],
            "confidence": float(predictions[int(idx)])
        })

    
    is_low_confidence = top1_conf < CONFIDENCE_THRESHOLD
    is_ambiguous = (top1_conf - top2_conf) < GAP_THRESHOLD

    is_unknown = is_low_confidence or is_ambiguous

    
    print("TOP1:", class_names[top1_idx], top1_conf)
    print("TOP2:", class_names[top2_idx], top2_conf)
    print("GAP:", top1_conf - top2_conf)

    if is_unknown:
        return {
            "display_name": None,
            "confidence": top1_conf,
            "is_unknown": True,
            
            "top_candidates": top_candidates
        }

    return {
        "display_name": class_names[top1_idx],
        "confidence": top1_conf,
        "is_unknown": False,
        
        "top_candidates": top_candidates
    }