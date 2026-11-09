"""show.py BIT:COLOR ...  — all zones dark, listed zones in colours.
Colours: r g b y (red green blue yellow), w (white)."""
import sys
import os, sys; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # noqa: E401
from msikb import Kb

C = {"r": (255, 0, 0), "g": (0, 255, 0), "b": (0, 0, 255), "y": (255, 200, 0), "w": (255, 255, 255),
     "m": (255, 0, 255), "c": (0, 255, 255), "o": (255, 60, 0)}
kb = Kb()
kb.static(0xFFFFFF, (0, 0, 0))
for arg in sys.argv[1:]:
    bit, col = arg.split(":")
    kb.static(1 << int(bit), C[col])
