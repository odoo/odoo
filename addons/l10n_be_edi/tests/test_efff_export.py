# -*- coding: utf-8 -*-
import base64
import io
from PyPDF2 import PdfFileWriter, PdfFileReader

from odoo.addons.account_edi.tests.common import AccountEdiTestCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUBLBE(AccountEdiTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_be.l10nbe_chart_template', edi_format_ref='l10n_be_edi.edi_efff_1'):
        super().setUpClass(chart_template_ref=chart_template_ref, edi_format_ref=edi_format_ref)

        cls.partner_a.write({
            'street': "Chaussée de Namur 40",
            'zip': "1367",
            'city': "Ramillies",
            'vat': 'BE0202239951',
            'country_id': cls.env.ref('base.be').id,
        })

        cls.env.company.write({
            'street': "Rue des Bourlottes 9",
            'zip': "1367",
            'city': "Ramillies",
            'vat': 'BE0477472701',
            'country_id': cls.env.ref('base.be').id,
        })

        cls.tax_21 = cls.env['account.tax'].create({
            'name': 'tax_21',
            'amount_type': 'percent',
            'amount': 21,
            'type_tax_use': 'sale',
        })

    def test_out_invoice_efff(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_payment_term_id': self.pay_terms_b.id,
            'invoice_date': '2017-01-01',
            'date': '2017-01-01',
            'ref': 'test invoice ref',
            'narration': 'test narration',
            'invoice_line_ids': [(0, 0, {
                'price_unit': 1000.0,
                'product_id': self.product_a.id,
                'tax_ids': [(6, 0, self.tax_21.ids)],
            })],
        })
        invoice.action_post()

        # Print the invoice to append AdditionalDocumentReference.
        pdf_buffer = io.BytesIO()
        pdf_writer = PdfFileWriter()
        pdf_writer.addBlankPage(42, 42)
        pdf_writer.write(pdf_buffer)
        self.env.ref('account.account_invoices_without_payment')._postprocess_pdf_report(invoice, pdf_buffer)
        pdf_buffer.close()

        attachment = invoice._get_edi_attachment(self.edi_format)
        self.assertTrue(attachment)
        xml_content = base64.b64decode(attachment.datas)

        current_etree = self.get_xml_tree_from_string(xml_content)
        expected_etree = self.get_xml_tree_from_string(f'''
            <Invoice>
                <UBLVersionID>2.0</UBLVersionID>
                <ID>{invoice.name}</ID>
                <IssueDate>2017-01-01</IssueDate>
                <InvoiceTypeCode>380</InvoiceTypeCode>
                <Note>test narration</Note>
                <DocumentCurrencyCode>EUR</DocumentCurrencyCode>
                <OrderReference>
                    <ID>test invoice ref</ID>
                </OrderReference>
                <AdditionalDocumentReference>
                    <ID>efff_BE0477472701_INV201700001.pdf</ID>
                    <Attachment>
                        <EmbeddedDocumentBinaryObject
                            mimeCode="application/pdf"
                            filename="efff_BE0477472701_INV201700001.pdf">___ignore___</EmbeddedDocumentBinaryObject>
                    </Attachment>
                </AdditionalDocumentReference>
                <AccountingSupplierParty>
                    <Party>
                        <PartyName>
                            <Name>company_1_data</Name>
                        </PartyName>
                        <Language>
                            <LocaleCode>en_US</LocaleCode>
                        </Language>
                        <PostalAddress>
                            <StreetName>Rue des Bourlottes 9</StreetName>
                            <CityName>Ramillies</CityName>
                            <PostalZone>1367</PostalZone>
                            <Country>
                                <IdentificationCode>BE</IdentificationCode>
                                <Name>Belgium</Name>
                            </Country>
                        </PostalAddress>
                        <PartyTaxScheme>
                            <RegistrationName>company_1_data</RegistrationName>
                            <CompanyID>BE0477472701</CompanyID>
                            <TaxScheme>
                                <ID schemeID="UN/ECE 5153" schemeAgencyID="6">VAT</ID>
                            </TaxScheme>
                        </PartyTaxScheme>
                        <Contact>
                            <Name>company_1_data</Name>
                        </Contact>
                    </Party>
                </AccountingSupplierParty>
                <AccountingCustomerParty>
                    <Party>
                        <PartyName>
                            <Name>partner_a</Name>
                        </PartyName>
                        <Language>
                            <LocaleCode>en_US</LocaleCode>
                        </Language>
                        <PostalAddress>
                            <StreetName>Chaussée de Namur 40</StreetName>
                            <CityName>Ramillies</CityName>
                            <PostalZone>1367</PostalZone>
                            <Country>
                                <IdentificationCode>BE</IdentificationCode>
                                <Name>Belgium</Name>
                            </Country>
                        </PostalAddress>
                        <PartyTaxScheme>
                            <RegistrationName>partner_a</RegistrationName>
                            <CompanyID>BE0202239951</CompanyID>
                            <TaxScheme>
                                <ID schemeID="UN/ECE 5153" schemeAgencyID="6">VAT</ID>
                            </TaxScheme>
                        </PartyTaxScheme>
                        <Contact>
                            <Name>partner_a</Name>
                        </Contact>
                    </Party>
                </AccountingCustomerParty>
                <PaymentMeans>
                    <PaymentMeansCode listID="UN/ECE 4461">31</PaymentMeansCode>
                    <PaymentDueDate>2017-02-28</PaymentDueDate>
                    <InstructionID>{invoice.name}</InstructionID>
                </PaymentMeans>
                <PaymentTerms>
                    <Note>30% Advance End of Following Month</Note>
                </PaymentTerms>
                <TaxTotal>
                    <TaxAmount currencyID="EUR">210.00</TaxAmount>
                </TaxTotal>
                <LegalMonetaryTotal>
                    <LineExtensionAmount currencyID="EUR">1000.00</LineExtensionAmount>
                    <TaxExclusiveAmount currencyID="EUR">1000.00</TaxExclusiveAmount>
                    <TaxInclusiveAmount currencyID="EUR">1210.00</TaxInclusiveAmount>
                    <PrepaidAmount currencyID="EUR">0.00</PrepaidAmount>
                    <PayableAmount currencyID="EUR">1210.00</PayableAmount>
                </LegalMonetaryTotal>
                <InvoiceLine>
                    <ID>___ignore___</ID>
                    <InvoicedQuantity>1.0</InvoicedQuantity>
                    <LineExtensionAmount currencyID="EUR">1000.00</LineExtensionAmount>
                    <TaxTotal>
                        <TaxAmount currencyID="EUR">210.00</TaxAmount>
                    </TaxTotal>
                    <Item>
                        <Description>product_a</Description>
                        <Name>product_a</Name>
                    </Item>
                    <Price>
                        <PriceAmount currencyID="EUR">1000.00</PriceAmount>
                    </Price>
                </InvoiceLine>
            </Invoice>
        ''')
        self.assertXmlTreeEqual(current_etree, expected_etree)
