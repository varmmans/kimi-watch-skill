#!/usr/bin/env python3
"""Extract transcript/subtitles from a video URL (YouTube or any yt-dlp supported site).

Strategy (agent decides order, this script implements the fallbacks):
  1. YouTube URL  -> youtube-transcript-api (fast, no media download)
  2. Any URL      -> yt-dlp automatic/manual subtitles
  3. --audio      -> download audio (last resort; transcribe with an STT tool if needed)

Usage:
  python3 get_transcript.py <url> [--out transcript.txt] [--lang es|en|...]
                              [--timestamps] [--audio] [--audio-out audio.mp3]

Outputs JSON to stdout: {"title","uploader","duration", "source", "transcript_file", "audio_file"}
If no subtitles exist, transcript_file is null and audio_file is set (with --audio).
"""
import argparse
import json
import os
import re
import sys
import tempfile

YOUTUBE_RE = re.compile(r"(?:youtube\.com|youtu\.be|youtube-nocookie\.com)")


def yt_video_id(url: str) -> str | None:
    m = re.search(r"(?:v=|youtu\.be/|shorts/|embed/)([\w-]{11})", url)
    return m.group(1) if m else None


def try_youtube_transcript_api(video_id: str, lang: str | None):
    from youtube_transcript_api import YouTubeTranscriptApi
    api = YouTubeTranscriptApi()
    try:
        if lang:
            fetched = api.fetch(video_id, languages=[lang, "en", "es"])
        else:
            fetched = api.fetch(video_id)
        segments = [
            {"start": round(s.start, 2), "text": s.text}
            for s in fetched.snippets
        ]
        return segments, f"youtube-transcript-api ({fetched.language_code})"
    except Exception:
        return None, None


def try_ytdlp_subtitles(url: str, lang: str | None, tmpdir: str):
    import yt_dlp

    def hook(d):
        if d.get("status") == "finished":
            print(f"[yt-dlp] subtitle file: {d.get('filename')}", file=sys.stderr)

    base = os.path.join(tmpdir, "subs")
    ydl_opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitlesformat": "vtt/srt/best",
        "subtitleslangs": [lang] if lang else ["all"],
        "outtmpl": base + ".%(ext)s",
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [hook],
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        # collect downloaded subtitle files
        files = []
        for root, _, names in os.walk(tmpdir):
            for n in names:
                if n.startswith("subs.") and n.rsplit(".", 1)[-1] in ("vtt", "srt", "ttml", "srv3"):
                    files.append(os.path.join(root, n))
        return info, files


def parse_subtitle_file(path: str) -> list[dict]:
    """Parse .vtt or .srt into [{start, text}] (deduplicated, no tags)."""
    raw = open(path, encoding="utf-8", errors="replace").read()
    raw = re.sub(r"<[^>]+>", "", raw)
    segments = []
    if path.endswith(".srt"):
        blocks = re.split(r"\n\s*\n", raw)
        for b in blocks:
            m = re.search(r"(\d+:\d+:\d+[,.]\d+)\s*-->", b)
            if not m:
                continue
            text = re.sub(r"^\s*\d+\s*$", "", b, flags=re.M)
            text = re.sub(r"\d+:\d+:\d+[,.]\d+\s*-->\s*\d+:\d+:\d+[,.]\d+", "", text)
            text = " ".join(line.strip() for line in text.splitlines() if line.strip())
            if text:
                h, mnt, rest = m.group(1).replace(",", ".").split(":")
                segments.append({"start": int(h) * 3600 + int(mnt) * 60 + float(rest), "text": text})
    else:  # vtt
        raw = re.sub(r"^WEBVTT.*?(\d{2}:\d{2}:\d{2}\.\d{3})", r"\1", raw, flags=re.S)
        for line in raw.splitlines():
            m = re.match(r"(?:\d+\s+)?(\d{2}):(\d{2}):(\d{2})\.\d{3}\s+-->", line.strip())
            if m:
                h, mnt, s = int(m.group(1)), int(m.group(2)), int(m.group(3))
                segments.append({"start": h * 3600 + mnt * 60 + s, "text": None})
            else:
                line = line.strip()
                if line and segments and segments[-1]["text"] is None:
                    segments[-1]["text"] = line
                elif line and segments:
                    segments[-1]["text"] = (segments[-1]["text"] or "") + " " + line
    # dedupe consecutive identical / roll-up caption lines
    out = []
    for seg in segments:
        if seg["text"] and (not out or out[-1]["text"] != seg["text"]):
            out.append(seg)
    return out


def fmt_ts(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"


def write_transcript(segments: list[dict], out_path: str, with_timestamps: bool) -> None:
    with open(out_path, "w", encoding="utf-8") as f:
        for seg in segments:
            if with_timestamps:
                f.write(f"[{fmt_ts(seg['start'])}] {seg['text']}\n")
            else:
                f.write(seg["text"] + "\n")


def download_audio(url: str, out_path: str) -> None:
    import yt_dlp
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": out_path,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--out", help="Output transcript file path (.txt)")
    ap.add_argument("--lang", help="Preferred subtitle language code (e.g. es, en)")
    ap.add_argument("--timestamps", action="store_true", help="Prefix each line with [HH:MM:SS]")
    ap.add_argument("--audio", action="store_true", help="Fallback: download audio if no subtitles")
    ap.add_argument("--audio-out", default=None, help="Audio output path (default: <tmpdir>/audio.mp3)")
    args = ap.parse_args()

    result = {"url": args.url, "title": None, "uploader": None, "duration": None,
              "source": None, "transcript_file": None, "audio_file": None}
    segments, source = None, None

    # Strategy 1: YouTube transcript API
    if YOUTUBE_RE.search(args.url):
        vid = yt_video_id(args.url)
        if vid:
            segments, source = try_youtube_transcript_api(vid, args.lang)
            if segments:
                result["source"] = source

    # Strategy 2: yt-dlp subtitles (any site)
    if not segments:
        tmpdir = tempfile.mkdtemp(prefix="watch_")
        try:
            info, files = try_ytdlp_subtitles(args.url, args.lang, tmpdir)
            result["title"] = info.get("title")
            result["uploader"] = info.get("uploader") or info.get("channel")
            result["duration"] = info.get("duration")
            if files:
                # prefer manual subs over auto, preferred lang
                files.sort(key=lambda p: ("auto" in p, args.lang and args.lang not in p))
                segments = parse_subtitle_file(files[0])
                if segments:
                    result["source"] = f"yt-dlp subtitles ({os.path.basename(files[0])})"
        except Exception as e:
            print(f"[watch] yt-dlp subtitle extraction failed: {e}", file=sys.stderr)

    # Write transcript
    if segments:
        out_path = args.out or os.path.join(tempfile.gettempdir(), "watch_transcript.txt")
        write_transcript(segments, out_path, args.timestamps)
        result["transcript_file"] = out_path
        result["language"] = source.split("(")[-1].rstrip(")") if source and "(" in source else None

    # Strategy 3: audio fallback
    if not segments and args.audio:
        audio_out = args.audio_out or os.path.join(tempfile.gettempdir(), "watch_audio.mp3")
        try:
            download_audio(args.url, audio_out)
            result["audio_file"] = audio_out
        except Exception as e:
            result["error"] = f"audio download failed: {e}"

    if not segments and not result.get("audio_file"):
        result["error"] = result.get("error") or "no subtitles found; retry with --audio to download audio"

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
