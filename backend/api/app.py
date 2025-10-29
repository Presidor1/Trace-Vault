# tracevault/backend/api/app.py

import os
import uuid
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Task Queue setup
import redis
from rq import Queue

# --- Project Imports ---
# NOTE: We need to import the function we want to enqueue
# The 'workers' directory must be visible to the Flask app
from workers.metadata_worker import process_media

# --- Load Environment Variables ---
# Assumes the .env file is one directory up (in backend/config)
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'config', '.env'))

# --- Flask App Initialization ---
app = Flask(__name__)

# Security: Allow frontend (React on Render) to talk to the backend
CORS(app) 
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER') or '/tmp/uploads'

# Ensure the upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- Redis & Task Queue Setup ---
try:
    # Connect to the Redis instance using the URL from .env
    redis_conn = redis.from_url(os.getenv('REDIS_URL'))
    
    # Create the RQ Queue instance. 'default' is the standard queue name.
    task_queue = Queue('default', connection=redis_conn)
    
    print("✅ Successfully connected to Redis/Upstash Task Queue.")
    
except Exception as e:
    print(f"❌ Failed to connect to Redis: {e}")
    # In a production app, you would log this and perhaps halt the app.
    task_queue = None
    redis_conn = None


# --- API Routes ---

@app.route('/api/upload', methods=['POST'])
def upload_evidence():
    """
    Handles file upload, saves the file, and dispatches a job to the queue.
    """
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part in the request"}), 400

    uploaded_file = request.files['file']

    if uploaded_file.filename == '':
        return jsonify({"status": "error", "message": "No file selected for uploading"}), 400

    if uploaded_file:
        # Create a unique, secure filename to prevent collisions and path traversal
        file_ext = os.path.splitext(uploaded_file.filename)[1]
        unique_filename = str(uuid.uuid4()) + file_ext
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        try:
            # 1. Save the file locally (This will be replaced by direct S3 upload later)
            uploaded_file.save(save_path)
            
            # 2. Dispatch the job to the Redis Queue
            if task_queue:
                # The 'process_media' function from metadata_worker.py is added to the queue
                job = task_queue.enqueue(
                    f=process_media, 
                    args=(save_path,),             # Arguments passed to the function
                    job_timeout='1h',              # Set a generous timeout for processing
                    result_ttl=86400               # Store the job result for 24 hours
                )

                # 3. Return the Job ID to the frontend for status polling
                return jsonify({
                    "status": "processing", 
                    "message": "File uploaded and analysis job dispatched.",
                    "job_id": job.id,
                    "filename": unique_filename
                }), 202 # 202 Accepted, job is pending

            else:
                return jsonify({"status": "error", "message": "Task queue service is unavailable."}), 503

        except Exception as e:
            app.logger.error(f"Error during file processing: {e}")
            return jsonify({"status": "error", "message": f"Server processing error: {e}"}), 500


@app.route('/api/status/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """
    Allows the frontend to poll for the status of a specific job.
    """
    if not task_queue:
        return jsonify({"status": "error", "message": "Task queue service is unavailable."}), 503

    try:
        job = task_queue.fetch_job(job_id)

        if job is None:
            return jsonify({"status": "error", "message": "Job not found."}), 404

        status = job.get_status()
        
        if status == 'finished':
            # The job is complete, return the result (which is a JSON string)
            return jsonify({
                "status": "complete",
                "result": json.loads(job.result), # Convert the JSON string from the worker back to a Python object
                "message": "Analysis complete."
            }), 200
        
        else:
            # Job is queued, started, deferred, etc.
            return jsonify({
                "status": status,
                "message": f"Job is currently {status}.",
            }), 202

    except Exception as e:
        return jsonify({"status": "error", "message": f"Could not retrieve job status: {e}"}), 500


# --- Server Start ---
if __name__ == '__main__':
    # When deployed on Render, the host will likely be 0.0.0.0
    app.run(debug=True, host='0.0.0.0', port=5000)

