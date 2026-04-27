# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from datetime import date


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    def _l10n_pk_get_tax(self, income):
        self.ensure_one()
        result = 0
        tax_brackets = list(iter(self._rule_parameter('l10n_pk_tax_brackets')))
        for i, (low, high, rate, fix) in enumerate(tax_brackets):
            if income > low:
                if income <= high:
                    if i == len(tax_brackets) - 1 and self.date_from > date(2025, 6, 30):
                        base_rate = tax_brackets[i - 1][2]
                        result += base_rate * (income - low)
                        surcharge_amount = rate * result
                        result += surcharge_amount
                        break
                    result += rate * (income - low)
                    break
                else:
                    result = fix
        return result
