# -*- coding: utf-8 -*-
from freezegun import freeze_time
from odoo.addons.account_edi.tests.common import AccountEdiTestCommon
from odoo.modules.module import get_module_resource
import base64
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountEdiPeppol(AccountEdiTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None, edi_format_ref='account_edi_peppol.edi_peppol_3_10'):
        super().setUpClass(chart_template_ref=chart_template_ref, edi_format_ref=edi_format_ref)

        # ==== Init ====

        cls.company_data['company'].country_id = cls.env.ref('base.be')
        cls.company_data['company'].vat = 'BE0477472701'

        cls.partner_b.country_id = cls.env.ref('base.be')
        cls.partner_b.vat = 'BE0246697724'

        # ==== Invoice ====

        cls.invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'journal_id': cls.journal.id,
            'partner_id': cls.partner_b.id,
            'invoice_date': '2017-01-01',
            'date': '2017-01-01',
            'currency_id': cls.currency_data['currency'].id,
            'invoice_line_ids': [(0, 0, {
                'product_id': cls.product_a.id,
                'product_uom_id': cls.env.ref('uom.product_uom_dozen').id,
                'price_unit': 275.0,
                'quantity': 5,
                'discount': 20.0,
                'tax_ids': [(6, 0, cls.tax_sale_a.ids)],
            })],
        })

        cls.expected_peppol_values = '''
            <Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2" xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
                <cbc:CustomizationID>urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0</cbc:CustomizationID>
                <cbc:ProfileID>urn:fdc:peppol.eu:2017:poacc:billing:01:1.0</cbc:ProfileID>
                <cbc:ID>INV/2017/01/0001</cbc:ID>
                <cbc:IssueDate>2017-01-01</cbc:IssueDate>
                <cbc:DueDate>2017-01-01</cbc:DueDate>
                <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>
                <cbc:DocumentCurrencyCode>Gol</cbc:DocumentCurrencyCode>
                <cbc:TaxCurrencyCode>USD</cbc:TaxCurrencyCode>
                <cac:AccountingSupplierParty>
                    <cac:Party>
                        <cbc:EndpointID schemeID="9925">BE0477472701</cbc:EndpointID>
                        <cac:PartyIdentification>
                            <cbc:ID>BE0477472701</cbc:ID>
                        </cac:PartyIdentification>
                        <cac:PartyName>
                            <cbc:Name>company_1_data</cbc:Name>
                        </cac:PartyName>
                        <cac:PostalAddress>
                            <cac:Country>
                                <cbc:IdentificationCode>BE</cbc:IdentificationCode>
                            </cac:Country>
                        </cac:PostalAddress>
                        <cac:PartyTaxScheme>
                            <cbc:CompanyID>BE0477472701</cbc:CompanyID>
                            <cac:TaxScheme>
                                <cbc:ID>VAT</cbc:ID>
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
                        <cbc:EndpointID schemeID="9925">BE0246697724</cbc:EndpointID>
                        <cac:PartyIdentification>
                            <cbc:ID>BE0246697724</cbc:ID>
                        </cac:PartyIdentification>
                        <cac:PartyName>
                            <cbc:Name>partner_b</cbc:Name>
                        </cac:PartyName>
                        <cac:PostalAddress>
                            <cac:Country>
                                <cbc:IdentificationCode>BE</cbc:IdentificationCode>
                            </cac:Country>
                        </cac:PostalAddress>
                        <cac:PartyTaxScheme>
                            <cbc:CompanyID>BE0246697724</cbc:CompanyID>
                            <cac:TaxScheme>
                                <cbc:ID>VAT</cbc:ID>
                            </cac:TaxScheme>
                        </cac:PartyTaxScheme>
                        <cac:PartyLegalEntity>
                            <cbc:RegistrationName>partner_b</cbc:RegistrationName>
                        </cac:PartyLegalEntity>
                        <cac:Contact>
                            <cbc:Name>partner_b</cbc:Name>
                        </cac:Contact>
                    </cac:Party>
                </cac:AccountingCustomerParty>
                <cac:PaymentMeans>
                    <cbc:PaymentMeansCode>31</cbc:PaymentMeansCode>
                </cac:PaymentMeans>
                <cac:TaxTotal>
                    <cbc:TaxAmount currencyID="Gol">165.000</cbc:TaxAmount>
                    <cac:TaxSubtotal>
                        <cbc:TaxableAmount currencyID="Gol">1100.000</cbc:TaxableAmount>
                        <cbc:TaxAmount currencyID="Gol">165.000</cbc:TaxAmount>
                        <cac:TaxCategory>
                            <cbc:ID>S</cbc:ID>
                            <cbc:Percent>15.0</cbc:Percent>
                            <cac:TaxScheme>
                                <cbc:ID>VAT</cbc:ID>
                            </cac:TaxScheme>
                        </cac:TaxCategory>
                    </cac:TaxSubtotal>
                </cac:TaxTotal>
                <cac:TaxTotal>
                    <cbc:TaxAmount currencyID="USD">41.250</cbc:TaxAmount>
                </cac:TaxTotal>
                <cac:LegalMonetaryTotal>
                    <cbc:LineExtensionAmount currencyID="Gol">1100.000</cbc:LineExtensionAmount>
                    <cbc:TaxExclusiveAmount currencyID="Gol">1100.000</cbc:TaxExclusiveAmount>
                    <cbc:TaxInclusiveAmount currencyID="Gol">1265.000</cbc:TaxInclusiveAmount>
                    <cbc:PrepaidAmount currencyID="Gol">0.000</cbc:PrepaidAmount>
                    <cbc:PayableAmount currencyID="Gol">1265.000</cbc:PayableAmount>
                </cac:LegalMonetaryTotal>
                <cac:InvoiceLine>
                    <cbc:ID>1</cbc:ID>
                    <cbc:Note>Discount (20.0 %)</cbc:Note>
                    <cbc:InvoicedQuantity unitCode="ZZ">5.0</cbc:InvoicedQuantity>
                    <cbc:LineExtensionAmount currencyID="Gol">1100.000</cbc:LineExtensionAmount>
                    <cac:Item>
                        <cbc:Description>product_a</cbc:Description>
                        <cbc:Name>product_a</cbc:Name>
                            <cac:ClassifiedTaxCategory>
                                <cbc:ID>S</cbc:ID>
                                <cbc:Percent>15.0</cbc:Percent>
                                <cac:TaxScheme>
                                    <cbc:ID>VAT</cbc:ID>
                                </cac:TaxScheme>
                            </cac:ClassifiedTaxCategory>
                    </cac:Item>
                    <cac:Price>
                        <cbc:PriceAmount currencyID="Gol">1100.000</cbc:PriceAmount>
                        <cbc:BaseQuantity>5.0</cbc:BaseQuantity>
                    </cac:Price>
                </cac:InvoiceLine>
            </Invoice>
        '''

    def test_peppol_export(self):
        ''' Test the generated Facturx Edi attachment without any modification of the invoice. '''
        self.assert_generated_file_equal(self.invoice, self.expected_peppol_values)

    def test_peppol_export_no_tax(self):
        self.invoice.write({
            'invoice_line_ids': [
                (1, self.invoice.invoice_line_ids[0].id, {'tax_ids': [(5, 0)]}),
            ]
        })

        applied_xpath = '''
            <xpath expr="(//*[name()='cac:TaxTotal'])[1]" position="replace" />
            <xpath expr="(//*[name()='cac:TaxTotal'])[1]" position="replace" >
                <cac:TaxTotal>
                    <cbc:TaxAmount currencyID="Gol">0.000</cbc:TaxAmount>
                    <cac:TaxSubtotal>
                        <cbc:TaxableAmount currencyID="Gol">1100.000</cbc:TaxableAmount>
                        <cbc:TaxAmount currencyID="Gol">0.000</cbc:TaxAmount>
                        <cac:TaxCategory>
                            <cbc:ID>Z</cbc:ID>
                            <cbc:Percent>0</cbc:Percent>
                            <cac:TaxScheme>
                                <cbc:ID>VAT</cbc:ID>
                            </cac:TaxScheme>
                        </cac:TaxCategory>
                    </cac:TaxSubtotal>
                </cac:TaxTotal>
                <cac:TaxTotal>
                    <cbc:TaxAmount currencyID="USD">0.000</cbc:TaxAmount>
                </cac:TaxTotal>
            </xpath>
            <xpath expr="//*[name()='cbc:TaxInclusiveAmount']" position="replace">
                    <cbc:TaxInclusiveAmount currencyID="Gol">1100.000</cbc:TaxInclusiveAmount>
            </xpath>
            <xpath expr="//*[name()='cbc:PayableAmount']" position="replace">
                    <cbc:PayableAmount currencyID="Gol">1100.000</cbc:PayableAmount>
            </xpath>
            <xpath expr="//*[name()='cac:ClassifiedTaxCategory']" position="replace">
                <cac:ClassifiedTaxCategory>
                    <cbc:ID>Z</cbc:ID>
                    <cbc:Percent>0</cbc:Percent>
                    <cac:TaxScheme>
                        <cbc:ID>VAT</cbc:ID>
                    </cac:TaxScheme>
                </cac:ClassifiedTaxCategory>
            </xpath>
        '''
        ns_prefix = 'xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"'

        self.assert_generated_file_equal(self.invoice, self.expected_peppol_values, applied_xpath=applied_xpath, ns_prefix=ns_prefix)

    def test_peppol_invoice_import(self):
        xml_file_path = get_module_resource('account_edi_peppol', 'test_xml_file', 'peppol_test.xml')
        xml_file = open(xml_file_path, 'rb').read()
        invoice = self.env['account.move'].with_context(default_move_type='in_invoice').create({})

        attachment_id = self.env['ir.attachment'].create({
            'name': 'peppol_test.xml',
            'datas': base64.encodebytes(xml_file),
            'res_id': invoice.id,
            'res_model': 'account.move',
        })

        invoice.message_post(attachment_ids=[attachment_id.id])

        self.assertEqual(invoice.amount_total, 368)
        self.assertEqual(invoice.amount_tax, 48)
        self.assertEqual(len(invoice.invoice_line_ids), 1)
