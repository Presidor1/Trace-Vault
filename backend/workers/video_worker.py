# tracevault/backend/workers/video_worker.py

import subprocess
import json
import logging
import os
import sys
import shutil
import uuid
from typing import List, Dict, Optional

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [VIDEO_WORKER] - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# --- Configuration ---
# Target frame rate: 1 frame every X seconds. 
# 0.25 means 1 frame every 4 seconds (1/4=0.25). 1 means 1 frame per second.
TARGET_FPS = 1.0 

# Directory for saving extracted frames (must exist and be writable)
# We will create a unique subfolder per job for clean-up
FRAME_OUTPUT_BASE_DIR = os.getenv('FRAME_OUTPUT_DIR') or '/tmp/frames'

# --- Core Service: Video Frame Extraction ---
def extract_frames(video_path: str, job_id: str) -> Optional[List[str]]:
    """
    Uses FFmpeg to extract frames from a video at a fixed rate (TARGET_FPS).

    Args:
        video_path (str): The absolute path to the video file.
        job_id (str): A unique identifier for the job (used for temporary folder name).

    Returns:
        Optional[List[str]]: A list of absolute paths to the extracted frames (JPGs), 
                              or None if extraction fails.
    """
    
    # 1. Create a temporary, unique output directory for the frames
    output_dir = os.path.join(FRAME_OUTPUT_BASE_DIR, job_id)
    os.makedirs(output_dir, exist_ok=True)
    
    # The output filename pattern: frame_0001.jpg, frame_0002.jpg, etc.
    output_pattern = os.path.join(output_dir, "frame_%04d.jpg")
    
    logger.info(f"Extracting frames for job {job_id} into: {output_dir}")
    
    # FFmpeg Command Construction:
    # -i {input}: specifies the input file
    # -r {fps}: sets the output frame rate (e.g., 1.0 for 1 frame per second)
    # -q:v 2: sets the video quality (2 is good/high quality JPEG)
    command = [
        'ffmpeg',
        '-i', video_path,
        '-r', str(TARGET_FPS),
        '-q:v', '2',
        output_pattern
    ]
    
    try:
        # Execute the FFmpeg command
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True, # Raise exception on non-zero exit code
            encoding='utf-8',
            timeout=300 # Set a timeout (5 minutes) for video processing
        )
        
        # Check output directory for results
        extracted_frames = [
            os.path.join(output_dir, f)
            for f in os.listdir(output_dir)
            if f.endswith('.jpg')
        ]
        
        if not extracted_frames:
            logger.warning(f"FFmpeg ran successfully but found no frames in {output_dir}. Video might be too short.")
            return []
            
        logger.info(f"Successfully extracted {len(extracted_frames)} frames.")
        return extracted_frames

    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg failed for job {job_id}. Error:\n{e.stderr}")
        return None
    except FileNotFoundError:
        logger.critical("FFmpeg command not found. Is it installed and in your Render PATH?")
        return None
    except subprocess.TimeoutExpired:
        logger.error(f"FFmpeg process timed out after 300 seconds for job {job_id}.")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred during frame extraction: {e}")
        return None


# --- Worker Cleanup and Main Function ---
def process_video(video_path: str) -> str:
    """
    The main entry point for the video processing worker.
    """
    # 1. Generate a job ID to manage temporary files
    job_id = str(uuid.uuid4())
    
    if not os.path.exists(video_path):
        logger.error(f"Video file not found: {video_path}")
        return json.dumps({
            "status": "error",
            "message": "Video file not found at specified path.",
            "file_path": video_path
        })
        
    try:
        # 2. Extract frames
        frame_paths = extract_frames(video_path, job_id)

        if frame_paths is None:
            # Extraction failed due to critical error (e.g., FFmpeg not found)
            status = "critical_error"
            message = "Video frame extraction failed. Check worker logs."
        elif not frame_paths:
            # Extraction succeeded but yielded no frames
            status = "success"
            message = "Video processed, but no frames could be extracted (video too short or invalid)."
        else:
            # Extraction successful
            status = "success"
            message = f"Successfully extracted {len(frame_paths)} key frames."
        
        # 3. Compile Final Report
        final_report = {
            "status": status,
            "message": message,
            "video_path": video_path,
            # IMPORTANT: These paths must be passed to the next workers!
            "extracted_frames": frame_paths 
        }
        
        logger.info(f"Completed video processing for job {job_id}.")
        
        # In a production environment, you would also delete the original video 
        # file (video_path) and the temporary frames directory here or in a separate cleanup job.
        
        return json.dumps(final_report, indent=2)

    finally:
        # 4. Cleanup temporary frame directory (CRITICAL for Render free tier!)
        output_dir = os.path.join(FRAME_OUTPUT_BASE_DIR, job_id)
        if os.path.exists(output_dir):
            try:
                shutil.rmtree(output_dir)
                logger.info(f"Cleaned up temporary directory: {output_dir}")
            except OSError as e:
                logger.error(f"Error during cleanup of {output_dir}: {e}")
        
# --- Test Block ---
if __name__ == "__main__":
    """
    Allows direct command line testing (requires a local FFmpeg installation).
    Usage: python backend/workers/video_worker.py /path/to/your/test_video.mp4
    """
    if len(sys.argv) != 2:
        print("Usage: python video_worker.py <path_to_video_file>")
        sys.exit(1)
        
    test_file = sys.argv[1]
    
    print(f"--- Running Test on {test_file} ---")
    
    # NOTE: You MUST set FRAME_OUTPUT_BASE_DIR manually for local testing
    # e.g., os.environ['FRAME_OUTPUT_DIR'] = './temp_frames'
    
    results = process_video(test_file)
    print("--- Results ---")
    print(results)
    print("--- Test Complete ---")

