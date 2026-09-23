import unittest
from unittest.mock import MagicMock

from odoo.tools.convert import xml_import


def _importer(idref=None, found=("ir.ui.view", 1469)):
    env = MagicMock()
    env.return_value = env
    env.context = {}
    env.__getitem__.return_value._xmlid_to_res_model_res_id.return_value = found
    importer = xml_import(env, "mymod", idref, "update")
    return importer, env.registry.record_xmlid_resolved


class TestConvertRecordsResolvedRefs(unittest.TestCase):
    def test_a_ref_looked_up_in_the_database_is_recorded(self):
        importer, record = _importer()
        self.assertEqual(importer.id_get("website.configurator_s_cover"), 1469)
        record.assert_called_once_with("website.configurator_s_cover", 1469)

    def test_a_ref_answered_by_an_earlier_record_of_the_load_is_recorded(self):
        importer, record = _importer(idref={"mymod.parent": 7})
        self.assertEqual(importer.id_get("parent"), 7)
        record.assert_called_once_with("mymod.parent", 7)

    def test_a_ref_that_resolves_to_nothing_is_not_recorded(self):
        importer, record = _importer(found=(False, False))
        self.assertFalse(importer.id_get("website.gone", raise_if_not_found=False))
        record.assert_not_called()
