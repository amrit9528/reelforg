# ReelForge EC2 Deployment Guide

## Quick Setup (Production Ready)

### Prerequisites on EC2
```bash
# Ubuntu/Debian AMI
sudo apt update
sudo apt install -y python3.12 python3.12-venv ffmpeg git curl

# Verify installations
python3.12 --version
ffmpeg -version
```

### 1. Clone & Setup
```bash
cd /opt
git clone <your-repo-url> reelforge
cd reelforge/backend

# Create venv
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment Variables
Create `.env` in backend folder:
```bash
ANTHROPIC_API_KEY=sk-ant-xxxxx
ALLOWED_ORIGINS=http://your-domain.com,http://localhost:3000
```

### 3. YouTube Setup (Optional)
If you need YouTube uploads, place `credentials.json`:
```bash
cp credentials.json backend/credentials.json
```

### 4. Start Backend
```bash
# Option A: Direct (for testing)
uvicorn main:app --host 0.0.0.0 --port 8000

# Option B: Production with Gunicorn
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000

# Option C: With systemd service (recommended)
# See systemd service section below
```

### 5. (Optional) Deploy Frontend
```bash
cd ../frontend
npm install
npm run build
# Serve the build/ folder with nginx or a static server
```

---

## Systemd Service (Auto-start on reboot)

Create `/etc/systemd/system/reelforge.service`:
```ini
[Unit]
Description=ReelForge Backend
After=network.target

[Service]
Type=notify
User=ubuntu
WorkingDirectory=/opt/reelforge/backend
Environment="PATH=/opt/reelforge/backend/venv/bin"
ExecStart=/opt/reelforge/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl enable reelforge
sudo systemctl start reelforge
sudo systemctl status reelforge
```

---

## Nginx Reverse Proxy

Install nginx:
```bash
sudo apt install nginx
```

Create `/etc/nginx/sites-available/reelforge`:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 2G;
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
sudo nginx -t
sudo systemctl restart nginx
```

---

## API Endpoints (No Frontend Needed)

All API calls can be made with `curl` or any HTTP client:

### 1. Process YouTube Video
```bash
curl -X POST http://your-ec2-ip:8000/api/process/youtube \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://youtube.com/watch?v=...",
    "format": "both",
    "max_shorts": 5,
    "mode": "best_shorts",
    "clip_duration": 60
  }'
```

### 2. Process Video File URL
```bash
curl -X POST http://your-ec2-ip:8000/api/process/url \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/video.mp4",
    "format": "vertical",
    "max_shorts": 3,
    "mode": "best_shorts"
  }'
```

### 3. Upload Video File
```bash
curl -X POST http://your-ec2-ip:8000/api/process/upload \
  -F "file=@/path/to/video.mp4" \
  -F "format=both" \
  -F "max_shorts=5" \
  -F "mode=best_shorts"
```

### 4. Check Job Status
```bash
curl http://your-ec2-ip:8000/api/status/{job_id}
```

### 5. Generate SEO Metadata
```bash
curl -X POST http://your-ec2-ip:8000/api/seo \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "...",
    "filename": "clip_001_vertical.mp4",
    "topic": "Optional context"
  }'
```

### 6. Upload to YouTube
```bash
curl -X POST http://your-ec2-ip:8000/api/youtube/upload \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "...",
    "filename": "clip_001_vertical.mp4",
    "title": "Video Title",
    "description": "Description",
    "tags": ["tag1", "tag2"],
    "privacy": "private"
  }'
```

---

## Storage & Cleanup

### S3 Integration (Optional)
Store outputs directly to S3 instead of local disk:

```python
# In main.py, add:
import boto3
s3 = boto3.client('s3')

# Override OUTPUT_DIR to use S3
```

### Cleanup Old Jobs
```bash
# Delete outputs older than 7 days
find /opt/reelforge/outputs -type f -mtime +7 -delete
find /opt/reelforge/uploads -type f -mtime +7 -delete
```

Schedule with cron:
```bash
0 2 * * * find /opt/reelforge/outputs -type f -mtime +7 -delete
0 2 * * * find /opt/reelforge/uploads -type f -mtime +7 -delete
```

---

## Monitoring & Logs

### Check service status
```bash
sudo systemctl status reelforge
sudo journalctl -u reelforge -f
```

### Monitor disk usage
```bash
df -h /opt/reelforge
du -sh /opt/reelforge/*
```

### Monitor processes
```bash
ps aux | grep uvicorn
watch -n 1 'ps aux | grep uvicorn'
```

---

## Security Checklist

- [ ] Set `ALLOWED_ORIGINS` to your domain only
- [ ] Use HTTPS (enable with nginx + Let's Encrypt)
- [ ] Restrict SSH access (security groups)
- [ ] Use IAM roles for AWS services (if using S3)
- [ ] Rotate `ANTHROPIC_API_KEY` regularly
- [ ] Keep credentials.json private (not in git)
- [ ] Monitor API usage and rate limit if needed

---

## Troubleshooting

### "Permission denied" on uploads
```bash
sudo chown -R ubuntu:ubuntu /opt/reelforge
chmod -R 755 /opt/reelforge
```

### "Port 8000 already in use"
```bash
sudo lsof -i :8000
sudo kill -9 <PID>
```

### "FFmpeg not found"
```bash
which ffmpeg
apt install ffmpeg
```

### "ANTHROPIC_API_KEY not set"
```bash
export ANTHROPIC_API_KEY=sk-ant-xxxxx
# Or add to .env file
```

---

## Performance Tuning

### Increase Uvicorn Workers
```bash
gunicorn -w 8 -k uvicorn.workers.UvicornWorker main:app
```

### Increase Max File Upload
In nginx config:
```nginx
client_max_body_size 5G;  # For large videos
```

### Enable Gzip Compression
In nginx config:
```nginx
gzip on;
gzip_types application/json;
```

### Use Faster Video Encoding
In processor.py, change CRF:
```python
"-crf", "23",  # Faster (lower quality) instead of 18
```

---

## Cost Optimization on AWS

1. **EC2 Instance Type**: Use `c6i.xlarge` or `g4dn.xlarge` (GPU for faster encoding)
2. **EBS Volume**: 100-200GB SSD for videos, auto-delete old jobs
3. **S3 Storage**: Move outputs to S3 after processing (much cheaper)
4. **NAT Gateway**: If using, disable when not processing
5. **Spot Instances**: Use for non-critical batch jobs

---

## Next Steps

1. Deploy to EC2 ✅
2. Test API endpoints
3. Set up monitoring (CloudWatch, DataDog)
4. Enable HTTPS with Let's Encrypt
5. Add database for job persistence (PostgreSQL)
6. Set up CI/CD pipeline (GitHub Actions → CodeDeploy)
