# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
"""Create an AP billing request from a confirmed purchase order.

The form button only shows when the order carries at least one line that is
billable straight from the order (product ``purchase_method == 'purchase'``
and ``qty_to_invoice > 0``); a line whose ``purchase_method == 'receive'``
never shows it - that line is billed from the receipt transfer instead. A
source line already referenced by an active request is never pulled twice.
"""

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestBillingRequestFromPurchaseOrder(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.partner_a
        cls.service_product = cls.product_a
        # ``service`` lines need to be billed on the ordered quantity
        # (purchase method), otherwise ``qty_to_invoice`` stays at zero.
        cls.service_product.type = "service"
        cls.service_product.purchase_method = "purchase"
        # Goods product billed on *received* quantities: the button stays
        # hidden on such an order because the line must be billed from the
        # receipt transfer (``purchase_method != 'purchase'``).
        cls.goods_product = cls.env["product.product"].create(
            {
                "name": "PO Goods Product",
                "type": "consu",
                "is_storable": False,
                "purchase_method": "receive",
                "standard_price": 40.0,
            }
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _new_po(self, lines, product=None):
        """``lines`` = [(name, qty, price), ...]."""
        product = product or self.service_product
        return self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_qty": qty,
                            "price_unit": price,
                            "name": name,
                            "date_planned": "2026-11-10 00:00:00",
                        },
                    )
                    for name, qty, price in lines
                ],
            }
        )

    def _confirmed_po(self, lines, product=None):
        po = self._new_po(lines, product=product)
        # ``button_confirm`` is gated by the procurement approval flow
        # (od19_purchase_procurement_core): a PO must be approved first.
        po.action_od19_submit_for_approval()
        po.action_od19_approve()
        po.button_confirm()
        return po

    def _request_from(self, po):
        action = po.action_od19_create_billing_request()
        request = self.env["od19.billing.request"].browse(action["res_id"])
        return action, request

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------
    def test_confirmed_purchase_order_creates_ap_request(self):
        po = self._confirmed_po([("Service", 3.0, 40.0)])

        action, request = self._request_from(po)

        self.assertEqual(action["res_model"], "od19.billing.request")
        self.assertEqual(request.direction, "ap")
        self.assertEqual(request.origin_ref, po)
        self.assertEqual(request.partner_id, self.vendor)
        self.assertEqual(len(request.line_ids), 1)
        self.assertEqual(request.line_ids.purchase_line_id, po.order_line)
        self.assertAlmostEqual(request.line_ids.quantity, 3.0)

    def test_draft_purchase_order_is_rejected(self):
        po = self._new_po([("Service", 1.0, 40.0)])

        with self.assertRaises(UserError):
            po.action_od19_create_billing_request()

    def test_service_order_shows_button(self):
        po = self._confirmed_po([("Service", 3.0, 40.0)])

        self.assertTrue(po.od19_billing_request_available)

    def test_received_policy_line_hides_button(self):
        """Control Policy = 'On received quantities': ยังไม่รับของจึงยังเปิดบิล
        จากใบสั่งซื้อไม่ได้ (ต้องไปเปิดจากใบรับของแทน)."""
        po = self._confirmed_po([("Goods", 3.0, 40.0)], product=self.goods_product)

        self.assertEqual(po.order_line.product_id.purchase_method, "receive")
        self.assertEqual(po.order_line.qty_to_invoice, 0.0)
        self.assertFalse(po.od19_billing_request_available)

    def test_ordered_policy_goods_shows_button(self):
        """Control Policy = 'On ordered quantities': เปิดบิลจากใบสั่งซื้อได้ทันที
        แม้เป็นสินค้า (ไม่ผูกกับ product type อีกต่อไป)."""
        product = self.env["product.product"].create(
            {
                "name": "PO Goods Ordered Policy",
                "type": "consu",
                "is_storable": False,
                "purchase_method": "purchase",
                "standard_price": 40.0,
            }
        )
        po = self._confirmed_po([("Goods", 3.0, 40.0)], product=product)

        self.assertGreater(po.order_line.qty_to_invoice, 0.0)
        self.assertTrue(po.od19_billing_request_available)

    def test_line_already_requested_is_not_pulled_twice(self):
        po = self._confirmed_po([("Service", 3.0, 40.0)])

        _action, first = self._request_from(po)
        self.assertEqual(len(first.line_ids), 1)

        _action, second = self._request_from(po)
        self.assertFalse(second.line_ids)

    def test_purchase_order_form_button_view_exists(self):
        self.assertTrue(
            self.env.ref(
                "od19_billing_request.view_purchase_order_form_od19_billing_request"
            )
        )
