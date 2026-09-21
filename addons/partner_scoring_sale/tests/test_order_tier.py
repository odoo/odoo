from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "partner_scoring_sale")
class TestOrderTier(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Tier = cls.env["partner.tier"]
        Tier.search([]).write({"active": False})
        cls.low = Tier.create(
            {"name": "Order Low", "min_value": 0.0, "max_value": 50.0}
        )
        cls.high = Tier.create(
            {"name": "Order High", "min_value": 50.0, "max_value": 0.0}
        )
        cls.customer = cls.env["res.partner"].create(
            {"name": "Tiered Customer", "is_company": True}
        )
        cls.customer._score_refresh()
        cls.contact = cls.env["res.partner"].create(
            {"name": "Tiered Contact", "parent_id": cls.customer.id, "type": "invoice"}
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Tiered Product", "list_price": 10.0}
        )

    def _order(self, partner):
        return self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "line_ids": [(0, 0, {"product_id": self.product.id})],
            }
        )

    def test_a_quotation_follows_the_customers_tier_through_the_contact(self):
        self.assertEqual(self.customer.tier_id, self.low)
        order = self._order(self.contact)
        self.assertEqual(order.tier_id, self.low)
        self.customer.score_line_ids.sudo().write(
            {"points": 100.0, "max_points": 100.0}
        )
        self.customer._score_reclassify()
        self.assertEqual(self.customer.tier_id, self.high)
        self.assertEqual(order.tier_id, self.high)

    def test_a_confirmed_order_keeps_the_tier_it_was_sold_under(self):
        order = self._order(self.customer)
        order.action_confirm()
        self.assertEqual(order.tier_id, self.low)
        self.customer.score_line_ids.sudo().write(
            {"points": 100.0, "max_points": 100.0}
        )
        self.customer._score_reclassify()
        self.assertEqual(self.customer.tier_id, self.high)
        self.assertEqual(order.tier_id, self.low)
        self.env.flush_all()
        report = self.env["sale.report"].search([("name", "=", order.name)])
        self.assertTrue(report)
        self.assertEqual(report.tier_id, self.low)
