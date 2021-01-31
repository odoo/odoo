# Copyright 2018 Tecnativa - Ernesto Tejeda
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0

from odoo.tests.common import TransactionCase


class TestWebDialogSize(TransactionCase):
    def setUp(self):
        super(TestWebDialogSize, self).setUp()

    def test_get_web_dialog_size_config(self):
        obj = self.env["ir.config_parameter"]

        self.assertFalse(obj.get_web_dialog_size_config()["default_maximize"])

        obj.set_param("web_dialog_size.default_maximize", "True")
        self.assertTrue(obj.get_web_dialog_size_config()["default_maximize"])

        obj.set_param("web_dialog_size.default_maximize", "False")
        self.assertFalse(obj.get_web_dialog_size_config()["default_maximize"])
