# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.sale.tests.common import TestSaleCommon


@tagged("at_install", "-post_install")  # LEGACY at_install
class TestSaleFlow(TestSaleCommon):
    """Test running at-install to test flows independently to other modules, e.g. 'sale_stock'."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        user = cls.env["res.users"].create({
            "name": "Because I am saleman!",
            "login": "saleman",
            "group_ids": [
                Command.set(cls.env.user.group_ids.ids),
                Command.link(cls.env.ref("account.group_account_user").id),
            ],
        })
        user.partner_id.email = "saleman@test.com"

        # Shadow the current environment/cursor with the newly created user.
        cls.env = cls.env(user=user)
        cls.cr = cls.env.cr

        cls.partner_a = cls.env["res.partner"].create({"name": "partner_a", "company_id": False})

        cls.analytic_plan = cls.env["account.analytic.plan"].create({"name": "Plan"})

        cls.analytic_account = cls.env["account.analytic.account"].create({
            "name": "Test analytic_account",
            "code": "analytic_account",
            "plan_id": cls.analytic_plan.id,
            "company_id": cls.company.id,
            "partner_id": cls.partner_a.id,
        })

        user.company_ids |= cls.company
        user.company_id = cls.company

    def test_qty_delivered(self):
        """Test 'qty_delivered' at-install to avoid the change when 'sale_stock' is installed."""
        sale_order = self.env["sale.order"].create({
            "partner_id": self.partner_a.id,
            "partner_invoice_id": self.partner_a.id,
            "partner_shipping_id": self.partner_a.id,
            "order_line": [
                Command.create({
                    "name": self.company_data["product_order_cost"].name,
                    "product_id": self.company_data["product_order_cost"].id,
                    "product_uom_qty": 2,
                    "qty_delivered": 1,
                    "price_unit": self.company_data["product_order_cost"].list_price,
                }),
                Command.create({
                    "name": self.company_data["product_delivery_cost"].name,
                    "product_id": self.company_data["product_delivery_cost"].id,
                    "product_uom_qty": 4,
                    "qty_delivered": 1,
                    "price_unit": self.company_data["product_delivery_cost"].list_price,
                }),
            ],
        })

        sale_order.action_confirm()

        self.assertRecordValues(
            sale_order.order_line, [{"qty_delivered": 1.0}, {"qty_delivered": 1.0}]
        )

    def test_so_is_delivered_when_consumable_lines_are_delivered(self):
        """Test 'delivery_status' at-install to avoid the change when 'sale_stock' is installed."""
        sale_order = self.env["sale.order"].create({
            "partner_id": self.partner_a.id,
            "partner_invoice_id": self.partner_a.id,
            "partner_shipping_id": self.partner_a.id,
            "order_line": [
                Command.create({
                    "product_id": self.company_data["product_order_cost"].id,
                    "product_uom_qty": 2,
                }),
                Command.create({
                    "product_id": self.company_data["product_service_order"].id,
                    "product_uom_qty": 1,
                }),
            ],
        })
        sale_order.action_confirm()

        sale_order.order_line.filtered(
            lambda line: line.product_id == self.company_data["product_order_cost"]
        ).qty_delivered = 2

        self.assertEqual(sale_order.delivery_status, "full")
