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
        taxes = (self.percent_tax(10.0, price_include_override='tax_included') + self.percent_tax(10.0, price_include_override='tax_included'))\
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

        self.assertEqual(
            self.env["account.tax"].search([("name", "ilike", "tix")]),
            list_ten_fixed_tax,
        )
        self.assertEqual(
            self.env["account.tax"].search([("name", "ilike", "\"tix\"")]),
            ten_fixed_tax_tix,
        )
        self.assertEqual(
            self.env["account.tax"].search([("name", "ilike", "Ten \"tix\"")]),
            ten_fixed_tax_tix,
        )

    def test_repartition_line_in(self):
        tax = self.env['account.tax'].create({
            'name': 'tax20',
            'amount_type': 'percent',
            'amount': 20,
            'type_tax_use': 'none',
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
        })
        self.env.company.country_id = self.env.ref('base.in')
        self._check_compute_all_results(
            tax,
            {
                'total_included': 1000,
                'total_excluded': 1000,
                'taxes': (
                    (1000, 200.0),
                    (1000, -200.0),
                ),
            },
            1000.0,
        )
