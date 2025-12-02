from odoo import fields, models
from odoo.fields import Domain


class HrEmployee(models.Model):
    _inherit = 'hr.employee.public'

    filter_for_expense = fields.Boolean(store=False, search='_search_filter_for_expense', groups="hr.group_hr_user")

    def _search_filter_for_expense(self, operator, value):
        if operator != 'in':
            return NotImplemented

        domain = Domain.FALSE  # Nothing accepted by domain, by default
        user = self.env.user
        employee = user.employee_id
        if user.has_groups('hr_expense.group_hr_expense_user') or user.has_groups('account.group_account_user'):
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
