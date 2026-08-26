from typing import Any
import json
import os
import sys
import threading
import traceback
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import config
from src.pipeline import execute_pipeline, seconds_to_hhmmss_sss

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
OUTPUT_DIR = config.OUTPUT_DIR

# Global state for tracking running pipeline jobs
current_job: dict[str, Any] = {
    "status": "idle",
    "progress": 0,
    "message": "",
    "result": None,
    "error": None,
}
job_lock = threading.Lock()


def run_pipeline_worker(video_url: str, target_dialogue: str):
    global current_job
    with job_lock:
        current_job["status"] = "running"
        current_job["progress"] = 10
        current_job["message"] = "Initializing extraction pipeline..."
        current_job["result"] = None
        current_job["error"] = None

    def progress_callback(msg: str, pct: int):
        with job_lock:
            current_job["progress"] = pct
            current_job["message"] = msg

    try:
        result = execute_pipeline(
            video_url=video_url,
            target_dialogue=target_dialogue,
            progress_callback=progress_callback,
        )
        with job_lock:
            current_job["status"] = "completed"
            current_job["progress"] = 100
            current_job["message"] = "Completed successfully!"
            current_job["result"] = result
            current_job["error"] = None
    except Exception as e:
        traceback.print_exc()
        with job_lock:
            current_job["status"] = "error"
            current_job["progress"] = 0
            current_job["message"] = f"Pipeline Error: {str(e)}"
            current_job["error"] = str(e)


class CustomRequestHandler(SimpleHTTPRequestHandler):
    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        if path in ("/", "/index.html"):
            index_file = TEMPLATES_DIR / "index.html"
            if not index_file.exists():
                self.send_response(404)
                self.send_cors_headers()
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"Index template not found")
                return
            content = index_file.read_bytes()
            self.send_response(200)
            self.send_cors_headers()
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

        elif path == "/api/status":
            with job_lock:
                data = json.dumps(current_job).encode("utf-8")
            self.send_response(200)
            self.send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        elif path in ("/api/frame", "/output/target_frame.png"):
            frame_path = OUTPUT_DIR / "target_frame.png"
            if frame_path.exists() and frame_path.is_file():
                content = frame_path.read_bytes()
                self.send_response(200)
                self.send_cors_headers()
                self.send_header("Content-Type", "image/png")
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_response(404)
                self.send_cors_headers()
                self.send_header("Content-Type", "application/json")
                err_msg = json.dumps({"error": "Target frame not found. Run pipeline first."}).encode("utf-8")
                self.send_header("Content-Length", str(len(err_msg)))
                self.end_headers()
                self.wfile.write(err_msg)
            return

        elif path.startswith("/static/"):
            file_path = BASE_DIR / path.lstrip("/")
            if file_path.exists() and file_path.is_file():
                self.send_response(200)
                self.send_cors_headers()
                content = file_path.read_bytes()
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return
            else:
                self.send_response(404)
                self.send_cors_headers()
                self.end_headers()
                return

        self.send_response(404)
        self.send_cors_headers()
        self.end_headers()

    def do_POST(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        if path == "/api/process":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                data = json.loads(body) if body else {}
            except Exception:
                data = {}

            video_url = data.get("video_url") or config.DEFAULT_VIDEO_URL
            target_dialogue = data.get("target_dialogue") or config.DEFAULT_TARGET_DIALOGUE

            with job_lock:
                if current_job["status"] == "running":
                    self.send_response(409)
                    self.send_cors_headers()
                    self.send_header("Content-Type", "application/json")
                    err_resp = json.dumps({"error": "A pipeline task is already in progress."}).encode("utf-8")
                    self.send_header("Content-Length", str(len(err_resp)))
                    self.end_headers()
                    self.wfile.write(err_resp)
                    return

            # Start worker thread
            thread = threading.Thread(
                target=run_pipeline_worker,
                args=(video_url, target_dialogue),
                daemon=True,
            )
            thread.start()

            self.send_response(200)
            self.send_cors_headers()
            self.send_header("Content-Type", "application/json")
            resp = json.dumps({"status": "started", "message": "Pipeline started successfully."}).encode("utf-8")
            self.send_header("Content-Length", str(len(resp)))
            self.end_headers()
            self.wfile.write(resp)
            return

        self.send_response(404)
        self.send_cors_headers()
        self.end_headers()


class ReusableThreadingServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def start_server(port: int = 5000):
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    server_address = ("", port)
    httpd = ReusableThreadingServer(server_address, CustomRequestHandler)
    print(f"\n=======================================================")
    print(f"  QuestOne React + Tailwind Frontend Server Running")
    print(f"  URL: http://localhost:{port}")
    print(f"=======================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer shutting down gracefully...")
        httpd.server_close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    start_server(port)
