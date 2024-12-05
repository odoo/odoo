# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    expense_to_approve_count = fields.Integer(compute='_compute_expenses_to_approve', string='Expenses to Approve')

    def _compute_expenses_to_approve(self):
        expense_data = self.env['hr.expense']._read_group([('department_id', 'in', self.ids), ('state', '=', 'submitted')], ['department_id'], ['__count'])
        result = {department.id: count for department, count in expense_data}
        for department in self:
            department.expense_to_approve_count = result.get(department.id, 0)

