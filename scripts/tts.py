#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/tts.py
MiniMax Text-to-Speech API Client
"""

import os
import sys
import json
import argparse
import requests
import subprocess

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.json")
ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")

def load_env(env_path):
    if not os.path.exists(env_path):
        return {}
    res = {}
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            res[k.strip()] = v.strip().strip("'\"")
    return res

def synthesize_minimax(text, output_file, voice_id=None, speed=1.0):
    env_vars = load_env(ENV_PATH)
    api_key = env_vars.get("MINIMAX_API_KEY") or os.environ.get("MINIMAX_API_KEY")
    
    # Try reading from config.json
    config = {}
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception:
            pass

    if not api_key:
        api_key = config.get("minimax_api_key")
        
    chosen_voice = voice_id or config.get("voice_id", "male-qn-qingse")
    model = config.get("model", "speech-2.8-hd")
    base_url = env_vars.get("MINIMAX_BASE_URL") or config.get("base_url", "https://api.minimaxi.com")

    # Optional: fallback to local script if specified by environment
    ps_fallback = os.environ.get("MINIMAX_PS_SCRIPT")
    if not api_key and ps_fallback and os.path.exists(ps_fallback):
        print("[TTS] Using local PowerShell MiniMax caller...")
        cmd = [
            "powershell", "-ExecutionPolicy", "Bypass",
            "-File", ps_fallback,
            "-Text", text,
            "-VoiceId", chosen_voice,
            "-OutFile", output_file
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and os.path.exists(output_file):
            print(f"[TTS] Successfully generated: {output_file}")
            return output_file
        else:
            raise RuntimeError(f"PowerShell TTS failed: {res.stderr}")

    if not api_key:
        raise ValueError("Missing MINIMAX_API_KEY. Please configure it in .env or config.json.")

    endpoint = f"{base_url.rstrip('/')}/v1/t2a_v2"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    def request_tts(v_id):
        payload = {
            "model": model,
            "text": text.strip(),
            "stream": False,
            "language_boost": "Chinese",
            "output_format": "hex",
            "voice_setting": {
                "voice_id": v_id,
                "speed": float(speed),
                "vol": 1.0,
                "pitch": 0
            },
            "audio_setting": {
                "sample_rate": 32000,
                "bitrate": 128000,
                "format": "mp3",
                "channel": 1,
                "force_cbr": True
            }
        }
        return requests.post(endpoint, headers=headers, json=payload, timeout=60)

    print(f"[TTS] Requesting MiniMax TTS (voice={chosen_voice})...")
    resp = request_tts(chosen_voice)
    if resp.status_code == 200:
        data = resp.json()
        base_resp = data.get("base_resp", {})
        # If private voice not found or permission denied, fallback to system voice
        if base_resp.get("status_code") != 0 and chosen_voice != "male-qn-qingse":
            print(f"[TTS] Voice '{chosen_voice}' failed ({base_resp.get('status_msg')}), falling back to public voice 'male-qn-qingse'...")
            chosen_voice = "male-qn-qingse"
            resp = request_tts(chosen_voice)

    if resp.status_code != 200:
        raise RuntimeError(f"MiniMax API returned error {resp.status_code}: {resp.text}")

    data = resp.json()
    base_resp = data.get("base_resp", {})
    if base_resp.get("status_code", 0) != 0:
        raise RuntimeError(f"MiniMax Error {base_resp.get('status_code')}: {base_resp.get('status_msg')}")

    hex_audio = data.get("data", {}).get("audio", "")
    if not hex_audio:
        raise RuntimeError("MiniMax returned empty audio payload.")

    audio_bytes = bytes.fromhex(hex_audio.strip())
    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
    with open(output_file, "wb") as f:
        f.write(audio_bytes)

    print(f"[TTS] Audio saved to: {output_file} ({len(audio_bytes)} bytes)")
    return output_file

def main():
    parser = argparse.ArgumentParser(description="MiniMax TTS Tool")
    parser.add_argument("--text", required=True, help="Text to synthesize")
    parser.add_argument("--output", required=True, help="Output MP3 file path")
    parser.add_argument("--voice", default="male-qn-qingse", help="Voice ID")
    parser.add_argument("--speed", type=float, default=1.0, help="Speech speed multiplier")
    args = parser.parse_args()

    synthesize_minimax(args.text, args.output, args.voice, args.speed)

if __name__ == "__main__":
    main()
