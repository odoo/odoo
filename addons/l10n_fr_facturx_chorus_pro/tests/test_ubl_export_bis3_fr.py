from odoo.addons.account_edi_ubl_cii.tests.common import TestUblBis3Common, TestUblCiiFRCommon
from odoo.addons.l10n_fr_facturx_chorus_pro.tests.common import TestUblCiiCommonChorusPro
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install', *TestUblBis3Common.extra_tags)
class TestUblExportBis3FRChorusPro(TestUblBis3Common, TestUblCiiCommonChorusPro, TestUblCiiFRCommon):

    def subfolder(self):
        return super().subfolder().replace('export', 'export/bis3/invoice')

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
