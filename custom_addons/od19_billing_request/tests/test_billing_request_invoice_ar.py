from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestBillingRequestInvoiceAR(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.partner_a
        cls.product = cls.product_a
        # ``service`` avoids creating a delivery picking on confirm
        # (od19_delivery_label requires a DEPT code on outgoing pickings).
        cls.product.type = "service"
        cls.product.invoice_policy = "order"
        cls.company = cls.env.company
        cls.company.od19_ar_require_evidence = False

    def _submitted_request(self, qty=2.0):
        so = self.env["sale.order"].sudo().create(
            {
                "partner_id": self.customer.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 5.0,
                            "price_unit": 100.0,
                            "name": self.product.name,
                        },
                    )
                ],
            }
        )
        so.action_confirm()
        request = self.env["od19.billing.request"].create(
            {
                "direction": "ar",
                "partner_id": self.customer.id,
                "origin_ref": "sale.order,%s" % so.id,
            }
        )
        request._od19_pull_apply(so, so.order_line)
        request.line_ids.write({"quantity": qty})
        request.action_submit()
        return request, so

    def test_create_invoice_links_target_and_line(self):
        request, so = self._submitted_request()
        move = request.action_create_invoice()
        self.assertEqual(move.move_type, "out_invoice")
        self.assertEqual(request.target_move_id, move)
        self.assertEqual(request.state, "invoiced")
        self.assertAlmostEqual(move.invoice_line_ids.quantity, 2.0)
        self.assertEqual(move.invoice_line_ids.sale_line_ids, so.order_line)
        self.assertEqual(request.line_ids.target_line_id, move.invoice_line_ids)

    def test_create_invoice_twice_is_blocked(self):
        request, _so = self._submitted_request()
        request.action_create_invoice()
        with self.assertRaises(UserError):
            request.action_create_invoice()

    def test_create_invoice_links_lines_in_sequence_order(self):
        """Each request line maps to the move line of the same product."""
        so = self.env["sale.order"].sudo().create(
            {
                "partner_id": self.customer.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 4.0,
                            "price_unit": 100.0,
                            "name": "Line A",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 6.0,
                            "price_unit": 50.0,
                            "name": "Line B",
                        },
                    ),
                ],
            }
        )
        so.action_confirm()
        request = self.env["od19.billing.request"].create(
            {
                "direction": "ar",
                "partner_id": self.customer.id,
                "origin_ref": "sale.order,%s" % so.id,
            }
        )
        request._od19_pull_apply(so, so.order_line)
        request.action_submit()
        move = request.action_create_invoice()
        self.assertEqual(len(move.invoice_line_ids), 2)
        for request_line in request.line_ids:
            self.assertTrue(request_line.target_line_id)
            self.assertEqual(request_line.target_line_id.name, request_line.name)
            self.assertAlmostEqual(
                request_line.target_line_id.quantity, request_line.quantity
            )

    def test_create_invoice_uses_request_company(self):
        """The bill must belong to the request's company (multi-company)."""
        data = self.setup_other_company()
        other_company = data["company"]
        other_company.od19_ar_require_evidence = False
        request = (
            self.env["od19.billing.request"]
            .with_company(other_company)
            .create(
                {
                    "direction": "ar",
                    "partner_id": self.customer.id,
                    "company_id": other_company.id,
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "product_id": self.product.id,
                                "name": "Service",
                                "quantity": 1.0,
                                "price_unit": 10.0,
                            },
                        )
                    ],
                }
            )
        )
        request.action_submit()
        move = request.action_create_invoice()
        self.assertEqual(move.company_id, other_company)
        self.assertEqual(request.company_id, other_company)
