# -*- coding: utf-8 -*-
from odoo import Command
from odoo.addons.account_edi_ubl.tests.common import TestUBLCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUBLNO(TestUBLCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_no.no_chart_template'):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.bank = cls.env['res.bank'].create({
            'name': "DNB BANK ASA",
            'bic': 'DNBANOKKXXX',
        })

        cls.partner_1 = cls.env['res.partner'].create({
            'name': "partner_1",
            'street': "Bjertnes",
            'zip': "3536",
            'city': "Noresund",
            'vat': 'NO988077917',
            'l10n_no_bronnoysund_number': '965920358',
            'country_id': cls.env.ref('base.no').id,
            'bank_ids': [Command.create({
                'acc_number': 'NO8562617237763',
                'bank_id': cls.bank.id,
            })],
        })

        cls.partner_2 = cls.env['res.partner'].create({
            'name': "partner_2",
            'street': "Busundveien 68",
            'zip': "3519",
            'city': "Hønefoss",
            'vat': 'NO123456785',
            'l10n_no_bronnoysund_number': '971285850',
            'country_id': cls.env.ref('base.no').id,
            'bank_ids': [Command.create({
                'acc_number': 'NO5085673457453',
                'bank_id': cls.bank.id,
            })],
        })

        cls.tax_25 = cls._get_tax_by_xml_id('l10n_no.tax3')
        cls.tax_15 = cls._get_tax_by_xml_id('l10n_no.tax15')

    def test_out_invoice_bis3_no(self):
        invoice, xml_etree, xml_filename = self._export_invoice_bis3(
            self.partner_1,
            self.partner_2,
            xpaths=f'''
                <xpath expr="./AccountingSupplierParty/Party/EndpointID" position="replace">
                    <EndpointID schemeID="0192">{self.partner_1.l10n_no_bronnoysund_number}</EndpointID>
                </xpath>
                <xpath expr="./AccountingSupplierParty/Party/PostalAddress/Country/IdentificationCode" position="replace">
                    <IdentificationCode listID="ISO3166-1:Alpha2">{self.partner_1.country_id.code}</IdentificationCode>
                </xpath>
                <xpath expr="./AccountingSupplierParty/Party/PartyTaxScheme/CompanyID" position="replace">
                    <CompanyID>NO965920358MVA</CompanyID>
                </xpath>
                <xpath expr="./AccountingCustomerParty/Party/EndpointID" position="replace">
                    <EndpointID schemeID="0192">{self.partner_2.l10n_no_bronnoysund_number}</EndpointID>
                </xpath>
                <xpath expr="./AccountingCustomerParty/Party/PostalAddress/Country/IdentificationCode" position="replace">
                    <IdentificationCode listID="ISO3166-1:Alpha2">{self.partner_2.country_id.code}</IdentificationCode>
                </xpath>
                <xpath expr="./AccountingCustomerParty/Party/PartyTaxScheme/CompanyID" position="replace">
                    <CompanyID>NO971285850MVA</CompanyID>
                </xpath>
                <xpath expr="./PaymentMeans/PaymentID" position="after">
                    <PayeeFinancialAccount>
                        <ID>NO8562617237763</ID>
                        <FinancialInstitutionBranch>
                            <ID schemeID="BIC">DNBANOKKXXX</ID>
                            <FinancialInstitution>
                                <ID schemeID="BIC">DNBANOKKXXX</ID>
                                <Name>DNB BANK ASA</Name>
                            </FinancialInstitution>
                        </FinancialInstitutionBranch>
                    </PayeeFinancialAccount>
                </xpath>
                <xpath expr="./PaymentTerms" position="after">
                    <TaxTotal>
                        <TaxAmount currencyID="USD">2362.50</TaxAmount>
                        <TaxSubtotal>
                            <TaxableAmount currencyID="USD">8910.00</TaxableAmount>
                            <TaxAmount currencyID="USD">2227.50</TaxAmount>
                            <TaxCategory>
                                <ID>S</ID>
                                <Percent>25.0</Percent>
                                <TaxScheme>
                                    <ID>VAT</ID>
                                </TaxScheme>
                            </TaxCategory>
                        </TaxSubtotal>
                        <TaxSubtotal>
                            <TaxableAmount currencyID="USD">900.00</TaxableAmount>
                            <TaxAmount currencyID="USD">135.00</TaxAmount>
                            <TaxCategory>
                                <ID>S</ID>
                                <Percent>15.0</Percent>
                                <TaxScheme>
                                    <ID>VAT</ID>
                                </TaxScheme>
                            </TaxCategory>
                        </TaxSubtotal>
                    </TaxTotal>
                    <LegalMonetaryTotal>
                        <LineExtensionAmount currencyID="USD">9810.00</LineExtensionAmount>
                        <TaxExclusiveAmount currencyID="USD">9810.00</TaxExclusiveAmount>
                        <TaxInclusiveAmount currencyID="USD">12172.50</TaxInclusiveAmount>
                        <PrepaidAmount currencyID="USD">0.00</PrepaidAmount>
                        <PayableAmount currencyID="USD">12172.50</PayableAmount>
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
                                <Percent>25.0</Percent>
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
                                <Percent>15.0</Percent>
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
                                <Percent>15.0</Percent>
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
                    'tax_ids': [Command.set(self.tax_25.ids)],
                },
                {
                    'quantity': 10.0,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(self.tax_15.ids)],
                },
                {
                    'quantity': -1.0,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(self.tax_15.ids)],
                },
            ],
        )

        self._import_invoice_bis3(invoice, xml_etree, xml_filename)

    def test_out_refund_bis3_no(self):
        invoice, xml_etree, xml_filename = self._export_invoice_bis3(
            self.partner_1,
            self.partner_2,
            xpaths=f'''
                <xpath expr="./AccountingSupplierParty/Party/EndpointID" position="replace">
                    <EndpointID schemeID="0192">{self.partner_1.l10n_no_bronnoysund_number}</EndpointID>
                </xpath>
                <xpath expr="./AccountingSupplierParty/Party/PostalAddress/Country/IdentificationCode" position="replace">
                    <IdentificationCode listID="ISO3166-1:Alpha2">{self.partner_1.country_id.code}</IdentificationCode>
                </xpath>
                <xpath expr="./AccountingSupplierParty/Party/PartyTaxScheme/CompanyID" position="replace">
                    <CompanyID>NO965920358MVA</CompanyID>
                </xpath>
                <xpath expr="./AccountingCustomerParty/Party/EndpointID" position="replace">
                    <EndpointID schemeID="0192">{self.partner_2.l10n_no_bronnoysund_number}</EndpointID>
                </xpath>
                <xpath expr="./AccountingCustomerParty/Party/PostalAddress/Country/IdentificationCode" position="replace">
                    <IdentificationCode listID="ISO3166-1:Alpha2">{self.partner_2.country_id.code}</IdentificationCode>
                </xpath>
                <xpath expr="./AccountingCustomerParty/Party/PartyTaxScheme/CompanyID" position="replace">
                    <CompanyID>NO971285850MVA</CompanyID>
                </xpath>
                <xpath expr="./PaymentMeans/PaymentID" position="after">
                    <PayeeFinancialAccount>
                        <ID>NO5085673457453</ID>
                        <FinancialInstitutionBranch>
                            <ID schemeID="BIC">DNBANOKKXXX</ID>
                            <FinancialInstitution>
                                <ID schemeID="BIC">DNBANOKKXXX</ID>
                                <Name>DNB BANK ASA</Name>
                            </FinancialInstitution>
                        </FinancialInstitutionBranch>
                    </PayeeFinancialAccount>
                </xpath>
                <xpath expr="./PaymentTerms" position="after">
                    <TaxTotal>
                        <TaxAmount currencyID="USD">2362.50</TaxAmount>
                        <TaxSubtotal>
                            <TaxableAmount currencyID="USD">8910.00</TaxableAmount>
                            <TaxAmount currencyID="USD">2227.50</TaxAmount>
                            <TaxCategory>
                                <ID>S</ID>
                                <Percent>25.0</Percent>
                                <TaxScheme>
                                    <ID>VAT</ID>
                                </TaxScheme>
                            </TaxCategory>
                        </TaxSubtotal>
                        <TaxSubtotal>
                            <TaxableAmount currencyID="USD">900.00</TaxableAmount>
                            <TaxAmount currencyID="USD">135.00</TaxAmount>
                            <TaxCategory>
                                <ID>S</ID>
                                <Percent>15.0</Percent>
                                <TaxScheme>
                                    <ID>VAT</ID>
                                </TaxScheme>
                            </TaxCategory>
                        </TaxSubtotal>
                    </TaxTotal>
                    <LegalMonetaryTotal>
                        <LineExtensionAmount currencyID="USD">9810.00</LineExtensionAmount>
                        <TaxExclusiveAmount currencyID="USD">9810.00</TaxExclusiveAmount>
                        <TaxInclusiveAmount currencyID="USD">12172.50</TaxInclusiveAmount>
                        <PrepaidAmount currencyID="USD">0.00</PrepaidAmount>
                        <PayableAmount currencyID="USD">12172.50</PayableAmount>
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
                                <Percent>25.0</Percent>
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
                                <Percent>15.0</Percent>
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
                                <Percent>15.0</Percent>
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
                    'tax_ids': [Command.set(self.tax_25.ids)],
                },
                {
                    'quantity': 10.0,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(self.tax_15.ids)],
                },
                {
                    'quantity': -1.0,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(self.tax_15.ids)],
                },
            ],
        )

        self._import_invoice_bis3(invoice, xml_etree, xml_filename)
