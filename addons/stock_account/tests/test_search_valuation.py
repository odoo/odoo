from odoo.exceptions import UserError

from odoo.addons.stock_account.tests.common import TestStockValuationCommon


class TestSearchValuation(TestStockValuationCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product_periodic = cls.env["product.template"].create(
            {
                "name": "Periodic categ product",
                "categ_id": cls.category_standard.id,
            }
        )
        cls.product_real_time = cls.env["product.template"].create(
            {
                "name": "Real time categ product",
                "categ_id": cls.category_standard_auto.id,
            }
        )
        cls.category_no_valuation = cls.env["product.category"].create(
            {"name": "No categ valuation", "property_valuation": False}
        )
        cls.product_company_fallback = cls.env["product.template"].create(
            {
                "name": "Company fallback product",
                "categ_id": cls.category_no_valuation.id,
                "company_id": cls.company.id,
            }
        )

    def test_invalid_operator_raises(self):
        with self.assertRaises(UserError):
            self.env["product.template"].search([("valuation", ">", "periodic")])

    def test_invalid_value_raises(self):
        with self.assertRaises(UserError):
            self.env["product.template"].search([("valuation", "=", "bogus")])

    def test_matches_category_property_valuation(self):
        found = self.env["product.template"].search(
            [
                ("id", "in", (self.product_periodic + self.product_real_time).ids),
                ("valuation", "=", "periodic"),
            ]
        )
        self.assertEqual(found, self.product_periodic)

    def test_not_equal_operator_flips_the_match(self):
        found = self.env["product.template"].search(
            [
                ("id", "in", (self.product_periodic + self.product_real_time).ids),
                ("valuation", "!=", "periodic"),
            ]
        )
        self.assertEqual(found, self.product_real_time)

    def test_falls_back_to_company_inventory_valuation(self):
        self.assertFalse(self.category_no_valuation.property_valuation)
        self.assertEqual(self.company.stock_config_id.inventory_valuation, "periodic")
        found = self.env["product.template"].search(
            [
                ("id", "=", self.product_company_fallback.id),
                ("valuation", "=", "periodic"),
            ]
        )
        self.assertEqual(found, self.product_company_fallback)
