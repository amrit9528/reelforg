#!/bin/bash

# ReelForge Production Start Script

set -e

# Load environment variables
if [ -f ".env" ]; then
    export $(cat .env | xargs)
fi

# Check dependencies
echo "Checking dependencies..."
command -v python3.12 >/dev/null 2>&1 || { echo "❌ Python 3.12 not found"; exit 1; }
command -v ffmpeg >/dev/null 2>&1 || { echo "❌ FFmpeg not found"; exit 1; }

# Setup backend
echo "🚀 Starting ReelForge Backend..."
cd backend

# Create/activate venv if needed
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3.12 -m venv venv
fi

source venv/bin/activate

# Install dependencies
if [ "$1" == "--fresh" ]; then
    echo "📥 Installing dependencies (fresh)..."
    pip install -r requirements-prod.txt
fi

# Start backend
WORKERS=${WORKERS:-4}
PORT=${PORT:-8000}
HOST=${HOST:-0.0.0.0}

echo "✅ Backend starting on $HOST:$PORT with $WORKERS workers"
echo "📡 API docs at http://$HOST:$PORT/docs"

gunicorn \
    -w $WORKERS \
    -k uvicorn.workers.UvicornWorker \
    main:app \
    --bind $HOST:$PORT \
    --timeout 300 \
    --access-logfile - \
    --error-logfile -
