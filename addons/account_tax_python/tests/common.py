from odoo.addons.account.tests.test_tax import TestTaxCommon


class TestTaxCommonAccountTaxPython(TestTaxCommon):

    _test_user_groups = None  # FIXME list needed groups

    def _jsonify_tax(self, tax):
        values = super()._jsonify_tax(tax)
        values['formula_decoded_info'] = tax.formula_decoded_info
        return values
