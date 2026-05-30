# ReelForge - Complete Code Analysis

## 📋 Project Overview

**ReelForge** is a full-stack web application that converts long-form videos into short-form clips (YouTube Shorts) with AI-powered optimization. It supports three distinct workflows and delivers 4K output in vertical and horizontal formats.

### Key Features
- **Best Shorts Mode**: AI scene detection & engagement scoring
- **Equal Clips Mode**: Fixed-duration chunk splitting
- **YouTube Upload Mode**: Direct upload with Claude-powered SEO (title, description, tags)
- **4K Output**: 9:16 (2160×3840) vertical and 16:9 (3840×2160) horizontal
- **Multi-format Export**: Support for both formats in a single job

---

## 🏗️ Architecture Overview

### Tech Stack
| Component | Technology | Version |
|-----------|-----------|---------|
| **Backend** | FastAPI | 0.115.0 |
| **Server** | Uvicorn | 0.30.6 |
| **Frontend** | React | 18.3.1 |
| **Video Processing** | FFmpeg + yt-dlp | 2024.8.6 |
| **AI/SEO** | Claude API (Sonnet) | claude-sonnet-4-20250514 |
| **YouTube Upload** | Google YouTube Data API v3 | - |
| **Auth** | Google OAuth2 | - |

### Project Structure
```
reelforge/
├── backend/
│   ├── main.py              # FastAPI app + endpoints
│   ├── processor.py         # Video processing pipeline
│   ├── seo.py               # Claude API SEO generator
│   ├── youtube_uploader.py  # YouTube upload + OAuth
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.js           # React main component
│   │   └── App.css
│   └── package.json
├── uploads/                 # Temp storage for uploaded files
├── outputs/                 # Generated clips (job_id folders)
└── start.sh                 # Launch both servers
```

---

## 📡 Backend Architecture

### FastAPI Application (`main.py`)

#### **Database Structure (In-Memory)**
```python
jobs = {
    "uuid": {
        "status": "queued|processing|done|error",
        "progress": 0-100,
        "message": "Human-readable status",
        "shorts": [
            {
                "filename": "clip_001_vertical.mp4",
                "url": "/outputs/{job_id}/clip_001_vertical.mp4",
                "format": "vertical|horizontal",
                "duration": 45.2,
                "start": 120.5,
                "resolution": "2160x3840",
                "size_mb": 45.3,
                "uploaded_to_yt": false,
                "yt_url": null  # Set after YouTube upload
            }
        ]
    }
}
```

#### **API Endpoints**

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/process/youtube` | Start pipeline from YouTube URL |
| `POST` | `/api/process/upload` | Start pipeline from file upload |
| `GET` | `/api/status/{job_id}` | Poll job status |
| `POST` | `/api/seo` | Generate SEO metadata (Claude API) |
| `POST` | `/api/youtube/upload` | Upload clip to YouTube |

#### **Request/Response Models**

**YouTubeRequest**
```python
{
    "url": "https://youtube.com/watch?v=...",
    "format": "both",           # "vertical", "horizontal", "both"
    "max_shorts": 5,            # For best_shorts mode
    "mode": "best_shorts",      # "best_shorts" | "equal_clips"
    "clip_duration": 60         # Seconds (for equal_clips)
}
```

**UploadRequest** (FormData)
```
file: <binary>
format: "both"
max_shorts: 5
mode: "best_shorts"
clip_duration: 60
```

**StatusResponse**
```python
{
    "job_id": "uuid",
    "status": "queued|processing|done|error",
    "progress": 0-100,
    "message": "...",
    "shorts": [...]
}
```

**SEORequest**
```python
{
    "job_id": "uuid",
    "filename": "clip_001_vertical.mp4",
    "topic": "optional context"
}
```

**SEOResponse** (Claude-generated)
```json
{
    "title": "Engaging title under 100 chars",
    "description": "2-3 paragraph description with hooks and CTAs",
    "tags": ["tag1", "tag2", ...],
    "hashtags": ["#Shorts", "#relevant", ...]
}
```

---

### Video Processing Pipeline (`processor.py`)

#### **VideoProcessor Class**

**Initialization**
```python
processor = VideoProcessor(
    job_id="uuid",
    video_path="/path/to/video.mp4",  # OR None if downloading from YouTube
    yt_url="https://youtube.com/...",  # OR None if uploading file
    output_dir="../outputs",
    format="both",
    max_shorts=5,
    mode="best_shorts",
    clip_duration=60,
    jobs=jobs_dict  # Shared job tracker
)
```

#### **Execution Flow**

```
VideoProcessor.run()
├── If yt_url provided:
│   └── _download_youtube()
│       └── Uses yt_dlp to fetch video
│           ├── Format: bestvideo[mp4] + bestaudio[m4a]
│           └── Output: {job_id}/source.ext
│
├── _get_video_info() [ffprobe]
│   └── Extract: duration, bitrate, codecs
│
├── If mode == "equal_clips":
│   └── _run_equal_clips(duration)
│       ├── Calculate: total_clips = duration / clip_duration
│       └── For each clip:
│           ├── Create segment {start, end, duration}
│           └── _export_short(segment, index)
│
└── If mode == "best_shorts":
    ├── _detect_scenes(duration) [ffmpeg scene detection]
    │   ├── Use scenedetect filter (threshold=0.35)
    │   └── Return: [timestamps of scene changes]
    │
    ├── _rank_segments(segments, duration)
    │   ├── Score each segment by:
    │   │   ├── Duration (30-60s = +50, 20-90s = +30, else = +10)
    │   │   └── Position (avoid intro/outro)
    │   └── Return: Top N sorted by score, then by start time
    │
    └── For each top segment:
        └── _export_short(segment, index)
