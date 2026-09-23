import os
import unittest
from unittest.mock import patch

from odoo.tools.i18n import format_list
from odoo.tools.locale_utils import babel_locale_parse


class TestBabelLocaleParse(unittest.TestCase):
    def setUp(self):
        babel_locale_parse.cache_clear()
        self.addCleanup(babel_locale_parse.cache_clear)

    def test_latin_modifier_selects_the_latin_script(self):
        locale = babel_locale_parse("sr@latin")
        self.assertEqual((locale.language, locale.script), ("sr", "Latn"))
        self.assertEqual(
            format_list(None, ["a", "b", "c"], lang_code="sr@latin"), "a, b i c"
        )

    def test_cyrillic_modifier_selects_the_cyrillic_script(self):
        locale = babel_locale_parse("sr@Cyrl")
        self.assertEqual((locale.language, locale.script), ("sr", "Cyrl"))

    def test_plain_codes_parse_as_before(self):
        for code, expected in (
            ("en_US", "en_US"),
            ("es_419", "es_419"),
            ("zh_TW", "zh_Hant_TW"),
            ("fr", "fr"),
        ):
            with self.subTest(code=code):
                self.assertEqual(str(babel_locale_parse(code)), expected)

    def test_a_posix_code_set_is_not_part_of_the_locale(self):
        for code, expected in (
            ("fr_FR.UTF-8", "fr_FR"),
            ("es_MX.utf8", "es_MX"),
            ("sr_RS.UTF-8@latin", "sr_Latn_RS"),
        ):
            with self.subTest(code=code):
                self.assertEqual(str(babel_locale_parse(code)), expected)

    def test_unknown_code_falls_back_to_en_us_whatever_the_environment(self):
        with patch.dict(os.environ, {"LANG": "fr_FR.UTF-8", "LC_ALL": "fr_FR.UTF-8"}):
            for code in ("xx_XX", "", None):
                with self.subTest(code=code):
                    self.assertEqual(str(babel_locale_parse(code)), "en_US")


if __name__ == "__main__":
    unittest.main()
