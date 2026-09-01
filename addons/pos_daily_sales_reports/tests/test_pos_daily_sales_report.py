# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo
from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@odoo.tests.tagged('post_install', '-at_install')
class TestPoSDailySalesReports(TestPoSCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.basic_config
        cls.PosOrder = cls.env["pos.order"]
        cls.partner_01 = cls.env["res.partner"].create({"name": "Test partner 1"})
        cls.tax_15 = cls.env["account.tax"].create(
            {
                "name": "TAX 15%",
                "amount_type": "percent",
                "type_tax_use": "sale",
                "amount": 15.0,
            }
        )
        cls.tax_5 = cls.env["account.tax"].create(
            {
                "name": "TAX 5%",
                "amount_type": "percent",
                "type_tax_use": "sale",
                "amount": 5.0,
            }
        )
        cls.tax = cls.env["account.tax"].create(
            {
                "name": "TAX 15%",
                "amount_type": "percent",
                "type_tax_use": "sale",
                "amount": 15.0,
            }
        )
        cls.product1 = cls.env["product.product"].create(
            {"name": "Test Product 1",
            "list_price": 10.0,
            "taxes_id": [(6, 0, (cls.tax_15 | cls.tax_5).ids)],
            }
        )

    def test_pos_total_discount(self):
        """Test that the total discount is correctly calculated in the POS daily sales report."""
        pos_session = self.open_new_session()

        orders = [
            self.create_ui_order_data(
                [(self.product1, 3, 10)], False)
        ]
        self.env["pos.order"].create_from_ui(orders)
        self.assertEqual(pos_session.get_total_discount(), 9.0)
