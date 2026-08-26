from pathlib import Path
from typing import Optional
import torch
import whisper
from rapidfuzz import fuzz

class DialogueTranscriber:
    _model_cache = {}

    def __init__(self, model_size: str = "base"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        if model_size not in DialogueTranscriber._model_cache:
            print(f"[-] Loading Whisper model '{model_size}' onto device '{self.device}'...")
            DialogueTranscriber._model_cache[model_size] = whisper.load_model(model_size, device=self.device)
        else:
            print(f"[+] Reusing cached Whisper model '{model_size}'")
            
        self.model = DialogueTranscriber._model_cache[model_size]

    def locate_phrase(self, audio_path: Path, target_phrase: str, threshold: int = 75) -> dict:
        print("[-] Transcribing audio (word-level timestamps)...")
        
        use_fp16 = True if self.device == "cuda" else False
        result = self.model.transcribe(str(audio_path), word_timestamps=True, fp16=use_fp16)

        words: list[dict] = []
        for segment in result.get("segments", []):
            seg_words = segment.get("words")
            if seg_words:
                for w in seg_words:
                    if isinstance(w, dict) and "word" in w:
                        w_text = w["word"].strip()
                        w_start = w.get("start", segment.get("start", 0.0))
                        w_end = w.get("end", segment.get("end", w_start))
                        if w_text:
                            words.append({"word": w_text, "start": w_start, "end": w_end})
            else:
                seg_text = segment.get("text", "").strip()
                tokens = seg_text.split()
                if tokens:
                    seg_start = float(segment.get("start", 0.0))
                    seg_end = float(segment.get("end", seg_start + 1.0))
                    step = (seg_end - seg_start) / max(len(tokens), 1)
                    for idx, token in enumerate(tokens):
                        words.append({
                            "word": token,
                            "start": seg_start + idx * step,
                            "end": seg_start + (idx + 1) * step,
                        })

        if not words:
            raise RuntimeError("No words transcribed — audio may be silent or unreadable.")

        target_len = len(target_phrase.split())
        best_score: float = 0.0
        best_start: Optional[float] = None
        best_end: Optional[float] = None
        best_text: Optional[str] = None

        for window in range(max(1, target_len - 2), target_len + 3):
            for i in range(len(words) - window + 1):
                chunk = words[i:i + window]
                candidate_text = " ".join(w["word"] for w in chunk)
                score = fuzz.ratio(candidate_text.lower(), target_phrase.lower())
                if score > best_score:
                    best_score = score
                    best_start = chunk[0]["start"]
                    best_end = chunk[-1]["end"]
                    best_text = candidate_text

        if best_score < threshold or best_start is None or best_end is None:
            raise RuntimeError(
                f"No confident match found (best score {best_score:.1f} < {threshold}). "
                f"Closest: \"{best_text}\""
            )

        midpoint = (best_start + best_end) / 2
        print(f"[+] Match found: \"{best_text}\" (score={best_score:.1f}) at {midpoint:.2f}s")

        return {"start": best_start, "end": best_end, "midpoint": midpoint, "score": best_score, "text": best_text}


def get_or_download_media(url: str, output_dir: Path, filename: str = "temp_video.mp4") -> Path:
    """Checks the output directory for existing temp_video.mp4 or temp_audio.wav."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    target_path = output_dir / filename
    audio_fallback = output_dir / "temp_audio.wav"

    # Priority 1: Use temp_video.mp4 if it exists
    if target_path.exists() and target_path.stat().st_size > 0:
        print(f"[+] Found existing video at '{target_path}'. Skipping download.")
        return target_path

    # Priority 2: Fallback to temp_audio.wav if video isn't there
    if audio_fallback.exists() and audio_fallback.stat().st_size > 0:
        print(f"[+] Found existing audio at '{audio_fallback}'. Skipping download.")
        return audio_fallback

    # Priority 3: Download if neither file is present
    print(f"[-] No media found in '{output_dir}'. Downloading from {url}...")
    
    # Place your download execution code here (e.g., yt-dlp)
    
    return target_path


if __name__ == "__main__":
    import sys
    
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    try:
        import config
        default_url = config.DEFAULT_VIDEO_URL
        default_phrase = config.DEFAULT_TARGET_DIALOGUE
        output_directory = config.OUTPUT_DIR
    except Exception:
        default_url = "https://huggingface.co/datasets/sarankishore1912/questone-videos/resolve/main/3716271639269.mp4"
        default_phrase = "My mind rebels at stagnation"
        output_directory = Path("output")

    media_filename = "temp_video.mp4"  # Matches your output directory layout

    # Interactive input prompts
    user_url = input(f"Enter video URL [Press Enter for default: '{default_url}']: ").strip()
    source_url = user_url if user_url else default_url

    user_phrase = input(f"Enter search phrase [Press Enter for default: '{default_phrase}']: ").strip()
    search_phrase = user_phrase if user_phrase else default_phrase

    print(f"\n[-] Target URL   : {source_url}")
    print(f"[-] Search Phrase: \"{search_phrase}\"\n")

    # Step 1: Look for temp_video.mp4 or temp_audio.wav in output/
    media_file_path = get_or_download_media(
        url=source_url, 
        output_dir=output_directory, 
        filename=media_filename
    )

    # Step 2: Run transcription on the resolved path
    transcriber = DialogueTranscriber(model_size="base")
    location_data = transcriber.locate_phrase(media_file_path, target_phrase=search_phrase)
    
    print("\nResults:", location_data)