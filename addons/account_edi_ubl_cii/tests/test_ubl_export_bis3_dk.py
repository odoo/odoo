from lxml import etree

from odoo.addons.account_edi_ubl_cii.tests.common import TestUblBis3Common
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install', *TestUblBis3Common.extra_tags)
class TestUblExportBis3DK(TestUblBis3Common):

    @classmethod
    def _create_company(cls, **create_values):
        company = super()._create_company(**create_values)
        company.partner_id.write({
            'street': "Nørregade 1",
            'zip': "1165",
            'city': "København",
            'vat': 'DK12345674',
            'company_registry': '12345674',
            'country_id': cls.env.ref('base.dk').id,
            'peppol_eas': '0184',
            'peppol_endpoint': '12345674',
        })
        return company

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_dk = cls.env['res.partner'].create({
            **cls._create_partner_default_values(),
            'name': 'partner_dk',
            'street': "Vesterbrogade 1",
            'zip': "1620",
            'city': "København",
            'vat': 'DK88146328',
            'company_registry': '88146328',
            'country_id': cls.env.ref('base.dk').id,
            'peppol_eas': '0088',  # GLN
            'peppol_endpoint': '5790000000005',
        })

    def _export_party_legal_entity_company_id(self, invoice, party):
        xml, errors = self.env['account.edi.xml.ubl_bis3']._export_invoice(invoice)
        node = etree.fromstring(xml).find(
            f'.//{{*}}{party}/{{*}}Party/{{*}}PartyLegalEntity/{{*}}CompanyID'
        )
        return node, errors

    def test_export_party_legal_entity_cvr(self):
        """ DK-R-014 / DK-R-017: PartyLegalEntity/CompanyID must be the CVR number with schemeID 0184,
        even when the Peppol endpoint of the partner is not a CVR number (e.g. GLN). """
        tax_25 = self.percent_tax(25.0)
        product = self._create_product(lst_price=100.0, taxes_id=tax_25)
        invoice = self._create_invoice_one_line(product_id=product, partner_id=self.partner_dk, post=True)

        for party, cvr in (('AccountingSupplierParty', '12345674'), ('AccountingCustomerParty', '88146328')):
            node, errors = self._export_party_legal_entity_company_id(invoice, party)
            self.assertFalse(errors)
            self.assertEqual(node.text, cvr)
            self.assertEqual(node.get('schemeID'), '0184')

    def test_export_party_legal_entity_cvr_missing(self):
        tax_25 = self.percent_tax(25.0)
        product = self._create_product(lst_price=100.0, taxes_id=tax_25)
        invoice = self._create_invoice_one_line(product_id=product, partner_id=self.partner_dk, post=True)
        self.partner_dk.company_registry = False

        _node, errors = self._export_party_legal_entity_company_id(invoice, 'AccountingCustomerParty')
        self.assertIn("partner_dk should have a CVR number in the Company ID field.", errors)
