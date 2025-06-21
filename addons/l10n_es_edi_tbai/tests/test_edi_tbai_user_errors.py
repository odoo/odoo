from unittest.mock import patch

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import TestEsEdiTbaiCommonGipuzkoa


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestTbaiUserErrors(TestEsEdiTbaiCommonGipuzkoa):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.invoice_to_send = cls._create_posted_invoice()
        cls.invoice_send_wizard = cls._get_invoice_send_wizard(cls.invoice_to_send)

        cls.tbai_error_msg = "Error when sending the invoice to TicketBAI:\n- "

    def test_no_certificate(self):
        self.invoice_to_send.company_id.l10n_es_tbai_certificate_id = False

        with self.assertRaises(UserError) as e:
            self.invoice_send_wizard.action_send_and_print()

        self.assertEqual(str(e.exception), self.tbai_error_msg + "Please configure the certificate for TicketBAI.")

    def test_no_tax_agency(self):
        self.invoice_to_send.company_id.l10n_es_tbai_tax_agency = False

        with self.assertRaises(UserError) as e:
            self.invoice_send_wizard.action_send_and_print()

        self.assertEqual(str(e.exception), self.tbai_error_msg + "Please specify a tax agency on your company for TicketBAI.")

    def test_no_company_vat(self):
        self.invoice_to_send.company_id.vat = False

        with self.assertRaises(UserError) as e:
            self.invoice_send_wizard.action_send_and_print()

        self.assertEqual(str(e.exception), self.tbai_error_msg + "Please configure the Tax ID on your company for TicketBAI.")

    def test_no_tax_on_line(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2025-01-01',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 1000.0,
                    'quantity': 1,
                    'tax_ids': self._get_tax_by_xml_id('s_iva21b').ids,
                }),
                Command.create({
                    'product_id': self.product_b.id,
                    'price_unit': 50.0,
                    'quantity': 1,
                    'tax_ids': False,
                }),
            ],
        })
        invoice.action_post()

        with self.assertRaises(UserError) as e:
            self._get_invoice_send_wizard(invoice).action_send_and_print()

        self.assertEqual(str(e.exception), self.tbai_error_msg + "There should be at least one tax set on each line in order to send to TicketBAI.")

    def test_pending_invoice(self):
        first_invoice = self._create_posted_invoice()
        first_invoice_send_wizard = self._get_invoice_send_wizard(first_invoice)
        second_invoice = self._create_posted_invoice()
        second_invoice_send_wizard = self._get_invoice_send_wizard(second_invoice)

        # Post first with request error
        try:
            with patch(
                'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
                side_effect=self.mock_request_error,
            ):
                first_invoice_send_wizard.action_send_and_print()
            raise AssertionError("A UserError should have been raised.")

        except UserError:
            self.assertEqual(first_invoice.l10n_es_tbai_state, 'to_send')
            self.assertTrue(first_invoice.l10n_es_tbai_chain_index)

        # Post second raises an error as first is pending
        try:
            second_invoice_send_wizard.action_send_and_print()
            raise AssertionError("A UserError should have been raised.")
        except UserError as e:
            self.assertEqual(str(e), self.tbai_error_msg + f"TicketBAI: Cannot post invoice while chain head ({first_invoice.name}) has not been posted")
            self.assertEqual(second_invoice.l10n_es_tbai_state, 'to_send')
            self.assertFalse(second_invoice.l10n_es_tbai_chain_index)
            self.assertEqual(second_invoice.l10n_es_tbai_post_document_id.state, 'to_send')

        # Post first with success
        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
            return_value=self.mock_response_post_invoice_success,
        ):
            first_invoice_send_wizard.action_send_and_print()

        # Can now post second with success
        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
            return_value=self.mock_response_post_invoice_success,
        ):
            second_invoice_send_wizard.action_send_and_print()

        self.assertEqual(first_invoice.l10n_es_tbai_state, 'sent')
        self.assertEqual(second_invoice.l10n_es_tbai_state, 'sent')
        self.assertGreater(second_invoice.l10n_es_tbai_chain_index, first_invoice.l10n_es_tbai_chain_index)

    def test_post_tbai_credit_note_before_reversed_invoice(self):
        move_reversal = (
            self.env['account.move.reversal']
            .with_context(active_model="account.move", active_ids=self.invoice_to_send.ids)
            .create({
                'journal_id': self.invoice_to_send.journal_id.id,
                'l10n_es_tbai_refund_reason': 'R4',
            })
        )
        credit_note_id = move_reversal.refund_moves()['res_id']
        credit_note = self.env['account.move'].browse(credit_note_id)
        credit_note.action_post()
        credit_note_send_wizard = self._get_invoice_send_wizard(credit_note)

        try:
            credit_note_send_wizard.action_send_and_print()
            raise AssertionError("A UserError should have been raised.")
        except UserError as e:
            self.assertEqual(str(e), self.tbai_error_msg + "TicketBAI: Cannot post a reversal document while the source document has not been posted")

        # Post the source invoice
        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
            return_value=self.mock_response_post_invoice_success,
        ):
            self.invoice_send_wizard.action_send_and_print()

        # It is now possible to post the credit note
        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
            return_value=self.mock_response_post_invoice_success,
        ):
            credit_note_send_wizard.action_send_and_print()

        self.assertEqual(self.invoice_to_send.l10n_es_tbai_state, 'sent')
        self.assertEqual(credit_note.l10n_es_tbai_state, 'sent')
