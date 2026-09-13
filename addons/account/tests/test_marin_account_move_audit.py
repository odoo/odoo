from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestMailTemplateSelection(AccountTestInvoicingCommon):
    def test_empty_recordset_gets_the_invoice_template(self):
        self.assertEqual(
            self.env["account.move"].browse()._get_mail_template(),
            self.env.ref("account.email_template_edi_invoice"),
        )

    def test_send_wizard_without_a_move_gets_the_invoice_template(self):
        wizard = self.env["account.move.send.wizard"].new({})
        self.assertFalse(wizard.move_id)
        self.assertEqual(
            wizard.template_id,
            self.env.ref("account.email_template_edi_invoice"),
        )

    def test_a_mixed_recordset_falls_back_to_the_invoice_template(self):
        refund = self.init_invoice("out_refund", amounts=[100.0])
        invoice = self.init_invoice("out_invoice", amounts=[100.0])
        self.assertEqual(
            (refund | invoice)._get_mail_template(),
            self.env.ref("account.email_template_edi_invoice"),
        )

    def test_a_uniform_refund_recordset_still_gets_the_credit_note_template(self):
        refunds = self.init_invoice("out_refund", amounts=[100.0]) | self.init_invoice(
            "out_refund", amounts=[200.0]
        )
        self.assertEqual(
            refunds._get_mail_template(),
            self.env.ref("account.email_template_edi_credit_note"),
        )


