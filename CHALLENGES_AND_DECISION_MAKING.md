# Engineering Challenges & Decision-Making Log

This document records the technical bottlenecks encountered during the development of the audio-visual dialogue extractor and details the architectural solutions implemented to solve them.

---

## Challenge 1: Severe Latency During Transcription Initialization

- **Issue:** Initial runs using OpenAI Whisper `base` with `word_timestamps=True` on media files (~400MB+) experienced high processing latency and hung for extended periods.
- **Root Cause Analysis:** The execution environment defaulted to CPU execution due to a standard CPU-only PyTorch wheel installation. Generating word-level alignment requires frame-by-frame attention calculation, which is computationally expensive on a CPU.
- **Decision & Solution:**
  1. Updated model initialization to dynamically detect CUDA acceleration (`self.device = "cuda" if torch.cuda.is_available() else "cpu"`).
  2. Enabled `fp16=True` execution inside `model.transcribe()` when running on CUDA to leverage GPU Tensor Cores.

---

## Challenge 2: Redundant Network Media Downloads

- **Issue:** Every execution cycle triggered a network download request, re-downloading large video files even when iteratively testing the same media asset.
- **Root Cause Analysis:** Processing flows lacked file system state inspection prior to downloading.
- **Decision & Solution:**
  Created a helper utility (`get_or_download_media`) that inspects the designated output folder for existing, non-empty media assets (`temp_video.mp4` or `temp_audio.wav`) before invoking download functions:
  ```python
  if target_path.exists() and target_path.stat().st_size > 0:
      return target_path  # Reuses existing file
  ```

---

## Challenge 3: PyTorch CUDA Package Compatibility on Python 3.13

- **Issue:** Attempting to install PyTorch CUDA 12.1 packages on Python 3.13 via standard `pip` indexes produced the following error:
  `ERROR: Could not find a version that satisfies the requirement torch`.
- **Root Cause Analysis:** Official PyTorch CUDA 12.1 binary packages are not published for Python 3.13; PyTorch transitioned Python 3.13 CUDA distributions to CUDA 12.4 (`cu124`) index paths.
- **Decision & Solution:**
  Targeted the explicit CUDA 12.4 wheel repository during installation:
  ```bash
  pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
  ```

---

## Challenge 4: Audio Transcription Mismatches Breaking Exact Search Queries

- **Issue:** Direct string match logic (`string == target`) regularly failed when speech-to-text outputs contained minor acoustic errors, missing punctuation, or slight phrase variations.
- **Root Cause Analysis:** Speech recognition outputs depend heavily on background noise and speaker clarity, making exact string equality brittle.
- **Decision & Solution:**
  Implemented sliding-window fuzzy string matching via `rapidfuzz`. The window dynamically expands around the target length and computes similarity ratios across word token arrays to reliably locate phrases even with imperfect audio transcriptions.

---

## Challenge 5: Local Network Requests Blocked at the Source Platform

- **Issue:** Downloading source video directly from the local machine was unreliable — requests were increasingly met with bot-detection challenges and outright request blocking, regardless of client spoofing, cookie authentication, or retry logic.
- **Root Cause Analysis:** The source platform applies escalating anti-automation measures at the network level (IP-based flags, JavaScript challenge walls, session verification) that specifically target direct, local, non-browser requests. This made local-only video acquisition fragile and inconsistent, independent of any application-level bug.
- **Decision & Solution:**
  Moved video ingestion off the local machine entirely by routing it through a **Hugging Face Space**, which handles fetching/uploading the source video in an environment not subject to the same local network restrictions. The pipeline then consumes the resulting media file locally for the remaining processing stages (audio extraction, transcription, matching, frame extraction), decoupling "acquiring the video" from "processing the video."
