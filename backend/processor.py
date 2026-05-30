import asyncio
import os
import subprocess
import json
import re
import math
from pathlib import Path
import yt_dlp
import urllib.request


class VideoProcessor:
    def __init__(self, job_id, video_path, yt_url, output_dir, format, max_shorts, mode, clip_duration, jobs):
        self.job_id = job_id
        self.video_path = video_path
        self.yt_url = yt_url
        self.output_dir = Path(output_dir) / job_id
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.format = format
        self.max_shorts = max_shorts
        self.mode = mode  # "best_shorts" | "equal_clips"
        self.clip_duration = clip_duration  # seconds, for equal_clips mode
        self.jobs = jobs

    def update(self, status, progress, message, shorts=None):
        self.jobs[self.job_id]["status"] = status
        self.jobs[self.job_id]["progress"] = progress
        self.jobs[self.job_id]["message"] = message
        if shorts is not None:
            self.jobs[self.job_id]["shorts"] = shorts

    async def run(self, detection_only=False):
        try:
            if self.yt_url:
                self.update("processing", 5, "Downloading video from YouTube...")
                self.video_path = await asyncio.to_thread(self._download_youtube)
            elif self.video_path and self.video_path.startswith("http"):
                self.update("processing", 5, "Downloading video from URL...")
                self.video_path = await asyncio.to_thread(self._download_file_url)

            self.update("processing", 15, "Analyzing video metadata...")
            info = await asyncio.to_thread(self._get_video_info)
            duration = float(info.get("duration", 0))
            self.jobs[self.job_id]["video_path"] = self.video_path

            if detection_only:
                await self._run_detection_only(duration)
            elif self.mode == "equal_clips":
                await self._run_equal_clips(duration)
            else:
                await self._run_best_shorts(duration)

        except Exception as e:
            self.update("error", 0, f"Error: {str(e)}")
            raise

    async def _run_detection_only(self, duration):
        self.update("processing", 25, "Detecting scenes and engaging moments...")
        segments = await asyncio.to_thread(self._detect_scenes, duration)

        self.update("processing", 45, "Scoring segments for engagement...")
        best_segments = await asyncio.to_thread(self._rank_segments, segments, duration)

        self.jobs[self.job_id]["detected_segments"] = best_segments
        self.jobs[self.job_id]["shorts"] = [
            {
                "index": i,
                "start": seg["start"],
                "duration": seg["duration"],
                "score": seg.get("score", 0),
            }
            for i, seg in enumerate(best_segments)
        ]
        self.update("detected", 50, f"Detected {len(best_segments)} clips. Select which ones to export.", self.jobs[self.job_id]["shorts"])

    async def _run_equal_clips(self, duration):
        clip_sec = self.clip_duration
        total_clips = math.floor(duration / clip_sec)
        if total_clips == 0:
            total_clips = 1

        self.update("processing", 20, f"Splitting into {total_clips} clips of {clip_sec}s each...")

        shorts = []
        for i in range(total_clips):
            start = i * clip_sec
            actual_dur = min(clip_sec, duration - start)
            if actual_dur < 5:
                break
            pct = 20 + int((i / total_clips) * 75)
            self.update("processing", pct, f"Exporting clip {i+1}/{total_clips}...")
            seg = {"start": start, "end": start + actual_dur, "duration": actual_dur}
            results = await asyncio.to_thread(self._export_short, seg, i)
            shorts.extend(results)
            self.jobs[self.job_id]["shorts"] = shorts  # stream results live

        self.update("done", 100, f"All {len(shorts)} clips ready!", shorts=shorts)

    async def _run_best_shorts(self, duration):
        self.update("processing", 25, "Detecting scenes and engaging moments...")
        segments = await asyncio.to_thread(self._detect_scenes, duration)

        self.update("processing", 45, "Scoring segments for engagement...")
        best_segments = await asyncio.to_thread(self._rank_segments, segments, duration)

        shorts = []
        total = len(best_segments)
        for i, seg in enumerate(best_segments):
            pct = 55 + int((i / total) * 40)
            self.update("processing", pct, f"Exporting short {i+1}/{total}...")
            results = await asyncio.to_thread(self._export_short, seg, i)
            shorts.extend(results)
            self.jobs[self.job_id]["shorts"] = shorts

        self.update("done", 100, "All shorts ready!", shorts=shorts)

    def _download_youtube(self):
        out_path = str(self.output_dir / "source.%(ext)s")
        ydl_opts = {
            "format": "bestvideo[ext=mp4][height<=2160]+bestaudio[ext=m4a]/bestvideo[ext=mp4]+bestaudio/best[ext=mp4]/best",
            "outtmpl": out_path,
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 30,
            "skip_unavailable_fragments": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.yt_url, download=True)
            for f in self.output_dir.glob("source.*"):
                return str(f)
        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            if "Please sign in" in error_msg or "age-restricted" in error_msg.lower():
                raise Exception(
                    f"Video requires authentication or is age-restricted. "
                    f"Please upload the video file instead. Details: {error_msg}"
                )
            raise Exception(f"Failed to download video: {error_msg}")

    def _download_file_url(self):
        try:
            # Determine file extension from URL
            url = self.video_path
            path = url.split("?")[0]  # Remove query parameters
            ext = Path(path).suffix or ".mp4"

            out_path = str(self.output_dir / f"source{ext}")

            # Download file with progress
            def download_with_timeout(url, output_path, timeout=300):
                urllib.request.urlopen(url, timeout=timeout)
                urllib.request.urlretrieve(url, output_path)

            download_with_timeout(url, out_path)
            return out_path
        except Exception as e:
            raise Exception(f"Failed to download video from URL: {str(e)}")

    def _get_video_info(self):
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_streams", "-show_format", self.video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return json.loads(result.stdout).get("format", {})

    def _detect_scenes(self, duration):
        cmd = [
            "ffmpeg", "-i", self.video_path,
            "-vf", "select='gt(scene,0.35)',showinfo",
            "-vsync", "vfr", "-f", "null", "-",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stderr

        timestamps = [0.0]
        for line in output.split("\n"):
            if "pts_time" in line:
                match = re.search(r"pts_time:([\d.]+)", line)
                if match:
                    t = float(match.group(1))
                    if t > 0 and (not timestamps or t - timestamps[-1] > 5):
                        timestamps.append(t)

        if duration > 0:
            timestamps.append(duration)

        segments = []
        for i in range(len(timestamps) - 1):
            start = timestamps[i]
            end = timestamps[i + 1]
            seg_len = end - start
            if seg_len < 15:
                continue
            if seg_len <= 90:
                segments.append({"start": start, "end": end, "duration": seg_len})
            else:
                chunk_size = 55
                pos = start
                while pos < end - 20:
                    chunk_end = min(pos + chunk_size, end)
                    segments.append({"start": pos, "end": chunk_end, "duration": chunk_end - pos})
                    pos = chunk_end
        return segments

    def _rank_segments(self, segments, total_duration):
        scored = []
        for seg in segments:
            score = 0
            dur = seg["duration"]
            start = seg["start"]
            if 30 <= dur <= 60:
                score += 50
            elif 20 <= dur <= 90:
                score += 30
            else:
                score += 10
            rel_pos = start / total_duration if total_duration > 0 else 0
            if 0.05 < rel_pos < 0.85:
                score += 40
            elif 0.05 < rel_pos < 0.90:
                score += 20
            if 0.20 < rel_pos < 0.70:
                score += 20
            seg["score"] = score
            scored.append(seg)
        top = sorted(scored, key=lambda x: x["score"], reverse=True)[: self.max_shorts]
        top = sorted(top, key=lambda x: x["start"])
        return top

    def _get_source_dimensions(self):
        probe_cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_streams", self.video_path
        ]
        probe = subprocess.run(probe_cmd, capture_output=True, text=True)
        streams = json.loads(probe.stdout).get("streams", [])
        for s in streams:
            if s.get("codec_type") == "video":
                return s.get("width", 1920), s.get("height", 1080)
        return 1920, 1080

    def _export_short(self, segment, index):
        start = segment["start"]
        duration = segment["duration"]
        results = []
        src_w, src_h = self._get_source_dimensions()

        formats_to_export = []
        if self.format in ("vertical", "both"):
            formats_to_export.append("vertical")
        if self.format in ("horizontal", "both"):
            formats_to_export.append("horizontal")

        for fmt in formats_to_export:
            out_name = f"clip_{index+1:03d}_{fmt}.mp4"
            out_path = str(self.output_dir / out_name)

            if fmt == "vertical":
                crop_w = int(src_h * 9 / 16)
                crop_w = min(crop_w, src_w)
                crop_x = (src_w - crop_w) // 2
                vf = (
                    f"crop={crop_w}:{src_h}:{crop_x}:0,"
                    f"scale=2160:3840:flags=lanczos,"
                    f"pad=2160:3840:(ow-iw)/2:(oh-ih)/2"
                )
                target_w, target_h = 2160, 3840
            else:
                vf = "scale=3840:2160:flags=lanczos"
                target_w, target_h = 3840, 2160

            cmd = [
                "ffmpeg", "-y",
                "-ss", str(start),
                "-i", self.video_path,
                "-t", str(duration),
                "-vf", vf,
                "-c:v", "libx264",
                "-preset", "slow",
                "-crf", "18",
                "-c:a", "aac",
                "-b:a", "320k",
                "-movflags", "+faststart",
                out_path,
            ]
            subprocess.run(cmd, capture_output=True)

            if os.path.exists(out_path):
                size_mb = round(os.path.getsize(out_path) / (1024 * 1024), 1)
                results.append({
                    "filename": out_name,
                    "url": f"/outputs/{self.job_id}/{out_name}",
                    "format": fmt,
                    "duration": round(duration, 1),
                    "start": round(start, 1),
                    "resolution": f"{target_w}x{target_h}",
                    "size_mb": size_mb,
                    "uploaded_to_yt": False,
                    "yt_url": None,
                })
        return results

    async def export_clips(self, segments):
        try:
            shorts = []
            total = len(segments)
            for i, seg in enumerate(segments):
                pct = int((i / total) * 95) + 5
                self.update("processing", pct, f"Exporting clip {i+1}/{total}...")
                results = await asyncio.to_thread(self._export_short, seg, i)
                shorts.extend(results)
                self.jobs[self.job_id]["shorts"] = shorts

            self.update("done", 100, "All clips exported!", shorts=shorts)
        except Exception as e:
            self.update("error", 0, f"Export error: {str(e)}")
            raise
