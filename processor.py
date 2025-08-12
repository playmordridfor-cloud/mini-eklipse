import os, subprocess, json, shutil, sys

def run(cmd, cwd=None):
    print(">>", " ".join(cmd))
    p = subprocess.run(cmd, cwd=cwd, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"Falhou: {' '.join(cmd)}")

def process_vod(job_id: str, vod_url: str):
    job_dir = os.path.join('jobs', job_id)
    status_path = os.path.join(job_dir, 'status.json')

    def save_status(d):
        with open(status_path, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, indent=2)

    try:
        save_status({'status':'running','message':'Baixando VOD...'})
        # 1) baixar VOD para a pasta do job usando python -m yt_dlp
        vod_path = os.path.join(job_dir, 'vod.mp4')
        run([sys.executable, "-m", "yt_dlp", "-f", "mp4/best", "-o", vod_path, vod_url])

        save_status({'status':'running','message':'Gerando cortes...'})
        # 2) chamar seu main.py (precisa existir na mesma pasta do projeto)
        run([sys.executable, "main.py", "--input", vod_path, "--out", job_dir, "--top-k", "8", "--clip-dur", "18", "--pre","2","--post","3"])

        save_status({'status':'running','message':'Convertendo para 9:16...'})
        clips_dir = os.path.join(job_dir, "clips")
        out916 = os.path.join(job_dir, "clips_916")
        os.makedirs(out916, exist_ok=True)
        run([sys.executable, "render_916.py", "--clips-dir", clips_dir, "--out-dir", out916, "--preset", "fortnite_preset.json"])

        # 3) zip com clipes verticais
        clips_zip = os.path.join(job_dir, "clips_916.zip")
        shutil.make_archive(os.path.splitext(clips_zip)[0], 'zip', out916)

        # 4) status final com links relativos
        samples = []
        for name in sorted(os.listdir(out916))[:3]:
            if name.lower().endswith(".mp4"):
                samples.append(f"/jobs/{job_id}/clips_916/{name}")

        compiled = os.path.join(job_dir, "compilado.mp4")
        compiled_rel = f"/jobs/{job_id}/compilado.mp4" if os.path.exists(compiled) else None

        save_status({
            'status':'done',
            'message':'Finalizado!',
            'compiled': compiled_rel,
            'clips_zip': f"/jobs/{job_id}/clips_916.zip",
            'clip_samples': samples
        })
    except Exception as e:
        save_status({'status':'error','message': str(e)})
