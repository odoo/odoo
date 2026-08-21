# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
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
                (6, 0, cls.env.user.group_ids.ids),
                (4, cls.env.ref("account.group_account_user").id),
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
        sale_order = (
            self
            .env["sale.order"]
            .create({
                "partner_id": self.partner_a.id,
                "partner_invoice_id": self.partner_a.id,
                "partner_shipping_id": self.partner_a.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "name": self.company_data["product_order_cost"].name,
                            "product_id": self.company_data["product_order_cost"].id,
                            "product_uom_qty": 2,
                            "qty_delivered": 1,
                            "price_unit": self.company_data["product_order_cost"].list_price,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": self.company_data["product_delivery_cost"].name,
                            "product_id": self.company_data["product_delivery_cost"].id,
                            "product_uom_qty": 4,
                            "qty_delivered": 1,
                            "price_unit": self.company_data["product_delivery_cost"].list_price,
                        },
                    ),
                ],
            })
        )

        sale_order.action_confirm()

        self.assertRecordValues(sale_order.order_line, [
            {'qty_delivered': 1.0},
            {'qty_delivered': 1.0},
        ])

    def test_qty_delivered_non_analytic_lines(self):

        sale_order = self.env['sale.order'].with_context(mail_notrack=True, mail_create_nolog=True).create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': self.company_data['product_delivery_no'].name,
                    'product_id': self.company_data['product_delivery_no'].id,
                    'product_uom_qty': 2,
                    'qty_delivered': 1,
                    'price_unit': self.company_data['product_delivery_no'].list_price,
                }),
                (0, 0, {
                    'name': "Note Line",
                    'display_type': "line_note",
                }),
            ],
        })

        sale_order.action_confirm()

        self.assertRecordValues(sale_order.order_line, [
            {'qty_delivered': 1.0},
            {'qty_delivered': 0.0},
        ])

        self.assertTrue(sale_order.show_deliver_button)

        sale_order.deliver_sold_quantity()

        self.assertRecordValues(sale_order.order_line, [
            {'qty_delivered': 2.0},
            {'qty_delivered': 0.0},
        ])

        self.assertFalse(sale_order.show_deliver_button)

    def test_outgoing_qty_after_overdelivered_so(self):
        """Test that outgoing, forecasted and free-to-use quantities are computed correctly
        when the delivered quantity exceeds the ordered quantity.
        """
        if self.env["ir.module.module"]._get("stock").state == "installed":
            self.skipTest("This test won't work if stock is installed, as these "
                "quantities are computed from stock moves and stock quants.")
        product = self.product
        product.is_storable = True
        product.qty_available = 100
        so = self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "order_line": [Command.create({"product_id": product.id, "product_uom_qty": 10})],
        })
        so.action_confirm()
        self.assertEqual(product.outgoing_qty, 10)
        self.assertEqual(product.free_qty, 90)
        self.assertEqual(product.virtual_available, 90)
        so.order_line.qty_delivered = 20
        product.invalidate_recordset(["outgoing_qty"])
        self.assertEqual(product.outgoing_qty, 0)
        self.assertEqual(product.free_qty, 80)
        self.assertEqual(product.virtual_available, 80)
