import unittest
from unittest.mock import patch

from odoo.tools import translate
from odoo.tools.translate import get_text_content, get_translation

_FRENCH = {
    "Hello": "Bonjour",
    "Hello %(name)s": "Bonjour %(name)s",
    "Discount %(rate)s": "Remise %(rate)s %%",
    "Hello %s": "Bonjour %s",
}


def _render(source, args):
    with patch.object(
        translate.code_translations,
        "get_python_translations",
        return_value=_FRENCH,
    ):
        return get_translation("base", "fr_FR", source, args)


class TestMappingArguments(unittest.TestCase):
    def test_translation_without_placeholders_is_kept(self):
        with self.assertNoLogs("odoo.tools.translate", level="ERROR"):
            self.assertEqual(_render("Hello", {"name": "Ana"}), "Bonjour")

    def test_named_placeholder_is_formatted(self):
        self.assertEqual(_render("Hello %(name)s", {"name": "Ana"}), "Bonjour Ana")

    def test_escaped_percent_is_not_a_positional_placeholder(self):
        with self.assertNoLogs("odoo.tools.translate", level="ERROR"):
            self.assertEqual(_render("Discount %(rate)s", {"rate": 5}), "Remise 5 %")

    def test_positional_placeholder_with_a_mapping_falls_back_to_the_source(self):
        with self.assertLogs("odoo.tools.translate", level="ERROR"):
            self.assertEqual(
                _render("Hello %s", {"name": "Ana"}), "Hello {'name': 'Ana'}"
            )


class TestTextContent(unittest.TestCase):
    def test_a_term_without_a_document_has_no_text(self):
        for term in ("", "   ", "\n", "<!-- note -->"):
            with self.subTest(term=term):
                self.assertEqual(get_text_content(term), "")

    def test_markup_is_stripped_and_whitespace_collapsed(self):
        self.assertEqual(get_text_content("<b>a \n b</b>"), "a b")


if __name__ == "__main__":
    unittest.main()
