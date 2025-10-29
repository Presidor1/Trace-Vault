#!/bin/bash
# tracevault/start.sh

# This script runs both the Gunicorn server for the Flask API and the Next.js server
# in the background, allowing the container to serve both the API and the UI.

echo "Starting TraceVault Backend API (Gunicorn)..."

# Run the Flask API on port 5000 (internal port)
# Adjust workers based on your Render plan vCPUs
gunicorn --bind 0.0.0.0:5000 'backend.api.app:app' --workers 2 --timeout 120 &

API_PID=$!

echo "Starting TraceVault Frontend (Next.js Standalone)..."

# Run the Next.js Standalone server on port 3000 (internal port)
# The Next.js server handles the UI traffic. The API calls go to port 5000
# internally. Render's proxy should forward /api traffic to 5000.
node server.js &

FRONTEND_PID=$!

echo "Waiting for both services to start..."

# Wait for both background processes to complete (or fail)
wait $API_PID $FRONTEND_PID
