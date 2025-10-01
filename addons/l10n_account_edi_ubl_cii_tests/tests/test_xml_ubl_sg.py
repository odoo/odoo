from odoo import Command
from odoo.tests import tagged
from odoo.addons.l10n_account_edi_ubl_cii_tests.tests.common import TestUBLCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUBLSG(TestUBLCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].set_param('account_edi_ubl_cii.use_new_dict_to_xml_helpers', 'False')

        cls.partner_1 = cls.env['res.partner'].create({
            'name': "partner_1",
            'street': 'Tyersall Avenue',
            'zip': '248048',
            'city': 'Central Singapore',
            'vat': '197401143C',
            'phone': '+65 9123 4567',
            'email': 'info@outlook.sg',
            'country_id': cls.env.ref('base.sg').id,
            'bank_ids': [(0, 0, {'acc_number': '000099998B57'})],
            'ref': 'ref_partner_1',
            'invoice_edi_format': 'ubl_sg',
        })

        cls.partner_2 = cls.env['res.partner'].create({
            'name': "partner_2",
            'street': 'that other street, 3',
            'zip': '248050',
            'city': 'East Singapore',
            'vat': 'S16FC0121D',
            'phone': '+65 9123 4589',
            'country_id': cls.env.ref('base.sg').id,
            'bank_ids': [(0, 0, {'acc_number': '93999574162167'})],
            'ref': 'ref_partner_2',
            'invoice_edi_format': 'ubl_sg',
        })

    ####################################################
    # Test export - import
    ####################################################

    def test_export_import_invoice(self):
        tax_10 = self.percent_tax(10)
        tax_0 = self.percent_tax(0)
        invoice = self._generate_move(
            self.partner_1,
            self.partner_2,
            move_type='out_invoice',
            invoice_line_ids=[
                {
                    'product_id': self.product_a.id,
                    'quantity': 2.0,
                    'price_unit': 1000.0,
                    'discount': 20.0,
                    'tax_ids': [(Command.set(tax_10.ids))],
                },
                {
                    'product_id': self.product_b.id,
                    'quantity': 2.0,
                    'price_unit': 500.0,
                    'tax_ids': [(Command.set(tax_0.ids))],
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
                <xpath expr=".//*[local-name()='PaymentMeans']/*[local-name()='PaymentID']" position="replace">
                    <cbc:PaymentID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">___ignore___</cbc:PaymentID>
                </xpath>
                <xpath expr=".//*[local-name()='AdditionalDocumentReference']/*[local-name()='Attachment']/*[local-name()='EmbeddedDocumentBinaryObject']" position="attributes">
                    <attribute name="mimeCode">application/pdf</attribute>
                    <attribute name="filename">{invoice.invoice_pdf_report_id.name}</attribute>
                </xpath>
            ''',
            expected_file_path='from_odoo/sg_out_invoice.xml',
        )
        self.assertEqual(attachment.name[-6:], "sg.xml")
        self._assert_imported_invoice_from_etree(invoice, attachment)

    def test_export_import_invoice_new(self):
        self.env['ir.config_parameter'].set_param('account_edi_ubl_cii.use_new_dict_to_xml_helpers', 'True')
        self.test_export_import_invoice()

    def test_export_import_refund(self):
        tax_10 = self.percent_tax(10)
        tax_0 = self.percent_tax(0)
        refund = self._generate_move(
            self.partner_1,
            self.partner_2,
            move_type='out_refund',
            invoice_line_ids=[
                {
                    'product_id': self.product_a.id,
                    'quantity': 2.0,
                    'price_unit': 1000.0,
                    'discount': 20.0,
                    'tax_ids': [(Command.set(tax_10.ids))],
                },
                {
                    'product_id': self.product_b.id,
                    'quantity': 2.0,
                    'price_unit': 500.0,
                    'tax_ids': [(Command.set(tax_0.ids))],
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
                <xpath expr=".//*[local-name()='PaymentMeans']/*[local-name()='PaymentID']" position="replace">
                    <cbc:PaymentID xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">___ignore___</cbc:PaymentID>
                </xpath>
                <xpath expr=".//*[local-name()='AdditionalDocumentReference']/*[local-name()='Attachment']/*[local-name()='EmbeddedDocumentBinaryObject']" position="attributes">
                    <attribute name="mimeCode">application/pdf</attribute>
                    <attribute name="filename">{refund.invoice_pdf_report_id.name}</attribute>
                </xpath>
            ''',
            expected_file_path='from_odoo/sg_out_refund.xml',
        )
        self.assertEqual(attachment.name[-6:], "sg.xml")
        self._assert_imported_invoice_from_etree(refund, attachment)

    def test_export_import_refund_new(self):
        self.env['ir.config_parameter'].set_param('account_edi_ubl_cii.use_new_dict_to_xml_helpers', 'True')
        self.test_export_import_refund()
