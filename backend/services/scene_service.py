# tracevault/backend/services/scene_service.py

import logging
import json
import os
import sys
from typing import List, Dict, Optional
from PIL import Image

# Ensure the transformers and torch libraries are installed
try:
    from transformers import CLIPProcessor, CLIPModel
    import torch
except ImportError:
    print("CRITICAL: CLIP libraries not found. Please install: pip install transformers torch Pillow")
    sys.exit(1)

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [SCENE_SERVICE] - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# --- Configuration ---

# CLIP Model Name: A good balance of speed and accuracy
CLIP_MODEL_NAME = "openai/clip-vit-base-patch32"

# --- Scene Classification Categories (The 'prompts' for CLIP) ---
# These are the descriptive text categories we want to score the image against.
SCENE_CATEGORIES = [
    "A picture of an urban street or city center",
    "A picture of a commercial building or interior office",
    "A picture of a residential area or suburban home",
    "A picture of a forest, park, or natural outdoor environment",
    "A picture of a desert or arid landscape",
    "A picture of a transportation hub like an airport or train station",
    "A picture of a large public gathering or event venue",
    "A picture of a private, enclosed space or basement",
    "A picture of an industrial complex or warehouse",
]

# --- Model Initialization ---
# Load the model and processor once to save time in the worker lifecycle
try:
    logger.info(f"Loading CLIP model: {CLIP_MODEL_NAME}...")
    CLIP_MODEL = CLIPModel.from_pretrained(CLIP_MODEL_NAME)
    CLIP_PROCESSOR = CLIPProcessor.from_pretrained(CLIP_MODEL_NAME)
    logger.info("CLIP model loaded successfully.")
    
    # Pre-tokenize and encode the text categories for faster scoring
    TEXT_INPUT = CLIP_PROCESSOR(text=SCENE_CATEGORIES, return_tensors="pt", padding=True)
    with torch.no_grad():
        TEXT_FEATURES = CLIP_MODEL.get_text_features(**TEXT_INPUT)
        TEXT_FEATURES /= TEXT_FEATURES.norm(dim=-1, keepdim=True)

except Exception as e:
    logger.critical(f"Failed to load CLIP model or processor: {e}")
    CLIP_MODEL = None
    CLIP_PROCESSOR = None
    TEXT_FEATURES = None

# --- Core Service: Scene Recognition ---
def classify_scene(image_path: str, top_k: int = 3) -> Optional[Dict[str, float]]:
    """
    Classifies the image against the predefined scene categories using CLIP.

    Args:
        image_path (str): The absolute path to the image file.
        top_k (int): The number of highest-scoring categories to return.

    Returns:
        Optional[Dict[str, float]]: A dictionary of the top K scenes and their confidence scores (0-1), 
                                     or None on critical failure.
    """
    if CLIP_MODEL is None or TEXT_FEATURES is None:
        logger.error("CLIP model not initialized. Cannot perform scene analysis.")
        return None
        
    if not os.path.exists(image_path):
        logger.error(f"Image not found for scene analysis: {image_path}")
        return {}

    logger.info(f"Starting scene classification on: {image_path}")
    
    try:
        image = Image.open(image_path).convert("RGB")
        
        # 1. Process the image
        image_input = CLIP_PROCESSOR(images=image, return_tensors="pt")
        
        # 2. Get image features
        with torch.no_grad():
            image_features = CLIP_MODEL.get_image_features(**image_input)
            image_features /= image_features.norm(dim=-1, keepdim=True)
            
            # 3. Calculate similarity (dot product of normalized features)
            # This yields the cosine similarity scores
            similarity = (image_features @ TEXT_FEATURES.T).squeeze(0)
            
            # 4. Convert to probabilities (softmax) to get confidence scores
            scores = torch.softmax(similarity, dim=0)

        # 5. Find the top K matches
        top_scores, top_indices = torch.topk(scores, top_k)
        
        results = {}
        for score, index in zip(top_scores.tolist(), top_indices.tolist()):
            # Use a clean category name for the key
            category_description = SCENE_CATEGORIES[index]
            category_name = category_description.split(" of a ")[1].split(" or ")[0].strip()
            
            # Store the result: Category Name -> Confidence Score
            results[category_name] = round(score, 4)
            
        logger.info(f"Successfully classified scene: Top match is '{list(results.keys())[0]}' with score {list(results.values())[0]}")
        return results

    except Exception as e:
        logger.error(f"An error occurred during scene classification: {e}")
        return None

# --- Main Worker Function (Wrapper) ---
def process_scene_analysis(image_path: str) -> str:
    """
    Worker wrapper for scene classification.

    Args:
        image_path (str): The absolute path to the image or extracted video frame.

    Returns:
        str: A JSON string containing the structured results.
    """
    
    results = classify_scene(image_path, top_k=3)
    
    if results is None:
        status = "error"
        message = "Critical failure during scene analysis."
    elif not results:
        status = "success"
        message = "Scene analysis produced no results."
    else:
        status = "success"
        message = "Scene analysis successful."

    final_report = {
        "status": status,
        "message": message,
        "file_path": image_path,
        "scene_scores": results if results is not None else {}
    }
    
    return json.dumps(final_report, indent=2)

# --- Test Block ---
if __name__ == "__main__":
    """
    Usage: python backend/services/scene_service.py /path/to/image_file.jpg
    NOTE: This test requires a large download on first run (CLIP model).
    """
    if len(sys.argv) != 2:
        print("Usage: python scene_service.py <path_to_image_file>")
        sys.exit(1)
        
    test_file = sys.argv[1]
    
    print(f"--- Running Scene Classification Test on {test_file} ---")
    results = process_scene_analysis(test_file)
    print("--- Results ---")
    print(results)
    print("--- Test Complete ---")

