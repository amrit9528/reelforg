# ReelForge Production Setup (API-Only)

This is a cleaned-up, production-ready version of ReelForge for EC2 deployment. **The React frontend has been removed** — interact with the API directly.

## What Was Removed

- ❌ React frontend (`frontend/` folder)
- ❌ Chrome cookie extraction (server won't have Chrome)
- ❌ Drag-and-drop UI code
- ❌ Status polling UI
- ❌ Static file serving
- ✅ Kept: Core API, video processing, AI SEO, YouTube upload

## Quick Start (Docker)

### Option 1: Docker Compose (Easiest)

```bash
# 1. Create .env file
cat > .env << EOF
ANTHROPIC_API_KEY=sk-ant-xxxxx
ALLOWED_ORIGINS=http://your-ec2-ip,http://your-domain.com
EOF

# 2. Start
docker-compose up -d

# 3. Check status
curl http://localhost:8000/docs

# 4. Stop
docker-compose down
```

### Option 2: Docker Build

```bash
docker build -t reelforge .
docker run -p 8000:8000 \
  -e ANTHROPIC_API_KEY=sk-ant-xxxxx \
  -v $(pwd)/outputs:/app/outputs \
  -v $(pwd)/uploads:/app/uploads \
  reelforge
```

### Option 3: Direct Install (Ubuntu/Debian)

```bash
# 1. Install dependencies
sudo apt update
sudo apt install -y python3.12 python3.12-venv ffmpeg

# 2. Setup
cd backend
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements-prod.txt

# 3. Create .env
cat > .env << EOF
ANTHROPIC_API_KEY=sk-ant-xxxxx
EOF

# 4. Start
bash ../start-prod.sh
```

---

## API Usage Examples

### 1. Process YouTube Video
```bash
curl -X POST http://localhost:8000/api/process/youtube \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
    "format": "both",
    "max_shorts": 5,
    "mode": "best_shorts"
  }'

# Response:
# {"job_id": "abc123-def456-ghi789"}
```

### 2. Process Video from URL
```bash
curl -X POST http://localhost:8000/api/process/url \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/video.mp4",
    "format": "vertical",
    "max_shorts": 3
  }'
```

### 3. Upload Local Video
```bash
curl -X POST http://localhost:8000/api/process/upload \
  -F "file=@/path/to/video.mp4" \
  -F "format=both" \
  -F "max_shorts=5"
```

### 4. Check Job Status
```bash
curl http://localhost:8000/api/status/abc123-def456-ghi789

# Response:
# {
#   "job_id": "abc123-def456-ghi789",
#   "status": "processing",
#   "progress": 45,
#   "message": "Exporting short 3/5...",
#   "shorts": [
#     {
#       "filename": "clip_001_vertical.mp4",
#       "url": "/outputs/abc123-def456-ghi789/clip_001_vertical.mp4",
#       "format": "vertical",
#       "duration": 45.2,
#       "resolution": "2160x3840",
#       "size_mb": 45.3
#     }
#   ]
# }
```

### 5. Generate SEO Metadata (Claude AI)
```bash
curl -X POST http://localhost:8000/api/seo \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "abc123-def456-ghi789",
    "filename": "clip_001_vertical.mp4",
    "topic": "Tutorial, AI, Tech"
  }'

# Response:
# {
#   "title": "Epic AI Tutorial You Need to Watch",
#   "description": "Learn how to use AI...",
#   "tags": ["AI", "Tutorial", ...],
#   "hashtags": ["#Shorts", "#AI", ...]
# }
```

### 6. Upload to YouTube
```bash
curl -X POST http://localhost:8000/api/youtube/upload \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "abc123-def456-ghi789",
    "filename": "clip_001_vertical.mp4",
    "title": "Epic AI Tutorial",
    "description": "Learn about AI in this short clip",
    "tags": ["AI", "Tutorial"],
    "privacy": "private"
  }'

# Response:
# {
#   "success": true,
#   "video_id": "dQw4w9WgXcQ",
#   "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
#   "shorts_url": "https://youtube.com/shorts/dQw4w9WgXcQ"
# }
```

---

## Environment Variables

| Variable | Required | Example | Notes |
|----------|----------|---------|-------|
| `ANTHROPIC_API_KEY` | Yes | `sk-ant-xxxxx` | Get from https://console.anthropic.com |
| `ALLOWED_ORIGINS` | No | `http://localhost:3000` | CORS origins (comma-separated) |
| `WORKERS` | No | `4` | Number of Uvicorn workers |
| `PORT` | No | `8000` | API port |
| `HOST` | No | `0.0.0.0` | Bind address |

---

## YouTube Setup (Optional)

If you want to upload to YouTube, place `credentials.json` in `backend/`:

1. Go to https://console.cloud.google.com
2. Create project → Enable YouTube Data API v3
3. Create OAuth 2.0 Client ID (Desktop App)
4. Download JSON → Save as `backend/credentials.json`

First upload will open browser for auth (use `localhost:8080`).

---

## Nginx Config (For EC2)

Place in `/etc/nginx/sites-available/reelforge`:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    client_max_body_size 2G;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /outputs/ {
        alias /opt/reelforge/outputs/;
        expires 1h;
    }
}
```

Enable:
```bash
sudo ln -s /etc/nginx/sites-available/reelforge /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

