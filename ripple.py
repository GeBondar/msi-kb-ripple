"""Water-drop ripple lighting for MSI Sword 17 HX (MysticLight MS-1603, 24 zones).

Each key press drops a "stone" at the key's physical position; rings expand
from there and light the 24 zones as they pass. Keys are only used for their
position — nothing is logged or stored. Ctrl+C in this window to stop.

    python ripple.py          # react to real typing
    python ripple.py --demo   # simulated typing, hands off
"""
import colorsys
import ctypes
import ctypes.wintypes as wt
import math
import queue
import random
import sys
import threading
import time

from msikb import Kb

# ---------- look & feel ----------
BG = (0, 3, 12)            # calm water (dim, so rings stand out)
SPEED = 6.5                # ring speed, keys per second
FRONT = 0.9                # sharpness of the ring's leading edge, keys
TAIL = 1.1                 # length of the soft glow behind the ring, keys
LIFE = 1.0                 # seconds until a drop fades out
GAIN = 2.3                # overall ring brightness (clipped at 255)
ATTACK = 0.35              # per-frame smoothing when getting brighter (1 = instant)
RELEASE = 0.38           # per-frame smoothing when getting darker (smaller = softer fade)
HUE_DRIFT = True           # each drop slightly different colour (cyan..blue..violet)
FPS = 45

# ---------- zone centres (x = key columns, y = rows; 0 = F-row) ----------
ZONES = {
    0: (0.6, 1.4), 1: (1.9, 2.0), 2: (3.0, 2.0), 3: (5.4, 1.6),
    4: (7.2, 1.0), 5: (9.4, 1.4), 6: (11.6, 1.0), 7: (13.4, 1.2),
    8: (15.6, 2.4), 9: (16.6, 2.4), 10: (17.6, 2.4), 11: (0.8, 4.0),
    12: (2.2, 3.0), 13: (3.0, 2.6), 14: (4.2, 3.0), 15: (5.0, 3.6),
    16: (6.6, 3.6), 17: (8.4, 3.6), 18: (10.8, 3.6), 19: (12.8, 4.2),
    20: (16.6, 1.3), 21: (15.6, 3.8), 22: (14.5, 4.6), 23: (17.6, 4.2),
}

# ---------- physical key positions by scan code ((code, extended) -> (x, y)) ----------
KEYPOS = {}


def row(y, x0, step, codes, ext=False):
    for i, c in enumerate(codes):
        KEYPOS[(c, ext)] = (x0 + i * step, y)


row(0, 0.5, 1.0, [0x01, 0x3B, 0x3C, 0x3D, 0x3E, 0x3F, 0x40, 0x41, 0x42, 0x43, 0x44, 0x57, 0x58])
KEYPOS[(0x37, True)] = (13.5, 0); KEYPOS[(0x52, True)] = (14.5, 0); KEYPOS[(0x53, True)] = (15.5, 0)
KEYPOS[(0x37, False)] = (16.6, 0); KEYPOS[(0x35, True)] = (17.6, 0)          # num * and num /
row(1, 0.5, 1.0, list(range(0x29, 0x2A)) + list(range(0x02, 0x0E)))        # ` 1..0 - =
KEYPOS[(0x0E, False)] = (13.8, 1)                                           # Backspace
row(2, 0.8, 0, [0x0F]); row(2, 1.9, 1.0, list(range(0x10, 0x1C))); KEYPOS[(0x2B, False)] = (13.9, 2)
row(3, 0.8, 0, [0x3A]); row(3, 2.2, 1.0, list(range(0x1E, 0x29))); KEYPOS[(0x1C, False)] = (13.6, 3)
row(4, 1.0, 0, [0x2A]); row(4, 2.6, 1.0, list(range(0x2C, 0x36))); KEYPOS[(0x36, False)] = (13.0, 4)
KEYPOS.update({(0x1D, False): (0.7, 5), (0x5B, True): (2.0, 5), (0x38, False): (3.0, 5),
               (0x39, False): (6.5, 5), (0x38, True): (10.0, 5), (0x1D, True): (11.5, 5),
               (0x56, False): (11.0, 5)})
