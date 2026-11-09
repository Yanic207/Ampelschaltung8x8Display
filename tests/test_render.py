"""Tests für das 8x8-Pixelbild der Ampel."""

import unittest

from ampel.phases import Phase
from ampel.render import HEIGHT, WIDTH, empty_grid, render


class RenderTest(unittest.TestCase):
    def test_grid_dimensions(self):
        for phase in Phase:
            with self.subTest(phase=phase):
                grid = render(phase)
                self.assertEqual(len(grid), HEIGHT)
                self.assertTrue(all(len(row) == WIDTH for row in grid))

    def test_empty_grid(self):
        grid = empty_grid()
        self.assertEqual(len(grid), 8)
        self.assertFalse(any(any(row) for row in grid))

    def test_rot_lights_top_lamp(self):
        self._assert_lit(render(Phase.ROT), top=0)
        self._assert_dot(render(Phase.ROT), top=3)
        self._assert_dot(render(Phase.ROT), top=6)

    def test_yellow_lights_middle_lamp(self):
        self._assert_dot(render(Phase.GELB), top=0)
        self._assert_lit(render(Phase.GELB), top=3)
        self._assert_dot(render(Phase.GELB), top=6)

    def test_green_lights_bottom_lamp(self):
        self._assert_dot(render(Phase.GRUEN), top=0)
        self._assert_dot(render(Phase.GRUEN), top=3)
        self._assert_lit(render(Phase.GRUEN), top=6)

    def test_red_yellow_lights_both_top_lamps(self):
        grid = render(Phase.ROT_GELB)
        self._assert_lit(grid, top=0)
        self._assert_lit(grid, top=3)
        self._assert_dot(grid, top=6)

    def test_gap_rows_stay_dark(self):
        for phase in Phase:
            grid = render(phase)
            with self.subTest(phase=phase):
                self.assertFalse(any(grid[2]))
                self.assertFalse(any(grid[5]))

    def _assert_lit(self, grid, top):
        for y in (top, top + 1):
            for x in range(WIDTH):
                expected = 1 <= x <= 6
                self.assertEqual(grid[y][x], expected, f"y={y}, x={x}")

    def _assert_dot(self, grid, top):
        for y in (top, top + 1):
            for x in range(WIDTH):
                expected = x in (3, 4)
                self.assertEqual(grid[y][x], expected, f"y={y}, x={x}")


if __name__ == "__main__":
    unittest.main()
