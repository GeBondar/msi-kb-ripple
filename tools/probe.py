"""Interactive probe: lights candidate zone-select bits one at a time.
For each step, look at the keyboard and type which keys lit up (or Enter if nothing)."""
import datetime
import time
import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # noqa: E401
from msikb import Kb

LOG = "probe_log.txt"
WHITE = (255, 255, 255)
kb = Kb()


def step(name, action):
    kb.off(0x0F)
    time.sleep(0.15)
    action()
    ans = input(f"\n[{name}] Что светится? (Enter = ничего, q = выход): ").strip()
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.datetime.now():%H:%M:%S}\t{name}\t{ans}\n")
    return ans


steps = [("ALL red (mask 0x0F)", lambda: kb.static(0x0F, (255, 0, 0)))]
for m, label in [(1, "WASD?"), (2, "letters?"), (4, "nav?"), (8, "numpad?")]:
    steps.append((f"mask {m:#x} {label}", lambda m=m: kb.static(m, WHITE)))
# Candidate finer bits: bits 4..31 of a wider mask
for bit in range(4, 32):
    m = 1 << bit
    steps.append((f"mask bit {bit} ({m:#x})", lambda m=m: kb.static(m, WHITE)))

print("Смотри на клавиатуру. После каждого шага опиши, что зажглось.")
try:
    for name, act in steps:
        if step(name, act).lower() == "q":
            break
finally:
    kb.static(0x0F, WHITE)
    print("Готово, подсветка возвращена в белый. Лог:", LOG)
