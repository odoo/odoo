# -*- coding: utf-8 -*-
from odoo.addons.account.tests.test_tax import TestTax
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestTaxPython(TestTax):

    def setUp(self):
        super(TestTaxPython, self).setUp()

        self.python_tax = self.tax_model.create({
            'name': 'Python TAx',
            'amount_type': 'code',
            'amount': 0.0,
            'python_compute': 'result = ((price_unit * quantity) - ((price_unit * quantity) / 1.12)) * 0.5',
            'sequence': 1,
        })

    def test_tax_python_basic(self):
        res = self.python_tax.compute_all(130.0)
        self._check_compute_all_results(
            136.96, # 'total_included'
            130.0,  # 'total_excluded'
            [
                # base , amount    | seq | amount | incl | incl_base
                # --------------------------------------------------
                (130.0, 6.96),   # |  1  |    6%  |   t  |
                # --------------------------------------------------
            ],
            res
        )

    def test_tax_python_price_include(self):
        self.python_tax.price_include = True
        res = self.python_tax.compute_all(130.0)
        self._check_compute_all_results(
            130,    # 'total_included'
            123.04, # 'total_excluded'
            [
                # base , amount     | seq | amount | incl | incl_base
                # ---------------------------------------------------
                (123.04, 6.96),   # |  1  |    6%  |   t  |
                # ---------------------------------------------------
            ],
            res
        )

        res = (self.python_tax + self.python_tax).compute_all(130.0)
        self._check_compute_all_results(
            130,    # 'total_included'
            116.07, # 'total_excluded'
            [
                # base , amount     | seq | amount | incl | incl_base
                # ---------------------------------------------------
                (116.07, 6.96),   # |  1  |    6%  |   t  |
                (116.07, 6.97),   # |  1  |    6%  |   t  |
                # ---------------------------------------------------
            ],
            res
        )
