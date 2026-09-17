#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/render.py
Industrial-grade Video Assembler & Pillow Subtitle Overlay Engine
"""

import os
import sys
import json
import argparse
import subprocess
from PIL import Image, ImageDraw, ImageFont

# Find system font (default Windows YaHei Bold)
def find_font():
    candidates = [
        r"C:\Windows\Fonts\msyhbd.ttc",
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None

def render_subtitle_image(text: str, out_png: str, font_path, width=720, height=1280, font_sz=68, y_pos=970):
    im = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    if not text.strip():
        im.save(out_png)
        return out_png

    draw = ImageDraw.Draw(im)
    try:
        f = ImageFont.truetype(font_path, font_sz)
    except Exception:
        f = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=f)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]

    x = (width - w) // 2
    y = y_pos - h // 2

    # Drop shadow (+3, +3)
    draw.text((x + 3, y + 3), text, font=f, fill=(0, 0, 0, 220))
    # 68px Bright Yellow (#FFE000) with 6px Black Stroke
    draw.text((x, y), text, font=f, fill=(255, 224, 0, 255), stroke_width=6, stroke_fill=(0, 0, 0, 255))

    im.save(out_png)
    return out_png

def get_media_duration(path):
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", path]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0:
        data = json.loads(res.stdout)
        return float(data.get("format", {}).get("duration", 0))
    return 0.0

def build_video(audio_path, subs_path, material_dir, bgm_path, output_mp4, bgm_vol=0.45):
    font_path = find_font()
    if not font_path:
        raise RuntimeError("No suitable bold Chinese font found on system.")

    audio_dur = get_media_duration(audio_path)
    if audio_dur <= 0:
        raise RuntimeError(f"Invalid audio duration: {audio_path}")

    with open(subs_path, "r", encoding="utf-8") as f:
        subs = json.load(f)

    print(f"[Render] Audio Duration: {audio_dur:.2f}s | Total Subtitles: {len(subs)}")

    # Collect available materials
    valid_exts = (".mp4", ".mov", ".mkv", ".png", ".jpg", ".jpeg")
    materials = []
    for f in os.listdir(material_dir):
        if f.lower().endswith(valid_exts):
            materials.append(os.path.join(material_dir, f))

    if not materials:
        raise RuntimeError(f"No video or image materials found in: {material_dir}")

    temp_dir = os.path.join(os.path.dirname(os.path.abspath(output_mp4)), "render_temp")
    os.makedirs(temp_dir, exist_ok=True)

    # Design shot sequence: 2.5s ~ 4.0s per shot
    shot_durs = []
    accum = 0.0
    while accum < audio_dur:
        rem = audio_dur - accum
        if rem <= 4.0:
            shot_durs.append(rem)
            break
        elif rem <= 5.5:
            shot_durs.append(rem / 2.0)
            shot_durs.append(rem / 2.0)
            break
        else:
            sd = 3.2
            shot_durs.append(sd)
            accum += sd

    shots = []
    curr_time = 0.0
    for i, dur in enumerate(shot_durs):
        mat = materials[i % len(materials)]
        mat_dur = get_media_duration(mat)
        src_start = 0.5 if mat_dur > dur + 1.0 else 0.0
        shots.append({
            "idx": i + 1,
            "video": mat,
            "src_start": src_start,
            "start": round(curr_time, 2),
            "end": round(curr_time + dur, 2),
            "dur": round(dur, 2),
            "subtitles": []
        })
        curr_time += dur

    # Assign subtitles to overlapping shots
    for sub in subs:
        sub_st = sub["start"]
        sub_ed = sub["end"]
        for s in shots:
            if max(s["start"], sub_st) < min(s["end"], sub_ed):
                s["subtitles"].append(sub)

    # Render each shot with Pillow overlay
    shot_files = []
    for s in shots:
        s_idx = s["idx"]
        dur = s["dur"]
        v_src = s["video"]
        src_st = s["src_start"]
        shot_out = os.path.join(temp_dir, f"shot_{s_idx:02d}.mp4")
        shot_files.append(shot_out)

        is_img = v_src.lower().endswith((".png", ".jpg", ".jpeg"))
        if is_img:
            input_args = ["-loop", "1", "-t", str(dur), "-i", v_src]
        else:
            input_args = ["-ss", str(src_st), "-t", str(dur), "-i", v_src]

        filter_complex = "[0:v]scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,setsar=1[base]"
        last_v = "[base]"

        for i_sub, sub in enumerate(s["subtitles"]):
            ov_path = os.path.join(temp_dir, f"shot_{s_idx:02d}_sub_{i_sub}.png")
            render_subtitle_image(sub["text"], ov_path, font_path)
            input_args.extend(["-i", ov_path])
            sub_rel_st = max(0.0, round(sub["start"] - s["start"], 3))
            sub_rel_ed = min(dur, round(sub["end"] - s["start"], 3))
            next_v = f"[v{i_sub}]"
            input_idx = i_sub + 1
            filter_complex += f";{last_v}[{input_idx}:v]overlay=0:0:enable='between(t,{sub_rel_st},{sub_rel_ed})'{next_v}"
            last_v = next_v

        cmd = [
            "ffmpeg", "-y",
            *input_args,
            "-filter_complex", filter_complex,
            "-map", last_v,
            "-t", str(dur),
            "-r", "30",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
            "-an",
            shot_out
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"Error rendering shot {s_idx}: {res.stderr[-300:]}")
        print(f"  [Shot {s_idx:02d}] {os.path.basename(v_src)} ({dur:.2f}s, {len(s['subtitles'])} subs)")

    # Concat raw video
    concat_txt = os.path.join(temp_dir, "concat.txt")
    with open(concat_txt, "w", encoding="utf-8") as f:
        for sf in shot_files:
            clean_p = sf.replace("\\", "/")
            f.write(f"file '{clean_p}'\n")

    concat_raw = os.path.join(temp_dir, "concat_raw.mp4")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_txt, "-c", "copy", concat_raw], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Audio Muxing
    os.makedirs(os.path.dirname(os.path.abspath(output_mp4)), exist_ok=True)
    if bgm_path and os.path.exists(bgm_path):
        amix_filter = f"[1:a]volume=1.0[vce];[2:a]volume={bgm_vol}[bgm];[vce][bgm]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,alimiter=limit=0.95[aout]"
        cmd_mux = [
            "ffmpeg", "-y",
            "-i", concat_raw,
            "-i", audio_path,
            "-stream_loop", "-1", "-i", bgm_path,
            "-filter_complex", amix_filter,
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            output_mp4
        ]
    else:
        cmd_mux = [
            "ffmpeg", "-y",
            "-i", concat_raw,
            "-i", audio_path,
            "-map", "0:v", "-map", "1:a",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            output_mp4
        ]

    subprocess.run(cmd_mux, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"[Render] ✅ Success! Exported to: {output_mp4}")
    return output_mp4

def main():
    parser = argparse.ArgumentParser(description="Video Assembler & Renderer")
    parser.add_argument("--audio", required=True, help="Input voiceover MP3")
    parser.add_argument("--subs", required=True, help="Input subtitle JSON")
    parser.add_argument("--material-dir", required=True, help="Directory containing B-roll videos/images")
    parser.add_argument("--bgm", default=None, help="Path to BGM file")
    parser.add_argument("--bgm-vol", type=float, default=0.45, help="BGM volume multiplier (default 0.45)")
    parser.add_argument("--output", required=True, help="Output MP4 file path")
    args = parser.parse_args()

    build_video(args.audio, args.subs, args.material_dir, args.bgm, args.output, args.bgm_vol)

if __name__ == "__main__":
    main()
