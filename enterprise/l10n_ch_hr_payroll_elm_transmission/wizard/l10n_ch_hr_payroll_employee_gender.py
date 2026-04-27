# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from odoo import fields, models


class L10nChHrPayrollEmployeeGenderWizard(models.TransientModel):
    _name = 'l10n_ch.hr.payroll.employee.gender.wizard'
    _description = 'Change Employee Gender'

    def _default_line_ids(self):
        res = []
        if 'employee_ids' in self.env.context:
            res.extend([(0, 0, {'employee_id': employee}) for employee in self.env.context.get('employee_ids')])
        return res

    line_ids = fields.One2many('l10n_ch.hr.payroll.employee.gender.wizard.line', 'wizard_id', string='Lines', default=_default_line_ids)
    slip_ids = fields.Many2many('hr.payslip', store=False)

    def action_validate(self):
        for wizard in self:
            gender_to_employee = defaultdict(lambda: self.env['hr.employee'])
            for line in wizard.line_ids:
                gender_to_employee[line.gender] |= line.employee_id
            for gender, employees in gender_to_employee.items():
                employees.write({'gender': gender})
        return self.slip_ids.compute_sheet()


class L10nChHrPayrollEmployeeGenderWizardLine(models.TransientModel):
    _name = 'l10n_ch.hr.payroll.employee.gender.wizard.line'
    _description = 'Change Employee Gender Line'

    wizard_id = fields.Many2one('l10n_ch.hr.payroll.employee.gender.wizard')
    employee_id = fields.Many2one('hr.employee')
    gender = fields.Selection([
        ('female', 'Female'),
        ('male', 'Male')], string="Gender", required=True)
