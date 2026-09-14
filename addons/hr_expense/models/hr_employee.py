from odoo import api, fields, models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def _group_hr_expense_user_domain(self):
        group = self.env.ref(
            "hr_expense.group_hr_expense_team_approver", raise_if_not_found=False
        )
        return (
            ["|", ("id", "parent_of", self.ids), ("all_group_ids", "in", group.ids)]
            if group
            else [("id", "parent_of", self.ids)]
        )

    expense_manager_id = fields.Many2one(
        comodel_name="res.users",
        string="Expense Approver",
        compute="_compute_expense_manager_id",
        store=True,
        readonly=False,
        domain=_group_hr_expense_user_domain,
        help='Select the user responsible for approving "Expenses" of this employee.\n'
        "If empty, the approval is done by an Administrator or Approver (determined in settings/users).",
    )

    filter_for_expense = fields.Boolean(
        search="_search_filter_for_expense",
        store=False,
        groups="hr.group_hr_user,hr_expense.group_hr_expense_manager",
    )

    def _search_filter_for_expense(self, operator, value):
        if operator != "in":
            return NotImplemented

        domain = Domain.FALSE
        user = self.env.user
        employee = user.employee_id
        _debug.logic("expense_filter_domain", user=user, employee=employee)
        if user.has_groups("hr_expense.group_hr_expense_user"):
            domain = Domain("company_id", "=", False) | Domain(
                "company_id", "child_of", self.env.company.root_id.id
            )
        elif (
            user.has_groups("hr_expense.group_hr_expense_team_approver")
            and user.employee_ids
        ):
            domain = (
                Domain("department_id.manager_id", "=", employee.id)
                | Domain("parent_id", "=", employee.id)
                | Domain("id", "=", employee.id)
                | Domain("expense_manager_id", "=", user.id)
            ) & Domain("company_id", "in", [False, employee.company_id.id])
        elif user.employee_id:
            domain = Domain("id", "=", employee.id) & Domain(
                "company_id", "in", [False, employee.company_id.id]
            )
        return domain

    @api.depends("parent_id")
    def _compute_expense_manager_id(self):
        for employee in self:
            previous_manager = employee._origin.parent_id.user_id
            new_manager = employee.parent_id.user_id
            if new_manager and (
                employee.expense_manager_id == previous_manager
                or not employee.expense_manager_id
            ):
                _debug.lifecycle(
                    "expense_manager_followed_parent",
                    employee=employee,
                    previous=previous_manager,
                    new=new_manager,
                )
                employee.expense_manager_id = new_manager
            elif not employee.expense_manager_id:
                employee.expense_manager_id = False

    def _get_user_field_names_to_empty_on_archive(self):
        return super()._get_user_field_names_to_empty_on_archive() + [
            "expense_manager_id"
        ]
