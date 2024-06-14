# -*- coding: utf-8 -*-
from odoo import Command
from odoo.addons.account.tests.common import TestTaxCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestTax(TestTaxCommon):

    def _check_compute_all_results(self, taxes, expected_values, price_unit, **kwargs):
        results = taxes.compute_all(price_unit, **kwargs)
        self.assertAlmostEqual(results['total_included'], expected_values['total_included'])
        self.assertAlmostEqual(results['total_excluded'], expected_values['total_excluded'])
        self.assertEqual(len(results['taxes']), len(expected_values['taxes']))
        for values, tax_expected_values in zip(results['taxes'], expected_values['taxes']):
            self.assertEqual(round(values['base'], 6), tax_expected_values[0])
            self.assertEqual(round(values['amount'], 6), tax_expected_values[1])

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

    def test_forced_price_exclude_context_key(self):
        """ Test the 'force_price_include' context key that force all taxes to act as price excluded taxes. """
        taxes = (self.percent_tax(10.0, price_include=True) + self.percent_tax(10.0, price_include=True))\
            .with_context({'force_price_include': False})
        self._check_compute_all_results(
            taxes,
            {
                'total_included': 120.0,
                'total_excluded': 100.0,
                'taxes': (
                    (100.0, 10.0),
                    (100.0, 10.0),
                ),
            },
            100.0,
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
