# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestVendorBillRequiredForPayment(AccountTestInvoicingCommon):
    """AP bill-first rule: ต้องตั้งหนี้ (Vendor Bill) ก่อนถึงจะจ่ายชำระได้."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.od19_require_vendor_bill_for_payment = True

    def _create_standalone_payment(self, payment_type, partner_type):
        return self.env["account.payment"].create(
            {
                "payment_type": payment_type,
                "partner_type": partner_type,
                "partner_id": self.partner_a.id,
                "amount": 100.0,
                "journal_id": self.company_data["default_journal_bank"].id,
            }
        )

    def test_outbound_without_bill_is_blocked(self):
        payment = self._create_standalone_payment("outbound", "supplier")
        with self.assertRaises(UserError):
            payment.action_post()

    def test_outbound_from_vendor_bill_is_allowed(self):
        bill = self.init_invoice(
            "in_invoice",
            partner=self.partner_a,
            invoice_date="2016-01-01",
            post=False,
            amounts=[100.0],
        )
        # เอกสารซื้อของไทยต้องมีเลขที่/วันที่ใบกำกับภาษีก่อน post
        # (ข้อกำหนดของ OCA l10n_th_account_tax)
        bill.tax_invoice_ids.write(
            {
                "tax_invoice_number": "TEST-TAX-001",
                "tax_invoice_date": "2016-01-01",
            }
        )
        bill.action_post()
        payment = (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=bill.ids)
            .create({"payment_date": "2016-01-01"})
            ._create_payments()
        )
        self.assertEqual(payment.payment_type, "outbound")
        self.assertIn(payment.state, ("in_process", "paid"))

    def test_inbound_without_invoice_is_not_blocked(self):
        payment = self._create_standalone_payment("inbound", "customer")
        # Must not raise: the rule only guards the payables (outbound) side.
        payment._od19_check_vendor_bill_required()

    def test_setting_disabled_allows_standalone_outbound(self):
        self.env.company.od19_require_vendor_bill_for_payment = False
        payment = self._create_standalone_payment("outbound", "supplier")
        payment._od19_check_vendor_bill_required()

    def test_bypass_context_allows_standalone_outbound(self):
        payment = self._create_standalone_payment("outbound", "supplier")
        payment.with_context(od19_skip_vendor_bill_check=True)._od19_check_vendor_bill_required()
