# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    def _compute_expense_sheets_to_approve(self):
        result = self.env['hr.expense.sheet']._aggregate([('department_id', 'in', self.ids), ('state', '=', 'submit')], ['*:count'], ['department_id'])
        for department in self:
            department.expense_sheets_to_approve_count = result.get_agg(department, '*:count', 0)

    expense_sheets_to_approve_count = fields.Integer(compute='_compute_expense_sheets_to_approve', string='Expenses Reports to Approve')
