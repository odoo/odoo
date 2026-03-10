# Copyright (C) 2020  KMEE INFORMATICA LTDA
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo.tests.common import TransactionCase


class TestUomUom(TransactionCase):
    def setUp(self):
        super().setUp()
        self.uom_uom_kg = self.env.ref("uom.product_uom_kgm")

    def test_uom_uom_alternative(self):
        uom_uom_alternative = self.env["uom.uom.alternative"].create(
            {"code": "kg", "uom_id": self.uom_uom_kg.id}
        )

        self.assertIn(uom_uom_alternative, self.uom_uom_kg.alternative_ids)

        self.assertEqual(
            self.env["uom.uom"].search([("code", "=", "KG")]),
            self.env["uom.uom"].search([("code", "=", "kg")]),
        )
