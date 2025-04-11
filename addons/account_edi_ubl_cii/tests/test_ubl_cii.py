# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree
from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tools import file_open


@tagged('post_install', '-at_install')
class TestAccountEdiUblCii(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.uom_units = cls.env.ref('uom.product_uom_unit')
        cls.uom_dozens = cls.env.ref('uom.product_uom_dozen')

        cls.displace_prdct = cls.env['product.product'].create({
            'name': 'Displacement',
            'uom_id': cls.uom_units.id,
            'standard_price': 90.0,
        })

        cls.place_prdct = cls.env['product.product'].create({
            'name': 'Placement',
            'uom_id': cls.uom_units.id,
            'standard_price': 80.0,
        })

    def test_import_product(self):
        products = self.env['product.product'].create([{
            'name': 'XYZ',
            'default_code': '1234',
        }, {
            'name': 'XYZ',
            'default_code': '5678',
        }, {
            'name': 'XXX',
            'default_code': '1111',
            'barcode': '00001',
        }, {
            'name': 'YYY',
            'default_code': '1111',
            'barcode': '00002',
        }])
        line_vals = [
           {'product_id': self.place_prdct.id, 'product_uom_id': self.uom_units.id},
           {'product_id': self.displace_prdct.id, 'product_uom_id': self.uom_units.id},
           {'product_id': self.displace_prdct.id, 'product_uom_id': self.uom_units.id},
           {'product_id': self.displace_prdct.id, 'product_uom_id': self.uom_dozens.id},
           {'product_id': products[0].id, 'product_uom_id': self.uom_units.id},
           {'product_id': products[1].id, 'product_uom_id': self.uom_units.id},
           {'product_id': products[2].id, 'product_uom_id': self.uom_units.id},
           {'product_id': products[3].id, 'product_uom_id': self.uom_units.id},
        ]
        # To allow for the creation of Factur-X EDI the company must be either French or German
        company = self.company_data['company']
        company.country_id = self.env['res.country'].search([('code', '=', 'DE')])
        journal = self.company_data['default_journal_sale']
        journal.edi_format_ids = [
            Command.set(journal.compatible_edi_ids.filtered(lambda rec: rec.code == 'facturx_1_0_05').ids)
        ]

        invoice = self.env['account.move'].create({
            'partner_id': self.company_data_2['company'].partner_id.id,
            'move_type': 'out_invoice',
            'journal_id': journal.id,
            'invoice_line_ids': [Command.create(vals) for vals in line_vals],
        })
        invoice.action_post()

        facturx_attachment = invoice.edi_document_ids.attachment_id
        xml_tree = etree.fromstring(facturx_attachment.raw)

        # Testing the case where a product on the invoice has a UoM with a different category than the one in the DB
        wrong_uom_line = xml_tree.findall('./{*}SupplyChainTradeTransaction/{*}IncludedSupplyChainTradeLineItem')[1]
        wrong_uom_line.find('./{*}SpecifiedLineTradeDelivery/{*}BilledQuantity').attrib['unitCode'] = 'HUR'

        new_invoice = self.env.ref('account_edi_ubl_cii.edi_facturx_1_0_05')._create_invoice_from_xml_tree(
            facturx_attachment.name,
            xml_tree,
            invoice.journal_id,
        )

        self.assertRecordValues(new_invoice.invoice_line_ids, line_vals)

    def test_import_tax_prediction(self):
        """ We are going to create 2 tax and import the e-invoice twice.

        On the first attempt, as there isn't any data to leverage, the classic 'search' will be called and we expect
        the first tax created to be the selected one as the retrieval order is `sequence, id`.

        We will set the second tax on the bill and post it which make it the most probable one.

        On the second attempt, we expect that second tax to be retrieved.
        """
        if not hasattr(self.env["account.move.line"], '_predict_specific_tax'):
            self.skipTest("The predictive bill module isn't install and thus prediction with edi can't be tested.")
        # create 2 new taxes for the test seperatly to ensure the first gets the smaller id
        new_tax_1 = self.env["account.tax"].create({
            'name': 'tax with lower id could be retrieved first',
            'amount_type': 'percent',
            'type_tax_use': 'purchase',
            'amount': 16.0,
        })
        new_tax_2 = self.env["account.tax"].create({
            'name': 'tax with higher id could be retrieved second',
            'amount_type': 'percent',
            'type_tax_use': 'purchase',
            'amount': 16.0,
        })

        file_path = "bis3_bill_example.xml"
        file_path = f"{self.test_module}/tests/test_files/{file_path}"
        with file_open(file_path, 'rb') as file:
            xml_attachment = self.env['ir.attachment'].create({
                'mimetype': 'application/xml',
                'name': 'test_invoice.xml',
                'raw': file.read(),
            })

        # Import the document for the first time
        bill = self.env['account.journal']\
                .with_context(default_journal_id=self.company_data["default_journal_purchase"].id)\
                ._create_document_from_attachment(xml_attachment.id)

        # Ensure the first tax is retrieved as there isn't any prediction that could be leverage
        self.assertEqual(bill.invoice_line_ids.tax_ids, new_tax_1)

        # Set the second tax on the line to make it the most probable one
        bill.invoice_line_ids.tax_ids = new_tax_2
        bill.action_post()

        # Import the bill again and ensure the prediction did his work
        bill = self.env['account.journal']\
                .with_context(default_journal_id=self.company_data["default_journal_purchase"].id)\
                ._create_document_from_attachment(xml_attachment.id)
        self.assertEqual(bill.invoice_line_ids.tax_ids, new_tax_2)

    def test_norway_partner_without_vat(self):
        partner = self.env["res.partner"].create({
            "name": "Norwegian partner",
            "country_id": self.env.ref('base.no').id,
        })

        new_invoice = self.env["account.move"].create({
            "partner_id": partner.id,
            "move_type": "out_invoice",
            "invoice_line_ids": [Command.create({"name": "Test product", "price_unit": 100})],
        })
        new_invoice.action_post()
        xml = self.env['account.edi.xml.ubl_bis3']._export_invoice(new_invoice)[0]
        root = etree.fromstring(xml)
        self.assertEqual(root.findtext('./{*}AccountingCustomerParty/{*}Party/{*}EndpointID'), None)

    def test_import_partner_fields(self):
        """ We are going to import the e-invoice and check partner is correctly imported."""
        file_path = "bis3_bill_example.xml"
        file_path = f"{self.test_module}/tests/test_files/{file_path}"
        with file_open(file_path, 'rb') as file:
            xml_attachment = self.env['ir.attachment'].create({
                'mimetype': 'application/xml',
                'name': 'test_invoice.xml',
                'raw': file.read(),
            })

        bill = self.env['account.journal']\
                .with_context(default_journal_id=self.company_data["default_journal_purchase"].id)\
                ._create_document_from_attachment(xml_attachment.id)

        self.assertRecordValues(bill.partner_id, [{
            'name': "ALD Automotive LU",
            'phone': False,
            'email': 'adl@test.com',
            'vat': 'LU12977109',
            'street': '270 rte d\'Arlon',
            'street2': False,
            'city': 'Strassen',
            'zip': '8010',
        }])

    def test_import_bill_without_tax(self):
        """ Test that no tax is set (even the default one) when importing a bill without tax."""
        file_path = "bis3_bill_without_tax.xml"
        file_path = f"{self.test_module}/tests/test_files/{file_path}"
        with file_open(file_path, 'rb') as file:
            xml_attachment = self.env['ir.attachment'].create({
                'mimetype': 'application/xml',
                'name': 'test_invoice.xml',
                'raw': file.read(),
            })
        purchase_tax = self.env['account.tax'].create({
            'type_tax_use': 'purchase',
            'name': 'purchase_tax_10',
            'amount': 10,
        })
        self.company_data['company'].account_purchase_tax_id = purchase_tax
        bill = self.env['account.journal']\
                .with_context(default_journal_id=self.company_data['default_journal_purchase'].id)\
                ._create_document_from_attachment(xml_attachment.id)

        self.assertRecordValues(bill.invoice_line_ids, [{
            'amount_currency': 100.00,
            'quantity': 1.0,
            'tax_ids': self.env['account.tax'],
        }])
