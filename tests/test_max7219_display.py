"""Tests für die MAX7219-Anbindung – mit gestubbter Hardware.

Auf einem normalen Rechner sind weder ``luma`` noch Pillow installiert. Die
Tests ersetzen beide Pakete durch minimale Attrappen und prüfen, dass unsere
Parameter (SPI, Rotation, Helligkeit, Kaskadierung) korrekt ankommen.
"""

import sys
import types
import unittest
from unittest.mock import patch

from ampel.displays import Max7219Display
from ampel.phases import Phase


class FakeImage:
    """Minimaler Ersatz für ein PIL-Bild."""

    def __init__(self, mode, size, color=0):
        self.mode = mode
        self.size = size
        self.data = [color] * (size[0] * size[1])
        self.pasted = []

    def putdata(self, data):
        self.data = list(data)

    def paste(self, image, box):
        self.pasted.append((image, box))


class FakeMax7219:
    def __init__(self, serial_interface, **kwargs):
        self.serial_interface = serial_interface
        self.kwargs = kwargs
        self.images = []
        self.cleaned = False

    def display(self, image):
        self.images.append(image)

    def cleanup(self):
        self.cleaned = True


def _fake_modules(record):
    pil = types.ModuleType("PIL")
    pil_image = types.ModuleType("PIL.Image")
    pil_image.new = lambda mode, size, color=0: FakeImage(mode, size, color)
    pil.Image = pil_image

    serial_mod = types.ModuleType("luma.core.interface.serial")

    def fake_spi(**kwargs):
        record["spi"] = kwargs
        return object()

    serial_mod.spi = fake_spi
    serial_mod.noop = lambda: None

    device_mod = types.ModuleType("luma.led_matrix.device")

    def fake_max7219(serial_interface, **kwargs):
        record["device"] = FakeMax7219(serial_interface, **kwargs)
        return record["device"]

    device_mod.max7219 = fake_max7219

    return {
        "PIL": pil,
        "PIL.Image": pil_image,
        "luma": types.ModuleType("luma"),
        "luma.core": types.ModuleType("luma.core"),
        "luma.core.interface": types.ModuleType("luma.core.interface"),
        "luma.core.interface.serial": serial_mod,
        "luma.led_matrix": types.ModuleType("luma.led_matrix"),
        "luma.led_matrix.device": device_mod,
    }


class Max7219DisplayTest(unittest.TestCase):
    def _run_display(self, cascade=1):
        record = {}
        with patch.dict(sys.modules, _fake_modules(record)):
            display = Max7219Display(
                cascade=cascade,
                spi_port=0,
                spi_device=1,
                rotate=2,
                block_orientation=-90,
                intensity=32,
                reverse=True,
            )
            display.update(Phase.ROT, 10.0, 0.0)
            display.update(Phase.ROT, 9.0, 0.1)  # gleiche Phase: kein neues Bild
            display.update(Phase.GRUEN, 8.0, 0.0)
            display.close()
        return record

    def test_parameters_are_forwarded(self):
        record = self._run_display()
        self.assertEqual(record["spi"], {"port": 0, "device": 1, "gpio": None})
        self.assertEqual(
            record["device"].kwargs,
            {
                "cascaded": 1,
                "block_orientation": -90,
                "rotate": 2,
                "blocks_arranged_in_reverse_order": True,
                "contrast": 32,
            },
        )

    def test_redraws_only_on_phase_change(self):
        device = self._run_display()["device"]
        self.assertEqual(len(device.images), 2)  # Rot und Grün
        self.assertEqual([image.size for image in device.images], [(8, 8), (8, 8)])
        self.assertEqual([image.mode for image in device.images], ["1", "1"])
        self.assertTrue(device.cleaned)

    def test_cascaded_modules_get_a_wider_image(self):
        device = self._run_display(cascade=2)["device"]
        self.assertEqual(device.images[0].size, (16, 8))
        self.assertEqual(len(device.images[0].pasted), 2)  # zwei 8x8-Blöcke


if __name__ == "__main__":
    unittest.main()
