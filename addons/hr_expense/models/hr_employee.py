# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api

class Employee(models.Model):
    _inherit = 'hr.employee'

    expense_manager_id = fields.Many2one(
        'res.users', string='Expense Responsible',
        domain=lambda self: [('groups_id', 'in', self.env.ref('hr_expense.group_hr_expense_user').id)],
        help="User responsible of expense approval. Should be Expense Manager.")

    @api.onchange('parent_id')
    def _onchange_parent_id(self):
        super(Employee, self)._onchange_parent_id()
        previous_manager = self._origin.parent_id.user_id
        manager = self.parent_id.user_id
        if manager and manager.has_group('hr_expense.group_hr_expense_user') and (self.expense_manager_id == previous_manager or not self.expense_manager_id):
            self.expense_manager_id = manager
