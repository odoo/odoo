import ast
from datetime import UTC, datetime

from dateutil.relativedelta import relativedelta

from odoo import fields, models
from odoo.fields import Domain


class HrDepartment(models.Model):
    _inherit = "hr.department"

    absence_of_today = fields.Integer(
        string="Absence by Today",
        compute="_compute_leave_count",
    )
    leave_to_approve_count = fields.Integer(
        string="Time Off to Approve",
        compute="_compute_leave_count",
    )
    allocation_to_approve_count = fields.Integer(
        string="Allocation to Approve",
        compute="_compute_leave_count",
    )

    def _compute_leave_count(self):
        Requests = self.env["hr.leave"]
        Allocations = self.env["hr.leave.allocation"]
        today_date = datetime.now(UTC).date()
        today_start = fields.Datetime.to_string(today_date)
        today_end = fields.Datetime.to_string(
            today_date + relativedelta(hours=23, minutes=59, seconds=59)
        )

        leave_data = Requests._read_group(
            [("department_id", "in", self.ids), ("state", "=", "confirm")],
            ["department_id"],
            ["__count"],
        )
        allocation_data = Allocations._read_group(
            [("department_id", "in", self.ids), ("state", "=", "confirm")],
            ["department_id"],
            ["__count"],
        )
        absence_data = Requests._read_group(
            [
                ("department_id", "in", self.ids),
                ("state", "=", "validate"),
                ("date_from", "<=", today_end),
                ("date_to", ">=", today_start),
            ],
            ["department_id"],
            ["__count"],
        )

        res_leave = {department.id: count for department, count in leave_data}
        res_allocation = {department.id: count for department, count in allocation_data}
        res_absence = {department.id: count for department, count in absence_data}

        for department in self:
            department.leave_to_approve_count = res_leave.get(department.id, 0)
            department.allocation_to_approve_count = res_allocation.get(
                department.id, 0
            )
            department.absence_of_today = res_absence.get(department.id, 0)

    def _get_action_context(self):
        return {
            "search_default_approve": 1,
            "search_default_active_employee": 2,
            "search_default_department_id": self.id,
            "default_department_id": self.id,
            "searchpanel_default_department_id": self.id,
        }

    def action_view_leave_department(self):
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "hr_holidays.hr_leave_action_action_approve_department"
        )
        action["context"] = {
            **self._get_action_context(),
            "search_default_active_time_off": 3,
            "hide_employee_name": 1,
        }
        return action

    def action_view_allocation_department(self):
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "hr_holidays.hr_leave_allocation_action_approve_department"
        )
        action["context"] = self._get_action_context()
        action["context"]["search_default_second_approval"] = 3
        action["domain"] = Domain.AND(
            [ast.literal_eval(action["domain"]), [("state", "=", "confirm")]]
        )
        return action
