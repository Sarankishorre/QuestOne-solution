from pathlib import Path
from typing import Callable, Optional
import config
from src.audio_extractor import AudioExtractor
from src.transcriber import DialogueTranscriber
from src.frame_processor import FrameProcessor


def seconds_to_hhmmss_sss(seconds: float) -> str:
    """Format seconds into HH:MM:SS.sss format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def execute_pipeline(
    video_url: str,
    target_dialogue: str,
    progress_callback: Optional[Callable[[str, int], None]] = None,
) -> dict:
    """
    Executes the end-to-end video dialogue frame extraction pipeline.
    """
    output_video_path = config.OUTPUT_DIR / "temp_video.mp4"
    output_audio_path = config.OUTPUT_DIR / "temp_audio.wav"
    output_frame_path = config.OUTPUT_DIR / "target_frame.png"
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if progress_callback:
        progress_callback("Step 1: Downloading video stream...", 20)
    AudioExtractor.extract_audio(video_url, output_audio_path, output_video_path)

    if progress_callback:
        progress_callback("Step 2: Transcribing audio with Whisper AI & matching dialogue...", 50)
    transcriber = DialogueTranscriber(model_size=config.WHISPER_MODEL_SIZE)
    match_info = transcriber.locate_phrase(
        audio_path=output_audio_path,
        target_phrase=target_dialogue,
        threshold=config.FUZZY_MATCH_THRESHOLD,
    )

    if progress_callback:
        progress_callback("Step 3: Extracting optimal sharpness frame...", 85)
    frame_info = FrameProcessor.extract_optimal_frame(
        video_path=output_video_path,
        timestamp=match_info["midpoint"],
        output_path=output_frame_path,
        search_window=config.FRAME_SEARCH_WINDOW,
    )

    if progress_callback:
        progress_callback("Processing complete!", 100)

    ts_formatted = seconds_to_hhmmss_sss(frame_info["timestamp"])
    target_clean = target_dialogue.strip()

    # Exact expected format:
    # Timestamp : HH:MM:SS.sss
    # Frame : <Frame number>
    # Text : "<target dialogue>"
    formatted_output = (
        f"Timestamp : {ts_formatted}\n"
        f"Frame : {frame_info['frame_number']}\n"
        f'Text : "{target_clean}"'
    )

    return {
        "status": "success",
        "formatted_output": formatted_output,
        "timestamp_formatted": ts_formatted,
        "timestamp_seconds": frame_info["timestamp"],
        "frame_number": frame_info["frame_number"],
        "text": target_clean,
        "matched_text": match_info.get("text", target_clean),
        "score": round(match_info["score"], 1),
        "sharpness_score": frame_info.get("sharpness_score", 0.0),
        "saved_path": str(frame_info["saved_path"]),
    }
