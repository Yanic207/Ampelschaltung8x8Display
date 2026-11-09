"""Kommandozeilen-Einstieg: ``python3 -m ampel``."""

from __future__ import annotations

import argparse
import signal
import sys
import time
from typing import List, Optional

from .displays import AsciiDisplay, Display, Max7219Display
from .phases import Phase, Timings, TrafficLight


def _intensity(value: str) -> int:
    """Argparse-Typ für die Helligkeit (0–255)."""
    number = int(value)
    if not 0 <= number <= 255:
        raise argparse.ArgumentTypeError("muss zwischen 0 und 255 liegen")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m ampel",
        description=(
            "Simulierte Ampel auf einem 8x8-LED-Matrixmodul mit MAX7219 "
            "(z. B. ME042) am Raspberry Pi."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--driver",
        choices=("max7219", "ascii"),
        default="max7219",
        help="max7219 = echtes Modul, ascii = Vorschau im Terminal",
    )

    hardware = parser.add_argument_group("MAX7219-Hardware")
    hardware.add_argument(
        "--cascade",
        type=int,
        default=1,
        metavar="N",
        help="Anzahl verketteter 8x8-Module",
    )
    hardware.add_argument(
        "--spi-port",
        type=int,
        default=0,
        metavar="N",
        help="SPI-Bus (0 = /dev/spidev0.x)",
    )
    hardware.add_argument(
        "--spi-device",
        type=int,
        choices=(0, 1),
        default=0,
        help="Chip-Select: 0 = CE0 (GPIO8, Pin 24), 1 = CE1 (GPIO7, Pin 26)",
    )
    hardware.add_argument(
        "--rotate",
        type=int,
        choices=(0, 1, 2, 3),
        default=0,
        help="Bild in 90-Grad-Schritten drehen (0–3)",
    )
    hardware.add_argument(
        "--block-orientation",
        type=int,
        choices=(0, 90, -90, 180),
        default=0,
        help="Orientierung der 8x8-Blöcke korrigieren",
    )
    hardware.add_argument(
        "--reverse",
        action="store_true",
        help="Reihenfolge verketteter Module umkehren",
    )
    hardware.add_argument(
        "--intensity",
        type=_intensity,
        default=64,
        metavar="0-255",
        help="Helligkeit (0 = sehr dunkel, 255 = maximal)",
    )

    timings = parser.add_argument_group("Phasendauern in Sekunden")
    timings.add_argument("--rot", type=float, default=10.0, help="Dauer Rot")
    timings.add_argument("--rot-gelb", type=float, default=2.0, help="Dauer Rot-Gelb")
    timings.add_argument("--gruen", type=float, default=8.0, help="Dauer Grün")
    timings.add_argument("--gelb", type=float, default=3.0, help="Dauer Gelb")

    parser.add_argument(
        "--cycles",
        type=int,
        default=0,
        metavar="N",
        help="Nach N vollständigen Zyklen beenden (0 = unendlich)",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=10.0,
        help="Abtastrate der Simulation in Hz",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Keine Statusmeldungen auf der Konsole (nur bei --driver max7219)",
    )

    return parser


def _create_display(args: argparse.Namespace) -> Display:
    if args.driver == "ascii":
        return AsciiDisplay()
    return Max7219Display(
        cascade=args.cascade,
        spi_port=args.spi_port,
        spi_device=args.spi_device,
        rotate=args.rotate,
        block_orientation=args.block_orientation,
        intensity=args.intensity,
        reverse=args.reverse,
    )


def _status_line(light: TrafficLight) -> str:
    return (
        f"{time.strftime('%H:%M:%S')}  {light.phase.label:<8} "
        f"noch {light.remaining:4.1f} s"
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.fps <= 0:
        parser.error("--fps muss größer als 0 sein")
    if args.cascade < 1:
        parser.error("--cascade muss mindestens 1 sein")
    if args.cycles < 0:
        parser.error("--cycles darf nicht negativ sein")

    try:
        timings = Timings(
            rot=args.rot,
            rot_gelb=args.rot_gelb,
            gruen=args.gruen,
            gelb=args.gelb,
        )
    except ValueError as exc:
        parser.error(str(exc))

    try:
        display = _create_display(args)
    except Exception as exc:  # Hardware-/SPI-Fehler verständlich ausgeben
        print(f"Fehler: Display konnte nicht initialisiert werden: {exc}", file=sys.stderr)
        print(
            "Tipp: SPI mit 'sudo raspi-config' aktivieren. "
            "Ohne Hardware lässt sich die Ampel mit '--driver ascii' testen.",
            file=sys.stderr,
        )
        return 2

    # Für das Terminal ist die Statuszeile Teil der Anzeige; beim echten Modul
    # protokollieren wir die Phasenwechsel auf der Konsole.
    log = not args.quiet and args.driver != "ascii"

    # Startphase ist bewusst Rot – der sichere Zustand nach dem Einschalten.
    light = TrafficLight(timings, start=Phase.ROT, now=time.monotonic())
    if log:
        print(
            "Ampel-Simulation gestartet – "
            f"Rot {timings.rot:g}s, Rot-Gelb {timings.rot_gelb:g}s, "
            f"Grün {timings.gruen:g}s, Gelb {timings.gelb:g}s",
            flush=True,
        )
        print(_status_line(light), flush=True)

    stop = False

    def request_stop(signum: int, frame: object) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    interval = 1.0 / args.fps
    cycles_done = 0

    try:
        while not stop:
            now = time.monotonic()
            phase_before = light.phase

            if light.update(now):
                # Von Gelb nach Rot: ein vollständiger Umlauf ist fertig.
                if phase_before is Phase.GELB and light.phase is Phase.ROT:
                    cycles_done += 1
                if log:
                    print(_status_line(light), flush=True)

            display.update(light.phase, light.remaining, light.progress)

            if args.cycles and cycles_done >= args.cycles:
                break

            time.sleep(interval)
    finally:
        display.close()
        if log:
            print("Ampel ausgeschaltet.", flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
