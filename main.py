import config
from src.pipeline import execute_pipeline, seconds_to_hhmmss_sss


def run_pipeline():
    print("\n================ PIPELINE INITIALIZED ================")
    print("Select Video Source Option:")
    print("  [1] Use local cached video file / default URL")
    print("  [2] Provide a custom video URL")
    choice = input("Enter choice (1 or 2): ").strip()

    video_url = input("Enter the video URL: ").strip().strip('"').strip("'") \
        if choice == "2" else config.DEFAULT_VIDEO_URL

    target_text = input(
        f"Enter target dialogue text [Enter for default: '{config.DEFAULT_TARGET_DIALOGUE}']: "
    ).strip() or config.DEFAULT_TARGET_DIALOGUE

    print(f"\nTarget Text: \"{target_text}\"\n")

    try:
        result = execute_pipeline(
            video_url=video_url,
            target_dialogue=target_text,
            progress_callback=lambda msg, pct: print(f"[{pct}%] {msg}")
        )

        print("\n================ MATCH FOUND ================")
        print(result["formatted_output"])
        print(f"Match Score  : {result['score']}%")
        print(f"Output Image : {result['saved_path']}")
        print("===============================================\n")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n[!] Pipeline Failure: {e}")


if __name__ == "__main__":
    run_pipeline()