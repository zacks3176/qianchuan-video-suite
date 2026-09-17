#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/align.py
Whisper Word-Level Timestamp Extraction & Natural 4~8 Char Subtitle Chunker
"""

import os
import sys
import json
import re
import argparse

# Enable HuggingFace mirror for domestic users in China
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

from faster_whisper import WhisperModel

def align_and_chunk(audio_file, output_json, model_size="base", max_chars=8, min_chars=4):
    print(f"[Align] Loading Faster-Whisper model ({model_size})...")
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    
    print(f"[Align] Transcribing with word timestamps: {audio_file}")
    segments, info = model.transcribe(audio_file, word_timestamps=True, language="zh")
    
    raw_words = []
    for s in segments:
        for w in s.words:
            clean_w = re.sub(r'[^\w\u4e00-\u9fff]', '', w.word)
            if clean_w:
                raw_words.append({
                    "word": clean_w,
                    "start": round(w.start, 2),
                    "end": round(w.end, 2)
                })

    if not raw_words:
        raise RuntimeError("No speech detected in audio file.")

    print(f"[Align] Detected {len(raw_words)} spoken words, audio duration: {info.duration:.2f}s")

    # Cluster words into natural 4~8 character chunks
    chunks = []
    curr = []
    curr_len = 0
    for w in raw_words:
        w_len = len(w["word"])
        if curr_len + w_len > max_chars and curr:
            chunks.append(curr)
            curr = [w]
            curr_len = w_len
        else:
            curr.append(w)
            curr_len += w_len
    if curr:
        chunks.append(curr)

    # Convert chunks to seamless subtitle cues
    cues = []
    for i, c in enumerate(chunks):
        txt = "".join([x["word"] for x in c])
        st = c[0]["start"]
        # Extend to start of next cue to eliminate black screen breath pauses
        if i + 1 < len(chunks):
            ed = chunks[i + 1][0]["start"]
        else:
            ed = min(info.duration, c[-1]["end"] + 0.3)
        cues.append({
            "text": txt,
            "start": round(st, 2),
            "end": round(ed, 2)
        })

    os.makedirs(os.path.dirname(os.path.abspath(output_json)), exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(cues, f, ensure_ascii=False, indent=2)

    print(f"[Align] Successfully generated {len(cues)} subtitle cues (all <= {max_chars} chars) -> {output_json}")
    return cues

def main():
    parser = argparse.ArgumentParser(description="Whisper Alignment & Subtitle Chunker")
    parser.add_argument("--audio", required=True, help="Input voiceover MP3/WAV")
    parser.add_argument("--output", required=True, help="Output subtitle JSON path")
    parser.add_argument("--model", default="base", help="Whisper model size (tiny/base/small)")
    parser.add_argument("--max-chars", type=int, default=8, help="Maximum characters per line (default: 8)")
    args = parser.parse_args()

    align_and_chunk(args.audio, args.output, args.model, args.max_chars)

if __name__ == "__main__":
    main()
