"""Tests für die ASCII-Vorschau (ohne Terminal, ohne Hardware)."""

import io
import unittest

from ampel.displays import AsciiDisplay
from ampel.phases import Phase


class AsciiDisplayTest(unittest.TestCase):
    def setUp(self):
        self.stream = io.StringIO()
        self.display = AsciiDisplay(self.stream)

    def test_frame_has_eight_rows_and_status_line(self):
        self.display.update(Phase.GRUEN, 5.0, 0.4)
        lines = self.stream.getvalue().splitlines()
        self.assertEqual(len(lines), 9)  # 8 Matrixzeilen + Statuszeile
        self.assertIn("Grün", lines[-1])
        self.assertIn("5 s", lines[-1])

    def test_non_tty_draws_only_on_phase_change(self):
        self.display.update(Phase.ROT, 10.0, 0.0)
        after_first = self.stream.getvalue()

        # Gleiche Phase, nur die Restzeit ändert sich: keine neue Grafik.
        self.display.update(Phase.ROT, 9.0, 0.1)
        self.assertEqual(self.stream.getvalue(), after_first)

        # Neuer Zustand: neue Grafik.
        self.display.update(Phase.ROT_GELB, 2.0, 0.0)
        self.assertGreater(len(self.stream.getvalue()), len(after_first))
        self.assertIn("Rot-Gelb", self.stream.getvalue())

    def test_plain_frame_layout(self):
        self.display.update(Phase.ROT, 10.0, 0.0)
        lines = self.stream.getvalue().splitlines()
        # Obere Lampe aktiv: Balken über die Spalten 1..6 (je zwei Zeichen).
        self.assertEqual(lines[0], "  .." + "#" * 12 + "..")
        # Untere Lampe inaktiv: nur der 2x2-Punkt in der Mitte.
        self.assertEqual(lines[7], "  ......" + "####" + "......")

    def test_close_is_idempotent(self):
        self.display.update(Phase.ROT, 1.0, 0.9)
        self.display.close()
        self.display.close()


if __name__ == "__main__":
    unittest.main()
