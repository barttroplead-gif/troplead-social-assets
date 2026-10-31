"""Turn post graphics into a 1080x1920 Reel with the TropLead music bed.

Usage: python3 tools/reel.py OUT.mp4 [--music N] IMG [IMG ...]
One image: slow push-in. Several: slideshow with crossfades, longer hold on
first and last slide. 9:16 images (1080x1920) fill the frame; 4:5 ones are
centred on their background colour. --music picks one of the beds in music.py.
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


def main(out, *images, music=0):
    durs = durations(len(images))
    total = sum(durs) - FADE * (len(images) - 1)
    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "bed.wav")
        subprocess.run([sys.executable, os.path.join(HERE, "music.py"), wav, f"{total + 0.5:.2f}", str(music)], check=True)

        args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
        for img, d in zip(images, durs):
            args += ["-loop", "1", "-t", f"{d}", "-i", img]
        args += ["-i", wav]

        parts = []
        for i, (img, d) in enumerate(zip(images, durs)):
            frames = int(d * FPS)
            zoom = "min(1+0.0006*on,1.04)" if len(images) == 1 else "min(1+0.0005*on,1.03)"
            w, h = Image.open(img).size
            if h / w > 1.7:  # native 9:16, no padding
                size, pad = "1080x1920", ""
                scale = "scale=2160:3840"
            else:
                size, pad = "1080x1350", f",pad=1080:1920:0:190:color={bg(img)}"
                scale = "scale=2160:2700"
            parts.append(
                f"[{i}:v]{scale},zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                f":d={frames}:s={size}:fps={FPS}{pad},setsar=1,format=yuv420p[v{i}]"
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
    argv = sys.argv[2:]
    music = 0
    if argv[:1] == ["--music"]:
        music, argv = int(argv[1]), argv[2:]
    main(sys.argv[1], *argv, music=music)
