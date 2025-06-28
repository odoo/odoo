# -*- coding: utf-8 -*-
from odoo import Command
from odoo.addons.l10n_account_edi_ubl_cii_tests.tests.common import TestUBLCommon
from odoo.tests import tagged
from odoo.exceptions import UserError
import base64


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUBLDE(TestUBLCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref="de_skr03"):
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
            'bank_ids': [(0, 0, {'acc_number': 'DE48500105176424548921'})],
            'ref': 'ref_partner_1',
        })

        cls.partner_2 = cls.env['res.partner'].create({
            'name': "partner_2",
            'street': "Europa-Park-Straße 2",
            'zip': "77977",
            'city': "Rust",
            'vat': 'DE186775212',
            'country_id': cls.env.ref('base.de').id,
            'bank_ids': [(0, 0, {'acc_number': 'DE50500105175653254743'})],
            'ref': 'ref_partner_2',
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

    @classmethod
    def setup_company_data(cls, company_name, chart_template):
        # OVERRIDE
        # to force the company to be german + add phone and email
        res = super().setup_company_data(
            company_name,
            chart_template=chart_template,
            country_id=cls.env.ref("base.de").id,
            phone="+49(0) 30 227-0",
            email="test@xrechnung@com",
        )
        return res

    def _detach_attachment(self, attachment):
        # attachments are protected from being edited because of the audit trail
        # in the tests, we are reusing the ame attachment coming from another invoice, which would then switch invoice
        self.env.cr.execute("UPDATE ir_attachment SET res_id = NULL WHERE id = %s", (attachment.id,))
        attachment.invalidate_recordset()

    def _assert_imported_invoice_from_etree(self, invoice, attachment):
        self._detach_attachment(attachment)
        return super()._assert_imported_invoice_from_etree(invoice, attachment)

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
            expected_file_path='from_odoo/xrechnung_ubl_out_invoice.xml',
        )
        self.assertEqual(attachment.name[-10:], "ubl_de.xml")
        self._assert_imported_invoice_from_etree(invoice, attachment)

    def test_export_import_invoice_without_vat_and_peppol_endpoint(self):
        self.partner_2.write({
            'vat': False,
            'peppol_endpoint': False,
            'email': 'partner_2@test.test',
        })
        invoice = self._generate_move(
            self.partner_1,
            self.partner_2,
            move_type='out_invoice',
            invoice_line_ids=[
                {
                    'product_id': self.product_a.id,
                    'quantity': 1.0,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(self.tax_19.ids)],
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
                <xpath expr=".//*[local-name()='PaymentMeans']/*[local-name()='PaymentID']" position="replace">
                    <PaymentID>___ignore___</PaymentID>
                </xpath>
                <xpath expr=".//*[local-name()='AdditionalDocumentReference']/*[local-name()='Attachment']/*[local-name()='EmbeddedDocumentBinaryObject']" position="attributes">
                    <attribute name="mimeCode">application/pdf</attribute>
                    <attribute name="filename">{invoice.invoice_pdf_report_id.name}</attribute>
                </xpath>
            ''',
            expected_file_path='from_odoo/xrechnung_ubl_out_invoice_without_vat.xml',
        )
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
            expected_file_path='from_odoo/xrechnung_ubl_out_refund.xml',
        )
        self.assertEqual(attachment.name[-10:], "ubl_de.xml")
        self._assert_imported_invoice_from_etree(refund, attachment)

    ####################################################
    # Test import
    ####################################################

    def test_import_invoice_xml(self):
        self._assert_imported_invoice_from_file(subfolder='tests/test_files/from_odoo',
            filename='xrechnung_ubl_out_invoice.xml', amount_total=3083.58, amount_tax=401.58,
            list_line_subtotals=[1782, 1000, -100], currency_id=self.currency_data['currency'].id)

    def test_import_export_invoice_xml(self):
        """
        Test whether the elements which are only specific to ubl_de are correctly exported
        and imported in the xml file
        """
        acc_bank = self.env['res.partner.bank'].create({
            'acc_number': 'BE15001559627232',
            'partner_id': self.company_data['company'].partner_id.id,
        })

        invoice = self._generate_move(
            self.partner_1,
            self.partner_2,
            move_type='out_invoice',
            partner_id=self.partner_1.id,
            partner_bank_id=acc_bank.id,
            invoice_date='2017-01-01',
            date='2017-01-01',
            invoice_line_ids=[{
                'product_id': self.product_a.id,
                'product_uom_id': self.env.ref('uom.product_uom_dozen').id,
                'price_unit': 275.0,
                'quantity': 5,
                'discount': 20.0,
                'tax_ids': [(6, 0, self.tax_19.ids)],
            }],
        )

        partner = invoice.commercial_partner_id
        attachment = invoice.ubl_cii_xml_id

        self.assertTrue(attachment)

        xml_content = base64.b64decode(attachment.with_context(bin_size=False).datas)
        xml_etree = self.get_xml_tree_from_string(xml_content)

        # Export: BuyerReference is in the out_invoice xml
        self.assertEqual(xml_etree.find('{*}BuyerReference').text, partner.ref)
        self.assertEqual(
            xml_etree.find('{*}CustomizationID').text,
            'urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0'
        )

        created_bill = self.env['account.move'].create({'move_type': 'in_invoice'})
        self._detach_attachment(attachment)
        created_bill.message_post(attachment_ids=[attachment.id])
        self.assertTrue(created_bill)
