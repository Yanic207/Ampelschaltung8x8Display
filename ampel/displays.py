"""Ausgabegeräte für die Ampel.

* :class:`Max7219Display` – echtes 8x8-Modul am SPI-Bus des Raspberry Pi.
* :class:`AsciiDisplay` – farbige Vorschau im Terminal, ganz ohne Hardware.

Beide erfüllen dasselbe kleine Interface und werden vom Hauptprogramm nur mit
Phase, Restzeit und Fortschritt gefüttert.
"""

from __future__ import annotations

import math
import sys
from typing import Optional, Protocol, TextIO

from .phases import Phase
from .render import ACTIVE_LAMPS, HEIGHT, LAMP_TOP, WIDTH, Grid, render

# ANSI-Farben – nur für die Terminal-Vorschau. Die echte Matrix ist rot.
_RESET = "\x1b[0m"
_BOLD = "\x1b[1m"
_DIM = "\x1b[38;5;238m"
_LAMP_COLORS = {
    Phase.ROT: "\x1b[38;5;196m",
    Phase.GELB: "\x1b[38;5;226m",
    Phase.GRUEN: "\x1b[38;5;46m",
}
_BAR_COLOR = {
    Phase.ROT: _LAMP_COLORS[Phase.ROT],
    Phase.ROT_GELB: _LAMP_COLORS[Phase.GELB],
    Phase.GRUEN: _LAMP_COLORS[Phase.GRUEN],
    Phase.GELB: _LAMP_COLORS[Phase.GELB],
}


class Display(Protocol):
    """Gemeinsames Interface der Ausgabegeräte."""

    def update(self, phase: Phase, remaining: float, progress: float = 0.0) -> None:
        ...

    def close(self) -> None:
        ...


def grid_to_image(grid: Grid):
    """Wandelt das 8x8-Raster in ein 1-Bit-Bild für ``luma`` um."""
    from PIL import Image

    image = Image.new("1", (WIDTH, HEIGHT), 0)
    image.putdata([255 if pixel else 0 for row in grid for pixel in row])
    return image


class Max7219Display:
    """8x8-Matrix mit MAX7219-Treiber am SPI-Bus (z. B. ME042/FC-16)."""

    def __init__(
        self,
        *,
        cascade: int = 1,
        spi_port: int = 0,
        spi_device: int = 0,
        rotate: int = 0,
        block_orientation: int = 0,
        intensity: int = 64,
        reverse: bool = False,
    ) -> None:
        try:
            from luma.core.interface.serial import noop, spi
            from luma.led_matrix.device import max7219
        except ImportError as exc:  # pragma: no cover – nur auf dem Pi relevant
            raise RuntimeError(
                "luma.led_matrix ist nicht installiert. "
                "Bitte im Projektordner 'pip install -r requirements.txt' ausführen."
            ) from exc

        serial = spi(port=spi_port, device=spi_device, gpio=noop())
        self._cascade = cascade
        self._device = max7219(
            serial,
            cascaded=cascade,
            block_orientation=block_orientation,
            rotate=rotate,
            blocks_arranged_in_reverse_order=reverse,
            contrast=intensity,
        )
        self._last_phase: Optional[Phase] = None

    def update(self, phase: Phase, remaining: float, progress: float = 0.0) -> None:
        # Die LED-Matrix ist rein binär und damit zeitunabhängig – neu zeichnen
        # genügt beim Phasenwechsel.
        if phase is self._last_phase:
            return
        self._last_phase = phase

        from PIL import Image

        tile = grid_to_image(render(phase))
        if self._cascade == 1:
            image = tile
        else:
            # Bei mehreren verketteten Modulen die Ampel auf jedes Modul malen.
            image = Image.new("1", (WIDTH * self._cascade, HEIGHT), 0)
            for index in range(self._cascade):
                image.paste(tile, (index * WIDTH, 0))

        self._device.display(image)

    def close(self) -> None:
        self._device.cleanup()


class AsciiDisplay:
    """Farbige Ampel-Vorschau im Terminal.

    Bei einem echten Terminal wird das Bild an Ort und Stelle aktualisiert.
    Wird die Ausgabe umgeleitet (z. B. in eine Datei), erscheint pro
    Phasenwechsel ein neues Bild ohne Steuerzeichen.
    """

    def __init__(self, stream: Optional[TextIO] = None) -> None:
        self._stream = stream or sys.stdout
        self._tty = bool(getattr(self._stream, "isatty", lambda: False)())
        self._last_phase: Optional[Phase] = None
        self._last_second: Optional[int] = None
        self._drawn = False

    def update(self, phase: Phase, remaining: float, progress: float = 0.0) -> None:
        second = int(math.ceil(remaining))
        if phase is self._last_phase and second == self._last_second:
            return

        phase_changed = phase is not self._last_phase
        self._last_phase = phase
        self._last_second = second

        # Ohne Terminal (Pipe/Datei) nicht jede Sekunde eine neue Grafik anfügen.
        if not self._tty and not phase_changed:
            return

        self._draw(phase, remaining, progress)

    def close(self) -> None:
        if self._tty and self._drawn:
            self._stream.write(_RESET + "\n")
            self._stream.flush()
        self._drawn = False

    def _draw(self, phase: Phase, remaining: float, progress: float) -> None:
        lines = self._frame(phase, remaining, progress)

        if self._tty:
            if self._drawn:
                # Cursor über das zuletzt gezeichnete Bild setzen …
                self._stream.write(f"\x1b[{len(lines)}A")
            for line in lines:
                # … und jede Zeile komplett überschreiben.
                self._stream.write("\x1b[2K" + line + "\n")
        else:
            self._stream.write("\n".join(lines) + "\n")

        self._stream.flush()
        self._drawn = True

    def _frame(self, phase: Phase, remaining: float, progress: float) -> list[str]:
        grid = render(phase)
        active = ACTIVE_LAMPS[phase]
        lines = []

        for y, row in enumerate(grid):
            lamp = self._lamp_for_row(y)

            if self._tty:
                color = _LAMP_COLORS[lamp] if lamp in active else _DIM
                cells = "".join(
                    (color + "██" + _RESET) if pixel else (_DIM + "··" + _RESET)
                    for pixel in row
                )
            else:
                cells = "".join("##" if pixel else ".." for pixel in row)

            lines.append("  " + cells)

        lines.append(self._status(phase, remaining, progress))
        return lines

    @staticmethod
    def _lamp_for_row(y: int) -> Optional[Phase]:
        for lamp, top in LAMP_TOP.items():
            if y in (top, top + 1):
                return lamp
        return None

    def _status(self, phase: Phase, remaining: float, progress: float) -> str:
        seconds = max(0, int(math.ceil(remaining)))

        if not self._tty:
            return f"Phase: {phase.label}, Restzeit: {seconds} s"

        filled = int(round(progress * 20))
        bar = (
            _BAR_COLOR[phase]
            + "█" * filled
            + _DIM
            + "░" * (20 - filled)
            + _RESET
        )
        return f"  {_BOLD}{phase.label}{_RESET} – noch {seconds:2d} s  [{bar}]"
