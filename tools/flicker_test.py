"""Test A: rewrite the SAME colour 30x/s for 4 s (does a write itself blink?).
Test B: one hardware keyframe fade (controller interpolates itself), 4 s."""
import sys
import time
import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # noqa: E401
from msikb import Kb, CYCLE

kb = Kb()
ALL = 0xFFFFFF
if sys.argv[1] == "A":
    kb.static(ALL, (0, 80, 160))
    t = time.time()
    while time.time() - t < 4:
        kb.static(ALL, (0, 80, 160))
        time.sleep(1 / 30)
else:
    kb.select(ALL)
    # 2 s period: dark -> bright cyan -> dark, smooth, done by the controller
    kb.mode(CYCLE, [(0, 0, 0, 8), (30, 80, 200, 255), (100, 0, 0, 8)], speed=200)
    time.sleep(6)
    kb.static(ALL, (0, 0, 8))
