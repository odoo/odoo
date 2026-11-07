# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrVersion(models.Model):
    _inherit = 'hr.version'

    def _group_hr_expense_user_domain(self):
        # We return the domain only if the group exists for the following reason:
        # When a group is created (at module installation), the `res.users` form view is
        # automatically modified to add application accesses. When modifying the view, it
        # reads the related field `expense_manager_id` of `res.users` and retrieve its domain.
        # This is a problem because the `group_hr_expense_team_approver` record has already been created but
        # not its associated `ir.model.data` which makes `self.env.ref(...)` fail.
        group = self.env.ref('hr_expense.group_hr_expense_team_approver', raise_if_not_found=False)
        return [
            '|', ('id', 'parent_of', self.ids), ('all_group_ids', 'in', group.ids)
        ] if group else [('id', 'parent_of', self.ids)]

    expense_manager_id = fields.Many2one(
        comodel_name='res.users',
        string='Expense Approver',
        compute='_compute_expense_manager', store=True, readonly=False,
        domain=_group_hr_expense_user_domain,
        help='Select the user responsible for approving "Expenses" of this employee.\n'
             'If empty, the approval is done by the department manager (if they are an expense approver), '
             "otherwise by the employee's manager. If there is none, the expense is auto-validated.",
    )

    @api.depends('parent_id')
    def _compute_expense_manager(self):
        for version in self:
            previous_manager = version._origin.parent_id.user_id
            new_manager = version.parent_id.user_id
            if new_manager and version.expense_manager_id and version.expense_manager_id == previous_manager:
                version.expense_manager_id = new_manager
            elif not version.expense_manager_id:
                version.expense_manager_id = False
