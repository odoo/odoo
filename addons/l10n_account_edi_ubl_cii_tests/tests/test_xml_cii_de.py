# -*- coding: utf-8 -*-
from lxml import etree

from odoo.addons.l10n_account_edi_ubl_cii_tests.tests.common import TestUBLCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestCIIDE(TestUBLCommon):

    @classmethod
    @TestUBLCommon.setup_country('de')
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data['company'].partner_id.write({
            'street': 'Musterstraße 1',
            'zip': '10115',
            'city': 'Berlin',
            'vat': 'DE811112663',
            'phone': '+49 30 1234567',
            'email': 'info@example.de',
            'country_id': cls.env.ref('base.de').id,
        })
        cls.de_partner = cls.env['res.partner'].create({
            'name': 'German customer',
            'street': 'Kundenstraße 2',
            'zip': '20095',
            'city': 'Hamburg',
            'vat': 'DE462612124',
            'email': 'customer@example.de',
            'country_id': cls.env.ref('base.de').id,
        })
        cls.foreign_partner = cls.env['res.partner'].create({
            'name': 'French customer',
            'country_id': cls.env.ref('base.fr').id,
        })

    def _get_seller_tax_registrations(self, invoice):
        ram_ns = {'ram': 'urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100'}
        xml_content = self.env['account.edi.xml.cii']._export_invoice(invoice)[0]
        tree = etree.fromstring(xml_content)
        seller = tree.find('.//ram:SellerTradeParty', ram_ns)
        return [
            (node.get('schemeID'), node.text)
            for node in seller.findall('.//ram:SpecifiedTaxRegistration/ram:ID', ram_ns)
        ]

    def test_seller_tax_registrations(self):
        """
        Verify which SpecifiedTaxRegistration tag is emitted depending on whether the seller
        has a VAT number (BT-31, schemeID='VA'), a Steuernummer (BT-32, schemeID='FC'), both,
        or neither.

        FC is only added for a DE company with a Steuernummer: neither the VAT's validity nor
        the buyer's country affect this, and a non-DE seller never gets it, even if
        `l10n_de_stnr` happens to be set (e.g. a leftover value after a country change).
        """
        # Real stnr, checksum-valid example from res.company.l10n_de_stnr's own help text.
        valid_stnr = '2893081508152'
        foreign_company = self.setup_other_company(name='US Co', country_id=self.env.ref('base.us').id)['company']

        de_invoice = self._create_invoice_one_line(
            partner_id=self.de_partner,
            company_id=self.company_data['company'],
            price_unit=100.0,
            tax_ids=self.company_data['company'].account_sale_tax_id,
            post=True,
        )
        foreign_buyer_invoice = self._create_invoice_one_line(
            partner_id=self.foreign_partner,
            company_id=self.company_data['company'],
            price_unit=100.0,
            tax_ids=self.company_data['company'].account_sale_tax_id,
            post=True,
        )
        foreign_seller_invoice = self._create_invoice_one_line(  # partner_a: not restricted to a specific company
            partner_id=self.partner_a,
            company_id=foreign_company,
            price_unit=100.0,
            tax_ids=foreign_company.account_sale_tax_id,
            post=True,
        )
        de_buyer_invoice = self._create_invoice_one_line(  # de_partner: not restricted to a specific company either
            partner_id=self.de_partner,
            company_id=foreign_company,
            price_unit=100.0,
            tax_ids=foreign_company.account_sale_tax_id,
            post=True,
        )

        cases = [
            # (invoice, vat, l10n_de_stnr, expected)
            (de_invoice, 'DE811112663', valid_stnr, [('VA', 'DE811112663'), ('FC', valid_stnr)]),
            (de_invoice, 'DE811112663', False, [('VA', 'DE811112663')]),
            (de_invoice, '/', valid_stnr, [('FC', valid_stnr)]),
            # Same result with a foreign buyer: the buyer's country doesn't affect this.
            (foreign_buyer_invoice, 'DE811112663', valid_stnr, [('VA', 'DE811112663'), ('FC', valid_stnr)]),
            # A non-DE seller must behave like vanilla Odoo: FC never applies, even with a
            # Steuernummer set, whatever the buyer's country.
            (foreign_seller_invoice, 'US123456789', False, [('VA', 'US123456789')]),
            (foreign_seller_invoice, 'US123456789', valid_stnr, [('VA', 'US123456789')]),
            (de_buyer_invoice, 'US123456789', False, [('VA', 'US123456789')]),
        ]
        # The fix was applied to both the legacy QWeb template and the new dict-based builder:
        # exercise both so neither regresses on its own.
        for use_new_dict_to_xml_helpers in (False, True):
            # set_param(key, False) would unlink the parameter instead of storing it (see
            # ir.config_parameter.set_param), silently falling back to its own True default.
            self.env['ir.config_parameter'].sudo().set_param(
                'account_edi_ubl_cii.use_new_dict_to_xml_helpers', str(use_new_dict_to_xml_helpers))
            for invoice, vat, stnr, expected in cases:
                with self.subTest(use_new_dict_to_xml_helpers=use_new_dict_to_xml_helpers, invoice=invoice, vat=vat, l10n_de_stnr=stnr):
                    invoice.company_id.write({'vat': vat, 'l10n_de_stnr': stnr})
                    self.assertEqual(self._get_seller_tax_registrations(invoice), expected)
