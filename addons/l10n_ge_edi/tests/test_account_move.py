from datetime import datetime

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from odoo.addons.l10n_ge_edi.tests import stub_responses
from odoo.addons.l10n_ge_edi.tests.common import TestL10nGeEdiCommon
from odoo.addons.l10n_ge_edi.tools.rsge_client import (
    KIND_SUBMIT_FAILED,
    RSGE_TRANSIENT_ERROR_KINDS,
    RSGE_VAT_TYPE_EXEMPT,
    RSGE_VAT_TYPE_TAXABLE,
    RSGE_VAT_TYPE_ZERO_RATED,
    get_rsge_vat_type,
)


@tagged("post_install_l10n", "post_install", "-at_install")
class TestL10nGeEdiAccountMove(TestL10nGeEdiCommon, TestAccountMoveSendCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_ge.l10n_ge_edi_un_id = "1149251"

    def _create_ge_invoice(self, move_type="out_invoice", prices=(100.0,)):
        invoice = self.env["account.move"].create({
            "move_type": move_type,
            "partner_id": self.partner_ge.id,
            "invoice_date": "2026-01-15",
            "invoice_line_ids": [
                Command.create({"name": f"Line {index}", "quantity": 1.0, "price_unit": price, "tax_ids": [Command.set(self.tax_18.ids)]})
                for index, price in enumerate(prices, start=1)
            ],
        })
        invoice.action_post()
        return invoice

    def _send_to_rsge(self, invoice):
        """Put `invoice` through the real send wizard, so a journey starts from a genuinely sent one."""
        self._stub_rsge(
            save_invoice=stub_responses.save_invoice(invois_id=700123),
            save_invoice_desc=stub_responses.save_invoice_desc(id=800001),
            change_invoice_status=stub_responses.change_invoice_status(),
            get_invoice=stub_responses.get_invoice(status=1),
        )
        self.create_send_and_print(invoice).action_send_and_print()

    def _confirmed_ge_invoice(self):
        """A sent-and-confirmed invoice, the only state RS.ge lets a correction be created against."""
        invoice = self._create_ge_invoice()
        self._send_to_rsge(invoice)
        self._stub_rsge(get_invoice=stub_responses.get_invoice(status=2))
        invoice.action_l10n_ge_edi_refresh_status()
        return invoice

    def _k_invoice_wizard(self, invoice):
        return self.env["l10n_ge_edi.k_invoice.wizard"].create({"move_id": invoice.id})

    def test_invoice_is_registered_then_confirmed_by_the_buyer(self):
        invoice = self._create_ge_invoice(prices=(100.0, 250.0))
        self._stub_rsge(
            save_invoice=stub_responses.save_invoice(invois_id=700123),
            save_invoice_desc=[stub_responses.save_invoice_desc(id=800001), stub_responses.save_invoice_desc(id=800002)],
            change_invoice_status=stub_responses.change_invoice_status(),
            get_invoice=stub_responses.get_invoice(status=1, reg_dt="2026-01-15T10:30:00"),
        )

        self.create_send_and_print(invoice).action_send_and_print()

        self.assertEqual(invoice.l10n_ge_edi_state, "sent")
        self.assertEqual(invoice.l10n_ge_edi_invoice_id, "700123")
        self.assertEqual(invoice.l10n_ge_edi_f_series, "AA")
        self.assertEqual(invoice.l10n_ge_edi_f_number, "12345")
        # RS.ge reports reg_dt in Georgian local time (+04), Odoo stores naive UTC
        self.assertEqual(invoice.l10n_ge_edi_registration_date, datetime(2026, 1, 15, 6, 30))
        self.assertEqual(invoice.invoice_line_ids.mapped("l10n_ge_edi_line_id"), ["800001", "800002"])

        self._stub_rsge(get_invoice=stub_responses.get_invoice(status=2))
        invoice.action_l10n_ge_edi_refresh_status()

        self.assertEqual(invoice.l10n_ge_edi_state, "confirmed")
        self.assertFalse(self.create_send_and_print(invoice).extra_edi_checkboxes)
        with self.assertRaisesRegex(UserError, "cannot be reset to draft"):
            invoice.button_draft()

    def test_rejected_header_leaves_the_invoice_in_error_and_retryable(self):
        invoice = self._create_ge_invoice()
        self._stub_rsge(save_invoice=stub_responses.save_invoice(result=False))

        # called directly, not through the wizard: the wizard raises, and assertRaises would roll
        # back the state we want to read
        error = invoice._l10n_ge_edi_submit_invoice()

        self.assertEqual(invoice.l10n_ge_edi_state, "error")
        self.assertEqual(error.kind, KIND_SUBMIT_FAILED)
        self.assertNotIn(error.kind, RSGE_TRANSIENT_ERROR_KINDS)
        self.assertIn("ge_edi", self.create_send_and_print(invoice).extra_edi_checkboxes)

    def test_soap_fault_while_sending_is_reported_as_retryable(self):
        invoice = self._create_ge_invoice()
        self._stub_rsge(save_invoice=stub_responses.fault())

        error = invoice._l10n_ge_edi_submit_invoice()

        self.assertEqual(invoice.l10n_ge_edi_state, "error")
        self.assertIn(error.kind, RSGE_TRANSIENT_ERROR_KINDS)

    def test_bulk_refresh_skips_a_company_without_credentials(self):
        invoice = self._create_ge_invoice()
        self._send_to_rsge(invoice)
        # neutralize.sql clears these on every restored copy of a production database
        self.company.sudo().write({"l10n_ge_edi_su": False, "l10n_ge_edi_sp": False})

        self.env["account.move"]._l10n_ge_edi_refresh_all_statuses()

        self.assertEqual(invoice.l10n_ge_edi_state, "sent")

    def test_unpaid_refund_can_request_cancellation(self):
        invoice = self._confirmed_ge_invoice()
        self._stub_rsge(k_invoice=stub_responses.k_invoice(k_id=700901), get_invoice=stub_responses.get_invoice(status=3))
        self._k_invoice_wizard(invoice).action_full_partial_refund()
        correction = invoice.l10n_ge_edi_correction_move_id
        correction.action_post()
        # posting a reversal reconciles it against the original, which is not a payment
        correction.l10n_ge_edi_state = "confirmed_correction"

        self._stub_rsge(
            change_invoice_status=stub_responses.change_invoice_status(),
            get_invoice=stub_responses.get_invoice(status=6),
        )
        correction.action_l10n_ge_edi_request_cancellation()

        self.assertEqual(correction.l10n_ge_edi_state, "cancel_requested")

    def test_paid_invoice_cannot_request_cancellation(self):
        invoice = self._confirmed_ge_invoice()
        self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=invoice.ids,
        ).create({})._create_payments()

        with self.assertRaisesRegex(UserError, "reconciled payments"):
            invoice.action_l10n_ge_edi_request_cancellation()

    def test_rsge_option_offered_only_to_georgian_companies(self):
        invoice = self._create_ge_invoice()
        self.assertIn("ge_edi", self.create_send_and_print(invoice).extra_edi_checkboxes)

        # the same invoice under a company that files somewhere else
        self.company.account_fiscal_country_id = self.env.ref("base.be")
        invoice.invalidate_recordset(["country_code"])

        self.assertFalse(self.create_send_and_print(invoice).extra_edi_checkboxes)

    def test_rejected_invoice_is_resent_without_being_registered_again(self):
        invoice = self._create_ge_invoice()
        self._send_to_rsge(invoice)

        self._stub_rsge(get_invoice=stub_responses.get_invoice(status=0))
        invoice.action_l10n_ge_edi_refresh_status()

        self.assertEqual(invoice.l10n_ge_edi_state, "rejected")
        self.assertIn("ge_edi", self.create_send_and_print(invoice).extra_edi_checkboxes)

        # no save_invoice or save_invoice_desc is stubbed: RS.ge already holds both, and reaching
        # for either would fail on a missing recorded response
        self._stub_rsge(
            get_invoice=[stub_responses.get_invoice(status=0), stub_responses.get_invoice(status=1)],
            get_invoice_desc=stub_responses.get_invoice_desc({
                "ID": "800001",
                "GOODS": "Line 1",
                "G_UNIT": "pcs",
                "G_NUMBER": "1",
                "FULL_AMOUNT": "118.0",
                "VAT_TYPE": "0",
            }),
            change_invoice_status=stub_responses.change_invoice_status(),
        )
        self.create_send_and_print(invoice).action_send_and_print()

        self.assertEqual(invoice.l10n_ge_edi_state, "sent")
        self.assertEqual(invoice.l10n_ge_edi_invoice_id, "700123")
        self.assertEqual(invoice.invoice_line_ids.l10n_ge_edi_line_id, "800001")

        self._stub_rsge(get_invoice=stub_responses.get_invoice(status=2))
        invoice.action_l10n_ge_edi_refresh_status()

        self.assertEqual(invoice.l10n_ge_edi_state, "confirmed")

    def test_cancellation_is_requested_then_confirmed_by_the_buyer(self):
        invoice = self._create_ge_invoice()
        self._send_to_rsge(invoice)

        with self.assertRaisesRegex(UserError, "must be confirmed by RS.ge"):
            invoice.action_l10n_ge_edi_request_cancellation()

        self._stub_rsge(get_invoice=stub_responses.get_invoice(status=2))
        invoice.action_l10n_ge_edi_refresh_status()

        self._stub_rsge(
            change_invoice_status=stub_responses.change_invoice_status(),
            get_invoice=stub_responses.get_invoice(status=6),
        )
        invoice.action_l10n_ge_edi_request_cancellation()

        self.assertEqual(invoice.l10n_ge_edi_state, "cancel_requested")
        self.assertEqual(invoice.state, "posted")

        self._stub_rsge(get_invoice=stub_responses.get_invoice(status=7))
        invoice.action_l10n_ge_edi_refresh_status()

        self.assertEqual(invoice.l10n_ge_edi_state, "confirmed_cancelled")
        self.assertEqual(invoice.state, "cancel")

    def test_each_tax_group_reaches_rsge_as_the_right_vat_type(self):
        chart_template = self.env["account.chart.template"].with_company(self.company)
        invoice = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.partner_ge.id,
            "invoice_date": "2026-01-15",
            "invoice_line_ids": [
                Command.create({"name": name, "quantity": 1.0, "price_unit": 100.0, "tax_ids": [Command.set(chart_template.ref(tax).ids)]})
                for name, tax in (
                    ("Taxable", "ge_vat_sale_18"),
                    ("Zero rated", "ge_vat_sale_0_ex"),
                    ("Exempt", "ge_vat_sale_exempt_financial"),
                )
            ],
        })
        taxable, zero_rated, exempt = invoice.invoice_line_ids

        self.assertEqual(taxable._l10n_ge_edi_drg_amount(), 18.0)
        self.assertEqual(zero_rated._l10n_ge_edi_drg_amount(), 0)
        self.assertEqual(exempt._l10n_ge_edi_drg_amount(), -1)

        self.assertEqual(get_rsge_vat_type(taxable._l10n_ge_edi_drg_amount()), RSGE_VAT_TYPE_TAXABLE)
        self.assertEqual(get_rsge_vat_type(zero_rated._l10n_ge_edi_drg_amount()), RSGE_VAT_TYPE_ZERO_RATED)
        self.assertEqual(get_rsge_vat_type(exempt._l10n_ge_edi_drg_amount()), RSGE_VAT_TYPE_EXEMPT)

    def test_k_invoice_needs_a_confirmed_original(self):
        invoice = self._create_ge_invoice()
        self._send_to_rsge(invoice)

        with self.assertRaisesRegex(UserError, "must be confirmed by RS.ge"):
            self._k_invoice_wizard(invoice).action_taxable_transaction_cancelled()

    def test_cancel_transaction_creates_and_sends_a_credit_note(self):
        invoice = self._confirmed_ge_invoice()
        self._stub_rsge(
            k_invoice=stub_responses.k_invoice(k_id=700900),
            change_invoice_status=stub_responses.change_invoice_status(),
            get_invoice=[stub_responses.get_invoice(status=5), stub_responses.get_invoice(status=3)],
        )

        self._k_invoice_wizard(invoice).action_taxable_transaction_cancelled()
        correction = invoice.l10n_ge_edi_correction_move_id

        self.assertEqual(correction.move_type, "out_refund")
        self.assertEqual(correction.state, "posted")
        self.assertEqual(correction.l10n_ge_edi_k_type, "1")
        self.assertEqual(correction.l10n_ge_edi_invoice_id, "700900")
        self.assertEqual(correction.l10n_ge_edi_state, "correction_pending_confirmation")
        self.assertEqual(correction.l10n_ge_edi_original_move_id, invoice)
        self.assertEqual(invoice.l10n_ge_edi_state, "corrected_original")

    def test_full_partial_refund_leaves_the_credit_note_editable(self):
        invoice = self._confirmed_ge_invoice()
        self._stub_rsge(
            k_invoice=stub_responses.k_invoice(k_id=700901),
            get_invoice=stub_responses.get_invoice(status=3),
        )

        self._k_invoice_wizard(invoice).action_full_partial_refund()
        correction = invoice.l10n_ge_edi_correction_move_id

        self.assertEqual(correction.state, "draft")
        self.assertEqual(correction.l10n_ge_edi_state, "not_sent")
        self.assertEqual(correction.l10n_ge_edi_k_type, "4")
        self.assertEqual(correction.l10n_ge_edi_invoice_id, "700901")
        self.assertEqual(invoice.l10n_ge_edi_state, "corrected_original")

    def test_modify_invoice_replaces_the_original_and_discards_it(self):
        invoice = self._confirmed_ge_invoice()
        self._stub_rsge(
            k_invoice=stub_responses.k_invoice(k_id=700902),
            get_invoice_desc=stub_responses.get_invoice_desc({"ID": "800500", "GOODS": "Line 1"}),
            get_invoice=stub_responses.get_invoice(status=3),
        )

        self._k_invoice_wizard(invoice).action_modify_invoice()
        replacement = invoice.l10n_ge_edi_correction_move_id

        self.assertEqual(replacement.move_type, "out_invoice")
        self.assertEqual(replacement.l10n_ge_edi_k_type, "3")
        self.assertEqual(replacement.l10n_ge_edi_invoice_id, "700902")
        self.assertEqual(replacement.invoice_line_ids.l10n_ge_edi_line_id, "800500")
        self.assertEqual(invoice.l10n_ge_edi_state, "corrected_original")
        self.assertEqual(invoice.state, "cancel")

    def test_confirmed_correction_is_cancelled_and_the_original_reopens(self):
        invoice = self._confirmed_ge_invoice()
        matching_row = {
            "ID": "800500",
            "GOODS": "Line 1",
            "G_UNIT": "pcs",
            "G_NUMBER": "1",
            "FULL_AMOUNT": "118.0",
            "VAT_TYPE": "0",
        }
        self._stub_rsge(
            k_invoice=stub_responses.k_invoice(k_id=700902),
            get_invoice_desc=stub_responses.get_invoice_desc(matching_row),
            get_invoice=stub_responses.get_invoice(status=3),
        )
        self._k_invoice_wizard(invoice).action_modify_invoice()
        replacement = invoice.l10n_ge_edi_correction_move_id
        replacement.action_post()

        self._stub_rsge(
            get_invoice_desc=stub_responses.get_invoice_desc(matching_row),
            change_invoice_status=stub_responses.change_invoice_status(),
            get_invoice=stub_responses.get_invoice(status=5),
        )
        self.create_send_and_print(replacement).action_send_and_print()

        self.assertEqual(replacement.l10n_ge_edi_state, "correction_pending_confirmation")

        self._stub_rsge(get_invoice=stub_responses.get_invoice(status=8))
        self.env["account.move"]._l10n_ge_edi_refresh_all_statuses()

        self.assertEqual(replacement.l10n_ge_edi_state, "confirmed_correction")
        self.assertEqual(invoice.l10n_ge_edi_state, "corrected_original")

        self._stub_rsge(
            change_invoice_status=stub_responses.change_invoice_status(),
            get_invoice=stub_responses.get_invoice(status=6),
        )
        replacement.action_l10n_ge_edi_request_cancellation()

        self.assertEqual(replacement.l10n_ge_edi_state, "cancel_requested")

        self._stub_rsge(get_invoice=[stub_responses.get_invoice(status=7), stub_responses.get_invoice(status=2)])
        replacement.action_l10n_ge_edi_refresh_status()

        self.assertEqual(replacement.l10n_ge_edi_state, "confirmed_cancelled")
        self.assertEqual(invoice.l10n_ge_edi_state, "confirmed")
