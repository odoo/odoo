# -*- coding: utf-8 -*-
from odoo.addons.account.tests.test_tax import TestTaxCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestTaxPython(TestTaxCommon):

    @classmethod
    def setUpClass(cls):
        super(TestTaxPython, cls).setUpClass()
        cls.python_tax = cls.env['account.tax'].create({
            'name': 'Python TAx',
            'amount_type': 'code',
            'amount': 0.0,
            'python_compute': 'result = ((price_unit * quantity) - ((price_unit * quantity) / 1.12)) * 0.5',
            'sequence': 1,
        })

    def test_tax_python_basic(self):
        res = self.python_tax.compute_all(130.0)
        self._check_compute_all_results(
            136.96,  # 'total_included'
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

        python_tax_2 = self.python_tax.copy()
        res = (self.python_tax + python_tax_2).compute_all(130.0)
        self._check_compute_all_results(
            130,  # 'total_included'
            116.08,  # 'total_excluded'
            [
                # base , amount     | seq | amount | incl | incl_base
                # ---------------------------------------------------
                (116.08, 6.96),   # |  1  |    6%  |   t  |
                (116.08, 6.96),   # |  1  |    6%  |   t  |
                # ---------------------------------------------------
            ],
            res
        )

    def test_price_included_multi_taxes_with_python_tax_1(self):
        """ Test multiple price-included taxes with a Python code tax applied last
        to ensure the total matches the price, and cached tax didn't bypassing the rounding correction.
        """
        tax_12_percent = self.env['account.tax'].create({
            'name': "Tax 12%",
            'amount_type': 'percent',
            'amount': 12.0,
            'price_include': True,
            'include_base_amount': False,
            'sequence': 1,  # Ensure this tax is applied first
        })

        tax_python = self.env['account.tax'].create({
            'name': "Python Tax",
            'amount_type': 'code',
            'python_compute': "result = 22.503",
            'price_include': True,
            'include_base_amount': False,
            'sequence': 2,  # Ensure this tax is applied after the 12% tax
        })

        taxes = tax_12_percent + tax_python
        res = taxes.compute_all(516.00)

        self._check_compute_all_results(
            516.0,  # total_included
            440.63,  # total_excluded
            [
                (440.63, 52.87),
                (440.63, 22.5),
            ],
            res
        )

    def test_price_included_multi_taxes_with_python_tax_2(self):
        tax_python = self.env['account.tax'].create({
            'name': "Python Tax",
            'amount_type': 'code',
            'python_compute': "result = 5",
            'price_include': True,
            'include_base_amount': True,
            'sequence': 1,  # Ensure this tax is applied first
        })

        tax_12_percent = self.env['account.tax'].create({
            'name': "Tax 12%",
            'amount_type': 'percent',
            'amount': 15.0,
            'price_include': True,
            'include_base_amount': False,
            'sequence': 2,  # Ensure this tax is applied after the 12% tax
        })

        taxes = tax_python + tax_12_percent
        res = taxes.compute_all(100.00)

        self._check_compute_all_results(
            total_included=100.0,
            total_excluded=81.96,
            taxes=[
                (81.96, 5.0),
                (86.96, 13.04),
            ],
            res=res,
        )
