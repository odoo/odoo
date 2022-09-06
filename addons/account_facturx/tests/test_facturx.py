# -*- coding: utf-8 -*-

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tests.common import Form
from odoo.modules.module import get_resource_path
from odoo.tools.misc import file_open
from odoo import Command

import base64


@tagged('post_install', '-at_install')
class TestFacturx(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # Required for `product_uom_id` to be visible in the form views
        cls.env.user.groups_id += cls.env.ref('uom.group_uom')

        cls.currency_data['currency'] = cls.env.ref('base.EUR')

        cls.partner_1 = cls.env['res.partner'].create({
            'name': "partner_1",
            'street': "Rue Jean Jaurès, 42",
            'zip': "75000",
            'city': "Paris",
            'vat': 'FR05677404089',
            'country_id': cls.env.ref('base.fr').id,
            'bank_ids': [(0, 0, {'acc_number': 'FR15001559627230'})],
            'phone': '+1 (650) 555-0111',
            'email': "partner1@yourcompany.com",
            'ref': 'seller_ref',
        })

        cls.partner_2 = cls.env['res.partner'].create({
            'name': "partner_2",
            'street': "Rue Charles de Gaulle",
            'zip': "52330",
            'city': "Colombey-les-Deux-Églises",
            'vat': 'FR35562153452',
            'country_id': cls.env.ref('base.fr').id,
            'bank_ids': [(0, 0, {'acc_number': 'FR90735788866632'})],
            'ref': 'buyer_ref',
        })

        cls.tax_21 = cls.env['account.tax'].create({
            'name': 'tax_21',
            'amount_type': 'percent',
            'amount': 21,
            'type_tax_use': 'sale',
            'country_id': cls.env.ref('base.fr').id,
        })

        cls.tax_12 = cls.env['account.tax'].create({
            'name': 'tax_12',
            'amount_type': 'percent',
            'amount': 12,
            'type_tax_use': 'sale',
            'country_id': cls.env.ref('base.fr').id,
        })

        cls.tax_21_purchase = cls.env['account.tax'].create({
            'name': 'tax_21',
            'amount_type': 'percent',
            'amount': 21,
            'type_tax_use': 'purchase',
            'country_id': cls.env.ref('base.fr').id,
        })

        cls.tax_20_purchase = cls.env['account.tax'].create({
            'name': 'tax_20',
            'amount_type': 'percent',
            'amount': 20,
            'type_tax_use': 'purchase',
            'country_id': cls.env.ref('base.fr').id,
        })

        cls.tax_12_purchase = cls.env['account.tax'].create({
            'name': 'tax_12',
            'amount_type': 'percent',
            'amount': 12,
            'type_tax_use': 'purchase',
            'country_id': cls.env.ref('base.fr').id,
        })

        cls.tax_55_purchase = cls.env['account.tax'].create({
            'name': 'tax_55',
            'amount_type': 'percent',
            'amount': 5.5,
            'type_tax_use': 'purchase',
            'country_id': cls.env.ref('base.fr').id,
        })

    @classmethod
    def setup_company_data(cls, company_name, chart_template):
        # OVERRIDE
        eur = cls.env.ref('base.EUR')
        if not eur.active:
            eur.active = True

        res = super().setup_company_data(
            company_name,
            chart_template=chart_template,
            country_id=cls.env.ref("base.fr").id,
            phone='+1 (650) 555-0111',  # [BR-DE-6] "Seller contact telephone number" (BT-42) is required
            email="info@yourcompany.com",  # [BR-DE-7] The element "Seller contact email address" (BT-43) is required
        )
        res['company'].currency_id = eur
        return res

    def _generate_move(self, seller, buyer, move_type, **invoice_kwargs):
        self.env.company.write({
            'partner_id': seller.id,
            'name': seller.name,
            'street': seller.street,
            'zip': seller.zip,
            'city': seller.city,
            'vat': seller.vat,
            'country_id': seller.country_id.id,
        })

        account_move = self.env['account.move'].create({
            'partner_id': buyer.id,
            'partner_bank_id': (seller if move_type == 'out_invoice' else buyer).bank_ids[:1].id,
            'invoice_payment_term_id': self.pay_terms_b.id,
            'invoice_date': '2017-01-01',
            'date': '2017-01-01',
            'currency_id': self.currency_data['currency'].id,
            'invoice_origin': 'test invoice origin',
            'narration': 'test narration',
            'move_type': move_type,
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 2.0,
                    'product_uom_id': self.env.ref('uom.product_uom_dozen').id,
                    'price_unit': 990.0,
                    'discount': 10.0,
                    'tax_ids': [Command.set(self.tax_21.ids)],
                }),
                Command.create({
                    'product_id': self.product_b.id,
                    'quantity': 10.0,
                    'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(self.tax_12.ids)],
                }),
                Command.create({
                    'product_id': self.product_b.id,
                    'quantity': -1.0,
                    'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(self.tax_12.ids)],
                }),
            ]
        })

        account_move.action_post()
        return account_move

    def _assert_attachment_equal(self, attachment, xpaths, expected_file):
        """
        Compare a given attachment content with an expected xml file.
        """
        xml_etree = self.get_xml_tree_from_string(attachment)

        expected_file_path = get_resource_path('account_facturx', 'tests/test_files', expected_file)
        expected_etree = self.get_xml_tree_from_string(file_open(expected_file_path, "r").read())

        modified_etree = self.with_applied_xpath(
            expected_etree,
            xpaths
        )

        self.assertXmlTreeEqual(
            xml_etree,
            modified_etree,
        )

    def _assert_imported_invoice_from_file(self, filename, amount_total, amount_tax, list_line_subtotals,
                                           move_type='in_invoice'):
        """
        Create an empty account.move, update the file to fill its fields, asserts the currency, total and tax amounts
        are as expected.
        """
        # Create empty account.move, then update a file
        invoice = self.env['account.move'].create({
            'move_type': move_type,
            'journal_id': self.company_data['default_journal_purchase'].id,
        })
        invoice_count = len(self.env['account.move'].search([]))

        # Import the file to fill the empty invoice
        file_path = get_resource_path('account_facturx', 'tests/test_files', filename)
        file = open(file_path, 'rb').read()

        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'datas': base64.encodebytes(file),
            'res_id': invoice.id,
            'res_model': 'account.move',
        })

        invoice.message_post(attachment_ids=[attachment.id])

        # Checks
        self.assertEqual(len(self.env['account.move'].search([])), invoice_count)
        self.assertRecordValues(invoice, [{
            'amount_total': amount_total,
            'amount_tax': amount_tax,
        }])
        self.assertEqual(invoice.invoice_line_ids.mapped('price_subtotal'), list_line_subtotals)


    ####################################################
    # Test export - import
    ####################################################

    def test_export_pdf(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_1.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id
            })],
        })
        invoice.action_post()
        ctx = invoice.action_invoice_sent()['context']
        ctx.update({'active_ids': [invoice.id]})
        wizard = self.env['account.invoice.send'].with_context(ctx).create({})
        form = Form(wizard)
        form.is_email = True  # trigger the onchange
        attachment_id = form._values['attachment_ids'][0][2]
        # In a test environment, we can't generate pdf, only html: see _render_qweb_pdf in base
        html_attachment = self.env['ir.attachment'].browse(attachment_id)
        self.assertEqual(html_attachment.name, 'Invoice_INV_2022_00001.html')

    def test_export_invoice(self):
        invoice = self._generate_move(
            self.partner_1,
            self.partner_2,
            move_type='out_invoice',
        )
        facturx_content, errors = self.env['account.facturx']._export_invoice(invoice)
        self._assert_attachment_equal(
            facturx_content,
            xpaths='''
                <xpath expr="./*[local-name()='ExchangedDocument']/*[local-name()='ID']" position="replace">
                        <ID>___ignore___</ID>
                </xpath>
                <xpath expr=".//*[local-name()='IssuerAssignedID']" position="replace">
                        <IssuerAssignedID>___ignore___</IssuerAssignedID>
                </xpath>
                <xpath expr=".//*[local-name()='PaymentReference']" position="replace">
                        <PaymentReference>___ignore___</PaymentReference>
                </xpath>
            ''',
            expected_file='facturx_out_invoice.xml',
        )

    def test_export_refund(self):
        refund = self._generate_move(
            self.partner_1,
            self.partner_2,
            move_type='out_refund',
        )
        facturx_content, errors = self.env['account.facturx']._export_invoice(refund)
        self._assert_attachment_equal(
            facturx_content,
            xpaths='''
                <xpath expr="./*[local-name()='ExchangedDocument']/*[local-name()='ID']" position="replace">
                        <ID>___ignore___</ID>
                </xpath>
                <xpath expr=".//*[local-name()='IssuerAssignedID']" position="replace">
                        <IssuerAssignedID>___ignore___</IssuerAssignedID>
                </xpath>
            ''',
            expected_file='facturx_out_refund.xml'
        )

    ####################################################
    # Test import
    ####################################################

    def test_import_fnfe_examples(self):
        # Source: official documentation of the FNFE (subdirectory: "5. FACTUR-X 1.0.06 - Examples")
        # the 2 following files have the same pdf but one is labelled as an invoice and the other as a refund
        # source: Avoir_FR_type380_EN16931.pdf
        self._assert_imported_invoice_from_file(filename='facturx_credit_note_type380.xml',
            amount_total=233.47, amount_tax=14.99, list_line_subtotals=[20.48, 198], move_type='in_refund')
        # source: Avoir_FR_type381_EN16931.pdf
        self._assert_imported_invoice_from_file(filename='facturx_credit_note_type381.xml',
            amount_total=233.47, amount_tax=14.99, list_line_subtotals=[20.48, 198], move_type='in_refund')
        # source: Facture_F20220024_EN_16931_basis_quantity, basis quantity != 1 for one of the lines
        self._assert_imported_invoice_from_file(filename='facturx_invoice_basis_quantity.xml',
            amount_total=108, amount_tax=8, list_line_subtotals=[-5, 10, 60, 28, 7])
        # source: Facture_F20220029_EN_16931_K.pdf, credit note labelled as an invoice with negative amounts
        self._assert_imported_invoice_from_file(filename='facturx_invoice_negative_amounts.xml',
            amount_total=90, amount_tax=0, list_line_subtotals=[-5, 10, 60, 30, 5, 0, -10], move_type='in_refund')
