# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrVersion(models.Model):
    _inherit = 'hr.version'

    def _group_hr_expense_user_domain(self):
        # any internal user can approve: the approver group is granted on assignment
        # (see hr.employee._grant_approver_groups), making a light user a regular one
        return "[('share', '=', False), ('company_ids', 'in', company_id)]"

    expense_manager_id = fields.Many2one(
        comodel_name='res.users',
        string='Expense Approver',
        compute='_compute_expense_manager', store=True, readonly=False, index='btree_not_null',
        ui_domain=_group_hr_expense_user_domain,
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
