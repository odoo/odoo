# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class HrEmployee(models.Model):
    _inherit = 'hr.payslip'

    def _get_data_files_to_update(self):
        # Note: file order should be maintained
        return super()._get_data_files_to_update() + [(
            'l10n_mx_hr_payroll', [
                'data/hr_salary_rule_category_data.xml',
                'data/hr_payroll_structure_type_data.xml',
                'data/hr_payroll_structure_data.xml',
                'data/hr_rule_parameters_data.xml',
                'data/salary_rules/hr_salary_rule_christmas_bonus_data.xml',
                'data/salary_rules/hr_salary_rule_regular_pay_data.xml',
            ])]

    def _get_paid_amount(self):
        self.ensure_one()
        mx_payslip = self.struct_id.country_id.code == "MX"
        if not mx_payslip:
            return super()._get_paid_amount()
        if self.struct_id.code == "MXMONTHLY":
            coefficients = {
                'daily': 1,
                'weekly': 7,
                '10_days': 10,
                'bi_weekly': 15,
                'monthly': 30,
                'yearly': 365,
            }
            return self._get_contract_wage() / 30 * coefficients[self.contract_id.l10n_mx_schedule_pay or 'monthly']
        if self.struct_id.code == "MXCHRISTMAS":
            return self._get_contract_wage() / 30 * self.contract_id.l10n_mx_christmas_bonus
