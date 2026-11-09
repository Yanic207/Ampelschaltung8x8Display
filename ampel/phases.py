"""Reine Ampel-Logik – ohne Hardware, ohne echte Uhr.

Die Steuerung ist eine kleine Zustandsmaschine. Sie bekommt bei jedem Aufruf
von :meth:`TrafficLight.update` eine monoton steigende Zeit in Sekunden und
wechselt die Phase, sobald deren Dauer abgelaufen ist.

Phasenfolge einer deutschen Lichtsignalanlage::

    Rot ──► Rot-Gelb ──► Grün ──► Gelb ──► Rot …

Die Ampel startet bewusst mit Rot: Nach einem Neustart darf niemals direkt
Grün angezeigt werden.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict


class Phase(Enum):
    """Die vier Zustände einer Ampel."""

    ROT = "rot"
    ROT_GELB = "rot-gelb"
    GRUEN = "gruen"
    GELB = "gelb"

    @property
    def label(self) -> str:
        """Deutsche Bezeichnung für die Ausgabe auf der Konsole."""
        return _LABELS[self]


_LABELS: Dict[Phase, str] = {
    Phase.ROT: "Rot",
    Phase.ROT_GELB: "Rot-Gelb",
    Phase.GRUEN: "Grün",
    Phase.GELB: "Gelb",
}

#: Nächste Phase im Zyklus.
NEXT_PHASE: Dict[Phase, Phase] = {
    Phase.ROT: Phase.ROT_GELB,
    Phase.ROT_GELB: Phase.GRUEN,
    Phase.GRUEN: Phase.GELB,
    Phase.GELB: Phase.ROT,
}


@dataclass(frozen=True)
class Timings:
    """Dauern der einzelnen Phasen in Sekunden."""

    rot: float = 10.0
    rot_gelb: float = 2.0
    gruen: float = 8.0
    gelb: float = 3.0

    def __post_init__(self) -> None:
        if any(value <= 0 for value in (self.rot, self.rot_gelb, self.gruen, self.gelb)):
            raise ValueError("Alle Phasendauern müssen größer als 0 sein.")

    def duration(self, phase: Phase) -> float:
        """Dauer der übergebenen Phase in Sekunden."""
        return {
            Phase.ROT: self.rot,
            Phase.ROT_GELB: self.rot_gelb,
            Phase.GRUEN: self.gruen,
            Phase.GELB: self.gelb,
        }[phase]


class TrafficLight:
    """Zustandsmaschine der simulierten Ampel.

    Parameters
    ----------
    timings:
        Dauern der vier Phasen.
    start:
        Startphase (Standard: Rot).
    now:
        Startzeit in Sekunden, üblicherweise ``time.monotonic()``.
    """

    def __init__(
        self,
        timings: Timings | None = None,
        start: Phase = Phase.ROT,
        now: float = 0.0,
    ) -> None:
        self.timings = timings or Timings()
        self.phase = start
        self._phase_start = now
        self._now = now

    def update(self, now: float) -> bool:
        """Führt die Ampel bis zur Zeit ``now`` fort.

        Returns
        -------
        bool
            ``True``, wenn mindestens ein Phasenwechsel stattgefunden hat.
        """
        if now < self._now:
            # Eine monotone Uhr läuft nicht rückwärts. Falls doch (etwa in
            # einem Test mit unsortierten Zeitstempeln), Zeit einfrieren.
            now = self._now
        self._now = now

        changed = False
        while now - self._phase_start >= self.timings.duration(self.phase):
            self._phase_start += self.timings.duration(self.phase)
            self.phase = NEXT_PHASE[self.phase]
            changed = True
        return changed

    @property
    def elapsed(self) -> float:
        """Vergangene Zeit in der aktuellen Phase in Sekunden."""
        return self._now - self._phase_start

    @property
    def remaining(self) -> float:
        """Restzeit der aktuellen Phase in Sekunden."""
        return max(0.0, self.timings.duration(self.phase) - self.elapsed)

    @property
    def progress(self) -> float:
        """Fortschritt der aktuellen Phase zwischen 0.0 und 1.0."""
        return min(1.0, max(0.0, self.elapsed / self.timings.duration(self.phase)))
