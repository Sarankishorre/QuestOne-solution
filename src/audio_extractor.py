from pathlib import Path
import subprocess
import traceback
import yt_dlp

class AudioExtractor:
    @staticmethod
    def extract_audio(video_url: str, output_audio_path: Path, output_video_path: Path):
        print(f"[-] Step 1: Downloading stream: {video_url}")
        output_video_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Clean up old temporary files from prior runs
        for old_file in output_video_path.parent.glob("temp_video*"):
            try:
                old_file.unlink()
            except Exception:
                pass
                
        if output_audio_path.exists():
            try:
                output_audio_path.unlink()
            except Exception:
                pass

        # Capped at 720p max height to dramatically speed up downloads
        ydl_opts = {
            "format": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
            "merge_output_format": "mp4",
            "outtmpl": f"{output_video_path.with_suffix('')}.%(ext)s",
            "quiet": False,
            "no_warnings": True,
            "nocheckcertificate": True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            
            possible_files = list(output_video_path.parent.glob("temp_video*"))
            valid_files = [f for f in possible_files if f.is_file() and not f.name.endswith('.wav')]
            
            if not valid_files:
                raise RuntimeError("Download completed, but no video file was found in the output directory.")
            
            actual_video_file = valid_files[0]
            print(f"[+] Successfully located downloaded video: {actual_video_file}")
            
            # Extract audio track using ffmpeg
            print(f"[-] Extracting audio track to {output_audio_path}...")
            cmd = [
                "ffmpeg", "-y",
                "-i", str(actual_video_file),
                "-vn",
                "-acodec", "pcm_s16le",
                "-ar", "16000",
                "-ac", "1",
                str(output_audio_path)
            ]
            
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                print(f"FFmpeg STDERR:\n{result.stderr}")
                raise RuntimeError(f"FFmpeg exited with code {result.returncode}")
                
            print(f"[+] Successfully extracted audio track.")

        except Exception as e:
            traceback.print_exc()
            raise RuntimeError(f"Download or audio extraction failed: {e}") from e