# arrows
KEYPOS.update({(0x48, True): (14.5, 4), (0x4B, True): (13.5, 5), (0x50, True): (14.5, 5), (0x4D, True): (15.5, 5)})
# numpad (also its nav aliases with NumLock off)
for codes, y in (([0x4E, 0x4A, 0x45], 0.8), ([0x47, 0x48, 0x49], 1.6), ([0x4B, 0x4C, 0x4D], 2.4), ([0x4F, 0x50, 0x51], 3.2)):
    for i, c in enumerate(codes):
        KEYPOS.setdefault((c, False), (15.6 + i, y))
KEYPOS[(0x45, True)] = (17.6, 0.8)  # NumLock reports as extended
KEYPOS.update({(0x52, False): (16.0, 4.0), (0x53, False): (17.6, 4.0), (0x1C, True): (17.0, 5.0)})
for (c, e), p in list(KEYPOS.items()):  # Home/End/PgUp... on the numpad keys send extended codes
    if not e and 0x47 <= c <= 0x53:
        KEYPOS.setdefault((c, True), p)

# ---------- keyboard hook (positions only) ----------
drops = queue.Queue()
WH_KEYBOARD_LL, WM_KEYDOWN, WM_SYSKEYDOWN, WM_KEYUP, WM_SYSKEYUP = 13, 0x100, 0x104, 0x101, 0x105


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("vkCode", wt.DWORD), ("scanCode", wt.DWORD), ("flags", wt.DWORD),
                ("time", wt.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int, wt.WPARAM, wt.LPARAM)
user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wt.HINSTANCE, wt.DWORD]
user32.SetWindowsHookExW.restype = wt.HHOOK
user32.CallNextHookEx.argtypes = [wt.HHOOK, ctypes.c_int, wt.WPARAM, wt.LPARAM]
user32.CallNextHookEx.restype = ctypes.c_ssize_t
kernel32.GetModuleHandleW.restype = wt.HMODULE
held = set()


def _hook(n, wparam, lparam):
    if n == 0:
        k = ctypes.cast(lparam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
        key = (k.scanCode, bool(k.flags & 1))
        if wparam in (WM_KEYDOWN, WM_SYSKEYDOWN):
            if key not in held:              # ignore auto-repeat
                held.add(key)
                drops.put((key, time.perf_counter()))
        elif wparam in (WM_KEYUP, WM_SYSKEYUP):
            held.discard(key)
    return user32.CallNextHookEx(None, n, wparam, lparam)


_hook_ref = HOOKPROC(_hook)


def hook_thread():
    h = user32.SetWindowsHookExW(WH_KEYBOARD_LL, _hook_ref, kernel32.GetModuleHandleW(None), 0)
    if not h:
        raise ctypes.WinError(ctypes.get_last_error())
    msg = wt.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))


# ---------- simulated typing (demo mode + README animation) ----------
_US = {**{c: 0x10 + i for i, c in enumerate("qwertyuiop")},
       **{c: 0x1E + i for i, c in enumerate("asdfghjkl")},
       **{c: 0x2C + i for i, c in enumerate("zxcvbnm")},
       **{c: 0x02 + i for i, c in enumerate("1234567890")}, " ": 0x39, "\n": 0x1C}
DEMO_TEXT = "hello world\ndrop by drop\n"


def demo_presses(seed=7):
    """Endless (key, delay_before_s) stream: human-ish typing, pauses, the odd numpad/arrow burst."""
    rnd = random.Random(seed)
    extras = [(0x4B, True), (0x48, True), (0x4D, True), (0x50, True),     # arrows
              (0x47, False), (0x4C, False), (0x51, False), (0x0E, False),   # num7 num5 num3 Backspace
              (0x01, False), (0x3A, False)]                                # Esc Caps
    while True:
        for ch in DEMO_TEXT:
            yield (_US[ch], False), rnd.uniform(0.09, 0.22) + (0.35 if ch in " \n" else 0)
        yield rnd.choice(extras), 0.6
        for _ in range(rnd.randint(1, 3)):
            yield rnd.choice(extras), rnd.uniform(0.15, 0.3)
        yield rnd.choice(extras), 0.8


