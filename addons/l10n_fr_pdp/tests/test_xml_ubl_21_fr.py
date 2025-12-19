from odoo import Command
from odoo.tests import tagged

from .common import TestL10nFrPdpCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nFrPdpXml(TestL10nFrPdpCommon):

    def test_export_invoice_partner_fr(self):
        invoice = self._create_french_invoice()
        invoice.action_post()
        self._send_patched(invoice)
        self._assert_invoice_ubl_file(invoice, "from_odoo/ubl_21_fr_out_invoice")

    def test_export_credit_note_partner_fr(self):
        invoice = self._create_french_invoice()

        invoice.action_post()
        self.env['account.move.reversal'].with_company(self.company).create(
            {
                'move_ids': [Command.set((invoice.id,))],
                'date': self.fakenow.date(),
                'journal_id': invoice.journal_id.id,
            }
        ).reverse_moves()
        credit_note = invoice.reversal_move_ids
        credit_note.action_post()
        self._send_patched(credit_note)
        self._assert_invoice_ubl_file(credit_note, "from_odoo/ubl_21_fr_out_credit_note")
