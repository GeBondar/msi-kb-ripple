"""Map each of the 24 zone bits to physical keys.
Background = dim blue, current zone = bright white."""
import datetime
import time
import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # noqa: E401
from msikb import Kb

LOG = "map24_log.txt"
kb = Kb()
ALL = 0xFFFFFF

print("Фон будет тусклым синим, текущая зона — ярко-белой.")
print("Напиши клавиши под белым пятном (например: Esc F1 F2 1 2 Q). Enter = ничего, b = повторить шаг назад, q = выход.\n")
bit = 0
try:
    while bit < 24:
        kb.static(ALL, (0, 0, 40))
        time.sleep(0.1)
        kb.static(1 << bit, (255, 255, 255))
        ans = input(f"[зона {bit:2d}] Белые клавиши: ").strip()
        if ans.lower() == "q":
            break
        if ans.lower() == "b":
            bit = max(0, bit - 1)
            continue
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now():%H:%M:%S}\t{bit}\t{ans}\n")
        bit += 1
finally:
    kb.static(ALL, (255, 255, 255))
    print("Готово, подсветка белая. Лог:", LOG)
