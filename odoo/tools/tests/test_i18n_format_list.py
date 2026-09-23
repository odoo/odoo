import csv
import unittest

from odoo.tools.i18n import format_list
from odoo.tools.misc import file_open


class TestFormatList(unittest.TestCase):
    def test_english_standard(self):
        self.assertEqual(
            format_list(None, ["a", "b", "c"], lang_code="en_US"), "a, b, and c"
        )

    def test_two_items(self):
        self.assertEqual(format_list(None, ["a", "b"], lang_code="en_US"), "a and b")

    def test_single_item(self):
        self.assertEqual(format_list(None, ["a"], lang_code="en_US"), "a")

    def test_empty_list(self):
        self.assertEqual(format_list(None, [], lang_code="en_US"), "")

    def test_or_style(self):
        self.assertEqual(
            format_list(None, ["a", "b", "c"], style="or", lang_code="en_US"),
            "a, b, or c",
        )

    def test_localised_separator(self):
        french = format_list(None, ["a", "b", "c"], lang_code="fr_FR")
        self.assertNotEqual(french, "a, b, and c")
        self.assertIn("et", french)

    def test_non_string_items_are_stringified(self):
        self.assertEqual(format_list(None, [1, 2, 3], lang_code="en_US"), "1, 2, and 3")

    def test_generator_input(self):
        self.assertEqual(
            format_list(None, (c for c in "abc"), lang_code="en_US"), "a, b, and c"
        )

    def test_unknown_style_falls_back_to_standard(self):
        self.assertEqual(
            format_list(
                None,
                ["a", "b"],
                style="no-such-style",  # type: ignore[arg-type]
                lang_code="en_US",
            ),
            "a and b",
        )

    def test_unit_styles_are_accepted(self):
        for style in ("unit", "unit-short", "unit-narrow"):
            with self.subTest(style=style):
                out = format_list(
                    None, ["3 ft", "7 in"], style=style, lang_code="en_US"
                )
                self.assertIn("3 ft", out)
                self.assertIn("7 in", out)

    def test_every_style_renders_in_every_shipped_language(self):
        # a locale may define a style only in part (es_MX `unit-short` has an
        # `end` and no `start`); such a style falls back instead of raising
        with file_open("base/data/res.lang.csv") as handle:
            codes = [row["code"] for row in csv.DictReader(handle)]
        styles = (
            "standard",
            "standard-short",
            "or",
            "or-short",
            "unit",
            "unit-short",
            "unit-narrow",
        )
        for code in codes:
            for style in styles:
                with self.subTest(code=code, style=style):
                    out = format_list(
                        None, ["a", "b", "c"], style=style, lang_code=code
                    )
                    self.assertTrue(all(item in out for item in "abc"))

    def test_unparseable_lang_code_still_renders(self):
        self.assertIn("a", format_list(None, ["a", "b"], lang_code="not_a_locale"))


if __name__ == "__main__":
    unittest.main()
