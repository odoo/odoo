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

    def test_credit_notes_lines_matching_2(self):
        self.company.l10n_jo_edi_taxpayer_type = 'income'
        self.company.l10n_jo_edi_sequence_income_source = '4419618'

        order_vals = {
            'name': 'EIN00017',
            'lines': [
                {  # id = 1
                    'product_id': self.product_a.id,
                    'price_unit': 10,
                    'qty': 1,
                },
                {  # id = 2
                    'product_id': self.product_a.id,
                    'price_unit': 10,
                    'qty': 3,
                },
                {  # id = 3
                    'product_id': self.product_a.id,
                    'price_unit': 10,
                    'qty': 2,
                },
            ],
        }
        refund_vals = {
            'name': 'EIN998833',
            'lines': [
                {  # id = 3
                    'product_id': self.product_a.id,
                    'price_unit': 10,
                    'qty': 2,
                    'name': '3',  # label should not affect matching
                },
                {  # id = 1
                    'product_id': self.product_a.id,
                    'price_unit': 10,
                    'qty': 1,
                    'name': '1',
                },
                {  # id = 2
                    'product_id': self.product_a.id,
                    'price_unit': 10,
                    'qty': 2,
                    'name': '2',
                },
            ],
        }
        refund = self._l10n_jo_create_order_refund(order_vals, refund_vals)
        xml_string = self.env['pos.edi.xml.ubl_21.jo']._export_pos_order(refund)[0]
        xml_tree = self.get_xml_tree_from_string(xml_string)
        for xml_line, expected_line_id in zip(xml_tree.findall('./{*}InvoiceLine'), [3, 1, 2]):
            self.assertEqual(int(xml_line.findtext('{*}ID')), expected_line_id)

    def test_different_payment_methods(self):
        def get_xml_order_type(order):
            if order._l10n_jo_validate_fields():  # conflicting payment methods
                return False

            generated_file = self.env['pos.edi.xml.ubl_21.jo']._export_pos_order(order)[0]
            xml_tree = self.get_xml_tree_from_string(generated_file)
            return xml_tree.find(".//{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}InvoiceTypeCode").get('name')

        self.company.l10n_jo_edi_taxpayer_type = 'income'
        self.company.l10n_jo_edi_sequence_income_source = '4419618'

        cash_pm1, cash_pm2, bank_pm1, bank_pm2 = self.env['pos.payment.method'].create([
            {
                'name': 'Cash 1',
                'l10n_jo_edi_pos_is_cash': True,
            },
            {
                'name': 'Cash 2',
                'l10n_jo_edi_pos_is_cash': True,
            },
            {
                'name': 'Bank 1',
                'l10n_jo_edi_pos_is_cash': False,
            },
            {
                'name': 'Bank 2',
                'l10n_jo_edi_pos_is_cash': False,
            },
        ])
        self.main_pos_config.write({
            'payment_method_ids': [
                Command.link(cash_pm1.id),
                Command.link(cash_pm2.id),
                Command.link(bank_pm1.id),
                Command.link(bank_pm2.id),
            ],
        })
        for (payments, expected_type) in [
            ([(cash_pm1, 100)], '011'),
            ([(bank_pm1, 100)], '021'),
            ([(cash_pm1, 50), (bank_pm1, 50)], False),
            ([], False),
            ([(cash_pm1, 50), (cash_pm2, 50)], '011'),
            ([(bank_pm1, 50), (bank_pm2, 50)], '021'),
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
            order = self._l10n_jo_create_order(order_vals, payments=payments, default_payment=False)
            order_type = get_xml_order_type(order)
            self.assertEqual(order_type, expected_type)

    def test_mandatory_customer(self):
        self.company.l10n_jo_edi_taxpayer_type = 'income'
        self.company.l10n_jo_edi_sequence_income_source = '4419618'
        cash_pm, bank_pm = self.env['pos.payment.method'].create([
            {
                'name': 'Cash',
                'l10n_jo_edi_pos_is_cash': True,
            },
            {
                'name': 'Bank',
                'l10n_jo_edi_pos_is_cash': False,
            },
        ])
        self.main_pos_config.write({
            'payment_method_ids': [
                Command.link(cash_pm.id),
                Command.link(bank_pm.id),
            ],
        })
        # The rate is 1 USD = 2 JOD
        for currency_id, has_partner, amount_total, payment_method, is_valid in [
            (self.jod,   True,        100,          cash_pm,        True),
            (self.jod,   True,        10_000,       cash_pm,        True),
            (self.jod,   True,        10_001,       cash_pm,        True),
            (self.jod,   False,       100,          cash_pm,        True),
            (self.jod,   False,       10_000,       cash_pm,        True),
            (self.jod,   False,       10_001,       cash_pm,        False),
            (self.jod,   False,       20_000,       cash_pm,        False),
            (self.usd,   False,       5000.1,       cash_pm,        False),
            (self.usd,   False,       5000,         cash_pm,        True),
            (self.jod,   True,        100,          bank_pm,        True),
            (self.jod,   True,        10_000,       bank_pm,        True),
            (self.jod,   True,        10_001,       bank_pm,        True),
            (self.jod,   False,       100,          bank_pm,        False),
            (self.usd,   False,       100,          bank_pm,        False),
            (self.jod,   False,       10_000,       bank_pm,        False),
            (self.jod,   False,       10_001,       bank_pm,        False),
        ]:
            order_vals = {
                'name': 'EIN/998833/0',
                'partner_id': self.partner_jo.id if has_partner else False,
                'currency_id': currency_id,
                'date_order': '2022-09-27',
                'general_customer_note': 'ملاحظات 2',
                'lines': [
                    {
                        'product_id': self.product_a.id,
                        'price_unit': amount_total,
                        'qty': 1,
                        'discount': 0,
                        'tax_ids': [Command.clear()],
                    },
                ],
            }
            order = self._l10n_jo_create_order(order_vals, payments=[(payment_method, amount_total)], default_payment=False)
            self.assertEqual(bool(order._l10n_jo_validate_fields()), not is_valid)
