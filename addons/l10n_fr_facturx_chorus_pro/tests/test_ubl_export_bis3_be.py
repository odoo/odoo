from odoo.addons.account_edi_ubl_cii.tests.test_ubl_export_bis3_be import TestUblExportBis3BE
from odoo.addons.l10n_fr_facturx_chorus_pro.tests.common import TestUblCiiCommonChorusPro
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install', *TestUblExportBis3BE.extra_tags)
class TestUblExportBis3BEChorusPro(TestUblCiiCommonChorusPro, TestUblExportBis3BE):

    def test_invoice_customer_party_identifiers_partner_chorus_pro(self):
        # VAT and siret set.
        # Supplier:
        # EndpointID is filled using the company registry.
        # PartyIdentification is filled using the VAT.
        # PartyTaxScheme is filled using the VAT.
        # PartyLegalEntity is filled using the company registry.
        # Customer:
        # EndpointID is filled using the CHORUS PRO siret.
        # PartyIdentification is filled using the customer siret.
        # PartyTaxScheme is filled using the VAT.
        # PartyLegalEntity is filled using the customer siret.
        self._assert_invoice_partner_party_identifiers(
            partner=self.partner_fr_chorus_pro,
            test_file='test_invoice_customer_party_identifiers_partner_chorus_pro',
        )
