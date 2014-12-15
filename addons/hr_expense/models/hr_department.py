# -*- coding: utf-8 -*-

from openerp import fields, models

class HrDepartment(models.Model):
    _inherit = 'hr.department'

    expense_to_approve_ids = fields.One2many('hr.expense.sheet', 'department_id',
         domain=[('state', '=', 'confirm')], string='Expenses to Approve')
