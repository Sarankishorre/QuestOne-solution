import config
from src.audio_extractor import AudioExtractor
from src.transcriber import DialogueTranscriber
from src.frame_processor import FrameProcessor


def run_pipeline():
    print("\n================ PIPELINE INITIALIZED ================")
    print("Select Video Source Option:")
    print("  [1] Use local cached video file")
    print("  [2] Provide a video URL")
    choice = input("Enter choice (1 or 2): ").strip()

    video_url = input("Enter the video URL: ").strip().strip('"').strip("'") \
        if choice == "2" else config.DEFAULT_VIDEO_URL

    target_text = input(
        f"Enter target dialogue text [Enter for default: '{config.DEFAULT_TARGET_DIALOGUE}']: "
    ).strip() or config.DEFAULT_TARGET_DIALOGUE

    output_video_path = config.OUTPUT_DIR / "temp_video.mp4"
    output_audio_path = config.OUTPUT_DIR / "temp_audio.wav"

    print(f"\nTarget Text: \"{target_text}\"\n")

    try:
        AudioExtractor.extract_audio(video_url, output_audio_path, output_video_path)

        transcriber = DialogueTranscriber(model_size=config.WHISPER_MODEL_SIZE)
        match_info = transcriber.locate_phrase(
            audio_path=output_audio_path,
            target_phrase=target_text,
            threshold=config.FUZZY_MATCH_THRESHOLD,
        )

        frame_info = FrameProcessor.extract_optimal_frame(
            video_path=output_video_path,
            timestamp=match_info["midpoint"],
            output_path=config.OUTPUT_DIR / "target_frame.png",
            search_window=config.FRAME_SEARCH_WINDOW,
        )

        print("\n================ MATCH FOUND ================")
        print(f"Timestamp    : {frame_info['timestamp']}s")
        print(f"Frame Number : {frame_info['frame_number']}")
        print(f"Match Score  : {match_info['score']:.1f}")
        print(f"Output Image : {frame_info['saved_path']}")
        print("===============================================")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n[!] Pipeline Failure: {e}")


if __name__ == "__main__":
    run_pipeline()