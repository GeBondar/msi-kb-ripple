"""Hearth fire for MSI MysticLight MS-1603 (24 zones).

Glowing coals along the bottom rows, flame tongues licking upward, the odd
spark drifting to the top. Typing stokes the fire: each key press feeds it,
with a flare right where you pressed.

    python fire.py          # fire reacts to typing
    python fire.py --calm   # just the fire, ignores the keyboard
"""
import ctypes
import math
import random
import sys
import threading
import time

import ripple as R          # zone map, key positions, keyboard hook, HID helpers

# ---------- look & feel ----------
FLAME = 4.6                # base flame height, in key rows above the bottom
LICK = 2.2                  # how much tongues rise and fall (rows)
SWAY = 2.0                  # tongue speed (higher = livelier)
GUST = 0.9                  # slow whole-fire surges (rows)
COAL = 1.0                 # minimum heat of the bottom rows (embers never go out)
FLICKER = 0.2               # fast shimmer on top of everything
SPARKS = 2.5                # sparks per second
STOKE = 1.1                 # extra flame height from one key press (rows)
STOKE_DECAY = 1.2           # seconds for a stoke to burn down
BRIGHT = 1.0                # overall brightness
ATTACK, RELEASE = 0.5, 0.35
FPS = 45

BOTTOM = 5.2                # y of the hearth floor in key rows (keyboard rows go 0..5)

# black -> deep red -> orange -> yellow -> pale gold
# mostly pure red and pure yellow, only a short orange transition between them
RAMP = [(0.00, (80, 0, 0)), (0.18, (255, 0, 0)), (0.46, (255, 8, 0)),
        (0.58, (255, 120, 0)), (0.68, (255, 210, 0)), (0.88, (255, 235, 20)), (1.00, (255, 255, 120))]
HEAT = 0.12                # added to every zone's heat: shifts the whole fire toward yellow-white


def ramp(h):
    h = max(0.0, min(1.0, h))
    for (h0, c0), (h1, c1) in zip(RAMP, RAMP[1:]):
        if h <= h1:
            t = (h - h0) / (h1 - h0)
            return tuple(a + (b - a) * t for a, b in zip(c0, c1))
    return RAMP[-1][1]


class Fire:
    def __init__(self, seed=None):
        rnd = random.Random(seed)
        # a few incommensurate waves per column = organic, never-repeating tongues
        self.waves = [(rnd.uniform(0.5, 1.2), rnd.uniform(0.3, 0.9), rnd.uniform(0, 6.28)) for _ in range(4)]
        self.zone_phase = {z: rnd.uniform(0, 6.28) for z in R.ZONES}
        self.sparks = []        # (x, y0, t0, speed)
        self.stokes = []        # (x, y, t0)
        self.rnd = rnd

    def tongue(self, x, t):
        v = 0.0
        for kx, kt, ph in self.waves:
            v += math.sin(x * kx + t * kt * SWAY * 3.0 + ph)
        return v / len(self.waves)      # -1..1

    def stoke(self, x, y, t):
        self.stokes.append((x, y, t))

    def heat(self, now):
        self.stokes = [s for s in self.stokes if now - s[2] < STOKE_DECAY * 2]
        if self.rnd.random() < SPARKS / FPS:
            self.sparks.append((self.rnd.uniform(0.5, 17.5), BOTTOM - 1.0, now, self.rnd.uniform(2.5, 4.5)))
        self.sparks = [s for s in self.sparks if s[1] - (now - s[2]) * s[3] > -1.0]

        boost = sum(STOKE * math.exp(-(now - t0) / STOKE_DECAY) for _, _, t0 in self.stokes)
        out = {}
        for z, (x, y) in R.ZONES.items():
            above = BOTTOM - y                                   # rows above the hearth floor
            gust = GUST * math.sin(now * 0.9) * math.sin(now * 0.37 + 1.0)
            height = FLAME + LICK * self.tongue(x, now) + gust + min(boost, 2.5)
            h = 1.0 - above / max(height, 0.3)                   # 1 at the floor, 0 at the flame tip
            h = max(COAL * max(0.0, 1.0 - above / 2.2), h)       # coals stay lit
            h += FLICKER * math.sin(now * 11.0 + self.zone_phase[z]) * math.sin(now * 7.3 + 2 * self.zone_phase[z])
            for sx, sy, t0 in self.stokes:                      # local flare where you typed
                a = math.exp(-(now - t0) / 0.5)
                h += 0.55 * a * math.exp(-(((x - sx) / 2.0) ** 2 + ((y - sy) / 1.6) ** 2))
            for sx, sy0, t0, sp in self.sparks:                  # rising sparks
                sy = sy0 - (now - t0) * sp
                h = max(h, 0.85 * math.exp(-(((x - sx) / 0.9) ** 2 + ((y - sy) / 0.7) ** 2)))
            out[z] = tuple(min(1.0, c / 255 * BRIGHT) for c in ramp(h + HEAT))
        return out


def smooth(state, target):
    for z, tgt in target.items():
        state[z] = tuple(c + (t - c) * (ATTACK if t > c else RELEASE) for c, t in zip(state[z], tgt))
    return {z: tuple(int(round(v * 255)) for v in c) for z, c in state.items()}


def main():
    R.kernel32.CreateMutexW(None, False, "Local\\msi-kb-ripple")   # one lighting effect at a time
    if ctypes.get_last_error() == 183:
        print("Another effect is running (stop it with stop-ripple.cmd).")
        return
    calm = "--calm" in sys.argv
    kb = R.Kb()
    kb.static(0xFFFFFF, (0, 0, 0))
    if not calm:
        threading.Thread(target=R.hook_thread, daemon=True).start()
    fire = Fire()
    state = {z: (0.0, 0.0, 0.0) for z in R.ZONES}
    shown = {z: (0, 0, 0) for z in R.ZONES}
    print("Fire lit." + ("" if calm else " Type to stoke it.") + " Ctrl+C to stop.")
    try:
        while True:
            now = time.perf_counter()
            while not R.drops.empty():
                key, t0 = R.drops.get()
                x, y = R.KEYPOS.get(key, (7.0, 3.0))
                fire.stoke(x, y, t0)
            frame = smooth(state, fire.heat(now))
            groups = {}
            for z, c in frame.items():
                if max(abs(a - b) for a, b in zip(shown[z], c)) >= 2:
                    groups[c] = groups.get(c, 0) | (1 << z)
            for c, mask in groups.items():
                kb.static(mask, c)
                for z in R.ZONES:
                    if mask >> z & 1:
                        shown[z] = c
            time.sleep(max(0.0, 1 / FPS - (time.perf_counter() - now)))
    except KeyboardInterrupt:
        pass
    finally:
        try:
            kb.static(0xFFFFFF, (255, 255, 255))
        except Exception:
            pass
        print("Fire out, keyboard set to white.")


if __name__ == "__main__":
    main()
