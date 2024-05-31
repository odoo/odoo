import inspect
from unittest.mock import patch

from odoo.tests import common
from odoo.tools.translate import GettextAlias


class TestGettextAlias(common.TransactionCase):

    @patch("odoo.tools.translate.code_translations.get_python_translations")
    @patch("odoo.modules.get_resource_from_path")
    @patch.object(GettextAlias, "_get_lang", return_value="fr_FR")
    def test_get_translation_with_current_frame(self, mock_get_lang, mock_get_resource_from_path, mock_get_python_translations):
        source = "hello"
        module = "test_module"
        lang = "fr_FR"

        mock_get_python_translations.return_value = {source: "bonjour"}

        mock_get_resource_from_path.return_value = [module, "path/to/module"]

        result = GettextAlias()._get_translation(source, module=module)

        mock_get_lang.assert_called_with(inspect.currentframe())
        mock_get_python_translations.assert_called_with(module, lang)
        self.assertEqual(result, "bonjour")

    @patch("odoo.tools.translate.code_translations.get_python_translations")
    @patch("odoo.modules.get_resource_from_path")
    @patch.object(GettextAlias, "_get_lang", return_value="fr_FR")
    def test_get_translation_with_one_frame_deeper(self, mock_get_lang, mock_get_resource_from_path, mock_get_python_translations):
        source = "hello"
        module = "test_module"
        lang = "fr_FR"

        mock_get_python_translations.return_value = {source: "bonjour"}

        mock_get_resource_from_path.return_value = [module, "path/to/module"]

        def go_deeper_one_frame():
            return GettextAlias()._get_translation(source, module=module)

        result = go_deeper_one_frame()

        mock_get_lang.assert_called_with(inspect.currentframe())
        mock_get_python_translations.assert_called_with(module, lang)
        self.assertEqual(result, "bonjour")
