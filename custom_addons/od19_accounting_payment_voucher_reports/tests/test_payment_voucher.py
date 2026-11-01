# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests.common import TransactionCase


# ``res.partner`` carries fields made required by other installed modules (for
# instance ``group_rfq`` from ``purchase_stock``). While this module is being
# installed the registry does not carry them yet, so the class runs during
# ``post_install`` where the registry is complete.
@tagged("post_install", "-at_install")
class TestPaymentVoucherNumber(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {"name": "Test Partner", "is_company": True}
        )
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "Test Bank",
                "code": "TBNK",
                "type": "bank",
                "company_id": cls.env.company.id,
            }
        )

    def _create_payment(self, payment_type, partner_type):
        return self.env["account.payment"].create(
            {
                "payment_type": payment_type,
                "partner_type": partner_type,
                "partner_id": self.partner.id,
                "amount": 1000.0,
                "journal_id": self.journal.id,
                "date": "2026-10-21",
            }
        )

    def test_supplier_payment_gets_pv_number(self):
        payment = self._create_payment("outbound", "supplier")
        self.assertFalse(payment.od19_voucher_no)
        payment._od19_assign_voucher_number()
        self.assertTrue(payment.od19_voucher_no)
        self.assertTrue(payment.od19_voucher_no.startswith("PV"))

    def test_customer_payment_gets_rv_number(self):
        payment = self._create_payment("inbound", "customer")
        payment._od19_assign_voucher_number()
        self.assertTrue(payment.od19_voucher_no)
        self.assertTrue(payment.od19_voucher_no.startswith("RV"))

    def test_voucher_number_is_not_reassigned(self):
        payment = self._create_payment("outbound", "supplier")
        payment._od19_assign_voucher_number()
        first_number = payment.od19_voucher_no
        payment._od19_assign_voucher_number()
        self.assertEqual(payment.od19_voucher_no, first_number)

    def test_prepare_assigns_number_and_audit_fields(self):
        payment = self._create_payment("outbound", "supplier")
        self.assertEqual(payment.od19_prepare_state, "draft")
        payment.action_od19_prepare()
        self.assertTrue(payment.od19_voucher_no)
        self.assertEqual(payment.od19_prepare_state, "prepared")
        self.assertEqual(payment.od19_prepared_by, self.env.user)
        self.assertTrue(payment.od19_prepared_date)

    def test_approve_requires_prepare(self):
        payment = self._create_payment("outbound", "supplier")
        with self.assertRaises(UserError):
            payment.action_od19_approve()

    def test_approve_records_approver(self):
        payment = self._create_payment("outbound", "supplier")
        payment.action_od19_prepare()
        payment.action_od19_approve()
        self.assertEqual(payment.od19_prepare_state, "approved")
        self.assertEqual(payment.od19_approved_by, self.env.user)
        self.assertTrue(payment.od19_approved_date)

    def test_prepare_denied_when_not_draft(self):
        payment = self._create_payment("outbound", "supplier")
        payment.state = "in_process"
        with self.assertRaises(UserError):
            payment.action_od19_prepare()

    def test_prepare_keeps_number_stable(self):
        payment = self._create_payment("outbound", "supplier")
        payment.action_od19_prepare()
        first_number = payment.od19_voucher_no
        payment.action_od19_approve()
        payment._od19_assign_voucher_number()
        self.assertEqual(payment.od19_voucher_no, first_number)


@tagged("post_install", "-at_install")
class TestPreparePaymentFromWizard(AccountTestInvoicingCommon):
    """The "Prepare payment" option of the Register Payment wizard."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.od19_require_vendor_bill_for_payment = True

    def _register_payment(self, bill, prepare):
        wizard = (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=bill.ids)
            .create(
                {
                    "payment_date": "2016-01-01",
                    "od19_prepare_payment": prepare,
                }
            )
        )
        return wizard._create_payments()

    def _create_bill(self, amount=1000.0):
        bill = self.init_invoice(
            "in_invoice",
            partner=self.partner_a,
            invoice_date="2016-01-01",
            post=False,
            amounts=[amount],
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
        return bill

    def test_prepare_option_keeps_payment_in_draft(self):
        bill = self._create_bill()
        payment = self._register_payment(bill, prepare=True)
        self.assertEqual(payment.state, "draft")
        self.assertTrue(payment.od19_pending_reconcile_line_ids)
        self.assertFalse(payment.od19_voucher_no)
        self.assertEqual(bill.payment_state, "not_paid")

    def test_prepared_payment_posts_and_settles_bill(self):
        bill = self._create_bill()
        payment = self._register_payment(bill, prepare=True)
        payment.action_od19_prepare()
        payment.action_od19_approve()
        payment.action_post()
        self.assertTrue(payment.od19_voucher_no.startswith("PV"))
        # Posting settles the source bill; depending on whether the outstanding
        # account is reconcilable the payment lands on "in_process" or directly
        # on "paid" (same outcome as the standard register-payment flow).
        self.assertIn(payment.state, ("in_process", "paid"))
        self.assertEqual(bill.payment_state, "paid")

    def test_standard_register_payment_still_posts_immediately(self):
        bill = self._create_bill()
        payment = self._register_payment(bill, prepare=False)
        self.assertIn(payment.state, ("in_process", "paid"))
        self.assertEqual(bill.payment_state, "paid")
