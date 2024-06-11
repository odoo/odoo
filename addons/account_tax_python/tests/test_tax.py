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
        tax1 = self.python_tax("result = max(quantity * price_unit * 0.21, quantity * 4.17)")
        self._check_tax_results(
            tax1,
            {
                'total_included': 157.3,
                'total_excluded': 130.0,
                'tax_values_list': (
                    (130.0, 27.3),
                ),
            },
            130.0,
        )

        tax1.price_include = True
        self._check_tax_results(
            tax1,
            {
                'total_included': 130.0,
                'total_excluded': 102.7,
                'tax_values_list': (
                    (102.7, 27.3),
                ),
            },
            130.0,
        )

        tax1.python_applicable = "False"
        self._check_tax_results(
            tax1,
            {
                'total_included': 130.0,
                'total_excluded': 130.0,
                'tax_values_list': [],
            },
            130.0,
        )

        product1 = self.env['product.product'].create({
            'name': "product1",
            'volume': 200.0,
        })
        tax2 = self.python_tax("result = product['volume'] > 100 and 10 or 5")
        self._check_tax_results(
            tax2,
            {
                'total_included': 110.0,
                'total_excluded': 100.0,
                'tax_values_list': (
                    (100.0, 10.0),
                ),
            },
            100.0,
            {'product': product1},
        )

        product2 = self.env['product.product'].create({
            'name': "product1",
            'volume': 50.0,
        })
        self._check_tax_results(
            tax2,
            {
                'total_included': 105.0,
                'total_excluded': 100.0,
                'tax_values_list': (
                    (100.0, 5.0),
                ),
            },
            100.0,
            {'product': product2},
        )
