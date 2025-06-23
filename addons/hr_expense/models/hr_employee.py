# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.fields import Domain


class HrEmployeeBase(models.AbstractModel):
    _inherit = 'hr.employee.base'

    filter_for_expense = fields.Boolean(store=False, search='_search_filter_for_expense', groups="hr.group_hr_user")

    def _search_filter_for_expense(self, operator, value):
        if operator != 'in':
            return NotImplemented

        domain = Domain.FALSE  # Nothing accepted by domain, by default
        user = self.env.user
        employee = user.employee_id
        if user.has_groups('hr_expense.group_hr_expense_user'):
            domain = Domain('company_id', '=', False) | Domain('company_id', 'child_of', self.env.company.root_id.id)  # Then, domain accepts everything
        elif user.has_groups('hr_expense.group_hr_expense_team_approver') and user.employee_ids:
            domain = (
                Domain('department_id.manager_id', '=', employee.id)
                | Domain('parent_id', '=', employee.id)
                | Domain('id', '=', employee.id)
                | Domain('expense_manager_id', '=', user.id)
            ) & Domain('company_id', 'in', [False, employee.company_id.id])
        elif user.employee_id:
            domain = Domain('id', '=', employee.id) & Domain('company_id', 'in', [False, employee.company_id.id])
        return domain


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

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
             'If empty, the approval is done by an Administrator or Approver (determined in settings/users).',
    )

    @api.depends('parent_id')
    def _compute_expense_manager(self):
        for employee in self:
            previous_manager = employee._origin.parent_id.user_id
            new_manager = employee.parent_id.user_id
            if new_manager and (employee.expense_manager_id == previous_manager or not employee.expense_manager_id):
                employee.expense_manager_id = new_manager
            elif not employee.expense_manager_id:
                employee.expense_manager_id = False

    def _get_user_m2o_to_empty_on_archived_employees(self):
        return super()._get_user_m2o_to_empty_on_archived_employees() + ['expense_manager_id']


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    expense_manager_id = fields.Many2one('res.users', readonly=True)


class ResUsers(models.Model):
    _inherit = 'res.users'

    expense_manager_id = fields.Many2one(related='employee_id.expense_manager_id', readonly=False)

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['expense_manager_id']
