#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/pipeline.py
One-Click Automated Video Pipeline:
Text -> MiniMax TTS -> Whisper Alignment -> Pillow Subtitles -> FFmpeg Render
"""

import os
import sys
import argparse
from tts import synthesize_minimax
from align import align_and_chunk
from render import build_video

def run_pipeline(text, material_dir, output_mp4, voice="male-qn-qingse", bgm=None, bgm_vol=0.45):
    work_dir = os.path.join(os.path.dirname(os.path.abspath(output_mp4)), "pipeline_temp")
    os.makedirs(work_dir, exist_ok=True)

    audio_file = os.path.join(work_dir, "voice.mp3")
    subs_file = os.path.join(work_dir, "subs.json")

    print("\n>>> [Step 1/3] Synthesizing Voiceover...")
    synthesize_minimax(text, audio_file, voice_id=voice)

    print("\n>>> [Step 2/3] Aligning Subtitles with Faster-Whisper...")
    align_and_chunk(audio_file, subs_file, max_chars=8)

    print("\n>>> [Step 3/3] Assembling & Rendering Video...")
    build_video(audio_file, subs_file, material_dir, bgm, output_mp4, bgm_vol=bgm_vol)

    print(f"\n🎉 ALL DONE! Final Video: {output_mp4}\n")
    return output_mp4

def main():
    parser = argparse.ArgumentParser(description="One-Click Qianchuan Video Pipeline")
    parser.add_argument("--text", required=True, help="Copywriting script text")
    parser.add_argument("--material-dir", required=True, help="B-roll footage directory")
    parser.add_argument("--output", required=True, help="Output MP4 file path")
    parser.add_argument("--voice", default="male-qn-qingse", help="MiniMax voice ID")
    parser.add_argument("--bgm", default=None, help="BGM file path")
    parser.add_argument("--bgm-vol", type=float, default=0.45, help="BGM volume multiplier")
    args = parser.parse_args()

    run_pipeline(args.text, args.material_dir, args.output, args.voice, args.bgm, args.bgm_vol)

if __name__ == "__main__":
    main()
