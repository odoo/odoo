# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class Employee(models.Model):
    _inherit = 'hr.employee'

    expense_manager_id = fields.Many2one(
        'res.users', string='Expense Responsible',
        domain=lambda self: [('groups_id', 'in', self.env.ref('hr_expense.group_hr_expense_user').id)],
        help="User responsible of expense approval. Should be Expense Manager.")
