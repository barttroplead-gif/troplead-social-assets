"""Original, royalty-free background bed for TropLead Reels (synthesised, no samples).

Usage: python3 tools/music.py OUT.wav SECONDS
Warm lo-fi/corporate groove: 96 BPM, Fmaj7–G6–Em7–Am7, soft pad, pluck arpeggio,
sub bass, gentle kick + hats, pumped by the kick.
"""
import sys
import wave

import numpy as np

SR = 44100
BPM = 96
BEAT = 60 / BPM
BAR = 4 * BEAT
CHORDS = [  # MIDI notes
    [53, 57, 60, 64],  # Fmaj7
    [55, 59, 62, 64],  # G6
    [52, 55, 59, 62],  # Em7
    [57, 60, 64, 67],  # Am7
]
BASS = [41, 43, 40, 45]


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):  # one-pole; fine for a few seconds of audio
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def saw(f, t):
    return 2 * ((f * t) % 1.0) - 1


def env(n, attack, release):
    e = np.ones(n)
    a, r = int(attack * SR), int(release * SR)
    if a:
        e[:a] = np.linspace(0, 1, a)
    if r:
        e[-r:] *= np.linspace(1, 0, r)
    return e


def render(seconds):
    n = int(seconds * SR)
    out = np.zeros((n, 2))
    t_bar = np.arange(int(BAR * SR)) / SR
    bars = int(np.ceil(seconds / BAR))
    rng = np.random.default_rng(7)

    for b in range(bars):
        start = int(b * BAR * SR)
        chord, bass = CHORDS[b % 4], BASS[b % 4]
        seg = len(t_bar)
        # pad: detuned saws, filtered, slow attack
        pad = sum(saw(hz(m) * d, t_bar) for m in chord for d in (0.997, 1.003))
        pad = lowpass(pad / 8, 900) * env(seg, 0.25, 0.25) * 0.75
        # sub bass on 1 and the "and" of 3
        bl = np.zeros(seg)
        for pos in (0, 2.5):
            s = int(pos * BEAT * SR)
            ln = int(1.2 * BEAT * SR)
            tt = np.arange(ln) / SR
            note = np.sin(2 * np.pi * hz(bass) * tt) * np.exp(-tt * 2.2)
            bl[s:s + ln] += note[: seg - s]
        # pluck arpeggio, 8th notes
        arp = np.zeros((seg, 2))
        pattern = [0, 2, 1, 3, 2, 1, 3, 2]
        for k, idx in enumerate(pattern):
            s = int(k * BEAT / 2 * SR)
            ln = int(0.45 * SR)
            tt = np.arange(ln) / SR
            f = hz(chord[idx] + 12)
            tone = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt)) * np.exp(-tt * 7)
            pan = 0.35 + 0.3 * (k % 2)
            e = min(seg, s + ln)
            arp[s:e, 0] += tone[: e - s] * (1 - pan)
            arp[s:e, 1] += tone[: e - s] * pan
        # drums
        dr = np.zeros(seg)
        pump = np.ones(seg)
        for beat in range(4):
            s = int(beat * BEAT * SR)
            if beat in (0, 2):
                ln = int(0.35 * SR)
                tt = np.arange(ln) / SR
                kick = np.sin(2 * np.pi * (45 + 90 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 9)
                dr[s:s + ln] += kick * 0.45
                pl = int(0.3 * SR)
                pump[s:s + pl] = np.minimum(pump[s:s + pl], 0.65 + 0.35 * np.linspace(0, 1, pl))
            for half in (0, 1):  # hats on 8ths
                hs = s + int(half * BEAT / 2 * SR)
                ln = int(0.05 * SR)
                noise = rng.standard_normal(ln)
                hat = (noise - lowpass(noise, 6000)) * np.exp(-np.arange(ln) / SR * 80)
                dr[hs:hs + ln] += hat * (0.18 if half else 0.1)
            if beat in (1, 3):  # soft clap
                ln = int(0.15 * SR)
                noise = rng.standard_normal(ln)
                clap = lowpass(noise, 2500) * np.exp(-np.arange(ln) / SR * 25)
                dr[s:s + ln] += clap * 0.25
        mono = (pad + bl * 0.35) * pump + dr
        stereo = np.stack([mono, mono], axis=1) + arp * 0.4 * pump[:, None]
        e = min(n, start + seg)
        out[start:e] += stereo[: e - start]

    fade = int(1.5 * SR)
    out[-fade:] *= np.linspace(1, 0, fade)[:, None]
    out[: int(0.05 * SR)] *= np.linspace(0, 1, int(0.05 * SR))[:, None]
    out /= np.max(np.abs(out)) / 0.8
    return out


def main(path, seconds):
    audio = (render(float(seconds)) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(audio.tobytes())


if __name__ == "__main__":
    main(*sys.argv[1:3])
