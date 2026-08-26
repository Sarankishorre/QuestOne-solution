from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"

DEFAULT_VIDEO_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
DEFAULT_TARGET_DIALOGUE = "Never gonna give you up"

WHISPER_MODEL_SIZE = "medium"          # tiny/base/small/medium/large-v3
FUZZY_MATCH_THRESHOLD = 75             # 0-100, rapidfuzz partial_ratio
FRAME_SEARCH_WINDOW = 0.75             # seconds either side of timestamp to scan for sharpest frame