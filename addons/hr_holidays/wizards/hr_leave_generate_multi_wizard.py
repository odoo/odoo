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
    leave_type_request_unit = fields.Selection(
        related="holiday_status_id.request_unit",
    )
    # only meaningful when the type is taken in hours
    hour_from = fields.Float(
        string="Hour from",
        compute="_compute_hour_from_to",
        readonly=False,
        store=True,
    )
    hour_to = fields.Float(
        string="Hour to",
        compute="_compute_hour_from_to",
        readonly=False,
        store=True,
    )
    # only meaningful when the type is taken in half days
    date_from_period = fields.Selection(
        selection=[("am", "Morning"), ("pm", "Afternoon")],
        string="Date Period Start",
        default="am",
    )
    date_to_period = fields.Selection(
        selection=[("am", "Morning"), ("pm", "Afternoon")],
        string="Date Period End",
        default="pm",
    )

    @api.depends("employee_ids", "date_from", "date_to", "leave_type_request_unit")
    def _compute_hour_from_to(self):
        """Propose the working hours of the days being asked for.

        One shared calendar for the whole batch is the best that can be
        proposed: the hours land on every generated request, so they cannot
        follow each employee. Fall back to the company calendar as soon as
        the selection does not agree on one.
        """
        company_calendar = self.env.company.resource_calendar_id
        for record in self:
            calendars = record.employee_ids.resource_calendar_id
            calendar = calendars if len(calendars) == 1 else company_calendar
            if (
                record.leave_type_request_unit == "hour"
                and record.date_from
                and record.date_to
                and calendar
            ):
                record.hour_from, _unused = calendar._get_hours_for_date(
                    record.date_from
                )
                _unused, record.hour_to = calendar._get_hours_for_date(record.date_to)
            else:
                record.hour_from = 0.0
                record.hour_to = 0.0

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
        values = []
        for employee in employees:
            if not work_days_data[employee.id]["days"]:
                continue
            employee_values = {
                "name": self.name,
                "holiday_status_id": self.holiday_status_id.id,
                "request_date_from": self.date_from,
                "request_date_to": self.date_to,
                "employee_id": employee.id,
                "state": "validate" if validated else "confirm",
            }
            if self.leave_type_request_unit == "hour":
                employee_values["request_hour_from"] = self.hour_from
                employee_values["request_hour_to"] = self.hour_to
            elif self.leave_type_request_unit == "half_day":
                employee_values["request_date_from_period"] = self.date_from_period
                employee_values["request_date_to_period"] = self.date_to_period
            else:
                # a full day spans the whole window, which is already known
                # here; letting _compute_date_from_to redo it would recompute
                # number_of_days for every leave of the batch at once
                employee_values.update(
                    {
                        "date_from": date_from_tz,
                        "date_to": date_to_tz,
                        "number_of_days": work_days_data[employee.id]["days"],
                    }
                )
            values.append(employee_values)
        return values

    def action_generate_time_off(self):
        self.check_singleton()
        employees = self._get_employees_from_allocation_mode()

        tz = timezone(
            self.company_id.resource_calendar_id.tz or self.env.user.tz or "UTC"
        )
        if self.leave_type_request_unit == "hour":
            date_from_tz = (
                (
                    datetime.combine(self.date_from, datetime.min.time())
                    + timedelta(hours=self.hour_from)
                )
                .replace(tzinfo=tz)
                .astimezone(UTC)
                .replace(tzinfo=None)
            )
            date_to_tz = (
                (
                    datetime.combine(self.date_to, datetime.min.time())
                    + timedelta(hours=self.hour_to)
                )
                .replace(tzinfo=tz)
                .astimezone(UTC)
                .replace(tzinfo=None)
            )
        else:
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
