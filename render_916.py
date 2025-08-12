import argparse, os, json, subprocess

def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr)

def make_916(in_path, out_path, wm_text=None):
    vf = ["scale=-2:1920","crop=1080:1920"]
    filter_str = ",".join(vf)
    cmd = ["ffmpeg","-y","-i", in_path,"-vf", filter_str,"-c:v","libx264","-preset","veryfast","-crf","20","-c:a","aac","-b:a","160k", out_path]
    run(cmd)

def main():
    ap = argparse.ArgumentParser(description="Render clips para 9:16 (vertical)")
    ap.add_argument("--clips-dir", default="out/clips")
    ap.add_argument("--out-dir", default="out/clips_916")
    ap.add_argument("--preset", default="fortnite_preset.json")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    preset = {}
    if os.path.exists(args.preset):
        with open(args.preset, "r", encoding="utf-8") as f:
            preset = json.load(f)
    wm_text = None
    if preset.get("render_916", {}).get("watermark", {}).get("enable"):
        wm_text = preset["render_916"]["watermark"]["text"]

    clips = [c for c in os.listdir(args.clips_dir) if c.lower().endswith(".mp4")]
    clips.sort()
    for c in clips:
        in_p = os.path.join(args.clips_dir, c)
        out_p = os.path.join(args.out_dir, c.replace(".mp4", "_916.mp4"))
        print(">>", c)
        make_916(in_p, out_p, wm_text=wm_text)

    print("Pronto! Clips 9:16 em:", args.out_dir)

if __name__ == "__main__":
    main()
