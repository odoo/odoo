from contextlib import contextmanager

from odoo import Command
from odoo.addons.account.tests.common import TestTaxCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestTaxesTaxTotalsSummary(TestTaxCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.currency = cls.env.company.currency_id
        cls.foreign_currency = cls.setup_other_currency('EUR')
        cls.tax_groups = cls.env['account.tax.group'].create([
            {'name': str(i), 'sequence': str(i)}
            for i in range(1, 10)
        ])

    @contextmanager
    def same_tax_group(self, taxes):
        taxes.tax_group_id = self.tax_groups[0]
        yield

    @contextmanager
    def different_tax_group(self, taxes):
        for i, tax in enumerate(taxes):
            tax.tax_group_id = self.tax_groups[i]
        yield

    def _test_taxes_l10n_in(self):
        tax1 = self.percent_tax(6, include_base_amount=True)
        tax2 = self.percent_tax(6, include_base_amount=True, is_base_affected=False)
        tax3 = self.percent_tax(3)
        taxes = tax1 + tax2 + tax3

        document_params = self.init_document(
            lines=[
                {'price_unit': 15.89, 'tax_ids': taxes},
                {'price_unit': 15.89, 'tax_ids': taxes},
            ],
            currency=self.foreign_currency,
            rate=5.0,
        )
        with self.same_tax_group(taxes):
            with self.with_tax_calculation_rounding_method('round_per_line'):
                expected_values = {
                    'same_tax_base': True,
                    'currency_id': self.foreign_currency.id,
                    'company_currency_id': self.currency.id,
                    'base_amount_currency': 31.78,
                    'base_amount': 6.36,
                    'tax_amount_currency': 4.86,
                    'tax_amount': 0.98,
                    'total_amount_currency': 36.64,
                    'total_amount': 7.34,
                    'subtotals': [
                        {
                            'name': "Untaxed Amount",
                            'base_amount_currency': 31.78,
                            'base_amount': 6.36,
                            'tax_amount_currency': 4.86,
                            'tax_amount': 0.98,
                            'tax_groups': [
                                {
                                    'id': self.tax_groups[0].id,
                                    'base_amount_currency': 31.78,
                                    'base_amount': 6.36,
                                    'tax_amount_currency': 4.86,
                                    'tax_amount': 0.98,
                                    'display_base_amount_currency': 31.78,
                                    'display_base_amount': 6.36,
                                },
                            ],
                        },
                    ],
                }
                yield 1, self.populate_document(document_params), expected_values
            with self.with_tax_calculation_rounding_method('round_globally'):
                expected_values = {
                    'same_tax_base': True,
                    'currency_id': self.foreign_currency.id,
                    'company_currency_id': self.currency.id,
                    'base_amount_currency': 31.78,
                    'base_amount': 6.36,
                    'tax_amount_currency': 4.89,
                    'tax_amount': 0.97,
                    'total_amount_currency': 36.67,
                    'total_amount': 7.33,
                    'subtotals': [
                        {
                            'name': "Untaxed Amount",
                            'base_amount_currency': 31.78,
                            'base_amount': 6.36,
                            'tax_amount_currency': 4.89,
                            'tax_amount': 0.97,
                            'tax_groups': [
                                {
                                    'id': self.tax_groups[0].id,
                                    'base_amount_currency': 31.78,
                                    'base_amount': 6.36,
                                    'tax_amount_currency': 4.89,
                                    'tax_amount': 0.97,
                                    'display_base_amount_currency': 31.78,
                                    'display_base_amount': 6.36,
                                },
                            ],
                        },
                    ],
                }
                yield 2, self.populate_document(document_params), expected_values
        with self.different_tax_group(taxes):
            with self.with_tax_calculation_rounding_method('round_per_line'):
                expected_values = {
                    'same_tax_base': False,
                    'currency_id': self.foreign_currency.id,
                    'company_currency_id': self.currency.id,
                    'base_amount_currency': 31.78,
                    'base_amount': 6.36,
                    'tax_amount_currency': 4.86,
                    'tax_amount': 0.98,
                    'total_amount_currency': 36.64,
                    'total_amount': 7.34,
                    'subtotals': [
                        {
                            'name': "Untaxed Amount",
                            'base_amount_currency': 31.78,
                            'base_amount': 6.36,
                            'tax_amount_currency': 4.86,
                            'tax_amount': 0.98,
                            'tax_groups': [
                                {
                                    'id': self.tax_groups[0].id,
                                    'base_amount_currency': 31.78,
                                    'base_amount': 6.36,
                                    'tax_amount_currency': 1.9,
                                    'tax_amount': 0.38,
                                    'display_base_amount_currency': 31.78,
                                    'display_base_amount': 6.36,
                                },
                                {
                                    'id': self.tax_groups[1].id,
                                    'base_amount_currency': 31.78,
                                    'base_amount': 6.36,
                                    'tax_amount_currency': 1.9,
                                    'tax_amount': 0.38,
                                    'display_base_amount_currency': 31.78,
                                    'display_base_amount': 6.36,
                                },
                                {
                                    'id': self.tax_groups[2].id,
                                    'base_amount_currency': 35.58,
                                    'base_amount': 7.12,
                                    'tax_amount_currency': 1.06,
                                    'tax_amount': 0.22,
                                    'display_base_amount_currency': 35.58,
                                    'display_base_amount': 7.12,
                                },
                            ],
                        },
                    ],
                }
                yield 3, self.populate_document(document_params), expected_values
            with self.with_tax_calculation_rounding_method('round_globally'):
                expected_values = {
                    'same_tax_base': False,
                    'currency_id': self.foreign_currency.id,
                    'company_currency_id': self.currency.id,
                    'base_amount_currency': 31.78,
                    'base_amount': 6.36,
                    'tax_amount_currency': 4.89,
                    'tax_amount': 0.97,
                    'total_amount_currency': 36.67,
                    'total_amount': 7.33,
                    'subtotals': [
                        {
                            'name': "Untaxed Amount",
                            'base_amount_currency': 31.78,
                            'base_amount': 6.36,
                            'tax_amount_currency': 4.89,
                            'tax_amount': 0.97,
                            'tax_groups': [
                                {
                                    'id': self.tax_groups[0].id,
                                    'base_amount_currency': 31.78,
                                    'base_amount': 6.36,
                                    'tax_amount_currency': 1.91,
                                    'tax_amount': 0.38,
                                    'display_base_amount_currency': 31.78,
                                    'display_base_amount': 6.36,
                                },
                                {
                                    'id': self.tax_groups[1].id,
                                    'base_amount_currency': 31.78,
                                    'base_amount': 6.36,
                                    'tax_amount_currency': 1.91,
                                    'tax_amount': 0.38,
                                    'display_base_amount_currency': 31.78,
                                    'display_base_amount': 6.36,
                                },
                                {
                                    'id': self.tax_groups[2].id,
                                    'base_amount_currency': 35.59,
                                    'base_amount': 7.12,
                                    'tax_amount_currency': 1.07,
                                    'tax_amount': 0.21,
                                    'display_base_amount_currency': 35.59,
                                    'display_base_amount': 7.12,
                                },
                            ],
                        },
                    ],
                }
                yield 4, self.populate_document(document_params), expected_values

        tax1.price_include_override = 'tax_included'
        tax2.price_include_override = 'tax_included'
        document_params = self.init_document(
            lines=[
                {'price_unit': 17.79, 'tax_ids': taxes},
                {'price_unit': 17.79, 'tax_ids': taxes},
            ],
            currency=self.foreign_currency,
            rate=5.0,
        )
        with self.same_tax_group(taxes):
            with self.with_tax_calculation_rounding_method('round_per_line'):
                expected_values = {
                    'same_tax_base': True,
                    'currency_id': self.foreign_currency.id,
                    'company_currency_id': self.currency.id,
                    'base_amount_currency': 31.78,
                    'base_amount': 6.36,
                    'tax_amount_currency': 4.86,
                    'tax_amount': 0.98,
                    'total_amount_currency': 36.64,
                    'total_amount': 7.34,
                    'subtotals': [
                        {
                            'name': "Untaxed Amount",
                            'base_amount_currency': 31.78,
                            'base_amount': 6.36,
                            'tax_amount_currency': 4.86,
                            'tax_amount': 0.98,
                            'tax_groups': [
                                {
                                    'id': self.tax_groups[0].id,
                                    'base_amount_currency': 31.78,
                                    'base_amount': 6.36,
                                    'tax_amount_currency': 4.86,
                                    'tax_amount': 0.98,
                                    'display_base_amount_currency': 31.78,
                                    'display_base_amount': 6.36,
                                },
                            ],
                        },
                    ],
                }
                yield 5, self.populate_document(document_params), expected_values
            with self.with_tax_calculation_rounding_method('round_globally'):
                expected_values = {
                    'same_tax_base': True,
                    'currency_id': self.foreign_currency.id,
                    'company_currency_id': self.currency.id,
                    'base_amount_currency': 31.77,
                    'base_amount': 6.35,
                    'tax_amount_currency': 4.89,
                    'tax_amount': 0.97,
                    'total_amount_currency': 36.66,
                    'total_amount': 7.32,
                    'subtotals': [
                        {
                            'name': "Untaxed Amount",
                            'base_amount_currency': 31.77,
                            'base_amount': 6.35,
                            'tax_amount_currency': 4.89,
                            'tax_amount': 0.97,
                            'tax_groups': [
                                {
                                    'id': self.tax_groups[0].id,
                                    'base_amount_currency': 31.77,
                                    'base_amount': 6.35,
                                    'tax_amount_currency': 4.89,
                                    'tax_amount': 0.97,
                                    'display_base_amount_currency': 31.77,
                                    'display_base_amount': 6.35,
                                },
                            ],
                        },
                    ],
                }
                yield 6, self.populate_document(document_params), expected_values
        with self.different_tax_group(taxes):
            with self.with_tax_calculation_rounding_method('round_per_line'):
                expected_values = {
                    'same_tax_base': False,
                    'currency_id': self.foreign_currency.id,
                    'company_currency_id': self.currency.id,
                    'base_amount_currency': 31.78,
                    'base_amount': 6.36,
                    'tax_amount_currency': 4.86,
                    'tax_amount': 0.98,
                    'total_amount_currency': 36.64,
                    'total_amount': 7.34,
                    'subtotals': [
                        {
                            'name': "Untaxed Amount",
                            'base_amount_currency': 31.78,
                            'base_amount': 6.36,
                            'tax_amount_currency': 4.86,
                            'tax_amount': 0.98,
                            'tax_groups': [
                                {
                                    'id': self.tax_groups[0].id,
                                    'base_amount_currency': 31.78,
                                    'base_amount': 6.36,
                                    'tax_amount_currency': 1.9,
                                    'tax_amount': 0.38,
                                    'display_base_amount_currency': 31.78,
                                    'display_base_amount': 6.36,
                                },
                                {
                                    'id': self.tax_groups[1].id,
                                    'base_amount_currency': 31.78,
                                    'base_amount': 6.36,
                                    'tax_amount_currency': 1.9,
                                    'tax_amount': 0.38,
                                    'display_base_amount_currency': 31.78,
                                    'display_base_amount': 6.36,
                                },
                                {
                                    'id': self.tax_groups[2].id,
                                    'base_amount_currency': 35.58,
                                    'base_amount': 7.12,
                                    'tax_amount_currency': 1.06,
                                    'tax_amount': 0.22,
                                    'display_base_amount_currency': 35.58,
                                    'display_base_amount': 7.12,
                                },
                            ],
                        },
                    ],
                }
                yield 7, self.populate_document(document_params), expected_values
            with self.with_tax_calculation_rounding_method('round_globally'):
                expected_values = {
                    'same_tax_base': False,
                    'currency_id': self.foreign_currency.id,
                    'company_currency_id': self.currency.id,
                    'base_amount_currency': 31.77,
                    'base_amount': 6.35,
                    'tax_amount_currency': 4.89,
                    'tax_amount': 0.97,
                    'total_amount_currency': 36.66,
                    'total_amount': 7.32,
                    'subtotals': [
                        {
                            'name': "Untaxed Amount",
                            'base_amount_currency': 31.77,
                            'base_amount': 6.35,
                            'tax_amount_currency': 4.89,
                            'tax_amount': 0.97,
                            'tax_groups': [
                                {
                                    'id': self.tax_groups[0].id,
                                    'base_amount_currency': 31.77,
                                    'base_amount': 6.35,
                                    'tax_amount_currency': 1.91,
                                    'tax_amount': 0.38,
                                    'display_base_amount_currency': 31.77,
                                    'display_base_amount': 6.35,
                                },
                                {
                                    'id': self.tax_groups[1].id,
                                    'base_amount_currency': 31.77,
                                    'base_amount': 6.35,
                                    'tax_amount_currency': 1.91,
                                    'tax_amount': 0.38,
                                    'display_base_amount_currency': 31.77,
                                    'display_base_amount': 6.35,
                                },
                                {
                                    'id': self.tax_groups[2].id,
                                    'base_amount_currency': 35.58,
                                    'base_amount': 7.12,
                                    'tax_amount_currency': 1.07,
                                    'tax_amount': 0.21,
                                    'display_base_amount_currency': 35.58,
                                    'display_base_amount': 7.12,
                                },
                            ],
                        },
                    ],
                }
                yield 8, self.populate_document(document_params), expected_values

    def test_taxes_l10n_in_generic_helpers(self):
        for test_index, document, expected_values in self._test_taxes_l10n_in():
            with self.subTest(test_index=test_index):
                self.assert_tax_totals_summary(document, expected_values)
        self._run_js_tests()

    def test_taxes_l10n_in_invoices(self):
        for test_index, document, expected_values in self._test_taxes_l10n_in():
            with self.subTest(test_index=test_index):
                invoice = self.convert_document_to_invoice(document)
                self.assert_invoice_tax_totals_summary(invoice, expected_values)

    def _test_taxes_l10n_br(self):
        tax1 = self.division_tax(5)
        tax2 = self.division_tax(3)
        tax3 = self.division_tax(0.65)
        tax4 = self.division_tax(9)
        tax5 = self.division_tax(15)
        taxes = tax1 + tax2 + tax3 + tax4 + tax5

        document_params = self.init_document(
            lines=[
                {'price_unit': 32.33, 'tax_ids': taxes},
                {'price_unit': 32.33, 'tax_ids': taxes},
            ],
            currency=self.foreign_currency,
            rate=3.0,
        )
        with self.same_tax_group(taxes):
            with self.with_tax_calculation_rounding_method('round_per_line'):
                expected_values = {
                    'same_tax_base': True,
                    'currency_id': self.foreign_currency.id,
                    'company_currency_id': self.currency.id,
                    'base_amount_currency': 64.66,
                    'base_amount': 21.56,
                    'tax_amount_currency': 31.34,
                    'tax_amount': 10.44,
                    'total_amount_currency': 96.0,
                    'total_amount': 32.0,
                    'subtotals': [
                        {
                            'name': "Untaxed Amount",
                            'base_amount_currency': 64.66,
                            'base_amount': 21.56,
                            'tax_amount_currency': 31.34,
                            'tax_amount': 10.44,
                            'tax_groups': [
                                {
                                    'id': self.tax_groups[0].id,
                                    'base_amount_currency': 64.66,
                                    'base_amount': 21.56,
                                    'tax_amount_currency': 31.34,
                                    'tax_amount': 10.44,
                                    'display_base_amount_currency': 64.66,
                                    'display_base_amount': 21.56,
                                },
                            ],
                        },
                    ],
                }
                yield 1, self.populate_document(document_params), expected_values
            with self.with_tax_calculation_rounding_method('round_globally'):
                expected_values = {
                    'same_tax_base': True,
                    'currency_id': self.foreign_currency.id,
                    'company_currency_id': self.currency.id,
                    'base_amount_currency': 64.66,
                    'base_amount': 21.55,
                    'tax_amount_currency': 31.34,
                    'tax_amount': 10.45,
                    'total_amount_currency': 96.0,
                    'total_amount': 32.0,
                    'subtotals': [
                        {
                            'name': "Untaxed Amount",
                            'base_amount_currency': 64.66,
                            'base_amount': 21.55,
                            'tax_amount_currency': 31.34,
                            'tax_amount': 10.45,
                            'tax_groups': [
                                {
                                    'id': self.tax_groups[0].id,
                                    'base_amount_currency': 64.66,
                                    'base_amount': 21.55,
                                    'tax_amount_currency': 31.34,
                                    'tax_amount': 10.45,
                                    'display_base_amount_currency': 64.66,
                                    'display_base_amount': 21.55,
                                },
                            ],
                        },
                    ],
                }
                yield 2, self.populate_document(document_params), expected_values
        with self.different_tax_group(taxes):
            with self.with_tax_calculation_rounding_method('round_per_line'):
                expected_values = {
                    'same_tax_base': True,
                    'currency_id': self.foreign_currency.id,
                    'company_currency_id': self.currency.id,
                    'base_amount_currency': 64.66,
                    'base_amount': 21.56,
                    'tax_amount_currency': 31.34,
                    'tax_amount': 10.44,
                    'total_amount_currency': 96.0,
                    'total_amount': 32.0,
                    'subtotals': [
                        {
                            'name': "Untaxed Amount",
                            'base_amount_currency': 64.66,
                            'base_amount': 21.56,
                            'tax_amount_currency': 31.34,
                            'tax_amount': 10.44,
                            'tax_groups': [
                                {
                                    'id': self.tax_groups[0].id,
                                    'base_amount_currency': 64.66,
                                    'base_amount': 21.56,
                                    'tax_amount_currency': 4.8,
                                    'tax_amount': 1.6,
                                    'display_base_amount_currency': 64.66,
                                    'display_base_amount': 21.56,
                                },
                                {
                                    'id': self.tax_groups[1].id,
                                    'base_amount_currency': 64.66,
                                    'base_amount': 21.56,
                                    'tax_amount_currency': 2.88,
                                    'tax_amount': 0.96,
                                    'display_base_amount_currency': 64.66,
                                    'display_base_amount': 21.56,
                                },
                                {
                                    'id': self.tax_groups[2].id,
                                    'base_amount_currency': 64.66,
                                    'base_amount': 21.56,
                                    'tax_amount_currency': 0.62,
                                    'tax_amount': 0.2,
                                    'display_base_amount_currency': 64.66,
                                    'display_base_amount': 21.56,
                                },
                                {
                                    'id': self.tax_groups[3].id,
                                    'base_amount_currency': 64.66,
                                    'base_amount': 21.56,
                                    'tax_amount_currency': 8.64,
                                    'tax_amount': 2.88,
                                    'display_base_amount_currency': 64.66,
                                    'display_base_amount': 21.56,
                                },
                                {
                                    'id': self.tax_groups[4].id,
                                    'base_amount_currency': 64.66,
                                    'base_amount': 21.56,
                                    'tax_amount_currency': 14.4,
                                    'tax_amount': 4.8,
                                    'display_base_amount_currency': 64.66,
                                    'display_base_amount': 21.56,
                                },
                            ],
                        },
                    ],
                }
                yield 3, self.populate_document(document_params), expected_values
            with self.with_tax_calculation_rounding_method('round_globally'):
                expected_values = {
                    'same_tax_base': True,
                    'currency_id': self.foreign_currency.id,
                    'company_currency_id': self.currency.id,
                    'base_amount_currency': 64.66,
                    'base_amount': 21.55,
                    'tax_amount_currency': 31.34,
                    'tax_amount': 10.45,
                    'total_amount_currency': 96.0,
                    'total_amount': 32.0,
                    'subtotals': [
                        {
                            'name': "Untaxed Amount",
                            'base_amount_currency': 64.66,
                            'base_amount': 21.55,
                            'tax_amount_currency': 31.34,
                            'tax_amount': 10.45,
                            'tax_groups': [
                                {
                                    'id': self.tax_groups[0].id,
                                    'base_amount_currency': 64.66,
                                    'base_amount': 21.55,
                                    'tax_amount_currency': 4.8,
                                    'tax_amount': 1.6,
                                    'display_base_amount_currency': 64.66,
                                    'display_base_amount': 21.55,
                                },
                                {
                                    'id': self.tax_groups[1].id,
                                    'base_amount_currency': 64.66,
                                    'base_amount': 21.55,
                                    'tax_amount_currency': 2.88,
                                    'tax_amount': 0.96,
                                    'display_base_amount_currency': 64.66,
                                    'display_base_amount': 21.55,
                                },
                                {
                                    'id': self.tax_groups[2].id,
                                    'base_amount_currency': 64.66,
                                    'base_amount': 21.55,
                                    'tax_amount_currency': 0.62,
                                    'tax_amount': 0.21,
                                    'display_base_amount_currency': 64.66,
                                    'display_base_amount': 21.55,
                                },
                                {
                                    'id': self.tax_groups[3].id,
                                    'base_amount_currency': 64.66,
                                    'base_amount': 21.55,
                                    'tax_amount_currency': 8.64,
                                    'tax_amount': 2.88,
                                    'display_base_amount_currency': 64.66,
                                    'display_base_amount': 21.55,
                                },
                                {
                                    'id': self.tax_groups[4].id,
                                    'base_amount_currency': 64.66,
                                    'base_amount': 21.55,
                                    'tax_amount_currency': 14.4,
                                    'tax_amount': 4.8,
                                    'display_base_amount_currency': 64.66,
                                    'display_base_amount': 21.55,
                                },
                            ],
                        },
                    ],
                }
                yield 4, self.populate_document(document_params), expected_values

        taxes.price_include_override = 'tax_included'
        document_params = self.init_document(
            lines=[
                {'price_unit': 48.0, 'tax_ids': taxes},
                {'price_unit': 48.0, 'tax_ids': taxes},
            ],
            currency=self.foreign_currency,
            rate=3.0,
        )
        with self.same_tax_group(taxes):
            with self.with_tax_calculation_rounding_method('round_per_line'):
                expected_values = {
                    'same_tax_base': False,
                    'currency_id': self.foreign_currency.id,
                    'company_currency_id': self.currency.id,
                    'base_amount_currency': 64.66,
                    'base_amount': 21.56,
                    'tax_amount_currency': 31.34,
                    'tax_amount': 10.44,
                    'total_amount_currency': 96.0,
                    'total_amount': 32.0,
                    'subtotals': [
                        {
                            'name': "Untaxed Amount",
                            'base_amount_currency': 64.66,
                            'base_amount': 21.56,
                            'tax_amount_currency': 31.34,
                            'tax_amount': 10.44,
                            'tax_groups': [
                                {
                                    'id': self.tax_groups[0].id,
                                    'base_amount_currency': 64.66,
                                    'base_amount': 21.56,
                                    'tax_amount_currency': 31.34,
                                    'tax_amount': 10.44,
                                    'display_base_amount_currency': 96.0,
                                    'display_base_amount': 32.0,
                                },
                            ],
                        },
                    ],
                }
                yield 5, self.populate_document(document_params), expected_values
            with self.with_tax_calculation_rounding_method('round_globally'):
                expected_values = {
                    'same_tax_base': False,
                    'currency_id': self.foreign_currency.id,
                    'company_currency_id': self.currency.id,
                    'base_amount_currency': 64.66,
                    'base_amount': 21.55,
                    'tax_amount_currency': 31.34,
                    'tax_amount': 10.45,
                    'total_amount_currency': 96.0,
                    'total_amount': 32.0,
                    'subtotals': [
                        {
                            'name': "Untaxed Amount",
                            'base_amount_currency': 64.66,
                            'base_amount': 21.55,
                            'tax_amount_currency': 31.34,
                            'tax_amount': 10.45,
                            'tax_groups': [
                                {
                                    'id': self.tax_groups[0].id,
                                    'base_amount_currency': 64.66,
                                    'base_amount': 21.55,
                                    'tax_amount_currency': 31.34,
                                    'tax_amount': 10.45,
                                    'display_base_amount_currency': 96.0,
                                    'display_base_amount': 32.0,
                                },
                            ],
                        },
                    ],
                }
                yield 6, self.populate_document(document_params), expected_values
        with self.different_tax_group(taxes):
            with self.with_tax_calculation_rounding_method('round_per_line'):
                expected_values = {
                    'same_tax_base': False,
                    'currency_id': self.foreign_currency.id,
                    'company_currency_id': self.currency.id,
                    'base_amount_currency': 64.66,
                    'base_amount': 21.56,
                    'tax_amount_currency': 31.34,
                    'tax_amount': 10.44,
                    'total_amount_currency': 96.0,
                    'total_amount': 32.0,
                    'subtotals': [
                        {
                            'name': "Untaxed Amount",
                            'base_amount_currency': 64.66,
                            'base_amount': 21.56,
                            'tax_amount_currency': 31.34,
                            'tax_amount': 10.44,
                            'tax_groups': [
                                {
                                    'id': self.tax_groups[0].id,
                                    'base_amount_currency': 64.66,
                                    'base_amount': 21.56,
                                    'tax_amount_currency': 4.8,
                                    'tax_amount': 1.6,
                                    'display_base_amount_currency': 96.0,
                                    'display_base_amount': 32.0,
                                },
                                {
                                    'id': self.tax_groups[1].id,
                                    'base_amount_currency': 64.66,
                                    'base_amount': 21.56,
                                    'tax_amount_currency': 2.88,
                                    'tax_amount': 0.96,
                                    'display_base_amount_currency': 96.0,
                                    'display_base_amount': 32.0,
                                },
                                {
                                    'id': self.tax_groups[2].id,
                                    'base_amount_currency': 64.66,
                                    'base_amount': 21.56,
                                    'tax_amount_currency': 0.62,
                                    'tax_amount': 0.2,
                                    'display_base_amount_currency': 96.0,
                                    'display_base_amount': 32.0,
                                },
                                {
                                    'id': self.tax_groups[3].id,
                                    'base_amount_currency': 64.66,
                                    'base_amount': 21.56,
                                    'tax_amount_currency': 8.64,
                                    'tax_amount': 2.88,
                                    'display_base_amount_currency': 96.0,
                                    'display_base_amount': 32.0,
                                },
                                {
                                    'id': self.tax_groups[4].id,
                                    'base_amount_currency': 64.66,
                                    'base_amount': 21.56,
                                    'tax_amount_currency': 14.4,
                                    'tax_amount': 4.8,
                                    'display_base_amount_currency': 96.0,
                                    'display_base_amount': 32.0,
                                },
                            ],
                        },
                    ],
                }
                yield 7, self.populate_document(document_params), expected_values
            with self.with_tax_calculation_rounding_method('round_globally'):
                expected_values = {
                    'same_tax_base': False,
                    'currency_id': self.foreign_currency.id,
                    'company_currency_id': self.currency.id,
                    'base_amount_currency': 64.66,
                    'base_amount': 21.55,
                    'tax_amount_currency': 31.34,
                    'tax_amount': 10.45,
                    'total_amount_currency': 96.0,
                    'total_amount': 32.0,
                    'subtotals': [
                        {
                            'name': "Untaxed Amount",
                            'base_amount_currency': 64.66,
                            'base_amount': 21.55,
                            'tax_amount_currency': 31.34,
                            'tax_amount': 10.45,
                            'tax_groups': [
                                {
                                    'id': self.tax_groups[0].id,
                                    'base_amount_currency': 64.66,
                                    'base_amount': 21.55,
                                    'tax_amount_currency': 4.8,
                                    'tax_amount': 1.6,
                                    'display_base_amount_currency': 96.0,
                                    'display_base_amount': 32.0,
                                },
                                {
                                    'id': self.tax_groups[1].id,
                                    'base_amount_currency': 64.66,
                                    'base_amount': 21.55,
                                    'tax_amount_currency': 2.88,
                                    'tax_amount': 0.96,
                                    'display_base_amount_currency': 96.0,
                                    'display_base_amount': 32.0,
                                },
                                {
                                    'id': self.tax_groups[2].id,
                                    'base_amount_currency': 64.66,
                                    'base_amount': 21.55,
                                    'tax_amount_currency': 0.62,
                                    'tax_amount': 0.21,
                                    'display_base_amount_currency': 96.0,
                                    'display_base_amount': 32.0,
                                },
                                {
                                    'id': self.tax_groups[3].id,
                                    'base_amount_currency': 64.66,
                                    'base_amount': 21.55,
                                    'tax_amount_currency': 8.64,
                                    'tax_amount': 2.88,
                                    'display_base_amount_currency': 96.0,
                                    'display_base_amount': 32.0,
                                },
                                {
                                    'id': self.tax_groups[4].id,
                                    'base_amount_currency': 64.66,
                                    'base_amount': 21.55,
                                    'tax_amount_currency': 14.4,
                                    'tax_amount': 4.8,
                                    'display_base_amount_currency': 96.0,
                                    'display_base_amount': 32.0,
                                },
                            ],
                        },
                    ],
                }
                yield 8, self.populate_document(document_params), expected_values

        # Extreme case to push the computation of the display_base_amount to its limit.
        # Note: tax6 is the only one in a separated tax group.
        tax6 = self.fixed_tax(1, include_base_amount=True, sequence=0, tax_group_id=self.tax_groups[7].id)
        tax7 = self.division_tax(20, price_include_override='tax_included')
        tax8 = self.division_tax(20, price_include_override='tax_included')
        taxes += tax7 + tax8

        document_params = self.init_document(
            lines=[
                {'price_unit': 47.0, 'tax_ids': tax6 + tax1 + tax2 + tax3 + tax4 + tax5},
                {'price_unit': 48.0, 'tax_ids': tax7 + tax8},
            ],
            currency=self.foreign_currency,
            rate=3.0,
        )
        with self.same_tax_group(taxes):
            with self.with_tax_calculation_rounding_method('round_per_line'):
                expected_values = {
                    'same_tax_base': False,
                    'currency_id': self.foreign_currency.id,
                    'company_currency_id': self.currency.id,
                    'base_amount_currency': 60.13,
                    'base_amount': 20.04,
                    'tax_amount_currency': 35.87,
                    'tax_amount': 11.95,
                    'total_amount_currency': 96.0,
                    'total_amount': 31.99,
                    'subtotals': [
                        {
                            'name': "Untaxed Amount",
                            'base_amount_currency': 60.13,
                            'base_amount': 20.04,
                            'tax_amount_currency': 35.87,
                            'tax_amount': 11.95,
                            'tax_groups': [
                                {
                                    'id': self.tax_groups[0].id,
                                    'base_amount_currency': 61.13,
                                    'base_amount': 20.38,
                                    'tax_amount_currency': 34.87,
                                    'tax_amount': 11.62,
                                    'display_base_amount_currency': 96.0,
                                    'display_base_amount': 32.0,
                                },
                                {
                                    'id': self.tax_groups[7].id,
                                    'base_amount_currency': 31.33,
                                    'base_amount': 10.44,
                                    'tax_amount_currency': 1.0,
                                    'tax_amount': 0.33,
                                    'display_base_amount_currency': None,
                                    'display_base_amount': None,
                                },
                            ],
                        },
                    ],
                }
                yield 9, self.populate_document(document_params), expected_values
            with self.with_tax_calculation_rounding_method('round_globally'):
                expected_values = {
                    'same_tax_base': False,
                    'currency_id': self.foreign_currency.id,
                    'company_currency_id': self.currency.id,
                    'base_amount_currency': 60.13,
                    'base_amount': 20.04,
                    'tax_amount_currency': 35.87,
                    'tax_amount': 11.95,
                    'total_amount_currency': 96.0,
                    'total_amount': 31.99,
                    'subtotals': [
                        {
                            'name': "Untaxed Amount",
                            'base_amount_currency': 60.13,
                            'base_amount': 20.04,
                            'tax_amount_currency': 35.87,
                            'tax_amount': 11.95,
                            'tax_groups': [
                                {
                                    'id': self.tax_groups[0].id,
                                    'base_amount_currency': 61.13,
                                    'base_amount': 20.38,
                                    'tax_amount_currency': 34.87,
                                    'tax_amount': 11.62,
                                    'display_base_amount_currency': 96.0,
                                    'display_base_amount': 32.0,
                                },
                                {
                                    'id': self.tax_groups[7].id,
                                    'base_amount_currency': 31.33,
                                    'base_amount': 10.44,
                                    'tax_amount_currency': 1.0,
                                    'tax_amount': 0.33,
                                    'display_base_amount_currency': None,
                                    'display_base_amount': None,
                                },
                            ],
                        },
                    ],
                }
                yield 10, self.populate_document(document_params), expected_values

    def test_taxes_l10n_br_generic_helpers(self):
        for test_index, document, expected_values in self._test_taxes_l10n_br():
            with self.subTest(test_index=test_index):
                self.assert_tax_totals_summary(document, expected_values)
        self._run_js_tests()

    def test_taxes_l10n_br_invoices(self):
        for test_index, document, expected_values in self._test_taxes_l10n_br():
            with self.subTest(test_index=test_index):
                invoice = self.convert_document_to_invoice(document)
                self.assert_invoice_tax_totals_summary(invoice, expected_values)

    def _test_taxes_l10n_be(self):
        tax1 = self.fixed_tax(1, include_base_amount=True)
        tax2 = self.percent_tax(21)
        taxes = tax1 + tax2

        document_params = self.init_document(
            lines=[
                {'price_unit': 16.79, 'tax_ids': taxes},
                {'price_unit': 16.79, 'tax_ids': taxes},
            ],
            currency=self.foreign_currency,
            rate=0.5,
        )
        with self.same_tax_group(taxes):
            with self.with_tax_calculation_rounding_method('round_per_line'):
                expected_values = {
                    'same_tax_base': True,
                    'currency_id': self.foreign_currency.id,
                    'company_currency_id': self.currency.id,
                    'base_amount_currency': 33.58,
                    'base_amount': 67.16,
                    'tax_amount_currency': 9.48,
                    'tax_amount': 18.96,
                    'total_amount_currency': 43.06,
                    'total_amount': 86.12,
                    'subtotals': [
                        {
                            'name': "Untaxed Amount",
                            'base_amount_currency': 33.58,
                            'base_amount': 67.16,
                            'tax_amount_currency': 9.48,
                            'tax_amount': 18.96,
                            'tax_groups': [
                                {
                                    'id': self.tax_groups[0].id,
                                    'base_amount_currency': 33.58,
                                    'base_amount': 67.16,
                                    'tax_amount_currency': 9.48,
                                    'tax_amount': 18.96,
                                    'display_base_amount_currency': 33.58,
                                    'display_base_amount': 67.16,
                                },
                            ],
                        },
                    ],
                }
                yield 1, self.populate_document(document_params), expected_values
            with self.with_tax_calculation_rounding_method('round_globally'):
                expected_values = {
                    'same_tax_base': True,
                    'currency_id': self.foreign_currency.id,
                    'company_currency_id': self.currency.id,
                    'base_amount_currency': 33.58,
                    'base_amount': 67.16,
                    'tax_amount_currency': 9.47,
                    'tax_amount': 18.94,
                    'total_amount_currency': 43.05,
                    'total_amount': 86.1,
                    'subtotals': [
                        {
                            'name': "Untaxed Amount",
                            'base_amount_currency': 33.58,
                            'base_amount': 67.16,
                            'tax_amount_currency': 9.47,
                            'tax_amount': 18.94,
                            'tax_groups': [
                                {
                                    'id': self.tax_groups[0].id,
                                    'base_amount_currency': 33.58,
                                    'base_amount': 67.16,
                                    'tax_amount_currency': 9.47,
                                    'tax_amount': 18.94,
                                    'display_base_amount_currency': 33.58,
                                    'display_base_amount': 67.16,
                                },
                            ],
                        },
                    ],
                }
                yield 2, self.populate_document(document_params), expected_values
        with self.different_tax_group(taxes):
            with self.with_tax_calculation_rounding_method('round_per_line'):
                expected_values = {
                    'same_tax_base': False,
                    'currency_id': self.foreign_currency.id,
                    'company_currency_id': self.currency.id,
                    'base_amount_currency': 33.58,
                    'base_amount': 67.16,
                    'tax_amount_currency': 9.48,
                    'tax_amount': 18.96,
                    'total_amount_currency': 43.06,
                    'total_amount': 86.12,
                    'subtotals': [
                        {
                            'name': "Untaxed Amount",
                            'base_amount_currency': 33.58,
                            'base_amount': 67.16,
                            'tax_amount_currency': 9.48,
                            'tax_amount': 18.96,
                            'tax_groups': [
                                {
                                    'id': self.tax_groups[0].id,
                                    'base_amount_currency': 33.58,
                                    'base_amount': 67.16,
                                    'tax_amount_currency': 2.0,
                                    'tax_amount': 4.0,
                                    'display_base_amount_currency': None,
                                    'display_base_amount': None,
                                },
                                {
                                    'id': self.tax_groups[1].id,
                                    'base_amount_currency': 35.58,
                                    'base_amount': 71.16,
                                    'tax_amount_currency': 7.48,
                                    'tax_amount': 14.96,
                                    'display_base_amount_currency': 35.58,
                                    'display_base_amount': 71.16,
                                },
                            ],
                        },
                    ],
                }
                yield 3, self.populate_document(document_params), expected_values
            with self.with_tax_calculation_rounding_method('round_globally'):
                expected_values = {
                    'same_tax_base': False,
                    'currency_id': self.foreign_currency.id,
                    'company_currency_id': self.currency.id,
                    'base_amount_currency': 33.58,
                    'base_amount': 67.16,
                    'tax_amount_currency': 9.47,
                    'tax_amount': 18.94,
                    'total_amount_currency': 43.05,
                    'total_amount': 86.1,
                    'subtotals': [
                        {
                            'name': "Untaxed Amount",
                            'base_amount_currency': 33.58,
                            'base_amount': 67.16,
                            'tax_amount_currency': 9.47,
                            'tax_amount': 18.94,
                            'tax_groups': [
                                {
                                    'id': self.tax_groups[0].id,
                                    'base_amount_currency': 33.58,
                                    'base_amount': 67.16,
                                    'tax_amount_currency': 2.0,
                                    'tax_amount': 4.0,
                                    'display_base_amount_currency': None,
                                    'display_base_amount': None,
                                },
                                {
                                    'id': self.tax_groups[1].id,
                                    'base_amount_currency': 35.58,
                                    'base_amount': 71.16,
                                    'tax_amount_currency': 7.47,
                                    'tax_amount': 14.94,
                                    'display_base_amount_currency': 35.58,
                                    'display_base_amount': 71.16,
                                },
                            ],
                        },
                    ],
                }
                yield 4, self.populate_document(document_params), expected_values

        taxes.price_include_override = 'tax_included'

        document_params = self.init_document(
            lines=[
                {'price_unit': 21.53, 'tax_ids': taxes},
                {'price_unit': 21.53, 'tax_ids': taxes},
            ],
            currency=self.foreign_currency,
            rate=0.5,
        )
        with self.same_tax_group(taxes):
            with self.with_tax_calculation_rounding_method('round_per_line'):
                expected_values = {
                    'same_tax_base': True,
                    'currency_id': self.foreign_currency.id,
                    'company_currency_id': self.currency.id,
                    'base_amount_currency': 33.58,
                    'base_amount': 67.16,
                    'tax_amount_currency': 9.48,
                    'tax_amount': 18.96,
                    'total_amount_currency': 43.06,
                    'total_amount': 86.12,
                    'subtotals': [
                        {
                            'name': "Untaxed Amount",
                            'base_amount_currency': 33.58,
                            'base_amount': 67.16,
                            'tax_amount_currency': 9.48,
                            'tax_amount': 18.96,
                            'tax_groups': [
                                {
                                    'id': self.tax_groups[0].id,
                                    'base_amount_currency': 33.58,
                                    'base_amount': 67.16,
                                    'tax_amount_currency': 9.48,
                                    'tax_amount': 18.96,
                                    'display_base_amount_currency': 33.58,
                                    'display_base_amount': 67.16,
                                },
                            ],
                        },
                    ],
                }
                yield 5, self.populate_document(document_params), expected_values
            with self.with_tax_calculation_rounding_method('round_globally'):
                expected_values = {
                    'same_tax_base': True,
                    'currency_id': self.foreign_currency.id,
                    'company_currency_id': self.currency.id,
                    'base_amount_currency': 33.59,
                    'base_amount': 67.17,
                    'tax_amount_currency': 9.47,
                    'tax_amount': 18.95,
                    'total_amount_currency': 43.06,
                    'total_amount': 86.12,
                    'subtotals': [
                        {
                            'name': "Untaxed Amount",
                            'base_amount_currency': 33.59,
                            'base_amount': 67.17,
                            'tax_amount_currency': 9.47,
                            'tax_amount': 18.95,
                            'tax_groups': [
                                {
                                    'id': self.tax_groups[0].id,
                                    'base_amount_currency': 33.59,
                                    'base_amount': 67.17,
                                    'tax_amount_currency': 9.47,
                                    'tax_amount': 18.95,
                                    'display_base_amount_currency': 33.59,
                                    'display_base_amount': 67.17,
                                },
                            ],
                        },
                    ],
                }
                yield 6, self.populate_document(document_params), expected_values
        with self.different_tax_group(taxes):
            with self.with_tax_calculation_rounding_method('round_per_line'):
                expected_values = {
                    'same_tax_base': False,
                    'currency_id': self.foreign_currency.id,
                    'company_currency_id': self.currency.id,
                    'base_amount_currency': 33.58,
                    'base_amount': 67.16,
                    'tax_amount_currency': 9.48,
                    'tax_amount': 18.96,
                    'total_amount_currency': 43.06,
                    'total_amount': 86.12,
                    'subtotals': [
                        {
                            'name': "Untaxed Amount",
                            'base_amount_currency': 33.58,
                            'base_amount': 67.16,
                            'tax_amount_currency': 9.48,
                            'tax_amount': 18.96,
                            'tax_groups': [
                                {
                                    'id': self.tax_groups[0].id,
                                    'base_amount_currency': 33.58,
                                    'base_amount': 67.16,
                                    'tax_amount_currency': 2.0,
                                    'tax_amount': 4.0,
                                    'display_base_amount_currency': None,
                                    'display_base_amount': None,
                                },
                                {
                                    'id': self.tax_groups[1].id,
                                    'base_amount_currency': 35.58,
                                    'base_amount': 71.16,
                                    'tax_amount_currency': 7.48,
                                    'tax_amount': 14.96,
                                    'display_base_amount_currency': 35.58,
                                    'display_base_amount': 71.16,
                                },
                            ],
                        },
                    ],
                }
                yield 7, self.populate_document(document_params), expected_values
            with self.with_tax_calculation_rounding_method('round_globally'):
                expected_values = {
                    'same_tax_base': False,
                    'currency_id': self.foreign_currency.id,
                    'company_currency_id': self.currency.id,
                    'base_amount_currency': 33.59,
                    'base_amount': 67.17,
                    'tax_amount_currency': 9.47,
                    'tax_amount': 18.95,
                    'total_amount_currency': 43.06,
                    'total_amount': 86.12,
                    'subtotals': [
                        {
                            'name': "Untaxed Amount",
                            'base_amount_currency': 33.59,
                            'base_amount': 67.17,
                            'tax_amount_currency': 9.47,
                            'tax_amount': 18.95,
                            'tax_groups': [
                                {
                                    'id': self.tax_groups[0].id,
                                    'base_amount_currency': 33.59,
                                    'base_amount': 67.17,
                                    'tax_amount_currency': 2.0,
                                    'tax_amount': 4.0,
                                    'display_base_amount_currency': None,
                                    'display_base_amount': None,
                                },
                                {
                                    'id': self.tax_groups[1].id,
                                    'base_amount_currency': 35.59,
                                    'base_amount': 71.17,
                                    'tax_amount_currency': 7.47,
                                    'tax_amount': 14.95,
                                    'display_base_amount_currency': 35.59,
                                    'display_base_amount': 71.17,
                                },
                            ],
                        },
                    ],
                }
                yield 8, self.populate_document(document_params), expected_values

    def test_taxes_l10n_be_generic_helpers(self):
        for test_index, document, expected_values in self._test_taxes_l10n_be():
            with self.subTest(test_index=test_index):
                self.assert_tax_totals_summary(document, expected_values)
        self._run_js_tests()

    def test_taxes_l10n_be_invoices(self):
        for test_index, document, expected_values in self._test_taxes_l10n_be():
            with self.subTest(test_index=test_index):
                invoice = self.convert_document_to_invoice(document)
                self.assert_invoice_tax_totals_summary(invoice, expected_values)

    def _test_taxes_l10n_mx(self):
        tax = self.percent_tax(16, price_include_override='tax_included')

        document_params = self.init_document([
            {'price_unit': 1199.0, 'tax_ids': tax},
            {'price_unit': 1999.0, 'tax_ids': tax},
            {'price_unit': 1699.0, 'tax_ids': tax},
            {'price_unit': 11999.0, 'tax_ids': tax},
            {'price_unit': 11999.0, 'tax_ids': tax},
            {'price_unit': 11999.0, 'tax_ids': tax},
            {'price_unit': 10999.0, 'tax_ids': tax},
        ])
        with self.with_tax_calculation_rounding_method('round_per_line'):
            expected_values = {
                'same_tax_base': True,
                'currency_id': self.currency.id,
                'base_amount_currency': 44735.37,
                'tax_amount_currency': 7157.63,
                'total_amount_currency': 51893.00,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 44735.37,
                        'tax_amount_currency': 7157.63,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 44735.37,
                                'tax_amount_currency': 7157.63,
                                'display_base_amount_currency': 44735.37,
                            },
                        ],
                    },
                ],
            }
            yield 1, self.populate_document(document_params), expected_values
        with self.with_tax_calculation_rounding_method('round_globally'):
            expected_values = {
                'same_tax_base': True,
                'currency_id': self.currency.id,
                'base_amount_currency': 44735.34,
                'tax_amount_currency': 7157.66,
                'total_amount_currency': 51893.00,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 44735.34,
                        'tax_amount_currency': 7157.66,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 44735.34,
                                'tax_amount_currency': 7157.66,
                                'display_base_amount_currency': 44735.34,
                            },
                        ],
                    },
                ],
            }
            yield 2, self.populate_document(document_params), expected_values

    def test_taxes_l10n_mx_generic_helpers(self):
        for test_index, document, expected_values in self._test_taxes_l10n_mx():
            with self.subTest(test_index=test_index):
                self.assert_tax_totals_summary(document, expected_values)
        self._run_js_tests()

    def test_taxes_l10n_mx_invoices(self):
        for test_index, document, expected_values in self._test_taxes_l10n_mx():
            with self.subTest(test_index=test_index):
                invoice = self.convert_document_to_invoice(document)
                self.assert_invoice_tax_totals_summary(invoice, expected_values)

    def _test_taxes_l10n_pt(self):
        """ !!!! THOSE TESTS ARE THERE TO CERTIFY THE USE OF ODOO INVOICING IN PORTUGAL.
        Therefore, they have to stay like this to stay compliant.
        Note: this is a work in progress. The remaining stuff is coming...
        """
        self.env.company.tax_calculation_rounding_method = 'round_globally'
        tax_13 = self.percent_tax(13, tax_group_id=self.tax_groups[2].id)
        tax_23 = self.percent_tax(23, tax_group_id=self.tax_groups[3].id)

        document = self.populate_document(self.init_document(
            lines=[
                {'quantity': 12.12, 'price_unit': 12.12},
                {'quantity': 12.12, 'price_unit': 12.12},
            ],
        ))
        expected_values = {
            'same_tax_base': True,
            'currency_id': self.currency.id,
            'base_amount_currency': 293.79,
            'tax_amount_currency': 0.0,
            'total_amount_currency': 293.79,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 293.79,
                    'tax_amount_currency': 0.0,
                    'tax_groups': [],
                },
            ],
        }
        yield 1, document, expected_values

        document = self.populate_document(self.init_document(
            lines=[
                {'quantity': 12.12, 'price_unit': 12.12, 'tax_ids': tax_13},
                {'quantity': 12.12, 'price_unit': 12.12, 'tax_ids': tax_13},
            ],
        ))
        expected_values = {
            'same_tax_base': True,
            'currency_id': self.currency.id,
            'base_amount_currency': 293.79,
            'tax_amount_currency': 38.19,
            'total_amount_currency': 331.98,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 293.79,
                    'tax_amount_currency': 38.19,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[2].id,
                            'base_amount_currency': 293.79,
                            'tax_amount_currency': 38.19,
                            'display_base_amount_currency': 293.79,
                        },
                    ],
                },
            ],
        }
        yield 2, document, expected_values

        document = self.populate_document(self.init_document(
            lines=[
                {'quantity': 12.12, 'price_unit': 12.12, 'tax_ids': tax_13},
                {'quantity': 12.12, 'price_unit': 12.12, 'tax_ids': tax_23},
            ],
        ))
        expected_values = {
            'same_tax_base': False,
            'currency_id': self.currency.id,
            'base_amount_currency': 293.79,
            'tax_amount_currency': 52.89,
            'total_amount_currency': 346.68,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 293.79,
                    'tax_amount_currency': 52.89,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[2].id,
                            'base_amount_currency': 146.89,
                            'tax_amount_currency': 19.1,
                            'display_base_amount_currency': 146.89,
                        },
                        {
                            'id': self.tax_groups[3].id,
                            'base_amount_currency': 146.89,
                            'tax_amount_currency': 33.79,
                            'display_base_amount_currency': 146.89,
                        },
                    ],
                },
            ],
        }
        yield 3, document, expected_values

    def test_taxes_l10n_pt_generic_helpers(self):
        for test_index, document, expected_values in self._test_taxes_l10n_pt():
            with self.subTest(test_index=test_index):
                self.assert_tax_totals_summary(document, expected_values)
        self._run_js_tests()

    def test_taxes_l10n_pt_invoices(self):
        for test_index, document, expected_values in self._test_taxes_l10n_pt():
            with self.subTest(test_index=test_index):
                invoice = self.convert_document_to_invoice(document)
                self.assert_invoice_tax_totals_summary(invoice, expected_values)

    def _test_reverse_charge_taxes_1(self):
        tax = self.percent_tax(
            21.0,
            invoice_repartition_line_ids=[
                Command.create({'repartition_type': 'base', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': -100.0}),
            ],
            refund_repartition_line_ids=[
                Command.create({'repartition_type': 'base', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': -100.0}),
            ],
        )
        document_params = self.init_document(lines=[{'price_unit': 100.0, 'tax_ids': tax}])
        expected_values = {
            'same_tax_base': True,
            'currency_id': self.currency.id,
            'base_amount_currency': 100.0,
            'tax_amount_currency': 0.0,
            'total_amount_currency': 100.0,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 100.0,
                    'tax_amount_currency': 0.0,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 100.0,
                            'tax_amount_currency': 0.0,
                            'display_base_amount_currency': 100.0,
                        },
                    ],
                },
            ],
        }
        yield self.populate_document(document_params), expected_values

    def test_reverse_charge_taxes_1_generic_helpers(self):
        for document, expected_values in self._test_reverse_charge_taxes_1():
            self.assert_tax_totals_summary(document, expected_values)
        self._run_js_tests()

    def test_reverse_charge_taxes_1_invoices(self):
        for document, expected_values in self._test_reverse_charge_taxes_1():
            invoice = self.convert_document_to_invoice(document)
            self.assert_invoice_tax_totals_summary(invoice, expected_values)

    def _test_reverse_charge_taxes_2(self):
        self.env.company.tax_calculation_rounding_method = 'round_globally'
        tax = self.percent_tax(
            21.0,
            invoice_repartition_line_ids=[
                Command.create({'repartition_type': 'base', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': -100.0}),
            ],
            refund_repartition_line_ids=[
                Command.create({'repartition_type': 'base', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': -100.0}),
            ],
        )
        document_params = self.init_document(lines=[
            {'price_unit': 11178.65, 'discount': 10.0, 'tax_ids': tax},
        ])
        expected_values = {
            'same_tax_base': True,
            'currency_id': self.currency.id,
            'base_amount_currency': 10060.79,
            'tax_amount_currency': 0.0,
            'total_amount_currency': 10060.79,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 10060.79,
                    'tax_amount_currency': 0.0,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 10060.79,
                            'tax_amount_currency': 0.0,
                            'display_base_amount_currency': 10060.79,
                        },
                    ],
                },
            ],
        }
        yield self.populate_document(document_params), expected_values

    def test_reverse_charge_taxes_2_generic_helpers(self):
        for document, expected_values in self._test_reverse_charge_taxes_2():
            self.assert_tax_totals_summary(document, expected_values)
        self._run_js_tests()

    def test_reverse_charge_taxes_2_invoices(self):
        for document, expected_values in self._test_reverse_charge_taxes_2():
            invoice = self.convert_document_to_invoice(document)
            self.assert_invoice_tax_totals_summary(invoice, expected_values)

    def _test_cash_rounding(self):
        tax1 = self.division_tax(5)
        tax2 = self.division_tax(3)
        tax3 = self.division_tax(0.65)
        tax4 = self.division_tax(9)
        tax5 = self.division_tax(15)
        taxes = tax1 + tax2 + tax3 + tax4 + tax5

        with self.same_tax_group(taxes), self.with_tax_calculation_rounding_method('round_per_line'):
            cash_rounding = self.env['account.cash.rounding'].create({
                'name': 'add_invoice_line',
                'rounding': 0.05,
                'strategy': 'add_invoice_line',
                'profit_account_id': self.company_data['default_account_revenue'].id,
                'loss_account_id': self.company_data['default_account_expense'].id,
                'rounding_method': 'HALF-UP',
            })

            document_params = self.init_document(
                lines=[{'price_unit': 32.4, 'tax_ids': taxes}],
                currency=self.foreign_currency,
                rate=0.5,
                cash_rounding=cash_rounding,
            )

            expected_values = {
                'same_tax_base': True,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 32.4,
                'base_amount': 64.8,
                'cash_rounding_base_amount_currency': -0.01,
                'cash_rounding_base_amount': -0.02,
                'tax_amount_currency': 15.71,
                'tax_amount': 31.42,
                'total_amount_currency': 48.1,
                'total_amount': 96.2,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 32.4,
                        'base_amount': 64.8,
                        'tax_amount_currency': 15.71,
                        'tax_amount': 31.42,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 32.4,
                                'base_amount': 64.8,
                                'tax_amount_currency': 15.71,
                                'tax_amount': 31.42,
                                'display_base_amount_currency': 32.4,
                                'display_base_amount': 64.8,
                            },
                        ],
                    },
                ],
            }
            yield 1, self.populate_document(document_params), expected_values
        with self.different_tax_group(taxes), self.with_tax_calculation_rounding_method('round_per_line'):
            cash_rounding = self.env['account.cash.rounding'].create({
                'name': 'biggest_tax',
                'rounding': 0.05,
                'strategy': 'biggest_tax',
                'rounding_method': 'HALF-UP',
            })

            document_params = self.init_document(
                lines=[{'price_unit': 32.4, 'tax_ids': taxes}],
                currency=self.foreign_currency,
                rate=0.5,
                cash_rounding=cash_rounding,
            )

            expected_values = {
                'same_tax_base': True,
                'currency_id': self.foreign_currency.id,
                'company_currency_id': self.currency.id,
                'base_amount_currency': 32.40,
                'base_amount': 64.8,
                'tax_amount_currency': 15.7,
                'tax_amount': 31.40,
                'total_amount_currency': 48.10,
                'total_amount': 96.2,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 32.40,
                        'base_amount': 64.8,
                        'tax_amount_currency': 15.7,
                        'tax_amount': 31.40,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 32.4,
                                'base_amount': 64.8,
                                'tax_amount_currency': 2.41,
                                'tax_amount': 4.82,
                                'display_base_amount_currency': 32.4,
                                'display_base_amount': 64.8,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 32.4,
                                'base_amount': 64.8,
                                'tax_amount_currency': 1.44,
                                'tax_amount': 2.88,
                                'display_base_amount_currency': 32.4,
                                'display_base_amount': 64.8,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 32.4,
                                'base_amount': 64.8,
                                'tax_amount_currency': 0.31,
                                'tax_amount': 0.62,
                                'display_base_amount_currency': 32.4,
                                'display_base_amount': 64.8,
                            },
                            {
                                'id': self.tax_groups[3].id,
                                'base_amount_currency': 32.4,
                                'base_amount': 64.8,
                                'tax_amount_currency': 4.33,
                                'tax_amount': 8.66,
                                'display_base_amount_currency': 32.4,
                                'display_base_amount': 64.8,
                            },
                            {
                                'id': self.tax_groups[4].id,
                                'base_amount_currency': 32.4,
                                'base_amount': 64.8,
                                'tax_amount_currency': 7.21,
                                'tax_amount': 14.42,
                                'display_base_amount_currency': 32.4,
                                'display_base_amount': 64.8,
                            },
                        ],
                    },
                ],
            }
            yield 2, self.populate_document(document_params), expected_values

    def test_cash_rounding_generic_helpers(self):
        for test_index, document, expected_values in self._test_cash_rounding():
            with self.subTest(test_index=test_index):
                self.assert_tax_totals_summary(document, expected_values)
        self._run_js_tests()

    def test_cash_rounding_invoices(self):
        for test_index, document, expected_values in self._test_cash_rounding():
            with self.subTest(test_index=test_index):
                invoice = self.convert_document_to_invoice(document)
                self.assert_invoice_tax_totals_summary(invoice, expected_values)

    def test_cash_rounding_with_excluded_tax_groups(self):
        # Excluded tax groups are not managed js-side nor on invoices. However, they are used
        # in some localizations to build another tax totals aside.
        tax1 = self.division_tax(5, tax_group_id=self.tax_groups[0].id)
        tax2 = self.division_tax(3, tax_group_id=self.tax_groups[1].id)
        tax3 = self.division_tax(0.65, tax_group_id=self.tax_groups[2].id)
        tax4 = self.division_tax(9, tax_group_id=self.tax_groups[3].id)
        tax5 = self.division_tax(15, tax_group_id=self.tax_groups[4].id)
        taxes = tax1 + tax2 + tax3 + tax4 + tax5

        cash_rounding = self.env['account.cash.rounding'].create({
            'name': 'biggest_tax',
            'rounding': 0.05,
            'strategy': 'biggest_tax',
            'rounding_method': 'HALF-UP',
        })

        document_params = self.init_document(
            lines=[{'price_unit': 32.4, 'tax_ids': taxes}],
            currency=self.foreign_currency,
            rate=0.5,
            cash_rounding=cash_rounding,
        )
        document = self.populate_document(document_params)
        expected_values = {
            'same_tax_base': True,
            'currency_id': self.foreign_currency.id,
            'company_currency_id': self.currency.id,
            'base_amount_currency': 44.25,
            'base_amount': 88.5,
            'tax_amount_currency': 3.85,
            'tax_amount': 7.7,
            'total_amount_currency': 48.10,
            'total_amount': 96.20,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 44.25,
                    'base_amount': 88.5,
                    'tax_amount_currency': 3.85,
                    'tax_amount': 7.7,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 32.4,
                            'base_amount': 64.8,
                            'tax_amount_currency': 2.41,
                            'tax_amount': 4.82,
                            'display_base_amount_currency': 32.4,
                            'display_base_amount': 64.8,
                        },
                        {
                            'id': self.tax_groups[1].id,
                            'base_amount_currency': 32.4,
                            'base_amount': 64.8,
                            'tax_amount_currency': 1.44,
                            'tax_amount': 2.88,
                            'display_base_amount_currency': 32.4,
                            'display_base_amount': 64.8,
                        },
                    ],
                },
            ],
        }
        self.assert_tax_totals_summary(document, expected_values, excluded_tax_group_ids=self.tax_groups[2:5].ids)

    def _test_mixed_combined_standalone_taxes(self):
        tax_10 = self.percent_tax(10.0)
        tax_10_incl_base = self.percent_tax(10.0, include_base_amount=True)
        tax_20 = self.percent_tax(20.0)
        taxes = tax_10 + tax_20 + tax_10_incl_base

        document1 = self.populate_document(self.init_document(
            lines=[
                {'price_unit': 1000.0, 'tax_ids': tax_10 + tax_20},
                {'price_unit': 1000.0, 'tax_ids': tax_10},
                {'price_unit': 1000.0, 'tax_ids': tax_20},
            ],
        ))
        document2 = self.populate_document(self.init_document(
            lines=[
                {'price_unit': 1000.0, 'tax_ids': tax_10_incl_base + tax_20},
                {'price_unit': 1000.0, 'tax_ids': tax_10_incl_base},
                {'price_unit': 1000.0, 'tax_ids': tax_20},
            ],
        ))

        with self.same_tax_group(taxes):
            expected_values = {
                'same_tax_base': True,
                'currency_id': self.currency.id,
                'base_amount_currency': 3000.0,
                'tax_amount_currency': 600.0,
                'total_amount_currency': 3600.0,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 3000.0,
                        'tax_amount_currency': 600.0,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 3000.0,
                                'tax_amount_currency': 600.0,
                                'display_base_amount_currency': 3000.0,
                            },
                        ],
                    },
                ],
            }
            yield 1, document1, expected_values
            expected_values = {
                'same_tax_base': True,
                'currency_id': self.currency.id,
                'base_amount_currency': 3000.0,
                'tax_amount_currency': 620.0,
                'total_amount_currency': 3620.0,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 3000.0,
                        'tax_amount_currency': 620.0,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 3000.0,
                                'tax_amount_currency': 620.0,
                                'display_base_amount_currency': 3000.0,
                            },
                        ],
                    },
                ],
            }
            yield 2, document2, expected_values
        with self.different_tax_group(taxes):
            expected_values = {
                'same_tax_base': False,
                'currency_id': self.currency.id,
                'base_amount_currency': 3000.0,
                'tax_amount_currency': 600.0,
                'total_amount_currency': 3600.0,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 3000.0,
                        'tax_amount_currency': 600.0,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[0].id,
                                'base_amount_currency': 2000.0,
                                'tax_amount_currency': 200.0,
                                'display_base_amount_currency': 2000.0,
                            },
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 2000.0,
                                'tax_amount_currency': 400.0,
                                'display_base_amount_currency': 2000.0,
                            },
                        ],
                    },
                ],
            }
            yield 3, document1, expected_values
            expected_values = {
                'same_tax_base': False,
                'currency_id': self.currency.id,
                'base_amount_currency': 3000.0,
                'tax_amount_currency': 620.0,
                'total_amount_currency': 3620.0,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 3000.0,
                        'tax_amount_currency': 620.0,
                        'tax_groups': [
                            {
                                'id': self.tax_groups[1].id,
                                'base_amount_currency': 2100.0,
                                'tax_amount_currency': 420.0,
                                'display_base_amount_currency': 2100.0,
                            },
                            {
                                'id': self.tax_groups[2].id,
                                'base_amount_currency': 2000.0,
                                'tax_amount_currency': 200.0,
                                'display_base_amount_currency': 2000.0,
                            },
                        ],
                    },
                ],
            }
            yield 4, document2, expected_values

    def test_mixed_combined_standalone_taxes_generic_helpers(self):
        for test_index, document, expected_values in self._test_mixed_combined_standalone_taxes():
            with self.subTest(test_index=test_index):
                self.assert_tax_totals_summary(document, expected_values)
        self._run_js_tests()

    def test_mixed_combined_standalone_taxes_invoices(self):
        for test_index, document, expected_values in self._test_mixed_combined_standalone_taxes():
            with self.subTest(test_index=test_index):
                invoice = self.convert_document_to_invoice(document)
                self.assert_invoice_tax_totals_summary(invoice, expected_values)

    def _test_preceding_subtotal(self):
        self.tax_groups[1].preceding_subtotal = "PRE GROUP 1"
        self.tax_groups[2].preceding_subtotal = "PRE GROUP 2"
        tax_10 = self.percent_tax(10.0, tax_group_id=self.tax_groups[1].id)
        tax_25 = self.percent_tax(25.0, tax_group_id=self.tax_groups[2].id)
        tax_42 = self.percent_tax(42.0, tax_group_id=self.tax_groups[0].id)

        document = self.populate_document(self.init_document([
            {'price_unit': 1000.0},
            {'price_unit': 1000.0, 'tax_ids': tax_10},
            {'price_unit': 1000.0, 'tax_ids': tax_25},
            {'price_unit': 100.0, 'tax_ids': tax_42},
            {'price_unit': 200.0, 'tax_ids': tax_42 + tax_10 + tax_25},
        ]))
        expected_values = {
            'same_tax_base': False,
            'currency_id': self.currency.id,
            'base_amount_currency': 3300.0,
            'tax_amount_currency': 546.0,
            'total_amount_currency': 3846.0,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 1300.0,
                    'tax_amount_currency': 126.0,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 300.0,
                            'tax_amount_currency': 126.0,
                            'display_base_amount_currency': 300.0,
                        },
                    ],
                },
                {
                    'name': "PRE GROUP 1",
                    'base_amount_currency': 1200.0,
                    'tax_amount_currency': 120.0,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[1].id,
                            'base_amount_currency': 1200.0,
                            'tax_amount_currency': 120.0,
                            'display_base_amount_currency': 1200.0,
                        },
                    ],
                },
                {
                    'name': "PRE GROUP 2",
                    'base_amount_currency': 1200.0,
                    'tax_amount_currency': 300.0,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[2].id,
                            'base_amount_currency': 1200.0,
                            'tax_amount_currency': 300.0,
                            'display_base_amount_currency': 1200.0,
                        },
                    ],
                },
            ],
        }
        yield 1, document, expected_values

        self.tax_groups[3].preceding_subtotal = "PRE GROUP 1"  # same as tax_groups[1], on purpose
        tax_10.tax_group_id = self.tax_groups[3]  # preceding_subtotal == "PRE GROUP 1"
        tax_42.tax_group_id = self.tax_groups[1]  # preceding_subtotal == "PRE GROUP 1"
        tax_minus_25 = self.percent_tax(-25.0, tax_group_id=self.tax_groups[2].id)  # preceding_subtotal == "PRE GROUP 2"
        tax_30 = self.percent_tax(30.0, tax_group_id=self.tax_groups[0].id)

        document = self.populate_document(self.init_document([
            {'price_unit': 100.0, 'tax_ids': tax_10},
            {'price_unit': 100.0, 'tax_ids': tax_minus_25 + tax_42 + tax_30},
            {'price_unit': 200.0, 'tax_ids': tax_10 + tax_minus_25},
            {'price_unit': 1000.0, 'tax_ids': tax_30},
            {'price_unit': 100.0, 'tax_ids': tax_30 + tax_10},
        ]))

        expected_values = {
            'same_tax_base': False,
            'currency_id': self.currency.id,
            'base_amount_currency': 1500.0,
            'tax_amount_currency': 367.0,
            'total_amount_currency': 1867.0,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 1200.0,
                    'tax_amount_currency': 360.0,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 1200.0,
                            'tax_amount_currency': 360.0,
                            'display_base_amount_currency': 1200.0,
                        },
                    ],
                },
                {
                    'name': "PRE GROUP 1",
                    'base_amount_currency': 500.0,
                    'tax_amount_currency': 82.0,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[1].id,
                            'base_amount_currency': 100.0,
                            'tax_amount_currency': 42.0,
                            'display_base_amount_currency': 100.0,
                        },
                        {
                            'id': self.tax_groups[3].id,
                            'base_amount_currency': 400.0,
                            'tax_amount_currency': 40.0,
                            'display_base_amount_currency': 400.0,
                        },
                    ],
                },
                {
                    'name': "PRE GROUP 2",
                    'base_amount_currency': 300.0,
                    'tax_amount_currency': -75.0,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[2].id,
                            'base_amount_currency': 300.0,
                            'tax_amount_currency': -75.0,
                            'display_base_amount_currency': 300.0,
                        },
                    ],
                },
            ],
        }
        yield 2, document, expected_values

    def test_preceding_subtotal_generic_helpers(self):
        for test_index, document, expected_values in self._test_preceding_subtotal():
            with self.subTest(test_index=test_index):
                self.assert_tax_totals_summary(document, expected_values)
        self._run_js_tests()

    def test_preceding_subtotal_invoices(self):
        for test_index, document, expected_values in self._test_preceding_subtotal():
            with self.subTest(test_index=test_index):
                invoice = self.convert_document_to_invoice(document)
                self.assert_invoice_tax_totals_summary(invoice, expected_values)

    def _test_preceding_subtotal_with_tax_group(self):
        self.tax_groups[1].preceding_subtotal = "Tax withholding"
        tax_minus_47 = self.percent_tax(-47.0, tax_group_id=self.tax_groups[1].id)
        tax_10 = self.percent_tax(10.0, tax_group_id=self.tax_groups[0].id)
        tax_group = self.group_of_taxes(tax_minus_47 + tax_10)

        document = self.populate_document(self.init_document([
            {'price_unit': 100.0, 'tax_ids': tax_group},
        ]))

        expected_values = {
            'same_tax_base': True,
            'currency_id': self.currency.id,
            'base_amount_currency': 100.0,
            'tax_amount_currency': -37.0,
            'total_amount_currency': 63.0,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 100.0,
                    'tax_amount_currency': 10.0,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 100.0,
                            'tax_amount_currency': 10.0,
                            'display_base_amount_currency': 100.0,
                        },
                    ],
                },
                {
                    'name': "Tax withholding",
                    'base_amount_currency': 100.0,
                    'tax_amount_currency': -47.0,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[1].id,
                            'base_amount_currency': 100.0,
                            'tax_amount_currency': -47.0,
                            'display_base_amount_currency': 100.0,
                        },
                    ],
                },
            ],
        }
        yield 1, document, expected_values

    def test_preceding_subtotal_with_tax_group_generic_helpers(self):
        for test_index, document, expected_values in self._test_preceding_subtotal_with_tax_group():
            with self.subTest(test_index=test_index):
                self.assert_tax_totals_summary(document, expected_values)
        self._run_js_tests()

    def test_preceding_subtotal_with_tax_group_invoices(self):
        for test_index, document, expected_values in self._test_preceding_subtotal_with_tax_group():
            with self.subTest(test_index=test_index):
                invoice = self.convert_document_to_invoice(document)
                self.assert_invoice_tax_totals_summary(invoice, expected_values)

    def _test_reverse_charge_percent_tax(self):
        tax = self.percent_tax(
            21.0,
            invoice_repartition_line_ids=[
                Command.create({'repartition_type': 'base', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': -100.0}),
            ],
            refund_repartition_line_ids=[
                Command.create({'repartition_type': 'base', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': -100.0}),
            ],
        )

        document = self.populate_document(self.init_document([
            {'price_unit': 100.0, 'tax_ids': tax},
        ]))

        expected_values = {
            'same_tax_base': True,
            'currency_id': self.currency.id,
            'base_amount_currency': 100.0,
            'tax_amount_currency': 0.0,
            'total_amount_currency': 100.0,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 100.0,
                    'tax_amount_currency': 0.0,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 100.0,
                            'tax_amount_currency': 0.0,
                            'display_base_amount_currency': 100.0,
                        },
                    ],
                },
            ],
        }
        yield 1, document, expected_values

        tax.price_include_override = 'tax_included'
        document = self.populate_document(self.init_document([
            {'price_unit': 121.0, 'tax_ids': tax},
        ]))

        expected_values = {
            'same_tax_base': True,
            'currency_id': self.currency.id,
            'base_amount_currency': 100.0,
            'tax_amount_currency': 0.0,
            'total_amount_currency': 100.0,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 100.0,
                    'tax_amount_currency': 0.0,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 100.0,
                            'tax_amount_currency': 0.0,
                            'display_base_amount_currency': 100.0,
                        },
                    ],
                },
            ],
        }
        yield 2, document, expected_values

    def test_reverse_charge_percent_tax_generic_helpers(self):
        for test_index, document, expected_values in self._test_reverse_charge_percent_tax():
            with self.subTest(test_index=test_index):
                self.assert_tax_totals_summary(document, expected_values)
        self._run_js_tests()

    def test_reverse_charge_percent_tax_invoices(self):
        for test_index, document, expected_values in self._test_reverse_charge_percent_tax():
            with self.subTest(test_index=test_index):
                invoice = self.convert_document_to_invoice(document)
                self.assert_invoice_tax_totals_summary(invoice, expected_values)
                self.assertRecordValues(invoice.invoice_line_ids, [{
                    'price_subtotal': 100.0,
                    'price_total': 100.0,
                }])

    def _test_reverse_charge_division_tax(self):
        tax = self.division_tax(
            21.0,
            invoice_repartition_line_ids=[
                Command.create({'repartition_type': 'base', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': -100.0}),
            ],
            refund_repartition_line_ids=[
                Command.create({'repartition_type': 'base', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': -100.0}),
            ],
        )

        document = self.populate_document(self.init_document([
            {'price_unit': 79.0, 'tax_ids': tax},
        ]))

        expected_values = {
            'same_tax_base': True,
            'currency_id': self.currency.id,
            'base_amount_currency': 79.0,
            'tax_amount_currency': 0.0,
            'total_amount_currency': 79.0,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 79.0,
                    'tax_amount_currency': 0.0,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 79.0,
                            'tax_amount_currency': 0.0,
                            'display_base_amount_currency': 79.0,
                        },
                    ],
                },
            ],
        }
        yield 1, document, expected_values

        tax.price_include_override = 'tax_included'
        document = self.populate_document(self.init_document([
            {'price_unit': 100.0, 'tax_ids': tax},
        ]))

        expected_values = {
            'same_tax_base': True,
            'currency_id': self.currency.id,
            'base_amount_currency': 79.0,
            'tax_amount_currency': 0.0,
            'total_amount_currency': 79.0,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 79.0,
                    'tax_amount_currency': 0.0,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 79.0,
                            'tax_amount_currency': 0.0,
                            'display_base_amount_currency': 79.0,
                        },
                    ],
                },
            ],
        }
        yield 2, document, expected_values

    def test_reverse_charge_division_tax_generic_helpers(self):
        for test_index, document, expected_values in self._test_reverse_charge_division_tax():
            with self.subTest(test_index=test_index):
                self.assert_tax_totals_summary(document, expected_values)
        self._run_js_tests()

    def test_reverse_charge_division_tax_invoices(self):
        for test_index, document, expected_values in self._test_reverse_charge_division_tax():
            with self.subTest(test_index=test_index):
                invoice = self.convert_document_to_invoice(document)
                self.assert_invoice_tax_totals_summary(invoice, expected_values)
                self.assertRecordValues(invoice.invoice_line_ids, [{
                    'price_subtotal': 79.0,
                    'price_total': 79.0,
                }])

    def _test_discount_with_round_globally(self):
        self.env.company.tax_calculation_rounding_method = 'round_globally'
        tax = self.percent_tax(21.0)

        document_params = self.init_document([
            {'price_unit': 5.75, 'quantity': 5.0, 'discount': 18.0, 'tax_ids': tax},
            {'price_unit': 5.75, 'quantity': 5.0, 'discount': 18.0, 'tax_ids': tax},
            {'price_unit': 5.75, 'quantity': 5.0, 'discount': 18.0, 'tax_ids': tax},
            {'price_unit': 5.75, 'quantity': 5.0, 'discount': 18.0, 'tax_ids': tax},
            {'price_unit': 5.75, 'quantity': 5.0, 'discount': 18.0, 'tax_ids': tax},
            {'price_unit': 5.75, 'quantity': 5.0, 'discount': 18.0, 'tax_ids': tax},
        ])

        document = self.populate_document(document_params)
        expected_values = {
            'same_tax_base': True,
            'currency_id': self.currency.id,
            'base_amount_currency': 141.45,
            'tax_amount_currency': 29.70,
            'total_amount_currency': 171.15,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 141.45,
                    'tax_amount_currency': 29.70,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 141.45,
                            'tax_amount_currency': 29.70,
                            'display_base_amount_currency': 141.45,
                        },
                    ],
                },
            ],
        }
        yield 1, document, expected_values

        tax.price_include_override = 'tax_included'
        document = self.populate_document(document_params)
        expected_values = {
            'same_tax_base': True,
            'currency_id': self.currency.id,
            'base_amount_currency': 116.90,
            'tax_amount_currency': 24.55,
            'total_amount_currency': 141.45,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 116.90,
                    'tax_amount_currency': 24.55,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 116.90,
                            'tax_amount_currency': 24.55,
                            'display_base_amount_currency': 116.90,
                        },
                    ],
                },
            ],
        }
        yield 2, document, expected_values

    def test_discount_with_round_globally_generic_helpers(self):
        for test_index, document, expected_values in self._test_discount_with_round_globally():
            with self.subTest(test_index=test_index):
                self.assert_tax_totals_summary(document, expected_values)
        self._run_js_tests()

    def test_discount_with_round_globally_invoices(self):
        for test_index, document, expected_values in self._test_discount_with_round_globally():
            with self.subTest(test_index=test_index):
                invoice = self.convert_document_to_invoice(document)
                self.assert_invoice_tax_totals_summary(invoice, expected_values)

    def test_archived_tax_in_tax_totals(self):
        tax_10 = self.percent_tax(15.0)
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_date': '2020-01-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(tax_10.ids)],
                })
            ],
        })

        expected_values = {
            'same_tax_base': True,
            'currency_id': self.currency.id,
            'base_amount_currency': 100.0,
            'tax_amount_currency': 15.0,
            'total_amount_currency': 115.0,
            'subtotals': [
                {
                    'name': "Untaxed Amount",
                    'base_amount_currency': 100.0,
                    'tax_amount_currency': 15.0,
                    'tax_groups': [
                        {
                            'id': self.tax_groups[0].id,
                            'base_amount_currency': 100.0,
                            'tax_amount_currency': 15.0,
                            'display_base_amount_currency': 100.0,
                        },
                    ],
                },
            ],
        }
        self._assert_tax_totals_summary(invoice.tax_totals, expected_values)
        tax_10.active = False
        invoice.env.invalidate_all()
        self._assert_tax_totals_summary(invoice.tax_totals, expected_values)
