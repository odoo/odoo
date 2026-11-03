from unittest.mock import patch

from odoo import Command
from odoo.tests import tagged

from odoo.addons.l10n_ro_edi.tests.test_xml_ubl_ro import TestUBLROCommon

CIUSRO_CUSTOMIZATION_ID = b'urn:efactura.mfinante.ro:CIUS-RO'
UPLOAD_RESPONSE = b'<header xmlns="mfp:anaf:dgti:spv:respUploadFisier:v1" ExecutionStatus="0" index_incarcare="5019882651"/>'


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nRoEfacturaSend(TestUBLROCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref="ro"):
        super().setUpClass(chart_template_ref=chart_template_ref)
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
            'ubl_cii_format': 'ubl_bis3',
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
        wizard = self.env['account.move.send']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({'mail_template_id': self.move_template.id})
        self.assertTrue(wizard.l10n_ro_edi_send_checkbox)

        with patch(
            'odoo.addons.l10n_ro_efactura.models.ciusro_document.make_efactura_request',
            return_value={'content': UPLOAD_RESPONSE},
        ) as mock_request:
            wizard.action_send_and_print()

        self.assertEqual(invoice.l10n_ro_edi_state, 'invoice_sending')
        mock_request.assert_called_once()
        return mock_request.call_args.kwargs

    def test_send_romanian_customer(self):
        invoice = self._create_invoice(self.partner_a)
        request = self._send_to_spv(invoice)

        self.assertNotIn('extern', request['params'])
        self.assertEqual(request['data'], invoice.ubl_cii_xml_id.raw)
        self.assertIn(CIUSRO_CUSTOMIZATION_ID, request['data'])

    def test_send_foreign_customer(self):
        """ The customer's own format (Peppol BIS 3) is attached to the invoice, but the SPV must receive the CIUS-RO XML """
        invoice = self._create_invoice(self.partner_ch)
        request = self._send_to_spv(invoice)

        self.assertNotIn(CIUSRO_CUSTOMIZATION_ID, invoice.ubl_cii_xml_id.raw)
        self.assertIn(CIUSRO_CUSTOMIZATION_ID, request['data'])
        self.assertEqual(invoice.l10n_ro_edi_document_ids.attachment_id.raw, request['data'])
        # The buyer has no Romanian CUI
        self.assertEqual(request['endpoint'], 'upload')
        self.assertEqual(request['params'].get('extern'), 'DA')

    def test_is_extern(self):
        invoice = self._create_invoice(self.partner_ch)
        self.assertTrue(invoice._l10n_ro_edi_is_extern())

        # A foreign company registered for VAT in Romania has a CUI
        self.partner_ch.vat = 'RO1234567897'
        self.assertFalse(invoice._l10n_ro_edi_is_extern())

        self.assertFalse(self._create_invoice(self.partner_a)._l10n_ro_edi_is_extern())
