# -*- coding: utf-8 -*-
from odoo.addons.account_edi.tests.common import AccountEdiTestCommon
from odoo.tests import tagged
from odoo import Command


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nBeEdi(AccountEdiTestCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_be.l10nbe_chart_template', edi_format_ref='l10n_be_edi.edi_efff_1'):
        super().setUpClass(chart_template_ref=chart_template_ref, edi_format_ref=edi_format_ref)

        if cls.env['ir.module.module'].search(
            [('name', '=', 'account_edi_ubl_cii'), ('state', '=', 'installed')],
            limit=1,
        ):
            cls.skipTest(cls, "L10n_be_edi Tests skipped because account_edi_ubl_cii is installed.")

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
            'invoice_repartition_line_ids': [
                (0, 0, {'factor_percent': 100.0, 'repartition_type': 'base'}),
                (0, 0, {'factor_percent': 40.0, 'repartition_type': 'tax'}),
                (0, 0, {'factor_percent': 60.0, 'repartition_type': 'tax'}),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {'factor_percent': 100.0, 'repartition_type': 'base'}),
                (0, 0, {'factor_percent': 40.0, 'repartition_type': 'tax'}),
                (0, 0, {'factor_percent': 60.0, 'repartition_type': 'tax'}),
            ],
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

        cls.partner_a.vat = 'BE0477472701'

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

        cls.expected_invoice_efff_values = '''
            <Invoice>
                <UBLVersionID>2.0</UBLVersionID>
                <ID>INV/2017/00001</ID>
                <IssueDate>2017-01-01</IssueDate>
                <InvoiceTypeCode>380</InvoiceTypeCode>
                <DocumentCurrencyCode>Gol</DocumentCurrencyCode>
                <AccountingSupplierParty>
                    <Party>
                        <PartyName>
                            <Name>company_1_data</Name>
                        </PartyName>
                        <Language>
                            <LocaleCode>en_US</LocaleCode>
                        </Language>
                        <PostalAddress/>
                        <Contact>
                            <Name>company_1_data</Name>
                        </Contact>
                    </Party>
                </AccountingSupplierParty>
                <AccountingCustomerParty>
                    <Party>
                        <PartyName>
                            <Name>partner_b</Name>
                        </PartyName>
                        <Language>
                            <LocaleCode>en_US</LocaleCode>
                        </Language>
                        <PostalAddress/>
                        <Contact>
                            <Name>partner_b</Name>
                        </Contact>
                    </Party>
                </AccountingCustomerParty>
                <PaymentMeans>
                    <PaymentMeansCode listID="UN/ECE 4461">31</PaymentMeansCode>
                    <PaymentDueDate>2017-01-01</PaymentDueDate>
                    <InstructionID>INV/2017/00001</InstructionID>
                </PaymentMeans>
                <TaxTotal>
                    <TaxAmount currencyID="Gol">220.000</TaxAmount>
                </TaxTotal>
                <LegalMonetaryTotal>
                    <LineExtensionAmount currencyID="Gol">1100.000</LineExtensionAmount>
                    <TaxExclusiveAmount currencyID="Gol">1100.000</TaxExclusiveAmount>
                    <TaxInclusiveAmount currencyID="Gol">1320.000</TaxInclusiveAmount>
                    <PrepaidAmount currencyID="Gol">0.000</PrepaidAmount>
                    <PayableAmount currencyID="Gol">1320.000</PayableAmount>
                </LegalMonetaryTotal>
                <InvoiceLine>
                    <ID>___ignore___</ID>
                    <Note>Discount (20.0 %)</Note>
                    <InvoicedQuantity>5.0</InvoicedQuantity>
                    <LineExtensionAmount currencyID="Gol">1100.000</LineExtensionAmount>
                    <TaxTotal>
                        <TaxAmount currencyID="Gol">220.000</TaxAmount>
                    </TaxTotal>
                    <Item>
                        <Description>product_a</Description>
                        <Name>product_a</Name>
                    </Item>
                    <Price>
                        <PriceAmount currencyID="Gol">275.000</PriceAmount>
                    </Price>
                </InvoiceLine>
            </Invoice>
        '''

    ####################################################
    # Test export
    ####################################################

    def test_efff_simple_case(self):
        ''' Test the generated Facturx Edi attachment without any modification of the invoice. '''
        self.assert_generated_file_equal(self.invoice, self.expected_invoice_efff_values)

    def test_efff_group_of_taxes(self):
        self.invoice.write({
            'invoice_line_ids': [(1, self.invoice.invoice_line_ids.id, {'tax_ids': [Command.set(self.tax_group.ids)]})],
        })

        applied_xpath = '''
            <xpath expr="//TaxTotal/TaxAmount" position="replace">
                <TaxAmount currencyID="Gol">320.000</TaxAmount>
            </xpath>
            <xpath expr="//LegalMonetaryTotal/LineExtensionAmount" position="replace">
                <LineExtensionAmount currencyID="Gol">1000.000</LineExtensionAmount>
            </xpath>
            <xpath expr="//LegalMonetaryTotal/TaxExclusiveAmount" position="replace">
                <TaxExclusiveAmount currencyID="Gol">1000.000</TaxExclusiveAmount>
            </xpath>
            <xpath expr="//InvoiceLine/LineExtensionAmount" position="replace">
                <LineExtensionAmount currencyID="Gol">1000.000</LineExtensionAmount>
            </xpath>
            <xpath expr="//InvoiceLine/TaxTotal" position="replace">
                <TaxTotal>
                    <TaxAmount currencyID="Gol">100.000</TaxAmount>
                </TaxTotal>
                <TaxTotal>
                    <TaxAmount currencyID="Gol">220.000</TaxAmount>
                </TaxTotal>
            </xpath>
        '''

        self.assert_generated_file_equal(self.invoice, self.expected_invoice_efff_values, applied_xpath)

    ####################################################
    # Test import
    ####################################################

    def test_invoice_edi_xml_update(self):
        invoice = self._create_empty_vendor_bill()
        invoice_count = len(self.env['account.move'].search([]))
        self.update_invoice_from_file('l10n_be_edi', 'test_xml_file', 'efff_test.xml', invoice)

        self.assertEqual(len(self.env['account.move'].search([])), invoice_count)
        self.assertEqual(invoice.amount_total, 666.50)
        self.assertEqual(invoice.amount_tax, 115.67)
        self.assertEqual(invoice.partner_id, self.partner_a)

    def test_invoice_edi_xml_create(self):
        invoice_count = len(self.env['account.move'].search([]))
        invoice = self.create_invoice_from_file('l10n_be_edi', 'test_xml_file', 'efff_test.xml')
        self.assertEqual(len(self.env['account.move'].search([])), invoice_count + 1)
        self.assertEqual(invoice.amount_total, 666.50)
        self.assertEqual(invoice.amount_tax, 115.67)
        self.assertEqual(invoice.partner_id, self.partner_a)
