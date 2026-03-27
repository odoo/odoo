from odoo.addons.account.tests.common import TestTaxCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestTaxesDispatchingBaseLines(TestTaxCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.currency = cls.env.company.currency_id
        cls.foreign_currency = cls.setup_other_currency('EUR')

    def test_dispatch_return_of_merchandise_lines(self):
        self.env.company.tax_calculation_rounding_method = 'round_globally'
        AccountTax = self.env['account.tax']
        tax1 = self.fixed_tax(1, include_base_amount=True)
        tax2 = self.percent_tax(21)
        taxes = tax1 + tax2

        document_params = self.init_document(
            lines=[
                {'product_id': self.product_a, 'price_unit': 16.79, 'quantity': 10, 'tax_ids': taxes},
                {'product_id': self.product_a, 'price_unit': 16.79, 'quantity': 10, 'tax_ids': taxes},
                {'product_id': self.product_a, 'price_unit': 16.79, 'quantity': -12, 'tax_ids': taxes},
            ],
            currency=self.foreign_currency,
            rate=0.5,
        )
        expected_values = {
            'same_tax_base': True,
            'currency_id': self.foreign_currency.id,
            'company_currency_id': self.currency.id,
            'base_amount_currency': 134.32,
            'base_amount': 268.64,
            'tax_amount_currency': 37.89,
            'tax_amount': 75.77,
            'total_amount_currency': 172.21,
            'total_amount': 344.41,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 134.32,
                    'base_amount': 268.64,
                    'tax_amount_currency': 37.89,
                    'tax_amount': 75.77,
                    'tax_groups': [
                        {
                            'id': taxes.tax_group_id.id,
                            'base_amount_currency': 134.32,
                            'base_amount': 268.64,
                            'tax_amount_currency': 37.89,
                            'tax_amount': 75.77,
                            'display_base_amount_currency': 134.32,
                            'display_base_amount': 268.64,
                        },
                    ],
                },
            ],
        }
        document = self.populate_document(document_params)
        base_lines = document['lines']
        tax_totals = AccountTax._get_tax_totals_summary(base_lines, document['currency'], self.env.company)
        self._assert_tax_totals_summary(tax_totals, expected_values)

        # Dispatch the return of product on the others base lines.
        self.assertEqual(len(base_lines), 3)
        base_lines = AccountTax._dispatch_return_of_merchandise_lines(document['lines'], self.env.company)
        AccountTax._squash_return_of_merchandise_lines(base_lines, self.env.company)
        self.assertEqual(len(base_lines), 2)
        self.assertEqual(base_lines[0]['quantity'], 0)
        self.assertEqual(base_lines[1]['quantity'], 8)
        tax_totals = AccountTax._get_tax_totals_summary(base_lines, document['currency'], self.env.company)
        self._assert_tax_totals_summary(tax_totals, expected_values)

    def test_dispatch_return_of_merchandise_lines_no_match(self):
        self.env.company.tax_calculation_rounding_method = 'round_globally'
        AccountTax = self.env['account.tax']
        tax = self.percent_tax(21)

        document_params = self.init_document(
            lines=[
                {'product_id': self.product_a, 'price_unit': 16.79, 'quantity': 10, 'tax_ids': tax},
                {'product_id': self.product_a, 'price_unit': 16.79, 'quantity': -2, 'tax_ids': []},
            ],
        )
        expected_values = {
            'same_tax_base': False,
            'currency_id': self.currency.id,
            'base_amount_currency': 134.32,
            'tax_amount_currency': 35.26,
            'total_amount_currency': 169.58,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 134.32,
                    'tax_amount_currency': 35.26,
                    'tax_groups': [
                        {
                            'id': tax.tax_group_id.id,
                            'base_amount_currency': 167.9,
                            'tax_amount_currency': 35.26,
                            'display_base_amount_currency': 167.9,
                        },
                    ],
                },
            ],
        }
        document = self.populate_document(document_params)
        base_lines = document['lines']
        tax_totals = AccountTax._get_tax_totals_summary(base_lines, document['currency'], self.env.company)
        self._assert_tax_totals_summary(tax_totals, expected_values)

        # Dispatch the return of product on the others base lines.
        # The dispatching should fail so no changes.
        self.assertEqual(len(base_lines), 2)
        base_lines = AccountTax._dispatch_return_of_merchandise_lines(document['lines'], self.env.company)
        AccountTax._squash_return_of_merchandise_lines(base_lines, self.env.company)
        self.assertEqual(len(base_lines), 2)
        tax_totals = AccountTax._get_tax_totals_summary(base_lines, document['currency'], self.env.company)
        self._assert_tax_totals_summary(tax_totals, expected_values)

    def test_dispatch_global_discount_lines(self):
        self.env.company.tax_calculation_rounding_method = 'round_globally'
        AccountTax = self.env['account.tax']
        tax1 = self.fixed_tax(1, include_base_amount=True)
        tax2 = self.percent_tax(21)
        taxes = tax1 + tax2

        document_params = self.init_document(
            lines=[
                {'product_id': self.product_a, 'price_unit': 33.58, 'quantity': 10, 'tax_ids': taxes},
                {'product_id': self.product_a, 'price_unit': 16.79, 'quantity': 10, 'tax_ids': taxes},
            ],
            currency=self.foreign_currency,
            rate=0.5,
        )
        expected_values = {
            'same_tax_base': True,
            'currency_id': self.foreign_currency.id,
            'company_currency_id': self.currency.id,
            'base_amount_currency': 503.7,
            'base_amount': 1007.4,
            'tax_amount_currency': 129.98,
            'tax_amount': 259.95,
            'total_amount_currency': 633.68,
            'total_amount': 1267.35,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 503.7,
                    'base_amount': 1007.4,
                    'tax_amount_currency': 129.98,
                    'tax_amount': 259.95,
                    'tax_groups': [
                        {
                            'id': taxes.tax_group_id.id,
                            'base_amount_currency': 503.7,
                            'base_amount': 1007.4,
                            'tax_amount_currency': 129.98,
                            'tax_amount': 259.95,
                            'display_base_amount_currency': 503.7,
                            'display_base_amount': 1007.4,
                        },
                    ],
                },
            ],
        }
        document = self.populate_document(document_params)
        base_lines = document['lines']
        tax_totals = AccountTax._get_tax_totals_summary(base_lines, document['currency'], self.env.company)
        self._assert_tax_totals_summary(tax_totals, expected_values)

        # Global discount 20%.
        discount_base_lines = AccountTax._prepare_global_discount_lines(base_lines, self.env.company, 'percent', 20.0)
        base_lines += discount_base_lines
        AccountTax._add_tax_details_in_base_lines(base_lines, self.env.company)
        AccountTax._round_base_lines_tax_details(base_lines, self.env.company)
        tax_totals = AccountTax._get_tax_totals_summary(base_lines, document['currency'], self.env.company)
        expected_values = {
            'same_tax_base': True,
            'currency_id': self.foreign_currency.id,
            'company_currency_id': self.currency.id,
            'base_amount_currency': 402.96,
            'base_amount': 805.92,
            'tax_amount_currency': 108.82,
            'tax_amount': 217.64,
            'total_amount_currency': 511.78,
            'total_amount': 1023.56,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 402.96,
                    'base_amount': 805.92,
                    'tax_amount_currency': 108.82,
                    'tax_amount': 217.64,
                    'tax_groups': [
                        {
                            'id': taxes.tax_group_id.id,
                            'base_amount_currency': 402.96,
                            'base_amount': 805.92,
                            'tax_amount_currency': 108.82,
                            'tax_amount': 217.64,
                            'display_base_amount_currency': 402.96,
                            'display_base_amount': 805.92,
                        },
                    ],
                },
            ],
        }
        self._assert_tax_totals_summary(tax_totals, expected_values)

        # Dispatch the global discount on the others base lines.
        self.assertEqual(len(base_lines), 3)
        base_lines[-1]['special_type'] = 'global_discount'
        base_lines = AccountTax._dispatch_global_discount_lines(base_lines, self.env.company)
        AccountTax._squash_global_discount_lines(base_lines, self.env.company)
        self.assertEqual(len(base_lines), 2)
        tax_totals = AccountTax._get_tax_totals_summary(base_lines, document['currency'], self.env.company)
        self._assert_tax_totals_summary(tax_totals, expected_values)

    def test_dispatch_global_discount_lines_no_match(self):
        self.env.company.tax_calculation_rounding_method = 'round_globally'
        AccountTax = self.env['account.tax']
        tax = self.percent_tax(21)

        document_params = self.init_document(
            lines=[
                {'product_id': self.product_a, 'price_unit': 33.58, 'quantity': 10, 'tax_ids': tax},
                {'product_id': self.product_a, 'price_unit': 16.79, 'quantity': 10, 'tax_ids': tax},
                {'product_id': self.product_a, 'price_unit': -50.0, 'quantity': 1, 'tax_ids': [], 'special_type': 'global_discount'},
            ],
        )
        document = self.populate_document(document_params)
        base_lines = document['lines']

        # Should fail to dispatch the global discount on the others base lines.
        self.assertEqual(len(base_lines), 3)
        base_lines = AccountTax._dispatch_global_discount_lines(base_lines, self.env.company)
        AccountTax._squash_global_discount_lines(base_lines, self.env.company)
        self.assertEqual(len(base_lines), 3)

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
        self.env.company.tax_calculation_rounding_method = 'round_globally'
        tax1 = self.fixed_tax(1, include_base_amount=True)
        tax2 = self.fixed_tax(5)
        tax3 = self.percent_tax(21)
        taxes = tax1 + tax2 + tax3

        document_params = self.init_document(
            lines=[
                {'price_unit': 16.79, 'tax_ids': taxes},
                {'price_unit': 16.79, 'tax_ids': taxes},
            ],
            currency=self.foreign_currency,
            rate=0.5,
        )
        document = self.populate_document(document_params)

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
            exclude_function=lambda base_line, tax_data: tax_data['tax'] == tax3,
            expected_values={
                **expected_values,
                'base_amount_currency': 41.05,
                'tax_amount_currency': 12.0,
            },
        )

        taxes.price_include_override = 'tax_included'

        document_params = self.init_document(
            lines=[
                {'price_unit': 21.53, 'tax_ids': taxes},
                {'price_unit': 21.53, 'tax_ids': taxes},
            ],
            currency=self.foreign_currency,
            rate=0.5,
        )
        document = self.populate_document(document_params)

        expected_values = {
            'base_amount_currency': 25.32,
            'tax_amount_currency': 17.74,
            'total_amount_currency': 43.06,
        }
        self.assert_tax_totals_summary(document, expected_values, soft_checking=True)

        assert_tax_totals_summary_after_dispatching(
            document=document,
            exclude_function=lambda base_line, tax_data: tax_data['tax'] == tax1,
            expected_values={
                **expected_values,
                'base_amount_currency': 27.32,
                'tax_amount_currency': 15.74,
            },
        )
        assert_tax_totals_summary_after_dispatching(
            document=document,
            exclude_function=lambda base_line, tax_data: tax_data['tax'] == tax2,
            expected_values={
                **expected_values,
                'base_amount_currency': 35.32,
                'tax_amount_currency': 7.74,
            },
        )
        assert_tax_totals_summary_after_dispatching(
            document=document,
            exclude_function=lambda base_line, tax_data: tax_data['tax'] == tax3,
            expected_values={
                **expected_values,
                'base_amount_currency': 31.06,
                'tax_amount_currency': 12.0,
            },
        )
