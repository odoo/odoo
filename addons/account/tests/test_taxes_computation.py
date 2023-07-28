# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestTaxesComputationCommon(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.number = 0

    def _check_tax_results(self, taxes, expected_values, price_unit, quantity=1):
        results = taxes.compute_all(price_unit, quantity=quantity)
        self.assertAlmostEqual(results['total_included'], expected_values['total_included'])
        self.assertAlmostEqual(results['total_excluded'], expected_values['total_excluded'])
        self.assertEqual(len(results['taxes']), len(expected_values['taxes']))
        for values, expected_values in zip(results['taxes'], expected_values['taxes']):
            self.assertAlmostEqual(values['base'], expected_values[0])
            self.assertAlmostEqual(values['amount'], expected_values[1])

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
                    (45.6, 2.4),
                    (46.56, 1.44),
                    (47.69, 0.31),
                    (43.68, 4.32),
                    (40.8, 7.2),
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
                    (100.0, 2.0),
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
