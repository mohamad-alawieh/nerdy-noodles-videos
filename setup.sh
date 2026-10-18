#!/usr/bin/env bash
# One-time setup for a fresh session: drawing, video and voice tools.
set -e
cd "$(dirname "$0")"
pip install --break-system-packages -q pycairo numpy pillow kokoro-onnx soundfile pyworld librosa sherpa-onnx uharfbuzz 2>&1 | grep -v -i "warning" || true
which ffmpeg >/dev/null || { echo "ffmpeg missing"; exit 1; }
fc-list | grep -qi poppins || echo "WARNING: Poppins font not found; text will use a fallback font"
mkdir -p .tts
BASE=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0
[ -s .tts/kokoro-v1.0.int8.onnx ] || curl -sSL -o .tts/kokoro-v1.0.int8.onnx $BASE/kokoro-v1.0.int8.onnx
[ -s .tts/voices-v1.0.bin ] || curl -sSL -o .tts/voices-v1.0.bin $BASE/voices-v1.0.bin
# Arabic singing/speaking voice (Piper "kareem", via the sherpa-onnx model releases on GitHub)
AR=vits-piper-ar_JO-kareem-medium
[ -s .tts/$AR/ar_JO-kareem-medium.onnx ] || curl -sSL https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/$AR.tar.bz2 | tar xj -C .tts
# Lyrics checker (Whisper small, int8 parts only) used by engine/check_lyrics.py
WS=sherpa-onnx-whisper-small
[ -s .tts/$WS/small-decoder.int8.onnx ] || curl -sSL https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/$WS.tar.bz2 | tar xj -C .tts --wildcards "$WS/*int8.onnx" "$WS/small-tokens.txt"
python3 -c "import cairo, kokoro_onnx, pyworld, librosa, sherpa_onnx, uharfbuzz; print('setup ok')"