```

#### **Export Function** (`_export_short`)

For each segment, exports 1-2 files based on format:

**Vertical Format (9:16)**
- Resolution: 2160×3840
- Crop: Center 9:16 from source
- Codec: libx264 (slow preset, CRF=18)
- Audio: AAC 320k

**Horizontal Format (16:9)**
- Resolution: 3840×2160
- Scale: Maintain aspect, letter/pillar box
- Codec: libx264 (slow preset, CRF=18)
- Audio: AAC 320k

**FFmpeg Command Template**
```bash
ffmpeg -ss {start} -i {input} -t {duration} \
    -vf "{crop/scale filter}" \
    -c:v libx264 -preset slow -crf 18 \
    -c:a aac -b:a 320k \
    -movflags +faststart \
    {output}
```

#### **Performance Characteristics**

| Operation | Speed | Resource |
|-----------|-------|----------|
| Scene detection | ~1x video duration | CPU |
| Segment scoring | <1s | CPU |
| 60s → 4K export | ~3-5 min per clip | CPU/GPU |
| YouTube download | Network dependent | Bandwidth |

---

### AI SEO Generator (`seo.py`)

#### **Claude Integration**

**Model**: `claude-sonnet-4-20250514`
**Max Tokens**: 1000
**API Key**: Environment variable `ANTHROPIC_API_KEY`

#### **Prompt Strategy**

Input: Filename + optional topic context
Output: JSON with YouTube metadata

**Claude Request**
```python
message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1000,
    messages=[{"role": "user", "content": prompt}]
)
```

**JSON Parsing**
- Claude outputs raw JSON
- Response strips markdown fences: ` ```json ... ``` `
- `json.loads()` parses the result

#### **Output Structure**
```json
{
    "title": "Max 100 chars, keyword-rich, clickworthy",
    "description": "2-3 paragraphs with hooks, keywords, CTAs, hashtags",
    "tags": ["tag1", "tag2", ...],  // 10 tags (mix broad + niche)
    "hashtags": ["#Shorts", "#relevant", ...]
}
```

**Constraints**
- Title: <100 chars
- Tags: Exactly 10 (single words or short phrases)
- Always includes #Shorts hashtag

---

### YouTube Upload (`youtube_uploader.py`)

#### **OAuth2 Flow**

**Credentials Flow**
```
First time:
  ├── Check for {backend}/credentials.json
  │   └── (Downloaded from Google Cloud Console)
  ├── Launch browser: http://localhost:8080
  ├── User logs in + grants permission
  └── Save token.json for future use

Subsequent times:
  └── Reuse token.json (auto-refresh if expired)
```

**Required Credentials**
- File: `backend/credentials.json`
- From: Google Cloud Console → APIs & Services → Credentials
- Type: OAuth 2.0 Client ID (Desktop App)

**Scope**: `https://www.googleapis.com/auth/youtube.upload`

#### **Upload Process**

**Video Metadata**
```python
{
    "snippet": {
        "title": "title (max 100 chars)",
        "description": "description with hashtags",
        "tags": ["tag1", "tag2", ...],
        "categoryId": "22"  // People & Blogs
    },
    "status": {
        "privacyStatus": "private|unlisted|public",
        "selfDeclaredMadeForKids": False
    }
}
```

