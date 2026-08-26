# Engineering Challenges & Decision-Making Log

This document records the technical bottlenecks encountered during the development of the audio-visual dialogue extractor and details the architectural solutions implemented to solve them[cite: 3].

---

## Challenge 1: Unresolvable Network Request Blocks & Anti-Scraping Restrictions

* **Issue:** Direct video acquisition from local network environments was completely blocked by source platform rate limits, bot-detection challenge walls, and regional network restrictions.
* **Root Cause Analysis:** Source streaming platforms enforce strict anti-automation policies that flag and drop direct automated client requests. Traditional client-side workarounds—including custom HTTP headers, proxy servers, and VPN routing—failed entirely because requests were flagged at the network infrastructure level.
* **Decision & Solution:**
  1. Decoupled media acquisition from local network execution by offloading video fetching and hosting to a **Hugging Face Space / Dataset**.
  2. Configured the local processing pipeline to pull directly from public Hugging Face CDN endpoints (`/resolve/main/...`), ensuring unblocked, high-bandwidth media downloads independent of local network restrictions.

---

## Challenge 2: High Latency from Redundant Downloads & Heavy Model Load

* **Issue:** Downloading large video files (~400MB+) on every run combined with repeatedly reloading the heavy OpenAI Whisper model caused severe execution delays and workflow friction[cite: 3].
* **Root Cause Analysis:** Initial processing scripts lacked file system state checks prior to initiating downloads[cite: 3]. Furthermore, initializing the Whisper model on every execution cycle introduced unnecessary cold-start overhead. Attempting GPU acceleration via CUDA introduced driver instability and environment errors on Python 3.13, making optimized CPU execution with local caching the most reliable architecture.
* **Decision & Solution:**
  1. Implemented a local caching utility (`get_or_download_media`) that inspects the `output/` directory for existing media files (`temp_video.mp4` or `temp_audio.wav`) before triggering network calls[cite: 3]:
     ```python
     if target_path.exists() and target_path.stat().st_size > 0:
         return target_path  # Reuses existing file
     ```
  2. Introduced class-level in-memory model caching (`_model_cache`) inside `DialogueTranscriber` to retain the loaded Whisper instance across multiple search queries, eliminating repetitive model loading times.

---

## Challenge 3: Millisecond Timestamp Precision & Frame-Accurate Cut Alignment

* **Issue:** Coarse, whole-second timestamp extraction produced imprecise video cuts, often missing the exact visual frame where the target word was articulated.
* **Root Cause Analysis:** Spoken dialogue occurs within rapid millisecond time windows. Low sampling resolution or whole-second timestamp rounding fails to isolate exact lip movements and spoken articulation, resulting in truncated or misaligned video clips.
* **Decision & Solution:**
  1. Enabled Whisper's `word_timestamps=True` mode to extract granular start and end time offsets (in seconds with millisecond decimal precision) for every transcribed word token.
  2. Integrated high-FPS frame-mapping logic that converts millisecond acoustic boundaries directly into exact video frame numbers, ensuring the extracted segment captures the exact visual sequence corresponding to the target spoken phrase.

---

## Challenge 4: Audio Transcription Mismatches Breaking Exact Search Queries

* **Issue:** Direct string match logic (`string == target`) regularly failed when speech-to-text outputs contained minor acoustic errors, missing punctuation, filler words, or slight phrase variations[cite: 3].
* **Root Cause Analysis:** Speech recognition outputs depend heavily on background noise, accents, and acoustic clarity, making strict string equality brittle[cite: 3].
* **Decision & Solution:**
  Implemented sliding-window fuzzy string matching using `rapidfuzz`[cite: 3]. The algorithm dynamically scans token windows around the target word count and calculates similarity ratios to accurately locate phrases despite minor transcript discrepancies[cite: 3].
