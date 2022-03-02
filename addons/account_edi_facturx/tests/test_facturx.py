# -*- coding: utf-8 -*-
from freezegun import freeze_time
from odoo.addons.account_edi.tests.common import AccountEdiTestCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountEdiFacturx(AccountEdiTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_fr.l10n_fr_pcg_chart_template', edi_format_ref='account_edi_facturx.edi_facturx_1_0_05'):
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
            'partner_shipping_id': cls.partner_b,
            'partner_bank_id': cls.acc_iban.id,
        })

        cls.expected_invoice_facturx_values = '''
            <rsm:CrossIndustryInvoice xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:qdt="urn:un:unece:uncefact:data:standard:QualifiedDataType:100" xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100" xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100">
              <rsm:ExchangedDocumentContext>
                <ram:GuidelineSpecifiedDocumentContextParameter>
                  <ram:ID>urn:cen.eu:en16931:2017</ram:ID>
                </ram:GuidelineSpecifiedDocumentContextParameter>
              </rsm:ExchangedDocumentContext>
              <rsm:ExchangedDocument>
                <ram:ID>INV/2017/01/0001</ram:ID>
                <ram:TypeCode>380</ram:TypeCode>
                <ram:IssueDateTime>
                  <udt:DateTimeString format="102">20171113</udt:DateTimeString>
                </ram:IssueDateTime>
              </rsm:ExchangedDocument>
              <rsm:SupplyChainTradeTransaction>
                <ram:IncludedSupplyChainTradeLineItem>
                  <ram:AssociatedDocumentLineDocument>
                    <ram:LineID>1</ram:LineID>
                  </ram:AssociatedDocumentLineDocument>
                  <ram:SpecifiedTradeProduct>
                    <ram:Name>product_a</ram:Name>
                  </ram:SpecifiedTradeProduct>
                  <ram:SpecifiedLineTradeAgreement>
                    <ram:GrossPriceProductTradePrice>
                      <ram:ChargeAmount>275.00</ram:ChargeAmount>
                      <ram:AppliedTradeAllowanceCharge>
                        <ram:ChargeIndicator>
                          <udt:Indicator>false</udt:Indicator>
                        </ram:ChargeIndicator>
                        <ram:ActualAmount>55.00</ram:ActualAmount>
                      </ram:AppliedTradeAllowanceCharge>
                    </ram:GrossPriceProductTradePrice>
                    <ram:NetPriceProductTradePrice>
                      <ram:ChargeAmount>220.00</ram:ChargeAmount>
                    </ram:NetPriceProductTradePrice>
                  </ram:SpecifiedLineTradeAgreement>
                  <ram:SpecifiedLineTradeDelivery>
                    <ram:BilledQuantity unitCode="C62">0.417</ram:BilledQuantity>
                  </ram:SpecifiedLineTradeDelivery>
                  <ram:SpecifiedLineTradeSettlement>
                    <ram:ApplicableTradeTax>
                      <ram:TypeCode>VAT</ram:TypeCode>
                      <ram:CategoryCode>S</ram:CategoryCode>
                      <ram:RateApplicablePercent>20.0</ram:RateApplicablePercent>
                    </ram:ApplicableTradeTax>
                    <ram:SpecifiedTradeSettlementLineMonetarySummation>
                      <ram:LineTotalAmount>1100.00</ram:LineTotalAmount>
                    </ram:SpecifiedTradeSettlementLineMonetarySummation>
                  </ram:SpecifiedLineTradeSettlement>
                </ram:IncludedSupplyChainTradeLineItem>
                <ram:ApplicableHeaderTradeAgreement>
                  <ram:BuyerReference>SERVICE EXEC</ram:BuyerReference>
                  <ram:SellerTradeParty>
                    <ram:Name>company_1_data</ram:Name>
                    <ram:DefinedTradeContact>
                      <ram:PersonName>company_1_data</ram:PersonName>
                      <ram:TelephoneUniversalCommunication>
                        <ram:CompleteNumber>+33472070855</ram:CompleteNumber>
                      </ram:TelephoneUniversalCommunication>
                      <ram:EmailURIUniversalCommunication>
                        <ram:URIID schemeID="SMTP">sav@majolieboutique.net</ram:URIID>
                      </ram:EmailURIUniversalCommunication>
                    </ram:DefinedTradeContact>
                    <ram:PostalTradeAddress>
                      <ram:PostcodeCode>84340</ram:PostcodeCode>
                      <ram:LineOne>1242 chemin de l'olive</ram:LineOne>
                      <ram:CityName>Malaucène</ram:CityName>
                      <ram:CountryID>FR</ram:CountryID>
                    </ram:PostalTradeAddress>
                    <ram:SpecifiedTaxRegistration>
                      <ram:ID schemeID="VA">FR11999999998</ram:ID>
                    </ram:SpecifiedTaxRegistration>
                  </ram:SellerTradeParty>
                  <ram:BuyerTradeParty>
                    <ram:Name>partner_b</ram:Name>
                    <ram:DefinedTradeContact>
                      <ram:PersonName>partner_b</ram:PersonName>
                    </ram:DefinedTradeContact>
                    <ram:PostalTradeAddress>
                      <ram:PostcodeCode>69001</ram:PostcodeCode>
                      <ram:LineOne>35 rue de la République</ram:LineOne>
                      <ram:CityName>Lyon</ram:CityName>
                      <ram:CountryID>FR</ram:CountryID>
                    </ram:PostalTradeAddress>
                  </ram:BuyerTradeParty>
                  <ram:BuyerOrderReferencedDocument>
                    <ram:IssuerAssignedID>INV/2017/01/0001: INV/2017/01/0001</ram:IssuerAssignedID>
                  </ram:BuyerOrderReferencedDocument>
                </ram:ApplicableHeaderTradeAgreement>
                <ram:ApplicableHeaderTradeDelivery>
                  <ram:ShipToTradeParty>
                    <ram:PostalTradeAddress>
                      <ram:PostcodeCode>69001</ram:PostcodeCode>
                      <ram:LineOne>35 rue de la République</ram:LineOne>
                      <ram:CityName>Lyon</ram:CityName>
                      <ram:CountryID>FR</ram:CountryID>
                    </ram:PostalTradeAddress>
                  </ram:ShipToTradeParty>
                </ram:ApplicableHeaderTradeDelivery>
                <ram:ApplicableHeaderTradeSettlement>
                  <ram:PaymentReference>INV/2017/01/0001</ram:PaymentReference>
                  <ram:InvoiceCurrencyCode>EUR</ram:InvoiceCurrencyCode>
                  <ram:SpecifiedTradeSettlementPaymentMeans>
                    <ram:TypeCode>30</ram:TypeCode>
                    <ram:PayeePartyCreditorFinancialAccount>
                      <ram:ProprietaryID>FR15001559627230</ram:ProprietaryID>
                    </ram:PayeePartyCreditorFinancialAccount>
                  </ram:SpecifiedTradeSettlementPaymentMeans>
                  <ram:ApplicableTradeTax>
                    <ram:CalculatedAmount>220.00</ram:CalculatedAmount>
                    <ram:TypeCode>VAT</ram:TypeCode>
                    <ram:BasisAmount>1100.00</ram:BasisAmount>
                    <ram:CategoryCode>S</ram:CategoryCode>
                    <ram:DueDateTypeCode>5</ram:DueDateTypeCode>
                    <ram:RateApplicablePercent>20.0</ram:RateApplicablePercent>
                  </ram:ApplicableTradeTax>
                  <ram:SpecifiedTradePaymentTerms>
                    <ram:DueDateDateTime>
                      <udt:DateTimeString format="102">20171113</udt:DateTimeString>
                    </ram:DueDateDateTime>
                  </ram:SpecifiedTradePaymentTerms>
                  <ram:SpecifiedTradeSettlementHeaderMonetarySummation>
                    <ram:LineTotalAmount>1100.00</ram:LineTotalAmount>
                    <ram:TaxBasisTotalAmount>1100.00</ram:TaxBasisTotalAmount>
                    <ram:TaxTotalAmount currencyID="EUR">220.00</ram:TaxTotalAmount>
                    <ram:GrandTotalAmount>1320.00</ram:GrandTotalAmount>
                    <ram:TotalPrepaidAmount>0.00</ram:TotalPrepaidAmount>
                    <ram:DuePayableAmount>1320.00</ram:DuePayableAmount>
                  </ram:SpecifiedTradeSettlementHeaderMonetarySummation>
                </ram:ApplicableHeaderTradeSettlement>
              </rsm:SupplyChainTradeTransaction>
            </rsm:CrossIndustryInvoice>
        '''

    ####################################################
    # Test export
    ####################################################

    def test_facturx(self):
        ''' Test the generated Facturx Edi attachment without any modification of the invoice. '''
        self.assert_generated_file_equal(self.invoice, self.expected_invoice_facturx_values)

    """@freeze_time('2017-02-01')
    def test_facturx_group_of_taxes(self):
        ''' Same as above with a group of taxes. '''
        self.invoice.write({
            'invoice_line_ids': [(1, self.invoice.invoice_line_ids.id, {'tax_ids': [(6, 0, self.tax_group.ids)]})],
        })

        applied_xpath = '''
            <xpath expr="//NetPriceProductTradePrice/ChargeAmount" position="replace">
                <ChargeAmount currencyID="Gol">200.000</ChargeAmount>
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
                            <DateTimeString format="102">20170101</DateTimeString>
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
        '''

        self.assert_generated_file_equal(self.invoice, self.expected_invoice_facturx_values, applied_xpath)"""

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
        self.update_invoice_from_file('account_edi_facturx', 'test_file', 'test_out_invoice_to_france.pdf', invoice)

        self.assertEqual(len(self.env['account.move'].search([])), invoice_count)
        self.assertEqual(invoice.amount_total, 5217.60)

        self.create_invoice_from_file('account_edi_facturx', 'test_file', 'test_out_invoice_to_france.pdf')

        self.assertEqual(invoice.amount_total, 5217.60)
        self.assertEqual(len(self.env['account.move'].search([])), invoice_count + 1)

    def test_invoice_edi_xml(self):
        invoice = self._create_empty_vendor_bill()
        invoice_count = len(self.env['account.move'].search([]))
        self.update_invoice_from_file('account_edi_facturx', 'test_file', 'test_out_invoice_to_france.xml', invoice)

        self.assertEqual(len(self.env['account.move'].search([])), invoice_count)
        self.assertEqual(invoice.amount_total, 5217.60)

        self.create_invoice_from_file('account_edi_facturx', 'test_file', 'test_out_invoice_to_france.xml')

        self.assertEqual(invoice.amount_total, 5217.60)
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
        self.update_invoice_from_file('account_edi_facturx', 'test_file', 'test_out_invoice_to_france.xml', invoice)

        tax_ids = invoice.line_ids.tax_ids
        self.assertEqual(len(tax_ids), 1)
        self.assertEqual(tax_ids[0].name, "MyCompany Tax")
