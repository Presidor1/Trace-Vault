import subprocess
import json
import logging
import os
import sys
from PIL import Image, UnidentifiedImageError
import pytesseract

# --- Setup Logging ---
# This ensures that logs from this worker are clean and informative
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# --- Configuration ---
# You might need to set this if Tesseract isn't in your system's PATH
# Example for Windows: pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# Example for some Linux/macOS: Might not be needed if installed via apt/brew.

# --- Helper: Check if a file is likely an image ---
def is_image_file(file_path):
    """
    Checks if a file has a common image extension.
    This is a quick, simple check before attempting to open with PIL.
    """
    try:
        ext = os.path.splitext(file_path)[1].lower()
        return ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif']
    except Exception:
        return False

# --- Core Service 1: Metadata Extraction ---
def extract_metadata(file_path):
    """
    Uses the ExifTool binary to extract all metadata from any file.
    ExifTool is superior as it handles videos, docs, and images.
    
    Args:
        file_path (str): The absolute path to the media file.

    Returns:
        dict: A dictionary of all extracted metadata, or None if an error occurs.
    """
    logger.info(f"Extracting metadata from: {file_path}")
    try:
        # We use '-G' to get group names (e.g., "EXIF", "File") for better context
        # We use '-json' to get a machine-readable JSON output
        command = ['exiftool', '-json', '-G', file_path]
        
        # We run this as a subprocess
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,  # This will raise CalledProcessError if exiftool fails
            encoding='utf-8'
        )
        
        # ExifTool returns a list containing one JSON object
        metadata_list = json.loads(result.stdout)
        
        if not metadata_list:
            logger.warning(f"ExifTool returned no metadata for: {file_path}")
            return {}
            
        metadata = metadata_list[0]
        logger.info(f"Successfully extracted metadata for: {file_path}")
        return metadata

    except subprocess.CalledProcessError as e:
        logger.error(f"ExifTool failed for {file_path}. Return code: {e.returncode}")
        logger.error(f"ExifTool Error: {e.stderr}")
        return None
    except FileNotFoundError:
        logger.critical("ExifTool command not found. Is it installed and in your system's PATH?")
        return None
    except json.JSONDecodeError:
        logger.error(f"Failed to decode JSON output from ExifTool for: {file_path}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred during metadata extraction: {e}")
        return None

# --- Core Service 2: OCR (Text Extraction) ---
def extract_ocr(file_path):
    """
    Uses Tesseract OCR to extract any visible text from an image.
    
    Args:
        file_path (str): The absolute path to the image file.

    Returns:
        str: The extracted text, or None if an error or no text is found.
    """
    logger.info(f"Attempting OCR on: {file_path}")
    try:
        # Open the image file using Pillow
        with Image.open(file_path) as img:
            # Use pytesseract to extract text
            # We use 'lang='eng'' as a default, you can add more (e.g., 'eng+fra')
            text = pytesseract.image_to_string(img, lang='eng')
            
            if text.strip():
                logger.info(f"Successfully extracted OCR text from: {file_path}")
                return text.strip()
            else:
                logger.info(f"No OCR text found in: {file_path}")
                return ""

    except UnidentifiedImageError:
        logger.warning(f"Cannot perform OCR: File is not an image or is corrupted: {file_path}")
        return None
    except pytesseract.TesseractNotFoundError:
        logger.critical("Tesseract command not found. Is it installed and in your system's PATH?")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred during OCR: {e}")
        return None

# --- Main Worker Function ---
def process_media(file_path):
    """
    The main entry point for this worker.
    It orchestrates the extraction of metadata and OCR text.
    
    Args:
        file_path (str): The absolute path to the media file.

    Returns:
        str: A JSON string containing the structured results or an error message.
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return json.dumps({
            "status": "error",
            "message": "File not found at specified path.",
            "file_path": file_path
        })

    logger.info(f"Starting processing for job: {file_path}")
    
    # --- Step 1: Extract Metadata (Works on all files) ---
    metadata = extract_metadata(file_path)
    if metadata is None:
        # This is a critical failure, as ExifTool should work on any file
        return json.dumps({
            "status": "error",
            "message": "Critical failure during metadata extraction.",
            "file_path": file_path
        })

    # --- Step 2: Extract OCR (Only attempt on images) ---
    ocr_text = None
    if is_image_file(file_path):
        ocr_text = extract_ocr(file_path)
    else:
        logger.info(f"Skipping OCR: File is not an image: {file_path}")

    # --- Step 3: Compile Final Report ---
    final_report = {
        "status": "success",
        "file_path": file_path,
        "results": {
            "metadata": metadata,
            "ocr_text": ocr_text  # Will be None if not an image or if text extraction failed
        }
    }
    
    logger.info(f"Successfully completed processing for: {file_path}")
    
    # Return as a JSON string (as this is what a worker often passes back)
    return json.dumps(final_report, indent=2)

# --- Test Block ---
if __name__ == "__main__":
    """
    This allows you to test the worker script directly from the command line.
    
    Usage:
    python backend/workers/metadata_worker.py /path/to/your/test_image.jpg
    
    Find an image that has GPS data to see the full power.
    """
    if len(sys.argv) != 2:
        print("Usage: python metadata_worker.py <path_to_media_file>")
        sys.exit(1)
        
    test_file = sys.argv[1]
    
    print(f"--- Running Test on {test_file} ---")
    results = process_media(test_file)
    print("--- Results ---")
    print(results)
    print("--- Test Complete ---")
  
