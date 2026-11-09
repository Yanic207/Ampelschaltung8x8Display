"""Tests für die reine Ampel-Zustandsmaschine (ohne Hardware)."""

import unittest

from ampel.phases import NEXT_PHASE, Phase, Timings, TrafficLight


class TimingsTest(unittest.TestCase):
    def test_duration_mapping(self):
        timings = Timings(rot=11, rot_gelb=1.5, gruen=7, gelb=2.5)
        self.assertEqual(timings.duration(Phase.ROT), 11)
        self.assertEqual(timings.duration(Phase.ROT_GELB), 1.5)
        self.assertEqual(timings.duration(Phase.GRUEN), 7)
        self.assertEqual(timings.duration(Phase.GELB), 2.5)

    def test_rejects_non_positive_durations(self):
        for kwargs in (
            {"rot": 0},
            {"rot_gelb": -1},
            {"gruen": 0},
            {"gelb": -0.5},
        ):
            with self.subTest(**kwargs), self.assertRaises(ValueError):
                Timings(**kwargs)


class TrafficLightTest(unittest.TestCase):
    def setUp(self):
        self.timings = Timings(rot=10, rot_gelb=2, gruen=8, gelb=3)
        self.light = TrafficLight(self.timings, start=Phase.ROT, now=0.0)

    def test_starts_red(self):
        self.assertIs(self.light.phase, Phase.ROT)
        self.assertAlmostEqual(self.light.remaining, 10.0)

    def test_phase_sequence(self):
        expected = [
            (9.999, Phase.ROT),
            (10.0, Phase.ROT_GELB),
            (11.999, Phase.ROT_GELB),
            (12.0, Phase.GRUEN),
            (19.999, Phase.GRUEN),
            (20.0, Phase.GELB),
            (22.999, Phase.GELB),
            (23.0, Phase.ROT),
        ]
        for now, phase in expected:
            with self.subTest(now=now):
                self.light.update(now)
                self.assertIs(self.light.phase, phase)

    def test_changed_flag(self):
        self.assertFalse(self.light.update(5.0))
        self.assertTrue(self.light.update(10.0))
        self.assertFalse(self.light.update(10.5))
        self.assertTrue(self.light.update(12.0))

    def test_remaining_and_progress(self):
        self.light.update(4.0)
        self.assertAlmostEqual(self.light.remaining, 6.0)
        self.assertAlmostEqual(self.light.progress, 0.4)

    def test_does_not_skip_phases_with_small_steps(self):
        # 46 s in 50-ms-Schritten: zwei vollständige Zyklen (2 × 23 s).
        now = 0.0
        changes = 0
        while now < 46.0:
            now += 0.05
            if self.light.update(now):
                changes += 1
        self.assertEqual(changes, 8)
        self.assertIs(self.light.phase, Phase.ROT)

    def test_backwards_time_is_ignored(self):
        self.light.update(5.0)
        self.light.update(3.0)
        self.assertAlmostEqual(self.light.elapsed, 5.0)
        self.assertIs(self.light.phase, Phase.ROT)

    def test_next_phase_cycle_is_closed(self):
        phase = Phase.ROT
        seen = [phase]
        for _ in range(4):
            phase = NEXT_PHASE[phase]
            seen.append(phase)
        self.assertEqual(seen[0], seen[-1])
        self.assertEqual(set(seen), set(Phase))


if __name__ == "__main__":
    unittest.main()
