# Audio-Visual Dialogue Extractor & Timestamp Identifier

An automated pipeline that locates the **exact timestamp of a spoken phrase** inside a video, and returns the sharpest possible frame at that moment. It combines OpenAI **Whisper** speech-to-text with dynamic **fuzzy string matching** to turn spoken dialogue into granular, word-level timestamps — so instead of manually scrubbing through a video looking for a line, you just type the line and get the frame.

---

## Summary

Standard search engines and video players can't query *spoken* dialogue inside a video or audio file directly — there's no "Ctrl+F" for what someone said on screen. Manually scrubbing through footage to find one line of dialogue is slow and error-prone.

This project solves that by:

1. **Ingesting media reliably** — video is sourced through a **Hugging Face Space** acting as a media-fetch intermediary, rather than downloading directly from the source platform on the local machine. Direct local downloads from platforms like YouTube are increasingly subject to bot-detection and network-level request blocking (rate limiting, IP flags, JS-challenge walls), which made local extraction unreliable. Routing ingestion through a Hugging Face Space sidesteps this bottleneck and gives the pipeline a stable, repeatable way to pull source video.
2. **Transcribing it into time-aligned, word-level text** using Whisper.
3. **Locating the target phrase** via fuzzy text matching, even when the transcription isn't a perfect match for the phrase as typed.
4. **Extracting the sharpest frame** at that exact moment, using a small local search window and a sharpness (Laplacian variance) score to avoid motion-blurred frames.
5. **Caching every stage locally**, so re-running the same video/phrase doesn't repeat expensive downloads or transcriptions.

---

## Why We Built This

- Manual timestamp-hunting in long-form video is tedious and doesn't scale.
- Exact string matching against speech-to-text output is brittle — background noise, filler words, and imperfect transcription mean the target phrase is rarely transcribed character-for-character.
- Reliable video *acquisition* turned out to be its own problem: local machines making direct requests to video platforms increasingly hit bot-detection and network blocks. Using a Hugging Face Space as the upload/fetch layer decouples "getting the video" from "processing the video," and avoids those local network restrictions entirely.

---

## Key Technical Features

- **Hugging Face Space–based Ingestion** — Video acquisition is handled through a hosted Hugging Face Space rather than direct local network requests, avoiding the bot-detection and request-blocking issues that made direct local downloads unreliable.
- **Local Asset Reuse** — Checks `output/` for an existing `temp_video.mp4` / `temp_audio.wav` before triggering any fetch, avoiding redundant downloads.
- **Word-Level Speech-to-Text** — Whisper transcribes with word-level timestamps, not just sentence/segment-level.
- **Fuzzy Timestamp Matching** — `rapidfuzz.fuzz.ratio` is run across a sliding window of word tokens (sized around the target phrase length) to find the closest match even with imperfect transcription.
- **Sharpest-Frame Extraction** — Searches a small time window around the matched timestamp and picks the frame with the highest Laplacian-variance sharpness score, instead of just grabbing the nearest frame.
- **Hardware-Aware Transcription** — Detects CUDA availability and enables `fp16` precision automatically to speed up transcription on supported GPUs.

---

## Requirements & Setup

### Environment

- Python 3.12 or 3.13
- NVIDIA GPU with updated drivers (optional, for accelerated transcription)
- FFmpeg installed and available on PATH

### Installation

```bash
# Install PyTorch with CUDA 12.4 support
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# Install Whisper & core dependencies
pip install openai-whisper rapidfuzz
```

### Basic Usage

```python
from pathlib import Path
from src.pipeline import execute_pipeline

result = execute_pipeline(
    video_url="https://example.com/video",
    target_dialogue="your target phrase",
    progress_callback=lambda msg, pct: print(f"[{pct}%] {msg}")
)

print(result["formatted_output"])
```

Output format:
```
Timestamp : HH:MM:SS.sss
Frame : <frame number>
Text : "<matched dialogue>"
```

---

## Project Structure

| Component | Responsibility |
|---|---|
| `audio_extractor.py` | Fetches source video (via Hugging Face Space ingestion) and extracts a mono, 16kHz WAV audio track |
| `transcriber.py` | Runs Whisper transcription and locates the target phrase via fuzzy matching |
| `frame_processor.py` | Extracts the sharpest frame around the matched timestamp |
| `pipeline.py` | Orchestrates the end-to-end flow and formats the final output |

For the full step-by-step pipeline breakdown and diagram, see **`PROJECT_FLOW.txt`**.
For a log of engineering issues encountered and how they were solved, see **`CHALLENGES_AND_DECISION_MAKING.md`**.
