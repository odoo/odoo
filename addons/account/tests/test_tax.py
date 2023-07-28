# -*- coding: utf-8 -*-
from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


class TestTaxCommon(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.number = 0
        cls.maxDiff = None

    def tax_base_line(self, price_unit, code=None, **kwargs):
        return self.env['account.tax']._convert_to_tax_base_line_dict(
            code,
            quantity=1.0,
            **kwargs,
            price_unit=price_unit,
        )

    def new_currency(self, rounding):
        self.number += 1
        return self.env.company.currency_id.copy({
            'name': f"{self.number}",
            'rounding': rounding,
        })

    def group_of_taxes(self, taxes, **kwargs):
        self.number += 1
        return self.env['account.tax'].create({
            **kwargs,
            'name': f"group_({self.number})",
            'amount_type': 'group',
            'children_tax_ids': [Command.set(taxes.ids)],
        })

    def percent_tax(self, amount, **kwargs):
        self.number += 1
        return self.env['account.tax'].create({
            **kwargs,
            'name': f"percent_{amount}_({self.number})",
            'amount_type': 'percent',
            'amount': amount,
        })

    def division_tax(self, amount, **kwargs):
        self.number += 1
        return self.env['account.tax'].create({
            **kwargs,
            'name': f"division_{amount}_({self.number})",
            'amount_type': 'division',
            'amount': amount,
        })

    def fixed_tax(self, amount, **kwargs):
        self.number += 1
        return self.env['account.tax'].create({
            **kwargs,
            'name': f"fixed_{amount}_({self.number})",
            'amount_type': 'fixed',
            'amount': amount,
        })

    def _check_tax_results(self, taxes, expected_values, price_unit, **kwargs):
        results = taxes.compute_all(price_unit, **kwargs)
        self.assertAlmostEqual(results['total_included'], expected_values['total_included'])
        self.assertAlmostEqual(results['total_excluded'], expected_values['total_excluded'])
        self.assertEqual(len(results['taxes']), len(expected_values['taxes']))
        for values, expected_values in zip(results['taxes'], expected_values['taxes']):
            self.assertEqual(round(values['base'], 6), expected_values[0])
            self.assertEqual(round(values['amount'], 6), expected_values[1])


@tagged('post_install', '-at_install')
class TestTax(TestTaxCommon):

    def test_tax_groups(self):
        """ Test the tax groups are well flattened to perform the computation. """
        tax_group1 = self.group_of_taxes(
            self.fixed_tax(10.0, include_base_amount=True)
            + self.percent_tax(10.0)
        )
        tax_group2 = self.group_of_taxes(
            self.fixed_tax(10.0, include_base_amount=True)
            + self.percent_tax(10.0)
        )
        tax_group_of_groups = self.group_of_taxes(tax_group1 + tax_group2)

        self._check_tax_results(
            tax_group1,
            {
                'total_included': 231.0,
                'total_excluded': 200.0,
                'taxes': (
                    (200.0, 10.0),
                    (210.0, 21.0),
                ),
            },
            200.0,
        )

        self._check_tax_results(
            tax_group_of_groups,
            {
                'total_included': 263.0,
                'total_excluded': 200.0,
                'taxes': (
                    (200.0, 10.0),
                    (210.0, 21.0),
                    (210.0, 10.0),
                    (220.0, 22.0),
                ),
            },
            200.0,
        )

    def test_forced_price_include_context_key(self):
        """ Test the 'force_price_include' context key that force all taxes to act as price included taxes. """
        taxes = (self.percent_tax(10.0) + self.percent_tax(10.0)).with_context({'force_price_include': True})
        self._check_tax_results(
            taxes,
            {
                'total_included': 100.0,
                'total_excluded': 83.34,
                'taxes': (
                    (83.34, 8.33),
                    (83.34, 8.33),
                ),
            },
            100.0,
        )

    def test_taxes_ordering(self):
        """ Ensure the taxes are sorted according the sequence during the computation. """
        tax_division = self.division_tax(10.0, sequence=1)
        tax_fixed = self.fixed_tax(10.0, sequence=2)
        tax_percent = self.percent_tax(10.0, sequence=3)
        tax_group = self.group_of_taxes(tax_fixed + tax_percent, sequence=4)
        self._check_tax_results(
            tax_group | tax_division,
            {
                'total_included': 252.22,
                'total_excluded': 200.0,
                'taxes': (
                    (200.0, 22.22),
                    (200.0, 10.0),
                    (200.0, 20.0),
                ),
            },
            200.0,
        )

    def test_tax_repartition_lines_intracomm_tax(self):
        ''' Test usage of intracomm taxes having e.g.+100%, -100% as repartition lines. '''
        common_values = {
            'invoice_repartition_line_ids': [
                Command.create({'repartition_type': 'base', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': -100.0}),
            ],
            'refund_repartition_line_ids': [
                Command.create({'repartition_type': 'base', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': -100.0}),
            ],
        }
        tax_price_excluded = self.percent_tax(21.0, **common_values)
        tax_price_included = self.percent_tax(21.0, price_include=True, **common_values)

        for tax in (tax_price_included, tax_price_excluded):
            for sign in (1, -1):
                with self.subTest(sign=sign, price_include=tax.price_include):
                    self._check_tax_results(
                        tax,
                        {
                            'total_included': sign * 100.0,
                            'total_excluded': sign * 100.0,
                            'taxes': (
                                (sign * 100.0, sign * 21.0),
                                (sign * 100.0, -sign * 21.0),
                            ),
                        },
                        sign * 100.0,
                    )

    def test_tax_repartition_lines_dispatch_amount_1(self):
        ''' Ensure the tax amount is well dispatched to the repartition lines and the rounding errors are well managed. '''
        tax = self.percent_tax(
            3.0,
            invoice_repartition_line_ids=[
                Command.create({'repartition_type': 'base', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 50.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 50.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 50.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 50.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 50.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 50.0}),
            ],
            refund_repartition_line_ids=[
                Command.create({'repartition_type': 'base', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 50.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 50.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 50.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 50.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 50.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 50.0}),
            ],
        )

        for sign in (1, -1):
            with self.subTest(sign=sign):
                self._check_tax_results(
                    tax,
                    {
                        'total_included': sign * 1.09,
                        'total_excluded': sign * 1.0,
                        'taxes': (
                            (sign * 1.0, sign * 0.01),
                            (sign * 1.0, sign * 0.01),
                            (sign * 1.0, sign * 0.01),
                            (sign * 1.0, sign * 0.02),
                            (sign * 1.0, sign * 0.02),
                            (sign * 1.0, sign * 0.02),
                        ),
                    },
                    sign * 1.0,
                )

    def test_tax_repartition_lines_dispatch_amount_2(self):
        ''' Ensure the tax amount is well dispatched to the repartition lines and the rounding errors are well managed. '''
        tax = self.percent_tax(
            3.0,
            invoice_repartition_line_ids=[
                Command.create({'repartition_type': 'base', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 50.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': -50.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 25.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 25.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': -25.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': -25.0}),
            ],
            refund_repartition_line_ids=[
                Command.create({'repartition_type': 'base', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 50.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': -50.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 25.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 25.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': -25.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': -25.0}),
            ],
        )

        for sign in (1, -1):
            with self.subTest(sign=sign):
                self._check_tax_results(
                    tax,
                    {
                        'total_included': sign * 1.0,
                        'total_excluded': sign * 1.0,
                        'taxes': (
                            (sign * 1.0, sign * 0.02),
                            (sign * 1.0, sign * -0.02),
                            (sign * 1.0, sign * 0.01),
                            (sign * 1.0, sign * 0.01),
                            (sign * 1.0, sign * -0.01),
                            (sign * 1.0, sign * -0.01),
                        ),
                    },
                    sign * 1.0,
                )

    def test_specific_taxes_computation_in_both_round_per_line_round_globally(self):
        currency_dp_0 = self.new_currency(rounding=1.0)
        currency_dp_2 = self.new_currency(rounding=0.01)
        currency_dp_6 = self.new_currency(rounding=0.000001)
        currency_dp_half = self.new_currency(rounding=0.05)
        tax_percent_19 = self.percent_tax(19.0)
        tax_percent_0_price_included = self.percent_tax(0.0, price_include=True)
        tax_percent_5_price_included = self.percent_tax(5.0, price_include=True)
        tax_percent_8_price_included = self.percent_tax(8.0, price_include=True)
        tax_percent_19_price_included = self.percent_tax(19.0, price_include=True)
        tax_percent_12_price_included = self.percent_tax(12.0, price_include=True)
        tax_percent_20_price_included = self.percent_tax(20.0, price_include=True)
        tax_percent_21_price_included = self.percent_tax(21.0, price_include=True)

        with self.subTest('round_per_line'):
            self.env.company.tax_calculation_rounding_method = 'round_per_line'
            self._check_tax_results(
                tax_percent_8_price_included + tax_percent_0_price_included,
                {
                    'total_included': 124.40,
                    'total_excluded': 115.19,
                    'taxes': (
                        (115.19, 9.21),
                        (115.19, 0.00),
                    ),
                },
                124.40,
                currency=currency_dp_2,
            )
            self._check_tax_results(
                tax_percent_5_price_included,
                {
                    'total_included': 5.0,
                    'total_excluded': 4.75,
                    'taxes': (
                        (4.75, 0.25),
                    ),
                },
                5.0,
                currency=currency_dp_half,
            )
            self._check_tax_results(
                tax_percent_5_price_included,
                {
                    'total_included': 10.0,
                    'total_excluded': 9.5,
                    'taxes': (
                        (9.5, 0.5),
                    ),
                },
                10.0,
                currency=currency_dp_half,
            )
            self._check_tax_results(
                tax_percent_5_price_included,
                {
                    'total_included': 50.0,
                    'total_excluded': 47.6,
                    'taxes': (
                        (47.6, 2.4),
                    ),
                },
                50.0,
                currency=currency_dp_half,
            )
            self._check_tax_results(
                tax_percent_12_price_included,
                {
                    'total_included': 52.50,
                    'total_excluded': 46.87,
                    'taxes': (
                        (46.87, 5.63),
                    ),
                },
                52.50,
                currency=currency_dp_2,
            )
            self._check_tax_results(
                tax_percent_19,
                {
                    'total_included': 27000.0,
                    'total_excluded': 22689.0,
                    'taxes': (
                        (22689, 4311),
                    ),
                },
                22689.0,
                currency=currency_dp_0,
            )
            self._check_tax_results(
                tax_percent_19,
                {
                    'total_included': 10919.0,
                    'total_excluded': 9176.0,
                    'taxes': (
                        (9176,  1743),
                    ),
                },
                9176.0,
                currency=currency_dp_0,
            )
            self._check_tax_results(
                tax_percent_19_price_included,
                {
                    'total_included': 27000.0,
                    'total_excluded': 22689.0,
                    'taxes': (
                        (22689.0,  4311.0),
                    ),
                },
                27000.0,
                currency=currency_dp_0,
            )
            self._check_tax_results(
                tax_percent_19_price_included,
                {
                    'total_included': 10920.0,
                    'total_excluded': 9176.0,
                    'taxes': (
                        (9176.0,  1744.0),
                    ),
                },
                10920.0,
                currency=currency_dp_0,
            )
            self._check_tax_results(
                tax_percent_20_price_included,
                {
                    'total_included': 399.999999,
                    'total_excluded': 333.333332,
                    'taxes': (
                        # 399.999999 / 1.20 * 0.20 ~= 66.666667
                        # 399.999999 - 66.666667 = 333.333332
                        (333.333332, 66.666667),
                    ),
                },
                399.999999,
                currency=currency_dp_6,
            )
            self._check_tax_results(
                tax_percent_21_price_included,
                {
                    'total_included': 11.90,
                    'total_excluded': 9.83,
                    'taxes': (
                        (9.83, 2.07),
                    ),
                },
                11.90,
                currency=currency_dp_2,
            )
            self._check_tax_results(
                tax_percent_21_price_included,
                {
                    'total_included': 2.80,
                    'total_excluded': 2.31,
                    'taxes': (
                        (2.31,  0.49),
                    ),
                },
                2.80,
                currency=currency_dp_2,
            )
            self._check_tax_results(
                tax_percent_21_price_included,
                {
                    'total_included': 7.0,
                    'total_excluded': 5.785124,
                    'taxes': (
                        (5.785124, 1.214876),
                    ),
                },
                7.0,
                currency=currency_dp_6,
            )

        with self.subTest('round_globally'):
            self.env.company.tax_calculation_rounding_method = 'round_globally'
            self._check_tax_results(
                tax_percent_8_price_included + tax_percent_0_price_included,
                {
                    'total_included': 124.40,
                    'total_excluded': 115.19,
                    'taxes': (
                        (115.185185, 9.214815),
                        (115.185185, 0.00),
                    ),
                },
                124.40,
                currency=currency_dp_2,
            )
            self._check_tax_results(
                tax_percent_5_price_included,
                {
                    'total_included': 5.0,
                    'total_excluded': 4.75,
                    'taxes': (
                        (4.761905, 0.238095),
                    ),
                },
                5.0,
                currency=currency_dp_half,
            )
            self._check_tax_results(
                tax_percent_5_price_included,
                {
                    'total_included': 10.0,
                    'total_excluded': 9.5,
                    'taxes': (
                        (9.52381, 0.47619),
                    ),
                },
                10.0,
                currency=currency_dp_half,
            )
            self._check_tax_results(
                tax_percent_5_price_included,
                {
                    'total_included': 50.0,
                    'total_excluded': 47.6,
                    'taxes': (
                        (47.619048, 2.380952),
                    ),
                },
                50.0,
                currency=currency_dp_half,
            )
            self._check_tax_results(
                tax_percent_12_price_included,
                {
                    'total_included': 52.50,
                    'total_excluded': 46.88,
                    'taxes': (
                        (46.875, 5.625),
                    ),
                },
                52.50,
                currency=currency_dp_2,
            )
            self._check_tax_results(
                tax_percent_19,
                {
                    'total_included': 27000.0,
                    'total_excluded': 22689.0,
                    'taxes': (
                        (22689, 4310.91),
                    ),
                },
                22689.0,
                currency=currency_dp_0,
            )
            self._check_tax_results(
                tax_percent_19,
                {
                    'total_included': 10919.0,
                    'total_excluded': 9176.0,
                    'taxes': (
                        (9176,  1743.44),
                    ),
                },
                9176.0,
                currency=currency_dp_0,
            )
            self._check_tax_results(
                tax_percent_19_price_included,
                {
                    'total_included': 27000.0,
                    'total_excluded': 22689.0,
                    'taxes': (
                        (22689.07563,  4310.92437),
                    ),
                },
                27000.0,
                currency=currency_dp_0,
            )
            self._check_tax_results(
                tax_percent_19_price_included,
                {
                    'total_included': 10920.0,
                    'total_excluded': 9176.0,
                    'taxes': (
                        (9176.470588,  1743.529412),
                    ),
                },
                10920.0,
                currency=currency_dp_0,
            )
            self._check_tax_results(
                tax_percent_20_price_included,
                {
                    'total_included': 399.999999,
                    'total_excluded': 333.333333,
                    'taxes': (
                        (333.333332, 66.666667),
                    ),
                },
                399.999999,
                currency=currency_dp_6,
            )
            self._check_tax_results(
                tax_percent_21_price_included,
                {
                    'total_included': 2.80,
                    'total_excluded': 2.31,
                    'taxes': (
                        (2.31405,  0.48595),
                    ),
                },
                2.80,
                currency=currency_dp_2,
            )
            self._check_tax_results(
                tax_percent_21_price_included,
                {
                    'total_included': 7.0,
                    'total_excluded': 5.785124,
                    'taxes': (
                        (5.785124, 1.214876),
                    ),
                },
                7.0,
                currency=currency_dp_6,
            )

    def test_fixed_tax_price_included_affect_base_on_0(self):
        tax = self.fixed_tax(0.05, price_include=True, include_base_amount=True)
        self._check_tax_results(
            tax,
            {
                'total_included': 0.0,
                'total_excluded': -0.05,
                'taxes': (
                    (-0.05, 0.05),
                ),
            },
            0.0,
        )

    def test_percent_taxes_for_l10n_in(self):
        tax1 = self.percent_tax(6)
        tax2 = self.percent_tax(6)
        tax3 = self.percent_tax(3)

        self._check_tax_results(
            tax1 + tax2 + tax3,
            {
                'total_included': 115.0,
                'total_excluded': 100.0,
                'taxes': (
                    (100.0, 6.0),
                    (100.0, 6.0),
                    (100.0, 3.0),
                ),
            },
            100.0,
        )

        tax1.include_base_amount = True
        self._check_tax_results(
            tax1 + tax2 + tax3,
            {
                'total_included': 115.54,
                'total_excluded': 100.0,
                'taxes': (
                    (100.0, 6.0),
                    (106.0, 6.36),
                    (106.0, 3.18),
                ),
            },
            100.0,
        )

        tax2.include_base_amount = True
        self._check_tax_results(
            tax1 + tax2 + tax3,
            {
                'total_included': 115.73,
                'total_excluded': 100.0,
                'taxes': (
                    (100.0, 6.0),
                    (106.0, 6.36),
                    (112.36, 3.37),
                ),
            },
            100.0,
        )

        tax2.is_base_affected = False
        self._check_tax_results(
            tax1 + tax2 + tax3,
            {
                'total_included': 115.36,
                'total_excluded': 100.0,
                'taxes': (
                    (100.0, 6.0),
                    (100.0, 6.0),
                    (112.0, 3.36),
                ),
            },
            100.0,
        )

        tax1.price_include = True
        tax2.price_include = True
        self._check_tax_results(
            tax1 + tax2 + tax3,
            {
                'total_included': 115.36,
                'total_excluded': 100.0,
                'taxes': (
                    (100.0, 6.0),
                    (100.0, 6.0),
                    (112.0, 3.36),
                ),
            },
            112.0,
        )

        # Ensure tax1 & tax2 give always the same result.
        self._check_tax_results(
            tax1 + tax2,
            {
                'total_included': 17.79,
                'total_excluded': 15.89,
                'taxes': (
                    (15.89, 0.95),
                    (15.89, 0.95),
                ),
            },
            17.79,
        )

    def test_division_taxes_for_l10n_br(self):
        tax1 = self.division_tax(5)
        tax2 = self.division_tax(3)
        tax3 = self.division_tax(0.65)
        tax4 = self.division_tax(9)
        tax5 = self.division_tax(15)

        self._check_tax_results(
            tax1 + tax2 + tax3 + tax4 + tax5,
            {
                'total_included': 44.15,
                'total_excluded': 32.33,
                'taxes': (
                    (32.33, 1.7),
                    (32.33, 1.0),
                    (32.33, 0.21),
                    (32.33, 3.2),
                    (32.33, 5.71),
                ),
            },
            32.33,
        )

        tax1.price_include = True
        tax2.price_include = True
        tax3.price_include = True
        tax4.price_include = True
        tax5.price_include = True
        self._check_tax_results(
            tax1 + tax2 + tax3 + tax4 + tax5,
            {
                'total_included': 48.0,
                'total_excluded': 32.33,
                'taxes': (
                    (32.33, 2.4),
                    (32.33, 1.44),
                    (32.33, 0.31),
                    (32.33, 4.32),
                    (32.33, 7.2),
                ),
            },
            48.0,
        )

    def test_fixed_taxes_for_l10n_be(self):
        tax1 = self.fixed_tax(1)
        tax2 = self.percent_tax(21)
        tax3 = self.fixed_tax(2)

        self._check_tax_results(
            tax1 + tax2 + tax3,
            {
                'total_included': 136.0,
                'total_excluded': 100.0,
                'taxes': (
                    (100.0, 5.0),
                    (100.0, 21.0),
                    (100.0, 10.0),
                ),
            },
            20.0,
            quantity=5,
        )

        tax1.include_base_amount = True
        self._check_tax_results(
            tax1 + tax2 + tax3,
            {
                'total_included': 131.0,
                'total_excluded': 95.0,
                'taxes': (
                    (95.0, 5.0),
                    (100.0, 21.0),
                    (100.0, 10.0),
                ),
            },
            19.0,
            quantity=5,
        )

        tax2.price_include = True
        self._check_tax_results(
            tax1 + tax2 + tax3,
            {
                'total_included': 123.0,
                'total_excluded': 99.0,
                'taxes': (
                    (99.0, 1.0),
                    (100.0, 21.0),
                    (121.0, 2.0),
                ),
            },
            120.0,
        )

        tax2.include_base_amount = True
        self._check_tax_results(
            tax1 + tax2 + tax3,
            {
                'total_included': 123.0,
                'total_excluded': 99.0,
                'taxes': (
                    (99.0, 1.0),
                    (100.0, 21.0),
                    (121.0, 2.0),
                ),
            },
            120.0,
        )

        tax1.include_base_amount = False
        self._check_tax_results(
            tax1 + tax2 + tax3,
            {
                'total_included': 124.0,
                'total_excluded': 100.0,
                'taxes': (
                    (100.0, 1.0),
                    (100.0, 21.0),
                    (121.0, 2.0),
                ),
            },
            121.0,
        )

        tax1.price_include = True
        self._check_tax_results(
            tax1 + tax2 + tax3,
            {
                'total_included': 123.0,
                'total_excluded': 99.0,
                'taxes': (
                    (99.0, 1.0),
                    (100.0, 21.0),
                    (121.0, 2.0),
                ),
            },
            121.0,
        )

    def test_parse_name_search(self):
        list_ten_fixed_tax = self.env["account.tax"]
        ten_fixed_tax = self.env["account.tax"].create(
            {"name": "Ten Fixed tax", "amount_type": "fixed", "amount": 10}
        )
        list_ten_fixed_tax |= ten_fixed_tax
        ten_fixed_tax_tix = self.env["account.tax"].create(
            {"name": "Ten Fixed tax tix", "amount_type": "fixed", "amount": 10}
        )
        list_ten_fixed_tax |= ten_fixed_tax_tix

        self.assertListEqual(
            [x[0] for x in self.env["account.tax"].name_search("tix")],
            list_ten_fixed_tax.ids,
        )
        self.assertListEqual(
            [x[0] for x in self.env["account.tax"].name_search("\"tix\"")],
            ten_fixed_tax_tix.ids,
        )
        self.assertListEqual(
            [x[0] for x in self.env["account.tax"].name_search("Ten \"tix\"")],
            ten_fixed_tax_tix.ids,
        )
