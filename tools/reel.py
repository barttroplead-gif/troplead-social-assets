"""Turn post graphics into a 1080x1920 Reel with the TropLead music bed.

Usage: python3 tools/reel.py OUT.mp4 IMG [IMG ...]
One image: slow push-in. Several: slideshow with crossfades, longer hold on
first and last slide. Each 4:5 slide is centred on its own background colour.
"""
import os
import subprocess
import sys
import tempfile

from PIL import Image

FPS = 30
FADE = 0.4
HERE = os.path.dirname(os.path.abspath(__file__))


def durations(n):
    if n == 1:
        return [8.0]
    return [3.0] + [2.6] * (n - 2) + [3.6]


def bg(path):
    r, g, b = Image.open(path).convert("RGB").getpixel((6, 6))
    return f"0x{r:02X}{g:02X}{b:02X}"


def main(out, *images):
    durs = durations(len(images))
    total = sum(durs) - FADE * (len(images) - 1)
    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "bed.wav")
        subprocess.run([sys.executable, os.path.join(HERE, "music.py"), wav, f"{total + 0.5:.2f}"], check=True)

        args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
        for img, d in zip(images, durs):
            args += ["-loop", "1", "-t", f"{d}", "-i", img]
        args += ["-i", wav]

        parts = []
        for i, (img, d) in enumerate(zip(images, durs)):
            frames = int(d * FPS)
            zoom = "min(1+0.0006*on,1.04)" if len(images) == 1 else "min(1+0.0005*on,1.03)"
            parts.append(
                f"[{i}:v]scale=2160:2700,zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                f":d={frames}:s=1080x1350:fps={FPS},pad=1080:1920:0:190:color={bg(img)},setsar=1,format=yuv420p[v{i}]"
            )
        last, offset = "v0", 0.0
        for i in range(1, len(images)):
            offset += durs[i - 1] - FADE
            parts.append(f"[{last}][v{i}]xfade=transition=fade:duration={FADE}:offset={offset:.2f}[x{i}]")
            last = f"x{i}"
        a = len(images)
        parts.append(f"[{a}:a]atrim=0:{total:.2f},afade=t=out:st={total - 1.2:.2f}:d=1.2,aresample=48000[a]")

        args += ["-filter_complex", ";".join(parts), "-map", f"[{last}]", "-map", "[a]",
                 "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high", "-preset", "medium", "-crf", "20", "-r", str(FPS),
                 "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-t", f"{total:.2f}", out]
        subprocess.run(args, check=True)


if __name__ == "__main__":
    main(sys.argv[1], *sys.argv[2:])
