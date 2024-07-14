# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class HrEmployee(models.Model):
    _inherit = 'hr.payslip'

    def _get_data_files_to_update(self):
        # Note: file order should be maintained
        return super()._get_data_files_to_update() + [(
            'l10n_lt_hr_payroll', [
                'data/hr_salary_rule_category_data.xml',
                'data/hr_payroll_structure_type_data.xml',
                'data/hr_payroll_structure_data.xml',
                'data/hr_rule_parameters_data.xml',
                'data/hr_salary_rule_data.xml',
            ])]

    def _get_l10n_lt_taxable_amount(self, localdict, sick=False):
        self.ensure_one()
        categories = localdict['categories']
        taxable_amount = categories['GROSS']
        if not self.employee_id.is_non_resident:
            low = self._rule_parameter('l10n_lt_tax_exempt_low')
            high = self._rule_parameter('l10n_lt_tax_exempt_high')
            basic = self._rule_parameter('l10n_lt_tax_exempt_basic')
            rate = self._rule_parameter('l10n_lt_tax_exempt_rate')
            if taxable_amount <= low:
                taxable_amount -= basic
            elif taxable_amount <= high:
                taxable_amount -= basic - rate * (taxable_amount - low)

            if self.employee_id.l10n_lt_working_capacity == "0_25":
                taxable_amount -= self._rule_parameter('l10n_lt_tax_exempt_0_25')
            elif self.employee_id.l10n_lt_working_capacity == "30_55":
                taxable_amount -= self._rule_parameter('l10n_lt_tax_exempt_30_55')
        sick_amount = sum(self.worked_days_line_ids.filtered(lambda wd: wd.code == 'LEAVE110').mapped('amount'))
        if sick:
            return min(taxable_amount, sick_amount)
        return max(taxable_amount - sick_amount, 0)
