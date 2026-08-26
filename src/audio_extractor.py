from pathlib import Path
import yt_dlp
import traceback
import subprocess

class AudioExtractor:
    @staticmethod
    def extract_audio(video_url: str, output_audio_path: Path, output_video_path: Path):
        print(f"[-] Step 1: Downloading stream from YouTube: {video_url}")
        output_video_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Clean up any leftover partial files to avoid format/container conflicts
        if output_video_path.exists():
            output_video_path.unlink()

        ydl_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": str(output_video_path.with_suffix('')), # yt-dlp adds extension automatically based on format
            "merge_output_format": "mp4",
            "quiet": False,
            "no_warnings": True,
        }
        
        try:
            # 1. Download video forcing MP4 container
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            
            # Ensure output_video_path points to the actual generated file if extension adjusted
            actual_video_file = output_video_path.with_suffix('.mp4')
            if not actual_video_file.exists():
                # Fallback search in output directory
                files = list(output_video_path.parent.glob("temp_video.*"))
                if files:
                    actual_video_file = files[0]
            
            print(f"[+] Successfully downloaded video to {actual_video_file}")
            
            # 2. Extract audio into temp_audio.wav using ffmpeg (letting stderr print if error occurs)
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