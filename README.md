# ⚡ ReelForge — 4K Video Clip Engine

Three powerful modes. Zero quality compromise.

---

## Three Modes

### 1. ✦ Best Shorts
AI detects the most engaging scenes from your video and exports the top N clips. Great for highlight reels, teasers, and viral content.

### 2. ⊞ Equal Clips
Splits the entire video into equal-length chunks. A 60-minute video with 60s duration = 60 clips. Perfect for batch content, course material, or episode archives.

### 3. ▲ YouTube Upload
Processes your video into shorts, then lets you generate AI-powered SEO (title, description, tags) per clip and upload directly to YouTube — all in one workflow.

---

## Prerequisites

### FFmpeg
```bash
brew install ffmpeg          # Mac
sudo apt install ffmpeg      # Ubuntu/Debian
```

### Python 3.12
```bash
brew install python@3.12
```

### Node.js 18+
Download from https://nodejs.org

---

## Run Locally

```bash
cd reelforge
bash start.sh
```

Open **http://localhost:3000**

Or manually:

**Terminal 1 — Backend:**
```bash
cd reelforge/backend
$(brew --prefix python@3.12)/bin/python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 — Frontend:**
```bash
cd reelforge/frontend
npm install
npm start
```

---

## YouTube Upload Setup

To use the YouTube Upload mode, you need a Google OAuth2 credentials file:

1. Go to https://console.cloud.google.com
2. Create a project → Enable **YouTube Data API v3**
3. Go to **APIs & Services → Credentials → Create OAuth 2.0 Client ID**
4. Application type: **Desktop App**
5. Download the JSON → rename it to `credentials.json`
6. Place it at: `reelforge/backend/credentials.json`

On first upload, a browser window will open asking you to log in to Google and authorize the app. After that, a `token.json` is saved and reused automatically.

---

## AI SEO Setup

ReelForge uses Claude AI to generate titles, descriptions, and tags.

Set your Anthropic API key:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Or add it to a `.env` file in the `backend/` folder:
```
ANTHROPIC_API_KEY=sk-ant-...
```

Get your API key at: https://console.anthropic.com

---

## Output Location

All clips are saved to:
```
reelforge/outputs/{job_id}/
```

Files are named:
- `clip_001_vertical.mp4` — 9:16, 2160×3840 (4K)
- `clip_001_horizontal.mp4` — 16:9, 3840×2160 (4K)

---

## Project Structure

```
reelforge/
├── backend/
│   ├── main.py              # FastAPI server
│   ├── processor.py         # Video pipeline (best_shorts + equal_clips)
│   ├── seo.py               # Claude AI SEO generator
│   ├── youtube_uploader.py  # YouTube Data API uploader
│   ├── requirements.txt
│   └── credentials.json     # (you add this for YouTube)
├── frontend/
│   ├── src/
│   │   ├── App.js           # Full React UI
│   │   └── App.css
│   └── package.json
├── uploads/
├── outputs/
└── start.sh
```
