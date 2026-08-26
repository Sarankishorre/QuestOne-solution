# Project Flow — Audio-Visual Dialogue Extractor & Timestamp Identifier

This document walks through the pipeline end-to-end, stage by stage, in the order execution actually happens.

---

## Stage 0 — User Input

The user provides two things:
- A video source (URL)
- A target dialogue phrase to locate inside that video

---

## Stage 1 — Media Ingestion (Hugging Face Space)

Rather than the local machine making a direct network request to the source platform, the video is fetched from a **Hugging Face Space** acting as an intermediary mirror.

**Why:** direct local downloads from video platforms increasingly hit bot-detection and request-blocking at the network level (rate limits, IP flags, JS-challenge walls), which made local-only extraction unreliable. The Hugging Face Space provides a stable, repeatable path to acquire the video without the local machine making the flagged request.

---

## Stage 2 — Local Cache Check

Before doing any further work, the pipeline checks the `output/` directory for an existing, non-empty `temp_video.mp4` or `temp_audio.wav`.

- **Found** → skip ingestion + audio extraction entirely
- **Not found** → proceed to audio extraction

This avoids re-fetching or re-processing the same media on repeated runs.

---

## Stage 3 — Audio Extraction

FFmpeg strips the audio track from the downloaded video and converts it to a pipeline-friendly format:
- Mono channel
- 16kHz sample rate
- PCM WAV encoding

This normalized format is what Whisper expects for consistent, fast transcription.

---

## Stage 4 — Device & Hardware Detection

Before transcription starts, the pipeline detects whether a CUDA-capable GPU is available:
- **GPU available** → load Whisper on CUDA, enable `fp16` precision
- **No GPU** → fall back to CPU execution

---

## Stage 5 — Whisper Speech-to-Text

Whisper transcribes the extracted audio with word-level timestamps enabled, producing an array of `{ word, start_time, end_time }` entries.

If a segment doesn't return word-level timestamps, the pipeline falls back to evenly distributing timestamps across that segment's tokens, so downstream matching always has a timestamp per word.

---

## Stage 6 — Fuzzy Phrase Matching (rapidfuzz)

The target phrase is compared against sliding windows of transcribed words:
- Window size is centered around the target phrase's word count (checked across a small range)
- Each window's text is compared to the target phrase using `rapidfuzz.fuzz.ratio`
- The highest-scoring window becomes the match, provided it clears the configured confidence threshold

This makes matching resilient to minor transcription errors, missing punctuation, or slightly different phrasing.

---

## Stage 7 — Optimal Frame Extraction

Using the midpoint timestamp of the matched phrase, the pipeline scans a small window of frames around that timestamp (e.g. ±0.5s) and scores each one using Laplacian variance (a sharpness/blur metric). The sharpest frame in that window is selected and saved.

---

## Stage 8 — Output

The pipeline returns:
- Formatted timestamp (`HH:MM:SS.sss`)
- Frame number
- Matched dialogue text
- Match confidence score
- Frame sharpness score
- Path to the saved frame image

---

## Diagram

```
+-------------------------------------------------------------------------+
|                               USER INPUT                                |
|             - Media URL                                                 |
|             - Target Search Phrase                                      |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                 MEDIA INGESTION (Hugging Face Space)                    |
|   Video is fetched via a hosted Space, avoiding local network-level    |
|   request blocking / bot-detection on direct downloads                  |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                          LOCAL CACHE CHECK                              |
|   Inspect output/ for existing 'temp_video.mp4' or 'temp_audio.wav'     |
+-------------------------------------------------------------------------+
                 |                                       |
    [File Found / Non-Empty]                     [File Missing]
                 |                                       |
                 v                                       v
   +---------------------------+           +---------------------------+
   |  Skip Extraction Step     |           |  Extract Audio (FFmpeg)   |
   +---------------------------+           +---------------------------+
                 |                                       |
                 +-------------------+-------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                        DEVICE & HARDWARE DETECT                         |
|        Detect CUDA (NVIDIA GPU). Enable fp16 precision mode             |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                        WHISPER SPEECH-TO-TEXT                           |
|      Generate word-level timestamp array: [{word, start, end}, ...]     |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                   FUZZY PHRASE MATCHING (rapidfuzz)                     |
|  Sliding-window comparison over word arrays to match target text string |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                     OPTIMAL FRAME EXTRACTION (OpenCV)                   |
|   Scan a small window around the matched timestamp for the sharpest    |
|   frame using Laplacian variance scoring                                |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                              OUTPUT DATA                                |
|         - Formatted Timestamp (HH:MM:SS.sss) & Frame Number             |
|         - Matched Dialogue Text & Confidence Score                      |
|         - Saved Frame Path & Sharpness Score                            |
+-------------------------------------------------------------------------+
```
