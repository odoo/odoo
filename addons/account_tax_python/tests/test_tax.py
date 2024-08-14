# -*- coding: utf-8 -*-
from odoo.addons.account.tests.test_tax import TestTaxCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestTaxPython(TestTaxCommon):

    def python_tax(self, python_compute, **kwargs):
        self.number += 1
        return self.env['account.tax'].create({
            **kwargs,
            'name': f"code_({self.number})",
            'amount_type': 'code',
            'amount': 0.0,
            'python_compute': python_compute,
        })

    def test_python_taxes_for_l10n_in(self):
        tests = []
        formula = "result = max(quantity * price_unit * 0.21, quantity * 4.17)"
        tax1 = self.python_tax(formula)
        tests.append(self._prepare_taxes_computation_test(
            tax1,
            130.0,
            {
                'total_included': 157.3,
                'total_excluded': 130.0,
                'taxes_data': (
                    (130.0, 27.3),
                ),
            },
        ))

        tax1.price_include = True
        tests.append(self._prepare_taxes_computation_test(
            tax1,
            130.0,
            {
                'total_included': 130.0,
                'total_excluded': 102.7,
                'taxes_data': (
                    (102.7, 27.3),
                ),
            },
        ))

        tax2 = self.python_tax(formula, python_applicable="False")
        tests.append(self._prepare_taxes_computation_test(
            tax2,
            130.0,
            {
                'total_included': 130.0,
                'total_excluded': 130.0,
                'taxes_data': [],
            },
        ))

        product1 = self.env['product.product'].create({
            'name': "product1",
            'volume': 200.0,
        })
        tax3 = self.python_tax("result = product['volume'] > 100 and 10 or 5")
        tests.append(self._prepare_taxes_computation_test(
            tax3,
            100.0,
            {
                'total_included': 110.0,
                'total_excluded': 100.0,
                'taxes_data': (
                    (100.0, 10.0),
                ),
            },
            {'product': product1},
        ))

        product2 = self.env['product.product'].create({
            'name': "product1",
            'volume': 50.0,
        })
        tests.append(self._prepare_taxes_computation_test(
            tax3,
            100.0,
            {
                'total_included': 105.0,
                'total_excluded': 100.0,
                'taxes_data': (
                    (100.0, 5.0),
                ),
            },
            {'product': product2},
        ))
        self._assert_tests(tests, mode='py')

    def test_different_syntaxes(self):
        # Test the different syntaxes that are allowed: "product['standard_price']" and "product.standard_price"
        tests = []
        product = self.env['product.product'].create({
            'name': "product1",
            'standard_price': 120,
        })
        tax1 = self.python_tax("result = product.standard_price * 0.5")
        tests.append(self._prepare_taxes_computation_test(
            tax1,
            130.0,
            {
                'total_included': 190.0,
                'total_excluded': 130.0,
                'taxes_data': (
                    (130.0, 60.0),
                ),
            },
            {'product': product},
        ))
        tax2 = self.python_tax("result = product['standard_price'] * 0.5")
        tests.append(self._prepare_taxes_computation_test(
            tax2,
            130.0,
            {
                'total_included': 190.0,
                'total_excluded': 130.0,
                'taxes_data': (
                    (130.0, 60.0),
                ),
            },
            {'product': product},
        ))
        self._assert_tests(tests, mode='py')
