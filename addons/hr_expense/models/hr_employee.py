# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class Employee(models.Model):
    _inherit = 'hr.employee'

    def _group_hr_expense_user_domain(self):
        # We return the domain only if the group exists for the following reason:
        # When a group is created (at module installation), the `res.users` form view is
        # automatically modified to add application accesses. When modifying the view, it
        # reads the related field `expense_manager_id` of `res.users` and retrieve its domain.
        # This is a problem because the `group_hr_expense_user` record has already been created but
        # not its associated `ir.model.data` which makes `self.env.ref(...)` fail.
        group = self.env.ref('hr_expense.group_hr_expense_team_approver', raise_if_not_found=False)
        return [('groups_id', 'in', group.ids)] if group else []

    expense_manager_id = fields.Many2one(
        comodel_name='res.users',
        string='Expense',
        compute='_compute_expense_manager', store=True, readonly=False,
        domain=_group_hr_expense_user_domain,
        help='Select the user responsible for approving "Expenses" of this employee.\n'
             'If empty, the approval is done by an Administrator or Approver (determined in settings/users).',
    )

    filter_for_expense = fields.Boolean(store=False, search='_search_filter_for_expense')

    @api.depends('parent_id')
    def _compute_expense_manager(self):
        for employee in self:
            previous_manager = employee._origin.parent_id.user_id
            manager = employee.parent_id.user_id
            if manager and manager.has_group('hr_expense.group_hr_expense_user') \
                    and (employee.expense_manager_id == previous_manager or not employee.expense_manager_id):
                employee.expense_manager_id = manager
            elif not employee.expense_manager_id:
                employee.expense_manager_id = False

    def _get_user_m2o_to_empty_on_archived_employees(self):
        return super()._get_user_m2o_to_empty_on_archived_employees() + ['expense_manager_id']

    def _search_filter_for_expense(self, operator, value):
        assert operator == '='
        assert value

        res = [('id', '=', 0)]  # Nothing accepted by domain, by default
        if self.user_has_groups('hr_expense.group_hr_expense_user') or self.user_has_groups('account.group_account_user'):
            res = ['|', ('company_id', '=', False), ('company_id', 'child_of', self.env.company.root_id.id)]  # Then, domain accepts everything
        elif self.user_has_groups('hr_expense.group_hr_expense_team_approver') and self.env.user.employee_ids:
            user = self.env.user
            employee = self.env.user.employee_id
            res = [
                '|', '|', '|',
                ('department_id.manager_id', '=', employee.id),
                ('parent_id', '=', employee.id),
                ('id', '=', employee.id),
                ('expense_manager_id', '=', user.id),
                '|', ('company_id', '=', False), ('company_id', '=', employee.company_id.id),
            ]
        elif self.env.user.employee_id:
            employee = self.env.user.employee_id
            res = [('id', '=', employee.id), '|', ('company_id', '=', False), ('company_id', '=', employee.company_id.id)]
        return res


class EmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    expense_manager_id = fields.Many2one('res.users', readonly=True)


class User(models.Model):
    _inherit = ['res.users']

    expense_manager_id = fields.Many2one(related='employee_id.expense_manager_id', readonly=False)

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['expense_manager_id']
