# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import fields, models


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    def _compute_expense_to_approve(self):
        expense_data = self.env['hr.expense'].read_group([('department_id', 'in', self.ids), ('state', '=', 'submit')], ['department_id'], ['department_id'])
        result = dict((data['department_id'][0], data['department_id_count']) for data in expense_data)
        for department in self:
            department.expense_to_approve_count = result.get(department.id, 0)

    expense_to_approve_count = fields.Integer(compute='_compute_expense_to_approve', string='Expenses to Approve')
