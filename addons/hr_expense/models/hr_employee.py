# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class HrEmployeeBase(models.AbstractModel):
    _inherit = 'hr.employee.base'

    filter_for_expense = fields.Boolean(store=False, search='_search_filter_for_expense', groups="hr.group_hr_user")

    def _search_filter_for_expense(self, operator, value):
        assert operator == '=' and value, "Operation not supported"

        res = [('id', '=', 0)]  # Nothing accepted by domain, by default
        user = self.env.user
        employee = user.employee_id
        if user.has_groups('hr_expense.group_hr_expense_user') or user.has_groups('account.group_account_user'):
            res = ['|', ('company_id', '=', False), ('company_id', 'child_of', self.env.company.root_id.id)]  # Then, domain accepts everything
        elif user.has_groups('hr_expense.group_hr_expense_team_approver') and user.employee_ids:
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
        return [('groups_id', 'in', group.ids), ('id', 'parent_of', self.ids)] if group else []

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
        """ Search the proper manager for the the employee, recursively if needed """
        employees_to_compute = self.filtered(
            # We only want to compute the field for employees that don't have it set yet or if the value has changed
            lambda employee: employee.expense_manager_id in {employee._origin.parent_id.user_id, False}
        )

        employee_to_parent_map = dict(self._read_group(
            domain=[('id', 'parent_of', employees_to_compute.ids)],
            groupby=['id'],
            aggregates=['parent_id:recordset']
        ))
        employee_to_valid_manager_cache = {}  # Because on large recordset we will probably search the same parent path several times
        def get_closest_valid_manager(employee):
            """ Search in the given employee parent_id chain, and store it in cache to avoid """
            manager_in_cache = employee_to_valid_manager_cache.get(employee)
            if manager_in_cache:
                return manager_in_cache
            valid_manager = self.env['res.users']

            employees_to_cache = [employee]
            next_parent = employee_to_parent_map[employee]
            while next_parent:
                # If the current parent is valid, we add the queue to the cache and return the current parent
                if next_parent.user_id and next_parent.user_id.has_group('hr_expense.group_hr_expense_team_approver'):
                    valid_manager = next_parent.user_id
                    employee_to_valid_manager_cache.update({employee: valid_manager for employee in employees_to_cache})
                    break

                # If the current parent is already in the cache
                valid_manager = employee_to_valid_manager_cache.get(next_parent, self.env['res.users'])
                if valid_manager:
                    employee_to_valid_manager_cache.update({employee: valid_manager for employee in employees_to_cache})
                    break

                # Add the current parent to the caching queue and continue with their parent
                employees_to_cache.append(next_parent)
                next_parent = employee_to_parent_map[next_parent]
            return valid_manager

        for employee in employees_to_compute:
            manager = get_closest_valid_manager(employee)
            if manager:
                employee.expense_manager_id = manager
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