**Resumable Upload**
- File uploaded in chunks
- Auto-resume on network failure
- Waits until completion before returning

**Response**
```json
{
    "success": true,
    "video_id": "dQw4w9WgXcQ",
    "url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
    "shorts_url": "https://youtube.com/shorts/dQw4w9WgXcQ"
}
```

---

## 🎨 Frontend Architecture

### React Application (`App.js`)

#### **State Management**
```javascript
{
    step: "config|processing|results",     // UI step
    inputMode: "youtube|upload",           // Input source
    ytUrl: "",                             // YouTube URL
    file: null,                            // Uploaded file
    format: "vertical|horizontal|both",
    maxShorts: 5,
    clipDuration: 60,
    selectedMode: "best_shorts|equal_clips|youtube_upload",
    job: { status, progress, message, shorts },  // Current job
    jobId: "uuid",
    seoData: { filename: seo_object },     // Generated SEO
    seoLoading: { filename: boolean },
    uploadStatus: { filename: "uploading|done|error" },
    topic: "",                             // For SEO context
    privacy: "private|unlisted|public"
}
```

#### **UI Workflow**

```
1. CONFIG STEP
   ├── Choose mode (Best Shorts / Equal Clips / YouTube Upload)
   ├── Choose input (YouTube URL / File Upload)
   ├── Configure:
   │   ├── Format (vertical/horizontal/both)
   │   ├── Max shorts count
   │   └── Clip duration (for equal_clips)
   └── Submit

2. PROCESSING STEP
   ├── Poll job status every 1.5 seconds
   ├── Display progress bar
   ├── Show job message
   └── Wait for status: "done" or "error"

3. RESULTS STEP (if YouTube Upload mode)
   ├── Display generated clips
   ├── For each clip:
   │   ├── Generate SEO (Claude API)
   │   ├── Preview SEO metadata
   │   └── Upload to YouTube
   │       └── Set privacy level
   └── Show YouTube links
```

#### **API Integration**

**Processing Polling**
```javascript
// Every 1.5 seconds
GET /api/status/{job_id}
→ Update job state
→ If done/error: stop polling, show results
```

**SEO Generation** (on-demand, per-clip)
```javascript
POST /api/seo
{
    job_id: "uuid",
    filename: "clip_001_vertical.mp4",
    topic: "optional context"
}
```

**YouTube Upload** (per-clip)
```javascript
POST /api/youtube/upload
{
    job_id: "uuid",
    filename: "clip_001_vertical.mp4",
    title: "from SEO",
    description: "from SEO",
    tags: [],
    privacy: "private"
}
```

---

## 🐛 Known Issues & Error Analysis

### Current Error: YouTube Authentication

**Error Message**
```
yt_dlp.utils.ExtractorError: [youtube] GpQSUjNsNm0: Please sign in
```

**Root Cause**
- Some YouTube videos require authentication to view
- yt-dlp cannot bypass this without credentials
- Common reasons:
  - Age-restricted content
  - Private/unlisted videos
  - Geographic restrictions
  - Copyright claims

**Current Mitigation**
- Error propagates to frontend via job status
- User sees: `"error": "Error: ERROR: [youtube] ...: Please sign in"`
- No retry mechanism

**Potential Solutions**
1. Add YouTube credential support to yt-dlp config
2. Implement fallback/retry logic
3. Better user error messaging
4. Add metadata endpoint (for private vids)

---

## 📊 Data Flow Diagrams

### YouTube → Clips → Upload

```
Frontend                Backend              External
   │                       │                    │
   ├─ POST /process/youtube─┤                  │
   │                    ┌─┬─┘                  │
   │                    │ [Start VideoProcessor]
   │                    │  ├─ Download YouTube ┼─────→ YouTube
   │                    │  │  └─ _download_youtube()
   │                    │  │
   │                    │  ├─ Detect Scenes
   │                    │  │  └─ _detect_scenes() [ffmpeg]
   │                    │  │
   │                    │  ├─ Rank Segments
   │                    │  │  └─ _rank_segments()
   │                    │  │
   │                    │  └─ Export Clips
   │                    │     └─ _export_short() [ffmpeg]
   │                    │
   ├─ GET /status/{id} ─┤ (repeat every 1.5s)
   │ ◄─ {progress, shorts}
   │
   ├─ POST /seo ────────┤
   │ ◄─ {title, desc, tags} ◄─ Claude API
   │                        (via seo.py)
   │
   └─ POST /youtube/upload ─┤
     ◄─ {video_id, url}    ├─ Google YouTube API
                            └─→ youtube_uploader.py
```

