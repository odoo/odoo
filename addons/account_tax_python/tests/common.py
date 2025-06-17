from odoo.addons.account.tests.test_tax import TestTaxCommon


class TestTaxCommonAccountTaxPython(TestTaxCommon):

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
        return self.assert_taxes_computation(tax, price_unit, expected_values, product=product)
