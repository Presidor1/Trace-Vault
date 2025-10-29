# tracevault/backend/api/app.py (OVERWRITE)

import os
import uuid
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from dotenv import load_dotenv

# --- Project Imports ---
from logs.logger import get_logger
from database.models import init_db, Evidence, AnalysisStatus, MediaType
from workers.orchestrator_worker import orchestrate_analysis

# Task Queue setup
import redis
from rq import Queue
from sqlalchemy.orm import Session

# --- Setup ---
logger = get_logger(__name__)

# Load Environment Variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'config', '.env'))

# --- Flask App Initialization ---
app = Flask(__name__)
CORS(app) 
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER') or '/tmp/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- Global Connections ---
REDIS_URL = os.getenv('REDIS_URL')
DATABASE_URL = os.getenv('DATABASE_URL')

# Initialize DB and Redis/RQ outside of the main request loop
if not DATABASE_URL or not REDIS_URL:
    logger.critical("Missing DATABASE_URL or REDIS_URL in environment. Cannot start.")
    sys.exit(1)

try:
    SessionLocal, engine = init_db(DATABASE_URL)
    logger.info("✅ Database connected and models initialized.")
except Exception as e:
    logger.critical(f"❌ Failed to connect to Database: {e}")
    SessionLocal = None
    engine = None

try:
    redis_conn = redis.from_url(REDIS_URL)
    task_queue = Queue('default', connection=redis_conn)
    logger.info("✅ Redis Task Queue connected.")
except Exception as e:
    logger.critical(f"❌ Failed to connect to Redis: {e}")
    task_queue = None
    redis_conn = None


# --- Per-Request Database Session Management ---
@app.before_request
def before_request():
    """Opens a new database session before each request."""
    g.db = SessionLocal()

@app.teardown_request
def teardown_request(exception=None):
    """Closes the database session after each request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


# --- Utility: Determine Media Type ---
def get_media_type(filename: str) -> MediaType:
    ext = os.path.splitext(filename)[1].lower()
    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
        return MediaType.IMAGE
    elif ext in ['.mp4', '.mov', '.avi', '.wmv']:
        return MediaType.VIDEO
    elif ext in ['.pdf', '.doc', '.docx']:
        return MediaType.DOCUMENT
    return MediaType.OTHER


# --- API Routes ---

@app.route('/api/upload', methods=['POST'])
def upload_evidence():
    """
    Handles file upload, saves record to DB, and dispatches job to orchestrator.
    """
    if not g.db or not task_queue:
        return jsonify({"status": "error", "message": "Backend services unavailable."}), 503

    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part in the request"}), 400

    uploaded_file = request.files['file']
    if uploaded_file.filename == '':
        return jsonify({"status": "error", "message": "No file selected for uploading"}), 400

    if uploaded_file:
        file_ext = os.path.splitext(uploaded_file.filename)[1]
        unique_filename = str(uuid.uuid4()) + file_ext
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        media_type = get_media_type(uploaded_file.filename)
        
        try:
            # 1. Save the file locally to the temporary path
            uploaded_file.save(save_path)
            
            # 2. Create the initial Evidence record in the database
            new_evidence = Evidence(
                original_filename=uploaded_file.filename,
                storage_path=save_path, # In a real app, this is the S3 URL
                media_type=media_type,
                status=AnalysisStatus.PENDING
            )
            g.db.add(new_evidence)
            g.db.commit()
            evidence_id = new_evidence.id
            
            logger.info(f"Evidence {evidence_id} uploaded and saved to {save_path}.")

            # 3. Dispatch the job to the Orchestrator Worker
            job = task_queue.enqueue(
                f=orchestrate_analysis, 
                args=(evidence_id, save_path, media_type),
                job_timeout='2h', 
                result_ttl=86400
            )

            # 4. Return the Job ID and Evidence ID to the frontend
            return jsonify({
                "status": "queued", 
                "message": "File uploaded and analysis job dispatched.",
                "evidence_id": evidence_id,
                "job_id": job.id
            }), 202 

        except Exception as e:
            logger.error(f"Error during file upload/dispatch: {e}", exc_info=True)
            return jsonify({"status": "error", "message": f"Server processing error: {e}"}), 500


@app.route('/api/status/<evidence_id>', methods=['GET'])
def get_evidence_status(evidence_id):
    """
    Allows the frontend to check the status of the evidence and retrieve results.
    """
    if not g.db:
        return jsonify({"status": "error", "message": "Database service unavailable."}), 503

    try:
        # We don't need the RQ Job ID anymore, we track status via the DB record!
        evidence = g.db.query(Evidence).filter(Evidence.id == evidence_id).first()

        if evidence is None:
            return jsonify({"status": "error", "message": "Evidence ID not found."}), 404

        status = evidence.status.value
        response_data = {
            "status": status,
            "message": f"Evidence analysis status: {status}",
            "evidence_id": evidence.id,
            "media_type": evidence.media_type.value,
        }

        # If analysis is complete or failed, return the full report (simplified view)
        if status in [AnalysisStatus.ANALYSIS_COMPLETE.value, AnalysisStatus.FAILED.value]:
            
            if status == AnalysisStatus.ANALYSIS_COMPLETE.value:
                # Retrieve the basic report
                metadata = g.db.query(MetadataReport).filter(MetadataReport.evidence_id == evidence_id).first()
                frames = g.db.query(Frame).filter(Frame.evidence_id == evidence_id).all()
                
                report = {
                    "metadata": metadata.extracted_metadata if metadata else None,
                    "ocr_text": metadata.ocr_text if metadata else None,
                    "frames_analyzed": len(frames)
                    # For a real API, you would retrieve all linked Faces and Scenes here
                }
                response_data['report'] = report
            
            elif status == AnalysisStatus.FAILED.value:
                 response_data['message'] = "Analysis failed. Check backend logs for details."


        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Could not retrieve status for {evidence_id}: {e}", exc_info=True)
        return jsonify({"status": "error", "message": f"Server error retrieving status: {e}"}), 500


# --- Server Start ---
if __name__ == '__main__':
    # When deployed on Render, the host will likely be 0.0.0.0
    app.run(debug=True, host='0.0.0.0', port=5000)
        
