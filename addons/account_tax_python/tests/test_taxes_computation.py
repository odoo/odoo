from odoo.addons.account.tests.test_tax import TestTaxCommon
from odoo.tests import tagged
from odoo.exceptions import ValidationError


@tagged('post_install', '-at_install')
class TestTaxesComputation(TestTaxCommon):

    def _jsonify_tax(self, tax):
        values = super()._jsonify_tax(tax)
        values['formula_decoded_info'] = tax.formula_decoded_info
        return values

    def assert_python_taxes_computation(
        self,
        formula,
        price_unit,
        expected_values,
        product_values=None,
        product_uom_values=None,
        price_include_override='tax_excluded',
    ):
        tax = self.python_tax(formula, price_include_override=price_include_override)
        if product_values:
            product = self.env['product.product'].create({
                'name': "assert_python_taxes_computation",
                **product_values,
            })
        else:
            product = None
        if product_uom_values:
            uom = self.env['uom.uom'].create({
                'name': "assert_python_taxes_computation",
                'category_id': self.env.ref('uom.product_uom_categ_unit').id,
                'uom_type': 'bigger',
                **product_uom_values,
            })
        else:
            uom = None
        return self.assert_taxes_computation(tax, price_unit, expected_values, product=product, product_uom=uom)

    def test_formula(self):
        self.assert_python_taxes_computation(
            "max(quantity * price_unit * 0.21, quantity * 4.17)",
            130.0,
            {
                'total_included': 157.3,
                'total_excluded': 130.0,
                'taxes_data': (
                    (130.0, 27.3),
                ),
            },
        )
        self.assert_python_taxes_computation(
            "max(quantity * price_unit * 0.21, quantity * 4.17)",
            130.0,
            {
                'total_included': 130.0,
                'total_excluded': 102.7,
                'taxes_data': (
                    (102.7, 27.3),
                ),
            },
            price_include_override='tax_included',
        )
        self.assert_python_taxes_computation(
            "product.volume * quantity * 0.35",
            100.0,
            {
                'total_included': 135.0,
                'total_excluded': 100.0,
                'taxes_data': (
                    (100.0, 35.0),
                ),
            },
            product_values={'volume': 100.0},
        )
        self.assert_python_taxes_computation(
            "product.volume > 100 and 10 or 5",
            100.0,
            {
                'total_included': 110.0,
                'total_excluded': 100.0,
                'taxes_data': (
                    (100.0, 10.0),
                ),
            },
            product_values={'volume': 105.0},
        )
        self.assert_python_taxes_computation(
            "product.volume > 100 and 10 or 5",
            100.0,
            {
                'total_included': 105.0,
                'total_excluded': 100.0,
                'taxes_data': (
                    (100.0, 5.0),
                ),
            },
            product_values={'volume': 50.0},
        )
        self.assert_python_taxes_computation(
            "product.volume > 100 and 5 or None",
            100.0,
            {
                'total_included': 100.0,
                'total_excluded': 100.0,
                'taxes_data': [],
            },
            product_values={'volume': 50.0},
        )
        self.assert_python_taxes_computation(
            "(product.volume or 5.0) and 0.0 or 10.0",
            100.0,
            {
                'total_included': 110.0,
                'total_excluded': 100.0,
                'taxes_data': (
                    (100.0, 10.0),
                ),
            },
            product_values={'volume': 0.0},
        )
        self.assert_python_taxes_computation(
            "uom.factor",
            100.0,
            {
                'total_included': 142.0,
                'total_excluded': 100.0,
                'taxes_data': (
                    (100.0, 42.0),
                ),
            },
            product_uom_values={'factor': 42.0},
        )
        self._run_js_tests()

    def test_invalid_formula(self):
        # You have no access to relational field.
        with self.assertRaises(ValidationError):
            self.python_tax(formula='product.product_tmpl_id')
        # You don't have access to any record.
        with self.assertRaises(ValidationError):
            self.python_tax(formula='product.sudo()')
        # You are restricted to min max but that's it: no python collection.
        with self.assertRaises(ValidationError):
            self.python_tax(formula='tuple(1, 2, 3)')
        with self.assertRaises(ValidationError):
            self.python_tax(formula='set(1, 2, 3)')
        with self.assertRaises(ValidationError):
            self.python_tax(formula='[1, 2, 3]')
        # No access to builtins that are not part of the whitelist.
        with self.assertRaises(ValidationError):
            self.python_tax(formula='range(1, 10)')