def demo_thread():
    for key, delay in demo_presses(random.randrange(1 << 30)):
        time.sleep(delay)
        drops.put((key, time.perf_counter()))


# ---------- rendering ----------
def drop_colour(i):
    if not HUE_DRIFT:
        return (0.55, 0.9, 1.0)
    h = 0.50 + 0.22 * ((i * 0.618) % 1.0)          # cyan .. violet
    return colorsys.hsv_to_rgb(h, 0.75, 1.0)


def render(active, now):
    out = {}
    for z, (zx, zy) in ZONES.items():
        r, g, b = (c / 255 for c in BG)
        for (px, py), t0, col in active:
            t = now - t0
            fade = GAIN * max(0.0, 1.0 - t / LIFE) ** 1.2
            if fade <= 0:
                continue
            d = math.hypot(zx - px, (zy - py) * 1.15)
            k = d - SPEED * t                       # >0: ring not here yet, <0: ring has passed
            if k > 0:
                a = math.exp(-(k / FRONT) ** 2)      # sharp leading edge
            else:
                a = math.exp(k / TAIL)               # long soft wake, no extra pulses
            a *= fade
            r += col[0] * a; g += col[1] * a; b += col[2] * a
        out[z] = (min(1.0, r), min(1.0, g), min(1.0, b))
    return out


def smooth(state, target):
    for z, tgt in target.items():
        cur = state[z]
        state[z] = tuple(c + (t - c) * (ATTACK if t > c else RELEASE) for c, t in zip(cur, tgt))
    return {z: tuple(int(round(v * 255)) for v in c) for z, c in state.items()}


def open_kb():
    """Open the controller, waiting for it (e.g. right after login or wake from sleep)."""
    while True:
        try:
            kb = Kb()
            kb.static(0xFFFFFF, BG)
            return kb
        except (OSError, IOError, ValueError):
            time.sleep(3)


def main():
    # single instance: a second copy (e.g. autostart + manual run) just exits
    kernel32.CreateMutexW(None, False, "Local\\msi-kb-ripple")
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        print("Ripple is already running (stop it with stop-ripple.cmd).")
        return
    kb = open_kb()
    demo = "--demo" in sys.argv
    threading.Thread(target=demo_thread if demo else hook_thread, daemon=True).start()
    shown = {z: BG for z in ZONES}
    state = {z: tuple(c / 255 for c in BG) for z in ZONES}
    active, n = [], 0
    print("Ripple demo: simulated typing. Ctrl+C to stop." if demo else
          "Ripple on — start typing. Ctrl+C to stop.")
    try:
        while True:
            now = time.perf_counter()
            while not drops.empty():
                key, t0 = drops.get()
                pos = KEYPOS.get(key, (7.0, 3.0))
                active.append((pos, t0, drop_colour(n))); n += 1
            active = [a for a in active if now - a[1] < LIFE][-8:]
            frame = smooth(state, render(active, now))
            groups = {}
            for z, c in frame.items():
                if max(abs(a - b) for a, b in zip(shown[z], c)) >= 2:
                    groups[c] = groups.get(c, 0) | (1 << z)
            try:
                for c, mask in groups.items():
                    kb.static(mask, c)
                    for z in ZONES:
                        if mask >> z & 1:
                            shown[z] = c
            except (OSError, IOError, ValueError):   # device lost (sleep/resume): reconnect
                try:
                    kb.d.close()
                except Exception:
                    pass
                kb = open_kb()
                shown = {z: BG for z in ZONES}
            time.sleep(max(0.0, 1 / FPS - (time.perf_counter() - now)))
    except KeyboardInterrupt:
        pass
    finally:
        try:
            kb.static(0xFFFFFF, (255, 255, 255))
        except Exception:
            pass
        print("Stopped, keyboard set to white.")


if __name__ == "__main__":
    main()
