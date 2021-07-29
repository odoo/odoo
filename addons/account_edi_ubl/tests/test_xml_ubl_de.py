# -*- coding: utf-8 -*-
from odoo.addons.account_edi_ubl.tests.common import TestUBLCommon
from odoo import Command
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestUBLDE(TestUBLCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.partner_1 = cls.env['res.partner'].create({
            'name': "partner_1",
            'street': "Legoland-Allee 3",
            'zip': "89312",
            'city': "Günzburg",
            'vat': 'DE257486969',
            'phone': '+49 180 6 225789',
            'email': 'info@legoland.de',
            'country_id': cls.env.ref('base.de').id,
            'bank_ids': [Command.create({'acc_number': 'DE48500105176424548921'})],
        })

        cls.partner_2 = cls.env['res.partner'].create({
            'name': "partner_2",
            'street': "Europa-Park-Straße 2",
            'zip': "77977",
            'city': "Rust",
            'vat': 'DE186775212',
            'country_id': cls.env.ref('base.de').id,
            'bank_ids': [Command.create({'acc_number': 'DE50500105175653254743'})],
        })

        cls.tax_19 = cls.env['account.tax'].create({
            'name': 'tax_19',
            'amount_type': 'percent',
            'amount': 19,
            'type_tax_use': 'sale',
            'country_id': cls.env.ref('base.de').id,
        })

        cls.tax_7 = cls.env['account.tax'].create({
            'name': 'tax_7',
            'amount_type': 'percent',
            'amount': 7,
            'type_tax_use': 'sale',
            'country_id': cls.env.ref('base.de').id,
        })

    def test_out_invoice_bis3_de(self):
        invoice, xml_etree, xml_filename = self._export_invoice_bis3(
            self.partner_1,
            self.partner_2,
            xpaths=f'''
                <xpath expr="./CustomizationID" position="replace">
                    <CustomizationID>urn:cen.eu:en16931:2017#compliant#urn:xoev-de:kosit:standard:xrechnung_2.1#conformant#urn:xoev-de:kosit:extension:xrechnung_2.1</CustomizationID>
                </xpath>
                <xpath expr="./DocumentCurrencyCode" position="after">
                    <BuyerReference>{self.partner_2.name}</BuyerReference>
                </xpath>
                <xpath expr="./AccountingSupplierParty/Party/EndpointID" position="replace">
                    <EndpointID schemeID="9930">DE257486969</EndpointID>
                </xpath>
                <xpath expr="./AccountingSupplierParty/Party/Contact/Name" position="after">
                    <Telephone>{self.partner_1.phone}</Telephone>
                    <ElectronicMail>{self.partner_1.email}</ElectronicMail>
                </xpath>
                <xpath expr="./AccountingCustomerParty/Party/EndpointID" position="replace">
                    <EndpointID schemeID="9930">DE186775212</EndpointID>
                </xpath>
                <xpath expr="./PaymentMeans/PaymentID" position="after">
                    <PayeeFinancialAccount>
                        <ID>DE48500105176424548921</ID>
                    </PayeeFinancialAccount>
                </xpath>
                <xpath expr="./PaymentTerms" position="after">
                    <TaxTotal>
                        <TaxAmount currencyID="USD">1755.90</TaxAmount>
                        <TaxSubtotal>
                            <TaxableAmount currencyID="USD">8910.00</TaxableAmount>
                            <TaxAmount currencyID="USD">1692.90</TaxAmount>
                            <TaxCategory>
                                <ID>S</ID>
                                <Percent>19.0</Percent>
                                <TaxScheme>
                                    <ID>VAT</ID>
                                </TaxScheme>
                            </TaxCategory>
                        </TaxSubtotal>
                        <TaxSubtotal>
                            <TaxableAmount currencyID="USD">900.00</TaxableAmount>
                            <TaxAmount currencyID="USD">63.00</TaxAmount>
                            <TaxCategory>
                                <ID>S</ID>
                                <Percent>7.0</Percent>
                                <TaxScheme>
                                    <ID>VAT</ID>
                                </TaxScheme>
                            </TaxCategory>
                        </TaxSubtotal>
                    </TaxTotal>
                    <LegalMonetaryTotal>
                        <LineExtensionAmount currencyID="USD">9810.00</LineExtensionAmount>
                        <TaxExclusiveAmount currencyID="USD">9810.00</TaxExclusiveAmount>
                        <TaxInclusiveAmount currencyID="USD">11565.90</TaxInclusiveAmount>
                        <PrepaidAmount currencyID="USD">0.00</PrepaidAmount>
                        <PayableAmount currencyID="USD">11565.90</PayableAmount>
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
                                <Percent>19.0</Percent>
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
                                <Percent>7.0</Percent>
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
                                <Percent>7.0</Percent>
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
                    'tax_ids': [Command.set(self.tax_19.ids)],
                },
                {
                    'quantity': 10.0,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(self.tax_7.ids)],
                },
                {
                    'quantity': -1.0,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(self.tax_7.ids)],
                },
            ],
        )

        self._import_invoice_bis3(invoice, xml_etree, xml_filename)

    def test_out_refund_bis3_de(self):
        invoice, xml_etree, xml_filename = self._export_invoice_bis3(
            self.partner_1,
            self.partner_2,
            xpaths=f'''
                <xpath expr="./CustomizationID" position="replace">
                    <CustomizationID>urn:cen.eu:en16931:2017#compliant#urn:xoev-de:kosit:standard:xrechnung_2.1#conformant#urn:xoev-de:kosit:extension:xrechnung_2.1</CustomizationID>
                </xpath>
                <xpath expr="./DocumentCurrencyCode" position="after">
                    <BuyerReference>{self.partner_2.name}</BuyerReference>
                </xpath>
                <xpath expr="./AccountingSupplierParty/Party/EndpointID" position="replace">
                    <EndpointID schemeID="9930">DE257486969</EndpointID>
                </xpath>
                <xpath expr="./AccountingSupplierParty/Party/Contact/Name" position="after">
                    <Telephone>{self.partner_1.phone}</Telephone>
                    <ElectronicMail>{self.partner_1.email}</ElectronicMail>
                </xpath>
                <xpath expr="./AccountingCustomerParty/Party/EndpointID" position="replace">
                    <EndpointID schemeID="9930">DE186775212</EndpointID>
                </xpath>
                <xpath expr="./PaymentMeans/PaymentID" position="after">
                    <PayeeFinancialAccount>
                        <ID>DE50500105175653254743</ID>
                    </PayeeFinancialAccount>
                </xpath>
                <xpath expr="./PaymentTerms" position="after">
                    <TaxTotal>
                        <TaxAmount currencyID="USD">1755.90</TaxAmount>
                        <TaxSubtotal>
                            <TaxableAmount currencyID="USD">8910.00</TaxableAmount>
                            <TaxAmount currencyID="USD">1692.90</TaxAmount>
                            <TaxCategory>
                                <ID>S</ID>
                                <Percent>19.0</Percent>
                                <TaxScheme>
                                    <ID>VAT</ID>
                                </TaxScheme>
                            </TaxCategory>
                        </TaxSubtotal>
                        <TaxSubtotal>
                            <TaxableAmount currencyID="USD">900.00</TaxableAmount>
                            <TaxAmount currencyID="USD">63.00</TaxAmount>
                            <TaxCategory>
                                <ID>S</ID>
                                <Percent>7.0</Percent>
                                <TaxScheme>
                                    <ID>VAT</ID>
                                </TaxScheme>
                            </TaxCategory>
                        </TaxSubtotal>
                    </TaxTotal>
                    <LegalMonetaryTotal>
                        <LineExtensionAmount currencyID="USD">9810.00</LineExtensionAmount>
                        <TaxExclusiveAmount currencyID="USD">9810.00</TaxExclusiveAmount>
                        <TaxInclusiveAmount currencyID="USD">11565.90</TaxInclusiveAmount>
                        <PrepaidAmount currencyID="USD">0.00</PrepaidAmount>
                        <PayableAmount currencyID="USD">11565.90</PayableAmount>
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
                                <Percent>19.0</Percent>
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
                                <Percent>7.0</Percent>
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
                                <Percent>7.0</Percent>
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
                    'tax_ids': [Command.set(self.tax_19.ids)],
                },
                {
                    'quantity': 10.0,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(self.tax_7.ids)],
                },
                {
                    'quantity': -1.0,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(self.tax_7.ids)],
                },
            ],
        )

        self._import_invoice_bis3(invoice, xml_etree, xml_filename)
