from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBillingRequestGuards(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.env["res.partner"].create({"name": "BR Customer"})
        # ``service`` avoids creating an outgoing delivery picking on confirm
        # (od19_delivery_label requires a DEPT code on those pickings).
        cls.product = cls.env["product.product"].create(
            {"name": "BR Widget", "type": "service", "list_price": 50.0}
        )
        cls.product.invoice_policy = "order"
        cls.so = cls.env["sale.order"].create(
            {
                "partner_id": cls.customer.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product.id,
                            "product_uom_qty": 10.0,
                            "price_unit": 50.0,
                            "name": cls.product.name,
                        },
                    )
                ],
            }
        )
        cls.so.action_confirm()
        cls.sale_line = cls.so.order_line

    def _request_with(self, qty):
        return self.env["od19.billing.request"].create(
            {
                "direction": "ar",
                "partner_id": self.customer.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "sale_line_id": self.sale_line.id,
                            "quantity": qty,
                            "price_unit": 50.0,
                        },
                    )
                ],
            }
        )

    def test_quantity_ordered_and_remaining(self):
        request = self._request_with(4.0)
        line = request.line_ids
        self.assertAlmostEqual(line.qty_ordered, 10.0)
        self.assertAlmostEqual(line.remaining_to_bill, 6.0)

    def test_over_bill_is_blocked(self):
        with self.assertRaises(ValidationError):
            self._request_with(11.0)

    def test_second_request_cannot_exceed_remaining(self):
        self._request_with(6.0)
        with self.assertRaises(ValidationError):
            self._request_with(5.0)

    def test_zero_quantity_is_blocked(self):
        with self.assertRaises(ValidationError):
            self._request_with(0.0)

    def test_externally_invoiced_line_is_blocked(self):
        # Invoice the SO line directly in Odoo (outside this module) for the
        # full ordered qty, then a billing request must be blocked.
        self.so._create_invoices()
        self.so.invoice_ids.action_post()
        self.sale_line.invalidate_recordset(["qty_invoiced"])
        self.assertAlmostEqual(self.sale_line.qty_invoiced, 10.0)
        with self.assertRaises(ValidationError):
            self._request_with(1.0)
