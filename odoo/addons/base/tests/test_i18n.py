from odoo.tests import TransactionCase
from odoo.tools.i18n import format_list


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
