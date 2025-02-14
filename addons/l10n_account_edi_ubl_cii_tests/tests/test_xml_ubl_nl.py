# -*- coding: utf-8 -*-
from odoo.addons.l10n_account_edi_ubl_cii_tests.tests.common import TestUBLCommon
from odoo.tests import tagged
from odoo import Command

from lxml import etree


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUBLNL(TestUBLCommon):

    @classmethod
    @TestUBLCommon.setup_country('nl')
    def setUpClass(cls):
        super().setUpClass()

        cls.partner_1 = cls.env['res.partner'].create({
            'name': "partner_1",
            'street': "Kunststraat, 3",
            'zip': "1000",
            'city': "Amsterdam",
            'vat': 'NL000099998B57',
            'phone': '+31 180 6 225789',
            'email': 'info@outlook.nl',
            'country_id': cls.env.ref('base.nl').id,
            'bank_ids': [(0, 0, {'acc_number': 'NL000099998B57'})],
            'peppol_eas': '0106',
            'peppol_endpoint': '77777677',
            'ref': 'ref_partner_1',
            'invoice_edi_format': 'nlcius',
        })

        cls.partner_2 = cls.env['res.partner'].create({
            'name': "partner_2",
            'street': "Europaweg, 2",
            'zip': "1200",
            'city': "Rotterdam",
            'vat': 'NL41452B11',
            'country_id': cls.env.ref('base.nl').id,
            'bank_ids': [(0, 0, {'acc_number': 'NL93999574162167'})],
            'peppol_eas': '0106',
            'peppol_endpoint': '1234567',
            'ref': 'ref_partner_2',
            'invoice_edi_format': 'nlcius',
        })

        cls.tax_19 = cls.env['account.tax'].create({
            'name': 'tax_19',
            'amount_type': 'percent',
            'amount': 19,
            'type_tax_use': 'sale',
            'country_id': cls.env.ref('base.nl').id,
        })

        cls.tax_7 = cls.env['account.tax'].create({
            'name': 'tax_7',
            'amount_type': 'percent',
            'amount': 7,
            'type_tax_use': 'sale',
            'country_id': cls.env.ref('base.nl').id,
        })

        cls.tax_19_purchase = cls.env['account.tax'].create({
            'name': 'tax_19',
            'amount_type': 'percent',
            'amount': 19,
            'type_tax_use': 'purchase',
            'country_id': cls.env.ref('base.nl').id,
        })

        cls.tax_7_purchase = cls.env['account.tax'].create({
            'name': 'tax_7',
            'amount_type': 'percent',
            'amount': 7,
            'type_tax_use': 'purchase',
            'country_id': cls.env.ref('base.nl').id,
            'sequence': 2,
        })

        cls.tax_10_fixed = cls.env['account.tax'].create({
            'name': 'Test Tax',
            'amount_type': 'fixed',
            'include_base_amount': True,
            'country_id': cls.env.ref('base.nl').id,
            'amount': 10.0,
            'sequence': 1,
        })

    ####################################################
    # Test export - import
    ####################################################

    def test_export_import_invoice(self):
        invoice = self._generate_move(
            self.partner_1,
            self.partner_2,
            move_type='out_invoice',
            invoice_line_ids=[
                {
                    'product_id': self.product_a.id,
                    'quantity': 2.0,
                    'product_uom_id': self.env.ref('uom.product_uom_dozen').id,
                    'price_unit': 990.0,
                    'discount': 10.0,
                    'tax_ids': [(6, 0, self.tax_19.ids)],
                },
                {
                    'product_id': self.product_b.id,
                    'quantity': 10.0,
                    'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                    'price_unit': 100.0,
                    'tax_ids': [(6, 0, self.tax_7.ids)],
                },
                {
                    'product_id': self.product_b.id,
                    'quantity': -1.0,
                    'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                    'price_unit': 100.0,
                    'tax_ids': [(6, 0, self.tax_7.ids)],
                },
            ],
        )
        attachment = self._assert_invoice_attachment(
            invoice.ubl_cii_xml_id,
            xpaths=f'''
                <xpath expr="./*[local-name()='ID']" position="replace">
                    <ID>___ignore___</ID>
                </xpath>
                <xpath expr=".//*[local-name()='InvoiceLine'][1]/*[local-name()='ID']" position="replace">
                    <ID>___ignore___</ID>
                </xpath>
                <xpath expr=".//*[local-name()='InvoiceLine'][2]/*[local-name()='ID']" position="replace">
                    <ID>___ignore___</ID>
                </xpath>
                <xpath expr=".//*[local-name()='InvoiceLine'][3]/*[local-name()='ID']" position="replace">
                    <ID>___ignore___</ID>
                </xpath>
                <xpath expr=".//*[local-name()='PaymentMeans']/*[local-name()='PaymentID']" position="replace">
                    <PaymentID>___ignore___</PaymentID>
                </xpath>
                <xpath expr=".//*[local-name()='AdditionalDocumentReference']/*[local-name()='Attachment']/*[local-name()='EmbeddedDocumentBinaryObject']" position="attributes">
                    <attribute name="mimeCode">application/pdf</attribute>
                    <attribute name="filename">{invoice.invoice_pdf_report_id.name}</attribute>
                </xpath>
            ''',
            expected_file_path='from_odoo/nlcius_out_invoice.xml',
        )
        self.assertEqual(attachment.name[-10:], "nlcius.xml")
        self._assert_imported_invoice_from_etree(invoice, attachment)

    def test_export_import_refund(self):
        refund = self._generate_move(
            self.partner_1,
            self.partner_2,
            move_type='out_refund',
            invoice_line_ids=[
                {
                    'product_id': self.product_a.id,
                    'quantity': 2.0,
                    'product_uom_id': self.env.ref('uom.product_uom_dozen').id,
                    'price_unit': 990.0,
                    'discount': 10.0,
                    'tax_ids': [(6, 0, self.tax_19.ids)],
                },
                {
                    'product_id': self.product_b.id,
                    'quantity': 10.0,
                    'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                    'price_unit': 100.0,
                    'tax_ids': [(6, 0, self.tax_7.ids)],
                },
                {
                    'product_id': self.product_b.id,
                    'quantity': -1.0,
                    'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                    'price_unit': 100.0,
                    'tax_ids': [(6, 0, self.tax_7.ids)],
                },
            ],
        )
        attachment = self._assert_invoice_attachment(
            refund.ubl_cii_xml_id,
            xpaths=f'''
                <xpath expr="./*[local-name()='ID']" position="replace">
                    <ID>___ignore___</ID>
                </xpath>
                <xpath expr=".//*[local-name()='CreditNoteLine'][1]/*[local-name()='ID']" position="replace">
                    <ID>___ignore___</ID>
                </xpath>
                <xpath expr=".//*[local-name()='CreditNoteLine'][2]/*[local-name()='ID']" position="replace">
                    <ID>___ignore___</ID>
                </xpath>
                <xpath expr=".//*[local-name()='CreditNoteLine'][3]/*[local-name()='ID']" position="replace">
                    <ID>___ignore___</ID>
                </xpath>
                <xpath expr=".//*[local-name()='PaymentMeans']/*[local-name()='PaymentID']" position="replace">
                    <PaymentID>___ignore___</PaymentID>
                </xpath>
                <xpath expr=".//*[local-name()='AdditionalDocumentReference']/*[local-name()='Attachment']/*[local-name()='EmbeddedDocumentBinaryObject']" position="attributes">
                    <attribute name="mimeCode">application/pdf</attribute>
                    <attribute name="filename">{refund.invoice_pdf_report_id.name}</attribute>
                </xpath>
            ''',
            expected_file_path='from_odoo/nlcius_out_refund.xml',
        )
        self.assertEqual(attachment.name[-10:], "nlcius.xml")
        self._assert_imported_invoice_from_etree(refund, attachment)

    def test_export_fixed_tax(self):
        """
        Ensure that an invoice containing a product with a fixed tax posted to a journal with the peppol and nlcius edi
            tags generates edi documents with accurate LineExtensionAmount values
        """
        invoice = self._generate_move(
            self.partner_1, self.partner_2,
            move_type='out_invoice',
            invoice_line_ids=[{
                'name': 'product costing 50.0',
                'quantity': 1,
                'price_unit': 50.0,
                'tax_ids': [Command.set([self.tax_10_fixed.id, self.tax_7_purchase.id])]
            }]
        )
        amount = etree.fromstring(invoice.ubl_cii_xml_id.raw).find('.//{*}LegalMonetaryTotal/{*}LineExtensionAmount').text
        self.assertEqual(amount, '60.00')

    ####################################################
    # Test import
    ####################################################

    def test_import_invoice_xml(self):
        # test files https://github.com/peppolautoriteit-nl/validation ?
        self._assert_imported_invoice_from_file(
            subfolder='tests/test_files/from_odoo',
            filename='nlcius_out_invoice.xml',
            invoice_vals={
                'currency_id': self.other_currency.id,
                'amount_total': 3083.58,
                'amount_tax': 401.58,
                'invoice_lines': [{'price_subtotal': x} for x in (1782, 1000, -100)]
            },
        )
