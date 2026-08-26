# QuestOne • AI Audio-Visual Dialogue Frame Locator

An intelligent audio-visual pipeline that downloads video streams, performs high-precision speech-to-text with OpenAI Whisper, fuzzy-matches target dialogues using RapidFuzz, and extracts sharpness-optimized video frames using OpenCV.

---

## 🚀 Getting Started

### 1. Requirements & Dependencies
Ensure you have the required packages installed:
```bash
pip install -r requirements.txt
```

*Prerequisite*: [FFmpeg](https://ffmpeg.org/) installed and available in your system `PATH`.

---

## 💻 Running the Web Frontend (React + Tailwind)

Launch the integrated web server:
```bash
python app.py
```
Open your browser and navigate to:
👉 **`http://localhost:5000`**

### Features:
- 🎨 **React 18 + Tailwind CSS** dark-mode interface.
- ⚡ Real-time pipeline step tracker (Download -> Whisper ASR -> Frame Sharpness -> Result).
- 📋 **Expected Format Output Box** with 1-click clipboard copy.
- 🖼️ **Extracted Frame Viewer** with sharpness metric badge and direct PNG download.
- 🎯 Quick presets for fast testing.

---

## ⌨️ Running the CLI

You can also run the command-line interface:
```bash
python main.py
```

### Standard Output Format:
```text
Timestamp : HH:MM:SS.sss
Frame : <Frame number>
Text : "My mind rebels at stagnation"
```