from odoo import Command
from odoo.tests import tagged

from odoo.addons.l10n_fr_pdp.models.account_edi_xml_ubl_21_fr import CPRO_INVOICE_IDENTIFIER

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

    def test_export_invoice_partner_fr_without_pdp(self):
        """
        A French Peppol proxy user must have the BR-FR-05 mandatory notes
        (`PMT`, `PMD`, `AAB`) included in the `ubl_21_fr` exported XML.
        The export is tested directly rather than via send, as the patched
        send does not allow verifying the XML content in all versions.
        """
        self.env.company._reset_peppol_configuration()
        # To be able to generate the same XML as in `test_export_invoice_partner_fr`
        self.env.company.write({
            'peppol_eas': '0225',
            'peppol_endpoint': '968515759_96851575905899',
        })
        # Simulate a company that isn't connected to the PDP proxy at all
        self.proxy_user.unlink()

        invoice = self._create_french_invoice()
        invoice.action_post()

        wizard = self.create_send_and_print(invoice, sending_methods=['manual'], extra_edis=['ubl_21_fr'])
        wizard.action_send_and_print()
        self._assert_invoice_ubl_file(invoice, "ubl_21_fr_out_invoice")

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

    def test_export_invoice_partner_fr_b2g(self):
        if self.env['ir.module.module']._get('l10n_fr_facturx_chorus_pro').state != 'installed':
            self.skipTest("'l10n_fr_facturx_chorus_pro' is not installed")

        self.partner_a.peppol_supported_documents = [CPRO_INVOICE_IDENTIFIER]
        self.assertTrue(self.env['account.edi.xml.ubl_21_fr']._pdp_is_b2g(self.partner_a))

        invoice = self._create_french_invoice(
            buyer_reference="Chorus Pro buyer reference",
            purchase_order_reference="Chorus Pro purchase order reference",
        )
        invoice.action_post()
        self._send_patched(invoice)
        self._assert_invoice_ubl_file(invoice, "ubl_21_fr_out_invoice_b2g")
