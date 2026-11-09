# Simulierte Ampel auf 8×8-LED-Matrix (MAX7219 / ME042)

Eine kleine, realistische Ampelschaltung für ein **8×8-Red-LED-Dot-Matrix-Modul
mit MAX7219** (ME042 / FC-16) am **Raspberry Pi 4B**.

Das Modul zeigt eine klassische Ampel mit drei Lampen. Die Phasen folgen der
deutschen Lichtsignalanlage:

```
Rot ──► Rot-Gelb ──► Grün ──► Gelb ──► Rot …
```

Die Ampel startet nach dem Einschalten **immer mit Rot** – ein sicherer
Zustand, niemals direkt Grün. Alle Zeiten sind einstellbar.

```
██████      ← Rot      (aktive Lampe: breiter Balken)
██████
            (Lücke)
 ··██··     ← Gelb     (inaktive Lampe: kleiner Punkt)
 ··██··
            (Lücke)
 ··██··     ← Grün
 ··██··
```

> Auf dem Modul leuchten alle LEDs rot. Welche Lampe aktiv ist, erkennt man an
> der **Position und Form** des Balkens. Die Terminal-Vorschau färbt die Lampen
> zusätzlich rot/gelb/grün ein, damit man die Phase sofort sieht.

---

## 1. Hardware und Verdrahtung

### Benötigt

- Raspberry Pi 4B (jede Variante)
- ME042 / FC-16 8×8-LED-Matrixmodul mit MAX7219 (5 V)
- 5 Jumper-Kabel (female–female)
- Stromversorgung für den Pi (offizielles 5-V-Netzteil, ≥ 3 A empfohlen)
- Optional: Pegelwandler (siehe Hinweis unten)

### Anschluss

| ME042 / MAX7219 | Raspberry Pi 4B | Pin-Nr. | Funktion |
|---|---|---|---|
| **VCC** | 5 V | 2 oder 4 | Versorgung des Moduls (5 V) |
| **GND** | GND | 6 | gemeinsame Masse |
| **DIN** | GPIO10 | 19 | SPI0 MOSI – Daten zum Modul |
| **CS** | GPIO8 | 24 | SPI0 CE0 – Chip-Select |
| **CLK** | GPIO11 | 23 | SPI0 SCLK – Takt |

```
  ME042 / MAX7219                    Raspberry Pi 4B
  ┌──────────────┐                   ┌─────────────────────┐
  │ VCC ─────────┼───────────────────┤ 5V          Pin 2/4 │
  │ GND ─────────┼───────────────────┤ GND         Pin 6   │
  │ DIN ─────────┼───────────────────┤ GPIO10      Pin 19  │  SPI0 MOSI
  │ CS  ─────────┼───────────────────┤ GPIO8       Pin 24  │  SPI0 CE0
  │ CLK ─────────┼───────────────────┤ GPIO11      Pin 23  │  SPI0 SCLK
  └──────────────┘                   └─────────────────────┘
```

**Wichtig:**

- **DIN** ist der Dateneingang des Moduls (nicht DOUT – das ist der Ausgang für
  weitere verkettete Module).
- Manche Module beschriften **CS** auch mit **LOAD** oder **CSN**. Die
  Reihenfolge der 5 Pins ist nicht bei allen Herstellern gleich – bitte die
  Beschriftung auf der Platine prüfen.
- Nutzt du den zweiten Chip-Select, verbinde **CS** mit **GPIO7 (Pin 26)** und
  starte mit `--spi-device 1`.
- **Niemals 5 V auf einen GPIO-Eingang des Pi geben.** Die GPIOs sind nur
  3,3 V-tolerant. Das Modul liefert keine 5 V an den Pi zurück, die Verbindung
  in der Tabelle ist also sicher.
- Ein einzelnes Modul kann über den 5-V-Pin des Pi versorgt werden. Bei mehreren
  verketteten Modulen besser ein separates 5-V-Netzteil mit gemeinsamer Masse
  verwenden.
- **Pegel:** Der MAX7219 erwartet bei 5 V Versorgung laut Datenblatt ≥ 3,5 V
  High-Pegel, der Pi liefert 3,3 V. In der Praxis funktioniert das meist
  zuverlässig. Für einen dauerhaft stabilen Aufbau empfiehlt sich ein
  Pegelwandler (z. B. 74HCT125 oder TXS0108E) für CLK, DIN und CS.

