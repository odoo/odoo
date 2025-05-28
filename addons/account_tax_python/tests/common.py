from odoo.addons.account.tests.test_tax import TestTaxCommon


class TestTaxCommonAccountTaxPython(TestTaxCommon):

    def python_tax(self, formula, **kwargs):
        self.number += 1
        vals = {
            **kwargs,
            'name': f"code_({self.number})",
            'amount_type': 'code',
            'amount': 0.0,
            'formula': formula,
        }
        if 'price_include' in vals:
            price_include = vals.pop('price_include')
            if self.env.company.account_price_include != price_include:
                vals['price_include_override'] = price_include
            else:
                vals['price_include_override'] = False
        return self.env['account.tax'].create(vals)

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
        price_include='tax_excluded',
    ):
        tax = self.python_tax(formula, price_include=price_include)
        if product_values:
            product = self.env['product.product'].create({
                'name': "assert_python_taxes_computation",
                **product_values,
            })
        else:
            product = None
        return self.assert_taxes_computation(tax, price_unit, expected_values, product=product)
