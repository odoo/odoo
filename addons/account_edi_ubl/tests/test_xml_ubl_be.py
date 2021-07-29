# -*- coding: utf-8 -*-
from odoo.addons.account_edi_ubl.tests.common import TestUBLCommon
from odoo import Command
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestUBLBE(TestUBLCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.partner_1 = cls.env['res.partner'].create({
            'name': "partner_1",
            'street': "Chaussée de Namur 40",
            'zip': "1367",
            'city': "Ramillies",
            'vat': 'BE0202239951',
            'country_id': cls.env.ref('base.be').id,
            'bank_ids': [Command.create({'acc_number': 'BE15001559627230'})],
        })

        cls.partner_2 = cls.env['res.partner'].create({
            'name': "partner_2",
            'street': "Rue des Bourlottes 9",
            'zip': "1367",
            'city': "Ramillies",
            'vat': 'BE0477472701',
            'country_id': cls.env.ref('base.be').id,
            'bank_ids': [Command.create({'acc_number': 'BE90735788866632'})],
        })

        cls.tax_21 = cls.env['account.tax'].create({
            'name': 'tax_21',
            'amount_type': 'percent',
            'amount': 21,
            'type_tax_use': 'sale',
            'country_id': cls.env.ref('base.be').id,
        })

        cls.tax_12 = cls.env['account.tax'].create({
            'name': 'tax_12',
            'amount_type': 'percent',
            'amount': 12,
            'type_tax_use': 'sale',
            'country_id': cls.env.ref('base.be').id,
        })

        # TODO: decide how to categorise/manage more complex taxes: withholding/axes/recupel
        # cls.tax_10_withholding = cls.env['account.tax'].create({
        #     'name': 'tax_10_withholding',
        #     'amount_type': 'percent',
        #     'amount': -10,
        #     'type_tax_use': 'sale',
        #     'country_id': cls.env.ref('base.be').id,
        # })

    def test_out_invoice_bis3_be(self):
        invoice, xml_etree, xml_filename = self._export_invoice_bis3(
            self.partner_1,
            self.partner_2,
            xpaths='''
                <xpath expr="./PaymentMeans/PaymentID" position="after">
                    <PayeeFinancialAccount>
                        <ID>BE15001559627230</ID>
                    </PayeeFinancialAccount>
                </xpath>
                <xpath expr="./AccountingSupplierParty/Party/EndpointID" position="replace">
                    <EndpointID schemeID="9925">BE0202239951</EndpointID>
                </xpath>
                <xpath expr="./AccountingCustomerParty/Party/EndpointID" position="replace">
                    <EndpointID schemeID="9925">BE0477472701</EndpointID>
                </xpath>
                <xpath expr="./PaymentTerms" position="after">
                    <TaxTotal>
                        <TaxAmount currencyID="USD">1979.10</TaxAmount>
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
                            <TaxAmount currencyID="USD">108.00</TaxAmount>
                            <TaxCategory>
                                <ID>S</ID>
                                <Percent>12.0</Percent>
                                <TaxScheme>
                                    <ID>VAT</ID>
                                </TaxScheme>
                            </TaxCategory>
                        </TaxSubtotal>
                    </TaxTotal>
                    <LegalMonetaryTotal>
                        <LineExtensionAmount currencyID="USD">9810.00</LineExtensionAmount>
                        <TaxExclusiveAmount currencyID="USD">9810.00</TaxExclusiveAmount>
                        <TaxInclusiveAmount currencyID="USD">11789.10</TaxInclusiveAmount>
                        <PrepaidAmount currencyID="USD">0.00</PrepaidAmount>
                        <PayableAmount currencyID="USD">11789.10</PayableAmount>
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
                                <Percent>12.0</Percent>
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
                                <Percent>12.0</Percent>
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
                    # 'tax_ids': [Command.set((self.tax_12 + self.tax_10_withholding).ids)],
                    'tax_ids': [Command.set(self.tax_12.ids)],
                },
                {
                    'quantity': -1.0,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(self.tax_12.ids)],
                },
            ],
        )

        self._import_invoice_bis3(invoice, xml_etree, xml_filename)

    def test_out_refund_bis3_be(self):
        invoice, xml_etree, xml_filename = self._export_invoice_bis3(
            self.partner_1,
            self.partner_2,
            xpaths='''
                <xpath expr="./AccountingSupplierParty/Party/EndpointID" position="replace">
                    <EndpointID schemeID="9925">BE0202239951</EndpointID>
                </xpath>
                <xpath expr="./AccountingCustomerParty/Party/EndpointID" position="replace">
                    <EndpointID schemeID="9925">BE0477472701</EndpointID>
                </xpath>
                <xpath expr="./PaymentMeans/PaymentID" position="after">
                    <PayeeFinancialAccount>
                        <ID>BE90735788866632</ID>
                    </PayeeFinancialAccount>
                </xpath>
                <xpath expr="./PaymentTerms" position="after">
                    <TaxTotal>
                        <TaxAmount currencyID="USD">1979.10</TaxAmount>
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
                            <TaxAmount currencyID="USD">108.00</TaxAmount>
                            <TaxCategory>
                                <ID>S</ID>
                                <Percent>12.0</Percent>
                                <TaxScheme>
                                    <ID>VAT</ID>
                                </TaxScheme>
                            </TaxCategory>
                        </TaxSubtotal>
                    </TaxTotal>
                    <LegalMonetaryTotal>
                        <LineExtensionAmount currencyID="USD">9810.00</LineExtensionAmount>
                        <TaxExclusiveAmount currencyID="USD">9810.00</TaxExclusiveAmount>
                        <TaxInclusiveAmount currencyID="USD">11789.10</TaxInclusiveAmount>
                        <PrepaidAmount currencyID="USD">0.00</PrepaidAmount>
                        <PayableAmount currencyID="USD">11789.10</PayableAmount>
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
                                <Percent>12.0</Percent>
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
                                <Percent>12.0</Percent>
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
                    'tax_ids': [Command.set(self.tax_12.ids)],
                },
                {
                    'quantity': -1.0,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(self.tax_12.ids)],
                },
            ],
        )

        self._import_invoice_bis3(invoice, xml_etree, xml_filename)
