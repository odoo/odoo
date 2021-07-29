# -*- coding: utf-8 -*-
from odoo import Command
from odoo.addons.account_edi_ubl.tests.common import TestUBLCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUBLNL(TestUBLCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_nl.l10nnl_chart_template'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.partner_1 = cls.env['res.partner'].create({
            'name': "partner_1",
            'street': "Markt 1",
            'zip': "2801",
            'city': "Gouda",
            'vat': 'NL000099998B57',
            'l10n_nl_kvk': '77777677',
            'country_id': cls.env.ref('base.nl').id,
            'bank_ids': [Command.create({'acc_number': 'NL48ABNA9971485915'})],
        })

        cls.partner_2 = cls.env['res.partner'].create({
            'name': "partner_2",
            'street': "Lijnbaansgracht 256",
            'zip': "1017",
            'city': "Amsterdam",
            'vat': 'NL123456782B90',
            'l10n_nl_kvk': '82777822',
            'country_id': cls.env.ref('base.nl').id,
            'bank_ids': [Command.create({'acc_number': 'NL54ABNA9397935380'})],
        })

        cls.tax_21 = cls._get_tax_by_xml_id('l10n_nl.btw_21')
        cls.tax_6 = cls._get_tax_by_xml_id('l10n_nl.btw_6')

    def test_out_invoice_bis3_nl(self):
        invoice, xml_etree, xml_filename = self._export_invoice_bis3(
            self.partner_1,
            self.partner_2,
            xpaths=f'''
                <xpath expr="./CustomizationID" position="replace">
                    <CustomizationID>urn:cen.eu:en16931:2017#compliant#urn:fdc:nen.nl:nlcius:v1.0</CustomizationID>
                </xpath>
                <xpath expr="./PaymentMeans/PaymentID" position="after">
                    <PayeeFinancialAccount>
                        <ID>NL48ABNA9971485915</ID>
                    </PayeeFinancialAccount>
                </xpath>
                <xpath expr="./AccountingSupplierParty/Party/EndpointID" position="replace">
                    <EndpointID schemeID="0106">{self.partner_1.l10n_nl_kvk}</EndpointID>
                </xpath>
                <xpath expr="./AccountingSupplierParty/Party/PartyLegalEntity/CompanyID" position="replace">
                    <CompanyID schemeID="0106">{self.partner_1.vat}</CompanyID>
                </xpath>
                <xpath expr="./AccountingCustomerParty/Party/EndpointID" position="replace">
                    <EndpointID schemeID="0106">{self.partner_2.l10n_nl_kvk}</EndpointID>
                </xpath>
                <xpath expr="./AccountingCustomerParty/Party/PartyLegalEntity/CompanyID" position="replace">
                    <CompanyID schemeID="0106">{self.partner_2.vat}</CompanyID>
                </xpath>
                <xpath expr="./PaymentTerms" position="after">
                    <TaxTotal>
                        <TaxAmount currencyID="USD">1925.10</TaxAmount>
                        <TaxSubtotal>
                            <TaxableAmount currencyID="USD">8910.00</TaxableAmount>
                            <TaxAmount currencyID="USD">1871.10</TaxAmount>
                            <TaxCategory>
                                <ID>S</ID>
                                <Percent>21.0</Percent>
                                <TaxScheme>
                                    <ID>VAT</ID>
                                </TaxScheme>
                            </TaxCategory>
                        </TaxSubtotal>
                        <TaxSubtotal>
                            <TaxableAmount currencyID="USD">900.00</TaxableAmount>
                            <TaxAmount currencyID="USD">54.00</TaxAmount>
                            <TaxCategory>
                                <ID>S</ID>
                                <Percent>6.0</Percent>
                                <TaxScheme>
                                    <ID>VAT</ID>
                                </TaxScheme>
                            </TaxCategory>
                        </TaxSubtotal>
                    </TaxTotal>
                    <LegalMonetaryTotal>
                        <LineExtensionAmount currencyID="USD">9810.00</LineExtensionAmount>
                        <TaxExclusiveAmount currencyID="USD">9810.00</TaxExclusiveAmount>
                        <TaxInclusiveAmount currencyID="USD">11735.10</TaxInclusiveAmount>
                        <PrepaidAmount currencyID="USD">0.00</PrepaidAmount>
                        <PayableAmount currencyID="USD">11735.10</PayableAmount>
                    </LegalMonetaryTotal>
                    <InvoiceLine>
                        <ID>___ignore___</ID>
                        <InvoicedQuantity unitCode="C62">10.0</InvoicedQuantity>
                        <LineExtensionAmount currencyID="USD">8910.00</LineExtensionAmount>
                        <AllowanceCharge>
                            <ChargeIndicator>false</ChargeIndicator>
                            <AllowanceChargeReasonCode>95</AllowanceChargeReasonCode>
                            <Amount currencyID="USD">990.0</Amount>
                        </AllowanceCharge>
                        <Item>
                            <Description>product_a</Description>
                            <Name>product_a</Name>
                            <ClassifiedTaxCategory>
                                <ID>S</ID>
                                <Percent>21.0</Percent>
                                <TaxScheme>
                                    <ID>VAT</ID>
                                </TaxScheme>
                            </ClassifiedTaxCategory>
                        </Item>
                        <Price>
                            <PriceAmount currencyID="USD">990.0</PriceAmount>
                            <BaseQuantity unitCode="C62">1</BaseQuantity>
                        </Price>
                    </InvoiceLine>
                    <InvoiceLine>
                        <ID>___ignore___</ID>
                        <InvoicedQuantity unitCode="C62">10.0</InvoicedQuantity>
                        <LineExtensionAmount currencyID="USD">1000.00</LineExtensionAmount>
                        <Item>
                            <Description>product_a</Description>
                            <Name>product_a</Name>
                            <ClassifiedTaxCategory>
                                <ID>S</ID>
                                <Percent>6.0</Percent>
                                <TaxScheme>
                                    <ID>VAT</ID>
                                </TaxScheme>
                            </ClassifiedTaxCategory>
                        </Item>
                        <Price>
                            <PriceAmount currencyID="USD">100.0</PriceAmount>
                            <BaseQuantity unitCode="C62">1</BaseQuantity>
                        </Price>
                    </InvoiceLine>
                    <InvoiceLine>
                        <ID>___ignore___</ID>
                        <InvoicedQuantity unitCode="C62">-1.0</InvoicedQuantity>
                        <LineExtensionAmount currencyID="USD">-100.00</LineExtensionAmount>
                        <Item>
                            <Description>product_a</Description>
                            <Name>product_a</Name>
                            <ClassifiedTaxCategory>
                                <ID>S</ID>
                                <Percent>6.0</Percent>
                                <TaxScheme>
                                    <ID>VAT</ID>
                                </TaxScheme>
                            </ClassifiedTaxCategory>
                        </Item>
                        <Price>
                            <PriceAmount currencyID="USD">100.0</PriceAmount>
                            <BaseQuantity unitCode="C62">1</BaseQuantity>
                        </Price>
                    </InvoiceLine>
                </xpath>
            ''',
            export_file='export_out_invoice_bis3.xml',
            move_type='out_invoice',
            invoice_line_ids=[
                {
                    'quantity': 10.0,
                    'price_unit': 990.0,
                    'discount': 10.0,
                    'tax_ids': [Command.set(self.tax_21.ids)],
                },
                {
                    'quantity': 10.0,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(self.tax_6.ids)],
                },
                {
                    'quantity': -1.0,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(self.tax_6.ids)],
                },
            ],
        )

        self._import_invoice_bis3(invoice, xml_etree, xml_filename)

    def test_out_refund_bis3_nl(self):
        invoice, xml_etree, xml_filename = self._export_invoice_bis3(
            self.partner_1,
            self.partner_2,
            xpaths=f'''
                <xpath expr="./CustomizationID" position="replace">
                    <CustomizationID>urn:cen.eu:en16931:2017#compliant#urn:fdc:nen.nl:nlcius:v1.0</CustomizationID>
                </xpath>
                <xpath expr="./PaymentMeans/PaymentID" position="after">
                    <PayeeFinancialAccount>
                        <ID>NL54ABNA9397935380</ID>
                    </PayeeFinancialAccount>
                </xpath>
                <xpath expr="./AccountingSupplierParty/Party/EndpointID" position="replace">
                    <EndpointID schemeID="0106">{self.partner_1.l10n_nl_kvk}</EndpointID>
                </xpath>
                <xpath expr="./AccountingSupplierParty/Party/PartyLegalEntity/CompanyID" position="replace">
                    <CompanyID schemeID="0106">{self.partner_1.vat}</CompanyID>
                </xpath>
                <xpath expr="./AccountingCustomerParty/Party/EndpointID" position="replace">
                    <EndpointID schemeID="0106">{self.partner_2.l10n_nl_kvk}</EndpointID>
                </xpath>
                <xpath expr="./AccountingCustomerParty/Party/PartyLegalEntity/CompanyID" position="replace">
                    <CompanyID schemeID="0106">{self.partner_2.vat}</CompanyID>
                </xpath>
                <xpath expr="./PaymentTerms" position="after">
                    <TaxTotal>
                        <TaxAmount currencyID="USD">1925.10</TaxAmount>
                        <TaxSubtotal>
                            <TaxableAmount currencyID="USD">8910.00</TaxableAmount>
                            <TaxAmount currencyID="USD">1871.10</TaxAmount>
                            <TaxCategory>
                                <ID>S</ID>
                                <Percent>21.0</Percent>
                                <TaxScheme>
                                    <ID>VAT</ID>
                                </TaxScheme>
                            </TaxCategory>
                        </TaxSubtotal>
                        <TaxSubtotal>
                            <TaxableAmount currencyID="USD">900.00</TaxableAmount>
                            <TaxAmount currencyID="USD">54.00</TaxAmount>
                            <TaxCategory>
                                <ID>S</ID>
                                <Percent>6.0</Percent>
                                <TaxScheme>
                                    <ID>VAT</ID>
                                </TaxScheme>
                            </TaxCategory>
                        </TaxSubtotal>
                    </TaxTotal>
                    <LegalMonetaryTotal>
                        <LineExtensionAmount currencyID="USD">9810.00</LineExtensionAmount>
                        <TaxExclusiveAmount currencyID="USD">9810.00</TaxExclusiveAmount>
                        <TaxInclusiveAmount currencyID="USD">11735.10</TaxInclusiveAmount>
                        <PrepaidAmount currencyID="USD">0.00</PrepaidAmount>
                        <PayableAmount currencyID="USD">11735.10</PayableAmount>
                    </LegalMonetaryTotal>
                    <CreditNoteLine>
                        <ID>___ignore___</ID>
                        <CreditedQuantity unitCode="C62">10.0</CreditedQuantity>
                        <LineExtensionAmount currencyID="USD">8910.00</LineExtensionAmount>
                        <AllowanceCharge>
                            <ChargeIndicator>false</ChargeIndicator>
                            <AllowanceChargeReasonCode>95</AllowanceChargeReasonCode>
                            <Amount currencyID="USD">990.0</Amount>
                        </AllowanceCharge>
                        <Item>
                            <Description>product_a</Description>
                            <Name>product_a</Name>
                            <ClassifiedTaxCategory>
                                <ID>S</ID>
                                <Percent>21.0</Percent>
                                <TaxScheme>
                                    <ID>VAT</ID>
                                </TaxScheme>
                            </ClassifiedTaxCategory>
                        </Item>
                        <Price>
                            <PriceAmount currencyID="USD">990.0</PriceAmount>
                            <BaseQuantity unitCode="C62">1</BaseQuantity>
                        </Price>
                    </CreditNoteLine>
                    <CreditNoteLine>
                        <ID>___ignore___</ID>
                        <CreditedQuantity unitCode="C62">10.0</CreditedQuantity>
                        <LineExtensionAmount currencyID="USD">1000.00</LineExtensionAmount>
                        <Item>
                            <Description>product_a</Description>
                            <Name>product_a</Name>
                            <ClassifiedTaxCategory>
                                <ID>S</ID>
                                <Percent>6.0</Percent>
                                <TaxScheme>
                                    <ID>VAT</ID>
                                </TaxScheme>
                            </ClassifiedTaxCategory>
                        </Item>
                        <Price>
                            <PriceAmount currencyID="USD">100.0</PriceAmount>
                            <BaseQuantity unitCode="C62">1</BaseQuantity>
                        </Price>
                    </CreditNoteLine>
                    <CreditNoteLine>
                        <ID>___ignore___</ID>
                        <CreditedQuantity unitCode="C62">-1.0</CreditedQuantity>
                        <LineExtensionAmount currencyID="USD">-100.00</LineExtensionAmount>
                        <Item>
                            <Description>product_a</Description>
                            <Name>product_a</Name>
                            <ClassifiedTaxCategory>
                                <ID>S</ID>
                                <Percent>6.0</Percent>
                                <TaxScheme>
                                    <ID>VAT</ID>
                                </TaxScheme>
                            </ClassifiedTaxCategory>
                        </Item>
                        <Price>
                            <PriceAmount currencyID="USD">100.0</PriceAmount>
                            <BaseQuantity unitCode="C62">1</BaseQuantity>
                        </Price>
                    </CreditNoteLine>
                </xpath>
            ''',
            export_file='export_out_refund_bis3.xml',
            move_type='out_refund',
            invoice_line_ids=[
                {
                    'quantity': 10.0,
                    'price_unit': 990.0,
                    'discount': 10.0,
                    'tax_ids': [Command.set(self.tax_21.ids)],
                },
                {
                    'quantity': 10.0,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(self.tax_6.ids)],
                },
                {
                    'quantity': -1.0,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(self.tax_6.ids)],
                },
            ],
        )

        self._import_invoice_bis3(invoice, xml_etree, xml_filename)
