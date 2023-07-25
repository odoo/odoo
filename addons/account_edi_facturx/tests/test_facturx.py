# -*- coding: utf-8 -*-
from freezegun import freeze_time
from odoo.addons.account_edi.tests.common import AccountEdiTestCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountEdiFacturx(AccountEdiTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None, edi_format_ref='account_edi_facturx.edi_facturx_1_0_05'):
        super().setUpClass(chart_template_ref=chart_template_ref, edi_format_ref=edi_format_ref)

        if cls.env['ir.module.module'].search(
            [('name', '=', 'account_edi_ubl_cii'), ('state', '=', 'installed')],
            limit=1,
        ):
            cls.skipTest(cls, "Factur-X Tests skipped because account_edi_ubl_cii is installed.")

        # ==== Init ====

        cls.tax_10_include = cls.env['account.tax'].create({
            'name': 'tax_10_include',
            'amount_type': 'percent',
            'amount': 10,
            'type_tax_use': 'sale',
            'price_include': True,
            'include_base_amount': True,
            'sequence': 10,
        })

        cls.tax_20 = cls.env['account.tax'].create({
            'name': 'tax_20',
            'amount_type': 'percent',
            'amount': 20,
            'type_tax_use': 'sale',
            'sequence': 20,
        })

        cls.tax_group = cls.env['account.tax'].create({
            'name': 'tax_group',
            'amount_type': 'group',
            'amount': 0.0,
            'type_tax_use': 'sale',
            'children_tax_ids': [(6, 0, (cls.tax_10_include + cls.tax_20).ids)],
        })

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
                'tax_ids': [(6, 0, cls.tax_20.ids)],
            })],
        })

        cls.expected_invoice_facturx_values = '''
            <CrossIndustryInvoice>
                <ExchangedDocumentContext>
                    <GuidelineSpecifiedDocumentContextParameter>
                        <ID>urn:cen.eu:en16931:2017#conformant#urn:factur-x.eu:1p0:extended</ID>
                    </GuidelineSpecifiedDocumentContextParameter>
                </ExchangedDocumentContext>
                <ExchangedDocument>
                    <ID>INV/2017/01/0001</ID>
                    <TypeCode>380</TypeCode>
                    <IssueDateTime>
                        <DateTimeString format="102">20170101</DateTimeString>
                    </IssueDateTime>
                </ExchangedDocument>
                <SupplyChainTradeTransaction>
                    <IncludedSupplyChainTradeLineItem>
                        <AssociatedDocumentLineDocument>
                            <LineID>1</LineID>
                        </AssociatedDocumentLineDocument>
                        <SpecifiedTradeProduct>
                            <Name>product_a</Name>
                        </SpecifiedTradeProduct>
                        <SpecifiedLineTradeAgreement>
                            <GrossPriceProductTradePrice>
                                <ChargeAmount>275.000</ChargeAmount>
                                <AppliedTradeAllowanceCharge>
                                    <ChargeIndicator>
                                        <Indicator>false</Indicator>
                                    </ChargeIndicator>
                                    <ActualAmount>55.000</ActualAmount>
                                </AppliedTradeAllowanceCharge>
                            </GrossPriceProductTradePrice>
                            <NetPriceProductTradePrice>
                                <ChargeAmount>220.000</ChargeAmount>
                            </NetPriceProductTradePrice>
                        </SpecifiedLineTradeAgreement>
                        <SpecifiedLineTradeDelivery>
                            <BilledQuantity unitCode="C62">5.0</BilledQuantity>
                        </SpecifiedLineTradeDelivery>
                        <SpecifiedLineTradeSettlement>
                            <ApplicableTradeTax>
                                <TypeCode>VAT</TypeCode>
                                <CategoryCode>S</CategoryCode>
                                <RateApplicablePercent>20.0</RateApplicablePercent>
                            </ApplicableTradeTax>
                            <SpecifiedTradeSettlementLineMonetarySummation>
                                <LineTotalAmount>1100.000</LineTotalAmount>
                            </SpecifiedTradeSettlementLineMonetarySummation>
                        </SpecifiedLineTradeSettlement>
                    </IncludedSupplyChainTradeLineItem>
                    <ApplicableHeaderTradeAgreement>
                        <SellerTradeParty>
                            <Name>company_1_data</Name>
                            <DefinedTradeContact>
                                <PersonName>company_1_data</PersonName>
                            </DefinedTradeContact>
                            <PostalTradeAddress/>
                        </SellerTradeParty>
                        <BuyerTradeParty>
                            <Name>partner_b</Name>
                            <DefinedTradeContact>
                                <PersonName>partner_b</PersonName>
                            </DefinedTradeContact>
                            <PostalTradeAddress/>
                        </BuyerTradeParty>
                        <BuyerOrderReferencedDocument>
                            <IssuerAssignedID>INV/2017/01/0001</IssuerAssignedID>
                        </BuyerOrderReferencedDocument>
                    </ApplicableHeaderTradeAgreement>
                    <ApplicableHeaderTradeDelivery>
                        <ShipToTradeParty>
                            <Name>partner_b</Name>
                            <DefinedTradeContact>
                                <PersonName>partner_b</PersonName>
                            </DefinedTradeContact>
                            <PostalTradeAddress/>
                        </ShipToTradeParty>
                    </ApplicableHeaderTradeDelivery>
                    <ApplicableHeaderTradeSettlement>
                        <InvoiceCurrencyCode>Gol</InvoiceCurrencyCode>
                        <ApplicableTradeTax>
                            <CalculatedAmount>220.000</CalculatedAmount>
                            <TypeCode>VAT</TypeCode>
                            <BasisAmount>1100.000</BasisAmount>
                            <CategoryCode>S</CategoryCode>
                            <RateApplicablePercent>20.0</RateApplicablePercent>
                        </ApplicableTradeTax>
                        <BillingSpecifiedPeriod>
                            <StartDateTime>
                                <DateTimeString format="102">20170101</DateTimeString>
                            </StartDateTime>
                        </BillingSpecifiedPeriod>
                        <SpecifiedTradePaymentTerms>
                            <DueDateDateTime>
                                <DateTimeString format="102">20170101</DateTimeString>
                            </DueDateDateTime>
                        </SpecifiedTradePaymentTerms>
                        <SpecifiedTradeSettlementHeaderMonetarySummation>
                            <LineTotalAmount>1100.000</LineTotalAmount>
                            <TaxBasisTotalAmount>1100.000</TaxBasisTotalAmount>
                            <TaxTotalAmount currencyID="Gol">220.000</TaxTotalAmount>
                            <GrandTotalAmount>1320.000</GrandTotalAmount>
                            <TotalPrepaidAmount>0.000</TotalPrepaidAmount>
                            <DuePayableAmount>1320.000</DuePayableAmount>
                        </SpecifiedTradeSettlementHeaderMonetarySummation>
                    </ApplicableHeaderTradeSettlement>
                </SupplyChainTradeTransaction>
            </CrossIndustryInvoice>
        '''

    ####################################################
    # Test export
    ####################################################

    def test_facturx(self):
        ''' Test the generated Facturx Edi attachment without any modification of the invoice. '''
        self.assert_generated_file_equal(self.invoice, self.expected_invoice_facturx_values)

    @freeze_time('2017-02-01')
    def test_facturx_group_of_taxes(self):
        ''' Same as above with a group of taxes. '''
        self.invoice.write({
            'invoice_line_ids': [(1, self.invoice.invoice_line_ids.id, {'tax_ids': [(6, 0, self.tax_group.ids)]})],
        })

        applied_xpath = '''
                    <xpath expr="//AppliedTradeAllowanceCharge/ActualAmount" position="replace">
                        <ActualAmount>50.000</ActualAmount>
                    </xpath>
                    <xpath expr="//NetPriceProductTradePrice/ChargeAmount" position="replace">
                        <ChargeAmount>200.000</ChargeAmount>
                    </xpath>
                    <xpath expr="//SpecifiedLineTradeSettlement" position="replace">
                        <SpecifiedLineTradeSettlement>
                            <ApplicableTradeTax>
                                <TypeCode>VAT</TypeCode>
                                <CategoryCode>S</CategoryCode>
                                <RateApplicablePercent>10.0</RateApplicablePercent>
                            </ApplicableTradeTax>
                            <ApplicableTradeTax>
                                <TypeCode>VAT</TypeCode>
                                <CategoryCode>S</CategoryCode>
                                <RateApplicablePercent>20.0</RateApplicablePercent>
                            </ApplicableTradeTax>
                            <SpecifiedTradeSettlementLineMonetarySummation>
                                <LineTotalAmount>1000.000</LineTotalAmount>
                            </SpecifiedTradeSettlementLineMonetarySummation>
                        </SpecifiedLineTradeSettlement>
                    </xpath>
                    <xpath expr="//ApplicableHeaderTradeSettlement" position="replace">
                        <ApplicableHeaderTradeSettlement>
                        <InvoiceCurrencyCode>Gol</InvoiceCurrencyCode>
                            <ApplicableTradeTax>
                                <CalculatedAmount>100.000</CalculatedAmount>
                                <TypeCode>VAT</TypeCode>
                                <BasisAmount>1000.000</BasisAmount>
                                <CategoryCode>S</CategoryCode>
                                <RateApplicablePercent>10.0</RateApplicablePercent>
                            </ApplicableTradeTax>
                            <ApplicableTradeTax>
                                <CalculatedAmount>220.000</CalculatedAmount>
                                <TypeCode>VAT</TypeCode>
                                <BasisAmount>1100.000</BasisAmount>
                                <CategoryCode>S</CategoryCode>
                                <RateApplicablePercent>20.0</RateApplicablePercent>
                            </ApplicableTradeTax>
                            <BillingSpecifiedPeriod>
                                <StartDateTime>
                                    <DateTimeString format="102">20170101</DateTimeString>
                                </StartDateTime>
                            </BillingSpecifiedPeriod>
                            <SpecifiedTradePaymentTerms>
                                <DueDateDateTime>
                                    <DateTimeString format="102">20170101</DateTimeString>
                                </DueDateDateTime>
                            </SpecifiedTradePaymentTerms>
                            <SpecifiedTradeSettlementHeaderMonetarySummation>
                                <LineTotalAmount>1000.000</LineTotalAmount>
                                <TaxBasisTotalAmount>1000.000</TaxBasisTotalAmount>
                                <TaxTotalAmount currencyID="Gol">320.000</TaxTotalAmount>
                                <GrandTotalAmount>1320.000</GrandTotalAmount>
                                <TotalPrepaidAmount>0.000</TotalPrepaidAmount>
                                <DuePayableAmount>1320.000</DuePayableAmount>
                            </SpecifiedTradeSettlementHeaderMonetarySummation>
                        </ApplicableHeaderTradeSettlement>
                    </xpath>
        '''

        self.assert_generated_file_equal(self.invoice, self.expected_invoice_facturx_values, applied_xpath)

    def test_export_pdf(self):
        self.invoice.action_post()
        pdf_values = self.edi_format._get_embedding_to_invoice_pdf_values(self.invoice)
        self.assertEqual(pdf_values['name'], 'factur-x.xml')

    ####################################################
    # Test import
    ####################################################

    def test_invoice_edi_pdf(self):
        invoice = self._create_empty_vendor_bill()
        invoice_count = len(self.env['account.move'].search([]))
        self.update_invoice_from_file('account_edi_facturx', 'test_file', 'test_facturx.pdf', invoice)

        self.assertEqual(len(self.env['account.move'].search([])), invoice_count)
        self.assertEqual(invoice.amount_total, 525)

        self.create_invoice_from_file('account_edi_facturx', 'test_file', 'test_facturx.pdf')

        self.assertEqual(invoice.amount_total, 525)
        self.assertEqual(len(self.env['account.move'].search([])), invoice_count + 1)

    def test_invoice_edi_xml(self):
        invoice = self._create_empty_vendor_bill()
        invoice_count = len(self.env['account.move'].search([]))
        self.update_invoice_from_file('account_edi_facturx', 'test_file', 'test_facturx.xml', invoice)

        self.assertEqual(len(self.env['account.move'].search([])), invoice_count)
        self.assertEqual(invoice.amount_total, 4610)

        self.create_invoice_from_file('account_edi_facturx', 'test_file', 'test_facturx.xml')

        self.assertEqual(invoice.amount_total, 4610)
        self.assertEqual(len(self.env['account.move'].search([])), invoice_count + 1)

    def test_invoice_edi_multicompany(self):
        # Create taxes that will match the first line of the facturx invoice
        my_company_id = TestAccountEdiFacturx.company_data['company'].id
        other_company_id = TestAccountEdiFacturx.company_data_2['company'].id

        common_tax_fields = dict(amount_type='percent', type_tax_use='purchase', amount=0.0)
        self.env['account.tax'].create([
            dict(name="OtherCompany Tax", company_id=other_company_id, sequence=10, **common_tax_fields),
            dict(name="MyCompany Tax",    company_id=my_company_id,    sequence=20, **common_tax_fields),
        ])

        invoice = self._create_empty_vendor_bill()
        self.update_invoice_from_file('account_edi_facturx', 'test_file', 'test_facturx.xml', invoice)

        tax_ids = invoice.line_ids.tax_ids
        self.assertEqual(len(tax_ids), 1)
        self.assertEqual(tax_ids[0].name, "MyCompany Tax")
