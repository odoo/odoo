from odoo import Command
from odoo.tests import tagged
from odoo.addons.l10n_jo_edi_pos.tests.jo_edi_pos_common import JoEdiPosCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestJoEdiPosTypes(JoEdiPosCommon):
    def test_jo_pos_income_invoice(self):
        self.company.l10n_jo_edi_taxpayer_type = 'income'
        self.company.l10n_jo_edi_sequence_income_source = '4419618'

        order_vals = {
            'name': 'EIN/998833/0',
            'date_order': '2022-09-27',
            'general_customer_note': 'ملاحظات 2',
            'lines': [
                {
                    'product_id': self.product_a.id,
                    'price_unit': 3,
                    'qty': 44,
                    'discount': 1,
                },
            ],
        }
        order = self._l10n_jo_create_order(order_vals)

        expected_file = self._read_xml_test_file('type_1')
        generated_file = self.env['pos.edi.xml.ubl_21.jo']._export_pos_order(order)[0]
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(generated_file),
            self.get_xml_tree_from_string(expected_file)
        )

    def test_jo_pos_income_refund(self):
        self.company.l10n_jo_edi_taxpayer_type = 'income'
        self.company.l10n_jo_edi_sequence_income_source = '4419618'

        order_vals = {
            'name': 'EIN00017',
            'lines': [
                {
                    'product_id': self.product_a.id,
                    'price_unit': 18.85,
                    'qty': 10,
                    'discount': 20,
                },
            ],
        }
        refund_vals = {
            'name': 'EIN998833',
            'date_order': '2022-09-27',
            'general_customer_note': 'ملاحظات 2',
            'l10n_jo_edi_pos_return_reason': 'Reversal of: EIN00017, change price',
            'lines': [
                {
                    'price_unit': 3,
                    'qty': -44,
                    'discount': 1,
                },
            ],
        }
        refund = self._l10n_jo_create_order_refund(order_vals, refund_vals)

        expected_file = self._read_xml_test_file('type_2')
        generated_file = self.env['pos.edi.xml.ubl_21.jo']._export_pos_order(refund)[0]
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(generated_file),
            self.get_xml_tree_from_string(expected_file)
        )

    def test_jo_pos_sales_invoice(self):
        self.company.l10n_jo_edi_taxpayer_type = 'sales'
        self.company.l10n_jo_edi_sequence_income_source = '16683693'

        order_vals = {
            'name': 'TestEIN022',
            'date_order': '2023-11-10',
            'general_customer_note': 'Test General for Documentation',
            'lines': [
                {
                    'product_id': self.product_a.id,
                    'price_unit': 10,
                    'qty': 100,
                    'discount': 10,
                    'tax_ids': [Command.set(self.jo_general_tax_10.ids)],
                },
            ],
        }
        order = self._l10n_jo_create_order(order_vals)

        expected_file = self._read_xml_test_file('type_3')
        generated_file = self.env['pos.edi.xml.ubl_21.jo']._export_pos_order(order)[0]
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(generated_file),
            self.get_xml_tree_from_string(expected_file)
        )

    def test_jo_pos_sales_refund(self):
        self.company.l10n_jo_edi_taxpayer_type = 'sales'
        self.company.l10n_jo_edi_sequence_income_source = '16683693'

        order_vals = {
            'name': 'TestEIN022',
            'currency_id': self.usd.id,  # should not affect values as they are reported in order currency
            'lines': [
                {
                    'product_id': self.product_a.id,
                    'price_unit': 10,
                    'qty': 100,
                    'discount': 10,
                    'tax_ids': [Command.set(self.jo_general_tax_10.ids)],
                },
            ],
        }
        refund_vals = {
            'name': 'TestEIN022R',
            'currency_id': self.usd.id,  # should not affect values as they are reported in order currency
            'date_order': '2023-11-10',
            'l10n_jo_edi_pos_return_reason': 'Reversal of: TestEIN022, Test_Return',
        }
        refund = self._l10n_jo_create_order_refund(order_vals, refund_vals)

        expected_file = self._read_xml_test_file('type_4')
        generated_file = self.env['pos.edi.xml.ubl_21.jo']._export_pos_order(refund)[0]
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(generated_file),
            self.get_xml_tree_from_string(expected_file)
        )

    def test_jo_pos_special_invoice(self):
        self.company.l10n_jo_edi_taxpayer_type = 'special'
        self.company.l10n_jo_edi_sequence_income_source = '16683696'

        order_vals = {
            'name': 'TestEIN013',
            'currency_id': self.usd.id,  # should not affect values as they are reported in order currency
            'date_order': '2023-11-10',
            'lines': [
                {
                    'product_id': self.product_b.id,
                    'price_unit': 100,
                    'qty': 1,
                    'tax_ids': [Command.set((self.jo_general_tax_10 | self.jo_special_tax_10).ids)],
                },
            ],
        }
        order = self._l10n_jo_create_order(order_vals)

        expected_file = self._read_xml_test_file('type_5')
        generated_file = self.env['pos.edi.xml.ubl_21.jo']._export_pos_order(order)[0]
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(generated_file),
            self.get_xml_tree_from_string(expected_file)
        )

    def test_jo_pos_special_refund(self):
        self.company.l10n_jo_edi_taxpayer_type = 'special'
        self.company.l10n_jo_edi_sequence_income_source = '16683696'

        order_vals = {
            'name': 'TestEIN013',
            'lines': [
                {
                    'product_id': self.product_b.id,
                    'price_unit': 100,
                    'qty': 1,
                    'tax_ids': [Command.set((self.jo_general_tax_10 | self.jo_special_tax_10).ids)],
                },
            ],
        }
        refund_vals = {
            'name': 'TestEINReturn013',
            'date_order': '2023-11-10',
            'l10n_jo_edi_pos_return_reason': 'Reversal of: TestEIN013, Test Return',
        }
        refund = self._l10n_jo_create_order_refund(order_vals, refund_vals)

        expected_file = self._read_xml_test_file('type_6')
        generated_file = self.env['pos.edi.xml.ubl_21.jo']._export_pos_order(refund)[0]
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(generated_file),
            self.get_xml_tree_from_string(expected_file)
        )

    def test_jo_pos_no_vat_customer(self):
        self.company.l10n_jo_edi_taxpayer_type = 'income'
        self.company.l10n_jo_edi_sequence_income_source = '4419618'
        self.partner_jo.vat = False

        order_vals = {
            'name': 'EIN/998833/0',
            'date_order': '2022-09-27',
            'general_customer_note': 'ملاحظات 2',
            'lines': [
                {
                    'product_id': self.product_a.id,
                    'price_unit': 3,
                    'qty': 44,
                    'discount': 1,
                    'tax_ids': [Command.clear()],
                },
            ],
        }
        order = self._l10n_jo_create_order(order_vals)

        expected_file = self._read_xml_test_file('type_7')
        generated_file = self.env['pos.edi.xml.ubl_21.jo']._export_pos_order(order)[0]
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(generated_file),
            self.get_xml_tree_from_string(expected_file)
        )

    def test_jo_pos_no_country_customer(self):
        self.company.l10n_jo_edi_taxpayer_type = 'income'
        self.company.l10n_jo_edi_sequence_income_source = '4419618'
        self.partner_jo.country_id = False

        order_vals = {
            'name': 'EIN/998833/0',
            'date_order': '2022-09-27',
            'general_customer_note': 'ملاحظات 2',
            'lines': [
                {
                    'product_id': self.product_a.id,
                    'price_unit': 3,
                    'qty': 44,
                    'discount': 1,
                    'tax_ids': [Command.clear()],
                },
            ],
        }

        order = self._l10n_jo_create_order(order_vals)

        expected_file = self._read_xml_test_file('type_8')
        generated_file = self.env['pos.edi.xml.ubl_21.jo']._export_pos_order(order)[0]
        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(generated_file),
            self.get_xml_tree_from_string(expected_file)
        )

    def test_credit_notes_lines_matching(self):
        self.company.l10n_jo_edi_taxpayer_type = 'income'
        self.company.l10n_jo_edi_sequence_income_source = '4419618'

        order_vals = {
            'name': 'EIN00017',
            'lines': [
                {  # id = 1
                    'product_id': self.product_a.id,
                    'price_unit': 10,
                    'qty': 10,
                    'discount': 10,
                },
                {  # id = 2
                    'product_id': self.product_a.id,
                    'price_unit': 10,
                    'qty': 10,
                    'discount': 20,
                },
                {  # id = 3
                    'product_id': self.product_b.id,
                    'price_unit': 10,
                    'qty': 10,
                },
                {  # id = 4
                    'product_id': self.product_b.id,
                    'price_unit': 20,
                    'qty': 10,
                },
            ],
        }
        refund_vals = {
            'name': 'EIN998833',
            'date_order': '2022-09-27',
            'general_customer_note': 'ملاحظات 2',
            'l10n_jo_edi_pos_return_reason': 'change price',
            'lines': [
                {  # id should be 4
                    'product_id': self.product_b.id,
                    'price_unit': 20,
                    'qty': -3,
                    'discount': 0,
                },
                {  # id should be 1
                    'product_id': self.product_a.id,
                    'price_unit': 10,
                    'qty': -10,
                    'discount': 10,
                },
                {  # id should be 2
                    'product_id': self.product_a.id,
                    'price_unit': 10,
                    'qty': -1,
                    'discount': 20,
                },
                {  # id should be > 4
                    'product_id': self.product_b.id,
                    'price_unit': 30,
                    'qty': -10,
                },
            ],
        }
        refund = self._l10n_jo_create_order_refund(order_vals, refund_vals)
        xml_string = self.env['pos.edi.xml.ubl_21.jo']._export_pos_order(refund)[0]
        xml_tree = self.get_xml_tree_from_string(xml_string)
        for xml_line, expected_line_id in zip(xml_tree.findall('./{*}InvoiceLine'), [4, 1, 2]):
            self.assertEqual(int(xml_line.findtext('{*}ID')), expected_line_id)

        self.assertGreater(int(xml_tree.findall('./{*}InvoiceLine')[-1].findtext('{*}ID')), 4)

    def test_different_payment_methods(self):
        def get_xml_order_type(order, amount_cash, amount_bank):
            cash_pm = order.config_id.payment_method_ids.filtered(lambda pm: pm.l10n_jo_edi_pos_is_cash)[0]
            bank_pm = order.config_id.payment_method_ids.filtered(lambda pm: not pm.l10n_jo_edi_pos_is_cash)[0]

            if amount_cash:
                self.make_payment(order, cash_pm, amount_cash)
            if amount_bank:
                self.make_payment(order, bank_pm, amount_bank)
            if order._l10n_jo_validate_fields():  # conflicting payment methods
                return False

            generated_file = self.env['pos.edi.xml.ubl_21.jo']._export_pos_order(order)[0]
            xml_tree = self.get_xml_tree_from_string(generated_file)
            return xml_tree.find(".//{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}InvoiceTypeCode").get('name')

        self.company.l10n_jo_edi_taxpayer_type = 'income'
        self.company.l10n_jo_edi_sequence_income_source = '4419618'

        for (cash_amount, bank_amount, expected_type) in [
            (100, 0, '011'),
            (0, 100, '021'),
            (50, 50, False),
        ]:
            order_vals = {
                'name': 'EIN/998833/0',
                'date_order': '2022-09-27',
                'general_customer_note': 'ملاحظات 2',
                'lines': [
                    {
                        'product_id': self.product_a.id,
                        'price_unit': 100,
                        'qty': 1,
                        'discount': 0,
                        'tax_ids': [Command.clear()],
                    },
                ],
            }
            order = self._l10n_jo_create_order(order_vals)
            order_type = get_xml_order_type(order, cash_amount, bank_amount)
            self.assertEqual(order_type, expected_type)
