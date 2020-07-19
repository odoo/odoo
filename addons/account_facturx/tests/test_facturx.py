# -*- coding: utf-8 -*-
from odoo.addons.account.tests.account_test_xml import AccountTestEdiCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountEdiFacturx(AccountTestEdiCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

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

        # ==== EDI ====

        cls.journal = cls.company_data['default_journal_sale']

        # ==== Invoice ====

        cls.invoice = cls.env['account.move'].create({
            'type': 'out_invoice',
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
                        <ID>urn:cen.eu:en16931:2017</ID>
                    </GuidelineSpecifiedDocumentContextParameter>
                </ExchangedDocumentContext>
                <ExchangedDocument>
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
                                <ChargeAmount currencyID="Gol">275.000</ChargeAmount>
                                <AppliedTradeAllowanceCharge>
                                    <ChargeIndicator>
                                        <Indicator>true</Indicator>
                                    </ChargeIndicator>
                                    <CalculationPercent>20.0</CalculationPercent>
                                </AppliedTradeAllowanceCharge>
                            </GrossPriceProductTradePrice>
                        </SpecifiedLineTradeAgreement>
                        <SpecifiedLineTradeDelivery>
                            <BilledQuantity>5.0</BilledQuantity>
                        </SpecifiedLineTradeDelivery>
                        <SpecifiedLineTradeSettlement>
                            <ApplicableTradeTax>
                                <RateApplicablePercent>20.0</RateApplicablePercent>
                            </ApplicableTradeTax>
                            <SpecifiedTradeSettlementLineMonetarySummation>
                                <LineTotalAmount currencyID="Gol">1100.000</LineTotalAmount>
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
                            <IssuerAssignedID>INV/2017/0001: INV/2017/0001</IssuerAssignedID>
                        </BuyerOrderReferencedDocument>
                    </ApplicableHeaderTradeAgreement>
                    <ApplicableHeaderTradeDelivery/>
                    <ApplicableHeaderTradeSettlement>
                        <ApplicableTradeTax>
                            <CalculatedAmount currencyID="Gol">220.000</CalculatedAmount>
                            <BasisAmount currencyID="Gol">1100.000</BasisAmount>
                            <RateApplicablePercent>20.0</RateApplicablePercent>
                        </ApplicableTradeTax>
                        <SpecifiedTradePaymentTerms>
                            <DueDateDateTime>
                                <DateTimeString>20170101</DateTimeString>
                            </DueDateDateTime>
                        </SpecifiedTradePaymentTerms>
                        <SpecifiedTradeSettlementHeaderMonetarySummation>
                            <LineTotalAmount currencyID="Gol">1100.000</LineTotalAmount>
                            <TaxBasisTotalAmount currencyID="Gol">1100.000</TaxBasisTotalAmount>
                            <TaxTotalAmount currencyID="Gol">220.000</TaxTotalAmount>
                            <GrandTotalAmount currencyID="Gol">1320.000</GrandTotalAmount>
                            <TotalPrepaidAmount currencyID="Gol">0.000</TotalPrepaidAmount>
                            <DuePayableAmount currencyID="Gol">1320.000</DuePayableAmount>
                        </SpecifiedTradeSettlementHeaderMonetarySummation>
                    </ApplicableHeaderTradeSettlement>
                </SupplyChainTradeTransaction>
            </CrossIndustryInvoice>
        '''

    def test_facturx(self):
        ''' Test the generated Facturx Edi attachment without any modification of the invoice. '''

        with self.mocked_today('2017-02-01'):
            self.invoice.post()

            current_etree = self.get_xml_tree_from_string(self.invoice._export_as_facturx_xml())
            expected_etree = self.get_xml_tree_from_string(self.expected_invoice_facturx_values)
            self.assertXmlTreeEqual(current_etree, expected_etree)

    def test_facturx_group_of_taxes(self):
        ''' Same as above with a group of taxes. '''
        self.invoice.write({
            'invoice_line_ids': [(1, self.invoice.invoice_line_ids.id, {'tax_ids': [(6, 0, self.tax_group.ids)]})],
        })

        with self.mocked_today('2017-02-01'):
            self.invoice.post()

            current_etree = self.get_xml_tree_from_string(self.invoice._export_as_facturx_xml())
            expected_etree = self.with_applied_xpath(
                self.get_xml_tree_from_string(self.expected_invoice_facturx_values),
                '''
                    <xpath expr="//GrossPriceProductTradePrice/ChargeAmount" position="replace">
                        <ChargeAmount currencyID="Gol">275.000</ChargeAmount>
                    </xpath>
                    <xpath expr="//SpecifiedLineTradeSettlement" position="replace">
                        <SpecifiedLineTradeSettlement>
                            <ApplicableTradeTax>
                                <RateApplicablePercent>10.0</RateApplicablePercent>
                            </ApplicableTradeTax>
                            <ApplicableTradeTax>
                                <RateApplicablePercent>20.0</RateApplicablePercent>
                            </ApplicableTradeTax>
                            <SpecifiedTradeSettlementLineMonetarySummation>
                                <LineTotalAmount currencyID="Gol">1000.000</LineTotalAmount>
                            </SpecifiedTradeSettlementLineMonetarySummation>
                        </SpecifiedLineTradeSettlement>
                    </xpath>
                    <xpath expr="//ApplicableHeaderTradeSettlement" position="replace">
                        <ApplicableHeaderTradeSettlement>
                            <ApplicableTradeTax>
                                <CalculatedAmount currencyID="Gol">220.000</CalculatedAmount>
                                <BasisAmount currencyID="Gol">1100.000</BasisAmount>
                                <RateApplicablePercent>20.0</RateApplicablePercent>
                            </ApplicableTradeTax>
                            <ApplicableTradeTax>
                                <CalculatedAmount currencyID="Gol">100.000</CalculatedAmount>
                                <BasisAmount currencyID="Gol">1000.000</BasisAmount>
                                <RateApplicablePercent>10.0</RateApplicablePercent>
                            </ApplicableTradeTax>
                            <SpecifiedTradePaymentTerms>
                                <DueDateDateTime>
                                    <DateTimeString>20170101</DateTimeString>
                                </DueDateDateTime>
                            </SpecifiedTradePaymentTerms>
                            <SpecifiedTradeSettlementHeaderMonetarySummation>
                                <LineTotalAmount currencyID="Gol">1000.000</LineTotalAmount>
                                <TaxBasisTotalAmount currencyID="Gol">1000.000</TaxBasisTotalAmount>
                                <TaxTotalAmount currencyID="Gol">320.000</TaxTotalAmount>
                                <GrandTotalAmount currencyID="Gol">1320.000</GrandTotalAmount>
                                <TotalPrepaidAmount currencyID="Gol">0.000</TotalPrepaidAmount>
                                <DuePayableAmount currencyID="Gol">1320.000</DuePayableAmount>
                            </SpecifiedTradeSettlementHeaderMonetarySummation>
                        </ApplicableHeaderTradeSettlement>
                    </xpath>
                ''',
            )
            self.assertXmlTreeEqual(current_etree, expected_etree)
