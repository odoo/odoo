from odoo.addons.account.tests.common import TestTaxCommon
from odoo.tests import tagged

import copy


@tagged('post_install', '-at_install')
class TestTaxesDispatchingBaseLines(TestTaxCommon):

    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.currency = cls.env.company.currency_id
        cls.foreign_currency = cls.setup_other_currency('EUR')

    def test_dispatch_return_of_merchandise_lines(self):
        AccountTax = self.env['account.tax']
        tax1 = self.fixed_tax(1, include_base_amount=True)
        tax2 = self.percent_tax(21)
        taxes = tax1 + tax2

        document = self.populate_document(self.init_document(
            lines=[
                {'product_id': self.product_a, 'price_unit': 16.79, 'quantity': 10, 'tax_ids': taxes},
                {'product_id': self.product_a, 'price_unit': 16.79, 'quantity': 10, 'tax_ids': taxes},
                {'product_id': self.product_a, 'price_unit': 16.79, 'quantity': -12, 'tax_ids': taxes},
            ],
        ))
        AccountTax._add_tax_details(document['lines'], self.env.company)

        expected_base_line_tax_details_values_1_2_common = {
            'raw_total_excluded_currency': 167.9,
            'raw_total_included_currency': 215.259,
            'total_excluded_currency': 167.9,
            'total_included_currency': 215.26,
            'delta_total_excluded_currency': 0.0,
            'taxes_data': [
                {
                    'tax_id': tax1.id,
                    'raw_base_amount_currency': 167.9,
                    'raw_tax_amount_currency': 10.0,
                    'base_amount_currency': 167.9,
                    'tax_amount_currency': 10.0,
                },
                {
                    'tax_id': tax2.id,
                    'raw_base_amount_currency': 177.9,
                    'raw_tax_amount_currency': 37.359,
                    'base_amount_currency': 177.9,
                    'tax_amount_currency': 37.36,
                },
            ],
        }
        expected_base_line_tax_details_values_1 = expected_base_line_tax_details_values_1_2_common
        expected_base_line_tax_details_values_2 = expected_base_line_tax_details_values_1_2_common
        expected_base_line_tax_details_values_3 = {
            'raw_total_excluded_currency': -201.48,
            'raw_total_included_currency': -258.3108,
            'total_excluded_currency': -201.48,
            'total_included_currency': -258.31,
            'delta_total_excluded_currency': 0.0,
            'taxes_data': [
                {
                    'tax_id': tax1.id,
                    'raw_base_amount_currency': -201.48,
                    'raw_tax_amount_currency': -12.0,
                    'base_amount_currency': -201.48,
                    'tax_amount_currency': -12.0,
                },
                {
                    'tax_id': tax2.id,
                    'raw_base_amount_currency': -213.48,
                    'raw_tax_amount_currency': -44.8308,
                    'base_amount_currency': -213.48,
                    'tax_amount_currency': -44.83,
                },
            ],
        }
        self.assert_base_lines_tax_details(
            document=document,
            expected_base_lines_tax_details=[
                expected_base_line_tax_details_values_1,
                expected_base_line_tax_details_values_2,
                expected_base_line_tax_details_values_3,
            ],
            expected_base_amount=134.32,
            expected_tax_amount=37.89,
            expected_total_amount=172.21,
        )

        # Dispatch the return of product on the others base lines.
        base_lines = AccountTax._dispatch_return_of_merchandise_lines(document['lines'], self.env.company)
        AccountTax._squash_return_of_merchandise_lines(base_lines, self.env.company)
        self.assertEqual(len(base_lines), 2)
        self.assertEqual(base_lines[0]['quantity'], 0)
        self.assertEqual(base_lines[1]['quantity'], 8)
        new_document = copy.deepcopy(document)
        new_document['lines'] = base_lines

        expected_base_line_tax_details_values_1 = {
            'raw_total_excluded_currency': 0.0,
            'raw_total_included_currency': 0.0,
            'total_excluded_currency': 0.0,
            'total_included_currency': 0.0,
            'delta_total_excluded_currency': 0.0,
            'taxes_data': [
                {
                    'tax_id': tax1.id,
                    'raw_base_amount_currency': 0.0,
                    'raw_tax_amount_currency': 0.0,
                    'base_amount_currency': 0.0,
                    'tax_amount_currency': 0.0,
                },
                {
                    'tax_id': tax2.id,
                    'raw_base_amount_currency': 0.0,
                    'raw_tax_amount_currency': 0.0,
                    'base_amount_currency': 0.0,
                    'tax_amount_currency': 0.0,
                },
            ],
        }
        expected_base_line_tax_details_values_2 = {
            'raw_total_excluded_currency': 134.32,
            'raw_total_included_currency': 172.2072,
            'total_excluded_currency': 134.32,
            'total_included_currency': 172.21,
            'delta_total_excluded_currency': 0.0,
            'taxes_data': [
                {
                    'tax_id': tax1.id,
                    'raw_base_amount_currency': 134.32,
                    'raw_tax_amount_currency': 8.0,
                    'base_amount_currency': 134.32,
                    'tax_amount_currency': 8.0,
                },
                {
                    'tax_id': tax2.id,
                    'raw_base_amount_currency': 142.32,
                    'raw_tax_amount_currency': 29.8872,
                    'base_amount_currency': 142.32,
                    'tax_amount_currency': 29.89,
                },
            ],
        }
        self.assert_base_lines_tax_details(
            document=new_document,
            expected_base_lines_tax_details=[
                expected_base_line_tax_details_values_1,
                expected_base_line_tax_details_values_2,
            ],
            expected_base_amount=134.32,
            expected_tax_amount=37.89,
            expected_total_amount=172.21,
        )

    def test_dispatch_return_of_merchandise_lines_no_match(self):
        AccountTax = self.env['account.tax']
        tax = self.percent_tax(21)

        document = self.populate_document(self.init_document(
            lines=[
                {'product_id': self.product_a, 'price_unit': 16.79, 'quantity': 10, 'tax_ids': tax},
                {'product_id': self.product_a, 'price_unit': 16.79, 'quantity': -2, 'tax_ids': []},
            ],
        ))
        AccountTax._add_tax_details(document['lines'], self.env.company)

        # Dispatch the return of product on the others base lines.
        # The dispatching should fail so no changes.
        base_lines = AccountTax._dispatch_return_of_merchandise_lines(document['lines'], self.env.company)
        self.assertEqual(len(base_lines), 2)

    def test_dispatch_global_discount_lines(self):
        AccountTax = self.env['account.tax']
        tax1 = self.fixed_tax(1, include_base_amount=True)
        tax2 = self.percent_tax(21)
        taxes = tax1 + tax2

        document = self.populate_document(self.init_document(
            lines=[
                {'product_id': self.product_a, 'price_unit': 33.58, 'quantity': 10, 'tax_ids': taxes},
                {'product_id': self.product_a, 'price_unit': 16.79, 'quantity': 10, 'tax_ids': taxes},
            ],
        ))
        AccountTax._add_tax_details(document['lines'], self.env.company)

        expected_base_line_tax_details_values_1 = {
            'raw_total_excluded_currency': 335.8,
            'raw_total_included_currency': 418.418,
            'total_excluded_currency': 335.8,
            'total_included_currency': 418.42,
            'delta_total_excluded_currency': 0.0,
            'taxes_data': [
                {
                    'tax_id': tax1.id,
                    'raw_base_amount_currency': 335.8,
                    'raw_tax_amount_currency': 10.0,
                    'base_amount_currency': 335.8,
                    'tax_amount_currency': 10.0,
                },
                {
                    'tax_id': tax2.id,
                    'raw_base_amount_currency': 345.8,
                    'raw_tax_amount_currency': 72.618,
                    'base_amount_currency': 345.8,
                    'tax_amount_currency': 72.62,
                },
            ],
        }
        expected_base_line_tax_details_values_2 = {
            'raw_total_excluded_currency': 167.9,
            'raw_total_included_currency': 215.259,
            'total_excluded_currency': 167.9,
            'total_included_currency': 215.26,
            'delta_total_excluded_currency': 0.0,
            'taxes_data': [
                {
                    'tax_id': tax1.id,
                    'raw_base_amount_currency': 167.9,
                    'raw_tax_amount_currency': 10.0,
                    'base_amount_currency': 167.9,
                    'tax_amount_currency': 10.0,
                },
                {
                    'tax_id': tax2.id,
                    'raw_base_amount_currency': 177.9,
                    'raw_tax_amount_currency': 37.359,
                    'base_amount_currency': 177.9,
                    'tax_amount_currency': 37.36,
                },
            ],
        }
        self.assert_base_lines_tax_details(
            document=document,
            expected_base_lines_tax_details=[expected_base_line_tax_details_values_1, expected_base_line_tax_details_values_2],
            expected_base_amount=503.7,
            expected_tax_amount=129.98,
            expected_total_amount=633.68,
        )

        # Global discount 20%.
        base_lines = document['lines']
        discount_base_lines = AccountTax._prepare_global_discount_lines(base_lines, self.env.company, 'percent', 20.0)
        new_document = copy.deepcopy(document)
        new_document['lines'] += discount_base_lines

        expected_base_line_tax_details_values_3 = {
            'raw_total_excluded_currency': -100.74,
            'raw_total_included_currency': -121.8954,
            'total_excluded_currency': -100.74,
            'total_included_currency': -121.9,
            'delta_total_excluded_currency': 0.0,
            'taxes_data': [
                {
                    'tax_id': tax2.id,
                    'raw_base_amount_currency': -100.74,
                    'raw_tax_amount_currency': -21.1554,
                    'base_amount_currency': -100.74,
                    'tax_amount_currency': -21.16,
                },
            ],
        }
        self.assert_base_lines_tax_details(
            document=new_document,
            expected_base_lines_tax_details=[
                expected_base_line_tax_details_values_1,
                expected_base_line_tax_details_values_2,
                expected_base_line_tax_details_values_3,
            ],
            expected_base_amount=402.96,
            expected_tax_amount=108.82,
            expected_total_amount=511.78,
        )

        # Dispatch the global discount on the others base lines.
        base_lines = new_document['lines']
        base_lines[-1]['special_type'] = 'global_discount'
        base_lines = AccountTax._dispatch_global_discount_lines(base_lines, self.env.company)
        AccountTax._squash_global_discount_lines(base_lines, self.env.company)
        self.assertEqual(len(base_lines), 2)
        new_document = copy.deepcopy(document)
        new_document['lines'] = base_lines
        AccountTax._add_tax_details(new_document['lines'], self.env.company)

        expected_base_line_tax_details_values_1 = {
            'raw_total_excluded_currency': 335.8,
            'raw_total_included_currency': 404.4490534275348,
            'total_excluded_currency': 268.64,
            'total_included_currency': 337.15,
            'delta_total_excluded_currency': 0.0,
            'taxes_data': [
                {
                    'tax_id': tax1.id,
                    'raw_base_amount_currency': 335.8,
                    'raw_tax_amount_currency': 10.0,
                    'base_amount_currency': 268.64,
                    'tax_amount_currency': 10.0,
                },
                {
                    'tax_id': tax2.id,
                    'raw_base_amount_currency': 345.8,
                    'raw_tax_amount_currency': 58.649053427534845,
                    'base_amount_currency': 278.64,
                    'tax_amount_currency': 58.51,
                },
            ],
        }
        expected_base_line_tax_details_values_2 = {
            'raw_total_excluded_currency': 167.9,
            'raw_total_included_currency': 208.07254657246511,
            'total_excluded_currency': 134.32,
            'total_included_currency': 174.63,
            'delta_total_excluded_currency': 0.0,
            'taxes_data': [
                {
                    'tax_id': tax1.id,
                    'raw_base_amount_currency': 167.9,
                    'raw_tax_amount_currency': 10.0,
                    'base_amount_currency': 134.32,
                    'tax_amount_currency': 10.0,
                },
                {
                    'tax_id': tax2.id,
                    'raw_base_amount_currency': 177.9,
                    'raw_tax_amount_currency': 30.17254657246515,
                    'base_amount_currency': 144.32,
                    'tax_amount_currency': 30.31,
                },
            ],
        }
        self.assert_base_lines_tax_details(
            document=new_document,
            expected_base_lines_tax_details=[
                expected_base_line_tax_details_values_1,
                expected_base_line_tax_details_values_2,
            ],
            expected_base_amount=402.96,
            expected_tax_amount=108.82,
            expected_total_amount=511.78,
        )

    def test_dispatch_global_discount_lines_no_match(self):
        self.env.company.tax_calculation_rounding_method = 'round_globally'
        AccountTax = self.env['account.tax']
        tax = self.percent_tax(21)

        document = self.populate_document(self.init_document(
            lines=[
                {'product_id': self.product_a, 'price_unit': 33.58, 'quantity': 10, 'tax_ids': tax},
                {'product_id': self.product_a, 'price_unit': 16.79, 'quantity': 10, 'tax_ids': tax},
                {'product_id': self.product_a, 'price_unit': -50.0, 'quantity': 1, 'tax_ids': [], 'special_type': 'global_discount'},
            ],
        ))
        AccountTax._add_tax_details(document['lines'], self.env.company)
        base_lines = document['lines']

        # Should fail to dispatch the global discount on the others base lines.
        self.assertEqual(len(base_lines), 3)
        base_lines = AccountTax._dispatch_global_discount_lines(base_lines, self.env.company)
        AccountTax._squash_global_discount_lines(base_lines, self.env.company)
        self.assertEqual(len(base_lines), 3)

    def test_dispatch_global_discount_lines_raw_gross_total_excluded_and_discount(self):
        AccountTax = self.env['account.tax']
        company = self.env.company

        document = self.populate_document(self.init_document(lines=[
            {'price_unit': 100.0, 'quantity': 1.0, 'discount': 10.0},
            {'price_unit': -10.0, 'quantity': 1.0, 'special_type': 'global_discount'},
        ]))
        expected_base_line_tax_details_values_1 = {
            'raw_total_excluded_currency': 90.0,
            'raw_total_included_currency': 90.0,
            'total_excluded_currency': 90.0,
            'total_included_currency': 90.0,
            'delta_total_excluded_currency': 0.0,
            'taxes_data': [],
        }
        expected_base_line_tax_details_values_2 = {
            'raw_total_excluded_currency': -10.0,
            'raw_total_included_currency': -10.0,
            'total_excluded_currency': -10.0,
            'total_included_currency': -10.0,
            'delta_total_excluded_currency': 0.0,
            'taxes_data': [],
        }
        self.assert_base_lines_tax_details(
            document=document,
            expected_base_lines_tax_details=[
                expected_base_line_tax_details_values_1,
                expected_base_line_tax_details_values_2,
            ],
            expected_base_amount=80.0,
            expected_tax_amount=0.0,
            expected_total_amount=80.0,
        )

        base_lines = AccountTax._dispatch_global_discount_lines(document['lines'], company)
        AccountTax._squash_global_discount_lines(base_lines, company)
        new_document = copy.deepcopy(document)
        new_document['lines'] = base_lines
        self.assert_base_lines_tax_details(
            document=new_document,
            expected_base_lines_tax_details=[{
                'raw_total_excluded_currency': 80.0,
                'raw_total_included_currency': 80.0,
                'total_excluded_currency': 80.0,
                'total_included_currency': 80.0,
                'delta_total_excluded_currency': 0.0,
                'taxes_data': [],
            }],
            expected_base_amount=80.0,
            expected_tax_amount=0.0,
            expected_total_amount=80.0,
        )
        base_line = base_lines[0]
        self.assertEqual(base_line['price_unit'], 100.0)

        raw_gross_total_excluded_currency = AccountTax._get_gross_total_without_tax(base_line, company)
        self.assertEqual(raw_gross_total_excluded_currency, 100.0)

        raw_gross_price_unit_currency = AccountTax._get_price_unit_without_tax(base_line, company, raw_gross_total_excluded_currency)
        self.assertEqual(raw_gross_price_unit_currency, 100.0)

        raw_discount_amount_currency = AccountTax._get_discount_amount_without_tax(base_line, company, raw_gross_total_excluded_currency)
        self.assertEqual(raw_discount_amount_currency, 20.0)

    def test_dispatch_taxes_into_new_base_lines(self):

        def assert_tax_totals_summary_after_dispatching(document, exclude_function, expected_values):
            new_base_lines = AccountTax._dispatch_taxes_into_new_base_lines(
                base_lines=document['lines'],
                company=self.env.company,
                exclude_function=exclude_function,
            )

            extra_base_lines = AccountTax._turn_removed_taxes_into_new_base_lines(new_base_lines, self.env.company)
            self.assert_tax_totals_summary(
                document={
                    **document,
                    'lines': new_base_lines + extra_base_lines,
                },
                expected_values=expected_values,
                soft_checking=True,
            )

        AccountTax = self.env['account.tax']
        tax1 = self.fixed_tax(1, include_base_amount=True)
        tax2 = self.fixed_tax(5)
        tax3 = self.percent_tax(21)
        taxes = tax1 + tax2 + tax3

        document = self.populate_document(self.init_document(
            lines=[
                {'price_unit': 16.79, 'tax_ids': taxes},
                {'price_unit': 16.79, 'tax_ids': taxes},
            ],
            currency=self.foreign_currency,
            rate=0.5,
        ))
        AccountTax._add_tax_details(document['lines'], self.env.company)

        expected_values = {
            'base_amount_currency': 33.58,
            'tax_amount_currency': 19.47,
            'total_amount_currency': 53.05,
        }
        self.assert_tax_totals_summary(document, expected_values, soft_checking=True)

        assert_tax_totals_summary_after_dispatching(
            document=document,
            exclude_function=lambda base_line, tax_data: tax_data['tax'] == tax1,
            expected_values={
                **expected_values,
                'base_amount_currency': 35.58,
                'tax_amount_currency': 17.47,
            },
        )
        assert_tax_totals_summary_after_dispatching(
            document=document,
            exclude_function=lambda base_line, tax_data: tax_data['tax'] == tax2,
            expected_values={
                **expected_values,
                'base_amount_currency': 43.58,
                'tax_amount_currency': 9.47,
            },
        )
        assert_tax_totals_summary_after_dispatching(
            document=document,
            exclude_function=lambda base_line, tax_data: tax_data['tax'] in (tax1, tax2),
            expected_values={
                **expected_values,
                'base_amount_currency': 45.58,
                'tax_amount_currency': 7.47,
            },
        )
        assert_tax_totals_summary_after_dispatching(
            document=document,
            exclude_function=lambda base_line, tax_data: tax_data['tax'] == tax3,
            expected_values={
                **expected_values,
                'base_amount_currency': 41.05,
                'tax_amount_currency': 12.0,
            },
        )

        taxes = tax1 + tax3
        taxes.price_include_override = 'tax_included'

        document = self.populate_document(self.init_document(
            lines=[
                {'price_unit': 21.53, 'tax_ids': taxes},
                {'price_unit': 21.53, 'tax_ids': taxes},
            ],
            currency=self.foreign_currency,
            rate=0.5,
        ))
        AccountTax._add_tax_details(document['lines'], self.env.company)

        expected_values = {
            'base_amount_currency': 33.59,
            'tax_amount_currency': 9.47,
            'total_amount_currency': 43.06,
        }
        self.assert_tax_totals_summary(document, expected_values, soft_checking=True)

        assert_tax_totals_summary_after_dispatching(
            document=document,
            exclude_function=lambda base_line, tax_data: tax_data['tax'] == tax1,
            expected_values={
                **expected_values,
                'base_amount_currency': 35.59,
                'tax_amount_currency': 7.47,
            },
        )
        assert_tax_totals_summary_after_dispatching(
            document=document,
            exclude_function=lambda base_line, tax_data: True,
            expected_values={
                **expected_values,
                'base_amount_currency': 43.06,
                'tax_amount_currency': 0.0,
            },
        )
