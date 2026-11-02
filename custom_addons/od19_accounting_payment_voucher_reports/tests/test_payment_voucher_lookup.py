# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestVoucherRetrospectiveLookup(AccountTestInvoicingCommon):
    """Back-link, register and report data used to audit already-paid bills."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.od19_require_vendor_bill_for_payment = True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _create_bill(self, amount=1000.0):
        bill = self.init_invoice(
            "in_invoice",
            partner=self.partner_a,
            invoice_date="2016-01-01",
            post=False,
            amounts=[amount],
        )
        bill.tax_invoice_ids.write(
            {
                "tax_invoice_number": "TEST-TAX-001",
                "tax_invoice_date": "2016-01-01",
            }
        )
        bill.action_post()
        return bill

    def _create_customer_invoice(self, amount=1000.0):
        return self.init_invoice(
            "out_invoice",
            partner=self.partner_a,
            invoice_date="2016-01-01",
            post=True,
            amounts=[amount],
        )

    def _prepare_vendor_payment(self, bill):
        wizard = (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=bill.ids)
            .create({"payment_date": "2016-01-01", "od19_prepare_payment": True})
        )
        return wizard._create_payments()

    def _register_customer_payment(self, invoice):
        wizard = (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=invoice.ids)
            .create({"payment_date": "2016-01-01"})
        )
        return wizard._create_payments()

    # ------------------------------------------------------------------
    # Back-link from the bill to its vouchers
    # ------------------------------------------------------------------
    def test_bill_back_link_lists_voucher(self):
        bill = self._create_bill()
        payment = self._prepare_vendor_payment(bill)
        self.assertIn(payment, bill.od19_payment_ids)
        self.assertEqual(bill.od19_voucher_count, 1)

    def test_back_link_survives_posting(self):
        bill = self._create_bill()
        payment = self._prepare_vendor_payment(bill)
        payment.action_od19_prepare()
        payment.action_od19_approve()
        payment.action_post()
        self.assertEqual(bill.payment_state, "paid")
        self.assertIn(payment, bill.od19_payment_ids)
        self.assertEqual(bill.od19_voucher_count, 1)

    def test_voucher_summary_shows_number_and_status(self):
        bill = self._create_bill()
        payment = self._prepare_vendor_payment(bill)
        payment.action_od19_prepare()
        self.assertIn(payment.od19_voucher_no, bill.od19_voucher_summary)
        self.assertIn(payment.state, bill.od19_voucher_summary)

    def test_open_vouchers_action_targets_payment(self):
        bill = self._create_bill()
        payment = self._prepare_vendor_payment(bill)
        action = bill.action_od19_open_vouchers()
        self.assertEqual(action["res_model"], "account.payment")
        self.assertEqual(action["domain"], [("id", "in", payment.ids)])

    # ------------------------------------------------------------------
    # Derived report data
    # ------------------------------------------------------------------
    def test_source_bills_helper_returns_bill(self):
        bill = self._create_bill()
        payment = self._prepare_vendor_payment(bill)
        self.assertEqual(payment._od19_get_source_bills(), bill)

    def test_source_total_matches_bill(self):
        bill = self._create_bill(amount=1000.0)
        payment = self._prepare_vendor_payment(bill)
        self.assertAlmostEqual(
            payment.od19_bill_total_amount, bill.amount_total, places=2
        )

    def test_payee_display_falls_back_to_partner(self):
        bill = self._create_bill()
        payment = self._prepare_vendor_payment(bill)
        self.assertEqual(payment.od19_payee_display, bill.partner_id.display_name)

    def test_direction_and_state_labels(self):
        bill = self._create_bill()
        payment = self._prepare_vendor_payment(bill)
        self.assertTrue(payment.od19_direction_label)
        self.assertTrue(payment._od19_prepare_state_label())
        self.assertTrue(payment._od19_state_label())

    # ------------------------------------------------------------------
    # Report rendering (catches template errors)
    # ------------------------------------------------------------------
    def test_payment_voucher_report_renders(self):
        bill = self._create_bill()
        payment = self._prepare_vendor_payment(bill)
        payment.action_od19_prepare()
        html, _rtype = self.env["ir.actions.report"]._render_qweb_html(
            "od19_accounting_payment_voucher_reports.action_report_payment_voucher",
            payment.ids,
        )
        self.assertIn(b"PAYMENT VOUCHER", html.upper())
        self.assertIn(payment.od19_voucher_no.encode(), html)

    def test_payment_receipt_report_renders(self):
        invoice = self._create_customer_invoice()
        payment = self._register_customer_payment(invoice)
        html, _rtype = self.env["ir.actions.report"]._render_qweb_html(
            "od19_accounting_payment_voucher_reports.action_report_payment_receipt",
            payment.ids,
        )
        self.assertIn(b"PAYMENT RECEIPT", html.upper())

    def test_register_report_renders(self):
        bill = self._create_bill()
        payment = self._prepare_vendor_payment(bill)
        html, _rtype = self.env["ir.actions.report"]._render_qweb_html(
            "od19_accounting_payment_voucher_reports.action_report_payment_voucher_register",
            payment.ids,
        )
        self.assertIn(b"PAYMENT VOUCHER REGISTER", html.upper())
