# tracevault/backend/workers/orchestrator_worker.py

import json
import os
import sys
from typing import Dict, Any, List

# --- Project Imports ---
# Import the logger utility
from logs.logger import get_logger

# Import the core analysis services/workers
from workers.metadata_worker import process_media as metadata_processor
from workers.video_worker import process_video as video_processor
from services.face_service import process_face_embedding as face_processor
from services.scene_service import process_scene_analysis as scene_processor

# Import the database models and session tool
from database.models import init_db, Evidence, MetadataReport, Frame, AnalysisStatus, MediaType, FaceEmbedding, SceneAnalysis
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

# --- Setup ---
logger = get_logger(__name__)

# NOTE: The database URL must be passed to this worker via the environment
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    logger.critical("DATABASE_URL environment variable is not set!")
    sys.exit(1)

# Initialize DB connection tools globally (lazily)
SessionLocal, engine = init_db(DATABASE_URL)


# --- ORCHESTRATION LOGIC ---

def process_single_image_frame(
    db: Session, 
    evidence_id: str, 
    image_path: str,
    is_main_evidence: bool = False
):
    """
    Handles the common analysis steps for a single image or video frame:
    1. Face Embedding
    2. Scene Analysis
    3. Persistence to DB
    """
    
    # 1. Prepare Frame/Evidence Object in DB
    if is_main_evidence:
        # For a single image evidence, we treat it as its own "frame" record
        frame_record = Frame(
            evidence_id=evidence_id,
            frame_storage_path=image_path,
            timestamp_sec=0.0
        )
        db.add(frame_record)
        db.flush() # Flushes the object to get the ID
    else:
        # Find the frame record created by the video worker
        frame_record = db.query(Frame).filter(Frame.frame_storage_path == image_path).first()
        if not frame_record:
            logger.error(f"Frame record not found for path: {image_path}. Skipping analysis.")
            return

    logger.info(f"Processing frame/image: {image_path}")

    # --- Step 1: Face Analysis ---
    face_result_str = face_processor(image_path)
    face_result = json.loads(face_result_str)

    for face_data in face_result.get("faces", []):
        db_face = FaceEmbedding(
            frame_id=frame_record.id,
            embedding_vector=face_data.get("embedding"),
            bounding_box=face_data.get("box"),
            attributes=face_data.get("attributes")
        )
        db.add(db_face)
    
    logger.info(f"-> Face analysis complete: {len(face_result.get('faces', []))} faces recorded.")

    # --- Step 2: Scene Analysis ---
    scene_result_str = scene_processor(image_path)
    scene_result = json.loads(scene_result_str)
    
    if scene_result.get("scene_scores"):
        db_scene = SceneAnalysis(
            frame_id=frame_record.id,
            classification_scores=scene_result.get("scene_scores")
        )
        db.add(db_scene)
        logger.info(f"-> Scene analysis complete. Top score: {list(scene_result['scene_scores'].values())[0]}")
    else:
        logger.warning("-> Scene analysis returned no scores.")
    
    db.commit()


def orchestrate_analysis(evidence_id: str, original_path: str, media_type: MediaType):
    """
    The main orchestration function executed by the RQ worker.
    """
    logger.info(f"--- Starting orchestration for Evidence ID: {evidence_id} (Type: {media_type.value}) ---")
    
    # 1. Get a new DB session for this job
    db: Session = SessionLocal()
    
    try:
        evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
        if not evidence:
            logger.error(f"Evidence record not found for ID: {evidence_id}")
            return
            
        # --- PHASE 1: File-Level Extraction (Metadata & Video Frames) ---
        
        # 1.1 Metadata/OCR Extraction
        metadata_result_str = metadata_processor(original_path)
        metadata_result = json.loads(metadata_result_str)
        
        # Persist Metadata Report
        db_metadata = MetadataReport(
            evidence_id=evidence_id,
            extracted_metadata=metadata_result.get("results", {}).get("metadata"),
            ocr_text=metadata_result.get("results", {}).get("ocr_text")
        )
        db.add(db_metadata)
        db.commit()
        evidence.status = AnalysisStatus.METADATA_EXTRACTED
        logger.info("Metadata and OCR extraction persisted.")
        
        analysis_targets = [original_path]
        
        # 1.2 Video Frame Extraction (if necessary)
        if media_type == MediaType.VIDEO:
            video_result_str = video_processor(original_path)
            video_result = json.loads(video_result_str)
            
            extracted_frames = video_result.get("extracted_frames", [])
            logger.info(f"Video processor returned {len(extracted_frames)} frames.")
            
            # Persist Frame records first
            for frame_path in extracted_frames:
                # NOTE: For simplicity, timestamp_sec is omitted here. 
                # In production, the video worker should return the timestamp.
                db_frame = Frame(
                    evidence_id=evidence_id,
                    frame_storage_path=frame_path,
                    timestamp_sec=None # Could be calculated from filename (frame_0001.jpg)
                )
                db.add(db_frame)
                
            db.commit()
            evidence.status = AnalysisStatus.FRAMES_EXTRACTED
            logger.info("Video frame paths persisted to database.")

            # Update analysis targets to the extracted frames
            analysis_targets = extracted_frames

        
        # --- PHASE 2: Frame/Image Analysis (Face & Scene) ---
        
        for i, target_path in enumerate(analysis_targets):
            is_main = (i == 0 and media_type != MediaType.VIDEO)
            process_single_image_frame(db, evidence_id, target_path, is_main_evidence=is_main)
        
        
        # --- PHASE 3: Final Status Update ---
        evidence.status = AnalysisStatus.ANALYSIS_COMPLETE
        db.commit()
        logger.info(f"--- Orchestration SUCCESS for Evidence ID: {evidence_id} ---")

    except Exception as e:
        logger.error(f"Orchestration FAILED for Evidence ID: {evidence_id}. Error: {e}", exc_info=True)
        # Mark the evidence as failed
        evidence.status = AnalysisStatus.FAILED
        db.commit()
    finally:
        db.close()

# --- Test Block (Not functional without full environment setup) ---
if __name__ == '__main__':
    # This block is for conceptual testing only. In reality, it runs via RQ.
    print("Orchestrator worker logic defined. Ready for RQ dispatch.")
      
