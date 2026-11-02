from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestBillingRequestInvoiceAP(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.partner_a
        cls.product = cls.product_a
        cls.product.purchase_method = "purchase"
        cls.company = cls.env.company
        cls.company.od19_ap_require_original = True

    def _submitted_request(self):
        po = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_qty": 3.0,
                            "price_unit": 40.0,
                            "name": self.product.name,
                            "date_planned": "2026-11-10 00:00:00",
                        },
                    )
                ],
            }
        )
        # button_confirm is gated by the procurement approval flow
        # (od19_purchase_procurement_core): a PO must be approved first.
        po.action_od19_submit_for_approval()
        po.action_od19_approve()
        po.button_confirm()
        request = self.env["od19.billing.request"].create(
            {"direction": "ap", "partner_id": self.vendor.id, "origin_ref": po}
        )
        request._od19_pull_apply(po, po.order_line)
        request.action_submit()
        return request

    def test_ap_blocked_without_original(self):
        request = self._submitted_request()
        with self.assertRaises(UserError):
            request.action_create_invoice()

    def test_ap_requires_verified_evidence(self):
        request = self._submitted_request()
        request.original_received = True
        with self.assertRaises(UserError):
            request.action_create_invoice()

    def test_ap_creates_vendor_bill_when_gates_pass(self):
        request = self._submitted_request()
        request.original_received = True
        request.original_received_date = "2026-11-02"
        request.original_received_by_id = self.env.user.id
        evidence_type = self.env.ref(
            "od19_billing_request.evidence_type_vendor_tax_invoice"
        )
        attachment = self.env["ir.attachment"].create(
            {"name": "tax.pdf", "datas": "bW9jaw=="}
        )
        self.env["od19.billing.evidence"].create(
            {
                "name": "VAT-001",
                "billing_request_id": request.id,
                "evidence_type_id": evidence_type.id,
                "is_verified": True,
                "attachment_ids": [(4, attachment.id)],
            }
        )
        move = request.action_create_invoice()
        self.assertEqual(move.move_type, "in_invoice")
        self.assertEqual(request.state, "invoiced")
