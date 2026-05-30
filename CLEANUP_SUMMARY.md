# ReelForge Cleanup Summary

## What Was Cleaned Up for EC2 Production

### ✅ Removed (No longer needed on server)
- **Chrome Cookie Logic** - Servers don't have Chrome browsers
- **Frontend Drag-and-Drop UI** - Using API directly instead
- **React Status Polling** - Monitor with API calls instead
- **Static File Serving** - Nginx handles `/outputs/` now
- **Development Logging** - Simplified for production

### ✅ Added (Production-ready)
- **Docker Support** - `Dockerfile` + `docker-compose.yml`
- **Nginx Config** - Reverse proxy setup
- **Health Check Endpoint** - `/api/status/health` for load balancers
- **Production Requirements** - Lightweight `requirements-prod.txt`
- **Systemd Service** - Auto-start on reboot
- **Production Docs** - Complete deployment guide

### ✅ Code Changes
1. **processor.py** - Removed Chrome cookie extraction
2. **main.py** - Removed static file mounting, added CORS config
3. **requirements.txt** - Added `gunicorn` for production

---

## Deployment Options

### Option 1: Docker (Easiest) ⭐ Recommended
```bash
docker-compose up -d
curl http://localhost:8000/docs
```
**Pros**: Single command, portable, isolated  
**Time**: 5 minutes

### Option 2: Direct Install (Ubuntu/Debian)
```bash
bash start-prod.sh --fresh
```
**Pros**: Direct control, no Docker overhead  
**Time**: 10 minutes

### Option 3: Manual Setup (Full Control)
```bash
cd backend
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements-prod.txt
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000
```
**Pros**: Maximum customization  
**Time**: 15 minutes

---

## Quick Start on EC2

### 1. SSH into EC2
```bash
ssh -i key.pem ubuntu@your-ec2-ip
```

### 2. Clone repo
```bash
git clone <your-repo-url> ~/reelforge
cd ~/reelforge
```

### 3. Create .env
```bash
cat > .env << EOF
ANTHROPIC_API_KEY=sk-ant-xxxxx
ALLOWED_ORIGINS=http://your-ec2-ip:8000
EOF
```

### 4. Choose deployment method

**With Docker:**
```bash
docker-compose up -d
docker-compose logs -f
```

**Without Docker:**
```bash
bash start-prod.sh --fresh
```

### 5. Test API
```bash
curl http://localhost:8000/docs  # Swagger UI
curl http://localhost:8000/api/status/health  # Health check
```

---

## File Structure (Clean)

```
reelforge/
├── backend/
│   ├── main.py                 # FastAPI (cleaned)
│   ├── processor.py            # Video pipeline (cleaned)
│   ├── seo.py                  # Claude AI
│   ├── youtube_uploader.py     # YouTube upload
│   ├── requirements-prod.txt   # Minimal deps
│   └── .env                    # (You create this)
│
├── outputs/                    # Generated videos
├── uploads/                    # Temp uploads
│
├── Dockerfile                  # Production image
├── docker-compose.yml          # One-command deploy
├── nginx.conf                  # Reverse proxy
├── start-prod.sh              # Direct start script
│
├── PRODUCTION_SETUP.md        # API docs + examples
├── EC2_DEPLOYMENT.md          # Full deployment guide
└── README.md                  # Original docs
```

**NOT included** (removed for production):
- ❌ `frontend/` - Use API directly
- ❌ Chrome cookie extraction
- ❌ Development files
- ❌ Unnecessary UI code

---

## API Usage Examples

### 1. Health Check
```bash
curl http://your-ec2-ip:8000/api/status/health
```

### 2. Process YouTube Video
```bash
curl -X POST http://your-ec2-ip:8000/api/process/youtube \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://youtube.com/watch?v=...",
    "format": "vertical",
    "max_shorts": 3,
    "mode": "best_shorts"
  }'
```

### 3. Check Status
```bash
curl http://your-ec2-ip:8000/api/status/job-id-here
```

### 4. Generate SEO
```bash
curl -X POST http://your-ec2-ip:8000/api/seo \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "job-id",
    "filename": "clip_001_vertical.mp4"
  }'
```

Full docs available at: `http://your-ec2-ip:8000/docs`

---

## Cost Estimation

### EC2 Instance Types
| Instance | vCPU | RAM | Price/hr | Video Speed |
|----------|------|-----|----------|------------|
| t3.large | 2 | 8GB | $0.10 | 0.5x |
| c6i.xlarge | 4 | 8GB | $0.17 | 1x |
| c6i.2xlarge | 8 | 16GB | $0.34 | 2x |
| g4dn.xlarge | 4 + GPU | 16GB | $0.53 | 5x+ |

### Per-Video Processing Cost
- **t3.large** (slow): $0.10/hour × 2hrs = **$0.20/video**
- **c6i.xlarge** (normal): $0.17/hour × 1hr = **$0.17/video**
- **g4dn.xlarge** (GPU): $0.53/hour × 0.2hrs = **$0.11/video**

**Storage**: ~1GB per 5-minute video = **$0.02/month** (S3)

---

## Next Steps

1. ✅ Deploy to EC2 (see PRODUCTION_SETUP.md)
2. Set up HTTPS with Let's Encrypt
3. Monitor logs: `docker-compose logs -f api`
4. Enable auto-scaling (AWS)
5. Set up CI/CD pipeline
6. Add database for job persistence (optional)

---

## Key Files

| File | Purpose |
|------|---------|
| `PRODUCTION_SETUP.md` | Quick API reference + Docker setup |
| `EC2_DEPLOYMENT.md` | Complete deployment guide |
| `Dockerfile` | Production image definition |
| `docker-compose.yml` | One-command deploy |
| `start-prod.sh` | Direct Python startup |
| `requirements-prod.txt` | Minimal dependencies |

---

## Support & Troubleshooting

### Check logs
```bash
# Docker
docker-compose logs -f api

# Systemd
journalctl -u reelforge -f
```

### Restart service
```bash
# Docker
docker-compose restart api

# Systemd
sudo systemctl restart reelforge
```

### Check disk usage
```bash
du -sh outputs/ uploads/
df -h
```

### Clean old files
```bash
find outputs -mtime +7 -delete  # Delete files older than 7 days
```

---

**Ready to deploy?** Start with `PRODUCTION_SETUP.md`