@tagged("post_install", "-at_install")
class TestAlertsAreKeyedByUser(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.accountant = cls.env["res.users"].create(
            {
                "name": "Audit accountant",
                "login": "audit_accountant",
                "group_ids": [
                    Command.set(
                        [
                            cls.env.ref("base.group_user").id,
                            cls.env.ref("account.group_account_manager").id,
                            cls.env.ref("account.group_account_user").id,
                        ]
                    )
                ],
            }
        )
        cls.plain = cls.env["res.users"].create(
            {
                "name": "Audit plain",
                "login": "audit_plain",
                "group_ids": [Command.set([cls.env.ref("base.group_user").id])],
            }
        )

    def _locked_draft_invoice(self):
        invoice = self.init_invoice(
            "out_invoice", amounts=[100.0], invoice_date="2020-01-15", post=False
        )
        invoice.company_id.sudo().fiscalyear_lock_date = "2021-12-31"
        invoice.invalidate_recordset()
        self.assertTrue(invoice.tax_lock_date_message)
        return invoice

    def test_the_reading_order_does_not_decide_the_answer(self):
        invoice = self._locked_draft_invoice()

        invoice.invalidate_recordset(["alerts"])
        accountant_first = invoice.with_user(self.accountant).alerts
        plain_second = invoice.with_user(self.plain).alerts

        invoice.invalidate_recordset(["alerts"])
        plain_first = invoice.with_user(self.plain).alerts
        accountant_second = invoice.with_user(self.accountant).alerts

        self.assertEqual(accountant_first, accountant_second)
        self.assertEqual(plain_first, plain_second)

    def test_the_lock_date_alert_stays_with_the_accountant(self):
        invoice = self._locked_draft_invoice()
        invoice.invalidate_recordset(["alerts"])

        self.assertIn(
            "account_tax_lock_date", invoice.with_user(self.accountant).alerts
        )
        self.assertNotIn(
            "account_tax_lock_date", invoice.with_user(self.plain).alerts or {}
        )


@tagged("post_install", "-at_install")
class TestInvoiceCurrencyRateDepends(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_currency = cls.setup_other_currency("EUR")

    def test_the_declaration_names_the_inputs_that_discard_a_manual_rate(self):
        field = self.env["account.move"]._fields["invoice_currency_rate"]
        self.assertEqual(
            tuple(self.env.registry.field_depends[field]),
            (
                "currency_id",
                "company_currency_id",
                "company_id",
                "invoice_date",
                "taxable_supply_date",
            ),
        )

    def test_a_manual_rate_survives_the_dates_a_post_moves(self):
        invoice = self.init_invoice(
            "out_invoice",
            amounts=[100.0],
            currency=self.other_currency,
            invoice_date="2016-01-01",
            post=False,
        )
        invoice.invoice_currency_rate = 42.0
        invoice.write({"date": "2016-02-01", "delivery_date": "2016-01-15"})
        invoice.action_post()
        self.assertEqual(invoice.invoice_currency_rate, 42.0)

    def test_the_rate_still_follows_the_date(self):
        invoice = self.init_invoice(
            "out_invoice",
            amounts=[100.0],
            currency=self.other_currency,
            invoice_date="2016-01-01",
            post=False,
        )
        first = invoice.invoice_currency_rate
        invoice.invoice_date = "2017-01-01"
        self.assertNotEqual(invoice.invoice_currency_rate, first)
        self.assertEqual(invoice.invoice_currency_rate, invoice.expected_currency_rate)

    def test_the_refresh_button_and_the_compute_share_one_body(self):
        invoice = self.init_invoice(
            "out_invoice",
            amounts=[100.0],
            currency=self.other_currency,
            invoice_date="2016-01-01",
            post=False,
        )
        invoice.invoice_currency_rate = 42.0
        invoice.refresh_invoice_currency_rate()
        self.assertEqual(invoice.invoice_currency_rate, invoice.expected_currency_rate)


@tagged("post_install", "-at_install")
class TestReportFilenames(AccountTestInvoicingCommon):
    def test_a_numberless_draft_still_produces_a_filename(self):
        invoice = self.init_invoice("out_invoice", amounts=[100.0], post=False)
        invoice.name = False
        report = self.env.ref("account.account_invoices").copy(
            {
                "print_report_name": False,
                "name": "audit report without a name expression",
            }
        )
        self.assertEqual(
            invoice._get_invoice_report_filename(report=report),
            f"{invoice._get_move_display_name()}.pdf",
        )

    def test_the_proforma_filename_is_unchanged(self):
        invoice = self.init_invoice("out_invoice", amounts=[100.0], post=False)
        self.assertTrue(
            invoice._get_invoice_proforma_pdf_report_filename().endswith(
                "_proforma.pdf"
            )
        )


@tagged("post_install", "-at_install")
class TestQrCodeDoesNotWriteOnReadOnlyPaths(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.reader = cls.env["res.users"].create(
            {
                "name": "Audit reader",
                "login": "audit_reader",
                "group_ids": [
                    Command.set(
                        [
                            cls.env.ref("base.group_user").id,
                            cls.env.ref("account.group_account_readonly").id,
                        ]
                    )
                ],
            }
        )

    def test_a_reader_can_render_a_qr_code_without_write_access(self):
        invoice = self.init_invoice("out_invoice", amounts=[100.0], post=True)
        self.assertFalse(invoice.with_user(self.reader).has_access("write"))
        invoice.with_user(self.reader)._update_qr_code_method("ch_qr")
        self.assertFalse(
            invoice.qr_code_method,
            "a reader who cannot write the move must not write to it",
        )

    def test_a_writer_still_remembers_the_detected_method(self):
        invoice = self.init_invoice("out_invoice", amounts=[100.0], post=True)
        invoice._update_qr_code_method("ch_qr")
        self.assertEqual(invoice.qr_code_method, "ch_qr")


@tagged("post_install", "-at_install")
class TestCurrencyRateRpcIsGuarded(AccountTestInvoicingCommon):
    def test_a_portal_user_cannot_read_a_rate_through_a_move_they_cannot_read(self):
        portal = self.env["res.users"].create(
            {
                "name": "Audit portal",
                "login": "audit_portal",
                "group_ids": [Command.set([self.env.ref("base.group_portal").id])],
            }
        )
        invoice = self.init_invoice("out_invoice", amounts=[100.0], post=True)
        with self.assertRaises(AccessError):
            invoice.with_user(portal).get_currency_rate(
                self.env.company.id, self.env.company.currency_id.id, "2020-01-01"
            )

    def test_an_accountant_still_gets_a_rate(self):
        invoice = self.init_invoice("out_invoice", amounts=[100.0], post=True)
        self.assertEqual(
            invoice.get_currency_rate(
                self.env.company.id, self.env.company.currency_id.id, "2020-01-01"
            ),
            1.0,
        )
