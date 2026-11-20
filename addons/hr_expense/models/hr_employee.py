# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.fields import Domain


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    expense_manager_id = fields.Many2one(readonly=False, related='version_id.expense_manager_id', inherited=True,
        ui_domain=lambda self: self.env['hr.version']._group_hr_expense_user_domain())

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

    def _get_user_m2o_to_empty_on_archived_employees(self):
        return super()._get_user_m2o_to_empty_on_archived_employees() + ['expense_manager_id']

    def _get_approver_fields(self):
        return super()._get_approver_fields() | {'expense_manager_id': 'hr_expense.group_hr_expense_team_approver'}


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    expense_manager_id = fields.Many2one('res.users', readonly=True)
