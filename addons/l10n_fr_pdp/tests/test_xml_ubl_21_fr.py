from odoo import Command
from odoo.tests import tagged

from .common import TestL10nFrPdpCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nFrPdpXml(TestL10nFrPdpCommon):

    @classmethod
    def subfolders(cls):
        return 'ubl_21_fr', 'invoice', 'fr'

    def test_export_invoice_partner_fr(self):
        invoice = self._create_french_invoice()
        invoice.action_post()
        self._send_patched(invoice)
        self._assert_invoice_ubl_file(invoice, "ubl_21_fr_out_invoice")

    def test_export_invoice_pmd_custom_penalty_rate(self):
        self.company.write({'l10n_fr_pdp_late_payment_penalty_rate': 12.5})
        invoice = self._create_french_invoice()
        invoice.action_post()
        self._send_patched(invoice)
        self.assertIn(
            '#PMD#Late payment penalties at an annual rate of 12.5% are applied if the payment is made after the due date.',
            invoice.ubl_cii_xml_id.raw.decode(),
        )

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
        self._assert_invoice_ubl_file(credit_note, "ubl_21_fr_out_credit_note")