---

## Systemd Service (Auto-start)

Create `/etc/systemd/system/reelforge.service`:

```ini
[Unit]
Description=ReelForge API
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/reelforge
Environment="PATH=/opt/reelforge/backend/venv/bin"
ExecStart=/opt/reelforge/backend/venv/bin/gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl enable reelforge
sudo systemctl start reelforge
```

---

## Storage Cleanup

Auto-delete videos older than 7 days:

```bash
# Add to crontab
0 2 * * * find /opt/reelforge/outputs -type f -mtime +7 -delete
0 2 * * * find /opt/reelforge/uploads -type f -mtime +7 -delete
```

---

## Performance Tuning

### Increase Workers (for high load)
```bash
# Edit docker-compose.yml or systemd service
WORKERS=8  # Instead of 4
```

### Use GPU Encoding (c6i + NVIDIA)
```python
# In processor.py _export_short():
"-c:v", "h264_nvenc",  # Instead of libx264
```

### Lower Quality for Speed
```python
"-crf", "23",  # Instead of 18 (faster, lower quality)
```

---

## Monitoring

```bash
# View logs
docker-compose logs -f api

# Or with systemd
journalctl -u reelforge -f

# Check disk usage
du -sh outputs/ uploads/

# Monitor API
curl http://localhost:8000/docs
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "FFmpeg not found" | `apt install ffmpeg` |
| "Port 8000 in use" | `sudo lsof -i :8000` then kill |
| "ANTHROPIC_API_KEY not set" | Add to `.env` file |
| "Permission denied" | `sudo chown -R ubuntu:ubuntu /opt/reelforge` |
| "Disk full" | Run cleanup script: `find outputs -mtime +7 -delete` |

---

## Endpoints Summary

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/process/youtube` | Process YouTube video |
| `POST` | `/api/process/url` | Process video from direct URL |
| `POST` | `/api/process/upload` | Upload local video file |
| `GET` | `/api/status/{job_id}` | Check job progress |
| `POST` | `/api/seo` | Generate SEO metadata |
| `POST` | `/api/youtube/upload` | Upload to YouTube |
| `GET` | `/docs` | Interactive API docs (Swagger) |

---

## Next Steps

1. ✅ Deploy to EC2
2. Set up HTTPS with Let's Encrypt
3. Add database for job persistence
4. Set up monitoring (CloudWatch, Datadog)
5. Configure auto-scaling
6. Set up CI/CD (GitHub Actions → CodeDeploy)

---

**Need help?** Check the full guide: `EC2_DEPLOYMENT.md`
