# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class HRPayslip(models.Model):
    _inherit = 'hr.payslip'

    def _get_eg_tax(self, taxable_amount):
        # See: https://www.pwc.com/m1/en/services/tax/me-tax-legal-news/2023/egypt-law-no-30-of-2023-issued-by-the-egyptian-government.html
        self.ensure_one()

        def find_rates(x, rates):
            for low, high, bracket_rates in rates:
                if low <= x and (x <= high or self.currency_id.is_zero(high)):
                    return bracket_rates

        rates = self._rule_parameter('l10_eg_tax_rates')
        bracket_rates = find_rates(taxable_amount, rates)
        if not bracket_rates:
            return 0
        total_tax = 0
        for frm, to, rate in bracket_rates:
            if self.currency_id.is_zero(to):  # no upper limit
                total_tax += (taxable_amount - frm) * rate
            else:
                total_tax += min((taxable_amount - frm, to - frm)) * rate
            if taxable_amount <= to:
                break

        return total_tax

    def _get_data_files_to_update(self):
        # Note: file order should be maintained
        return super()._get_data_files_to_update() + [(
            'l10n_eg_hr_payroll', [
                'data/hr_rule_parameter_data.xml',
            ])]
