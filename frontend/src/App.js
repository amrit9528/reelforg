import React, { useState, useRef, useCallback } from "react";
import axios from "axios";
import "./App.css";

const API = "http://localhost:8000";

const MODES = [
  {
    id: "best_shorts",
    icon: "✦",
    label: "Best Shorts",
    desc: "AI picks the most engaging moments from your video",
  },
  {
    id: "equal_clips",
    icon: "⊞",
    label: "Equal Clips",
    desc: "Split video into equal-length clips (e.g. 60 clips from a 60-min video)",
  },
  {
    id: "youtube_upload",
    icon: "▲",
    label: "YouTube Upload",
    desc: "Upload clips directly to YouTube with AI-generated SEO",
  },
];

export default function App() {
  const [step, setStep] = useState("config");
  const [inputMode, setInputMode] = useState("youtube");
  const [ytUrl, setYtUrl] = useState("");
  const [file, setFile] = useState(null);
  const [fileUrl, setFileUrl] = useState("");
  const [uploadSubMode, setUploadSubMode] = useState("file");
  const [format, setFormat] = useState("both");
  const [maxShorts, setMaxShorts] = useState(5);
  const [clipDuration, setClipDuration] = useState(60);
  const [selectedMode, setSelectedMode] = useState("best_shorts");
  const [dragging, setDragging] = useState(false);
  const [job, setJob] = useState(null);
  const [jobId, setJobId] = useState(null);
  const [seoData, setSeoData] = useState({});
  const [seoLoading, setSeoLoading] = useState({});
  const [uploadStatus, setUploadStatus] = useState({});
  const [topic, setTopic] = useState("");
  const [privacy, setPrivacy] = useState("private");
  const fileRef = useRef();
  const pollRef = useRef();

  const startPolling = (id) => {
    pollRef.current = setInterval(async () => {
      try {
        const res = await axios.get(`${API}/api/status/${id}`);
        setJob(res.data);
        if (res.data.status === "done" || res.data.status === "error") {
          clearInterval(pollRef.current);
          if (res.data.status === "done") {
            setStep("results");
          } else if (res.data.status === "error") {
            const msg = res.data.message || "Unknown error";
            if (msg.toLowerCase().includes("age-restricted") || msg.toLowerCase().includes("please sign in")) {
              alert(
                "❌ YouTube video requires authentication.\n\n" +
                "📤 Try uploading the video file directly instead.\n\n" +
                "Details: " + msg
              );
            } else {
              alert("Processing failed:\n" + msg);
            }
          }
        }
      } catch (e) {}
    }, 1500);
  };

  const handleProcess = async () => {
    setJob(null);
    setJobId(null);
    setSeoData({});
    setUploadStatus({});
    setStep("processing");

    // Determine actual backend mode
    // youtube_upload uses best_shorts pipeline + adds SEO/upload UI
    const backendMode = selectedMode === "youtube_upload" ? "best_shorts" : selectedMode;

    console.log("=== REELFORGE SUBMIT ===");
    console.log("selectedMode:", selectedMode);
    console.log("backendMode:", backendMode);
    console.log("clipDuration:", clipDuration);
    console.log("maxShorts:", maxShorts);
    console.log("format:", format);
    console.log("inputMode:", inputMode);

    try {
      let res;

      if (inputMode === "youtube") {
        const payload = {
          url: ytUrl,
          format: format,
          max_shorts: maxShorts,
          mode: backendMode,
          clip_duration: clipDuration,
        };
        console.log("YouTube payload:", payload);
        res = await axios.post(`${API}/api/process/youtube`, payload);
      } else if (uploadSubMode === "file") {
        const fd = new FormData();
        fd.append("file", file);
        fd.append("format", format);
        fd.append("max_shorts", String(maxShorts));
        fd.append("mode", backendMode);
        fd.append("clip_duration", String(clipDuration));

        console.log("FormData fields:");
        for (let [k, v] of fd.entries()) {
          console.log(" ", k, "=", v instanceof File ? `File(${v.name})` : v);
        }

        res = await axios.post(`${API}/api/process/upload`, fd);
      } else {
        // URL mode
        const payload = {
          url: fileUrl,
          format: format,
          max_shorts: maxShorts,
          mode: backendMode,
          clip_duration: clipDuration,
        };
        console.log("File URL payload:", payload);
        res = await axios.post(`${API}/api/process/url`, payload);
      }

      setJobId(res.data.job_id);
      setJob({ status: "queued", progress: 0, message: "Starting...", shorts: [] });
      startPolling(res.data.job_id);
    } catch (e) {
      setStep("config");
      const errorMsg = e.response?.data?.detail || e.message;

      if (errorMsg && errorMsg.toLowerCase().includes("age-restricted")) {
        alert(
          "❌ This YouTube video is age-restricted or requires sign-in.\n\n" +
          "📤 Solution: Switch to 'File Upload' mode and upload the video directly.\n\n" +
          "Details: " + errorMsg
        );
      } else {
        alert("Error: " + errorMsg);
      }
    }
  };

  const generateSEO = async (filename) => {
    setSeoLoading((p) => ({ ...p, [filename]: true }));
    try {
      const res = await axios.post(`${API}/api/seo`, { job_id: jobId, filename, topic });
      setSeoData((p) => ({ ...p, [filename]: res.data }));
    } catch (e) {
      alert("SEO generation failed: " + (e.response?.data?.detail || e.message));
    }
    setSeoLoading((p) => ({ ...p, [filename]: false }));
  };

  const uploadToYT = async (short) => {
    const seo = seoData[short.filename];
    if (!seo) { alert("Generate SEO first before uploading."); return; }
    setUploadStatus((p) => ({ ...p, [short.filename]: "uploading" }));
    try {
      const res = await axios.post(`${API}/api/youtube/upload`, {
        job_id: jobId,
        filename: short.filename,
        title: seo.title,
        description: seo.description,
        tags: seo.tags,
        privacy,
      });
      setUploadStatus((p) => ({ ...p, [short.filename]: "done" }));
      setSeoData((p) => ({
        ...p,
        [short.filename]: { ...p[short.filename], yt_url: res.data.url },
      }));
    } catch (e) {
      setUploadStatus((p) => ({ ...p, [short.filename]: "error" }));
      alert("Upload failed: " + (e.response?.data?.detail || e.message));
    }
  };

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f && f.type.startsWith("video/")) setFile(f);
  }, []);

  const reset = () => {
    clearInterval(pollRef.current);
    setJob(null);
    setJobId(null);
    setFile(null);
    setFileUrl("");
    setYtUrl("");
    setSeoData({});
    setUploadStatus({});
    setStep("config");
  };

  const canSubmit = inputMode === "youtube" ? !!ytUrl : (uploadSubMode === "file" ? !!file : !!fileUrl);

  return (
    <div className="app">
      <header className="header">
        <div className="logo">
          <span className="logo-mark">R</span>
          <div>
            <div className="logo-name">ReelForge</div>
            <div className="logo-sub">4K Video Clip Engine</div>
          </div>
        </div>
        <div className="header-badges">
          <span className="badge">4K Output</span>
          <span className="badge">AI SEO</span>
          <span className="badge">YouTube Ready</span>
        </div>
      </header>

      {step === "config" && (
        <div className="config-layout">
          <section className="section">
            <div className="section-label">01 — Choose Mode</div>
            <div className="mode-grid">
              {MODES.map((m) => (
                <button
                  key={m.id}
                  className={`mode-card ${selectedMode === m.id ? "active" : ""}`}
                  onClick={() => setSelectedMode(m.id)}
                >
                  <div className="mode-icon">{m.icon}</div>
                  <div className="mode-label">{m.label}</div>
                  <div className="mode-desc">{m.desc}</div>
                </button>
              ))}
            </div>
          </section>

          <section className="section">
            <div className="section-label">02 — Video Source</div>
            <div className="input-toggle">
              <button className={`itoggle-btn ${inputMode === "youtube" ? "active" : ""}`} onClick={() => setInputMode("youtube")}>▶ YouTube URL</button>
              <button className={`itoggle-btn ${inputMode === "upload" ? "active" : ""}`} onClick={() => setInputMode("upload")}>↑ Upload File</button>
            </div>

            {inputMode === "youtube" ? (
              <input
                className="url-input"
                type="url"
                placeholder="https://youtube.com/watch?v=..."
                value={ytUrl}
                onChange={(e) => setYtUrl(e.target.value)}
              />
            ) : (
              <>
                <div className="input-toggle">
                  <button className={`itoggle-btn ${uploadSubMode === "file" ? "active" : ""}`} onClick={() => { setUploadSubMode("file"); setFileUrl(""); }}>📁 Upload File</button>
                  <button className={`itoggle-btn ${uploadSubMode === "url" ? "active" : ""}`} onClick={() => { setUploadSubMode("url"); setFile(null); }}>🔗 Video URL</button>
                </div>

                {uploadSubMode === "file" ? (
                  <div
                    className={`dropzone ${dragging ? "drag-over" : ""} ${file ? "has-file" : ""}`}
                    onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
                    onDragLeave={() => setDragging(false)}
                    onDrop={onDrop}
                    onClick={() => fileRef.current.click()}
                  >
                    <input ref={fileRef} type="file" accept="video/*" style={{ display: "none" }} onChange={(e) => setFile(e.target.files[0])} />
                    {file ? (
                      <div className="file-chosen">
                        <span>🎬</span>
                        <div>
                          <div className="file-name">{file.name}</div>
                          <div className="file-size">{(file.size / 1024 / 1024).toFixed(1)} MB</div>
                        </div>
                      </div>
                    ) : (
                      <div className="drop-hint">
                        <div className="drop-arrow">↑</div>
                        <div>Drop video here or click to browse</div>
                        <div className="drop-sub">MP4, MOV, MKV — up to 4K, 1hr+</div>
                      </div>
                    )}
                  </div>
                ) : (
                  <input
                    className="url-input"
                    type="url"
                    placeholder="https://example.com/video.mp4 or https://example.com/video.mov"
                    value={fileUrl}
                    onChange={(e) => setFileUrl(e.target.value)}
                  />
                )}
              </>
            )}
          </section>

          <section className="section">
            <div className="section-label">03 — Settings</div>
            <div className="settings-grid">

              {selectedMode === "equal_clips" ? (
                <div className="setting-box">
                  <div className="setting-title">
                    Clip Duration — <strong>{clipDuration >= 60 ? `${Math.floor(clipDuration/60)}m ${clipDuration%60 > 0 ? clipDuration%60+"s" : ""}`.trim() : `${clipDuration}s`}</strong>
                  </div>
                  <input
                    type="range" min="15" max="300" step="15"
                    value={clipDuration}
                    onChange={(e) => setClipDuration(Number(e.target.value))}
                    className="slider"
                  />
                  <div className="slider-labels"><span>15s</span><span>1m</span><span>2m</span><span>5m</span></div>
                  <div className="clip-preview-info">
                    A 60-min video at {clipDuration}s = <strong>{Math.floor(3600 / clipDuration)} clips</strong>
                  </div>
                </div>
              ) : (
                <div className="setting-box">
                  <div className="setting-title">Max Shorts — <strong>{maxShorts}</strong></div>
                  <input type="range" min="1" max="15" value={maxShorts} onChange={(e) => setMaxShorts(Number(e.target.value))} className="slider" />
                  <div className="slider-labels"><span>1</span><span>5</span><span>10</span><span>15</span></div>
                </div>
              )}

              <div className="setting-box">
                <div className="setting-title">Output Format</div>
                <div className="pill-row">
                  {[["vertical", "9:16 Vertical"], ["horizontal", "16:9 Horizontal"], ["both", "Both"]].map(([v, l]) => (
                    <button key={v} className={`pill ${format === v ? "active" : ""}`} onClick={() => setFormat(v)}>{l}</button>
                  ))}
                </div>
              </div>

              {selectedMode === "youtube_upload" && (
                <>
                  <div className="setting-box">
                    <div className="setting-title">Video Topic (helps AI write better SEO)</div>
                    <input className="url-input" placeholder="e.g. fitness tips, cooking tutorial..." value={topic} onChange={(e) => setTopic(e.target.value)} />
                  </div>
                  <div className="setting-box">
                    <div className="setting-title">YouTube Privacy</div>
                    <div className="pill-row">
                      {[["private", "🔒 Private"], ["unlisted", "🔗 Unlisted"], ["public", "🌐 Public"]].map(([v, l]) => (
                        <button key={v} className={`pill ${privacy === v ? "active" : ""}`} onClick={() => setPrivacy(v)}>{l}</button>
                      ))}
                    </div>
                  </div>
                </>
              )}
            </div>
          </section>

          {/* Summary bar before submitting */}
          <div className="submit-summary">
            <span>Mode: <strong>{MODES.find(m => m.id === selectedMode)?.label}</strong></span>
            <span>·</span>
            {selectedMode === "equal_clips"
              ? <span>Clip size: <strong>{clipDuration}s</strong></span>
              : <span>Max clips: <strong>{maxShorts}</strong></span>
            }
            <span>·</span>
            <span>Format: <strong>{format}</strong></span>
          </div>

          <button className="btn-forge" onClick={handleProcess} disabled={!canSubmit}>
            ⚡ Forge Clips
          </button>
        </div>
      )}

      {step === "processing" && job && (
        <div className="processing-view">
          <div className="proc-card">
            <div className="proc-top">
              <div className="proc-spinner" />
              <div>
                <div className="proc-msg">{job.message}</div>
                <div className="proc-pct">{job.progress}%</div>
              </div>
            </div>
            <div className="prog-bar"><div className="prog-fill" style={{ width: `${job.progress}%` }} /></div>
            <div className="proc-steps">
              {["Download", "Analyze", "Detect", "Score", "Export"].map((s, i) => (
                <div key={s} className={`proc-step ${job.progress >= i * 20 + 5 ? "done" : ""}`}>
                  <div className="pdot" /><span>{s}</span>
                </div>
              ))}
            </div>
          </div>

          {job.shorts && job.shorts.length > 0 && (
            <div className="live-results">
              <div className="live-label">⚡ Clips ready so far — {job.shorts.length}</div>
              <div className="clips-grid">
                {job.shorts.map((s, i) => <ClipCard key={i} short={s} jobId={jobId} />)}
              </div>
            </div>
          )}
        </div>
      )}

      {step === "results" && job && (
        <div className="results-view">
          <div className="results-header">
            <div>
              <h2>{job.shorts.length} Clip{job.shorts.length !== 1 ? "s" : ""} Ready <span className="done-badge">✓</span></h2>
              <p className="results-sub">All exported in 4K · {format === "both" ? "Vertical + Horizontal" : format}</p>
            </div>
            <button className="btn-new" onClick={reset}>+ New Video</button>
          </div>

          {selectedMode === "youtube_upload" && (
            <div className="yt-panel">
              <div className="yt-panel-title">▲ YouTube Upload Mode</div>
              <p>Generate AI SEO for each clip, then upload directly to your YouTube channel.</p>
              <div className="yt-note">⚠ Requires <code>credentials.json</code> from Google Cloud Console — see README.</div>
            </div>
          )}

          <div className="clips-grid">
            {job.shorts.map((short, i) => (
              <ClipCard
                key={i}
                short={short}
                jobId={jobId}
                showYT={selectedMode === "youtube_upload"}
                seo={seoData[short.filename]}
                seoLoading={seoLoading[short.filename]}
                uploadStatus={uploadStatus[short.filename]}
                topic={topic}
                onGenerateSEO={() => generateSEO(short.filename)}
                onUpload={() => uploadToYT(short)}
                onSeoEdit={(field, val) =>
                  setSeoData((p) => ({ ...p, [short.filename]: { ...p[short.filename], [field]: val } }))
                }
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ClipCard({ short, jobId, showYT, seo, seoLoading, uploadStatus, onGenerateSEO, onUpload, onSeoEdit }) {
  const [expanded, setExpanded] = useState(false);
  const [downloading, setDownloading] = useState(false);

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const response = await fetch(`${API}${short.url}`);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.style.display = "none";
      a.href = url;
      a.download = short.filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (e) {
      alert("Download failed: " + e.message);
    }
    setDownloading(false);
  };

  return (
    <div className={`clip-card ${short.format}`}>
      <div className="clip-preview">
        <video src={`${API}${short.url}`} controls className="clip-video" />
        <div className="clip-fmt-badge">{short.format === "vertical" ? "9:16" : "16:9"}</div>
        <div className="clip-res-badge">4K</div>
      </div>

      <div className="clip-body">
        <div className="clip-meta">
          <span>⏱ {short.duration}s</span>
          <span>📍 {short.start}s</span>
          <span>📐 {short.resolution}</span>
          <span>💾 {short.size_mb}MB</span>
        </div>

        <div className="clip-actions">
          <button onClick={handleDownload} disabled={downloading} className="btn-dl">
            {downloading ? "Downloading..." : "↓ Download"}
          </button>
          {showYT && (
            <>
              <button className="btn-seo" onClick={onGenerateSEO} disabled={seoLoading}>
                {seoLoading ? "Generating..." : seo ? "↺ Regenerate SEO" : "✦ Generate SEO"}
              </button>
              {seo && (
                <button className="btn-expand" onClick={() => setExpanded(!expanded)}>
                  {expanded ? "▲ Hide SEO" : "▼ View & Edit SEO"}
                </button>
              )}
            </>
          )}
        </div>

        {showYT && seo && expanded && (
          <div className="seo-panel">
            <div className="seo-field">
              <label>Title</label>
              <input className="seo-input" value={seo.title || ""} onChange={(e) => onSeoEdit("title", e.target.value)} />
            </div>
            <div className="seo-field">
              <label>Description</label>
              <textarea className="seo-textarea" rows={5} value={seo.description || ""} onChange={(e) => onSeoEdit("description", e.target.value)} />
            </div>
            <div className="seo-field">
              <label>Tags</label>
              <input className="seo-input" value={(seo.tags || []).join(", ")} onChange={(e) => onSeoEdit("tags", e.target.value.split(",").map(t => t.trim()))} />
            </div>
            <div className="seo-field">
              <label>Hashtags</label>
              <input className="seo-input" value={(seo.hashtags || []).join(" ")} readOnly />
            </div>
            {uploadStatus === "done" && seo.yt_url ? (
              <a href={seo.yt_url} target="_blank" rel="noreferrer" className="btn-yt-link">▲ View on YouTube</a>
            ) : (
              <button
                className={`btn-upload ${uploadStatus === "uploading" ? "loading" : ""} ${uploadStatus === "error" ? "error" : ""}`}
                onClick={onUpload}
                disabled={uploadStatus === "uploading"}
              >
                {uploadStatus === "uploading" ? "Uploading..." : uploadStatus === "error" ? "✕ Failed — Retry" : "▲ Upload to YouTube"}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
