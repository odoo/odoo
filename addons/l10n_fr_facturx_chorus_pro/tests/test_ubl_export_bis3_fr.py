from lxml import etree

from odoo import Command
from odoo.addons.account_edi_ubl_cii.models.account_edi_xml_ubl_bis3 import CHORUS_PRO_PEPPOL_ID
from odoo.addons.account_edi_ubl_cii.tests.common import TestUblBis3Common
from odoo.addons.l10n_fr_facturx_chorus_pro.tests.common import TestUblCiiFRCommonChorusPro
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install', *TestUblBis3Common.extra_tags)
class TestUblExportBis3FRChorusPro(TestUblBis3Common, TestUblCiiFRCommonChorusPro):

    @classmethod
    def subfolders(cls):
        subfolder_format, _subfolder_document, subfolder_country = super().subfolders()
        return subfolder_format, 'invoice', subfolder_country

    def _assert_invoice_partner_party_identifiers(self, partner, test_file):
        tax_20 = self.percent_tax(20.0)
        product = self._create_product(lst_price=100.0, taxes_id=tax_20)
        invoice = self._create_invoice_one_line(
            product_id=product,
            partner_id=partner,
            post=True,
        )
        self._generate_invoice_ubl_file(invoice)
        self._assert_invoice_ubl_file(invoice, test_file)

    def test_invoice_customer_party_identifiers_partner_chorus_pro(self):
        # VAT and siret set.
        # Supplier:
        # EndpointID is filled using the siret.
        # PartyIdentification is filled using the siret.
        # PartyTaxScheme is filled using the VAT.
        # PartyLegalEntity is filled using the siret.
        # Customer:
        # EndpointID is filled using the CHORUS PRO siret.
        # PartyIdentification is filled using the customer siret.
        # PartyTaxScheme is filled using the VAT.
        # PartyLegalEntity is filled using the customer siret.
        self._assert_invoice_partner_party_identifiers(
            partner=self.partner_fr_chorus_pro,
            test_file='test_invoice_customer_party_identifiers_partner_chorus_pro',
        )

    def test_export_invoice_chorus_pro_overseas_drom(self):
        """ A public customer located in a DROM, its SIRET must
        be used in PartyIdentification, exactly like metropolitan France.
        """
        chorus_eas, chorus_endpoint = CHORUS_PRO_PEPPOL_ID.split(":")
        drom_partner = self.env['res.partner'].create({
            'name': "Chorus Pro - Ville du Lamentin (Martinique)",
            'vat': "FR19219722139",
            'siret': "21972213900017",
            'peppol_eas': chorus_eas,
            'peppol_endpoint': chorus_endpoint,
            'country_id': self.env.ref('base.mq').id,  # Martinique (DROM)
            'invoice_edi_format': 'ubl_bis3',
        })
        invoice = self.env['account.move'].create({
            'company_id': self.env.company.id,
            'partner_id': drom_partner.id,
            'move_type': 'out_invoice',
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 100.0,
            })],
        })
        invoice.action_post()
        xml = self.env['account.edi.xml.ubl_bis3']._export_invoice(invoice)[0]
        xml_etree = etree.fromstring(xml)

        # The SIRET (not the VAT) must identify the overseas public customer
        customer_identification_node = xml_etree.find("{*}AccountingCustomerParty/{*}Party/{*}PartyIdentification/{*}ID")
        self.assertEqual(customer_identification_node.text, "21972213900017")
        self.assertEqual(customer_identification_node.attrib, {'schemeID': '0009'})
