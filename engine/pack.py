"""Pack a finished episode the way Ep03 was packed: script_epNN.md, subtitles_epNN.ass, keyframes/ (one per shot,
taken from the FINAL video) and storyboard_epNN.jpg.

    engine/.venv/bin/python engine/pack.py episodes/ep05_the_chain_in_the_bones/ep05.py ep05 GhoulGate_Ep05_FINAL.mp4
"""
import os, re, shutil, subprocess, sys
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

PY = sys.executable
FF = imageio_ffmpeg.get_ffmpeg_exe()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(script, tag, final):
    epdir = os.path.dirname(os.path.abspath(script))
    video = os.path.join(epdir, final)
    assert os.path.exists(video), video
    info = subprocess.run([PY, script, '--info'], capture_output=True, text=True, check=True).stdout.splitlines()
    shots = []
    for ln in info[1:]:
        m = re.match(r'\s*([\d.]+)\s+([\d.]+)\s+(\S+)', ln)
        if m:
            shots.append((float(m.group(1)), float(m.group(2)), m.group(3)))
    assert shots, 'no shots parsed'
    subprocess.run([PY, script, '--export-script', os.path.join(epdir, f'script_{tag}.md')], check=True, capture_output=True)
    shutil.copy(os.path.join(epdir, 'build', 'subs2.ass'), os.path.join(epdir, f'subtitles_{tag}.ass'))
    kd = os.path.join(epdir, 'keyframes')
    shutil.rmtree(kd, ignore_errors=True); os.makedirs(kd)
    names = []
    for i, (s, d, n) in enumerate(shots, 1):
        t = s + d / 2
        fn = os.path.join(kd, f'{i:02d}_{int(t // 60)}m{int(t % 60):02d}s_{n.strip("<>")}.png')
        subprocess.run([FF, '-y', '-v', 'error', '-ss', f'{t:.2f}', '-i', video, '-frames:v', '1', '-vf', 'scale=640:360', fn], check=True)
        names.append(fn)
    cols, tw, th, lab = 8, 320, 180, 16
    rows = -(-len(names) // cols)
    sb = Image.new('RGB', (cols * tw, rows * (th + lab)), (16, 16, 20))
    d = ImageDraw.Draw(sb)
    font = ImageFont.load_default()
    for i, fn in enumerate(names):
        x, y = (i % cols) * tw, (i // cols) * (th + lab)
        sb.paste(Image.open(fn).resize((tw, th)), (x, y + lab))
        d.text((x + 4, y + 2), os.path.basename(fn)[:-4], fill=(230, 230, 230), font=font)
    sb.save(os.path.join(epdir, f'storyboard_{tag}.jpg'), quality=88)
    print(f'{tag}: {len(shots)} shots packed')


if __name__ == '__main__':
    main(*sys.argv[1:4])
