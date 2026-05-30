#!/bin/bash
set -e

echo ""
echo "⚡  ReelForge — Starting up..."
echo "================================"

command -v python3 >/dev/null 2>&1 || { echo "❌  Python 3 required"; exit 1; }
command -v ffmpeg >/dev/null 2>&1 || { echo "❌  FFmpeg required: brew install ffmpeg"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "❌  Node.js required: https://nodejs.org"; exit 1; }

echo "✅  Dependencies OK"

cd backend

if [ ! -d "venv" ]; then
  $(brew --prefix python@3.12)/bin/python3.12 -m venv venv
fi

source venv/bin/activate
pip install -r requirements.txt -q

uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "   Backend → http://localhost:8000 (PID: $BACKEND_PID)"

cd ../frontend

if [ ! -d "node_modules" ]; then
  npm install -q
fi

echo ""
echo "================================"
echo "🚀  ReelForge is ready!"
echo "   Open → http://localhost:3000"
echo "   Ctrl+C to stop"
echo "================================"
echo ""

npm start

kill $BACKEND_PID 2>/dev/null
