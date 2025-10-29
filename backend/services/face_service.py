# tracevault/backend/services/face_service.py

import logging
import json
import os
import sys
from typing import List, Dict, Optional, Any

# Ensure deepface and its dependencies are installed
try:
    from deepface import DeepFace
except ImportError:
    print("CRITICAL: DeepFace library not found. Please install: pip install deepface")
    sys.exit(1)

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [FACE_SERVICE] - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# --- Configuration ---
# DeepFace models we'll rely on
EMBEDDING_MODEL = "Facenet"   # Reliable for generating embeddings
DETECTION_BACKEND = "retinaface" # State-of-the-art face detector
DISTANCE_METRIC = "cosine"    # Standard metric for comparing embeddings

# --- Core Service: Face Analysis ---
def get_face_analysis(image_path: str) -> Optional[List[Dict[str, Any]]]:
    """
    Detects faces in an image and extracts bounding boxes, embeddings, and basic attributes.

    Args:
        image_path (str): The absolute path to the image file.

    Returns:
        Optional[List[Dict[str, Any]]]: A list of dictionaries, one for each detected face,
                                         containing bounding box, embedding vector, and attributes.
                                         Returns None on critical failure.
    """
    if not os.path.exists(image_path):
        logger.error(f"Image not found for face analysis: {image_path}")
        return []

    logger.info(f"Starting face analysis on: {image_path}")
    
    try:
        # DeepFace.analyze is used for attributes (age, gender, emotion)
        # DeepFace.extract_faces is simpler but doesn't give embeddings directly
        # We use a combination of verify to force embedding and analyze for bounding box and attributes.
        
        # We perform analysis to get the full result structure
        results = DeepFace.analyze(
            img_path=image_path,
            actions=['age', 'gender', 'race', 'emotion'], # Basic attributes
            detector_backend=DETECTION_BACKEND,
            enforce_detection=False, # Don't raise an error if no face is found
            silent=True # Suppress console output from deepface
        )
        
        # Now, extract the embeddings for each detected face (DeepFace.analyze doesn't return embeddings by default)
        embeddings_results = DeepFace.represent(
            img_path=image_path,
            model_name=EMBEDDING_MODEL,
            detector_backend=DETECTION_BACKEND,
            enforce_detection=False,
            silent=True
        )

        final_data = []
        
        # We iterate over the analysis results and find the corresponding embedding
        # NOTE: This assumes the order of detected faces is consistent between analyze and represent.
        # This is generally true for the same detector backend.
        
        for i, analysis in enumerate(results):
            
            # Use the bounding box 'region' to link the result to an embedding
            x, y, w, h = analysis['region'].values()
            
            # Simple check to link analysis result to embedding result
            if i < len(embeddings_results):
                embedding = embeddings_results[i]['embedding']
            else:
                embedding = None # Should not happen if detector is consistent
            
            face_data = {
                "face_id": str(uuid.uuid4()), # Unique ID for this specific face instance
                "box": {"x": x, "y": y, "w": w, "h": h}, # Bounding box coordinates
                "embedding": embedding, # The critical numerical vector
                "attributes": {
                    "age": analysis.get('age'),
                    "gender": analysis.get('gender'),
                    "race": analysis.get('dominant_race'),
                    "emotion": analysis.get('dominant_emotion')
                }
            }
            final_data.append(face_data)

        logger.info(f"Successfully detected and processed {len(final_data)} faces in {image_path}.")
        return final_data

    except ValueError as e:
        if "Face could not be detected" in str(e):
             logger.warning(f"No faces detected in {image_path}.")
             return []
        logger.error(f"DeepFace ValueError: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred during face service: {e}")
        return None

# --- Main Worker Function (Wrapper) ---
def process_face_embedding(image_path: str) -> str:
    """
    Worker wrapper for face embedding generation.

    Args:
        image_path (str): The absolute path to the image or extracted video frame.

    Returns:
        str: A JSON string containing the structured results.
    """
    
    results = get_face_analysis(image_path)
    
    if results is None:
        status = "error"
        message = "Critical failure during face analysis."
    elif not results:
        status = "success"
        message = "No faces detected."
    else:
        status = "success"
        message = f"Detected and processed {len(results)} faces."

    final_report = {
        "status": status,
        "message": message,
        "file_path": image_path,
        "faces": results if results is not None else []
    }
    
    return json.dumps(final_report, indent=2)

# --- Test Block ---
if __name__ == "__main__":
    """
    Usage: python backend/services/face_service.py /path/to/image_with_faces.jpg
    """
    if len(sys.argv) != 2:
        print("Usage: python face_service.py <path_to_image_file>")
        sys.exit(1)
        
    test_file = sys.argv[1]
    
    print(f"--- Running Face Embedding Test on {test_file} ---")
    results = process_face_embedding(test_file)
    print("--- Results ---")
    print(results)
    print("--- Test Complete ---")

