"""Erzeugt aus einer Ampelphase ein 8x8-Pixelbild.

Reine Daten, keine Hardware- oder Grafikbibliothek – dadurch gut testbar und
auf jedem Rechner (auch ohne Raspberry Pi) ausführbar.

Aufbau des Bildes (8 Spalten, 8 Zeilen)::

    Zeile 0/1:  Rot      ─ aktive Lampe: Balken, inaktive Lampe: Punkt
    Zeile 2:    Lücke
    Zeile 3/4:  Gelb
    Zeile 5:    Lücke
    Zeile 6/7:  Grün

Aktive Lampen werden als breiter Balken (Spalten 1–6), inaktive als kleiner
Mittelpunkt (Spalten 3–4) dargestellt. So ist auch auf der rein roten
LED-Matrix auf einen Blick erkennbar, welche Lampe gerade leuchtet.
"""

from __future__ import annotations

from typing import Dict, FrozenSet, List

from .phases import Phase

WIDTH = 8
HEIGHT = 8

#: Zweidimensionales Pixelraster; ``True`` = LED an.
Grid = List[List[bool]]

#: Oberste Zeile der drei Lampen; jede Lampe ist zwei Zeilen hoch.
LAMP_TOP: Dict[Phase, int] = {
    Phase.ROT: 0,
    Phase.GELB: 3,
    Phase.GRUEN: 6,
}

#: Welche Lampen in welcher Phase leuchten.
ACTIVE_LAMPS: Dict[Phase, FrozenSet[Phase]] = {
    Phase.ROT: frozenset({Phase.ROT}),
    Phase.ROT_GELB: frozenset({Phase.ROT, Phase.GELB}),
    Phase.GRUEN: frozenset({Phase.GRUEN}),
    Phase.GELB: frozenset({Phase.GELB}),
}

_ACTIVE_X = range(1, 7)    # Balken: Spalten 1..6
_INACTIVE_X = range(3, 5)  # Punkt: Spalten 3..4


def empty_grid() -> Grid:
    """Ein vollständig ausgeschaltetes 8x8-Raster."""
    return [[False] * WIDTH for _ in range(HEIGHT)]


def render(phase: Phase) -> Grid:
    """Rendert eine Ampelphase als 8x8-Raster."""
    grid = empty_grid()
    active = ACTIVE_LAMPS[phase]

    for lamp, top in LAMP_TOP.items():
        columns = _ACTIVE_X if lamp in active else _INACTIVE_X
        for y in (top, top + 1):
            for x in columns:
                grid[y][x] = True

    return grid
