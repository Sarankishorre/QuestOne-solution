from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"

DEFAULT_VIDEO_URL = "https://youtu.be/NPX39xzhtr8"
DEFAULT_TARGET_DIALOGUE = "My mind rebels at stagnation"

WHISPER_MODEL_SIZE = "base"          # tiny/base/small/medium/large-v3
FUZZY_MATCH_THRESHOLD = 75             # 0-100, rapidfuzz partial_ratio
FRAME_SEARCH_WINDOW = 0.5            # seconds either side of timestamp to scan for sharpest frame