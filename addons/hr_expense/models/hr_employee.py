# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class Employee(models.Model):
    _inherit = 'hr.employee'

    def _group_hr_expense_user_domain(self):
        # We return the domain only if the group exists for the following reason:
        # When a group is created (at module installation), the `res.users` form view is
        # automatically modifiedto add application accesses. When modifiying the view, it
        # reads the related field `expense_manager_id` of `res.users` and retrieve its domain.
        # This is a problem because the `group_hr_expense_user` record has already been created but
        # not its associated `ir.model.data` which makes `self.env.ref(...)` fail.
        group = self.env.ref('hr_expense.group_hr_expense_team_approver', raise_if_not_found=False)
        return [('groups_id', 'in', group.ids)] if group else []

    expense_manager_id = fields.Many2one(
        'res.users', string='Expense',
        domain=_group_hr_expense_user_domain,
        help="User responsible of expense approval. Should be Expense approver.")

    @api.onchange('parent_id')
    def _onchange_parent_id(self):
        super(Employee, self)._onchange_parent_id()
        previous_manager = self._origin.parent_id.user_id
        manager = self.parent_id.user_id
        if manager and manager.has_group('hr_expense.group_hr_expense_user') and (self.expense_manager_id == previous_manager or not self.expense_manager_id):
            self.expense_manager_id = manager


class EmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    expense_manager_id = fields.Many2one('res.users', readonly=True)


class User(models.Model):
    _inherit = ['res.users']

    expense_manager_id = fields.Many2one(related='employee_id.expense_manager_id')

    def __init__(self, pool, cr):
        """ Override of __init__ to add access rights.
            Access rights are disabled by default, but allowed
            on some specific fields defined in self.SELF_{READ/WRITE}ABLE_FIELDS.
        """
        init_res = super(User, self).__init__(pool, cr)
        # duplicate list to avoid modifying the original reference
        type(self).SELF_READABLE_FIELDS = type(self).SELF_READABLE_FIELDS + ['expense_manager_id']
        return init_res
