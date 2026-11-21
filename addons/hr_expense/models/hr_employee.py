# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.fields import Domain


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def _group_hr_expense_user_domain(self):
        # any internal user can approve: the approver group is granted on assignment
        # (see hr.employee._grant_approver_groups), making a light user a regular one
        return "[('share', '=', False), ('company_ids', 'in', company_id)]"

    expense_manager_id = fields.Many2one(
        comodel_name='res.users',
        string='Expense Approver',
        compute='_compute_expense_manager', store=True, readonly=False,
        ui_domain=_group_hr_expense_user_domain,
        help='Select the user responsible for approving "Expenses" of this employee.\n'
             'If empty, the approval is done by the department manager (if they are an expense approver), '
             "otherwise by the employee's manager. If there is none, the expense is auto-validated.",
    )

    filter_for_expense = fields.Boolean(store=False, search='_search_filter_for_expense', groups="hr.group_hr_user,hr_expense.group_hr_expense_manager")

    def _search_filter_for_expense(self, operator, value):
        if operator != 'in':
            return NotImplemented

        domain = Domain.FALSE  # Nothing accepted by domain, by default
        user = self.env.user
        if user.has_groups('hr_expense.group_hr_expense_user'):
            domain = Domain('company_id', '=', False) | Domain('company_id', 'child_of', self.env.company.root_id.id)  # Then, domain accepts everything
        elif user.has_groups('hr_expense.group_hr_expense_team_approver') and user.employee_ids:
            employees = user.employee_ids
            domain = (
                Domain('department_id.manager_id', 'in', employees.ids)
                | Domain('parent_id', 'in', employees.ids)
                | Domain('id', 'in', employees.ids)
                | Domain('expense_manager_id', '=', user.id)
            )
        elif user.employee_id:
            employee = user.employee_id
            domain = Domain('id', '=', employee.id) & Domain('company_id', 'in', [False, employee.company_id.id])
        return domain

    def _get_expense_managers(self):
        self_sudo = self.sudo()
        return (
            self_sudo.expense_manager_id
            | self_sudo.parent_id.user_id
            | self_sudo.department_id.manager_id.user_id
        ).sudo(self.env.su)

    @api.depends('parent_id')
    def _compute_expense_manager(self):
        for employee in self:
            previous_manager = employee._origin.parent_id.user_id
            new_manager = employee.parent_id.user_id
            if new_manager and employee.expense_manager_id and employee.expense_manager_id == previous_manager:
                employee.expense_manager_id = new_manager
            elif not employee.expense_manager_id:
                employee.expense_manager_id = False

    def _get_user_m2o_to_empty_on_archived_employees(self):
        return super()._get_user_m2o_to_empty_on_archived_employees() + ['expense_manager_id']

    def _get_approver_fields(self):
        return super()._get_approver_fields() | {'expense_manager_id': 'hr_expense.group_hr_expense_team_approver'}


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    expense_manager_id = fields.Many2one('res.users', readonly=True)