---

## 2. Raspberry Pi vorbereiten

Benötigt wird **Python ≥ 3.9**; empfohlen ist Raspberry Pi OS **Bookworm** oder
neuer (dort ist Python 3.11 enthalten).

### SPI aktivieren

```bash
sudo raspi-config
```

→ **Interface Options** → **SPI** → **Yes** → neu starten.

Prüfen:

```bash
ls -l /dev/spidev0.0
```

Die Datei muss existieren.

### Software installieren

```bash
sudo apt update
sudo apt install -y python3-venv python3-pil python3-spidev

cd ~/Ampelschaltung8x8Display
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`--system-site-packages` sorgt dafür, dass das virtuelle Environment die per
`apt` installierten Pakete `spidev` und `Pillow` mitbenutzt. So muss auf dem Pi
nichts kompiliert werden.

> **Tipp:** Raspberry Pi OS in der 64-Bit-Version (`aarch64`) verwenden. Auf
> einem 32-Bit-System zieht `luma.led_matrix` zusätzlich das optionale
> WS2812-Paket `rpi_ws281x` nach, das kompiliert werden muss – dann vorher
> `sudo apt install -y build-essential python3-dev` ergänzen.

Falls der Zugriff auf `/dev/spidev0.0` verweigert wird, den Benutzer in die
Gruppen `spi` und `gpio` aufnehmen und neu anmelden:

```bash
sudo usermod -aG spi,gpio "$USER"
```

---

## 3. Starten

### Erst ohne Hardware testen (empfohlen)

Das geht auf dem Pi, aber auch auf jedem Mac/PC – es werden weder `luma` noch
Pillow benötigt. Auf einem Mac/PC genügt es, den Projektordner zu kopieren und
den Befehl dort auszuführen; eine Installation ist nicht erforderlich:

```bash
python3 -m ampel --driver ascii
```

Im Terminal erscheint die Ampel farbig und aktualisiert sich an Ort und Stelle.
Mit **Strg+C** beenden.

### Auf dem echten Modul

```bash
source .venv/bin/activate
python3 -m ampel --driver max7219
```

Beim Start werden die Phasenwechsel zusätzlich auf der Konsole protokolliert.
Mit **Strg+C** wird die Ampel sauber beendet und das Display ausgeschaltet.

Beispiele:

```bash
# Etwas dunkler (angenehmer für die Augen)
python3 -m ampel --driver max7219 --intensity 32

# Schneller Testdurchlauf: ein kompletter Zyklus, dann Ende
python3 -m ampel --driver ascii --rot 2 --rot-gelb 1 --gruen 2 --gelb 1 --cycles 1

