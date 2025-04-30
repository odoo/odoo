# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrManagerDepartmentReport(models.AbstractModel):
    _name = 'hr.manager.department.report'
    _description = 'Hr Manager Department Report'
    _auto = False

    employee_id = fields.Many2one('hr.employee', string="Employee", readonly=True)
    has_department_manager_access = fields.Boolean(search="_search_has_department_manager_access",
        compute="_compute_has_department_manager_access")

    def _search_has_department_manager_access(self, operator, value):
        if operator != 'in':
            return NotImplemented
        department_ids = self.env['hr.department']._search([('manager_id', 'in', self.env.user.employee_ids.ids)])
        return [
            '|',
                ('employee_id.user_id', '=', self.env.user.id),
                ('employee_id.department_id', 'child_of', tuple(department_ids)),
        ]

    def _compute_has_department_manager_access(self):
        department_ids = self.env['hr.department']._search([('manager_id', 'in', self.env.user.employee_ids.ids)])
        employees = self.env['hr.employee'].search([
            '|',
                ('user_id', '=', self.env.user.id),
                ('department_id', 'child_of', tuple(department_ids)),
            ])
        for report in self:
            report.has_department_manager_access = report.employee_id in employees
