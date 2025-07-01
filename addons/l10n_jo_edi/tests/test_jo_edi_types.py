from odoo import Command
from odoo.tests import tagged
from odoo.addons.l10n_jo_edi.tests.jo_edi_common import JoEdiCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestJoEdiTypes(JoEdiCommon):
    def test_jo_income_invoice(self):
        self.company.l10n_jo_edi_taxpayer_type = 'income'
        self.company.l10n_jo_edi_sequence_income_source = '4419618'

        invoice_vals = {
            'name': 'EIN/998833/0',
            'invoice_date': '2022-09-27',
            'narration': 'ملاحظات 2',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 3,
                    'quantity': 44,
                    'discount': 1,
                    'tax_ids': [Command.clear()],
                }),
            ]
        }
        invoice = self._l10n_jo_create_invoice(invoice_vals)

        expected_file = self._read_xml_test_file('type_1')
        generated_file = self.env['account.edi.xml.ubl_21.jo']._export_invoice(invoice)[0]
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(generated_file),
            self.get_xml_tree_from_string(expected_file)
        )

    def test_jo_income_refund(self):
        self.company.l10n_jo_edi_taxpayer_type = 'income'
        self.company.l10n_jo_edi_sequence_income_source = '4419618'

        invoice_vals = {
            'name': 'EIN00017',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 18.85,
                    'quantity': 10,
                    'discount': 20,
                    'tax_ids': [Command.clear()],
                }),
            ],
        }
        refund_vals = {
            'name': 'EIN998833',
            'invoice_date': '2022-09-27',
            'narration': 'ملاحظات 2',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 3,
                    'quantity': 44,
                    'discount': 1,
                    'tax_ids': [Command.clear()],
                }),
            ],
        }
        refund = self._l10n_jo_create_refund(invoice_vals, 'change price', refund_vals)

        expected_file = self._read_xml_test_file('type_2')
        generated_file = self.env['account.edi.xml.ubl_21.jo']._export_invoice(refund)[0]
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(generated_file),
            self.get_xml_tree_from_string(expected_file)
        )

    def test_jo_sales_invoice(self):
        self.company.l10n_jo_edi_taxpayer_type = 'sales'
        self.company.l10n_jo_edi_sequence_income_source = '16683693'

        invoice_vals = {
            'name': 'TestEIN022',
            'invoice_date': '2023-11-10',
            'narration': 'Test General for Documentation',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 10,
                    'quantity': 100,
                    'discount': 10,
                    'tax_ids': [Command.set(self.jo_general_tax_10.ids)],
                }),
            ],
        }
        invoice = self._l10n_jo_create_invoice(invoice_vals)

        expected_file = self._read_xml_test_file('type_3')
        generated_file = self.env['account.edi.xml.ubl_21.jo']._export_invoice(invoice)[0]
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(generated_file),
            self.get_xml_tree_from_string(expected_file)
        )

    def test_jo_sales_refund(self):
        self.company.l10n_jo_edi_taxpayer_type = 'sales'
        self.company.l10n_jo_edi_sequence_income_source = '16683693'

        invoice_vals = {
            'name': 'TestEIN022',
            'currency_id': self.usd.id,  # should not affect values as they are reported in invoice currency
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 10,
                    'quantity': 100,
                    'discount': 10,
                    'tax_ids': [Command.set(self.jo_general_tax_10.ids)],
                }),
            ],
        }
        refund_vals = {
            'name': 'TestEIN022R',
            'currency_id': self.usd.id,  # should not affect values as they are reported in invoice currency
            'invoice_date': '2023-11-10',
        }
        refund = self._l10n_jo_create_refund(invoice_vals, 'Test/Return', refund_vals)

        expected_file = self._read_xml_test_file('type_4')
        generated_file = self.env['account.edi.xml.ubl_21.jo']._export_invoice(refund)[0]
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(generated_file),
            self.get_xml_tree_from_string(expected_file)
        )

    def test_jo_special_invoice(self):
        self.company.l10n_jo_edi_taxpayer_type = 'special'
        self.company.l10n_jo_edi_sequence_income_source = '16683696'

        invoice_vals = {
            'name': 'TestEIN013',
            'currency_id': self.usd.id,  # should not affect values as they are reported in invoice currency
            'invoice_date': '2023-11-10',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_b.id,
                    'price_unit': 100,
                    'quantity': 1,
                    'tax_ids': [Command.set((self.jo_general_tax_10 | self.jo_special_tax_10).ids)],
                }),
            ],
        }
        invoice = self._l10n_jo_create_invoice(invoice_vals)

        expected_file = self._read_xml_test_file('type_5')
        generated_file = self.env['account.edi.xml.ubl_21.jo']._export_invoice(invoice)[0]
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(generated_file),
            self.get_xml_tree_from_string(expected_file)
        )

    def test_jo_special_refund(self):
        self.company.l10n_jo_edi_taxpayer_type = 'special'
        self.company.l10n_jo_edi_sequence_income_source = '16683696'

        invoice_vals = {
            'name': 'TestEIN013',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_b.id,
                    'price_unit': 100,
                    'quantity': 1,
                    'tax_ids': [Command.set((self.jo_general_tax_10 | self.jo_special_tax_10).ids)],
                }),
            ],
        }
        refund_vals = {
            'name': 'TestEINReturn013',
            'invoice_date': '2023-11-10',
        }
        refund = self._l10n_jo_create_refund(invoice_vals, 'Test Return', refund_vals)

        expected_file = self._read_xml_test_file('type_6')
        generated_file = self.env['account.edi.xml.ubl_21.jo']._export_invoice(refund)[0]
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(generated_file),
            self.get_xml_tree_from_string(expected_file)
        )

    def test_jo_no_vat_customer(self):
        self.company.l10n_jo_edi_taxpayer_type = 'income'
        self.company.l10n_jo_edi_sequence_income_source = '4419618'
        self.partner_jo.vat = False

        invoice = self._l10n_jo_create_invoice({
            'name': 'EIN/998833/0',
            'invoice_date': '2022-09-27',
            'narration': 'ملاحظات 2',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 3,
                    'quantity': 44,
                    'discount': 1,
                    'tax_ids': [Command.clear()],
                }),
            ],
        })

        expected_file = self._read_xml_test_file('type_7')
        generated_file = self.env['account.edi.xml.ubl_21.jo']._export_invoice(invoice)[0]
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(generated_file),
            self.get_xml_tree_from_string(expected_file)
        )

    def test_jo_no_country_customer(self):
        self.company.l10n_jo_edi_taxpayer_type = 'income'
        self.company.l10n_jo_edi_sequence_income_source = '4419618'
        self.partner_jo.country_id = False

        invoice = self._l10n_jo_create_invoice({
            'name': 'EIN/998833/0',
            'invoice_date': '2022-09-27',
            'narration': 'ملاحظات 2',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 3,
                    'quantity': 44,
                    'discount': 1,
                    'tax_ids': [Command.clear()],
                }),
            ],
        })

        expected_file = self._read_xml_test_file('type_8')
        generated_file = self.env['account.edi.xml.ubl_21.jo']._export_invoice(invoice)[0]
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(generated_file),
            self.get_xml_tree_from_string(expected_file)
        )

    def test_credit_notes_lines_matching(self):
        self.company.l10n_jo_edi_taxpayer_type = 'income'
        self.company.l10n_jo_edi_sequence_income_source = '4419618'

        invoice_vals = {
            'name': 'EIN00017',
            'invoice_line_ids': [
                Command.create({  # id = 1
                    'product_id': self.product_a.id,
                    'price_unit': 10,
                    'quantity': 10,
                    'discount': 10,
                }),
                Command.create({  # id = 2
                    'product_id': self.product_a.id,
                    'price_unit': 10,
                    'quantity': 10,
                    'discount': 20,
                }),
                Command.create({  # id = 3
                    'product_id': self.product_b.id,
                    'price_unit': 10,
                    'quantity': 10,
                }),
                Command.create({  # id = 4
                    'product_id': self.product_b.id,
                    'price_unit': 20,
                    'quantity': 10,
                }),
            ],
        }
        refund_vals = {
            'name': 'EIN998833',
            'invoice_date': '2022-09-27',
            'narration': 'ملاحظات 2',
            'invoice_line_ids': [
                Command.create({  # id should be 4
                    'product_id': self.product_b.id,
                    'price_unit': 20,
                    'quantity': 3,
                }),
                Command.create({  # id should be 1
                    'product_id': self.product_a.id,
                    'price_unit': 10,
                    'quantity': 10,
                    'discount': 10,
                }),
                Command.create({  # id should be 2
                    'product_id': self.product_a.id,
                    'price_unit': 10,
                    'quantity': 1,
                    'discount': 20,
                }),
                Command.create({  # id should be > 4
                    'product_id': self.product_b.id,
                    'price_unit': 30,
                    'quantity': 10,
                }),
            ],
        }
        refund = self._l10n_jo_create_refund(invoice_vals, 'change price', refund_vals)
        xml_string = self.env['account.edi.xml.ubl_21.jo']._export_invoice(refund)[0]
        xml_tree = self.get_xml_tree_from_string(xml_string)
        for xml_line, expected_line_id in zip(xml_tree.findall('./{*}InvoiceLine'), [4, 1, 2]):
            self.assertEqual(int(xml_line.findtext('{*}ID')), expected_line_id)

        self.assertGreater(int(xml_tree.findall('./{*}InvoiceLine')[-1].findtext('{*}ID')), 4)
