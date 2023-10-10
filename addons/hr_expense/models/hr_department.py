# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.osv import expression
import ast


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    def _compute_expense_sheets_to_approve(self):
        expense_sheet_data = self.env['hr.expense.sheet']._read_group([('department_id', 'in', self.ids), ('state', '=', 'submit')], ['department_id'], ['__count'])
        result = {department.id: count for department, count in expense_sheet_data}
        for department in self:
            department.expense_sheets_to_approve_count = result.get(department.id, 0)

    expense_sheets_to_approve_count = fields.Integer(compute='_compute_expense_sheets_to_approve', string='Expenses Reports to Approve')

    def action_hr_expense_sheet_department(self):
        action = self.env["ir.actions.actions"]._for_xml_id("hr_expense.action_hr_expense_sheet_department_to_approve")
        action['domain'] = expression.AND([ast.literal_eval(action['domain']), [('department_id', '=', self.id), ('state', '=', 'submit')]])
        return action
