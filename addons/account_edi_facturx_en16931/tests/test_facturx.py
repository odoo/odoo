# -*- coding: utf-8 -*-
from freezegun import freeze_time
from odoo.addons.account_edi.tests.common import AccountEdiTestCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountEdiFacturx(AccountEdiTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None, edi_format_ref='account_edi_facturx_en16931.edi_facturx_2_2'):
        #chart_template_ref = "l10n_fr.l10n_fr_pcg_chart_template"
        super().setUpClass(chart_template_ref=chart_template_ref, edi_format_ref=edi_format_ref)

        # ==== Init ====

        cls.partner_b.update({
            'street': "35 rue de la République",
            'city': "Lyon",
            'zip': 69001,
            'country_id': cls.env.ref('base.fr'),
            'ref': 'SERVICE EXEC',
        })

        cls.acc_iban = cls.env['res.partner.bank'].create({
            'acc_number': 'FR15001559627230',
            'partner_id': cls.company_data['company'].partner_id.id,
        })

        cls.company_data['company'].update({
            'street': "1242 chemin de l'olive",
            'zip': 84340,
            'city': "Malaucène",
            'country_id': cls.env.ref('base.fr'),
            'vat': "FR11999999998",
            'phone': "+33472070855",
            'email': "sav@majolieboutique.net",
        })

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

        # the following is needed when importing the test pdf, otherwise, no matching tax is found and the total
        # of the invoice is incorrect
        cls.tax_20_purchase = cls.env['account.tax'].create({
            'name': 'tax_20_purchase',
            'amount_type': 'percent',
            'amount': 20,
            'type_tax_use': 'purchase',
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
            'invoice_date': '2017-11-13',
            'date': '2017-01-01',
            'currency_id': cls.env.ref('base.EUR'),
            'invoice_line_ids': [(0, 0, {
                'product_id': cls.product_a.id,
                'product_uom_id': cls.env.ref('uom.product_uom_dozen').id,
                'price_unit': 275.0,
                'quantity': 5,
                'discount': 20.0,
                'tax_ids': [(6, 0, cls.tax_20.ids)],
            })],
            'partner_bank_id': cls.acc_iban.id,
        })

        cls.expected_invoice_facturx_values = '''
            <CrossIndustryInvoice xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100" xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100" xmlns:qdt="urn:un:unece:uncefact:data:standard:QualifiedDataType:100">
              <ExchangedDocumentContext>
                <GuidelineSpecifiedDocumentContextParameter>
                  <ID>urn:cen.eu:en16931:2017</ID>
                </GuidelineSpecifiedDocumentContextParameter>
              </ExchangedDocumentContext>
              <ExchangedDocument>
                <ID>INV/2017/01/0001</ID>
                <TypeCode>380</TypeCode>
                <IssueDateTime>
                  <DateTimeString format="102">20171113</DateTimeString>
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
                      <ChargeAmount>275.00</ChargeAmount>
                    </GrossPriceProductTradePrice>
                    <NetPriceProductTradePrice>
                      <ChargeAmount>220.00</ChargeAmount>
                    </NetPriceProductTradePrice>
                  </SpecifiedLineTradeAgreement>
                  <SpecifiedLineTradeDelivery>
                    <BilledQuantity unitCode="DZN">5.0</BilledQuantity>
                  </SpecifiedLineTradeDelivery>
                  <SpecifiedLineTradeSettlement>
                    <ApplicableTradeTax>
                      <TypeCode>VAT</TypeCode>
                      <CategoryCode>S</CategoryCode>
                      <RateApplicablePercent>20.0</RateApplicablePercent>
                    </ApplicableTradeTax>
                    <SpecifiedTradeAllowanceCharge>
                      <ChargeIndicator>
                        <Indicator>false</Indicator>
                      </ChargeIndicator>
                      <ActualAmount>55.00</ActualAmount>
                      <ReasonCode>95</ReasonCode>
                    </SpecifiedTradeAllowanceCharge>
                    <SpecifiedTradeSettlementLineMonetarySummation>
                      <LineTotalAmount>1100.00</LineTotalAmount>
                    </SpecifiedTradeSettlementLineMonetarySummation>
                  </SpecifiedLineTradeSettlement>
                </IncludedSupplyChainTradeLineItem>
                <ApplicableHeaderTradeAgreement>
                  <BuyerReference>SERVICE EXEC</BuyerReference>
                  <SellerTradeParty>
                    <Name>company_1_data</Name>
                    <DefinedTradeContact>
                      <PersonName>company_1_data</PersonName>
                      <TelephoneUniversalCommunication>
                        <CompleteNumber>+33472070855</CompleteNumber>
                      </TelephoneUniversalCommunication>
                      <EmailURIUniversalCommunication>
                        <URIID schemeID="SMTP">sav@majolieboutique.net</URIID>
                      </EmailURIUniversalCommunication>
                    </DefinedTradeContact>
                    <PostalTradeAddress>
                      <PostcodeCode>84340</PostcodeCode>
                      <LineOne>1242 chemin de l'olive</LineOne>
                      <CityName>Malaucène</CityName>
                      <CountryID>FR</CountryID>
                    </PostalTradeAddress>
                    <SpecifiedTaxRegistration>
                      <ID schemeID="VA">FR11999999998</ID>
                    </SpecifiedTaxRegistration>
                  </SellerTradeParty>
                  <BuyerTradeParty>
                    <Name>partner_b</Name>
                    <DefinedTradeContact>
                      <PersonName>partner_b</PersonName>
                    </DefinedTradeContact>
                    <PostalTradeAddress>
                      <PostcodeCode>69001</PostcodeCode>
                      <LineOne>35 rue de la République</LineOne>
                      <CityName>Lyon</CityName>
                      <CountryID>FR</CountryID>
                    </PostalTradeAddress>
                  </BuyerTradeParty>
                  <BuyerOrderReferencedDocument>
                    <IssuerAssignedID>INV/2017/01/0001: INV/2017/01/0001</IssuerAssignedID>
                  </BuyerOrderReferencedDocument>
                </ApplicableHeaderTradeAgreement>
                <ApplicableHeaderTradeDelivery>
                  <ShipToTradeParty>
                    <Name>partner_b</Name>
                    <PostalTradeAddress>
                      <PostcodeCode>69001</PostcodeCode>
                      <LineOne>35 rue de la République</LineOne>
                      <CityName>Lyon</CityName>
                      <CountryID>FR</CountryID>
                    </PostalTradeAddress>
                  </ShipToTradeParty>
                  <ActualDeliverySupplyChainEvent>
                    <OccurrenceDateTime>
                      <DateTimeString format="102">20171113</DateTimeString>
                    </OccurrenceDateTime>
                  </ActualDeliverySupplyChainEvent>
                </ApplicableHeaderTradeDelivery>
                <ApplicableHeaderTradeSettlement>
                  <PaymentReference>INV/2017/01/0001</PaymentReference>
                  <InvoiceCurrencyCode>EUR</InvoiceCurrencyCode>
                  <SpecifiedTradeSettlementPaymentMeans>
                    <TypeCode>30</TypeCode>
                    <PayeePartyCreditorFinancialAccount>
                      <ProprietaryID>FR15001559627230</ProprietaryID>
                    </PayeePartyCreditorFinancialAccount>
                  </SpecifiedTradeSettlementPaymentMeans>
                  <ApplicableTradeTax>
                    <CalculatedAmount>220.00</CalculatedAmount>
                    <TypeCode>VAT</TypeCode>
                    <BasisAmount>1100.00</BasisAmount>
                    <CategoryCode>S</CategoryCode>
                    <DueDateTypeCode>5</DueDateTypeCode>
                    <RateApplicablePercent>20.0</RateApplicablePercent>
                  </ApplicableTradeTax>
                  <SpecifiedTradePaymentTerms>
                    <DueDateDateTime>
                      <DateTimeString format="102">20171113</DateTimeString>
                    </DueDateDateTime>
                  </SpecifiedTradePaymentTerms>
                  <SpecifiedTradeSettlementHeaderMonetarySummation>
                    <LineTotalAmount>1100.00</LineTotalAmount>
                    <TaxBasisTotalAmount>1100.00</TaxBasisTotalAmount>
                    <TaxTotalAmount currencyID="EUR">220.00</TaxTotalAmount>
                    <GrandTotalAmount>1320.00</GrandTotalAmount>
                    <TotalPrepaidAmount>0.00</TotalPrepaidAmount>
                    <DuePayableAmount>1320.00</DuePayableAmount>
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
            <xpath expr="//NetPriceProductTradePrice/ChargeAmount" position="replace">
                <ChargeAmount>200.00</ChargeAmount>
            </xpath>
            <xpath expr="//IncludedSupplyChainTradeLineItem/SpecifiedLineTradeSettlement/ApplicableTradeTax" position="before">
                <ApplicableTradeTax>
                    <TypeCode>VAT</TypeCode>
                    <CategoryCode>S</CategoryCode>
                    <RateApplicablePercent>10.0</RateApplicablePercent>
                </ApplicableTradeTax>
            </xpath>
            <xpath expr="//SpecifiedTradeSettlementLineMonetarySummation/LineTotalAmount" position="replace">
                <LineTotalAmount>1000.00</LineTotalAmount>
            </xpath>
            <xpath expr="//ApplicableHeaderTradeSettlement/ApplicableTradeTax" position="before">
                <ApplicableTradeTax>
                    <CalculatedAmount>100.00</CalculatedAmount>
                    <TypeCode>VAT</TypeCode>
                    <BasisAmount>1000.00</BasisAmount>
                    <CategoryCode>S</CategoryCode>
                    <DueDateTypeCode>5</DueDateTypeCode>
                    <RateApplicablePercent>10.0</RateApplicablePercent>
			    </ApplicableTradeTax>
            </xpath>
            <xpath expr="//SpecifiedTradeSettlementHeaderMonetarySummation" position="replace">
                <SpecifiedTradeSettlementHeaderMonetarySummation>
                    <LineTotalAmount>1000.00</LineTotalAmount>
                    <TaxBasisTotalAmount>1000.00</TaxBasisTotalAmount>
                    <TaxTotalAmount currencyID="EUR">320.00</TaxTotalAmount>
                    <GrandTotalAmount>1320.00</GrandTotalAmount>
                    <TotalPrepaidAmount>0.00</TotalPrepaidAmount>
                    <DuePayableAmount>1320.00</DuePayableAmount>
                </SpecifiedTradeSettlementHeaderMonetarySummation>
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
        self.update_invoice_from_file('account_edi_facturx_en16931', 'test_file', 'test_facturx.pdf', invoice)

        self.assertEqual(len(self.env['account.move'].search([])), invoice_count)
        self.assertEqual(invoice.amount_total, 2321.76)

        self.create_invoice_from_file('account_edi_facturx_en16931', 'test_file', 'test_facturx.pdf')

        self.assertEqual(invoice.amount_total, 2321.76)
        self.assertEqual(len(self.env['account.move'].search([])), invoice_count + 1)
        # test the uom and discount are correctly imported
        self.assertEqual(invoice.invoice_line_ids[0].product_uom_id.name, 'Dozens')
        self.assertEqual(invoice.invoice_line_ids[0].discount, 0)
        self.assertEqual(invoice.invoice_line_ids[1].product_uom_id.name, 'Hours')
        self.assertEqual(invoice.invoice_line_ids[1].discount, 20)
        self.assertEqual(invoice.invoice_line_ids[2].product_uom_id.name, 'Units')
        self.assertEqual(invoice.invoice_line_ids[2].discount, 0)

    def test_invoice_edi_xml(self):
        invoice = self._create_empty_vendor_bill()
        invoice_count = len(self.env['account.move'].search([]))
        self.update_invoice_from_file('account_edi_facturx_en16931', 'test_file', 'test_facturx.xml', invoice)

        self.assertEqual(len(self.env['account.move'].search([])), invoice_count)
        self.assertEqual(invoice.amount_total, 2321.76)

        self.create_invoice_from_file('account_edi_facturx_en16931', 'test_file', 'test_facturx.xml')

        self.assertEqual(invoice.amount_total, 2321.76)
        self.assertEqual(len(self.env['account.move'].search([])), invoice_count + 1)
