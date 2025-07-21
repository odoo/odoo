# -*- coding: utf-8 -*-
from odoo.addons.l10n_account_edi_ubl_cii_tests.tests.common import TestUBLCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUBLAU(TestUBLCommon):

    @classmethod
    @TestUBLCommon.setup_country('au')
    def setUpClass(cls):
        super().setUpClass()

        cls.partner_1 = cls.env['res.partner'].create({
            'name': "partner_1",
            'street': "Spring St.",
            'zip': "3002",
            'city': "Melbourne",
            'vat': '83 914 571 673',
            'phone': '+31 180 6 225789',
            'email': 'info@outlook.au',
            'country_id': cls.env.ref('base.au').id,
            'bank_ids': [(0, 0, {'acc_number': '000099998B57'})],
            'ref': 'ref_partner_1',
            'invoice_edi_format': 'ubl_a_nz',
        })

        cls.partner_2 = cls.env['res.partner'].create({
            'name': "partner_2",
            'street': "Parliament Dr",
            'zip': "2600",
            'city': "Canberra",
            'vat': '53 930 548 027',
            'country_id': cls.env.ref('base.au').id,
            'bank_ids': [(0, 0, {'acc_number': '93999574162167'})],
            'ref': 'ref_partner_2',
            'invoice_edi_format': 'ubl_a_nz',
        })

        cls.tax_10 = cls.env['account.tax'].create({
            'name': 'tax_10',
            'amount_type': 'percent',
            'amount': 10,
            'type_tax_use': 'sale',
            'country_id': cls.env.ref('base.au').id,
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
                    'tax_ids': [(6, 0, self.tax_10.ids)],
                },
                {
                    'product_id': self.product_b.id,
                    'quantity': 10.0,
                    'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                    'price_unit': 100.0,
                    'tax_ids': [(6, 0, self.tax_10.ids)],
                },
                {
                    'product_id': self.product_b.id,
                    'quantity': -1.0,
                    'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                    'price_unit': 100.0,
                    'tax_ids': [(6, 0, self.tax_10.ids)],
                },
            ],
        )
        attachment = self._assert_invoice_attachment(
            invoice.ubl_cii_xml_id,
            xpaths=f'''
                <xpath expr="./*[local-name()='ID']" position="replace">
                    <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">___ignore___</cbc:ID>
                </xpath>
                <xpath expr=".//*[local-name()='InvoiceLine'][1]/*[local-name()='ID']" position="replace">
                    <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">___ignore___</cbc:ID>
                </xpath>
                <xpath expr=".//*[local-name()='InvoiceLine'][2]/*[local-name()='ID']" position="replace">
                    <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">___ignore___</cbc:ID>
                </xpath>
                <xpath expr=".//*[local-name()='InvoiceLine'][3]/*[local-name()='ID']" position="replace">
                    <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">___ignore___</cbc:ID>
                </xpath>
                <xpath expr=".//*[local-name()='PaymentMeans']/*[local-name()='PaymentID']" position="replace">
                    <cbc:PaymentID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">___ignore___</cbc:PaymentID>
                </xpath>
                <xpath expr=".//*[local-name()='AdditionalDocumentReference']/*[local-name()='Attachment']/*[local-name()='EmbeddedDocumentBinaryObject']" position="attributes">
                    <attribute name="mimeCode">application/pdf</attribute>
                    <attribute name="filename">{invoice.invoice_pdf_report_id.name}</attribute>
                </xpath>
            ''',
            expected_file_path='from_odoo/a_nz_out_invoice.xml',
        )
        self.assertEqual(attachment.name[-8:], "a_nz.xml")
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
                    'tax_ids': [(6, 0, self.tax_10.ids)],
                },
                {
                    'product_id': self.product_b.id,
                    'quantity': 10.0,
                    'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                    'price_unit': 100.0,
                    'tax_ids': [(6, 0, self.tax_10.ids)],
                },
                {
                    'product_id': self.product_b.id,
                    'quantity': -1.0,
                    'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                    'price_unit': 100.0,
                    'tax_ids': [(6, 0, self.tax_10.ids)],
                },
            ],
        )
        attachment = self._assert_invoice_attachment(
            refund.ubl_cii_xml_id,
            xpaths=f'''
                <xpath expr="./*[local-name()='ID']" position="replace">
                    <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">___ignore___</cbc:ID>
                </xpath>
                <xpath expr=".//*[local-name()='CreditNoteLine'][1]/*[local-name()='ID']" position="replace">
                    <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">___ignore___</cbc:ID>
                </xpath>
                <xpath expr=".//*[local-name()='CreditNoteLine'][2]/*[local-name()='ID']" position="replace">
                    <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">___ignore___</cbc:ID>
                </xpath>
                <xpath expr=".//*[local-name()='CreditNoteLine'][3]/*[local-name()='ID']" position="replace">
                    <cbc:ID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">___ignore___</cbc:ID>
                </xpath>
                <xpath expr=".//*[local-name()='PaymentMeans']/*[local-name()='PaymentID']" position="replace">
                    <cbc:PaymentID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">___ignore___</cbc:PaymentID>
                </xpath>
                <xpath expr=".//*[local-name()='AdditionalDocumentReference']/*[local-name()='Attachment']/*[local-name()='EmbeddedDocumentBinaryObject']" position="attributes">
                    <attribute name="mimeCode">application/pdf</attribute>
                    <attribute name="filename">{refund.invoice_pdf_report_id.name}</attribute>
                </xpath>
            ''',
            expected_file_path='from_odoo/a_nz_out_refund.xml',
        )
        self.assertEqual(attachment.name[-8:], "a_nz.xml")
        self._assert_imported_invoice_from_etree(refund, attachment)

    ####################################################
    # Test import
    ####################################################

    def test_import_invoice_xml(self):
        self._assert_imported_invoice_from_file(
            subfolder='tests/test_files/from_odoo',
            filename='a_nz_out_invoice.xml',
            invoice_vals={
                'currency_id': self.other_currency.id,
                'amount_total': 2950.2,
                'amount_tax': 268.2,
                'invoice_lines': [{'price_subtotal': x} for x in (1782, 1000, -100)]
            },
        )
