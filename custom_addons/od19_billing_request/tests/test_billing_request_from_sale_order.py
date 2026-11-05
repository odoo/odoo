# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
"""Create an AR billing request from a confirmed sale order.

Only the lines still open for billing (``qty_to_invoice > 0``) are pulled:
a line already invoiced in full never shows up, and a partially invoiced line
only brings its remaining quantity.
"""

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestBillingRequestFromSaleOrder(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.partner_a
        cls.product = cls.product_a
        # ``service`` avoids creating a delivery picking on confirm
        # (od19_delivery_label requires a DEPT code on outgoing pickings).
        cls.product.type = "service"
        cls.product.invoice_policy = "order"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _confirmed_so(self, lines):
        """``lines`` = [(name, qty, price), ...]."""
        so = self.env["sale.order"].sudo().create(
            {
                "partner_id": self.customer.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": qty,
                            "price_unit": price,
                            "name": name,
                        },
                    )
                    for name, qty, price in lines
                ],
            }
        )
        so.action_confirm()
        return so

    def _invoice_line(self, so_line, qty):
        """Post an invoice for ``qty`` on ``so_line`` (a prior bill)."""
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.customer.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": so_line.product_id.id,
                            "quantity": qty,
                            "price_unit": so_line.price_unit,
                            "sale_line_ids": [(6, 0, [so_line.id])],
                        },
                    )
                ],
            }
        )
        invoice.action_post()
        return invoice

    def _request_from(self, so):
        action = so.action_od19_create_billing_request()
        request = self.env["od19.billing.request"].browse(action["res_id"])
        return action, request

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------
    def test_confirmed_sale_order_creates_ar_request(self):
        so = self._confirmed_so([("Line A", 5.0, 100.0)])

        action, request = self._request_from(so)

        self.assertEqual(action["res_model"], "od19.billing.request")
        self.assertEqual(request.direction, "ar")
        self.assertEqual(request.origin_ref, so)
        self.assertEqual(request.partner_id, self.customer)
        self.assertEqual(len(request.line_ids), 1)
        self.assertEqual(request.line_ids.sale_line_id, so.order_line)
        self.assertAlmostEqual(request.line_ids.quantity, 5.0)

    def test_draft_sale_order_is_rejected(self):
        so = self.env["sale.order"].sudo().create(
            {
                "partner_id": self.customer.id,
                "order_line": [
                    (0, 0, {"product_id": self.product.id, "product_uom_qty": 1.0})
                ],
            }
        )

        with self.assertRaises(UserError):
            so.action_od19_create_billing_request()

    def test_fully_invoiced_line_is_not_pulled(self):
        so = self._confirmed_so([("Line A", 4.0, 100.0), ("Line B", 6.0, 50.0)])
        line_a, line_b = so.order_line
        self._invoice_line(line_a, 4.0)

        self.assertFalse(line_a.qty_to_invoice)
        self.assertAlmostEqual(line_b.qty_to_invoice, 6.0)

        _action, request = self._request_from(so)

        self.assertEqual(len(request.line_ids), 1)
        self.assertEqual(request.line_ids.sale_line_id, line_b)
        self.assertAlmostEqual(request.line_ids.quantity, 6.0)

    def test_partially_invoiced_line_pulls_remaining_only(self):
        so = self._confirmed_so([("Line A", 10.0, 100.0)])
        line_a = so.order_line
        self._invoice_line(line_a, 4.0)

        self.assertAlmostEqual(line_a.qty_to_invoice, 6.0)

        _action, request = self._request_from(so)

        self.assertEqual(len(request.line_ids), 1)
        self.assertAlmostEqual(request.line_ids.quantity, 6.0)

    def test_sale_order_form_button_view_exists(self):
        self.assertTrue(
            self.env.ref("od19_billing_request.view_order_form_od19_billing_request")
        )
