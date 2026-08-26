import whisper
from pathlib import Path
from typing import Optional
from rapidfuzz import fuzz

class DialogueTranscriber:
    _model_cache = {}

    def __init__(self, model_size: str = "base"):
        # Cache model instance to prevent disk reloads on every request
        if model_size not in DialogueTranscriber._model_cache:
            print(f"[-] Loading Whisper model '{model_size}' into RAM...")
            DialogueTranscriber._model_cache[model_size] = whisper.load_model(model_size)
        else:
            print(f"[+] Reusing cached Whisper model '{model_size}'")
            
        self.model = DialogueTranscriber._model_cache[model_size]

    def locate_phrase(self, audio_path: Path, target_phrase: str, threshold: int = 75) -> dict:
        print("[-] Transcribing audio (word-level timestamps)...")
        result = self.model.transcribe(str(audio_path), word_timestamps=True, fp16=False)

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