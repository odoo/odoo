# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.tests import HttpCase


@odoo.tests.tagged("-at_install", "post_install")
class TestGetModelDefinitions(HttpCase):
    def test_access_cr(self):
        with self.assertRaises(KeyError):
            self.env["ir.model"]._get_model_definitions(["res.users", "cr"])

    def test_access_all_model_fields(self):
        model_definitions = self.env["ir.model"]._get_model_definitions(
            ["res.users", "res.partner"]
        )
        self.assertIn("res.users", model_definitions)
        self.assertIn("res.partner", model_definitions)
        self.assertGreaterEqual(
            model_definitions["res.partner"]["fields"].keys(), {"active", "name", "user_ids"}
        )
        self.assertGreaterEqual(
            model_definitions["res.partner"]["fields"].keys(), {"active", "name", "user_ids"}
        )

    def test_relational_fields_with_missing_model(self):
        model_definitions = self.env["ir.model"]._get_model_definitions(["res.partner"])
        # since res.country is not requested, country_id shouldn't be in
        # the model definition fields
        self.assertNotIn("country_id", model_definitions["res.partner"]["fields"])
        model_definitions = self.env["ir.model"]._get_model_definitions(
            ["res.partner", "res.country"]
        )
        # res.country is requested, country_id should be present on res.partner
        self.assertIn("country_id", model_definitions["res.partner"]["fields"])
