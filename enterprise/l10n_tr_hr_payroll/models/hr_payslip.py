# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class HRPayslip(models.Model):
    _inherit = 'hr.payslip'

    def _l10n_tr_get_tax(self, taxable_amount):
        self.ensure_one()
        total_tax = 0
        rates = iter(self._rule_parameter('l10_tr_tax_rates'))
        lower, upper, rate = next(rates)
        while lower < taxable_amount:
            total_tax += min((taxable_amount - lower, float(upper) - lower)) * rate
            lower, upper, rate = next(rates)
        return total_tax

    def _get_data_files_to_update(self):
        # Note: file order should be maintained
        return super()._get_data_files_to_update() + [(
            'l10n_tr_hr_payroll', [
                'data/hr_rule_parameter_data.xml',
            ])]
