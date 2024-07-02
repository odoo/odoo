# -*- coding: utf-8 -*-
from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tools.float_utils import float_round


class TestTaxCommon(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.number = 0
        cls.maxDiff = None

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

    def _check_compute_all_results(self, taxes, expected_values, price_unit, **kwargs):
        results = taxes.compute_all(price_unit, **kwargs)
        self.assertAlmostEqual(results['total_included'], expected_values['total_included'])
        self.assertAlmostEqual(results['total_excluded'], expected_values['total_excluded'])
        self.assertEqual(len(results['taxes']), len(expected_values['taxes']))
        for values, tax_expected_values in zip(results['taxes'], expected_values['taxes']):
            self.assertEqual(round(values['base'], 6), tax_expected_values[0])
            self.assertEqual(round(values['amount'], 6), tax_expected_values[1])

    def _check_tax_results(self, taxes, expected_values, price_unit, evaluation_context_kwargs=None, compute_kwargs=None):
        """ Evaluate the taxes computation and compare the results with the expected ones.

        [!] Mirror of the same test in test_account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
        """

        def compare_values(results, expected_values, rounding):
            self.assertEqual(
                float_round(results['total_included'], precision_rounding=rounding),
                float_round(expected_values['total_included'], precision_rounding=rounding),
            )
            self.assertEqual(
                float_round(results['total_excluded'], precision_rounding=rounding),
                float_round(expected_values['total_excluded'], precision_rounding=rounding),
            )
            self.assertEqual(len(results['tax_values_list']), len(expected_values['tax_values_list']))
            for tax_values, expected_tax_values in zip(results['tax_values_list'], expected_values['tax_values_list']):
                self.assertEqual(
                    float_round(tax_values['base'], precision_rounding=rounding),
                    float_round(expected_tax_values[0], precision_rounding=rounding),
                )
                self.assertEqual(
                    float_round(tax_values['tax_amount_factorized'], precision_rounding=rounding),
                    float_round(expected_tax_values[1], precision_rounding=rounding),
                )

        evaluation_context_kwargs = evaluation_context_kwargs or {}
        compute_kwargs = compute_kwargs or {}
        quantity = evaluation_context_kwargs.pop('quantity', 1)
        evaluation_context = taxes._eval_taxes_computation_prepare_context(price_unit, quantity, **evaluation_context_kwargs)
        taxes_computation = taxes._prepare_taxes_computation(taxes._convert_to_dict_for_taxes_computation(), **compute_kwargs)
        results = taxes._eval_taxes_computation(taxes_computation, evaluation_context)
        is_round_globally = evaluation_context_kwargs.get('rounding_method') == 'round_globally'
        rounding = 0.000001 if is_round_globally else 0.01
        compare_values(results, expected_values, rounding)

        # Check the reverse in case of round_globally.
        if is_round_globally:
            evaluation_context = taxes._eval_taxes_computation_prepare_context(results['total_excluded'], quantity, **{
                **evaluation_context_kwargs,
                'reverse': True,
            })
            results = taxes._eval_taxes_computation(taxes_computation, evaluation_context)
            compare_values(results, expected_values, rounding)
            delta = sum(x['tax_amount_factorized'] for x in results['tax_values_list'] if x['price_include'])
            self.assertEqual(
                float_round(results['total_excluded'] + delta, precision_rounding=rounding),
                float_round(price_unit, precision_rounding=rounding),
            )


@tagged('post_install', '-at_install')
class TestTax(TestTaxCommon):

    def test_forced_price_include_context_key(self):
        """ Test the 'force_price_include' context key that force all taxes to act as price included taxes. """
        taxes = (self.percent_tax(10.0) + self.percent_tax(10.0)).with_context({'force_price_include': True})
        self._check_compute_all_results(
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
        """ Ensure the taxes are sorted according the sequence during the computation.

        [!] Mirror of the same test in test_account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
        """
        tax_division = self.division_tax(10.0, sequence=1)
        tax_fixed = self.fixed_tax(10.0, sequence=2)
        tax_percent = self.percent_tax(10.0, sequence=3)
        tax_group = self.group_of_taxes(tax_fixed + tax_percent, sequence=4)
        self._check_tax_results(
            tax_group | tax_division,
            {
                'total_included': 252.22,
                'total_excluded': 200.0,
                'tax_values_list': (
                    (200.0, 22.22),
                    (200.0, 10.0),
                    (200.0, 20.0),
                ),
            },
            200.0,
        )

    def test_tax_repartition_lines_intracomm_tax(self):
        ''' Test usage of intracomm taxes having e.g.+100%, -100% as repartition lines.'''
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
                    self._check_compute_all_results(
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
                self._check_compute_all_results(
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
                self._check_compute_all_results(
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

    def test_random_case_1(self):
        """
        [!] Mirror of the same test in test_account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
        """
        tax_percent_8_price_included = self.percent_tax(8.0, price_include=True)
        tax_percent_0_price_included = self.percent_tax(0.0, price_include=True)

        self._check_tax_results(
            tax_percent_8_price_included + tax_percent_0_price_included,
            {
                'total_included': 124.40,
                'total_excluded': 115.19,
                'tax_values_list': (
                    (115.19, 9.21),
                    (115.19, 0.0),
                ),
            },
            124.40,
            {'rounding_method': 'round_per_line'},
        )

        self._check_tax_results(
            tax_percent_8_price_included + tax_percent_0_price_included,
            {
                'total_included': 124.40,
                'total_excluded': 115.185185,
                'tax_values_list': (
                    (115.185185, 9.214815),
                    (115.185185, 0.0),
                ),
            },
            124.40,
            {'rounding_method': 'round_globally'},
        )

    def test_random_case_2(self):
        """
        [!] Mirror of the same test in test_account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
        """
        tax_percent_5_price_included = self.percent_tax(5.0, price_include=True)
        currency_dp_half = 0.05

        self._check_tax_results(
            tax_percent_5_price_included,
            {
                'total_included': 5.0,
                'total_excluded': 4.75,
                'tax_values_list': (
                    (4.75, 0.25),
                ),
            },
            5.0,
            {'rounding_method': 'round_per_line', 'precision_rounding': currency_dp_half},
        )
        self._check_tax_results(
            tax_percent_5_price_included,
            {
                'total_included': 10.0,
                'total_excluded': 9.5,
                'tax_values_list': (
                    (9.5, 0.5),
                ),
            },
            10.0,
            {'rounding_method': 'round_per_line', 'precision_rounding': currency_dp_half},
        )
        self._check_tax_results(
            tax_percent_5_price_included,
            {
                'total_included': 50.0,
                'total_excluded': 47.6,
                'tax_values_list': (
                    (47.6, 2.4),
                ),
            },
            50.0,
            {'rounding_method': 'round_per_line', 'precision_rounding': currency_dp_half},
        )

        self._check_tax_results(
            tax_percent_5_price_included,
            {
                'total_included': 5.0,
                'total_excluded': 4.761905,
                'tax_values_list': (
                    (4.761905, 0.238095),
                ),
            },
            5.0,
            {'rounding_method': 'round_globally'},
        )
        self._check_tax_results(
            tax_percent_5_price_included,
            {
                'total_included': 10.0,
                'total_excluded': 9.52381,
                'tax_values_list': (
                    (9.52381, 0.47619),
                ),
            },
            10.0,
            {'rounding_method': 'round_globally'},
        )
        self._check_tax_results(
            tax_percent_5_price_included,
            {
                'total_included': 50.0,
                'total_excluded': 47.619048,
                'tax_values_list': (
                    (47.619048, 2.380952),
                ),
            },
            50.0,
            {'rounding_method': 'round_globally'},
        )

    def test_random_case_3(self):
        """
        [!] Mirror of the same test in test_account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
        """
        tax_percent_15_price_excluded = self.percent_tax(15.0)
        tax_percent_5_5_price_included = self.percent_tax(5.5, price_include=True)

        self._check_tax_results(
            tax_percent_15_price_excluded + tax_percent_5_5_price_included,
            {
                'total_included': 2627.01,
                'total_excluded': 2180.09,
                'tax_values_list': (
                    (2180.09, 327.01),
                    (2180.09, 119.91),
                ),
            },
            2300.0,
            {'rounding_method': 'round_per_line'},
        )

        self._check_tax_results(
            tax_percent_15_price_excluded + tax_percent_5_5_price_included,
            {
                'total_included': 2627.014218,
                'total_excluded': 2180.094787,
                'tax_values_list': (
                    (2180.094787, 327.014218),
                    (2180.094787, 119.905213),
                ),
            },
            2300.0,
            {'rounding_method': 'round_globally'},
        )

    def test_random_case_4(self):
        """
        [!] Mirror of the same test in test_account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
        """
        tax_percent_12_price_included = self.percent_tax(12.0, price_include=True)

        self._check_tax_results(
            tax_percent_12_price_included,
            {
                'total_included': 52.50,
                'total_excluded': 46.87,
                'tax_values_list': (
                    (46.87, 5.63),
                ),
            },
            52.50,
            {'rounding_method': 'round_per_line'},
        )

        self._check_tax_results(
            tax_percent_12_price_included,
            {
                'total_included': 52.50,
                'total_excluded': 46.875,
                'tax_values_list': (
                    (46.875, 5.625),
                ),
            },
            52.50,
            {'rounding_method': 'round_globally'},
        )

    def test_random_case_5(self):
        """
        [!] Mirror of the same test in test_account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
        """
        tax_percent_19 = self.percent_tax(19.0)
        tax_percent_19_price_included = self.percent_tax(19.0, price_include=True)
        currency_dp_0 = 1.0

        self._check_tax_results(
            tax_percent_19,
            {
                'total_included': 27000.0,
                'total_excluded': 22689.0,
                'tax_values_list': (
                    (22689, 4311),
                ),
            },
            22689.0,
            {'rounding_method': 'round_per_line', 'precision_rounding': currency_dp_0},
        )
        self._check_tax_results(
            tax_percent_19,
            {
                'total_included': 10919.0,
                'total_excluded': 9176.0,
                'tax_values_list': (
                    (9176, 1743),
                ),
            },
            9176.0,
            {'rounding_method': 'round_per_line', 'precision_rounding': currency_dp_0},
        )
        self._check_tax_results(
            tax_percent_19_price_included,
            {
                'total_included': 27000.0,
                'total_excluded': 22689.0,
                'tax_values_list': (
                    (22689.0, 4311.0),
                ),
            },
            27000.0,
            {'rounding_method': 'round_per_line', 'precision_rounding': currency_dp_0},
        )
        self._check_tax_results(
            tax_percent_19_price_included,
            {
                'total_included': 10920.0,
                'total_excluded': 9176.0,
                'tax_values_list': (
                    (9176.0, 1744.0),
                ),
            },
            10920.0,
            {'rounding_method': 'round_per_line', 'precision_rounding': currency_dp_0},
        )

        self._check_tax_results(
            tax_percent_19,
            {
                'total_included': 26999.91,
                'total_excluded': 22689.0,
                'tax_values_list': (
                    (22689, 4310.91),
                ),
            },
            22689.0,
            {'rounding_method': 'round_globally'},
        )
        self._check_tax_results(
            tax_percent_19,
            {
                'total_included': 10919.44,
                'total_excluded': 9176.0,
                'tax_values_list': (
                    (9176, 1743.44),
                ),
            },
            9176.0,
            {'rounding_method': 'round_globally'},
        )
        self._check_tax_results(
            tax_percent_19_price_included,
            {
                'total_included': 27000.0,
                'total_excluded': 22689.07563,
                'tax_values_list': (
                    (22689.07563, 4310.92437),
                ),
            },
            27000.0,
            {'rounding_method': 'round_globally'},
        )
        self._check_tax_results(
            tax_percent_19_price_included,
            {
                'total_included': 10920.0,
                'total_excluded': 9176.470588,
                'tax_values_list': (
                    (9176.470588, 1743.529412),
                ),
            },
            10920.0,
            {'rounding_method': 'round_globally'},
        )

    def test_random_case_6(self):
        """
        [!] Mirror of the same test in test_account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
        """
        tax_percent_20_price_included = self.percent_tax(20.0, price_include=True)
        currency_dp_6 = 0.000001

        self._check_tax_results(
            tax_percent_20_price_included,
            {
                'total_included': 399.999999,
                'total_excluded': 333.333332,
                'tax_values_list': (
                    # 399.999999 / 1.20 * 0.20 ~= 66.666667
                    # 399.999999 - 66.666667 = 333.333332
                    (333.333332, 66.666667),
                ),
            },
            399.999999,
            {'rounding_method': 'round_per_line', 'precision_rounding': currency_dp_6},
        )

        self._check_tax_results(
            tax_percent_20_price_included,
            {
                'total_included': 399.999999,
                'total_excluded': 333.3333325,
                'tax_values_list': (
                    (333.3333325, 66.6666665),
                ),
            },
            399.999999,
            {'rounding_method': 'round_globally'},
        )

    def test_random_case_7(self):
        """
        [!] Mirror of the same test in test_account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
        """
        tax_percent_21_price_included = self.percent_tax(21.0, price_include=True)
        currency_dp_6 = 0.000001

        self._check_tax_results(
            tax_percent_21_price_included,
            {
                'total_included': 11.90,
                'total_excluded': 9.83,
                'tax_values_list': (
                    (9.83, 2.07),
                ),
            },
            11.90,
            {'rounding_method': 'round_per_line'},
        )
        self._check_tax_results(
            tax_percent_21_price_included,
            {
                'total_included': 2.80,
                'total_excluded': 2.31,
                'tax_values_list': (
                    (2.31, 0.49),
                ),
            },
            2.80,
            {'rounding_method': 'round_per_line'},
        )
        self._check_tax_results(
            tax_percent_21_price_included,
            {
                'total_included': 7.0,
                'total_excluded': 5.785124,
                'tax_values_list': (
                    (5.785124, 1.214876),
                ),
            },
            7.0,
            {'rounding_method': 'round_per_line', 'precision_rounding': currency_dp_6},
        )

        self._check_tax_results(
            tax_percent_21_price_included,
            {
                'total_included': 11.90,
                'total_excluded': 9.834711,
                'tax_values_list': (
                    (9.834711, 2.065289),
                ),
            },
            11.90,
            {'rounding_method': 'round_globally'},
        )
        self._check_tax_results(
            tax_percent_21_price_included,
            {
                'total_included': 2.80,
                'total_excluded': 2.31405,
                'tax_values_list': (
                    (2.31405, 0.48595),
                ),
            },
            2.80,
            {'rounding_method': 'round_globally'},
        )
        self._check_tax_results(
            tax_percent_21_price_included,
            {
                'total_included': 7.0,
                'total_excluded': 5.785124,
                'tax_values_list': (
                    (5.785124, 1.214876),
                ),
            },
            7.0,
            {'rounding_method': 'round_globally'},
        )

    def test_random_case_8(self):
        """
        [!] Mirror of the same test in test_account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
        """
        tax_percent_20_withholding = self.percent_tax(-20.0)
        tax_percent_4 = self.percent_tax(4.0, include_base_amount=True)
        tax_percent_22 = self.percent_tax(22.0)
        taxes = tax_percent_20_withholding + tax_percent_4 + tax_percent_22

        self._check_tax_results(
            taxes,
            {
                'total_included': 53.44,
                'total_excluded': 50.0,
                'tax_values_list': (
                    (50.0, -10.0),
                    (50.0, 2.0),
                    (52.0, 11.44),
                ),
            },
            50.0,
        )

    def test_fixed_tax_price_included_affect_base_on_0(self):
        """
        [!] Mirror of the same test in test_account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
        """
        tax = self.fixed_tax(0.05, price_include=True, include_base_amount=True)
        self._check_tax_results(
            tax,
            {
                'total_included': 0.0,
                'total_excluded': -0.05,
                'tax_values_list': (
                    (-0.05, 0.05),
                ),
            },
            0.0,
        )

    def test_percent_taxes_for_l10n_in(self):
        """
        [!] Mirror of the same test in test_account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
        """
        tax1 = self.percent_tax(6)
        tax2 = self.percent_tax(6)
        tax3 = self.percent_tax(3)

        self._check_tax_results(
            tax1 + tax2 + tax3,
            {
                'total_included': 115.0,
                'total_excluded': 100.0,
                'tax_values_list': (
                    (100.0, 6.0),
                    (100.0, 6.0),
                    (100.0, 3.0),
                ),
            },
            100.0,
        )

        # tax       price_incl      incl_base_amount    is_base_affected
        # ----------------------------------------------------------------
        # tax1                      T                   T
        # tax2                                          T
        # tax3                                          T
        tax1.include_base_amount = True
        self._check_tax_results(
            tax1 + tax2 + tax3,
            {
                'total_included': 115.54,
                'total_excluded': 100.0,
                'tax_values_list': (
                    (100.0, 6.0),
                    (106.0, 6.36),
                    (106.0, 3.18),
                ),
            },
            100.0,
        )

        # tax       price_incl      incl_base_amount    is_base_affected
        # ----------------------------------------------------------------
        # tax1                      T                   T
        # tax2                      T                   T
        # tax3                                          T
        tax2.include_base_amount = True
        self._check_tax_results(
            tax1 + tax2 + tax3,
            {
                'total_included': 115.73,
                'total_excluded': 100.0,
                'tax_values_list': (
                    (100.0, 6.0),
                    (106.0, 6.36),
                    (112.36, 3.37),
                ),
            },
            100.0,
        )

        # tax       price_incl      incl_base_amount    is_base_affected
        # ----------------------------------------------------------------
        # tax1                      T                   T
        # tax2                      T
        # tax3                                          T
        tax2.is_base_affected = False
        self._check_tax_results(
            tax1 + tax2 + tax3,
            {
                'total_included': 115.36,
                'total_excluded': 100.0,
                'tax_values_list': (
                    (100.0, 6.0),
                    (100.0, 6.0),
                    (112.0, 3.36),
                ),
            },
            100.0,
        )
        # Test the reverse:
        self._check_tax_results(
            tax1 + tax2 + tax3,
            {
                'total_included': 115.36,
                'total_excluded': 100.0,
                'tax_values_list': (
                    (100.0, 6.0),
                    (100.0, 6.0),
                    (112.0, 3.36),
                ),
            },
            100.0,
            {'rounding_method': 'round_globally'},
        )

        # tax       price_incl      incl_base_amount    is_base_affected
        # ----------------------------------------------------------------
        # tax1      T               T                   T
        # tax2      T               T
        # tax3                                          T
        tax1.price_include = True
        tax2.price_include = True
        self._check_tax_results(
            tax1 + tax2 + tax3,
            {
                'total_included': 115.36,
                'total_excluded': 100.0,
                'tax_values_list': (
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
                'tax_values_list': (
                    (15.89, 0.95),
                    (15.89, 0.95),
                ),
            },
            17.79,
        )

    def test_division_taxes_for_l10n_br(self):
        """
        [!] Mirror of the same test in test_account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
        """
        tax1 = self.division_tax(5)
        tax2 = self.division_tax(3)
        tax3 = self.division_tax(0.65)
        tax4 = self.division_tax(9)
        tax5 = self.division_tax(15)

        # Same of tax4/tax5 except the amount is based on 32% of the base amount.
        tax4_32 = self.division_tax(9)
        tax5_32 = self.division_tax(15)
        (tax4_32 + tax5_32).invoice_repartition_line_ids\
            .filtered(lambda x: x.repartition_type == 'tax')\
            .factor_percent = 32

        self._check_tax_results(
            tax1 + tax2 + tax3 + tax4 + tax5,
            {
                'total_included': 48.0,
                'total_excluded': 32.33,
                'tax_values_list': (
                    (32.33, 2.4),
                    (32.33, 1.44),
                    (32.33, 0.31),
                    (32.33, 4.32),
                    (32.33, 7.2),
                ),
            },
            32.33,
        )
        self._check_tax_results(
            tax1 + tax2 + tax3 + tax4_32 + tax5_32,
            {
                'total_included': 1000.0,
                'total_excluded': 836.7,
                'tax_values_list': (
                    (836.7, 50.0),
                    (836.7, 30.0),
                    (836.7, 6.5),
                    (836.7, 28.8),
                    (836.7, 48.0),
                ),
            },
            836.7,
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
                'tax_values_list': (
                    (32.33, 2.4),
                    (32.33, 1.44),
                    (32.33, 0.31),
                    (32.33, 4.32),
                    (32.33, 7.2),
                ),
            },
            48.0,
        )
        tax4_32.price_include = True
        tax5_32.price_include = True
        self._check_tax_results(
            tax1 + tax2 + tax3 + tax4_32 + tax5_32,
            {
                'total_included': 1000.0,
                'total_excluded': 836.7,
                'tax_values_list': (
                    (836.7, 50.0),
                    (836.7, 30.0),
                    (836.7, 6.5),
                    (836.7, 28.8),
                    (836.7, 48.0),
                ),
            },
            1000.0,
        )

        # Test the reverse:
        self._check_tax_results(
            tax1 + tax2 + tax3 + tax4 + tax5,
            {
                'total_included': 48.0,
                'total_excluded': 32.3279999,
                'tax_values_list': (
                    (32.3279999, 2.4),
                    (32.3279999, 1.44),
                    (32.3279999, 0.312),
                    (32.3279999, 4.32),
                    (32.3279999, 7.2),
                ),
            },
            48.0,
            {'rounding_method': 'round_globally'},
        )
        self._check_tax_results(
            tax1 + tax2 + tax3 + tax4_32 + tax5_32,
            {
                'total_included': 1000.0,
                'total_excluded': 836.7,
                'tax_values_list': (
                    (836.7, 50.0),
                    (836.7, 30.0),
                    (836.7, 6.5),
                    (836.7, 28.8),
                    (836.7, 48.0),
                ),
            },
            1000.0,
            {'rounding_method': 'round_globally'},
        )

    def test_fixed_taxes_for_l10n_be(self):
        """
        [!] Mirror of the same test in test_account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
        """
        tax1 = self.fixed_tax(1)
        tax2 = self.percent_tax(21)
        tax3 = self.fixed_tax(2)

        self._check_tax_results(
            tax1 + tax2 + tax3,
            {
                'total_included': 136.0,
                'total_excluded': 100.0,
                'tax_values_list': (
                    (100.0, 5.0),
                    (100.0, 21.0),
                    (100.0, 10.0),
                ),
            },
            20.0,
            {'quantity': 5},
        )

        # tax       price_incl      incl_base_amount
        # -----------------------------------------------
        # tax1                      T
        # tax2
        # tax3
        tax1.include_base_amount = True
        self._check_tax_results(
            tax1 + tax2 + tax3,
            {
                'total_included': 131.0,
                'total_excluded': 95.0,
                'tax_values_list': (
                    (95.0, 5.0),
                    (100.0, 21.0),
                    (100.0, 10.0),
                ),
            },
            19.0,
            {'quantity': 5},
        )

        # tax       price_incl      incl_base_amount
        # -----------------------------------------------
        # tax1                      T
        # tax2      T
        # tax3
        tax2.price_include = True
        self._check_tax_results(
            tax1 + tax2 + tax3,
            {
                'total_included': 123.0,
                'total_excluded': 99.0,
                'tax_values_list': (
                    (99.0, 1.0),
                    (100.0, 21.0),
                    (121.0, 2.0),
                ),
            },
            120.0,
        )

        # tax       price_incl      incl_base_amount
        # -----------------------------------------------
        # tax1                      T
        # tax2      T               T
        # tax3
        tax2.include_base_amount = True
        self._check_tax_results(
            tax1 + tax2 + tax3,
            {
                'total_included': 123.0,
                'total_excluded': 99.0,
                'tax_values_list': (
                    (99.0, 1.0),
                    (100.0, 21.0),
                    (121.0, 2.0),
                ),
            },
            120.0,
        )

        # tax       price_incl      incl_base_amount
        # -----------------------------------------------
        # tax1
        # tax2      T               T
        # tax3
        tax1.include_base_amount = False
        self._check_tax_results(
            tax1 + tax2 + tax3,
            {
                'total_included': 124.0,
                'total_excluded': 100.0,
                'tax_values_list': (
                    (100.0, 1.0),
                    (100.0, 21.0),
                    (121.0, 2.0),
                ),
            },
            121.0,
        )

        # tax       price_incl      incl_base_amount
        # -----------------------------------------------
        # tax1      T
        # tax2      T               T
        # tax3
        tax1.price_include = True
        self._check_tax_results(
            tax1 + tax2 + tax3,
            {
                'total_included': 123.0,
                'total_excluded': 99.0,
                'tax_values_list': (
                    (99.0, 1.0),
                    (100.0, 21.0),
                    (121.0, 2.0),
                ),
            },
            121.0,
        )

        # tax       price_incl      incl_base_amount
        # -----------------------------------------------
        # tax1      T               T
        # tax2      T               T
        # tax3
        tax1.include_base_amount = True
        self._check_tax_results(
            tax1 + tax2 + tax3,
            {
                'total_included': 123.0,
                'total_excluded': 99.0,
                'tax_values_list': (
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

    def test_adapt_price_unit_to_another_taxes(self):
        """
        [!] Mirror of the same test in test_account_tax.js.
        PLZ KEEP BOTH METHODS CONSISTENT WITH EACH OTHERS.
        """
        tax_fixed_incl = self.fixed_tax(10, price_include=True)
        tax_fixed_excl = self.fixed_tax(10)
        tax_include_src = self.percent_tax(21, price_include=True)
        tax_include_dst = self.percent_tax(6, price_include=True)
        tax_exclude_src = self.percent_tax(15)
        tax_exclude_dst = self.percent_tax(21)

        product_price_unit = self.env['account.tax']._adapt_price_unit_to_another_taxes(
            121.0,
            tax_include_src._convert_to_dict_for_taxes_computation(),
            tax_include_dst._convert_to_dict_for_taxes_computation(),
        )
        self.assertEqual(product_price_unit, 106.0)

        product_price_unit = self.env['account.tax']._adapt_price_unit_to_another_taxes(
            100.0,
            tax_exclude_src._convert_to_dict_for_taxes_computation(),
            tax_include_dst._convert_to_dict_for_taxes_computation(),
        )
        self.assertEqual(product_price_unit, 100.0)

        product_price_unit = self.env['account.tax']._adapt_price_unit_to_another_taxes(
            121.0,
            tax_include_src._convert_to_dict_for_taxes_computation(),
            tax_exclude_dst._convert_to_dict_for_taxes_computation(),
        )
        self.assertEqual(product_price_unit, 100.0)

        product_price_unit = self.env['account.tax']._adapt_price_unit_to_another_taxes(
            100.0,
            tax_exclude_src._convert_to_dict_for_taxes_computation(),
            tax_exclude_dst._convert_to_dict_for_taxes_computation(),
        )
        self.assertEqual(product_price_unit, 100.0)

        product_price_unit = self.env['account.tax']._adapt_price_unit_to_another_taxes(
            100.0,
            (tax_fixed_incl + tax_exclude_src)._convert_to_dict_for_taxes_computation(),
            tax_include_dst._convert_to_dict_for_taxes_computation(),
        )
        self.assertEqual(product_price_unit, 100.0)

        product_price_unit = self.env['account.tax']._adapt_price_unit_to_another_taxes(
            100.0,
            (tax_fixed_excl + tax_include_src)._convert_to_dict_for_taxes_computation(),
            tax_exclude_dst._convert_to_dict_for_taxes_computation(),
        )
        self.assertEqual(product_price_unit, 100.0)
