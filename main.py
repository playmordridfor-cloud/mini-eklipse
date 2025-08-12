import argparse
import os
import subprocess
import tempfile
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
import librosa

# ---------------------------- Utils ----------------------------

def run(cmd: List[str]) -> None:
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Comando falhou: {' '.join(cmd)}\nSTDERR:\n{proc.stderr}")

def ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)

def norm_path_for_ffmpeg(p: str) -> str:
    # Concat demuxer funciona melhor com paths com /
    return p.replace("\\", "/")

# ------------------------ Download VOD -------------------------

def download_twitch_vod(url: str, out_path: str) -> str:
    """
    Baixa o VOD da Twitch com yt-dlp para MP4.
    """
    ensure_dir(os.path.dirname(out_path) or ".")
    cmd = [
        "yt-dlp",
        "-f", "mp4/best",
        "-o", out_path,
        url,
    ]
    print("Baixando VOD com yt-dlp...")
    run(cmd)
    return out_path

# ----------------------- Áudio (RMS) ---------------------------

def extract_audio(input_video: str, wav_path: str, sr: int = 16000) -> str:
    """
    Extrai áudio mono em WAV 16kHz para análise.
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", input_video,
        "-ac", "1",
        "-ar", str(sr),
        "-vn",
        wav_path
    ]
    run(cmd)
    return wav_path

def audio_rms_series(wav_path: str, hop_length: int = 512) -> Tuple[np.ndarray, float]:
    """
    Retorna vetor de energia (RMS) e a "taxa" (fps analítico), em frames por segundo.
    """
    y, sr = librosa.load(wav_path, sr=None, mono=True)
    # Evita silencios extremos afetarem o centro
    y = librosa.util.normalize(y)
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop_length, center=True)[0]
    # Normalização robusta
    lo, hi = np.percentile(rms, [5, 95])
    rms_norm = np.clip((rms - lo) / (hi - lo + 1e-8), 0, 1)
    # Suaviza um pouco
    rms_norm = librosa.effects.hpss(rms_norm, margin=(1.0, 2.0))[0]  # separação simples para reduzir ruído
    # FPS aproximado
    fps = sr / hop_length
    return rms_norm, fps

# --------------------- Seleção de clipes -----------------------

@dataclass
class Clip:
    start: float
    end: float

def get_video_duration(input_video: str) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        input_video
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr)
    return float(proc.stdout.strip())

def suppress_overlaps(candidates: List[Clip], min_gap: float) -> List[Clip]:
    out = []
    last_end = -1e9
    for c in sorted(candidates, key=lambda x: x.start):
        if c.start >= last_end - 1e-6:
            out.append(c)
            last_end = c.end + min_gap
    return out

def pick_top_clips_from_rms(rms: np.ndarray, fps: float, total_dur: float,
                            top_k: int, clip_dur: float, pre: float, post: float,
                            min_gap: float = 3.0) -> List[Clip]:
    """
    Seleciona janelas em torno dos maiores picos do RMS.
    """
    n = len(rms)
    # Pegue mais candidatos do que o necessário e depois aplique supressão de sobreposição
    k = min(n, max(top_k * 8, top_k))  # over-sample
    peaks = np.argpartition(rms, -k)[-k:]
    peaks = peaks[np.argsort(-rms[peaks])]  # ordem decrescente

    chosen = []
    half = clip_dur / 2.0
    for p in peaks:
        center = p / fps
        s = max(0.0, center - half + (-pre))
        e = min(total_dur, center + half + post)
        chosen.append(Clip(start=s, end=e))

    # Remove sobreposições e limita a top_k
    chosen = suppress_overlaps(chosen, min_gap=min_gap)[:top_k]
    # Ordena por início
    chosen.sort(key=lambda c: c.start)
    return chosen

# -------------------------- Render -----------------------------

def cut_clip(input_video: str, out_path: str, start: float, end: float):
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start:.3f}",
        "-to", f"{end:.3f}",
        "-i", input_video,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "160k",
        out_path
    ]
    run(cmd)

def concat_clips(file_list_path: str, out_path: str):
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", file_list_path,
        "-c", "copy",
        out_path
    ]
    run(cmd)

# --------------------------- Main ------------------------------

def main():
    parser = argparse.ArgumentParser(description="IA simples (RMS) para cortes automáticos (Twitch VOD).")
    parser.add_argument("--twitch-url", type=str, help="URL do VOD da Twitch")
    parser.add_argument("--input", type=str, help="Arquivo de vídeo local (MP4/MKV etc.)")
    parser.add_argument("--out", type=str, default="out")
    parser.add_argument("--top-k", type=int, default=6)
    parser.add_argument("--clip-dur", type=float, default=20.0)
    parser.add_argument("--pre", type=float, default=3.0)
    parser.add_argument("--post", type=float, default=3.0)
    parser.add_argument("--min-gap", type=float, default=3.0, help="gap mínimo entre clipes após supressão")
    args = parser.parse_args()

    ensure_dir(args.out)
    clips_dir = os.path.join(args.out, "clips")
    ensure_dir(clips_dir)

    # 1) Baixar ou usar arquivo local
    if args.twitch_url:
        vod_path = os.path.join(args.out, "vod.mp4")
        download_twitch_vod(args.twitch_url, vod_path)
    elif args.input:
        vod_path = args.input
    else:
        raise SystemExit("Passe --twitch-url ou --input.")

    # 2) Duração total
    total_dur = get_video_duration(vod_path)

    # 3) Áudio → RMS
    with tempfile.TemporaryDirectory() as td:
        wav_path = os.path.join(td, "audio.wav")
        extract_audio(vod_path, wav_path, sr=16000)
        rms, afps = audio_rms_series(wav_path, hop_length=512)

    # 4) Seleciona top-K clipes com base no RMS
    clips = pick_top_clips_from_rms(
        rms=rms, fps=afps, total_dur=total_dur,
        top_k=args.top_k, clip_dur=args.clip_dur,
        pre=args.pre, post=args.post, min_gap=args.min_gap
    )

    if not clips:
        print("Nenhum clipe selecionado. Tente diminuir --clip-dur ou --top-k, e verifique se há áudio no VOD.")
        return

    # 5) Render clipes individuais e cria lista p/ concat
    list_file = os.path.join(args.out, "clips.txt")
    with open(list_file, "w", encoding="utf-8") as f:
        for idx, c in enumerate(clips, 1):
            out_clip = os.path.join(clips_dir, f"clip_{idx:03d}.mp4")
            print(f"Cortando clip {idx}: {c.start:.2f}s -> {c.end:.2f}s")
            cut_clip(vod_path, out_clip, c.start, c.end)
            f.write(f"file '{norm_path_for_ffmpeg(out_clip)}'\n")

    # 6) Compilado
    compilado = os.path.join(args.out, "compilado.mp4")
    print("Concatenando compilado...")
    concat_clips(list_file, compilado)
    print(f"Pronto! Veja os clipes em: {clips_dir}\nCompilado: {compilado}")

if __name__ == "__main__":
    main()
