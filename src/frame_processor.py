import cv2
from pathlib import Path


class FrameProcessor:
    @staticmethod
    def _sharpness(frame) -> float:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return cv2.Laplacian(gray, cv2.CV_64F).var()

    @staticmethod
    def extract_optimal_frame(video_path: Path, timestamp: float, output_path: Path,
                               search_window: float = 0.5) -> dict:  # Reduced default search window for speed
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError(f"Could not open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0

        start_ms = max(0, (timestamp - search_window)) * 1000
        end_ms = (timestamp + search_window) * 1000

        best_frame = None
        best_score = -1.0
        best_ts = timestamp
        t_ms = start_ms
        
        # Optimization: Step by 2 frames at a time (or 1.5x fps interval) to cut processing time in half
        step_ms = max(1000 / fps, 60.0) 

        while t_ms <= end_ms:
            cap.set(cv2.CAP_PROP_POS_MSEC, t_ms)
            ok, frame = cap.read()
            if not ok:
                break
            score = FrameProcessor._sharpness(frame)
            if score > best_score:
                best_score, best_frame, best_ts = score, frame, t_ms / 1000
            t_ms += step_ms

        cap.release()

        if best_frame is None:
            raise RuntimeError(f"Could not extract any frame near timestamp {timestamp:.2f}s")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(output_path), best_frame, [cv2.IMWRITE_PNG_COMPRESSION, 0])

        return {
            "timestamp": round(best_ts, 3),
            "frame_number": round(best_ts * fps),
            "sharpness_score": round(best_score, 2),
            "saved_path": str(output_path),
        }