### File Upload → Clips

```
Frontend                Backend              External
   │                       │
   ├─ POST /process/upload ┤
   │  (multipart/form-data)│
   │  ├─ file              │
   │  ├─ format            │
   │  └─ config            │
   │                    ┌──┴─────────────┐
   │                    │ Save to uploads/│
   │                    │ Start processor │
   │                    │                 │
   │                    ├─ _get_video_info() [ffprobe]
   │                    ├─ Detect/Rank Scenes
   │                    └─ Export Clips [ffmpeg]
   │
   ├─ GET /status/{id} ─┤ (repeat every 1.5s)
   │ ◄─ {progress}
   │
   ▼
```

---

## 🔐 Security Considerations

### Current State
| Aspect | Status | Risk |
|--------|--------|------|
| CORS | Open (`*`) | Medium (frontend-only) |
| Authentication | None | High |
| File Upload | No validation | Medium |
| API Keys | Env variables | Medium (exposed in docker) |
| OAuth Tokens | Filesystem (token.json) | Medium |
| Input Validation | Minimal | Low-Medium |

### Recommendations
1. **CORS**: Restrict to known domains
2. **Auth**: Add user authentication (JWT/session)
3. **File Upload**: Validate MIME types, max size
4. **API Keys**: Use secure vaults (AWS Secrets, HashiCorp)
5. **Token Storage**: Use secure storage (HTTPOnly cookies)

---

## 🚀 Performance Characteristics

### Bottlenecks

| Stage | Time | Resource |
|-------|------|----------|
| YouTube Download | 30s-5min | Network + Disk |
| Scene Detection | ~1x duration | CPU |
| Segment Ranking | <1s | CPU |
| 60s Clip Export | 3-5 min | CPU |
| SEO Generation | 2-5s | Network (Claude API) |
| YouTube Upload | 1-30 min | Network + Disk |

**Total Time**: 60-minute video → 5 clips: ~30-45 minutes

### Optimization Opportunities
1. **Parallel Export**: Process multiple clips simultaneously
2. **Video Caching**: Cache downloads for repeated URLs
3. **Compression**: Lower CRF (faster, lower quality)
4. **Hardware Acceleration**: GPU encoding (NVIDIA NVENC)
5. **Async Operations**: Better async/await patterns

---

## 📝 Code Quality Assessment

### Strengths
✅ Clean separation of concerns (processor, SEO, uploader)
✅ Async/await for non-blocking operations
✅ Comprehensive FFmpeg integration
✅ React state management (clear lifecycle)
✅ Error propagation to frontend

### Areas for Improvement
⚠️ No database persistence (in-memory jobs)
⚠️ Limited error handling (try/except too broad)
⚠️ No logging (hard to debug production issues)
⚠️ No input validation (lengths, types)
⚠️ No rate limiting
⚠️ No job cleanup (memory leak risk)
⚠️ Shell injection risk in subprocess calls

### Critical Issues
🔴 `subprocess.run()` with user-controlled paths (processor.py)
🔴 No cleanup of temp files in uploads/
🔴 No maximum request size limit
🔴 OAuth token stored plaintext (token.json)

---

## 🛠️ Deployment Checklist

- [ ] Set `ANTHROPIC_API_KEY` environment variable
- [ ] Download & place `credentials.json` in backend/
- [ ] Install FFmpeg system package
- [ ] Verify Python 3.12
- [ ] Install Python dependencies: `pip install -r requirements.txt`
- [ ] Install frontend dependencies: `npm install`
- [ ] Update CORS origins in main.py
- [ ] Set up error logging/monitoring
- [ ] Configure job cleanup/archival
- [ ] Load test with concurrent jobs
- [ ] Set up metrics/alerting

---

## 📚 Key File References

| File | Lines | Purpose |
|------|-------|---------|
| main.py | 161 | FastAPI routes + job orchestration |
| processor.py | 249 | Video pipeline + FFmpeg integration |
| seo.py | 48 | Claude API integration |
| youtube_uploader.py | 70 | YouTube API + OAuth |
| App.js | 500+ | React UI + API client |

---

## 🎯 Summary

**ReelForge** is a well-architected video processing application with clear separation between frontend (React), API (FastAPI), and specialized processors (video, AI, upload). The main strengths are its flexible processing modes and AI-powered metadata generation. Key areas for production readiness are error handling, persistence, security, and logging.

**Estimated Production Effort**: 40-60 hours for hardening, monitoring, and scaling.
