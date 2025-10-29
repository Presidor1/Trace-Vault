# tracevault/Dockerfile

# --- STAGE 1: Build the Next.js Frontend ---
FROM node:20-alpine AS frontend_builder

WORKDIR /app/frontend

# Copy package files and install dependencies
COPY frontend/package*.json ./
RUN npm install

# Copy source code and build the application
COPY frontend/ ./
RUN npm run build

# --- STAGE 2: Build the Python Backend and Final Image ---
# Use a Python base image for the runtime environment
FROM python:3.10-slim-buster AS backend_runtime

# Set environment variables
ENV PYTHONUNBUFFERED 1
ENV FLASK_APP=backend/api/app.py
ENV UPLOAD_FOLDER /app/uploads
ENV PYTHONPATH "${PYTHONPATH}:/app/backend" # Add backend to path for module imports

WORKDIR /app

# Install system dependencies (e.g., for OpenCV, ExifTool)
# Add necessary system tools. ExifTool often requires its own installation.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libgl1-mesa-glx \
        libsm6 \
        libxext6 \
        libxrender1 \
        exiftool \
        ffmpeg \
        # Clean up
        && apt-get clean \
        && rm -rf /var/lib/apt/lists/*

# Copy backend dependencies and install Python packages
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all backend source code
COPY backend/ ./backend/
COPY logs/ ./logs/
COPY database/ ./database/
COPY osint/ ./osint/

# Create the uploads directory for temporary file storage
RUN mkdir -p /app/uploads

# Copy the built frontend static and server files from the build stage
COPY --from=frontend_builder /app/frontend/.next/standalone ./
COPY --from=frontend_builder /app/frontend/.next/static ./.next/static
COPY --from=frontend_builder /app/frontend/public ./public

# Final command to start the application
# We use a tool like 'gunicorn' or a custom script to run both Next.js and Flask/API,
# but for simplicity in deployment, we'll run the Flask API as the main web entry.
# The Next.js build output runs the next server.

# A more robust setup would use a start script (start.sh) to run gunicorn (API) and
# the Next.js standalone server simultaneously, perhaps managed by something like supervisord.
# For simplicity in this Dockerfile:

# 1. Install gunicorn (add to requirements.txt)
# 2. Use a start script.

COPY start.sh .
RUN chmod +x start.sh

# Expose the internal port (Render maps an external port to this)
EXPOSE 10000 

CMD ["./start.sh"]
