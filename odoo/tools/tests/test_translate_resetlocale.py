import locale
import unittest

from odoo.tools.translate import get_locales, resetlocale


def _set_first(lang):
    for name in get_locales(lang):
        try:
            return locale.setlocale(locale.LC_ALL, name)
        except locale.Error:
            continue
    return None


class TestResetLocale(unittest.TestCase):
    def setUp(self):
        original = locale.setlocale(locale.LC_ALL)
        self.addCleanup(locale.setlocale, locale.LC_ALL, original)
        self.environment = locale.setlocale(locale.LC_ALL, "")

    def test_reset_restores_the_environment_locale_not_the_current_one(self):
        for lang in ("en_GB", "fr_FR", "de_DE", "es_MX"):
            applied = _set_first(lang)
            if applied and applied != self.environment:
                break
        else:
            self.skipTest("no installed locale differs from the environment's")
        self.assertEqual(resetlocale(), self.environment)
        self.assertEqual(locale.setlocale(locale.LC_ALL), self.environment)


class TestGetLocales(unittest.TestCase):
    def test_candidates_are_unique_and_end_with_the_bare_code(self):
        candidates = list(get_locales("en_GB"))
        self.assertEqual(len(candidates), len(set(candidates)))
        self.assertEqual(candidates[0], "en_GB.utf8")
        self.assertEqual(candidates[-1], "en_GB")


if __name__ == "__main__":
    unittest.main()
