# -*- coding: utf-8 -*-
from odoo.addons.account_edi.tests.common import AccountEdiTestCommon
from odoo.tests import tagged

from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUBL(AccountEdiTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_no.no_chart_template', edi_format_ref='l10n_no_edi.edi_ehf_3'):
        super().setUpClass(chart_template_ref=chart_template_ref, edi_format_ref=edi_format_ref)

        if cls.env['ir.module.module'].search(
            [('name', '=', 'account_edi_ubl_cii'), ('state', '=', 'installed')],
            limit=1,
        ):
            cls.skipTest(cls, "EHF Tests skipped because account_edi_ubl_cii is installed.")

        cls.company_data['company'].partner_id.write({
            'street': 'Archefstraat 42',
            'zip': '1000',
            'city': 'Amsterdam',
            'country_id': cls.env.ref('base.no').id,
            'l10n_no_bronnoysund_number': '987654325',
            'vat': 'NO987654325MVA',
        })

        cls.partner_a.write({
            'l10n_no_bronnoysund_number': '864234232',
            'country_id': cls.env.ref('base.no').id,
            'vat': 'NO864234232MVA',
        })

        bank_account = cls.env['res.partner.bank'].create({
            'acc_number': '86011117947',
            'partner_id': cls.partner_a.id,
        })

        cls.tax_sale_b.write({
            'amount': 15
        })

        cls.invoice = cls.env['account.move'].create({
            'partner_id': cls.partner_a.id,
            'move_type': 'out_invoice',
            'partner_bank_id': bank_account.id,
            'invoice_date_due': '2020-12-16',
            'invoice_line_ids': [
                (0, 0, {
                    'product_id': cls.product_a.id,
                    'quantity': 150,
                    'price_unit': 250,
                    'discount': 10,
                    'tax_ids': [(6, 0, cls.tax_sale_a.ids)],
                }),
                (0, 0, {
                    'product_id': cls.product_b.id,
                    'quantity': 12,
                    'price_unit': 100,
                    'tax_ids': [(6, 0, cls.tax_sale_b.ids)],
                }),
            ]
        })

        cls.expected_invoice_values = '''
            <Invoice xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
                <cbc:CustomizationID>urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0</cbc:CustomizationID>
                <cbc:ProfileID>urn:fdc:peppol.eu:2017:poacc:billing:01:1.0</cbc:ProfileID>
                <cbc:ID>INV/2020/00001</cbc:ID>
                <cbc:IssueDate>2020-12-16</cbc:IssueDate>
                <cbc:DueDate>2020-12-16</cbc:DueDate>
                <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>
                <cbc:DocumentCurrencyCode>NOK</cbc:DocumentCurrencyCode>
                <cbc:BuyerReference>partner_a</cbc:BuyerReference>
                <cac:AccountingSupplierParty>
            <cac:Party>
                <cbc:EndpointID schemeID="0192">987654325</cbc:EndpointID>
                <cac:PartyName>
                    <cbc:Name>company_1_data</cbc:Name>
                </cac:PartyName>
                <cac:PostalAddress>
                    <cbc:StreetName>Archefstraat 42</cbc:StreetName>
                    <cbc:CityName>Amsterdam</cbc:CityName>
                    <cbc:PostalZone>1000</cbc:PostalZone>
                    <cac:Country>
                        <cbc:IdentificationCode>NO</cbc:IdentificationCode>
                    </cac:Country>
                </cac:PostalAddress>
                <cac:PartyTaxScheme>
                    <cbc:CompanyID>NO987654325MVA</cbc:CompanyID>
                    <cac:TaxScheme>
                        <cbc:ID>VAT</cbc:ID>
                    </cac:TaxScheme>
                </cac:PartyTaxScheme>
                <cac:PartyTaxScheme>
                    <cbc:CompanyID>Foretaksregisteret</cbc:CompanyID>
                    <cac:TaxScheme>
                        <cbc:ID>TAX</cbc:ID>
                    </cac:TaxScheme>
                </cac:PartyTaxScheme>
                <cac:PartyLegalEntity>
                    <cbc:RegistrationName>company_1_data</cbc:RegistrationName>
                </cac:PartyLegalEntity>
                <cac:Contact>
                    <cbc:Name>company_1_data</cbc:Name>
                  </cac:Contact>
            </cac:Party>
        </cac:AccountingSupplierParty>
            <cac:AccountingCustomerParty>
            <cac:Party>
                <cbc:EndpointID schemeID="0192">864234232</cbc:EndpointID>
                <cac:PartyName>
                    <cbc:Name>partner_a</cbc:Name>
                </cac:PartyName>
                <cac:PostalAddress>
                    <cac:Country>
                        <cbc:IdentificationCode>NO</cbc:IdentificationCode>
                    </cac:Country>
                </cac:PostalAddress>
                <cac:PartyTaxScheme>
                    <cbc:CompanyID>NO864234232MVA</cbc:CompanyID>
                    <cac:TaxScheme>
                        <cbc:ID>VAT</cbc:ID>
                    </cac:TaxScheme>
                </cac:PartyTaxScheme>
                <cac:PartyLegalEntity>
                    <cbc:RegistrationName>partner_a</cbc:RegistrationName>
                </cac:PartyLegalEntity>
                <cac:Contact>
                    <cbc:Name>partner_a</cbc:Name>
                  </cac:Contact>
            </cac:Party>
        </cac:AccountingCustomerParty>
                <cac:PaymentMeans>
                    <cbc:PaymentMeansCode>31</cbc:PaymentMeansCode>
                    <cac:PayeeFinancialAccount>
                        <cbc:ID>86011117947</cbc:ID>
                    </cac:PayeeFinancialAccount>
                </cac:PaymentMeans>
                <cac:TaxTotal>
                    <cbc:TaxAmount currencyID="NOK">8617.50</cbc:TaxAmount>
                    <cac:TaxSubtotal>
                        <cbc:TaxableAmount currencyID="NOK">33750.00</cbc:TaxableAmount>
                        <cbc:TaxAmount currencyID="NOK">8437.50</cbc:TaxAmount>
                        <cac:TaxCategory>
                            <cbc:ID>S</cbc:ID>
                            <cbc:Percent>25.0</cbc:Percent>
                            <cac:TaxScheme>
                                <cbc:ID>VAT</cbc:ID>
                            </cac:TaxScheme>
                        </cac:TaxCategory>
                    </cac:TaxSubtotal><cac:TaxSubtotal>
                        <cbc:TaxableAmount currencyID="NOK">1200.00</cbc:TaxableAmount>
                        <cbc:TaxAmount currencyID="NOK">180.00</cbc:TaxAmount>
                        <cac:TaxCategory>
                            <cbc:ID>S</cbc:ID>
                            <cbc:Percent>15.0</cbc:Percent>
                            <cac:TaxScheme>
                                <cbc:ID>VAT</cbc:ID>
                            </cac:TaxScheme>
                        </cac:TaxCategory>
                    </cac:TaxSubtotal>
                </cac:TaxTotal>
                <cac:LegalMonetaryTotal>
                    <cbc:LineExtensionAmount currencyID="NOK">34950.00</cbc:LineExtensionAmount>
                    <cbc:TaxExclusiveAmount currencyID="NOK">34950.00</cbc:TaxExclusiveAmount>
                    <cbc:TaxInclusiveAmount currencyID="NOK">43567.50</cbc:TaxInclusiveAmount>
                    <cbc:PrepaidAmount currencyID="NOK">0.00</cbc:PrepaidAmount>
                    <cbc:PayableAmount currencyID="NOK">43567.50</cbc:PayableAmount>
                </cac:LegalMonetaryTotal>
            <cac:InvoiceLine>
                <cbc:ID>1</cbc:ID>
                <cbc:Note>Discount (10.0 %)</cbc:Note>
                <cbc:InvoicedQuantity unitCode="ZZ">150.0</cbc:InvoicedQuantity>
                <cbc:LineExtensionAmount currencyID="NOK">33750.00</cbc:LineExtensionAmount>
                <cac:Item>
                    <cbc:Description>product_a</cbc:Description>
                    <cbc:Name>product_a</cbc:Name>
                    <cac:ClassifiedTaxCategory>
                        <cbc:ID>S</cbc:ID>
                        <cbc:Percent>25.0</cbc:Percent>
                        <cac:TaxScheme>
                            <cbc:ID>VAT</cbc:ID>
                        </cac:TaxScheme>
                    </cac:ClassifiedTaxCategory>
                </cac:Item>
                <cac:Price>
                    <cbc:PriceAmount currencyID="NOK">225.00</cbc:PriceAmount>
                    <cbc:BaseQuantity>150.0</cbc:BaseQuantity>
                </cac:Price>
            </cac:InvoiceLine>
            <cac:InvoiceLine>
                <cbc:ID>2</cbc:ID>
                <cbc:InvoicedQuantity unitCode="ZZ">12.0</cbc:InvoicedQuantity>
                <cbc:LineExtensionAmount currencyID="NOK">1200.00</cbc:LineExtensionAmount>
                <cac:Item>
                    <cbc:Description>product_b</cbc:Description>
                    <cbc:Name>product_b</cbc:Name>
                    <cac:ClassifiedTaxCategory>
                        <cbc:ID>S</cbc:ID>
                        <cbc:Percent>15.0</cbc:Percent>
                        <cac:TaxScheme>
                            <cbc:ID>VAT</cbc:ID>
                        </cac:TaxScheme>
                    </cac:ClassifiedTaxCategory>
                </cac:Item>
                <cac:Price>
                    <cbc:PriceAmount currencyID="NOK">100.00</cbc:PriceAmount>
                    <cbc:BaseQuantity>12.0</cbc:BaseQuantity>
                </cac:Price>
            </cac:InvoiceLine>
            </Invoice>
        '''

    def test_ehf_import(self):
        invoice = self.env['account.move'].with_context(default_move_type='in_invoice').create({})
        invoice_count = self.env['account.move'].search_count([])
        self.update_invoice_from_file('l10n_no_edi', 'test_xml_file', 'ehf_test.xml', invoice)
        self.assertEqual(self.env['account.move'].search_count([]), invoice_count)
        self.assertRecordValues(invoice, [{
            'partner_id': self.partner_a.id,
            'amount_total': 1801.78,
            'amount_tax': 365.28,
        }])

    @freeze_time('2020-12-16')
    def test_ehf_export(self):
        self.assert_generated_file_equal(self.invoice, self.expected_invoice_values)
