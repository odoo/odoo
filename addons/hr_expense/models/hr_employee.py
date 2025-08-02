# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class EmployeeBase(models.AbstractModel):
    _inherit = 'hr.employee.base'

    filter_for_expense = fields.Boolean(store=False, search='_search_filter_for_expense')

    def _search_filter_for_expense(self, operator, value):
        assert operator == '=' and value, "Operation not supported"

        res = [('id', '=', 0)]  # Nothing accepted by domain, by default
        user = self.env.user
        employee = user.employee_id
        if self.user_has_groups('hr_expense.group_hr_expense_user') or self.user_has_groups('account.group_account_user'):
            res = ['|', ('company_id', '=', False), ('company_id', 'child_of', self.env.company.root_id.id)]  # Then, domain accepts everything
        elif self.user_has_groups('hr_expense.group_hr_expense_team_approver') and user.employee_ids:
            res = [
                '|', '|', '|',
                ('department_id.manager_id', '=', employee.id),
                ('parent_id', '=', employee.id),
                ('id', '=', employee.id),
                ('expense_manager_id', '=', user.id),
                '|', ('company_id', '=', False), ('company_id', '=', employee.company_id.id),
            ]
        elif user.employee_id:
            res = [('id', '=', employee.id), '|', ('company_id', '=', False), ('company_id', '=', employee.company_id.id)]
        return res


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
        store=True,
        readonly=False,
        domain="[('id', 'in', expense_approver_ids)]",
        help='Select the user responsible for approving "Expenses" of this employee.\n'
             'If empty, the approval is done by an Administrator or Approver (determined in settings/users).',
    )

    parent_ids = fields.Many2many('hr.employee', compute="_compute_parent_ids")
    expense_approver_ids = fields.Many2many('res.users', compute="_compute_expense_approver_ids")

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

    @api.depends('parent_id')
    def _compute_parent_ids(self):
        for employee in self:
            parents = employee.env['hr.employee']
            parent = employee.parent_id
            while parent and parent not in parents:
                # The while condition should avoid the loops because of orphans (parent_id = False)
                # and cycles where A is its own ancestor (A == A.parent_id. ... .parent_id)
                parents += parent
                parent = parent.parent_id
            employee.parent_ids = parents

    def _compute_expense_approver_ids(self):
        for employee in self:
            employee.expense_approver_ids = employee.user_id.expense_approver_ids

    def _get_user_m2o_to_empty_on_archived_employees(self):
        return super()._get_user_m2o_to_empty_on_archived_employees() + ['expense_manager_id']


class EmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    expense_manager_id = fields.Many2one('res.users', readonly=True)


class User(models.Model):
    _inherit = ['res.users']

    def _get_expense_approver_domain(self):
        return [('id', 'in', self.expense_approver_ids.ids)]

    expense_approver_ids = fields.Many2many(
        'res.users',
        'user_expense_approver_rel',
        'user_id',
        'approver_id',
        compute="_compute_expense_approver_ids",
    )

    expense_manager_id = fields.Many2one(
        related='employee_id.expense_manager_id',
        domain="[('id', 'in', expense_approver_ids)]",
        readonly=False,
    )

    @api.depends('employee_id', 'employee_id.parent_id')
    def _compute_expense_approver_ids(self):
        team_approvers_group = self.env.ref('hr_expense.group_hr_expense_team_approver', raise_if_not_found=False)
        approvers = team_approvers_group.users if team_approvers_group else self.env["res.users"]
        for user in self:
            user.expense_approver_ids = approvers & user.employee_id.parent_ids.mapped("user_id")

    @api.onchange('employee_parent_id', 'expense_approver_ids')
    def _check_expense_approver_in_domain(self):
        for user in self:
            if user.expense_manager_id not in user.expense_approver_ids:
                user.expense_manager_id = False

    def write(self, vals):
        """ If 'Expense/Team Approver' has been removed from the access rights, we recompute the field user_id of the
        expense sheets having this user as approver. """
        res = True
        for user in self:
            user_was_approver = user.has_group('hr_expense.group_hr_expense_team_approver')
            res &= super().write(vals)
            if user_was_approver and not user.has_group('hr_expense.group_hr_expense_team_approver'):
                expense_children = user.env['res.users'].search([('expense_manager_id', '=', self.id)])
                expense_children.write({'expense_manager_id': False})
                expense_sheets = self.env['hr.expense.sheet'].search([('user_id', '=', self.id), ('state', 'in', ['draft', 'submit'])])
                expense_sheets._compute_from_employee_id()
        return res

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['expense_manager_id', 'expense_approver_ids']
