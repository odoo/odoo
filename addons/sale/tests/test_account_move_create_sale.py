from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestCreateSaleOrder(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.user.group_ids += cls.env.ref("sale.group_sale_salesman")

        cls.customer = cls.env["res.partner"].create(
            {
                "name": "Test Customer",
                "customer_rank": 1,
            }
        )

        cls.product_saleable = cls.env["product.product"].create(
            {
                "name": "Saleable Product",
                "type": "consu",
                "sale_ok": True,
            }
        )

    def _create_invoice(self, line_vals):
        return self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.customer.id,
                "invoice_date": fields.Date.context_today(self.env.user),
                "invoice_line_ids": [(0, 0, line_vals)],
            }
        )

    def test_create_sale_order_success(self):
        invoice = self._create_invoice(
            {
                "product_id": self.product_saleable.id,
                "quantity": 5,
                "price_unit": 50.0,
            }
        )
        invoice.action_post()

        result = invoice.create_sale_order()

        self.assertTrue(result, "Should return True on success")

        so = self.env["sale.order"].search(
            [
                ("partner_id", "=", self.customer.id),
                ("origin", "=", invoice.name),
            ],
            limit=1,
        )

        self.assertTrue(so, "Sale order should be created")
        self.assertEqual(
            so.partner_id, self.customer, "SO should have correct customer"
        )
        self.assertEqual(len(so.line_ids), 1, "SO should have one line")
        self.assertEqual(
            so.line_ids.product_id,
            self.product_saleable,
            "SO line should have correct product",
        )
        self.assertEqual(
            invoice.invoice_line_ids.sale_line_ids,
            so.line_ids,
            "The move line should be linked to the created SO line",
        )

    def test_create_sale_order_no_product_error(self):
        invoice = self._create_invoice(
            {
                "name": "Service without product",
                "quantity": 1,
                "price_unit": 100.0,
            }
        )

        with self.assertRaises(UserError) as context:
            invoice.create_sale_order()

        self.assertIn(
            "product",
            str(context.exception).lower(),
            "Error should mention missing product",
        )

    def test_create_sale_order_idempotent_when_one_exists(self):
        invoice = self._create_invoice(
            {
                "product_id": self.product_saleable.id,
                "quantity": 5,
                "price_unit": 50.0,
            }
        )
        invoice.action_post()

        invoice.create_sale_order()

        invoice.create_sale_order()

        sos = self.env["sale.order"].search(
            [
                ("partner_id", "=", self.customer.id),
                ("origin", "=", invoice.name),
            ],
        )
        self.assertEqual(
            len(sos),
            1,
            "Second create_sale_order call must not duplicate the SO",
        )

    def test_create_sale_order_raises_when_duplicates_exist(self):
        invoice = self._create_invoice(
            {
                "product_id": self.product_saleable.id,
                "quantity": 5,
                "price_unit": 50.0,
            }
        )
        invoice.action_post()

        for _dummy in range(2):
            self.env["sale.order"].create(
                {
                    "partner_id": self.customer.id,
                    "origin": invoice.name,
                },
            )

        with self.assertRaises(UserError) as context:
            invoice.create_sale_order()

        self.assertIn(
            "more than one",
            str(context.exception).lower(),
            "Error should mention the multiple-SO condition",
        )
