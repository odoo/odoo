from unittest.mock import patch

from odoo.tests import tagged

from .common import TestEsEdiTbaiCommonGipuzkoa


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
