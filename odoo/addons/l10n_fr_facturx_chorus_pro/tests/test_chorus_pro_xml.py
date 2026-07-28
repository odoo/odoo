from lxml import etree

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from odoo.addons.l10n_fr_facturx_chorus_pro.models.account_edi_xml_ubl_bis3 import CHORUS_PRO_PEPPOL_ID


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestChorusProXml(TestAccountMoveSendCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='fr'):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.company = cls.company_data['company']
        cls.company.siret = "02546465000024"
        chorus_eas, chorus_endpoint = CHORUS_PRO_PEPPOL_ID.split(":")
        cls.chorus_pro_partner = cls.env['res.partner'].create({
            'name': "Chorus Pro - Commune de Nantes",
            # Commune de Nantes
            'vat': "FR74214401093",
            'siret': "21440109300015",
            # Peppol ID for the AIFE (= Chorus Pro)
            'peppol_eas': chorus_eas,
            'peppol_endpoint': chorus_endpoint,
            'country_id': cls.env.ref('base.fr').id,
            'ubl_cii_format': 'ubl_bis3',
        })

    def test_export_invoice_chorus_pro(self):
        invoice = self.env['account.move'].create({
            'company_id': self.company.id,
            'partner_id': self.chorus_pro_partner.id,
            'move_type': 'out_invoice',
            'buyer_reference': 'buyer_ref_123',
            'purchase_order_reference': 'order_ref_123',
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 100.0,
            })],
        })
        invoice.action_post()
        xml = self.env['account.edi.xml.ubl_bis3']._export_invoice(invoice)[0]
        xml_etree = etree.fromstring(xml)

        endpoint_node = xml_etree.find("{*}AccountingCustomerParty/{*}Party/{*}EndpointID")
        chorus_eas, chorus_endpoint = CHORUS_PRO_PEPPOL_ID.split(":")
        self.assertEqual(endpoint_node.text, chorus_endpoint)
        self.assertEqual(endpoint_node.attrib, {'schemeID': chorus_eas})

        supplier_identification_node = xml_etree.find("{*}AccountingSupplierParty/{*}Party/{*}PartyIdentification/{*}ID")
        self.assertEqual(supplier_identification_node.text, "02546465000024")
        self.assertEqual(supplier_identification_node.attrib, {'schemeName': '1'})

        customer_identification_node = xml_etree.find("{*}AccountingCustomerParty/{*}Party/{*}PartyIdentification/{*}ID")
        self.assertEqual(customer_identification_node.text, "21440109300015")
        self.assertEqual(customer_identification_node.attrib, {'schemeName': '1'})

        self.assertEqual(xml_etree.findtext("{*}BuyerReference"), "buyer_ref_123")
        self.assertEqual(xml_etree.findtext("{*}OrderReference/{*}ID"), "order_ref_123")

    def test_export_invoice_chorus_pro_no_bic(self):
        invoice = self.env['account.move'].create({
            'company_id': self.company.id,
            'partner_id': self.chorus_pro_partner.id,
            'move_type': 'out_invoice',
            'buyer_reference': 'buyer_ref_123',
            'purchase_order_reference': 'order_ref_123',
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 100.0,
            })],
        })
        invoice.action_post()
        invoice.partner_bank_id = None
        with self.assertRaisesRegex(UserError, "The BIC of the payee's bank is mandatory when invoicing to Chorus Pro."):
            wizard = self.create_send_and_print(invoice, checkbox_ubl_cii_xml=True, checkbox_download=True, checkbox_send_mail=False)
            wizard.action_send_and_print()
