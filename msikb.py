"""Minimal driver for MSI MysticLight laptop keyboard controller (1462:1603).

Only sends the two packet types known from OpenRGB / LightShow:
  report 2, packet 0x01 = zone select (bitmask)
  report 2, packet 0x02 = mode + colour keyframes
"""
import hid

VID, PID = 0x1462, 0x1603
OFF, STATIC, BREATH, CYCLE, WAVE = 0, 1, 2, 3, 4


class Kb:
    def __init__(self):
        self.d = hid.device()
        self.d.open(VID, PID)

    def _send(self, payload):
        buf = bytes([0x02]) + bytes(payload)
        buf = buf + bytes(64 - len(buf))
        if self.d.send_feature_report(buf) < 0:
            raise OSError("feature report write failed")

    def select(self, mask):
        """Zone select. mask may be wider than 8 bits: written little-endian from byte 2."""
        mb = mask.to_bytes(4, "little")
        self._send([0x01, *mb])

    def mode(self, mode, keyframes=(), speed=100, direction=0):
        p = [0x02, mode, speed & 0xFF, speed >> 8, 0, 0, 0x0F, 0x01, direction]
        for t, r, g, b in keyframes[:10]:
            p += [t, r, g, b]
        self._send(p)

    def static(self, mask, rgb):
        self.select(mask)
        r, g, b = rgb
        self.mode(STATIC, [(0, r, g, b), (100, r, g, b)])

    def off(self, mask=0x0F):
        self.select(mask)
        self.mode(OFF)
