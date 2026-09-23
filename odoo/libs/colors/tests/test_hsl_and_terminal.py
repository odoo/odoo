import re
import unittest

from odoo.libs.colors.conversions import (
    get_hsl_from_seed,
    get_lightness,
    get_saturation,
    hex_to_rgb,
    rgb_to_hex,
)
from odoo.libs.colors.terminal import BLUE, RED, colorize


class TestGetSaturation(unittest.TestCase):
    def test_greyscale_has_zero_saturation(self):
        self.assertEqual(get_saturation((0, 0, 0)), 0.0)
        self.assertEqual(get_saturation((128, 128, 128)), 0.0)
        self.assertEqual(get_saturation((255, 255, 255)), 0.0)

    def test_pure_red_is_fully_saturated(self):
        self.assertAlmostEqual(get_saturation((255, 0, 0)), 1.0)


class TestGetLightness(unittest.TestCase):
    def test_black_is_zero(self):
        self.assertEqual(get_lightness((0, 0, 0)), 0.0)

    def test_white_is_one(self):
        self.assertEqual(get_lightness((255, 255, 255)), 1.0)

    def test_midpoint(self):
        self.assertAlmostEqual(get_lightness((0, 255, 0)), 0.5)


class TestRgbToHex(unittest.TestCase):
    def test_round_trip(self):
        for rgb in [(255, 0, 0), (0, 128, 255), (17, 34, 51)]:
            self.assertEqual(hex_to_rgb(rgb_to_hex(rgb)), rgb)

    def test_format(self):
        self.assertEqual(rgb_to_hex((255, 0, 0)), "#ff0000")
        self.assertEqual(rgb_to_hex((0, 0, 0)), "#000000")


class TestHslFromSeed(unittest.TestCase):
    def test_deterministic(self):
        self.assertEqual(get_hsl_from_seed("agromarin"), get_hsl_from_seed("agromarin"))

    def test_different_seeds_can_differ(self):
        self.assertNotEqual(get_hsl_from_seed("seed-a"), get_hsl_from_seed("seed-b"))

    def test_format(self):
        self.assertRegex(get_hsl_from_seed("x"), r"^hsl\(\d+, \d+%, \d+%\)$")


class TestColorize(unittest.TestCase):
    def test_wraps_with_reset(self):
        result = colorize("hi", fg=RED)
        self.assertTrue(result.endswith("\033[0m"))
        self.assertIn("hi", result)

    def test_fg_and_bg_encoded(self):
        result = colorize("x", fg=RED, bg=BLUE)
        match = re.match(r"\033\[1;(\d+)m\033\[1;(\d+)mx", result)
        assert match is not None
        self.assertEqual(int(match.group(1)), 30 + RED)
        self.assertEqual(int(match.group(2)), 40 + BLUE)
