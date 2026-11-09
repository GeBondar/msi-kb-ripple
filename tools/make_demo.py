"""Render docs/demo.gif: the real ripple engine fed with simulated typing,
drawn on a top-down model of the Sword 17 HX keyboard.

    python tools/make_demo.py
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import ripple as R  # noqa: E402

U = 44                      # px per key unit
PAD = 22
SIM_HZ = R.FPS              # smoothing constants are per-frame at this rate
STEP = 2                    # keep every 2nd sim frame -> 22.5 fps gif
SECONDS = 9.0
QUIET_TAIL = 1.4            # no presses at the end, so the loop restarts from calm water

WIDE = {(0x0E, False): 1.6, (0x0F, False): 1.25, (0x3A, False): 1.5, (0x2A, False): 2.0,
        (0x1C, False): 1.45, (0x36, False): 1.8, (0x39, False): 5.0, (0x1D, False): 1.2,
        (0x52, False): 1.0}

# one rectangle per physical key (drop extended aliases that share a position)
KEYS, seen = [], set()
for key, (x, y) in R.KEYPOS.items():
    if (x, y) in seen or key == (0x1D, True):
        continue
    seen.add((x, y))
    numpad = x >= 15.5 and y > 0
    KEYS.append((key, x, y, WIDE.get(key, 0.9), 0.72 if numpad else 0.84))

W = int(19.0 * U + 2 * PAD)
H = int(5.9 * U + 2 * PAD)
NEAR = {k[0]: sorted(R.ZONES, key=lambda z: math.dist(R.ZONES[z], (k[1], k[2])))[:3] for k in KEYS}


def led_colour(key, x, y, frame):
    """Blend the 3 nearest zones, like light leaking under neighbouring caps."""
    acc, wsum = [0.0, 0.0, 0.0], 0.0
    for z in NEAR[key]:
        w = math.exp(-(math.dist(R.ZONES[z], (x, y)) / 1.1) ** 2) + 1e-3
        for i in range(3):
            acc[i] += frame[z][i] * w
        wsum += w
    return tuple(255 * (min(255, a / wsum) / 255) ** 0.6 for a in acc)   # gamma: LEDs look brighter than raw values


def draw(frame, pressed):
    glow = Image.new("RGB", (W, H), (6, 7, 10))
    g = ImageDraw.Draw(glow)
    caps = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    c = ImageDraw.Draw(caps)
    for key, x, y, kw, kh in KEYS:
        col = led_colour(key, x, y, frame)
        x0, y0 = PAD + (x - kw / 2) * U + U / 2, PAD + (y - kh / 2) * U + U / 2
        x1, y1 = x0 + kw * U, y0 + kh * U
        g.rounded_rectangle([x0 - 4, y0 - 4, x1 + 4, y1 + 4], 9, fill=tuple(int(v * 0.8) for v in col))
        inset = 3 if key in pressed else 0
        c.rounded_rectangle([x0 + inset, y0 + inset, x1 - inset, y1 - inset], 7,
                            fill=(17, 18, 23, 255), outline=tuple(int(v) for v in col) + (255,), width=2)
        c.rounded_rectangle([x0 + 9 + inset, y0 + 9 + inset, x0 + 15, y0 + 13], 2,
                            fill=tuple(int(v * 0.9) for v in col) + (255,))   # tiny "legend" light
    img = glow.filter(ImageFilter.GaussianBlur(9))
    img.paste(caps, (0, 0), caps)
    return img


def main():
    presses, t = [], 0.4
    for key, delay in R.demo_presses(seed=3):
        t += delay
        if t > SECONDS - QUIET_TAIL:
            break
        presses.append((t, key))

    state = {z: tuple(v / 255 for v in R.BG) for z in R.ZONES}
    active, frames, n, pi = [], [], 0, 0
    for i in range(int(SECONDS * SIM_HZ)):
        now = i / SIM_HZ
        while pi < len(presses) and presses[pi][0] <= now:
            pt, key = presses[pi]
            active.append((R.KEYPOS.get(key, (7.0, 3.0)), pt, R.drop_colour(n)))
            n += 1; pi += 1
        active = [a for a in active if now - a[1] < R.LIFE]
        frame = R.smooth(state, R.render(active, now))
        if i % STEP == 0:
            pressed = {k for pt, k in presses if 0 <= now - pt < 0.12}
            frames.append(draw(frame, pressed).quantize(colors=48, method=Image.Quantize.MEDIANCUT))

    out = os.path.join(ROOT, "docs", "demo.gif")
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=int(1000 * STEP / SIM_HZ),
                   loop=0, optimize=True, disposal=1)
    print(f"{out}: {len(frames)} frames, {os.path.getsize(out) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