# Andere Zeiten (Sekunden)
python3 -m ampel --driver max7219 --rot 12 --rot-gelb 2 --gruen 10 --gelb 3
```

---

## 4. Optionen

| Option | Standard | Bedeutung |
|---|---|---|
| `--driver max7219` | ✓ | Ausgabe auf dem LED-Modul |
| `--driver ascii` | | Vorschau im Terminal (ohne Hardware) |
| `--rot` | 10.0 | Dauer der Rotphase in Sekunden |
| `--rot-gelb` | 2.0 | Dauer Rot-Gelb in Sekunden |
| `--gruen` | 8.0 | Dauer der Grünphase in Sekunden |
| `--gelb` | 3.0 | Dauer der Gelbphase in Sekunden |
| `--cycles N` | 0 | Nach N vollständigen Zyklen beenden (0 = unendlich) |
| `--fps` | 10.0 | Abtastrate der Simulation |
| `--intensity 0-255` | 64 | Helligkeit des Moduls |
| `--cascade N` | 1 | Anzahl verketteter 8×8-Module |
| `--spi-port N` | 0 | SPI-Bus (`/dev/spidev0.x`) |
| `--spi-device 0/1` | 0 | CE0 (GPIO8) oder CE1 (GPIO7) |
| `--rotate 0-3` | 0 | Bild um 90°-Schritte drehen |
| `--block-orientation` | 0 | Blockausrichtung: `0`, `90`, `-90` oder `180` |
| `--reverse` | aus | Reihenfolge verketteter Module umkehren |
| `--quiet` | aus | Keine Statusmeldungen (nur bei `max7219`) |

Alle Optionen mit Beschreibung: `python3 -m ampel --help`

### Bildausrichtung anpassen

Die richtige Ausrichtung hängt davon ab, wie das Modul montiert ist. Zielbild:
**Rot oben, Gelb in der Mitte, Grün unten.**

| Anzeige | Lösung |
|---|---|
| Kopfstehend | `--rotate 2` |
| Um 90° gedreht | `--rotate 1` oder `--rotate 3` |
| Spiegelverkehrt / falsch gedreht | `--block-orientation -90` oder `--block-orientation 90` |
| Mehrere Module in falscher Reihenfolge | `--reverse` |

Die Terminal-Vorschau (`--driver ascii`) zeigt immer das gewünschte Bild und
eignet sich gut zum Vergleichen.

---

## 5. Automatischer Start mit systemd

Die Datei [`contrib/ampel.service`](contrib/ampel.service) ist vorbereitet.
Passe darin **Benutzer und Pfad** an (standardmäßig `pi` und
`/home/pi/Ampelschaltung8x8Display`):

```bash
sudo cp contrib/ampel.service /etc/systemd/system/ampel.service
sudo systemctl daemon-reload
sudo systemctl enable --now ampel
```

Status und Logs:

```bash
systemctl status ampel
journalctl -u ampel -f
```

Beenden bzw. deaktivieren:

```bash
sudo systemctl stop ampel
sudo systemctl disable ampel
```

---

## 6. Fehlersuche

| Problem | Mögliche Ursache | Lösung |
|---|---|---|
| `SPI device not found` / `No such file or directory` | SPI nicht aktiviert | `sudo raspi-config` → SPI einschalten, neu starten, `/dev/spidev0.0` prüfen |
| `Permission denied` auf `/dev/spidev0.0` | Benutzer nicht in der Gruppe `spi` | `sudo usermod -aG spi,gpio "$USER"`, neu anmelden |
| Modul bleibt dunkel | Helligkeit zu niedrig, Verkabelung, Modul nicht mit Strom versorgt | `--intensity 255` testen; VCC/GND und DIN/CLK prüfen |
| Zufällige Pixel / Flackern | CLK und DIN vertauscht oder Wackelkontakt | Verkabelung prüfen, Kabel kurz halten |
| Bild kopfstehend oder gedreht | Montagerichtung | `--rotate` / `--block-orientation` siehe oben |
| `ModuleNotFoundError: No module named 'luma'` | venv nicht aktiviert oder Installation fehlgeschlagen | `source .venv/bin/activate` und `pip install -r requirements.txt` |
| Modul wird warm | normal, besonders bei hoher Helligkeit | `--intensity` reduzieren |

---

## 7. Projektstruktur und Tests

```
ampel/
├── phases.py      # Phasenfolge und Zustandsmaschine (reine Logik)
├── render.py      # 8×8-Pixelbild der Ampel (reine Daten)
├── displays.py    # MAX7219-Hardware und ASCII-Vorschau
└── __main__.py    # Kommandozeile und Hauptschleife
tests/             # 23 Unit-Tests, laufen ohne Hardware
contrib/
└── ampel.service  # systemd-Unit für den Autostart
```

Tests ausführen (ohne Raspberry Pi, ohne installierte Hardware-Pakete):

```bash
python3 -m unittest discover -s tests -v
```

---

## 8. Ideen für Erweiterungen

- **Fußgängertaster** an GPIO17: Bei Anforderung verkürzt sich die Grünphase,
  danach folgt zuverlässig Rot.
- **Zweites Modul** für die Querrichtung: Das Modul unterstützt Verkettung
  (`DOUT` → `DIN`); mit `--cascade 2` wird die Ampel aktuell auf beide Module
  gespiegelt. Für eine echte Kreuzung müsste pro Modul eine eigene Phase
  gerendert werden.
- **Nachtmodus**: Gelbes Blinklicht zu bestimmten Uhrzeiten.
- **Akustiksignal** für Blinde über einen Buzzer an einem freien GPIO.

---

## Sicherheitshinweis

Dieses Projekt ist eine **Simulation für ein LED-Matrixmodul**. Es ist nicht
dafür gedacht, echte Lichtsignalanlagen oder Geräte mit Netzspannung zu
steuern. Arbeiten an 230-V-Anlagen gehören ausschließlich in die Hände einer
qualifizierten Elektrofachkraft.
