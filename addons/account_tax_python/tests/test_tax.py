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

    def test_tax_python(self):
        tax = self.python_tax('result = ((price_unit * quantity) - ((price_unit * quantity) / 1.12)) * 0.5')
        self._check_tax_results(
            tax,
            {
                'total_included': 136.96,
                'total_excluded': 130.0,
                'taxes': (
                    (130.0, 6.96),
                ),
            },
            130.0,
        )

        tax.price_include=True
        self._check_tax_results(
            tax,
            {
                'total_included': 130.0,
                'total_excluded': 123.04,
                'taxes': (
                    (123.04, 6.96),
                ),
            },
            130.0,
        )
