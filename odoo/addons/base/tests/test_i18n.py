from odoo.tests import TransactionCase
from odoo.tools import format_list, py_to_js_locale


class I18nTest(TransactionCase):
    def test_format_list(self):
        lang = self.env["res.lang"]

        formatted_text = format_list(self.env, ["Mario", "Luigi"])
        self.assertEqual(formatted_text, "Mario and Luigi", "Should default to English.")

        formatted_text = format_list(self.env, ["To be", "Not to be"], "or")
        self.assertEqual(formatted_text, "To be or Not to be", "Should take the style into account.")

        lang._activate_lang("fr_FR")

        formatted_text = format_list(lang.with_context(lang="fr_FR").env, ["Athos", "Porthos", "Aramis"])
        self.assertEqual(formatted_text, "Athos, Porthos et Aramis", "Should use the language of the user.")

        formatted_text = format_list(
            lang.with_context(lang="en_US").env, ["Athos", "Porthos", "Aramis"], lang_code="fr_FR",
        )
        self.assertEqual(formatted_text, "Athos, Porthos et Aramis", "Should use the chosen language.")

    def test_py_to_js_locale(self):
        self.assertEqual(py_to_js_locale("tg"), "tg")
        self.assertEqual(py_to_js_locale("kab"), "kab")
        self.assertEqual(py_to_js_locale("fr_BE"), "fr-BE")
        self.assertEqual(py_to_js_locale("es_419"), "es-419")
        self.assertEqual(py_to_js_locale("sr@latin"), "sr-Latn")
        self.assertEqual(py_to_js_locale("sr@Cyrl"), "sr-Cyrl")
        self.assertEqual(py_to_js_locale("sr_RS@latin"), "sr-Latn-RS")
        self.assertEqual(py_to_js_locale("fr-TG"), "fr-TG")
