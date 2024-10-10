from odoo import Command
from odoo.tests import tagged
from odoo.tools import misc
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEdiJo(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref='jo_standard'):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.company = cls.setup_company_data('Jordan Company', chart_template=chart_template_ref)['company']
        cls.company.vat = '8000514'

        def _create_tax(amount, amount_type):
            return cls.env['account.tax'].create(
                {
                    'name': f'{amount_type} {amount}',
                    'amount_type': amount_type,
                    'amount': amount,
                    'company_id': cls.company.id,
                    'include_base_amount': amount_type == 'fixed',
                    'is_base_affected': amount_type == 'percent',
                    'sequence': 2 if amount_type == 'percent' else 1,
                })

        cls.jo_general_tax_10 = _create_tax(10, 'percent')
        cls.jo_special_tax_10 = _create_tax(10, 'fixed')
        cls.jo_special_tax_5 = _create_tax(5, 'fixed')

        cls.partner_jo = cls.env['res.partner'].create({
            'name': 'Ahmad',
            'ref': 'Jordan Partner',
            'city': 'Amman',
            'vat': '54321',
            'zip': '94538',
            'country_id': cls.env.ref('base.jo').id,
            'state_id': cls.env.ref('base.state_jo_az').id,
            'phone': '+962 795-5585-949',
            'company_type': 'company',
        })

        # The rate of 1 USD = 2 JOD is meant to simplify tests
        cls.usd = cls.env.ref('base.USD')
        cls.setup_currency_rate(cls.usd, 0.5)

    @classmethod
    def setup_currency_rate(cls, currency, rate):
        currency.sudo().rate_ids.unlink()
        return cls.env['res.currency.rate'].create({
            'name': '2019-01-01',
            'rate': rate,
            'currency_id': currency.id,
            'company_id': cls.company.id,
        })

    def _create_invoice(self, **kwargs):
        def optional_arg(key):
            if key in kwargs:
                return kwargs[key]
            return None

        vals = {
            'name': kwargs['name'],
            'move_type': 'out_' + kwargs['type'],
            'company_id': self.company.id,
            'partner_id': self.partner_jo.id,
            'invoice_date': kwargs['date'],
            'currency_id': (optional_arg('currency') or self.company.currency_id).id,
            'narration': optional_arg('narration'),
            'invoice_line_ids': [Command.create({
                'product_id': line['product_id'].id,
                'price_unit': line['price'],
                'quantity': line['quantity'],
                'discount': line['discount_percent'],
                'currency_id': (optional_arg('currency') or self.company.currency_id).id,
                'tax_ids': [Command.set([tax.id for tax in line['taxes']])],
            }) for line in kwargs['lines']],
        }
        move = self.env['account.move'].create(vals)
        move.state = 'posted'
        return move

    def _read_xml_test_file(self, file_no):
        with misc.file_open(f'l10n_jo_edi/tests/test_files/{file_no}.xml', 'rb') as file:
            result_file = file.read()
        return result_file

    def test_jo_income_invoice(self):
        move_lines = [
            {
                'product_id': self.product_a,
                'price': 3,
                'quantity': 44,
                'discount_percent': 1,
                'taxes': [],
            },
        ]
        self.company.l10n_jo_edi_sequence_income_source = '4419618'
        move = self._create_invoice(name='EIN/998833/0',
                                    type='invoice',
                                    date='2022-09-27',
                                    narration='ملاحظات 2',
                                    lines=move_lines)

        expected_file = self._read_xml_test_file(1)
        generated_file = self.env['account.edi.xml.ubl_21.jo']._export_invoice(move)

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(generated_file),
            self.get_xml_tree_from_string(expected_file)
        )

    def test_jo_income_refund(self):
        move_lines = [
            {
                'product_id': self.product_a,
                'price': 3,
                'quantity': 44,
                'discount_percent': 1,
                'taxes': [],
            },
        ]
        self.company.l10n_jo_edi_sequence_income_source = '4419618'
        move = self._create_invoice(name='EIN998833',
                                    type='refund',
                                    date='2022-09-27',
                                    narration='ملاحظات 2',
                                    lines=move_lines)
        move.ref = 'change price'
        old_move_lines = [
            {
                'product_id': self.product_a,
                'price': 18.85,
                'quantity': 10,
                'discount_percent': 20,
                'taxes': [],
            },
        ]
        move.reversed_entry_id = self._create_invoice(name='EIN00017',
                                                      type='invoice',
                                                      date='2020-09-05',
                                                      lines=old_move_lines)

        expected_file = self._read_xml_test_file(2)
        generated_file = self.env['account.edi.xml.ubl_21.jo']._export_invoice(move)

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(generated_file),
            self.get_xml_tree_from_string(expected_file)
        )

    def test_jo_sales_invoice(self):
        self.company.l10n_jo_edi_taxpayer_type = 'sales'

        move_lines = [
            {
                'product_id': self.product_a,
                'price': 10,
                'quantity': 100,
                'discount_percent': 10,
                'taxes': [self.jo_general_tax_10],
            },
        ]
        self.company.l10n_jo_edi_sequence_income_source = '16683693'
        move = self._create_invoice(name='TestEIN022',
                                    type='invoice',
                                    date='2023-11-10',
                                    narration='Test General for Documentation',
                                    lines=move_lines)

        expected_file = self._read_xml_test_file(3)
        generated_file = self.env['account.edi.xml.ubl_21.jo']._export_invoice(move)

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(generated_file),
            self.get_xml_tree_from_string(expected_file)
        )

    def test_jo_sales_refund(self):
        self.company.l10n_jo_edi_taxpayer_type = 'sales'

        move_lines = [
            {
                'product_id': self.product_a,
                'price': 10,
                'quantity': 100,
                'discount_percent': 10,
                'taxes': [self.jo_general_tax_10],
            },
        ]
        self.company.l10n_jo_edi_sequence_income_source = '16683693'
        move = self._create_invoice(name='TestEIN022R',
                                    type='refund',
                                    date='2023-11-10',
                                    lines=move_lines)
        move.ref = 'Test/Return'
        move.reversed_entry_id = self._create_invoice(name='TestEIN022',
                                                      type='invoice',
                                                      date='2022-09-05',
                                                      lines=move_lines)

        expected_file = self._read_xml_test_file(4)
        generated_file = self.env['account.edi.xml.ubl_21.jo']._export_invoice(move)

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(generated_file),
            self.get_xml_tree_from_string(expected_file)
        )

    def test_jo_sales_refund_usd(self):
        """
        same test as above, but with price divided over 2
        the division would compensate for the USD exchange rate
        """
        self.company.l10n_jo_edi_taxpayer_type = 'sales'

        move_lines = [
            {
                'product_id': self.product_a,
                'price': 5,
                'quantity': 100,
                'discount_percent': 10,
                'taxes': [self.jo_general_tax_10],
            },
        ]
        self.company.l10n_jo_edi_sequence_income_source = '16683693'
        move = self._create_invoice(name='TestEIN022R',
                                    type='refund',
                                    date='2023-11-10',
                                    lines=move_lines,
                                    currency=self.usd)
        move.ref = 'Test/Return'
        move.reversed_entry_id = self._create_invoice(name='TestEIN022',
                                                      type='invoice',
                                                      date='2022-09-05',
                                                      lines=move_lines,
                                                      currency=self.usd)

        expected_file = self._read_xml_test_file(4)
        generated_file = self.env['account.edi.xml.ubl_21.jo']._export_invoice(move)

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(generated_file),
            self.get_xml_tree_from_string(expected_file)
        )

    def test_jo_special_invoice(self):
        self.company.l10n_jo_edi_taxpayer_type = 'special'

        move_lines = [
            {
                'product_id': self.product_b,
                'price': 100,
                'quantity': 1,
                'discount_percent': 0,
                'taxes': [self.jo_general_tax_10, self.jo_special_tax_10],
            },
        ]
        self.company.l10n_jo_edi_sequence_income_source = '16683696'
        move = self._create_invoice(name='TestEIN013',
                                    type='invoice',
                                    date='2023-11-10',
                                    lines=move_lines)

        expected_file = self._read_xml_test_file(5)
        generated_file = self.env['account.edi.xml.ubl_21.jo']._export_invoice(move)

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(generated_file),
            self.get_xml_tree_from_string(expected_file)
        )

    def test_jo_special_refund(self):
        self.company.l10n_jo_edi_taxpayer_type = 'special'

        move_lines = [
            {
                'product_id': self.product_b,
                'price': 100,
                'quantity': 1,
                'discount_percent': 0,
                'taxes': [self.jo_general_tax_10, self.jo_special_tax_10],
            },
        ]
        self.company.l10n_jo_edi_sequence_income_source = '16683696'
        move = self._create_invoice(name='TestEINReturn013',
                                    type='refund',
                                    date='2023-11-10',
                                    lines=move_lines)
        move.ref = 'Test Return'
        move.reversed_entry_id = self._create_invoice(name='TestEIN013',
                                                      type='invoice',
                                                      date='2022-08-20',
                                                      lines=move_lines)

        expected_file = self._read_xml_test_file(6)
        generated_file = self.env['account.edi.xml.ubl_21.jo']._export_invoice(move)

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(generated_file),
            self.get_xml_tree_from_string(expected_file)
        )

    def test_jo_special_refund_usd(self):
        self.company.l10n_jo_edi_taxpayer_type = 'special'

        move_lines = [
            {
                'product_id': self.product_b,
                'price': 50,
                'quantity': 1,
                'discount_percent': 0,
                'taxes': [self.jo_general_tax_10, self.jo_special_tax_5],
            },
        ]
        self.company.l10n_jo_edi_sequence_income_source = '16683696'
        move = self._create_invoice(name='TestEINReturn013',
                                    type='refund',
                                    date='2023-11-10',
                                    lines=move_lines,
                                    currency=self.usd)
        move.ref = 'Test Return'
        move.reversed_entry_id = self._create_invoice(name='TestEIN013',
                                                      type='invoice',
                                                      date='2022-08-20',
                                                      lines=move_lines,
                                                      currency=self.usd)

        expected_file = self._read_xml_test_file(6)
        generated_file = self.env['account.edi.xml.ubl_21.jo']._export_invoice(move)

        self.assertXmlTreeEqual(
            self.get_xml_tree_from_string(generated_file),
            self.get_xml_tree_from_string(expected_file)
        )
