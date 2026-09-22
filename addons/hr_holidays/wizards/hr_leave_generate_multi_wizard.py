from datetime import UTC, datetime, timedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.fields import Domain
from odoo.libs.datetime import timezone


class HrLeaveGenerateMultiWizard(models.TransientModel):
    _name = "hr.leave.generate.multi.wizard"
    _inherit = ["mixin.hr"]
    _description = "Generate time off for multiple employees"

    def _domain_employee_ids(self):
        domain = Domain([("company_id", "in", self.env.companies.ids)])
        if not self.env.user.has_group("hr_holidays.group_hr_holidays_user"):
            domain &= Domain(
                [
                    "|",
                    ("leave_manager_id", "=", self.env.user.id),
                    ("user_id", "=", self.env.user.id),
                ]
            )
        return domain

    name = fields.Char(string="Description")
    holiday_status_id = fields.Many2one(
        comodel_name="hr.leave.type",
        string="Time Off Type",
        required=True,
        domain="[('company_id', 'in', [company_id, False])]",
    )
    allocation_mode = fields.Selection(
        selection=[
            ("employee", "By Employee"),
            ("company", "By Company"),
            ("department", "By Department"),
            ("category", "By Employee Tag"),
        ],
        default="employee",
        readonly=False,
        required=True,
        help="Allow to create requests in batchs:\n- By Employee: for a specific employee"
        "\n- By Company: all employees of the specified company"
        "\n- By Department: all employees of the specified department"
        "\n- By Employee Tag: all employees of the specific employee group category",
    )
    employee_ids = fields.Many2many(
        comodel_name="hr.employee",
        string="Employees",
        domain=lambda self: self._domain_employee_ids(),
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        required=True,
    )
    department_id = fields.Many2one(comodel_name="hr.department")
    tag_id = fields.Many2one(
        comodel_name="res.partner.tag",
        string="Employee Tag",
    )
    date_from = fields.Date(
        string="Start Date",
        required=True,
    )
    date_to = fields.Date(
        string="End Date",
        required=True,
    )

    def _get_employees_from_allocation_mode(self):
        self.check_singleton()
        if self.allocation_mode == "employee":
            employees = self.employee_ids or self.env["hr.employee"].search(
                self._domain_employee_ids()
            )
        elif self.allocation_mode == "category":
            employees = self.tag_id.employee_ids.filtered(
                lambda e: e.company_id in self.env.companies
            )
        elif self.allocation_mode == "company":
            employees = self.env["hr.employee"].search(
                [("company_id", "=", self.company_id.id)]
            )
        else:
            employees = self.department_id.member_ids
        return employees

    def _prepare_employees_holiday_values(self, employees, date_from_tz, date_to_tz):
        self.check_singleton()
        work_days_data = employees.sudo()._get_work_days_data_batch(
            date_from_tz, date_to_tz
        )
        validated = (
            self.env.user.has_group("hr_holidays.group_hr_holidays_user")
            or self.holiday_status_id.leave_validation_type == "no_validation"
        )
        return [
            {
                "name": self.name,
                "holiday_status_id": self.holiday_status_id.id,
                "date_from": date_from_tz,
                "date_to": date_to_tz,
                "request_date_from": self.date_from,
                "request_date_to": self.date_to,
                "number_of_days": work_days_data[employee.id]["days"],
                "employee_id": employee.id,
                "state": "validate" if validated else "confirm",
            }
            for employee in employees
            if work_days_data[employee.id]["days"]
        ]

    def action_generate_time_off(self):
        self.check_singleton()
        employees = self._get_employees_from_allocation_mode()

        tz = timezone(
            self.company_id.resource_calendar_id.tz or self.env.user.tz or "UTC"
        )
        date_from_tz = (
            datetime.combine(self.date_from, datetime.min.time())
            .replace(tzinfo=tz)
            .astimezone(UTC)
            .replace(tzinfo=None)
        )
        date_to_tz = (
            datetime.combine(self.date_to, datetime.max.time())
            .replace(tzinfo=tz)
            .astimezone(UTC)
            .replace(tzinfo=None)
        )

        conflicting_leaves = (
            self.env["hr.leave"]
            .with_context(
                tracking_disable=True,
                mail_activity_automation_skip=True,
                leave_fast_create=True,
            )
            .search(
                [
                    ("date_from", "<=", date_to_tz),
                    ("date_to", ">", date_from_tz),
                    ("state", "not in", ["cancel", "refuse"]),
                    ("employee_id", "in", employees.ids),
                ]
            )
        )

        if conflicting_leaves:
            invalid_time_off = conflicting_leaves.filtered(
                lambda leave: leave.leave_type_request_unit == "hour"
            )
            if invalid_time_off:
                raise UserError(
                    self.env._(
                        "Some employees already have time off requests in hours that overlap with the selected period, Odoo cannot automatically adjust or split hourly leaves during batch generation. Conflicting time off:\n%s",
                        "\n".join(f"- {l.display_name}" for l in invalid_time_off),
                    )
                )
            one_day_leaves = conflicting_leaves.filtered(
                lambda leave: leave.request_date_from == leave.request_date_to
            )
            one_day_leaves.action_refuse()
            (conflicting_leaves - one_day_leaves)._split_leaves(
                self.date_from, self.date_to + timedelta(days=1)
            )

        vals_list = self._prepare_employees_holiday_values(
            employees, date_from_tz, date_to_tz
        )
        leaves = (
            self.env["hr.leave"]
            .with_context(
                tracking_disable=True,
                mail_activity_automation_skip=True,
                leave_fast_create=True,
                no_calendar_sync=True,
                leave_skip_state_check=True,
                multi_leave_request=True,
            )
            .create(vals_list)
        )
        # Only what is actually approved reserves the calendar. A request still
        # waiting for an officer would otherwise book the employee's working
        # time and put a meeting in their calendar before anyone said yes --
        # and its approval would then reserve the same period a second time,
        # because `_action_validate` applies it again.
        leaves.filtered(lambda leave: leave.state == "validate")._apply_leave_request()

        # create() drops the leaves of employees no allocation can cover; the
        # wizard is the only side that knows the request was a batch, so it is
        # the one that reports them. Employees who simply do not work those
        # days never made it into vals_list and are not "left out".
        requested = self.env["hr.employee"].browse(
            [vals["employee_id"] for vals in vals_list]
        )
        uncovered = requested - leaves.employee_id
        if uncovered:
            self.env.user._bus_send(
                "simple_notification",
                {
                    "type": "danger",
                    "message": self.env._(
                        "No valid allocation covers this request for: %(employees)s",
                        employees=", ".join(uncovered.mapped("name")),
                    ),
                },
            )

        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Generated Time Off"),
            "views": [
                [self.env.ref("hr_holidays.hr_leave_view_tree").id, "list"],
                [self.env.ref("hr_holidays.hr_leave_view_form_manager").id, "form"],
            ],
            "view_mode": "list",
            "res_model": "hr.leave",
            "domain": [("id", "in", leaves.ids)],
            "context": {
                "active_id": False,
            },
        }

    @api.constrains("allocation_mode")
    def _check_allocation_mode(self):
        is_manager = self.env.user.has_group("hr_holidays.group_hr_holidays_user")
        for record in self:
            if record.allocation_mode != "employee" and not is_manager:
                raise AccessError(
                    self.env._(
                        "As Time Off Responsible, you can only use the allocation mode 'By Employee'."
                    )
                )
