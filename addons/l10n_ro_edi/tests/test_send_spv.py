from unittest.mock import patch

from odoo import Command
from odoo.tests import tagged

from odoo.addons.l10n_ro_edi.tests.test_xml_ubl_ro import TestUBLROCommon

CIUSRO_CUSTOMIZATION_ID = b'urn:efactura.mfinante.ro:CIUS-RO'
UPLOAD_RESPONSE = b'<header xmlns="mfp:anaf:dgti:spv:respUploadFisier:v1" ExecutionStatus="0" index_incarcare="5019882651"/>'


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nRoEdiSendSpv(TestUBLROCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].l10n_ro_edi_access_token = 'test_access_token'

        cls.partner_ch = cls.env['res.partner'].create({
            'name': 'Swiss Customer',
            'is_company': True,
            'country_id': cls.env.ref('base.ch').id,
            'state_id': cls.env.ref('base.state_ch_zh').id,
            'city': 'Zürich',
            'zip': '8001',
            'street': 'Bahnhofstrasse 1',
            'vat': 'CHE-123.456.788 MWST',
            'invoice_edi_format': 'ubl_bis3',
        })

    def _create_invoice(self, partner):
        return self._generate_move(
            self.env.company.partner_id,
            partner,
            send=False,
            move_type='out_invoice',
            invoice_line_ids=[{
                'product_id': self.product_a.id,
                'price_unit': 500.0,
                'tax_ids': [Command.set(self.tax_19.ids)],
            }],
        )

    def _send_to_spv(self, invoice):
        """ Send the invoice with the Send & Print wizard and return the arguments of the upload request """
        wizard = self.env['account.move.send.wizard']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({'sending_methods': ['manual']})
        self.assertIn('ro_edi', wizard.extra_edis)

        with patch(
            'odoo.addons.l10n_ro_edi.models.ciusro_document.make_efactura_request',
            return_value={'content': UPLOAD_RESPONSE},
        ) as mock_request:
            wizard.action_send_and_print()

        self.assertEqual(invoice.l10n_ro_edi_state, 'invoice_sent')
        mock_request.assert_called_once()
        return mock_request.call_args.kwargs

    def test_send_romanian_customer(self):
        invoice = self._create_invoice(self.partner_a)
        request = self._send_to_spv(invoice)

        self.assertEqual(request['data'], invoice.ubl_cii_xml_id.raw)
        self.assertIn(CIUSRO_CUSTOMIZATION_ID, request['data'])

    def test_send_foreign_customer(self):
        """ The customer's own format (Peppol BIS 3) is attached to the invoice, but the SPV must receive the CIUS-RO XML """
        invoice = self._create_invoice(self.partner_ch)
        request = self._send_to_spv(invoice)

        self.assertNotIn(CIUSRO_CUSTOMIZATION_ID, invoice.ubl_cii_xml_id.raw)
        self.assertIn(CIUSRO_CUSTOMIZATION_ID, request['data'])
        self.assertEqual(invoice.l10n_ro_edi_document_ids.attachment_id.raw, request['data'])
