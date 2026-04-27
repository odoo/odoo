from odoo import models, _
from odoo.exceptions import UserError


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    def _compute_rule(self, localdict):
        result = super()._compute_rule(localdict)
        if self.struct_id.country_id.code != 'MX' or self.code != 'INT_DAY_WAGE_BASE':
            return result
        int_day_wage_base_rule = self.env.ref('l10n_mx_hr_payroll.l10n_mx_employees_salary_integrated_daily_wage')
        mx_pay_struct = self.env.ref('l10n_mx_hr_payroll.hr_payroll_structure_mx_employee_salary')
        if self == int_day_wage_base_rule and self.struct_id == mx_pay_struct:
            int_day_wage = result[0]
            self._check_int_day_wage_requirements(localdict, int_day_wage)
        return result

    def _check_int_day_wage_requirements(self, localdict, int_day_wage):
        """
        checks if the salary < mdw before computing the rule
        """
        mdw = localdict['payslip']._rule_parameter('l10n_mx_daily_min_wage')
        if int_day_wage < mdw:
            raise UserError(
                _('The integrated daily wage cannot be less than the minimum daily wage.'))
