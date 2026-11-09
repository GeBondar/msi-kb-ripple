# Zone map — MSI Sword 17 HX B13V (MysticLight MS-1603)

Bit `n` of the zone-select mask lights zone `n`. Mapped by lighting 4–5 zones
in distinct colours and photographing the keyboard. LEDs bleed into
neighbouring keys, so each zone is "centred on" rather than "exactly" these keys.
Centres in key units live in `ZONES` in `ripple.py`.

| Bit | Keys (approx.)                | Bit | Keys (approx.)                  |
|----:|-------------------------------|----:|---------------------------------|
| 0   | Esc / ` / Tab (left top)      | 12  | A                               |
| 1   | Q                             | 13  | S (also lights W)               |
| 2   | E                             | 14  | D                               |
| 3   | 5 6 T                         | 15  | F X C                           |
| 4   | F6–F8, 7 8, U                 | 16  | G H B                           |
| 5   | 9 0 O                         | 17  | J K M ,                         |
| 6   | F11 F12 - = [                 | 18  | ; ' . /                         |
| 7   | Del \ Backspace               | 19  | Enter, RShift, Fn, Copilot      |
| 8   | Num 4                         | 20  | Numpad top (7 8 9) — uncertain  |
| 9   | Num 5                         | 21  | Num 1, Num 0, ←                 |
| 10  | Num 6                         | 22  | Arrows — not clearly seen       |
| 11  | Caps, LShift, LCtrl           | 23  | Num 3, Num ., Num Enter, →      |

`mask = 0x0F` is **not** "the whole keyboard" on this model (it is on some
others — older docs describe 4 groups). `0xFFFFFF` is.
