from contextlib import contextmanager

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
            for i in range(1, 6)
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

    def test_taxes_l10n_in(self):
        tests = []
        tax1 = self.percent_tax(6, include_base_amount=True)
        tax2 = self.percent_tax(6, include_base_amount=True, is_base_affected=False)
        tax3 = self.percent_tax(3)
        taxes = tax1 + tax2 + tax3

        with self.same_tax_group(taxes):
            tests.extend([
                self._prepare_tax_totals_summary_test(
                    self._prepare_document_params(
                        rounding_method='round_per_line',
                        currency=self.foreign_currency,
                    ),
                    [
                        self._prepare_document_line_params(15.89, taxes=taxes, rate=0.2),
                        self._prepare_document_line_params(15.89, taxes=taxes, rate=0.2),
                    ],
                    {
                        'same_tax_base': True,
                        'currency_id': self.foreign_currency.id,
                        'company_currency_id': self.currency.id,
                        'base_amount_currency': 31.78,
                        'base_amount': 6.36,
                        'tax_amount_currency': 4.86,
                        'tax_amount': 0.97,
                        'total_amount_currency': 36.64,
                        'total_amount': 7.33,
                        'subtotals': [
                            {
                                'name': "Untaxed Amount",
                                'base_amount_currency': 31.78,
                                'base_amount': 6.36,
                                'tax_amount_currency': 4.86,
                                'tax_amount': 0.97,
                                'tax_groups': [
                                    {
                                        'id': self.tax_groups[0].id,
                                        'base_amount_currency': 31.78,
                                        'base_amount': 6.36,
                                        'tax_amount_currency': 4.86,
                                        'tax_amount': 0.97,
                                        'display_base_amount_currency': 31.78,
                                        'display_base_amount': 6.36,
                                        'group_name': self.tax_groups[0].name,
                                    },
                                ],
                            },
                        ],
                    },
                ),
                self._prepare_tax_totals_summary_test(
                    self._prepare_document_params(
                        rounding_method='round_globally',
                        currency=self.foreign_currency,
                    ),
                    [
                        self._prepare_document_line_params(15.89, taxes=taxes, rate=0.2),
                        self._prepare_document_line_params(15.89, taxes=taxes, rate=0.2),
                    ],
                    {
                        'same_tax_base': True,
                        'currency_id': self.foreign_currency.id,
                        'company_currency_id': self.currency.id,
                        'base_amount_currency': 31.78,
                        'base_amount': 6.36,
                        'tax_amount_currency': 4.890000000000001,
                        'tax_amount': 0.97,
                        'total_amount_currency': 36.67,
                        'total_amount': 7.33,
                        'subtotals': [
                            {
                                'name': "Untaxed Amount",
                                'base_amount_currency': 31.78,
                                'base_amount': 6.36,
                                'tax_amount_currency': 4.890000000000001,
                                'tax_amount': 0.97,
                                'tax_groups': [
                                    {
                                        'id': self.tax_groups[0].id,
                                        'base_amount_currency': 31.78,
                                        'base_amount': 6.36,
                                        'tax_amount_currency': 4.890000000000001,
                                        'tax_amount': 0.97,
                                        'display_base_amount_currency': 31.78,
                                        'display_base_amount': 6.36,
                                        'group_name': self.tax_groups[0].name,
                                    },
                                ],
                            },
                        ],
                    },
                ),
            ])

        with self.different_tax_group(taxes):
            tests.extend([
                self._prepare_total_per_tax_summary_test(
                    self._prepare_document_params(rounding_method='round_per_line'),
                    [
                        self._prepare_document_line_params(15.89, taxes=taxes),
                        self._prepare_document_line_params(15.89, taxes=taxes),
                    ],
                    {
                        'base_amount_currency': 31.78,
                        'tax_amount_currency': 4.86,
                        'total_amount_currency': 36.64,
                        'subtotals': {
                            tax1.id: {
                                'base_amount_currency': 31.78,
                                'tax_amount_currency': 1.9000000000000001,
                                'display_base_amount_currency': 31.78,
                            },
                            tax2.id: {
                                'base_amount_currency': 31.78,
                                'tax_amount_currency': 1.9000000000000001,
                                'display_base_amount_currency': 31.78,
                            },
                            tax3.id: {
                                'base_amount_currency': 35.58,
                                'tax_amount_currency': 1.06,
                                'display_base_amount_currency': 35.58,
                            },
                        },
                    },
                ),
                self._prepare_tax_totals_summary_test(
                    self._prepare_document_params(
                        rounding_method='round_per_line',
                        currency=self.foreign_currency,
                    ),
                    [
                        self._prepare_document_line_params(15.89, taxes=taxes, rate=0.2),
                        self._prepare_document_line_params(15.89, taxes=taxes, rate=0.2),
                    ],
                    {
                        'same_tax_base': False,
                        'currency_id': self.foreign_currency.id,
                        'company_currency_id': self.currency.id,
                        'base_amount_currency': 31.78,
                        'base_amount': 6.36,
                        'tax_amount_currency': 4.86,
                        'tax_amount': 0.97,
                        'total_amount_currency': 36.64,
                        'total_amount': 7.33,
                        'subtotals': [
                            {
                                'name': "Untaxed Amount",
                                'base_amount_currency': 31.78,
                                'base_amount': 6.36,
                                'tax_amount_currency': 4.86,
                                'tax_amount': 0.97,
                                'tax_groups': [
                                    {
                                        'id': self.tax_groups[0].id,
                                        'base_amount_currency': 31.78,
                                        'base_amount': 6.36,
                                        'tax_amount_currency': 1.9000000000000001,
                                        'tax_amount': 0.38,
                                        'display_base_amount_currency': 31.78,
                                        'display_base_amount': 6.36,
                                        'group_name': self.tax_groups[0].name,
                                    },
                                    {
                                        'id': self.tax_groups[1].id,
                                        'base_amount_currency': 31.78,
                                        'base_amount': 6.36,
                                        'tax_amount_currency': 1.9000000000000001,
                                        'tax_amount': 0.38,
                                        'display_base_amount_currency': 31.78,
                                        'display_base_amount': 6.36,
                                        'group_name': self.tax_groups[1].name,
                                    },
                                    {
                                        'id': self.tax_groups[2].id,
                                        'base_amount_currency': 35.58,
                                        'base_amount': 7.12,
                                        'tax_amount_currency': 1.06,
                                        'tax_amount': 0.21,
                                        'display_base_amount_currency': 35.58,
                                        'display_base_amount': 7.12,
                                        'group_name': self.tax_groups[2].name,
                                    },
                                ],
                            },
                        ],
                    },
                ),
                self._prepare_total_per_tax_summary_test(
                    self._prepare_document_params(rounding_method='round_globally'),
                    [
                        self._prepare_document_line_params(15.89, taxes=taxes),
                        self._prepare_document_line_params(15.89, taxes=taxes),
                    ],
                    {
                        'base_amount_currency': 31.78,
                        'tax_amount_currency': 4.890000000000001,
                        'total_amount_currency': 36.67,
                        'subtotals': {
                            tax1.id: {
                                'base_amount_currency': 31.78,
                                'tax_amount_currency': 1.9100000000000001,
                                'display_base_amount_currency': 31.78,
                            },
                            tax2.id: {
                                'base_amount_currency': 31.78,
                                'tax_amount_currency': 1.9100000000000001,
                                'display_base_amount_currency': 31.78,
                            },
                            tax3.id: {
                                'base_amount_currency': 35.59,
                                'tax_amount_currency': 1.07,
                                'display_base_amount_currency': 35.59,
                            },
                        },
                    },
                ),
                self._prepare_tax_totals_summary_test(
                    self._prepare_document_params(
                        rounding_method='round_globally',
                        currency=self.foreign_currency,
                    ),
                    [
                        self._prepare_document_line_params(15.89, taxes=taxes, rate=0.2),
                        self._prepare_document_line_params(15.89, taxes=taxes, rate=0.2),
                    ],
                    {
                        'same_tax_base': False,
                        'currency_id': self.foreign_currency.id,
                        'company_currency_id': self.currency.id,
                        'base_amount_currency': 31.78,
                        'base_amount': 6.36,
                        'tax_amount_currency': 4.890000000000001,
                        'tax_amount': 0.97,
                        'total_amount_currency': 36.67,
                        'total_amount': 7.33,
                        'subtotals': [
                            {
                                'name': "Untaxed Amount",
                                'base_amount_currency': 31.78,
                                'base_amount': 6.36,
                                'tax_amount_currency': 4.890000000000001,
                                'tax_amount': 0.97,
                                'tax_groups': [
                                    {
                                        'id': self.tax_groups[0].id,
                                        'base_amount_currency': 31.78,
                                        'base_amount': 6.36,
                                        'tax_amount_currency': 1.9100000000000001,
                                        'tax_amount': 0.38,
                                        'display_base_amount_currency': 31.78,
                                        'display_base_amount': 6.36,
                                        'group_name': self.tax_groups[0].name,
                                    },
                                    {
                                        'id': self.tax_groups[1].id,
                                        'base_amount_currency': 31.78,
                                        'base_amount': 6.36,
                                        'tax_amount_currency': 1.9100000000000001,
                                        'tax_amount': 0.38,
                                        'display_base_amount_currency': 31.78,
                                        'display_base_amount': 6.36,
                                        'group_name': self.tax_groups[1].name,
                                    },
                                    {
                                        'id': self.tax_groups[2].id,
                                        'base_amount_currency': 35.59,
                                        'base_amount': 7.12,
                                        'tax_amount_currency': 1.07,
                                        'tax_amount': 0.21,
                                        'display_base_amount_currency': 35.59,
                                        'display_base_amount': 7.12,
                                        'group_name': self.tax_groups[2].name,
                                    },
                                ],
                            },
                        ],
                    },
                ),
            ])

        tax1.price_include = True
        tax2.price_include = True
        with self.same_tax_group(taxes):
            tests.extend([
                self._prepare_tax_totals_summary_test(
                    self._prepare_document_params(
                        rounding_method='round_per_line',
                        currency=self.foreign_currency,
                    ),
                    [
                        self._prepare_document_line_params(17.79, taxes=taxes, rate=0.2),
                        self._prepare_document_line_params(17.79, taxes=taxes, rate=0.2),
                    ],
                    {
                        'same_tax_base': True,
                        'currency_id': self.foreign_currency.id,
                        'company_currency_id': self.currency.id,
                        'base_amount_currency': 31.78,
                        'base_amount': 6.36,
                        'tax_amount_currency': 4.86,
                        'tax_amount': 0.97,
                        'total_amount_currency': 36.64,
                        'total_amount': 7.33,
                        'subtotals': [
                            {
                                'name': "Untaxed Amount",
                                'base_amount_currency': 31.78,
                                'base_amount': 6.36,
                                'tax_amount_currency': 4.86,
                                'tax_amount': 0.97,
                                'tax_groups': [
                                    {
                                        'id': self.tax_groups[0].id,
                                        'base_amount_currency': 31.78,
                                        'base_amount': 6.36,
                                        'tax_amount_currency': 4.86,
                                        'tax_amount': 0.97,
                                        'display_base_amount_currency': 31.78,
                                        'display_base_amount': 6.36,
                                        'group_name': self.tax_groups[0].name,
                                    },
                                ],
                            },
                        ],
                    },
                ),
                self._prepare_tax_totals_summary_test(
                    self._prepare_document_params(
                        rounding_method='round_globally',
                        currency=self.foreign_currency,
                    ),
                    [
                        self._prepare_document_line_params(17.79, taxes=taxes, rate=0.2),
                        self._prepare_document_line_params(17.79, taxes=taxes, rate=0.2),
                    ],
                    {
                        'same_tax_base': True,
                        'currency_id': self.foreign_currency.id,
                        'company_currency_id': self.currency.id,
                        'base_amount_currency': 31.77,
                        'base_amount': 6.3500000000000005,
                        'tax_amount_currency': 4.890000000000001,
                        'tax_amount': 0.97,
                        'total_amount_currency': 36.66,
                        'total_amount': 7.32,
                        'subtotals': [
                            {
                                'name': "Untaxed Amount",
                                'base_amount_currency': 31.77,
                                'base_amount': 6.3500000000000005,
                                'tax_amount_currency': 4.890000000000001,
                                'tax_amount': 0.97,
                                'tax_groups': [
                                    {
                                        'id': self.tax_groups[0].id,
                                        'base_amount_currency': 31.77,
                                        'base_amount': 6.3500000000000005,
                                        'tax_amount_currency': 4.890000000000001,
                                        'tax_amount': 0.97,
                                        'display_base_amount_currency': 31.77,
                                        'display_base_amount': 6.3500000000000005,
                                        'group_name': self.tax_groups[0].name,
                                    },
                                ],
                            },
                        ],
                    },
                ),
            ])

        with self.different_tax_group(taxes):
            tests.extend([
                self._prepare_total_per_tax_summary_test(
                    self._prepare_document_params(rounding_method='round_per_line'),
                    [
                        self._prepare_document_line_params(17.79, taxes=taxes),
                        self._prepare_document_line_params(17.79, taxes=taxes),
                    ],
                    {
                        'base_amount_currency': 31.78,
                        'tax_amount_currency': 4.86,
                        'total_amount_currency': 36.64,
                        'subtotals': {
                            tax1.id: {
                                'base_amount_currency': 31.78,
                                'tax_amount_currency': 1.9000000000000001,
                                'display_base_amount_currency': 31.78,
                            },
                            tax2.id: {
                                'base_amount_currency': 31.78,
                                'tax_amount_currency': 1.9000000000000001,
                                'display_base_amount_currency': 31.78,
                            },
                            tax3.id: {
                                'base_amount_currency': 35.58,
                                'tax_amount_currency': 1.06,
                                'display_base_amount_currency': 35.58,
                            },
                        },
                    },
                ),
                self._prepare_tax_totals_summary_test(
                    self._prepare_document_params(
                        rounding_method='round_per_line',
                        currency=self.foreign_currency,
                    ),
                    [
                        self._prepare_document_line_params(17.79, taxes=taxes, rate=0.2),
                        self._prepare_document_line_params(17.79, taxes=taxes, rate=0.2),
                    ],
                    {
                        'same_tax_base': False,
                        'currency_id': self.foreign_currency.id,
                        'company_currency_id': self.currency.id,
                        'base_amount_currency': 31.78,
                        'base_amount': 6.36,
                        'tax_amount_currency': 4.86,
                        'tax_amount': 0.97,
                        'total_amount_currency': 36.64,
                        'total_amount': 7.33,
                        'subtotals': [
                            {
                                'name': "Untaxed Amount",
                                'base_amount_currency': 31.78,
                                'base_amount': 6.36,
                                'tax_amount_currency': 4.86,
                                'tax_amount': 0.97,
                                'tax_groups': [
                                    {
                                        'id': self.tax_groups[0].id,
                                        'base_amount_currency': 31.78,
                                        'base_amount': 6.36,
                                        'tax_amount_currency': 1.9000000000000001,
                                        'tax_amount': 0.38,
                                        'display_base_amount_currency': 31.78,
                                        'display_base_amount': 6.36,
                                        'group_name': self.tax_groups[0].name,
                                    },
                                    {
                                        'id': self.tax_groups[1].id,
                                        'base_amount_currency': 31.78,
                                        'base_amount': 6.36,
                                        'tax_amount_currency': 1.9000000000000001,
                                        'tax_amount': 0.38,
                                        'display_base_amount_currency': 31.78,
                                        'display_base_amount': 6.36,
                                        'group_name': self.tax_groups[1].name,
                                    },
                                    {
                                        'id': self.tax_groups[2].id,
                                        'base_amount_currency': 35.58,
                                        'base_amount': 7.12,
                                        'tax_amount_currency': 1.06,
                                        'tax_amount': 0.21,
                                        'display_base_amount_currency': 35.58,
                                        'display_base_amount': 7.12,
                                        'group_name': self.tax_groups[2].name,
                                    },
                                ],
                            },
                        ],
                    },
                ),
                self._prepare_total_per_tax_summary_test(
                    self._prepare_document_params(rounding_method='round_globally'),
                    [
                        self._prepare_document_line_params(17.79, taxes=taxes),
                        self._prepare_document_line_params(17.79, taxes=taxes),
                    ],
                    {
                        'base_amount_currency': 31.77,
                        'tax_amount_currency': 4.890000000000001,
                        'total_amount_currency': 36.66,
                        'subtotals': {
                            tax1.id: {
                                'base_amount_currency': 31.77,
                                'tax_amount_currency': 1.9100000000000001,
                                'display_base_amount_currency': 31.77,
                            },
                            tax2.id: {
                                'base_amount_currency': 31.77,
                                'tax_amount_currency': 1.9100000000000001,
                                'display_base_amount_currency': 31.77,
                            },
                            tax3.id: {
                                'base_amount_currency': 35.58,
                                'tax_amount_currency': 1.07,
                                'display_base_amount_currency': 35.58,
                            },
                        },
                    },
                ),
                self._prepare_tax_totals_summary_test(
                    self._prepare_document_params(
                        rounding_method='round_globally',
                        currency=self.foreign_currency,
                    ),
                    [
                        self._prepare_document_line_params(17.79, taxes=taxes, rate=0.2),
                        self._prepare_document_line_params(17.79, taxes=taxes, rate=0.2),
                    ],
                    {
                        'same_tax_base': False,
                        'currency_id': self.foreign_currency.id,
                        'company_currency_id': self.currency.id,
                        'base_amount_currency': 31.77,
                        'base_amount': 6.3500000000000005,
                        'tax_amount_currency': 4.890000000000001,
                        'tax_amount': 0.97,
                        'total_amount_currency': 36.66,
                        'total_amount': 7.32,
                        'subtotals': [
                            {
                                'name': "Untaxed Amount",
                                'base_amount_currency': 31.77,
                                'base_amount': 6.3500000000000005,
                                'tax_amount_currency': 4.890000000000001,
                                'tax_amount': 0.97,
                                'tax_groups': [
                                    {
                                        'id': self.tax_groups[0].id,
                                        'base_amount_currency': 31.77,
                                        'base_amount': 6.3500000000000005,
                                        'tax_amount_currency': 1.9100000000000001,
                                        'tax_amount': 0.38,
                                        'display_base_amount_currency': 31.77,
                                        'display_base_amount': 6.3500000000000005,
                                        'group_name': self.tax_groups[0].name,
                                    },
                                    {
                                        'id': self.tax_groups[1].id,
                                        'base_amount_currency': 31.77,
                                        'base_amount': 6.3500000000000005,
                                        'tax_amount_currency': 1.9100000000000001,
                                        'tax_amount': 0.38,
                                        'display_base_amount_currency': 31.77,
                                        'display_base_amount': 6.3500000000000005,
                                        'group_name': self.tax_groups[1].name,
                                    },
                                    {
                                        'id': self.tax_groups[2].id,
                                        'base_amount_currency': 35.58,
                                        'base_amount': 7.12,
                                        'tax_amount_currency': 1.07,
                                        'tax_amount': 0.21,
                                        'display_base_amount_currency': 35.58,
                                        'display_base_amount': 7.12,
                                        'group_name': self.tax_groups[2].name,
                                    },
                                ],
                            },
                        ],
                    },
                ),
            ])
        self._assert_tests(tests)

    def test_taxes_l10n_br(self):
        tests = []
        tax1 = self.division_tax(5)
        tax2 = self.division_tax(3)
        tax3 = self.division_tax(0.65)
        tax4 = self.division_tax(9)
        tax5 = self.division_tax(15)
        taxes = tax1 + tax2 + tax3 + tax4 + tax5

        with self.same_tax_group(taxes):
            for rounding_method in ('round_per_line', 'round_globally'):
                tests.append(
                    self._prepare_tax_totals_summary_test(
                        self._prepare_document_params(
                            rounding_method=rounding_method,
                            currency=self.foreign_currency,
                        ),
                        [
                            self._prepare_document_line_params(32.33, taxes=taxes, rate=0.3333),
                            self._prepare_document_line_params(32.33, taxes=taxes, rate=0.3333),
                        ],
                        {
                            'same_tax_base': True,
                            'currency_id': self.foreign_currency.id,
                            'company_currency_id': self.currency.id,
                            'base_amount_currency': 64.66,
                            'base_amount': 21.55,
                            'tax_amount_currency': 31.339999999999996,
                            'tax_amount': 10.45,
                            'total_amount_currency': 96.0,
                            'total_amount': 32.0,
                            'subtotals': [
                                {
                                    'name': "Untaxed Amount",
                                    'base_amount_currency': 64.66,
                                    'base_amount': 21.55,
                                    'tax_amount_currency': 31.339999999999996,
                                    'tax_amount': 10.45,
                                    'tax_groups': [
                                        {
                                            'id': self.tax_groups[0].id,
                                            'base_amount_currency': 64.66,
                                            'base_amount': 21.55,
                                            'tax_amount_currency': 31.339999999999996,
                                            'tax_amount': 10.45,
                                            'display_base_amount_currency': 64.66,
                                            'display_base_amount': 21.55,
                                            'group_name': self.tax_groups[0].name,
                                        },
                                    ],
                                },
                            ],
                        },
                    ),
                )

        with self.different_tax_group(taxes):
            for rounding_method in ('round_per_line', 'round_globally'):
                tests.extend([
                    self._prepare_total_per_tax_summary_test(
                        self._prepare_document_params(rounding_method=rounding_method),
                        [
                            self._prepare_document_line_params(32.33, taxes=taxes),
                            self._prepare_document_line_params(32.33, taxes=taxes),
                        ],
                        {
                            'base_amount_currency': 64.66,
                            'tax_amount_currency': 31.339999999999996,
                            'total_amount_currency': 96.0,
                            'subtotals': {
                                tax1.id: {
                                    'base_amount_currency': 64.66,
                                    'tax_amount_currency': 4.8,
                                    'display_base_amount_currency': 64.66,
                                },
                                tax2.id: {
                                    'base_amount_currency': 64.66,
                                    'tax_amount_currency': 2.88,
                                    'display_base_amount_currency': 64.66,
                                },
                                tax3.id: {
                                    'base_amount_currency': 64.66,
                                    'tax_amount_currency': 0.62,
                                    'display_base_amount_currency': 64.66,
                                },
                                tax4.id: {
                                    'base_amount_currency': 64.66,
                                    'tax_amount_currency': 8.64,
                                    'display_base_amount_currency': 64.66,
                                },
                                tax5.id: {
                                    'base_amount_currency': 64.66,
                                    'tax_amount_currency': 14.4,
                                    'display_base_amount_currency': 64.66,
                                },
                            },
                        },
                    ),
                    self._prepare_tax_totals_summary_test(
                        self._prepare_document_params(
                            rounding_method=rounding_method,
                            currency=self.foreign_currency,
                        ),
                        [
                            self._prepare_document_line_params(32.33, taxes=taxes, rate=0.3333),
                            self._prepare_document_line_params(32.33, taxes=taxes, rate=0.3333),
                        ],
                        {
                            'same_tax_base': True,
                            'currency_id': self.foreign_currency.id,
                            'company_currency_id': self.currency.id,
                            'base_amount_currency': 64.66,
                            'base_amount': 21.55,
                            'tax_amount_currency': 31.339999999999996,
                            'tax_amount': 10.45,
                            'total_amount_currency': 96.0,
                            'total_amount': 32.0,
                            'subtotals': [
                                {
                                    'name': "Untaxed Amount",
                                    'base_amount_currency': 64.66,
                                    'base_amount': 21.55,
                                    'tax_amount_currency': 31.339999999999996,
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
                                            'group_name': self.tax_groups[0].name,
                                        },
                                        {
                                            'id': self.tax_groups[1].id,
                                            'base_amount_currency': 64.66,
                                            'base_amount': 21.55,
                                            'tax_amount_currency': 2.88,
                                            'tax_amount': 0.96,
                                            'display_base_amount_currency': 64.66,
                                            'display_base_amount': 21.55,
                                            'group_name': self.tax_groups[1].name,
                                        },
                                        {
                                            'id': self.tax_groups[2].id,
                                            'base_amount_currency': 64.66,
                                            'base_amount': 21.55,
                                            'tax_amount_currency': 0.62,
                                            'tax_amount': 0.21,
                                            'display_base_amount_currency': 64.66,
                                            'display_base_amount': 21.55,
                                            'group_name': self.tax_groups[2].name,
                                        },
                                        {
                                            'id': self.tax_groups[3].id,
                                            'base_amount_currency': 64.66,
                                            'base_amount': 21.55,
                                            'tax_amount_currency': 8.64,
                                            'tax_amount': 2.88,
                                            'display_base_amount_currency': 64.66,
                                            'display_base_amount': 21.55,
                                            'group_name': self.tax_groups[3].name,
                                        },
                                        {
                                            'id': self.tax_groups[4].id,
                                            'base_amount_currency': 64.66,
                                            'base_amount': 21.55,
                                            'tax_amount_currency': 14.4,
                                            'tax_amount': 4.8,
                                            'display_base_amount_currency': 64.66,
                                            'display_base_amount': 21.55,
                                            'group_name': self.tax_groups[4].name,
                                        },
                                    ],
                                },
                            ],
                        },
                    )
                ])

        taxes.price_include = True
        with self.same_tax_group(taxes):
            tests.extend([
                self._prepare_tax_totals_summary_test(
                    self._prepare_document_params(
                        rounding_method='round_per_line',
                        currency=self.foreign_currency,
                    ),
                    [
                        self._prepare_document_line_params(48.0, taxes=taxes, rate=0.3333),
                        self._prepare_document_line_params(48.0, taxes=taxes, rate=0.3333),
                    ],
                    {
                        'same_tax_base': True,
                        'currency_id': self.foreign_currency.id,
                        'company_currency_id': self.currency.id,
                        'base_amount_currency': 64.66,
                        'base_amount': 21.55,
                        'tax_amount_currency': 31.339999999999996,
                        'tax_amount': 10.45,
                        'total_amount_currency': 96.0,
                        'total_amount': 32.0,
                        'subtotals': [
                            {
                                'name': "Untaxed Amount",
                                'base_amount_currency': 64.66,
                                'base_amount': 21.55,
                                'tax_amount_currency': 31.339999999999996,
                                'tax_amount': 10.45,
                                'tax_groups': [
                                    {
                                        'id': self.tax_groups[0].id,
                                        'base_amount_currency': 64.66,
                                        'base_amount': 21.55,
                                        'tax_amount_currency': 31.339999999999996,
                                        'tax_amount': 10.45,
                                        'display_base_amount_currency': 96.0,
                                        'display_base_amount': 32.0,
                                        'group_name': self.tax_groups[0].name,
                                    },
                                ],
                            },
                        ],
                    },
                ),
                self._prepare_tax_totals_summary_test(
                    self._prepare_document_params(
                        rounding_method='round_globally',
                        currency=self.foreign_currency,
                    ),
                    [
                        self._prepare_document_line_params(48.0, taxes=taxes, rate=0.3333),
                        self._prepare_document_line_params(48.0, taxes=taxes, rate=0.3333),
                    ],
                    {
                        'same_tax_base': True,
                        'currency_id': self.foreign_currency.id,
                        'company_currency_id': self.currency.id,
                        'base_amount_currency': 64.66,
                        'base_amount': 21.55,
                        'tax_amount_currency': 31.339999999999996,
                        'tax_amount': 10.45,
                        'total_amount_currency': 96.0,
                        'total_amount': 32.0,
                        'subtotals': [
                            {
                                'name': "Untaxed Amount",
                                'base_amount_currency': 64.66,
                                'base_amount': 21.55,
                                'tax_amount_currency': 31.339999999999996,
                                'tax_amount': 10.45,
                                'tax_groups': [
                                    {
                                        'id': self.tax_groups[0].id,
                                        'base_amount_currency': 64.66,
                                        'base_amount': 21.55,
                                        'tax_amount_currency': 31.339999999999996,
                                        'tax_amount': 10.45,
                                        'display_base_amount_currency': 96.0,
                                        'display_base_amount': 32.0,
                                        'group_name': self.tax_groups[0].name,
                                    },
                                ],
                            },
                        ],
                    },
                ),
            ])

        with self.different_tax_group(taxes):
            for rounding_method in ('round_per_line', 'round_globally'):
                tests.append(
                    self._prepare_total_per_tax_summary_test(
                        self._prepare_document_params(rounding_method=rounding_method),
                        [
                            self._prepare_document_line_params(48.0, taxes=taxes),
                            self._prepare_document_line_params(48.0, taxes=taxes),
                        ],
                        {
                            'base_amount_currency': 64.66,
                            'tax_amount_currency': 31.339999999999996,
                            'total_amount_currency': 96.0,
                            'subtotals': {
                                tax1.id: {
                                    'base_amount_currency': 64.66,
                                    'tax_amount_currency': 4.8,
                                    'display_base_amount_currency': 96.0,
                                },
                                tax2.id: {
                                    'base_amount_currency': 64.66,
                                    'tax_amount_currency': 2.88,
                                    'display_base_amount_currency': 96.0,
                                },
                                tax3.id: {
                                    'base_amount_currency': 64.66,
                                    'tax_amount_currency': 0.62,
                                    'display_base_amount_currency': 96.0,
                                },
                                tax4.id: {
                                    'base_amount_currency': 64.66,
                                    'tax_amount_currency': 8.64,
                                    'display_base_amount_currency': 96.0,
                                },
                                tax5.id: {
                                    'base_amount_currency': 64.66,
                                    'tax_amount_currency': 14.4,
                                    'display_base_amount_currency': 96.0,
                                },
                            },
                        },
                    ),
                )
            tests.extend([
                self._prepare_tax_totals_summary_test(
                    self._prepare_document_params(
                        rounding_method='round_per_line',
                        currency=self.foreign_currency,
                    ),
                    [
                        self._prepare_document_line_params(48.0, taxes=taxes, rate=0.3333),
                        self._prepare_document_line_params(48.0, taxes=taxes, rate=0.3333),
                    ],
                    {
                        'same_tax_base': True,
                        'currency_id': self.foreign_currency.id,
                        'company_currency_id': self.currency.id,
                        'base_amount_currency': 64.66,
                        'base_amount': 21.55,
                        'tax_amount_currency': 31.339999999999996,
                        'tax_amount': 10.45,
                        'total_amount_currency': 96.0,
                        'total_amount': 32.0,
                        'subtotals': [
                            {
                                'name': "Untaxed Amount",
                                'base_amount_currency': 64.66,
                                'base_amount': 21.55,
                                'tax_amount_currency': 31.339999999999996,
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
                                        'group_name': self.tax_groups[0].name,
                                    },
                                    {
                                        'id': self.tax_groups[1].id,
                                        'base_amount_currency': 64.66,
                                        'base_amount': 21.55,
                                        'tax_amount_currency': 2.88,
                                        'tax_amount': 0.96,
                                        'display_base_amount_currency': 96.0,
                                        'display_base_amount': 32.0,
                                        'group_name': self.tax_groups[1].name,
                                    },
                                    {
                                        'id': self.tax_groups[2].id,
                                        'base_amount_currency': 64.66,
                                        'base_amount': 21.55,
                                        'tax_amount_currency': 0.62,
                                        'tax_amount': 0.21,
                                        'display_base_amount_currency': 96.0,
                                        'display_base_amount': 32.0,
                                        'group_name': self.tax_groups[2].name,
                                    },
                                    {
                                        'id': self.tax_groups[3].id,
                                        'base_amount_currency': 64.66,
                                        'base_amount': 21.55,
                                        'tax_amount_currency': 8.64,
                                        'tax_amount': 2.88,
                                        'display_base_amount_currency': 96.0,
                                        'display_base_amount': 32.0,
                                        'group_name': self.tax_groups[3].name,
                                    },
                                    {
                                        'id': self.tax_groups[4].id,
                                        'base_amount_currency': 64.66,
                                        'base_amount': 21.55,
                                        'tax_amount_currency': 14.4,
                                        'tax_amount': 4.8,
                                        'display_base_amount_currency': 96.0,
                                        'display_base_amount': 32.0,
                                        'group_name': self.tax_groups[4].name,
                                    },
                                ],
                            },
                        ],
                    },
                ),
                self._prepare_tax_totals_summary_test(
                    self._prepare_document_params(
                        rounding_method='round_globally',
                        currency=self.foreign_currency,
                    ),
                    [
                        self._prepare_document_line_params(48.0, taxes=taxes, rate=0.3333),
                        self._prepare_document_line_params(48.0, taxes=taxes, rate=0.3333),
                    ],
                    {
                        'same_tax_base': True,
                        'currency_id': self.foreign_currency.id,
                        'company_currency_id': self.currency.id,
                        'base_amount_currency': 64.66,
                        'base_amount': 21.55,
                        'tax_amount_currency': 31.339999999999996,
                        'tax_amount': 10.45,
                        'total_amount_currency': 96.0,
                        'total_amount': 32.0,
                        'subtotals': [
                            {
                                'name': "Untaxed Amount",
                                'base_amount_currency': 64.66,
                                'base_amount': 21.55,
                                'tax_amount_currency': 31.339999999999996,
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
                                        'group_name': self.tax_groups[0].name,
                                    },
                                    {
                                        'id': self.tax_groups[1].id,
                                        'base_amount_currency': 64.66,
                                        'base_amount': 21.55,
                                        'tax_amount_currency': 2.88,
                                        'tax_amount': 0.96,
                                        'display_base_amount_currency': 96.0,
                                        'display_base_amount': 32.0,
                                        'group_name': self.tax_groups[1].name,
                                    },
                                    {
                                        'id': self.tax_groups[2].id,
                                        'base_amount_currency': 64.66,
                                        'base_amount': 21.55,
                                        'tax_amount_currency': 0.62,
                                        'tax_amount': 0.21,
                                        'display_base_amount_currency': 96.0,
                                        'display_base_amount': 32.0,
                                        'group_name': self.tax_groups[2].name,
                                    },
                                    {
                                        'id': self.tax_groups[3].id,
                                        'base_amount_currency': 64.66,
                                        'base_amount': 21.55,
                                        'tax_amount_currency': 8.64,
                                        'tax_amount': 2.88,
                                        'display_base_amount_currency': 96.0,
                                        'display_base_amount': 32.0,
                                        'group_name': self.tax_groups[3].name,
                                    },
                                    {
                                        'id': self.tax_groups[4].id,
                                        'base_amount_currency': 64.66,
                                        'base_amount': 21.55,
                                        'tax_amount_currency': 14.4,
                                        'tax_amount': 4.8,
                                        'display_base_amount_currency': 96.0,
                                        'display_base_amount': 32.0,
                                        'group_name': self.tax_groups[4].name,
                                    },
                                ],
                            },
                        ],
                    },
                ),
            ])
        self._assert_tests(tests)

    def test_taxes_l10n_be(self):
        tests = []
        tax1 = self.fixed_tax(1, include_base_amount=True)
        tax2 = self.percent_tax(21)
        taxes = tax1 + tax2

        with self.same_tax_group(taxes):
            tests.extend([
                self._prepare_tax_totals_summary_test(
                    self._prepare_document_params(
                        rounding_method='round_per_line',
                        currency=self.foreign_currency,
                    ),
                    [
                        self._prepare_document_line_params(16.79, taxes=taxes, rate=2.0),
                        self._prepare_document_line_params(16.79, taxes=taxes, rate=2.0),
                    ],
                    {
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
                                        'group_name': self.tax_groups[0].name,
                                    },
                                ],
                            },
                        ],
                    },
                ),
                self._prepare_tax_totals_summary_test(
                    self._prepare_document_params(
                        rounding_method='round_globally',
                        currency=self.foreign_currency,
                    ),
                    [
                        self._prepare_document_line_params(16.79, taxes=taxes, rate=2.0),
                        self._prepare_document_line_params(16.79, taxes=taxes, rate=2.0),
                    ],
                    {
                        'same_tax_base': True,
                        'currency_id': self.foreign_currency.id,
                        'company_currency_id': self.currency.id,
                        'base_amount_currency': 33.58,
                        'base_amount': 67.16,
                        'tax_amount_currency': 9.469999999999999,
                        'tax_amount': 18.939999999999998,
                        'total_amount_currency': 43.05,
                        'total_amount': 86.1,
                        'subtotals': [
                            {
                                'name': "Untaxed Amount",
                                'base_amount_currency': 33.58,
                                'base_amount': 67.16,
                                'tax_amount_currency': 9.469999999999999,
                                'tax_amount': 18.939999999999998,
                                'tax_groups': [
                                    {
                                        'id': self.tax_groups[0].id,
                                        'base_amount_currency': 33.58,
                                        'base_amount': 67.16,
                                        'tax_amount_currency': 9.469999999999999,
                                        'tax_amount': 18.939999999999998,
                                        'display_base_amount_currency': 33.58,
                                        'display_base_amount': 67.16,
                                        'group_name': self.tax_groups[0].name,
                                    },
                                ],
                            },
                        ],
                    },
                ),
            ])

        with self.different_tax_group(taxes):
            tests.extend([
                self._prepare_total_per_tax_summary_test(
                    self._prepare_document_params(rounding_method='round_per_line'),
                    [
                        self._prepare_document_line_params(16.79, taxes=taxes),
                        self._prepare_document_line_params(16.79, taxes=taxes),
                    ],
                    {
                        'base_amount_currency': 33.58,
                        'tax_amount_currency': 9.48,
                        'total_amount_currency': 43.06,
                        'subtotals': {
                            tax1.id: {
                                'base_amount_currency': 33.58,
                                'tax_amount_currency': 2.0,
                                'display_base_amount_currency': None,
                            },
                            tax2.id: {
                                'base_amount_currency': 35.58,
                                'tax_amount_currency': 7.48,
                                'display_base_amount_currency': 35.58,
                            },
                        },
                    },
                ),
                self._prepare_tax_totals_summary_test(
                    self._prepare_document_params(
                        rounding_method='round_per_line',
                        currency=self.foreign_currency,
                    ),
                    [
                        self._prepare_document_line_params(16.79, taxes=taxes, rate=2.0),
                        self._prepare_document_line_params(16.79, taxes=taxes, rate=2.0),
                    ],
                    {
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
                                        'tax_amount_currency': 2.0,
                                        'tax_amount': 4.0,
                                        'display_base_amount_currency': None,
                                        'display_base_amount': None,
                                        'group_name': self.tax_groups[0].name,
                                    },
                                    {
                                        'id': self.tax_groups[1].id,
                                        'base_amount_currency': 35.58,
                                        'base_amount': 71.16,
                                        'tax_amount_currency': 7.48,
                                        'tax_amount': 14.96,
                                        'display_base_amount_currency': 35.58,
                                        'display_base_amount': 71.16,
                                        'group_name': self.tax_groups[1].name,
                                    },
                                ],
                            },
                        ],
                    },
                ),
                self._prepare_total_per_tax_summary_test(
                    self._prepare_document_params(rounding_method='round_globally'),
                    [
                        self._prepare_document_line_params(16.79, taxes=taxes),
                        self._prepare_document_line_params(16.79, taxes=taxes),
                    ],
                    {
                        'base_amount_currency': 33.58,
                        'tax_amount_currency': 9.469999999999999,
                        'total_amount_currency': 43.05,
                        'subtotals': {
                            tax1.id: {
                                'base_amount_currency': 33.58,
                                'tax_amount_currency': 2.0,
                                'display_base_amount_currency': None,
                            },
                            tax2.id: {
                                'base_amount_currency': 35.58,
                                'tax_amount_currency': 7.47,
                                'display_base_amount_currency': 35.58,
                            },
                        },
                    },
                ),
                self._prepare_tax_totals_summary_test(
                    self._prepare_document_params(
                        rounding_method='round_globally',
                        currency=self.foreign_currency,
                    ),
                    [
                        self._prepare_document_line_params(16.79, taxes=taxes, rate=2.0),
                        self._prepare_document_line_params(16.79, taxes=taxes, rate=2.0),
                    ],
                    {
                        'same_tax_base': True,
                        'currency_id': self.foreign_currency.id,
                        'company_currency_id': self.currency.id,
                        'base_amount_currency': 33.58,
                        'base_amount': 67.16,
                        'tax_amount_currency': 9.469999999999999,
                        'tax_amount': 18.939999999999998,
                        'total_amount_currency': 43.05,
                        'total_amount': 86.1,
                        'subtotals': [
                            {
                                'name': "Untaxed Amount",
                                'base_amount_currency': 33.58,
                                'base_amount': 67.16,
                                'tax_amount_currency': 9.469999999999999,
                                'tax_amount': 18.939999999999998,
                                'tax_groups': [
                                    {
                                        'id': self.tax_groups[0].id,
                                        'base_amount_currency': 33.58,
                                        'base_amount': 67.16,
                                        'tax_amount_currency': 2.0,
                                        'tax_amount': 4.0,
                                        'display_base_amount_currency': None,
                                        'display_base_amount': None,
                                        'group_name': self.tax_groups[0].name,
                                    },
                                    {
                                        'id': self.tax_groups[1].id,
                                        'base_amount_currency': 35.58,
                                        'base_amount': 71.16,
                                        'tax_amount_currency': 7.47,
                                        'tax_amount': 14.94,
                                        'display_base_amount_currency': 35.58,
                                        'display_base_amount': 71.16,
                                        'group_name': self.tax_groups[1].name,
                                    },
                                ],
                            },
                        ],
                    },
                ),
            ])

        taxes.price_include = True
        with self.same_tax_group(taxes):
            tests.extend([
                self._prepare_tax_totals_summary_test(
                    self._prepare_document_params(
                        rounding_method='round_per_line',
                        currency=self.foreign_currency,
                    ),
                    [
                        self._prepare_document_line_params(21.53, taxes=taxes, rate=2.0),
                        self._prepare_document_line_params(21.53, taxes=taxes, rate=2.0),
                    ],
                    {
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
                                        'group_name': self.tax_groups[0].name,
                                    },
                                ],
                            },
                        ],
                    },
                ),
                self._prepare_tax_totals_summary_test(
                    self._prepare_document_params(
                        rounding_method='round_globally',
                        currency=self.foreign_currency,
                    ),
                    [
                        self._prepare_document_line_params(21.53, taxes=taxes, rate=2.0),
                        self._prepare_document_line_params(21.53, taxes=taxes, rate=2.0),
                    ],
                    {
                        'same_tax_base': True,
                        'currency_id': self.foreign_currency.id,
                        'company_currency_id': self.currency.id,
                        'base_amount_currency': 33.59,
                        'base_amount': 67.17,
                        'tax_amount_currency': 9.469999999999999,
                        'tax_amount': 18.950000000000003,
                        'total_amount_currency': 43.06,
                        'total_amount': 86.12,
                        'subtotals': [
                            {
                                'name': "Untaxed Amount",
                                'base_amount_currency': 33.59,
                                'base_amount': 67.17,
                                'tax_amount_currency': 9.469999999999999,
                                'tax_amount': 18.950000000000003,
                                'tax_groups': [
                                    {
                                        'id': self.tax_groups[0].id,
                                        'base_amount_currency': 33.59,
                                        'base_amount': 67.17,
                                        'tax_amount_currency': 9.469999999999999,
                                        'tax_amount': 18.950000000000003,
                                        'display_base_amount_currency': 33.59,
                                        'display_base_amount': 67.17,
                                        'group_name': self.tax_groups[0].name,
                                    },
                                ],
                            },
                        ],
                    },
                ),
            ])

        with self.different_tax_group(taxes):
            tests.extend([
                self._prepare_total_per_tax_summary_test(
                    self._prepare_document_params(rounding_method='round_per_line'),
                    [
                        self._prepare_document_line_params(21.53, taxes=taxes),
                        self._prepare_document_line_params(21.53, taxes=taxes),
                    ],
                    {
                        'base_amount_currency': 33.58,
                        'tax_amount_currency': 9.48,
                        'total_amount_currency': 43.06,
                        'subtotals': {
                            tax1.id: {
                                'base_amount_currency': 33.58,
                                'tax_amount_currency': 2.0,
                                'display_base_amount_currency': None,
                            },
                            tax2.id: {
                                'base_amount_currency': 35.58,
                                'tax_amount_currency': 7.48,
                                'display_base_amount_currency': 35.58,
                            },
                        },
                    },
                ),
                self._prepare_tax_totals_summary_test(
                    self._prepare_document_params(
                        rounding_method='round_per_line',
                        currency=self.foreign_currency,
                    ),
                    [
                        self._prepare_document_line_params(21.53, taxes=taxes, rate=2.0),
                        self._prepare_document_line_params(21.53, taxes=taxes, rate=2.0),
                    ],
                    {
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
                                        'tax_amount_currency': 2.0,
                                        'tax_amount': 4.0,
                                        'display_base_amount_currency': None,
                                        'display_base_amount': None,
                                        'group_name': self.tax_groups[0].name,
                                    },
                                    {
                                        'id': self.tax_groups[1].id,
                                        'base_amount_currency': 35.58,
                                        'base_amount': 71.16,
                                        'tax_amount_currency': 7.48,
                                        'tax_amount': 14.96,
                                        'display_base_amount_currency': 35.58,
                                        'display_base_amount': 71.16,
                                        'group_name': self.tax_groups[1].name,
                                    },
                                ],
                            },
                        ],
                    },
                ),
                self._prepare_total_per_tax_summary_test(
                    self._prepare_document_params(rounding_method='round_globally'),
                    [
                        self._prepare_document_line_params(21.53, taxes=taxes),
                        self._prepare_document_line_params(21.53, taxes=taxes),
                    ],
                    {
                        'base_amount_currency': 33.59,
                        'tax_amount_currency': 9.469999999999999,
                        'total_amount_currency': 43.06,
                        'subtotals': {
                            tax1.id: {
                                'base_amount_currency': 33.59,
                                'tax_amount_currency': 2.0,
                                'display_base_amount_currency': None,
                            },
                            tax2.id: {
                                'base_amount_currency': 35.59,
                                'tax_amount_currency': 7.47,
                                'display_base_amount_currency': 35.59,
                            },
                        },
                    },
                ),
                self._prepare_tax_totals_summary_test(
                    self._prepare_document_params(
                        rounding_method='round_globally',
                        currency=self.foreign_currency,
                    ),
                    [
                        self._prepare_document_line_params(21.53, taxes=taxes, rate=2.0),
                        self._prepare_document_line_params(21.53, taxes=taxes, rate=2.0),
                    ],
                    {
                        'same_tax_base': True,
                        'currency_id': self.foreign_currency.id,
                        'company_currency_id': self.currency.id,
                        'base_amount_currency': 33.59,
                        'base_amount': 67.17,
                        'tax_amount_currency': 9.469999999999999,
                        'tax_amount': 18.950000000000003,
                        'total_amount_currency': 43.06,
                        'total_amount': 86.12,
                        'subtotals': [
                            {
                                'name': "Untaxed Amount",
                                'base_amount_currency': 33.59,
                                'base_amount': 67.17,
                                'tax_amount_currency': 9.469999999999999,
                                'tax_amount': 18.950000000000003,
                                'tax_groups': [
                                    {
                                        'id': self.tax_groups[0].id,
                                        'base_amount_currency': 33.59,
                                        'base_amount': 67.17,
                                        'tax_amount_currency': 2.0,
                                        'tax_amount': 4.0,
                                        'display_base_amount_currency': None,
                                        'display_base_amount': None,
                                        'group_name': self.tax_groups[0].name,
                                    },
                                    {
                                        'id': self.tax_groups[1].id,
                                        'base_amount_currency': 35.59,
                                        'base_amount': 71.17,
                                        'tax_amount_currency': 7.47,
                                        'tax_amount': 14.950000000000001,
                                        'display_base_amount_currency': 35.59,
                                        'display_base_amount': 71.17,
                                        'group_name': self.tax_groups[1].name,
                                    },
                                ],
                            },
                        ],
                    },
                ),
            ])
        self._assert_tests(tests)

    def test_cash_rounding(self):
        tax1 = self.division_tax(5, tax_group_id=self.tax_groups[0].id)
        tax2 = self.division_tax(3, tax_group_id=self.tax_groups[1].id)
        tax3 = self.division_tax(0.65, tax_group_id=self.tax_groups[2].id)
        tax4 = self.division_tax(9, tax_group_id=self.tax_groups[3].id)
        tax5 = self.division_tax(15, tax_group_id=self.tax_groups[4].id)
        taxes = tax1 + tax2 + tax3 + tax4 + tax5

        tests = [
            self._prepare_tax_totals_summary_test(
                self._prepare_document_params(rounding_method='round_per_line'),
                [
                    self._prepare_document_cash_rounding('add_invoice_line'),
                    self._prepare_document_line_params(32.4, taxes=taxes),
                ],
                {
                    'same_tax_base': True,
                    'currency_id': self.currency.id,
                    'base_amount_currency': 32.39,
                    'cash_rounding_base_amount_currency': -0.01,
                    'tax_amount_currency': 15.71,
                    'total_amount_currency': 48.1,
                    'subtotals': [
                        {
                            'name': "Untaxed Amount",
                            'base_amount_currency': 32.39,
                            'tax_amount_currency': 15.71,
                            'tax_groups': [
                                {
                                    'id': self.tax_groups[0].id,
                                    'base_amount_currency': 32.4,
                                    'tax_amount_currency': 2.41,
                                    'display_base_amount_currency': 32.4,
                                    'group_name': self.tax_groups[0].name,
                                },
                                {
                                    'id': self.tax_groups[1].id,
                                    'base_amount_currency': 32.4,
                                    'tax_amount_currency': 1.44,
                                    'display_base_amount_currency': 32.4,
                                    'group_name': self.tax_groups[1].name,
                                },
                                {
                                    'id': self.tax_groups[2].id,
                                    'base_amount_currency': 32.4,
                                    'tax_amount_currency': 0.31,
                                    'display_base_amount_currency': 32.4,
                                    'group_name': self.tax_groups[2].name,
                                },
                                {
                                    'id': self.tax_groups[3].id,
                                    'base_amount_currency': 32.4,
                                    'tax_amount_currency': 4.33,
                                    'display_base_amount_currency': 32.4,
                                    'group_name': self.tax_groups[3].name,
                                },
                                {
                                    'id': self.tax_groups[4].id,
                                    'base_amount_currency': 32.4,
                                    'tax_amount_currency': 7.22,
                                    'display_base_amount_currency': 32.4,
                                    'group_name': self.tax_groups[4].name,
                                },
                            ],
                        },
                    ],
                },
            ),
            self._prepare_tax_totals_summary_test(
                self._prepare_document_params(rounding_method='round_per_line'),
                [
                    self._prepare_document_cash_rounding('biggest_tax'),
                    self._prepare_document_line_params(32.4, taxes=taxes),
                ],
                {
                    'same_tax_base': True,
                    'currency_id': self.currency.id,
                    'base_amount_currency': 32.40,
                    'tax_amount_currency': 15.7,
                    'total_amount_currency': 48.099999999999994,
                    'subtotals': [
                        {
                            'name': "Untaxed Amount",
                            'base_amount_currency': 32.4,
                            'tax_amount_currency': 15.7,
                            'tax_groups': [
                                {
                                    'id': self.tax_groups[0].id,
                                    'base_amount_currency': 32.4,
                                    'tax_amount_currency': 2.41,
                                    'display_base_amount_currency': 32.4,
                                    'group_name': self.tax_groups[0].name,
                                },
                                {
                                    'id': self.tax_groups[1].id,
                                    'base_amount_currency': 32.4,
                                    'tax_amount_currency': 1.44,
                                    'display_base_amount_currency': 32.4,
                                    'group_name': self.tax_groups[1].name,
                                },
                                {
                                    'id': self.tax_groups[2].id,
                                    'base_amount_currency': 32.4,
                                    'tax_amount_currency': 0.31,
                                    'display_base_amount_currency': 32.4,
                                    'group_name': self.tax_groups[2].name,
                                },
                                {
                                    'id': self.tax_groups[3].id,
                                    'base_amount_currency': 32.4,
                                    'tax_amount_currency': 4.33,
                                    'display_base_amount_currency': 32.4,
                                    'group_name': self.tax_groups[3].name,
                                },
                                {
                                    'id': self.tax_groups[4].id,
                                    'base_amount_currency': 32.4,
                                    'tax_amount_currency': 7.21,
                                    'cash_rounding_tax_amount_currency': -0.01,
                                    'display_base_amount_currency': 32.4,
                                    'group_name': self.tax_groups[4].name,
                                },
                            ],
                        },
                    ],
                },
            ),
            # Same but exclude some tax groups.
            self._prepare_tax_totals_summary_test(
                self._prepare_document_params(rounding_method='round_per_line'),
                [
                    self._prepare_document_cash_rounding('biggest_tax'),
                    self._prepare_document_line_params(32.4, taxes=taxes),
                ],
                {
                    'same_tax_base': True,
                    'currency_id': self.currency.id,
                    'base_amount_currency': 44.25,
                    'tax_amount_currency': 3.8499999999999988,
                    'total_amount_currency': 48.099999999999994,
                    'subtotals': [
                        {
                            'name': "Untaxed Amount",
                            'base_amount_currency': 44.25,
                            'tax_amount_currency': 3.8499999999999988,
                            'tax_groups': [
                                {
                                    'id': self.tax_groups[0].id,
                                    'base_amount_currency': 32.4,
                                    'tax_amount_currency': 2.41,
                                    'display_base_amount_currency': 32.4,
                                    'group_name': self.tax_groups[0].name,
                                },
                                {
                                    'id': self.tax_groups[1].id,
                                    'base_amount_currency': 32.4,
                                    'tax_amount_currency': 1.44,
                                    'display_base_amount_currency': 32.4,
                                    'group_name': self.tax_groups[1].name,
                                },
                            ],
                        },
                    ],
                },
                exclude_tax_group_ids=self.tax_groups[2:5].ids,
            ),
        ]
        self._assert_tests(tests)

    def test_exclude_tax_group(self):
        tax1 = self.division_tax(5, tax_group_id=self.tax_groups[0].id)
        tax2 = self.division_tax(3, tax_group_id=self.tax_groups[1].id)
        tax3 = self.division_tax(0.65, tax_group_id=self.tax_groups[2].id)
        tax4 = self.division_tax(9, tax_group_id=self.tax_groups[3].id)
        tax5 = self.division_tax(15, tax_group_id=self.tax_groups[4].id)
        taxes = tax1 + tax2 + tax3 + tax4 + tax5

        tests = [
            self._prepare_tax_totals_summary_test(
                self._prepare_document_params(rounding_method='round_per_line'),
                [
                    self._prepare_document_cash_rounding('biggest_tax'),
                    self._prepare_document_line_params(32.4, taxes=taxes),
                ],
                {
                    'same_tax_base': True,
                    'currency_id': self.currency.id,
                    'base_amount_currency': 44.25,
                    'tax_amount_currency': 3.8499999999999988,
                    'total_amount_currency': 48.099999999999994,
                    'subtotals': [
                        {
                            'name': "Untaxed Amount",
                            'base_amount_currency': 44.25,
                            'tax_amount_currency': 3.8499999999999988,
                            'tax_groups': [
                                {
                                    'id': self.tax_groups[0].id,
                                    'base_amount_currency': 32.4,
                                    'tax_amount_currency': 2.41,
                                    'display_base_amount_currency': 32.4,
                                    'group_name': self.tax_groups[0].name,
                                },
                                {
                                    'id': self.tax_groups[1].id,
                                    'base_amount_currency': 32.4,
                                    'tax_amount_currency': 1.44,
                                    'display_base_amount_currency': 32.4,
                                    'group_name': self.tax_groups[1].name,
                                },
                            ],
                        },
                    ],
                },
                exclude_tax_group_ids=self.tax_groups[2:5].ids,
            ),
        ]
        self._assert_tests(tests)

    def test_mixed_combined_standalone_taxes(self):
        """ Test when the same taxes are used both as standalone tax and combined all together. """
        tests = []
        tax_10 = self.percent_tax(10.0)
        tax_10_incl_base = self.percent_tax(10.0, include_base_amount=True)
        tax_20 = self.percent_tax(20.0)
        taxes = tax_10 + tax_20 + tax_10_incl_base

        with self.same_tax_group(taxes):
            tests.extend([
                self._prepare_tax_totals_summary_test(
                    self._prepare_document_params(),
                    [
                        self._prepare_document_line_params(1000.0, taxes=tax_10 + tax_20),
                        self._prepare_document_line_params(1000.0, taxes=tax_10),
                        self._prepare_document_line_params(1000.0, taxes=tax_20),
                    ],
                    {
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
                                        'group_name': self.tax_groups[0].name,
                                    },
                                ],
                            },
                        ],
                    },
                ),
                self._prepare_tax_totals_summary_test(
                    self._prepare_document_params(),
                    [
                        self._prepare_document_line_params(1000.0, taxes=tax_10_incl_base + tax_20),
                        self._prepare_document_line_params(1000.0, taxes=tax_10_incl_base),
                        self._prepare_document_line_params(1000.0, taxes=tax_20),
                    ],
                    {
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
                                        'group_name': self.tax_groups[0].name,
                                    },
                                ],
                            },
                        ],
                    },
                ),
            ])

        with self.different_tax_group(taxes):
            tests.extend([
                self._prepare_tax_totals_summary_test(
                    self._prepare_document_params(),
                    [
                        self._prepare_document_line_params(1000.0, taxes=tax_10 + tax_20),
                        self._prepare_document_line_params(1000.0, taxes=tax_10),
                        self._prepare_document_line_params(1000.0, taxes=tax_20),
                    ],
                    {
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
                                        'base_amount_currency': 2000.0,
                                        'tax_amount_currency': 200.0,
                                        'display_base_amount_currency': 2000.0,
                                        'group_name': self.tax_groups[0].name,
                                    },
                                    {
                                        'id': self.tax_groups[1].id,
                                        'base_amount_currency': 2000.0,
                                        'tax_amount_currency': 400.0,
                                        'display_base_amount_currency': 2000.0,
                                        'group_name': self.tax_groups[1].name,
                                    },
                                ],
                            },
                        ],
                    },
                ),
                self._prepare_tax_totals_summary_test(
                    self._prepare_document_params(),
                    [
                        self._prepare_document_line_params(1000.0, taxes=tax_10_incl_base + tax_20),
                        self._prepare_document_line_params(1000.0, taxes=tax_10_incl_base),
                        self._prepare_document_line_params(1000.0, taxes=tax_20),
                    ],
                    {
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
                                        'group_name': self.tax_groups[1].name,
                                    },
                                    {
                                        'id': self.tax_groups[2].id,
                                        'base_amount_currency': 2000.0,
                                        'tax_amount_currency': 200.0,
                                        'display_base_amount_currency': 2000.0,
                                        'group_name': self.tax_groups[2].name,
                                    },
                                ],
                            },
                        ],
                    },
                ),
            ])

        self._assert_tests(tests)

    def test_preceding_subtotal(self):
        self.tax_groups[1].preceding_subtotal = "PRE GROUP 1"
        self.tax_groups[2].preceding_subtotal = "PRE GROUP 2"
        tax_10 = self.percent_tax(10.0, tax_group_id=self.tax_groups[1].id)
        tax_25 = self.percent_tax(25.0, tax_group_id=self.tax_groups[2].id)
        tax_42 = self.percent_tax(42.0, tax_group_id=self.tax_groups[0].id)

        tests = [
            self._prepare_tax_totals_summary_test(
                self._prepare_document_params(),
                [
                    self._prepare_document_line_params(1000.0),
                    self._prepare_document_line_params(1000.0, taxes=tax_10),
                    self._prepare_document_line_params(1000.0, taxes=tax_25),
                    self._prepare_document_line_params(100.0, taxes=tax_42),
                    self._prepare_document_line_params(200.0, taxes=tax_42 + tax_10 + tax_25),
                ],
                {
                    'same_tax_base': False,
                    'currency_id': self.currency.id,
                    'base_amount_currency': 3300.0,
                    'tax_amount_currency': 546.0,
                    'total_amount_currency': 3846.0,
                    'subtotals': [
                        {
                            'name': "Untaxed Amount",
                            'base_amount_currency': 3300.0,
                            'tax_amount_currency': 126.0,
                            'tax_groups': [
                                {
                                    'id': self.tax_groups[0].id,
                                    'base_amount_currency': 300.0,
                                    'tax_amount_currency': 126.0,
                                    'display_base_amount_currency': 300.0,
                                    'group_name': self.tax_groups[0].name,
                                },
                            ],
                        },
                        {
                            'name': "PRE GROUP 1",
                            'base_amount_currency': 3426.0,
                            'tax_amount_currency': 120.0,
                            'tax_groups': [
                                {
                                    'id': self.tax_groups[1].id,
                                    'base_amount_currency': 1200.0,
                                    'tax_amount_currency': 120.0,
                                    'display_base_amount_currency': 1200.0,
                                    'group_name': self.tax_groups[1].name,
                                },
                            ],
                        },
                        {
                            'name': "PRE GROUP 2",
                            'base_amount_currency': 3546.0,
                            'tax_amount_currency': 300.0,
                            'tax_groups': [
                                {
                                    'id': self.tax_groups[2].id,
                                    'base_amount_currency': 1200.0,
                                    'tax_amount_currency': 300.0,
                                    'display_base_amount_currency': 1200.0,
                                    'group_name': self.tax_groups[2].name,
                                },
                            ],
                        },
                    ],
                },
            ),
        ]

        self.tax_groups[3].preceding_subtotal = "PRE GROUP 1"  # same as tax_groups[1], on purpose
        tax_10.tax_group_id = self.tax_groups[3]  # preceding_subtotal == "PRE GROUP 1"
        tax_42.tax_group_id = self.tax_groups[1]  # preceding_subtotal == "PRE GROUP 1"
        tax_minus_25 = self.percent_tax(-25.0, tax_group_id=self.tax_groups[2].id)  # preceding_subtotal == "PRE GROUP 2"
        tax_30 = self.percent_tax(30.0, tax_group_id=self.tax_groups[0].id)

        tests.append(
            self._prepare_tax_totals_summary_test(
                self._prepare_document_params(),
                [
                    self._prepare_document_line_params(100.0, taxes=tax_10),
                    self._prepare_document_line_params(100.0, taxes=tax_minus_25 + tax_42 + tax_30),
                    self._prepare_document_line_params(200.0, taxes=tax_10 + tax_minus_25),
                    self._prepare_document_line_params(1000.0, taxes=tax_30),
                    self._prepare_document_line_params(100.0, taxes=tax_30 + tax_10),
                ],
                {
                    'same_tax_base': False,
                    'currency_id': self.currency.id,
                    'base_amount_currency': 1500.0,
                    'tax_amount_currency': 367.0,
                    'total_amount_currency': 1867.0,
                    'subtotals': [
                        {
                            'name': "Untaxed Amount",
                            'base_amount_currency': 1500.0,
                            'tax_amount_currency': 360.0,
                            'tax_groups': [
                                {
                                    'id': self.tax_groups[0].id,
                                    'base_amount_currency': 1200.0,
                                    'tax_amount_currency': 360.0,
                                    'display_base_amount_currency': 1200.0,
                                    'group_name': self.tax_groups[0].name,
                                },
                            ],
                        },
                        {
                            'name': "PRE GROUP 1",
                            'base_amount_currency': 1860.0,
                            'tax_amount_currency': 82.0,
                            'tax_groups': [
                                {
                                    'id': self.tax_groups[1].id,
                                    'base_amount_currency': 100.0,
                                    'tax_amount_currency': 42.0,
                                    'display_base_amount_currency': 100.0,
                                    'group_name': self.tax_groups[1].name,
                                },
                                {
                                    'id': self.tax_groups[3].id,
                                    'base_amount_currency': 400.0,
                                    'tax_amount_currency': 40.0,
                                    'display_base_amount_currency': 400.0,
                                    'group_name': self.tax_groups[3].name,
                                },
                            ],
                        },
                        {
                            'name': "PRE GROUP 2",
                            'base_amount_currency': 1942.0,
                            'tax_amount_currency': -75.0,
                            'tax_groups': [
                                {
                                    'id': self.tax_groups[2].id,
                                    'base_amount_currency': 300.0,
                                    'tax_amount_currency': -75.0,
                                    'display_base_amount_currency': 300.0,
                                    'group_name': self.tax_groups[2].name,
                                },
                            ],
                        },
                    ],
                },
            )
        )

        self._assert_tests(tests)

    def test_preceding_subtotal_with_tax_group(self):
        self.tax_groups[1].preceding_subtotal = "Tax withholding"
        tax_minus_47 = self.percent_tax(-47.0, tax_group_id=self.tax_groups[1].id)
        tax_10 = self.percent_tax(10.0, tax_group_id=self.tax_groups[0].id)
        tax_group = self.group_of_taxes(tax_minus_47 + tax_10)

        tests = [
            self._prepare_tax_totals_summary_test(
                self._prepare_document_params(),
                [
                    self._prepare_document_line_params(100.0, taxes=tax_group),
                ],
                {
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
                                    'group_name': self.tax_groups[0].name,
                                },
                            ],
                        },
                        {
                            'name': "Tax withholding",
                            'base_amount_currency': 110.0,
                            'tax_amount_currency': -47.0,
                            'tax_groups': [
                                {
                                    'id': self.tax_groups[1].id,
                                    'base_amount_currency': 100.0,
                                    'tax_amount_currency': -47.0,
                                    'display_base_amount_currency': 100.0,
                                    'group_name': self.tax_groups[1].name,
                                },
                            ],
                        },
                    ],
                },
            ),
        ]

        self._assert_tests(tests)

    def test_random_tax_amount_currency(self):
        tax_16 = self.percent_tax(16.0)
        tax_53 = self.percent_tax(53.0)
        tax_10 = self.percent_tax(10.0)
        tax_23_1 = self.percent_tax(23.0)
        tax_23_2 = self.percent_tax(23.0)
        tax_17a = self.percent_tax(17.0)
        tax_17b = self.percent_tax(17.0)

        tests = [
            self._prepare_tax_amount_test(
                self._prepare_document_params(rounding_method='round_per_line'),
                [self._prepare_document_line_params(100.41, taxes=tax_16 + tax_53)],
                69.29,
            ),
            self._prepare_tax_amount_test(
                self._prepare_document_params(rounding_method='round_globally'),
                [self._prepare_document_line_params(100.41, taxes=tax_16 + tax_53)],
                69.29,
            ),
            self._prepare_tax_amount_test(
                self._prepare_document_params(rounding_method='round_per_line'),
                [
                    self._prepare_document_line_params(50.4, taxes=tax_17a),
                    self._prepare_document_line_params(47.21, taxes=tax_17b),
                ],
                16.60,
            ),
            self._prepare_tax_amount_test(
                self._prepare_document_params(rounding_method='round_globally'),
                [
                    self._prepare_document_line_params(50.4, taxes=tax_17a),
                    self._prepare_document_line_params(47.21, taxes=tax_17b)
                ],
                16.60,
            ),
            self._prepare_tax_amount_test(
                self._prepare_document_params(rounding_method='round_per_line'),
                [
                    self._prepare_document_line_params(50.4, taxes=tax_17a),
                    self._prepare_document_line_params(47.21, taxes=tax_17a),
                ],
                16.60,
            ),
            self._prepare_tax_amount_test(
                self._prepare_document_params(rounding_method='round_globally'),
                [
                    self._prepare_document_line_params(50.4, taxes=tax_17a),
                    self._prepare_document_line_params(47.21, taxes=tax_17a),
                ],
                16.59,
            ),
            self._prepare_tax_amount_test(
                self._prepare_document_params(rounding_method='round_per_line'),
                [
                    self._prepare_document_line_params(54.45, taxes=tax_10),
                    self._prepare_document_line_params(100.0, taxes=tax_10),
                ],
                15.45,
            ),
            self._prepare_tax_amount_test(
                self._prepare_document_params(rounding_method='round_globally'),
                [
                    self._prepare_document_line_params(54.45, taxes=tax_10),
                    self._prepare_document_line_params(100.0, taxes=tax_10),
                ],
                15.45,
            ),
            self._prepare_tax_amount_test(
                self._prepare_document_params(rounding_method='round_per_line'),
                [
                    self._prepare_document_line_params(54.45, taxes=tax_10),
                    self._prepare_document_line_params(600.0, taxes=tax_10),
                    self._prepare_document_line_params(-500.0, taxes=tax_10),
                ],
                15.45,
            ),
            self._prepare_tax_amount_test(
                self._prepare_document_params(rounding_method='round_globally'),
                [
                    self._prepare_document_line_params(54.45, taxes=tax_10),
                    self._prepare_document_line_params(600.0, taxes=tax_10),
                    self._prepare_document_line_params(-500.0, taxes=tax_10),
                ],
                15.44,
            ),
            self._prepare_tax_amount_test(
                self._prepare_document_params(rounding_method='round_per_line'),
                [
                    self._prepare_document_line_params(94.7, taxes=tax_23_1),
                    self._prepare_document_line_params(32.8, taxes=tax_23_2),
                ],
                29.32,
            ),
            self._prepare_tax_amount_test(
                self._prepare_document_params(rounding_method='round_globally'),
                [
                    self._prepare_document_line_params(94.7, taxes=tax_23_1),
                    self._prepare_document_line_params(32.8, taxes=tax_23_2),
                ],
                29.32,
            ),
        ]

        self._assert_tests(tests)
