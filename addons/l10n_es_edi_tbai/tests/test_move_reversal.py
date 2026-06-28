from unittest.mock import patch

from odoo.tests import tagged

from .common import TestEsEdiTbaiCommonGipuzkoa

from datetime import date


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestSendAndPrintEdiGipuzkoa(TestEsEdiTbaiCommonGipuzkoa):

    def test_post_and_cancel_tbai_credit_note(self):
        invoice = self._create_posted_invoice()
        invoice_send_wizard = self._get_invoice_send_wizard(invoice)

        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
            return_value=self.mock_response_post_invoice_success,
        ):
            invoice_send_wizard.action_send_and_print()

        move_reversal = self.env['account.move.reversal']\
                            .with_context(active_model="account.move", active_ids=invoice.ids)\
                            .create({
                                'journal_id': invoice.journal_id.id,
                                'l10n_es_tbai_refund_reason': 'R4',
                            })
        credit_note_id = move_reversal.refund_moves()['res_id']
        credit_note = self.env['account.move'].browse(credit_note_id)
        credit_note.l10n_es_original_invoice_credited = invoice.name or "INV/2026/00001"
        credit_note.action_post()

        self.assertEqual(credit_note.l10n_es_tbai_refund_reason, 'R4')

        send_wizard = self._get_invoice_send_wizard(credit_note)
        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
            return_value=self.mock_response_post_invoice_success,
        ):
            send_wizard.action_send_and_print()

        self.assertEqual(credit_note.l10n_es_tbai_state, 'sent')

        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
            return_value=self.mock_response_cancel_invoice_success,
        ):
            credit_note.l10n_es_tbai_cancel()

        self.assertEqual(credit_note.l10n_es_tbai_state, 'cancelled')

    def test_manual_refund_from_scratch_can_be_sent(self):
        """Test that a manual refund (without linked original invoice) can be sent with TBAI."""
        refund = self.env['account.move'].create({
            'move_type': 'out_refund',
            'invoice_date': date(2025, 1, 1),
            'partner_id': self.partner_a.id,
            'l10n_es_original_invoice_credited': 'INV/MANUAL/00042',
            'l10n_es_tbai_refund_reason': 'R4',
            'l10n_es_tbai_original_invoice_date': date(2024, 12, 1),
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'price_unit': 100.0,
                'quantity': 1,
                'tax_ids': [(6, 0, self._get_tax_by_xml_id('s_iva21b').ids)],
            })],
        })
        refund.action_post()

        # Verify refund fields are set
        self.assertEqual(refund.l10n_es_original_invoice_credited, 'INV/MANUAL/00042')
        self.assertEqual(refund.l10n_es_tbai_refund_reason, 'R4')
        self.assertEqual(refund.l10n_es_tbai_original_invoice_date, date(2024, 12, 1))

        # Send refund
        refund_send_wizard = self._get_invoice_send_wizard(refund)
        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
            return_value=self.mock_response_post_invoice_success,
        ):
            refund_send_wizard.action_send_and_print()

        self.assertEqual(refund.l10n_es_tbai_state, 'sent')
        self.assertTrue(refund.l10n_es_tbai_post_file)
