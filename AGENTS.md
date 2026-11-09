# AGENTS.md: installing msi-kb-ripple on a user's machine

You are setting up a keyboard lighting effect on a Windows MSI laptop. You
**cannot see the keyboard.** Every visual check goes through the user, so ask
short, concrete questions such as "Is the whole keyboard red now?", or ask for a
photo.

## Hard safety rules

1. Send **only** what `msikb.py` sends: feature report `0x02` with packet `0x01`
   (zone select) or `0x02` (mode/colour). Never write report IDs 1, 3–8, never
   invent packet IDs, never send firmware-looking data. A bad packet has
   permanently killed a similar MSI backlight.
2. Reading is safe: `hid.enumerate`, `get_report_descriptor`, `get_feature_report`.
3. Don't install MSI Center / SteelSeries GG yourself. If one is already
   installed, tell the user that it may fight over the LEDs.

## 1. Check the hardware

```powershell
python -m pip install -r requirements.txt
python -c "import hid; print(hid.enumerate(0x1462, 0x1603))"
```

* **Non-empty, `product_string` = `MysticLight MS-1603`** → supported, continue.
* **Other `0x1462` PID** (e.g. `0x1601`, `0x1605`, `0x1562`–`0x1572`): the same
  packet format is reported to work. Change `PID` in `msikb.py`, then do step 3
  (zone map) before installing.
* **Nothing from `0x1462`** → not supported (SteelSeries per-key boards are
  `0x1038:*`, a different protocol). Stop and tell the user.

## 2. Smoke test (ask the user to watch)

```powershell
python tools/show.py 0:r 5:g 10:b 15:y   # 4 coloured zones on a dark board
python -c "from msikb import Kb; Kb().static(0xFFFFFF,(255,0,0))"   # all red
```

If "all red" isn't the whole keyboard, the zone count differs. Go to step 3.

## 3. Zone map (only for a different model or layout)

`ZONES` in `ripple.py` holds the centre of each of the 24 zones in key units
(x = column from the left, y = row, 0 = F-row). To remap:

* `python tools/show.py 0:r 1:g 2:b 3:y`, then ask the user for a **photo of the
  whole keyboard**. Repeat for 4–7, 8–11, … (4 colours per photo are
  reliable; 8 are not).
* Write down which keys each colour lights and update `ZONES` and `docs/zones.md`.

## 4. Install

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
```

This adds the Startup shortcut `MSI Keyboard Ripple.lnk` (runs `pythonw`, no window)
and starts the effect. A single-instance mutex prevents duplicates. If you
change code, run `stop-ripple.cmd` and start it again, or the old copy keeps running.

## 5. Tune with the user

Run in a visible terminal while iterating: `python ripple.py` (Ctrl+C restores
white). Map their feedback to knobs at the top of `ripple.py`:

| User says | Change |
|---|---|
| "too fast" / "too slow" | `SPEED`, `LIFE` |
| "fades too slowly" | raise `RELEASE` (≤ 0.4), lower `TAIL` |
| "it flickers" | lower `RELEASE`, raise `BG` a bit; avoid multiple echo rings |
| "too dim" / "low contrast" | raise `GAIN`, darken `BG` |

Writes themselves don't flicker (verified). Flicker always comes from the
animation, i.e. repeated pulses or a too-dark background.

## Files

`ripple.py` engine + key hook · `msikb.py` HID driver · `install.ps1` /
`uninstall.ps1` / `stop-ripple.cmd` · `tools/show.py` zone painter ·
`tools/make_demo.py` renders `docs/demo.gif` · `tools/probe.py`, `map24.py`,
`flicker_test.py` were used for the original reverse engineering.
