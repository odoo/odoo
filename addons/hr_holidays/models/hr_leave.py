import logging
from collections import defaultdict
from datetime import UTC, datetime, time, timedelta
from math import ceil

from markupsafe import Markup

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Command, Date, Domain
from odoo.libs.datetime import timezone
from odoo.libs.intervals import Intervals
from odoo.libs.numbers import float_compare, float_round
from odoo.tools.date_utils import float_to_time
from odoo.tools.misc import clean_context, format_date
from odoo.tools.translate import _

from odoo.addons.base.models.ir_model_common import MODULE_UNINSTALL_FLAG
from odoo.addons.base.models.res_partner import _selection_timezones
from odoo.addons.resource.models.utils import HOURS_PER_DAY

_logger = logging.getLogger(__name__)

VALIDITY_TRIGGER_FIELDS = frozenset(
    {
        "employee_id",
        "holiday_status_id",
        "state",
    }
)

CONSUMPTION_FIELDS = ("date_from", "date_to", "number_of_days", "number_of_hours")


class HrLeave(models.Model):
    _name = "hr.leave"
    _description = "Time Off"
    _order = "date_from desc"
    _inherit = [
        "mixin.hr.leave.approval",
        "mixin.mail.thread.main.attachment",
        "mixin.mail.activity",
    ]
    _mail_post_access = "read"

    @api.model
    def default_get(self, fields):
        defaults = super().default_get(fields)
        defaults = self._default_get_request_dates(defaults)
        if (
            self.env.context.get("holiday_status_display_name", True)
            and "holiday_status_id" in fields
            and not defaults.get("holiday_status_id")
        ):
            domain = [
                "|",
                ("requires_allocation", "=", False),
                ("has_valid_allocation", "=", True),
            ]
            defaults["holiday_status_id"] = False
            leave_types = self.env["hr.leave.type"].search(domain, order="sequence")
            selected_leave_type = next(
                (
                    leave_type
                    for leave_type in leave_types
                    if (
                        defaults.get("request_unit_hours")
                        and leave_type["request_unit"] == "hour"
                    )
                    or (not defaults.get("request_unit_hours"))
                ),
                leave_types[0] if leave_types else None,
            )
            if selected_leave_type:
                defaults["holiday_status_id"] = selected_leave_type.id
                defaults["request_unit_hours"] = (
                    selected_leave_type.request_unit == "hour"
                )

        if "request_date_from" in fields and "request_date_from" not in defaults:
            defaults["request_date_from"] = Date.today()
        if "request_date_to" in fields and "request_date_to" not in defaults:
            defaults["request_date_to"] = Date.today()

        return defaults

    def _default_get_request_dates(self, values):

        client_tz = self.env.tz
        if values.get("date_from"):
            if not values.get("request_date_from"):
                values["request_date_from"] = (
                    values["date_from"].replace(tzinfo=UTC).astimezone(client_tz)
                )
            del values["date_from"]
        if values.get("date_to"):
            if not values.get("request_date_to"):
                values["request_date_to"] = (
                    values["date_to"].replace(tzinfo=UTC).astimezone(client_tz)
                )
            del values["date_to"]
        return values

    name = fields.Char(
        string="Description",
        compute="_compute_name",
        inverse="_inverse_name",
        search="_search_name",
        compute_sudo=False,
        copy=False,
    )
    private_name = fields.Char(
        string="Time Off Description",
        groups="hr_holidays.group_hr_holidays_responsible",
    )
    state = fields.Selection(
        selection=[
            ("confirm", "To Approve"),
            ("refuse", "Refused"),
            ("validate1", "Second Approval"),
            ("validate", "Approved"),
            ("cancel", "Cancelled"),
        ],
        string="Status",
        default="confirm",
        store=True,
        copy=False,
        readonly=False,
        tracking=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        related="employee_id.user_id",
        string="User",
        compute_sudo=True,
        related_sudo=True,
        store=True,
        index=True,
        readonly=True,
    )
    holiday_status_id = fields.Many2one(
        comodel_name="hr.leave.type",
        string="Time Off Type",
        compute="_compute_holiday_status_id",
        store=True,
        readonly=False,
        required=True,
        domain="""[
            '|',
                ('requires_allocation', '=', False),
                ('has_valid_allocation', '=', True),
        ]""",
        tracking=True,
    )
    holiday_status_requires_allocation = fields.Boolean(
        related="holiday_status_id.requires_allocation"
    )
    color = fields.Integer(
        related="holiday_status_id.color",
        string="Color",
    )
    validation_type = fields.Selection(
        related="holiday_status_id.leave_validation_type",
        string="Validation Type",
        readonly=False,
    )

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        default=lambda self: self.env.user.employee_id,
        index=True,
        required=True,
        domain=lambda self: self._domain_employee_id(),
        ondelete="restrict",
        tracking=True,
    )
    employee_company_id = fields.Many2one(
        related="employee_id.company_id",
        string="Employee Company",
        store=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        compute="_compute_company_id",
        store=True,
    )
    active_employee = fields.Boolean(
        related="employee_id.active",
        string="Employee Active",
    )
    tz_mismatch = fields.Boolean(compute="_compute_tz_mismatch")
    tz = fields.Selection(
        selection=_selection_timezones,
        compute="_compute_tz",
    )
    department_id = fields.Many2one(
        comodel_name="hr.department",
        compute="_compute_department_id",
        store=True,
        readonly=False,
    )
    notes = fields.Text(
        string="Reasons",
        readonly=False,
    )
    resource_calendar_id = fields.Many2one(
        comodel_name="resource.calendar",
        compute="_compute_resource_calendar_id",
        store=True,
        copy=False,
        readonly=False,
    )
    max_leaves = fields.Float(compute="_compute_leaves")
    virtual_remaining_leaves = fields.Float(
        string="Available Time Off",
        compute="_compute_leaves",
    )
    date_from = fields.Datetime(
        string="Start Date",
        compute="_compute_date_from_to",
        store=True,
        index=True,
        tracking=True,
    )
    date_to = fields.Datetime(
        string="End Date",
        compute="_compute_date_from_to",
        store=True,
        tracking=True,
    )
    number_of_days = fields.Float(
        string="Duration (Days)",
        help="Number of days of the time off request. Used in the calculation.",
        compute="_compute_duration",
        store=True,
        tracking=True,
    )
    number_of_hours = fields.Float(
        string="Duration (Hours)",
        help="Number of hours of the time off request. Used in the calculation.",
        compute="_compute_duration",
        store=True,
        tracking=True,
    )
    last_several_days = fields.Boolean(
        string="All day",
        compute="_compute_last_several_days",
    )
    duration_display = fields.Char(
        string="Requested",
        compute="_compute_duration_display",
        store=True,
    )
    meeting_id = fields.Many2one(
        comodel_name="calendar.event",
        copy=False,
    )
    first_approver_id = fields.Many2one(
        comodel_name="hr.employee",
        string="First Approval",
        help="This area is automatically filled by the user who validate the time off",
        copy=False,
        readonly=True,
    )
    second_approver_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Second Approval",
        help="This area is automatically filled by the user who validate the time off with second level (If time off type need second validation)",
        copy=False,
        readonly=True,
    )

    can_cancel = fields.Boolean(
        export_string_translation=False,
        compute="_compute_can_cancel",
    )
    can_back_to_approve = fields.Boolean(
        export_string_translation=False,
        compute="_compute_can_back_to_approve",
    )

    attachment_ids = fields.One2many(
        comodel_name="ir.attachment",
        inverse_name="res_id",
        string="Attachments",
    )
    supported_attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        string="Attach File",
        compute="_compute_supported_attachments",
        inverse="_inverse_supported_attachment_ids",
    )
    supported_attachment_ids_count = fields.Integer(
        compute="_compute_supported_attachments"
    )
    leave_type_request_unit = fields.Selection(
        related="holiday_status_id.request_unit",
        readonly=True,
    )
    leave_type_support_document = fields.Boolean(
        related="holiday_status_id.support_document"
    )
    request_date_from = fields.Date(string="Request Start Date")
    request_date_to = fields.Date(string="Request End Date")
    request_hour_from = fields.Float(
        string="Hour from",
        compute="_compute_request_hour_from_to",
        store=True,
        readonly=False,
    )
    request_hour_to = fields.Float(
        string="Hour to",
        compute="_compute_request_hour_from_to",
        store=True,
        readonly=False,
    )
    request_date_from_period = fields.Selection(
        selection=[("am", "Morning"), ("pm", "Afternoon")],
        string="Date Period Start",
        default="am",
    )
    request_date_to_period = fields.Selection(
        selection=[("am", "Morning"), ("pm", "Afternoon")],
        string="Date Period End",
        default="pm",
    )
    request_unit_half = fields.Boolean(
        string="Half-Day",
        compute="_compute_request_unit_half",
        store=True,
    )
    request_unit_hours = fields.Boolean(
        string="Specific Time",
        compute="_compute_request_unit_hours",
        store=True,
    )
    is_hatched = fields.Boolean(
        string="Hatched",
        compute="_compute_is_hatched_and_striked",
    )
    is_striked = fields.Boolean(
        string="Striked",
        compute="_compute_is_hatched_and_striked",
    )
    has_mandatory_day = fields.Boolean(compute="_compute_has_mandatory_day")
    leave_type_increases_duration = fields.Char(
        compute="_compute_leave_type_increases_duration"
    )

    dashboard_warning_message = fields.Char(
        compute="_compute_dashboard_warning_message"
    )
    _date_check2 = models.Constraint(
        "CHECK ((date_from <= date_to))",
        "The start date must be before or equal to the end date.",
    )
    _date_check3 = models.Constraint(
        "CHECK ((request_date_from <= request_date_to))",
        "The request start date must be before or equal to the request end date.",
    )
    _duration_check = models.Constraint(
        "CHECK ( number_of_days >= 0 )",
        "The duration of a time off cannot be negative.",
    )
    _date_to_date_from_index = models.Index("(date_to, date_from)")

    @api.onchange("request_hour_from", "request_hour_to")
    def _onchange_hours(self):
        self.request_hour_from = min(max(self.request_hour_from, 0.0), 23.99)
        self.request_hour_to = min(max(self.request_hour_to, 0.0), 24)

    @api.depends(
        "employee_id", "request_date_from", "request_date_to", "request_unit_hours"
    )
    def _compute_request_hour_from_to(self):
        env_company_calendar = self.env.company.resource_calendar_id
        for leave in self:
            calendar = leave.resource_calendar_id or env_company_calendar
            if (
                not leave.request_unit_hours
                and leave.employee_id
                and leave.request_date_from
                and leave.request_date_to
                and calendar
            ):
                hour_from, hour_to = leave._get_hour_from_to(
                    leave.request_date_from, leave.request_date_to
                )
                leave.request_hour_from = hour_from
                leave.request_hour_to = hour_to

    @api.depends(
        "employee_id",
        "leave_type_request_unit",
        "request_date_from",
        "request_date_to",
        "request_hour_from",
        "request_hour_to",
        "request_date_from_period",
        "request_date_to_period",
    )
    @api.depends_context("uid", "lang")
    def _compute_dashboard_warning_message(self):
        dated = self.filtered(lambda leave: leave.date_from and leave.date_to)
        (self - dated).dashboard_warning_message = False
        if not dated:
            return
        all_leaves = self.search(
            [
                ("date_from", "<", max(dated.mapped("date_to"))),
                ("date_to", ">", min(dated.mapped("date_from"))),
                ("employee_id", "in", self.employee_id.ids),
                ("holiday_status_id.allow_request_on_top", "=", False),
                ("state", "not in", ["cancel", "refuse"]),
            ]
        )
        dated.filtered(
            lambda leave: leave.state in ["cancel", "refuse"]
        ).dashboard_warning_message = False
        for holiday in dated.filtered(
            lambda leave: leave.state not in ["cancel", "refuse"]
        ):
            conflicting_holidays = all_leaves.filtered_domain(
                [
                    ("employee_id", "in", holiday.employee_id.ids),
                    ("date_from", "<", holiday.date_to),
                    ("date_to", ">", holiday.date_from),
                    ("id", "not in", holiday.ids),
                ]
            )
            if not conflicting_holidays:
                holiday.dashboard_warning_message = False
                continue

            conflicting_holidays_list = []
            holidays_only_have_uid = bool(holiday.employee_id)
            holiday_states = dict(
                conflicting_holidays.fields_get(allfields=["state"])["state"][
                    "selection"
                ]
            )
            for conflicting_holiday in conflicting_holidays:
                conflicting_holiday_data = {
                    "employee_name": conflicting_holiday.employee_id.name,
                    "date_from": format_date(
                        self.env, min(conflicting_holiday.mapped("date_from"))
                    ),
                    "date_to": format_date(
                        self.env, min(conflicting_holiday.mapped("date_to"))
                    ),
                    "state": holiday_states[conflicting_holiday.state],
                }
                if conflicting_holiday.employee_id.user_id.id != self.env.uid:
                    holidays_only_have_uid = False
                if conflicting_holiday_data not in conflicting_holidays_list:
                    conflicting_holidays_list.append(conflicting_holiday_data)

            msg = ""
            if holidays_only_have_uid:
                msg = self.env._(
                    "You've already booked time off which overlaps with this period:"
                )
            else:
                msg = self.env._(
                    "An employee already booked time off which overlaps with this period:"
                )

            holiday.dashboard_warning_message = msg + "".join(
                (
                    "\n\t"
                    + self.env._(
                        "%(employee_name)s from %(date_from)s to %(date_to)s - %(state)s"
                    )
                )
                % {
                    "employee_name": conflicting_holiday_data["employee_name"]
                    if not holidays_only_have_uid
                    else "",
                    "date_from": conflicting_holiday_data["date_from"],
                    "date_to": conflicting_holiday_data["date_to"],
                    "state": conflicting_holiday_data["state"],
                }
                for conflicting_holiday_data in conflicting_holidays_list
            )

    @api.depends_context("uid")
    def _compute_name(self):
        self.check_access("read")

        is_officer = self.env.user.has_group("hr_holidays.group_hr_holidays_user")

        for leave in self:
            if is_officer or self.env.user in (
                leave.user_id,
                leave.employee_id.leave_manager_id,
            ):
                leave.name = leave.sudo().private_name
            else:
                leave.name = "*****"

    def _inverse_name(self):
        is_officer = self.env.user.has_group("hr_holidays.group_hr_holidays_user")

        for leave in self:
            if is_officer or self.env.user in (
                leave.user_id,
                leave.employee_id.leave_manager_id,
            ):
                leave.sudo().private_name = leave.name

    def _search_name(self, operator, value):
        is_officer = self.env.user.has_group("hr_holidays.group_hr_holidays_user")
        domain = Domain("private_name", operator, value)

        if not is_officer:
            domain &= Domain("user_id", "=", self.env.user.id)
        query = self.sudo()._search(domain)
        return Domain("id", "in", query)

    @api.depends("employee_id", "request_date_from", "request_date_to")
    def _compute_resource_calendar_id(self):
        leaves_without_emp_or_date = self.filtered(
            lambda leave: (
                not (
                    leave.employee_id
                    and leave.request_date_from
                    and leave.request_date_to
                )
            )
        )
        valid_leaves = self - leaves_without_emp_or_date
        leaves_without_emp_or_date.resource_calendar_id = (
            self.env.company.resource_calendar_id
        )
        if not valid_leaves:
            return
        employees_by_dates = defaultdict(lambda: self.env["hr.employee"])
        contracts_by_employee = dict(
            self.env["hr.version"]._read_group(
                domain=[("employee_id", "in", self.employee_id.ids)],
                groupby=["employee_id"],
                aggregates=["id:recordset"],
            )
        )
        for leave in valid_leaves:
            employees_by_dates[leave.request_date_from] += leave.employee_id
        calendar_by_dates = {
            date_from: employees._get_calendars(date_from)
            for date_from, employees in employees_by_dates.items()
        }
        for leave in valid_leaves:
            calendar = (
                calendar_by_dates.get(leave.request_date_from, {}).get(
                    leave.employee_id.id
                )
                or self.env.company.resource_calendar_id
            )
            contracts = contracts_by_employee.get(
                leave.employee_id, self.env["hr.version"]
            ).filtered(
                lambda c, leave=leave: (
                    c.date_start <= leave.request_date_to
                    and (not c.date_end or c.date_end >= leave.request_date_from)
                )
            )
            if contracts:
                calendar = contracts[:1].resource_calendar_id
            leave.resource_calendar_id = calendar

    def _get_overlapping_contracts(self):
        self.check_singleton()
        if not self.date_from or not self.date_to:
            return self.env["hr.version"]
        versions = self.employee_id.sudo().version_ids.filtered_domain(
            [
                ("contract_date_start", "!=", False),
                ("contract_date_start", "<=", self.date_to.date()),
                "|",
                ("contract_date_end", ">=", self.date_from.date()),
                ("contract_date_end", "=", False),
            ]
        )
        return versions.filtered(
            lambda v: v._has_contract_overlap(
                self.date_from.date(), self.date_to.date()
            )
        )

    @api.constrains("date_from", "date_to")
    def _check_contracts(self):
        for holiday in self.filtered("employee_id"):
            versions = holiday._get_overlapping_contracts()
            if len(versions.resource_calendar_id) > 1:
                raise ValidationError(
                    self.env._(
                        """A leave cannot be set across multiple versions with different working schedules.

Please create one time off for each version period.

Time off:
%(time_off)s

Versions:
%(versions)s""",
                        time_off=holiday.display_name,
                        versions="\n".join(
                            _(
                                "- '%(version)s' from %(start_date)s to %(end_date)s",
                                version=version.name or version.employee_id.name,
                                start_date=format_date(self.env, version.date_start),
                                end_date=format_date(self.env, version.date_end)
                                if version.date_end
                                else self.env._("undefined"),
                            )
                            for version in versions
                        ),
                    )
                )

    @api.depends(
        "request_date_from_period",
        "request_date_to_period",
        "request_hour_from",
        "request_hour_to",
        "request_date_from",
        "request_date_to",
        "request_unit_half",
        "request_unit_hours",
        "employee_id",
    )
    def _compute_date_from_to(self):
        for holiday in self:
            if not holiday.request_date_from:
                holiday.date_from = False
                continue

            if not holiday.request_date_to:
                holiday.date_to = False
                continue

            if holiday.request_unit_hours:
                hour_from = holiday.request_hour_from
                hour_to = holiday.request_hour_to
                if not hour_from or not hour_to:
                    computed_from, computed_to = holiday._get_hour_from_to(
                        holiday.request_date_from, holiday.request_date_to
                    )
                    hour_from = hour_from or computed_from
                    hour_to = hour_to or computed_to

            elif holiday.request_unit_half:
                period_map = {"am": "morning", "pm": "afternoon"}
                from_period = period_map.get(holiday.request_date_from_period)
                to_period = period_map.get(holiday.request_date_to_period)
                if holiday.request_date_from == holiday.request_date_to:
                    day_period = from_period if from_period == to_period else None
                    hour_from, hour_to = holiday._get_hour_from_to(
                        holiday.request_date_from, holiday.request_date_to, day_period
                    )
                else:
                    hour_from, _ = holiday._get_hour_from_to(
                        holiday.request_date_from,
                        holiday.request_date_from,
                        from_period,
                    )
                    _, hour_to = holiday._get_hour_from_to(
                        holiday.request_date_to, holiday.request_date_to, to_period
                    )

            else:
                hour_from, hour_to = holiday._get_hour_from_to(
                    holiday.request_date_from, holiday.request_date_to
                )

            holiday.date_from = self._to_utc(
                holiday.request_date_from, hour_from, holiday.employee_id or holiday
            )
            holiday.date_to = self._to_utc(
                holiday.request_date_to, hour_to, holiday.employee_id or holiday
            )

    @api.depends("leave_type_request_unit")
    def _compute_request_unit_half(self):
        for holiday in self:
            holiday.request_unit_half = holiday.leave_type_request_unit == "half_day"

    @api.depends("leave_type_request_unit")
    def _compute_request_unit_hours(self):
        for holiday in self:
            holiday.request_unit_hours = holiday.leave_type_request_unit == "hour"

    def _domain_employee_id(self):
        domain = [
            ("active", "=", True),
            ("company_id", "in", self.env.companies.ids),
        ]
        if not self.env.user.has_group("hr_holidays.group_hr_holidays_user"):
            domain += [
                "|",
                ("user_id", "=", self.env.uid),
                ("leave_manager_id", "=", self.env.uid),
            ]
        return domain

    @api.depends("employee_id")
    @api.depends_context("uid")
    def _compute_holiday_status_id(self):
        for holiday in self:
            if not holiday.holiday_status_id.requires_allocation:
                continue
            if not holiday.employee_id:
                holiday.holiday_status_id = False
            elif (
                holiday.employee_id.user_id != self.env.user
                and holiday._origin.employee_id != holiday.employee_id
            ):
                if (
                    holiday.employee_id
                    and not holiday.holiday_status_id.with_context(
                        employee_id=holiday.employee_id.id
                    ).has_valid_allocation
                ):
                    holiday.holiday_status_id = False

    @api.depends("employee_id")
    def _compute_department_id(self):
        for holiday in self:
            holiday.department_id = holiday.employee_id.department_id

    @api.depends("date_from", "date_to", "holiday_status_id")
    def _compute_has_mandatory_day(self):
        dated = self.filtered(lambda leave: leave.date_from and leave.date_to)
        (self - dated).has_mandatory_day = False
        if dated:
            date_from = min(dated.mapped("date_from"))
            date_to = max(dated.mapped("date_to"))
            mandatory_days = self.employee_id.sudo()._get_mandatory_days(
                date_from.date(), date_to.date()
            )

            for leave in dated:
                department_ids = leave.employee_id.department_id.ids
                domain = [
                    ("start_date", "<=", leave.date_to.date()),
                    ("end_date", ">=", leave.date_from.date()),
                    "|",
                    ("resource_calendar_id", "=", False),
                    ("resource_calendar_id", "=", leave.resource_calendar_id.id),
                ]
                if department_ids:
                    domain += [
                        "|",
                        ("department_ids", "=", False),
                        ("department_ids", "parent_of", department_ids),
                    ]
                else:
                    domain += [("department_ids", "=", False)]

                if leave.holiday_status_id.company_id:
                    domain += [
                        ("company_id", "=", leave.holiday_status_id.company_id.id)
                    ]
                leave.has_mandatory_day = bool(mandatory_days.filtered_domain(domain))

    @api.depends("leave_type_request_unit", "number_of_days")
    @api.depends_context("lang")
    def _compute_leave_type_increases_duration(self):
        durations = self._get_durations(check_leave_type=False)
        for leave in self:
            days = durations[leave.id][0]
            if (
                leave.leave_type_request_unit == "day"
                and leave.holiday_status_requires_allocation
                and days < leave.number_of_days
            ):
                leave.leave_type_increases_duration = self.env._(
                    "According to your working schedule you are expected to work"
                    " %(days)s days in this period, but %(nb_days)s days will be used because this leave"
                    " %(leave_type_name)s can only be taken by days.",
                    days=days,
                    nb_days=leave.number_of_days,
                    leave_type_name=leave.holiday_status_id.name,
                )
            else:
                leave.leave_type_increases_duration = ""

    def _get_durations(self, check_leave_type=True, resource_calendar=None):
        result = {}
        employee_leaves = self.filtered("employee_id")
        per_day_employees = defaultdict(lambda: self.env["hr.employee"])
        work_data_employees = defaultdict(lambda: self.env["hr.employee"])
        for leave in employee_leaves:
            if not leave.date_from or not leave.date_to:
                continue
            if (
                leave.employee_id.sudo().is_flexible
                and leave.request_date_to == leave.request_date_from
            ):
                continue
            key = (
                leave.date_from,
                leave.date_to,
                leave.holiday_status_id.include_public_holidays_in_duration,
                resource_calendar or leave.resource_calendar_id,
            )
            if leave.leave_type_request_unit == "day" and check_leave_type:
                per_day_employees[key] += leave.employee_id
            else:
                work_data_employees[key] += leave.employee_id
        domain = [
            ("time_type", "=", "leave"),
            ("company_id", "in", self.env.companies.ids),
            "|",
            ("holiday_id", "=", False),
            ("holiday_id", "not in", employee_leaves.ids),
        ]
        work_time_per_day_mapped = {
            key: employees.with_context(
                compute_leaves=not key[2]
            )._list_work_time_per_day(key[0], key[1], domain=domain, calendar=key[3])
            for key, employees in per_day_employees.items()
        }
        work_days_data_mapped = {
            key: employees._get_work_days_data_batch(
                key[0],
                key[1],
                compute_leaves=not key[2],
                domain=domain,
                calendar=key[3],
            )
            for key, employees in work_data_employees.items()
        }
        for leave in self:
            calendar = resource_calendar or leave.resource_calendar_id
            if (
                not leave.date_from
                or not leave.date_to
                or (not calendar and not leave.employee_id)
            ):
                result[leave.id] = (0, 0)
                continue
            hours, days = (0, 0)
            if leave.employee_id:
                if (
                    leave.employee_id.sudo().is_flexible
                    and leave.request_date_to == leave.request_date_from
                ):
                    public_holidays = self.env["resource.calendar.leaves"].search(  # noqa: E8507 - one lookup per flexible one-day leave, on its own calendar and date
                        [
                            ("resource_id", "=", False),
                            ("date_from", "<", leave.date_to),
                            ("date_to", ">", leave.date_from),
                            ("calendar_id", "in", [False, calendar.id]),
                            ("company_id", "=", leave.company_id.id),
                        ]
                    )
                    if public_holidays:
                        public_holidays_intervals = Intervals(
                            [(ph.date_from, ph.date_to, ph) for ph in public_holidays]
                        )
                        leave_intervals = Intervals(
                            [(leave.date_from, leave.date_to, leave)]
                        )
                        real_leave_intervals = (
                            leave_intervals - public_holidays_intervals
                        )
                        hours = 0
                        for start, stop, _meta in real_leave_intervals:
                            hours += (stop - start).total_seconds() / 3600
                    else:
                        hours = (leave.date_to - leave.date_from).total_seconds() / 3600
                    if not leave.request_unit_hours and not public_holidays:
                        days = (
                            1
                            if not leave.request_unit_half
                            or leave.request_date_from_period
                            != leave.request_date_to_period
                            else 0.5
                        )
                    else:
                        days = hours / 24
                elif leave.leave_type_request_unit == "day" and check_leave_type:
                    work_time_per_day_list = work_time_per_day_mapped[
                        leave.date_from,
                        leave.date_to,
                        leave.holiday_status_id.include_public_holidays_in_duration,
                        calendar,
                    ][leave.employee_id.id]
                    days = len(work_time_per_day_list)
                    hours = sum(t[1] for t in work_time_per_day_list)
                else:
                    work_days_data = work_days_data_mapped[
                        leave.date_from,
                        leave.date_to,
                        leave.holiday_status_id.include_public_holidays_in_duration,
                        calendar,
                    ][leave.employee_id.id]
                    hours, days = work_days_data["hours"], work_days_data["days"]
            else:
                today_hours = calendar.get_work_hours_count(
                    datetime.combine(leave.date_from.date(), time.min),
                    datetime.combine(leave.date_from.date(), time.max),
                    False,
                )
                hours = calendar.get_work_hours_count(
                    leave.date_from,
                    leave.date_to,
                    compute_leaves=not leave.holiday_status_id.include_public_holidays_in_duration,
                )
                days = hours / (today_hours or HOURS_PER_DAY)
            if leave.leave_type_request_unit == "day" and check_leave_type:
                days = ceil(days)
            result[leave.id] = (days, hours)
        return result

    @api.depends(
        "date_from", "date_to", "resource_calendar_id", "holiday_status_id.request_unit"
    )
    def _compute_duration(self):
        durations = self._get_durations()
        for leave in self:
            days, hours = durations[leave.id]
            leave.number_of_hours = hours
            leave.number_of_days = days

    @api.depends("employee_company_id", "department_id.company_id")
    def _compute_company_id(self):
        for holiday in self:
            holiday.company_id = (
                holiday.employee_company_id
                or holiday.department_id.company_id
                or self.env.company
            )

    @api.depends("number_of_days")
    def _compute_last_several_days(self):
        for holiday in self:
            holiday.last_several_days = holiday.number_of_days > 1

    @api.depends("tz")
    @api.depends_context("uid")
    def _compute_tz_mismatch(self):
        for leave in self:
            leave.tz_mismatch = leave.tz != self.env.user.tz

    @api.depends("resource_calendar_id.tz")
    @api.depends_context("uid", "company")
    def _compute_tz(self):
        for leave in self:
            leave.tz = (
                leave.resource_calendar_id.tz
                or self.env.company.resource_calendar_id.tz
                or self.env.user.tz
                or "UTC"
            )

    @api.depends("number_of_hours", "number_of_days", "leave_type_request_unit")
    def _compute_duration_display(self):
        for leave in self:
            duration = leave.number_of_days
            unit = _("days")
            display = "%g %s" % (float_round(duration, precision_digits=2), unit)
            if leave.leave_type_request_unit == "hour":
                hours, minutes = divmod(abs(leave.number_of_hours) * 60, 60)
                minutes = round(minutes)
                if minutes == 60:
                    minutes = 0
                    hours += 1
                duration = "%d:%02d" % (hours, minutes)
                unit = _("hours")
                display = f"{duration} {unit}"
            leave.duration_display = display

    @api.depends_context("uid")
    @api.depends("state", "employee_id", "department_id")
    def _compute_can_back_to_approve(self):
        for holiday in self:
            holiday.can_back_to_approve = (
                holiday.state == "validate"
                and holiday._check_approval_update(
                    "confirm", raise_if_not_possible=False
                )
            )

    @api.depends_context("uid")
    @api.depends("state", "employee_id")
    def _compute_can_cancel(self):
        for holiday in self:
            holiday.can_cancel = holiday._check_approval_update(
                "cancel", raise_if_not_possible=False
            )

    @api.depends("state")
    def _compute_is_hatched_and_striked(self):
        for holiday in self:
            holiday.is_striked = holiday.state == "refuse"
            holiday.is_hatched = holiday.state not in ["refuse", "validate"]

    @api.depends("attachment_ids")
    def _compute_supported_attachments(self):
        for holiday in self:
            holiday.supported_attachment_ids = holiday.attachment_ids
            holiday.supported_attachment_ids_count = len(holiday.attachment_ids.ids)

    @api.depends("employee_id", "holiday_status_id")
    @api.depends_context("default_request_date_from")
    def _compute_leaves(self):
        date_from = (
            fields.Date.from_string(self.env.context["default_request_date_from"])
            if "default_request_date_from" in self.env.context
            else fields.Date.context_today(self)
        )
        employee_days_per_allocation = self.employee_id._get_consumed_leaves(
            self.holiday_status_id, date_from
        )[0]
        for leave in self:
            virtual_remaining_leaves = 0
            max_leaves = 0
            for allocation, allocation_dict in employee_days_per_allocation[
                leave.employee_id
            ][leave.holiday_status_id].items():
                if allocation and (
                    not allocation.date_to or allocation.date_to >= date_from
                ):
                    max_leaves += allocation_dict["max_leaves"]
                    virtual_remaining_leaves += allocation_dict[
                        "virtual_remaining_leaves"
                    ]
            leave.virtual_remaining_leaves = virtual_remaining_leaves
            leave.max_leaves = max_leaves

    def _inverse_supported_attachment_ids(self):
        for holiday in self:
            holiday.attachment_ids = holiday.supported_attachment_ids
        self.invalidate_recordset(["attachment_ids"])

    @api.constrains("date_from", "date_to", "employee_id")
    def _check_date(self):
        if self.env.context.get("leave_skip_date_check", False):
            return
        for holiday in self:
            if holiday.dashboard_warning_message:
                raise ValidationError(holiday.dashboard_warning_message)

    @api.constrains("date_from", "date_to", "employee_id")
    def _check_date_state(self):
        if self.env.context.get("leave_skip_state_check"):
            return
        for holiday in self:
            if holiday.state in ["validate1", "validate"]:
                raise ValidationError(
                    _("This modification is not allowed in the current state.")
                )

    def _raise_missing_allocation(self):
        raise ValidationError(
            _(
                "You do not have any allocation for this time off type.\n"
                "Please request an allocation before submitting your time off request."
            )
        )

    def _check_validity(self):
        if any(not leave.date_from or not leave.date_to for leave in self):
            raise ValidationError(
                _("A time off request needs both a start date and an end date.")
            )
        sorted_leaves = defaultdict(lambda: self.env["hr.leave"])
        for leave in self:
            sorted_leaves[(leave.holiday_status_id, leave.date_from.date())] |= leave
        for (leave_type, date_from), leaves in sorted_leaves.items():
            if not leave_type.requires_allocation:
                continue
            employees = leaves.employee_id
            leave_data = leave_type.get_allocation_data(employees, date_from)
            if leave_type.allows_negative:
                max_excess = leave_type.max_allowed_negative
                if all(leave.state in ("cancel", "refuse") for leave in leaves):
                    continue
                for employee in employees:
                    if not leave_data[employee][0][1]["max_leaves"]:
                        self._raise_missing_allocation()
                    if (
                        leave_data[employee]
                        and leave_data[employee][0][1]["virtual_remaining_leaves"]
                        < -max_excess
                    ):
                        raise ValidationError(
                            _("There is no valid allocation to cover that request.")
                        )
                continue

            previous_leave_data = leave_type.with_context(
                ignored_leave_ids=leaves.ids
            ).get_allocation_data(employees, date_from)
            for employee in employees:
                previous_emp_data = (
                    previous_leave_data[employee]
                    and previous_leave_data[employee][0][1]["virtual_excess_data"]
                )
                emp_data = (
                    leave_data[employee]
                    and leave_data[employee][0][1]["virtual_excess_data"]
                )
                if not leave_data[employee][0][1]["max_leaves"]:
                    self._raise_missing_allocation()
                if not previous_emp_data and not emp_data:
                    continue
                if previous_emp_data != emp_data and len(emp_data) >= len(
                    previous_emp_data
                ):
                    raise ValidationError(
                        _("There is no valid allocation to cover that request.")
                    )
        is_leave_user = self.env.user.has_group("hr_holidays.group_hr_holidays_user")
        if not is_leave_user and any(leave.has_mandatory_day for leave in self):
            raise ValidationError(
                _("You are not allowed to request time off on a Mandatory Day")
            )

    @api.depends(
        "tz",
        "date_from",
        "date_to",
        "employee_id",
        "holiday_status_id",
        "number_of_hours",
        "leave_type_request_unit",
        "number_of_days",
        "department_id",
    )
    @api.depends_context("short_name", "hide_employee_name", "group_by", "lang")
    def _compute_display_name(self):
        for leave in self:
            user_tz = timezone(leave.tz)
            date_from_utc = (
                leave.date_from and leave.date_from.astimezone(user_tz).date()
            )
            date_to_utc = leave.date_to and leave.date_to.astimezone(user_tz).date()
            time_off_type_display = leave.holiday_status_id.name
            if self.env.context.get("short_name"):
                short_leave_name = leave.name or time_off_type_display or _("Time Off")
                leave.display_name = _(
                    "%(name)s: %(duration)s",
                    name=short_leave_name,
                    duration=leave.duration_display,
                )
            else:
                target = leave.employee_id.name or ""
                display_date = format_date(self.env, date_from_utc) or ""
                if leave.number_of_days > 1 and date_from_utc and date_to_utc:
                    display_date += _(
                        " to %(date_to_utc)s",
                        date_to_utc=format_date(self.env, date_to_utc) or "",
                    )
                if not target or (
                    self.env.context.get("hide_employee_name")
                    and "employee_id" in self.env.context.get("group_by", [])
                ):
                    leave.display_name = _(
                        "%(leave_type)s: %(duration)s (%(start)s)",
                        leave_type=time_off_type_display,
                        duration=leave.duration_display,
                        start=display_date,
                    )
                elif not time_off_type_display:
                    leave.display_name = _(
                        "%(person)s: %(duration)s (%(start)s)",
                        person=target,
                        duration=leave.duration_display,
                        start=display_date,
                    )
                else:
                    leave.display_name = _(
                        "%(person)s on %(leave_type)s: %(duration)s (%(start)s)",
                        person=target,
                        leave_type=time_off_type_display,
                        duration=leave.duration_display,
                        start=display_date,
                    )

    def _check_double_validation_rules(self, employees, state):
        if self.env.user.has_group("hr_holidays.group_hr_holidays_manager"):
            return

        is_leave_user = self.env.user.has_group("hr_holidays.group_hr_holidays_user")
        if state == "validate1":
            employees = employees.filtered(
                lambda employee: employee.leave_manager_id != self.env.user
            )
            if employees and not is_leave_user:
                raise AccessError(
                    _(
                        "You cannot first approve a time off for %s, because you are not his time off manager",
                        employees[0].name,
                    )
                )
        elif state == "validate" and not is_leave_user:
            raise AccessError(
                _(
                    "You don't have the rights to apply second approval on a time off request"
                )
            )

    def _get_consumption_signature(self):
        return {
            leave.id: tuple(leave[fname] for fname in CONSUMPTION_FIELDS)
            for leave in self
        }

    def _invalidate_allocation_computes(self):
        self.env["hr.leave.allocation"].invalidate_model(["leaves_taken", "max_leaves"])

    @api.model_create_multi
    def create(self, vals_list):
        if any(not vals.get("employee_id") for vals in vals_list):
            raise UserError(
                _(
                    "There is no employee set on the time off. Please make sure you're logged in the correct company."
                )
            )
        holidays = super(
            HrLeave, self.with_context(mail_create_nosubscribe=True)
        ).create(vals_list)
        if not self.env.context.get("leave_fast_create"):
            for holiday in holidays.filtered(
                lambda leave: leave.validation_type == "both"
            ):
                holiday._check_double_validation_rules(
                    holiday.employee_id, holiday.state
                )
        holidays._check_validity()
        self._invalidate_allocation_computes()

        for holiday in holidays:
            if not self.env.context.get("leave_fast_create"):
                holiday_sudo = holiday.sudo()
                holiday_sudo.add_follower(holiday.employee_id.id)
                if holiday.validation_type == "manager":
                    holiday_sudo.message_subscribe(
                        partner_ids=holiday.employee_id.leave_manager_id.partner_id.ids
                    )
                if holiday.validation_type == "no_validation":
                    holiday_sudo.action_approve()
                    holiday_sudo.message_subscribe(
                        partner_ids=holiday._get_responsible_for_approval().partner_id.ids
                    )
                    holiday_sudo.message_post(
                        body=_("The time off has been automatically approved"),
                        subtype_xmlid="mail.mt_comment",
                    )
                elif not self.env.context.get("import_file"):
                    holiday_sudo.activity_update()
        return holidays

    def write(self, vals):
        values = vals
        is_officer = (
            self.env.user.has_group("hr_holidays.group_hr_holidays_user")
            or self.env.is_superuser()
        )
        if not is_officer and values.keys() - {
            "attachment_ids",
            "supported_attachment_ids",
            "message_main_attachment_id",
        }:
            if any(
                hol.date_from
                and hol.date_from.date() < fields.Date.today()
                and hol.employee_id.leave_manager_id != self.env.user
                and hol.state != "confirm"
                for hol in self
            ):
                raise UserError(
                    _(
                        "You must have manager rights to modify/validate a time off that already begun"
                    )
                )
            if any(leave.state == "cancel" for leave in self):
                raise UserError(_("Only a manager can modify a canceled leave."))

        if "state" in values and values["state"] != "validate":
            validated_leaves = self.filtered(lambda l: l.state == "validate")
            validated_leaves._remove_resource_leave()

        employee_id = values.get("employee_id", False)
        if not self.env.context.get("leave_fast_create"):
            if values.get("state"):
                self._check_approval_update(values["state"])
                if any(holiday.validation_type == "both" for holiday in self):
                    if values.get("employee_id"):
                        employees = self.env["hr.employee"].browse(
                            values.get("employee_id")
                        )
                    else:
                        employees = self.mapped("employee_id")
                    self._check_double_validation_rules(employees, values["state"])
            if "date_from" in values or "date_to" in values:
                values = dict(values)
                if "date_from" in values:
                    values["request_date_from"] = Date.to_date(values["date_from"])
                if "date_to" in values:
                    values["request_date_to"] = Date.to_date(values["date_to"])
        consumption_before = self._get_consumption_signature()
        result = super().write(values)
        if (
            not VALIDITY_TRIGGER_FIELDS.isdisjoint(values)
            or self._get_consumption_signature() != consumption_before
        ):
            if values.get("state") not in ("refuse", "cancel"):
                self._check_validity()
            self._invalidate_allocation_computes()
        if employee_id and not self.env.context.get("leave_fast_create"):
            self.add_follower(employee_id)

        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_if_correct_states(self):
        error_message = self.env._(
            "Oops! %(state)s Time-Off requests can only be deleted by Administrators."
        )
        state_description_values = {
            elem[0]: elem[1]
            for elem in self._fields["state"]._description_selection(self.env)
        }
        today = fields.Date.today()

        if not self.env.user.has_group("hr_holidays.group_hr_holidays_user"):
            for hol in self:
                if hol.state not in ["confirm", "validate1", "cancel"]:
                    raise UserError(
                        error_message
                        % {"state": state_description_values.get(hol.state)}
                    )
                if hol.date_from and hol.date_from.date() < today:
                    raise UserError(
                        _("You can't delete a time off request that is in the past.")
                    )
        elif not self.env.user.has_group("hr_holidays.group_hr_holidays_manager"):
            for holiday in self.filtered(
                lambda holiday: holiday.state not in ["cancel", "confirm"]
            ):
                raise UserError(
                    error_message
                    % {"state": state_description_values.get(holiday.state)}
                )

    def unlink(self):
        self.sudo()._post_leave_cancel()
        self._invalidate_allocation_computes()
        return super(HrLeave, self.with_context(leave_skip_date_check=True)).unlink()

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        if self.env.context.get("skip_copy_check"):
            return vals_list
        if all(leave.state in ["cancel", "refuse"] for leave in self):
            return vals_list
        raise UserError(_("A time off cannot be duplicated."))

    def _prepare_resource_leave_vals(self):
        self.check_singleton()
        return {
            "name": _("%s: Time Off", self.employee_id.name),
            "date_from": self.date_from,
            "holiday_id": self.id,
            "date_to": self.date_to,
            "resource_id": self.employee_id.resource_id.id,
            "calendar_id": self.resource_calendar_id.id,
            "time_type": self.holiday_status_id.time_type,
            "eligible_for_accrual_rate": self.holiday_status_id.eligible_for_accrual_rate,
        }

    def _create_resource_leave(self):
        vals_list = [leave._prepare_resource_leave_vals() for leave in self]
        return self.env["resource.calendar.leaves"].sudo().create(vals_list)

    def _remove_resource_leave(self):
        return (
            self.env["resource.calendar.leaves"]
            .sudo()
            .search([("holiday_id", "in", self.ids)])
            .unlink()
        )

    def _apply_leave_request(self):
        holidays = self.filtered("employee_id")
        holidays._create_resource_leave()
        meeting_holidays = holidays.filtered(
            lambda l: l.holiday_status_id.create_calendar_meeting
        )
        meetings = self.env["calendar.event"]
        if meeting_holidays:
            Meeting = self.env["calendar.event"]
            Meeting.check_access("create")
            meeting_values_for_user_id = (
                meeting_holidays._prepare_holidays_meeting_values()
            )
            for user_id, meeting_values in meeting_values_for_user_id.items():
                meetings += (
                    Meeting.with_user(user_id or self.env.uid)
                    .sudo()
                    .with_context(
                        clean_context(
                            {
                                **self.env.context,
                                "allowed_company_ids": [],
                                "no_mail_to_attendees": True,
                                "calendar_no_videocall": True,
                                "active_model": self._name,
                            }
                        )
                    )
                    .create(meeting_values)
                )
        Holiday = self.env["hr.leave"]
        for meeting in meetings:
            Holiday.browse(meeting.res_id).meeting_id = meeting

        for holiday in holidays:
            date_from_local = (
                holiday.date_from.replace(tzinfo=UTC)
                .astimezone(timezone(holiday.tz))
                .replace(tzinfo=None)
            )
            notify_partner_ids = holiday.employee_id.user_id.partner_id.ids
            holiday.message_post(
                body=_(
                    "Your %(leave_type)s planned on %(date)s has been accepted",
                    leave_type=holiday.holiday_status_id.display_name,
                    date=date_from_local,
                ),
                partner_ids=notify_partner_ids,
            )

    def _prepare_holidays_meeting_values(self):
        result = defaultdict(list)
        for holiday in self:
            user = holiday.user_id
            meeting_name = _(
                "%(employee)s on Time Off : %(duration)s",
                employee=holiday.employee_id.name,
                duration=holiday.duration_display,
            )
            allday_value = not holiday.request_unit_half or (
                holiday.request_date_from_period == "am"
                and holiday.request_date_to_period == "pm"
            )
            if holiday.leave_type_request_unit == "hour":
                allday_value = float_compare(holiday.number_of_days, 1.0, 1) >= 0

            if allday_value:
                leave_tz = timezone(holiday.tz) if holiday.tz else UTC
                start_value = (
                    holiday.date_from.replace(tzinfo=UTC)
                    .astimezone(leave_tz)
                    .replace(tzinfo=None)
                )
                stop_value = (
                    holiday.date_to.replace(tzinfo=UTC)
                    .astimezone(leave_tz)
                    .replace(tzinfo=None)
                )
            else:
                start_value = holiday.date_from
                stop_value = holiday.date_to

            meeting_values = {
                "name": meeting_name,
                "duration": holiday.number_of_days
                * (holiday.resource_calendar_id.hours_per_day or HOURS_PER_DAY),
                "description": holiday.notes,
                "user_id": user.id,
                "start": start_value,
                "stop": stop_value,
                "allday": allday_value,
                "privacy": "confidential",
                "event_tz": user.tz,
                "activity_ids": [Command.clear()],
                "res_id": holiday.id,
            }
            partner_id = (user and user.partner_id) or (
                holiday.employee_id and holiday.employee_id.partner_id
            )
            if partner_id:
                meeting_values["partner_ids"] = [Command.link(partner_id.id)]
            result[user.id].append(meeting_values)
        return result

    def action_cancel(self):
        self.check_singleton()

        return {
            "name": _("Cancel Time Off"),
            "type": "ir.actions.act_window",
            "target": "new",
            "res_model": "hr.holidays.cancel.leave",
            "view_mode": "form",
            "views": [[False, "form"]],
            "context": {
                "default_leave_id": self.id,
                "dialog_size": "medium",
            },
        }

    def action_approve(self, check_state=True):
        current_employee = self.env.user.employee_id
        leave_to_approve = self.env["hr.leave"]
        leave_to_validate = self.env["hr.leave"]
        for leave in self:
            if (check_state and leave.can_validate) or (
                not check_state and leave.validation_type != "both"
            ):
                leave_to_validate += leave
            elif (check_state and leave.can_approve) or (
                not check_state and leave.validation_type == "both"
            ):
                leave_to_approve += leave
            else:
                raise UserError(self.env._("You cannot approve this leave."))
        leave_to_approve.write(
            {"state": "validate1", "first_approver_id": current_employee.id}
        )
        leave_to_validate._action_validate(check_state)
        if not self.env.context.get("leave_fast_create"):
            leave_to_approve.activity_update()
        return True

    def action_back_to_approval(self):
        self.filtered(lambda l: l.can_back_to_approve)._move_validate_leave_to_confirm()
        return True

    def _move_validate_leave_to_confirm(self):
        self.write({"state": "confirm"})
        self.activity_update()
        self._post_leave_cancel()

    def _filtered_on_public_holiday(self):
        return self.filtered(lambda l: l.employee_id and not l.number_of_days)

    def _split_leaves(self, split_date_from, split_date_to=False):
        new_leaves_vals = []
        if not split_date_to:
            split_date_to = split_date_from

        multi_day_leaves = self.filtered(
            lambda l: (
                l.request_date_from < split_date_from
                or l.request_date_to >= split_date_to
            )
        )
        for leave in multi_day_leaves:
            new_leave_vals = []
            target_leave_vals = []
            if leave.request_date_from < split_date_from:
                new_leave_vals.append(
                    leave.with_context(skip_copy_check=True).copy_data(
                        {
                            "request_date_to": split_date_from + timedelta(days=-1),
                            "state": leave.state,
                        }
                    )[0]
                )

            if leave.request_date_to >= split_date_to:
                new_leave_vals.append(
                    leave.with_context(skip_copy_check=True).copy_data(
                        {"request_date_from": split_date_to, "state": leave.state}
                    )[0]
                )

            for leave_vals in new_leave_vals:
                new_leave = self.env["hr.leave"].new(leave_vals)
                new_leave._compute_date_from_to()
                if new_leave.date_from < new_leave.date_to:
                    target_leave_vals.append(leave_vals)

            if target_leave_vals:
                vals = target_leave_vals.pop(0)
                leave.with_context(leave_skip_state_check=True).write(
                    {
                        "request_date_from": vals["request_date_from"],
                        "request_date_to": vals["request_date_to"],
                    }
                )
                if target_leave_vals:
                    new_leaves_vals.extend(target_leave_vals)

        if not new_leaves_vals:
            return self.env["hr.leave"]
        return (
            self.env["hr.leave"]
            .with_context(
                tracking_disable=True,
                mail_activity_automation_skip=True,
                leave_fast_create=True,
                leave_skip_state_check=True,
            )
            .create(new_leaves_vals)
        )

    def _action_validate(self, check_state=True):
        current_employee = self.env.user.employee_id
        leaves = self._filtered_on_public_holiday()
        if check_state and any(not holiday.can_validate for holiday in self):
            raise UserError(_("You can't validate this leave."))
        if leaves:
            raise ValidationError(
                _(
                    "The following employees are not supposed to work during that period:\n %s"
                )
                % ",".join(leaves.mapped("employee_id.name"))
            )

        self.write({"state": "validate"})

        leaves_second_approver = self.env["hr.leave"]
        leaves_first_approver = self.env["hr.leave"]

        for leave in self:
            if leave.validation_type == "both":
                leaves_second_approver += leave
            else:
                leaves_first_approver += leave

        leaves_second_approver.write({"second_approver_id": current_employee.id})
        leaves_first_approver.write({"first_approver_id": current_employee.id})

        self._apply_leave_request()
        if not self.env.context.get("leave_fast_create"):
            self.filtered(
                lambda holiday: holiday.validation_type != "no_validation"
            ).activity_update()
        return True

    def action_refuse(self):
        current_employee = self.env.user.employee_id
        if any(
            holiday.state not in ["confirm", "validate", "validate1"]
            for holiday in self
        ):
            raise UserError(
                _(
                    "Time off request must be confirmed or validated in order to refuse it."
                )
            )

        self._notify_manager()
        validated_holidays = self.filtered(lambda hol: hol.state == "validate1")
        validated_holidays.write(
            {"state": "refuse", "first_approver_id": current_employee.id}
        )
        (self - validated_holidays).write(
            {"state": "refuse", "second_approver_id": current_employee.id}
        )
        self.mapped("meeting_id").write({"active": False})
        for holiday in self:
            if holiday.employee_id.user_id:
                holiday.message_post(
                    body=_(
                        "Your %(leave_type)s planned on %(date)s has been refused",
                        leave_type=holiday.holiday_status_id.display_name,
                        date=holiday.date_from,
                    ),
                    partner_ids=holiday.employee_id.user_id.partner_id.ids,
                )

        self.activity_update()
        return True

    def _notify_manager(self):
        leaves = self.filtered(
            lambda hol: (
                (
                    hol.validation_type == "both"
                    and hol.state in ["validate1", "validate"]
                )
                or (hol.validation_type == "manager" and hol.state == "validate")
            )
        )
        model_description = self.env["ir.model"]._get(self._name).name
        for holiday in leaves:
            responsible = holiday.employee_id.leave_manager_id.partner_id.ids
            if responsible:
                holiday.sudo().message_notify(
                    partner_ids=responsible,
                    model_description=model_description,
                    subject=_("Refused Time Off"),
                    body=_(
                        "%(holiday_name)s has been refused.",
                        holiday_name=holiday.display_name,
                    ),
                    email_layout_xmlid="mail.mail_notification_layout",
                    subtitles=[holiday.display_name],
                )

    def _action_user_cancel(self, reason=None):
        self.check_singleton()
        if not self.can_cancel:
            raise ValidationError(_("This time off cannot be cancelled."))

        self._force_cancel(reason, "mail.mt_note")

    def _force_cancel(
        self, reason=None, msg_subtype="mail.mt_comment", notify_responsibles=True
    ):
        leaves = self.browse() if self.env.context.get(MODULE_UNINSTALL_FLAG) else self
        if reason:
            model_description = self.env["ir.model"]._get(self._name).display_name
            for leave in leaves:
                body = self.env._(
                    "The time off request has been cancelled for the following reason:%(reason)s",
                    reason=Markup("<p>{reason}</p>").format(reason=reason),
                )
                leave.message_post(body=body, subtype_xmlid=msg_subtype)

                if not notify_responsibles:
                    continue

                responsibles = self.env["res.partner"]
                if (
                    leave.holiday_status_id.leave_validation_type == "manager"
                    and leave.state == "validate"
                ) or (
                    leave.holiday_status_id.leave_validation_type == "both"
                    and leave.state == "validate1"
                ):
                    responsibles = leave.employee_id.leave_manager_id.partner_id
                elif (
                    leave.holiday_status_id.leave_validation_type == "hr"
                    and leave.state == "validate"
                ):
                    responsibles = leave.holiday_status_id.responsible_ids.partner_id
                elif (
                    leave.holiday_status_id.leave_validation_type == "both"
                    and leave.state == "validate"
                ):
                    responsibles = leave.employee_id.leave_manager_id.partner_id
                    responsibles |= leave.holiday_status_id.responsible_ids.partner_id

                if responsibles:
                    body = self.env._(
                        "%(leave_name)s has been cancelled for the following reason: %(reason)s",
                        leave_name=leave.display_name,
                        reason=Markup("<blockquote>{reason}</blockquote>").format(
                            reason=reason
                        ),
                    )
                    leave.message_notify(
                        partner_ids=responsibles.ids,
                        model_description=model_description,
                        subject=self.env._("Cancelled Time Off"),
                        body=body,
                        email_layout_xmlid="mail.mail_notification_layout",
                        subtitles=[leave.display_name],
                    )
        leave_sudo = self.sudo()
        leave_sudo.state = "cancel"
        leave_sudo.activity_update()
        leave_sudo._post_leave_cancel()

    def _post_leave_cancel(self):
        self.meeting_id.active = False
        self._remove_resource_leave()

    def action_documents(self):
        domain = [("id", "in", self.attachment_ids.ids)]
        return {
            "name": _("Supporting Documents"),
            "type": "ir.actions.act_window",
            "res_model": "ir.attachment",
            "context": {"create": False},
            "view_mode": "kanban",
            "domain": domain,
        }

    def _get_next_states_by_state(self):
        self.check_singleton()
        state_result = {
            "confirm": set(),
            "validate1": set(),
            "validate": set(),
            "refuse": set(),
            "cancel": set(),
        }
        validation_type = self.validation_type

        user_employees = self.env.user.employee_ids
        is_own_leave = self.employee_id in user_employees
        is_in_past = self.date_from and self.date_from.date() < fields.Date.today()

        is_officer = self.env.user.has_group("hr_holidays.group_hr_holidays_user")
        is_time_off_manager = self.employee_id.leave_manager_id == self.env.user

        if is_own_leave and (not is_in_past or is_officer):
            state_result["validate1"].add("cancel")
            state_result["validate"].add("cancel")
            state_result["refuse"].add("cancel")

        if is_officer:
            if validation_type == "both":
                state_result["confirm"].add("validate1")
                state_result["refuse"].add("validate1")
                state_result["cancel"].add("validate1")
            state_result["confirm"].update({"validate", "refuse"})
            state_result["validate1"].update({"confirm", "validate", "refuse"})
            state_result["validate"].update({"confirm", "refuse"})
            state_result["refuse"].update({"confirm", "validate"})
            state_result["cancel"].update({"confirm", "validate", "refuse"})
        elif is_time_off_manager:
            if validation_type != "hr":
                state_result["confirm"].add("refuse")
                state_result["validate"].add("refuse")
            if validation_type == "both":
                state_result["confirm"].add("validate1")
                state_result["validate1"].add("refuse")
            elif validation_type == "manager":
                state_result["confirm"].add("validate")
                state_result["refuse"].add("validate")

        return state_result

    def _get_approval_precheck_error(self, state):
        if state == "validate1" and self.validation_type != "both":
            return self.env._(
                "Not possible state. State Approve is only used for leave needed 2 approvals"
            )
        if self.state == "cancel":
            return self.env._("A cancelled leave cannot be modified.")
        return ""

    def _approval_update_needs_write_access(self, state):
        return state != "cancel"

    def _get_approval_transition_error(self, state, is_time_off_manager):
        if state == "cancel":
            return self.env._(
                "You can only cancel your own leave. You can cancel a leave only if this leave \
is approved, validated or refused."
            )
        if state == "confirm":
            return self.env._(
                "You can't reset a leave. Cancel/delete this one and create an other"
            )
        if state == "validate1":
            if not is_time_off_manager:
                return self.env._(
                    "Only a Time Off Officer/Manager can approve a leave."
                )
            return self.env._("You can't approve a validated leave.")
        if state == "validate":
            if not is_time_off_manager:
                return self.env._(
                    "Only a Time Off Officer/Manager can validate a leave."
                )
            if self.state == "refuse":
                return self.env._("You can't approve this refused leave.")
            return self.env._(
                "You can only validate a leave with validation by Time Off Manager."
            )
        if state == "refuse":
            if not is_time_off_manager:
                return self.env._("Only a Time Off Officer/Manager can refuse a leave.")
            return self.env._(
                "You can't refuse a leave with validation by Time Off Officer."
            )
        return ""

    def _get_approval_category_xmlid(self):
        return "hr_holidays.approval_category_leave"

    def _get_approval_backfill_decider(self):
        return self.first_approver_id.user_id

    def _get_approval_sync_kinds(self):
        return {
            "confirm": "pending",
            "validate1": "progress",
            "validate": "approved",
            "refuse": "refused",
            "cancel": "cancelled",
        }

    def _get_approval_outcome_states(self):
        return {
            "progress": "validate1",
            "approved": "validate",
            "refused": "refuse",
            "cancelled": "cancel",
        }

    def _apply_approval_state(self, state):
        self.check_singleton()
        if state == "validate1":
            self.write(
                {
                    "state": "validate1",
                    "first_approver_id": self.env.user.employee_id.id,
                }
            )
        elif state == "validate":
            self._action_validate(check_state=False)
        elif state == "refuse":
            self.action_refuse()
        elif state == "cancel":
            self._force_cancel()

    def _get_approval_activity_xmlids(self):
        return (
            "hr_holidays.mail_act_leave_approval",
            "hr_holidays.mail_act_leave_second_approval",
        )

    def _get_approval_activity_note(self):
        if self.state == "confirm":
            return _(
                "New %(leave_type)s Request created by %(user)s",
                leave_type=self.holiday_status_id.name,
                user=self.create_uid.name,
            )
        return _(
            "Second approval request for %(leave_type)s",
            leave_type=self.holiday_status_id.name,
        )

    def _get_approval_activity_deadline(self, activity_type):
        today = fields.Date.today()
        if not self.date_from:
            return today
        return max((self.date_from - activity_type._get_delay_delta()).date(), today)

    def _get_approval_sudo_subscribe_states(self):
        return ("validate", "validate1")

    def _get_validated_notif_subtype(self):
        return self.holiday_status_id.leave_notif_subtype_id or self.env.ref(
            "hr_holidays.mt_leave"
        )

    def _notify_change(self, message, subtype_xmlid="mail.mt_note"):
        for leave in self:
            leave.message_post(body=message, subtype_xmlid=subtype_xmlid)

            recipient = None
            if leave.user_id:
                recipient = leave.user_id.partner_id.id
            elif leave.employee_id:
                recipient = leave.employee_id.partner_id.id

            if recipient:
                self.env["mixin.mail.thread"].sudo().message_notify(
                    body=message,
                    partner_ids=[recipient],
                    subject=_("Your Time Off"),
                )

    @api.model
    def get_unusual_days(self, date_from, date_to=None):
        employee_id = self.env.context.get("employee_id", False)
        employee = (
            self.env["hr.employee"].browse(employee_id)
            if employee_id
            else self.env.user.employee_id
        )
        return employee.sudo(False)._get_unusual_days(date_from, date_to)

    def _to_utc(self, date, hour, resource):
        hour = float_to_time(float(hour))
        holiday_tz = timezone(resource.tz or self.env.user.tz or "UTC")
        return (
            datetime.combine(date, hour)
            .replace(tzinfo=holiday_tz)
            .astimezone(UTC)
            .replace(tzinfo=None)
        )

    def _get_hour_from_to(self, request_date_from, request_date_to, day_period=None):
        calendar = self.resource_calendar_id
        if not calendar:
            return (0, 24)
        calendar.check_singleton()

        hour_from, _ = calendar._get_hours_for_date(request_date_from, day_period)
        _, hour_to = calendar._get_hours_for_date(request_date_to, day_period)

        return (hour_from, hour_to)

    @api.model
    def _cancel_invalid_leaves(self):
        inspected_date = fields.Date.today() + timedelta(days=31)
        start_datetime = datetime.combine(fields.Date.today(), datetime.min.time())
        end_datetime = datetime.combine(inspected_date, datetime.max.time())
        concerned_leaves = self.search(
            [
                ("date_from", ">=", start_datetime),
                ("date_from", "<=", end_datetime),
                ("state", "in", ["confirm", "validate1", "validate"]),
            ],
            order="date_from desc",
        )
        accrual_allocations = self.env["hr.leave.allocation"].search(
            [
                ("employee_id", "in", concerned_leaves.employee_id.ids),
                ("holiday_status_id", "in", concerned_leaves.holiday_status_id.ids),
                ("allocation_type", "=", "accrual"),
                ("date_from", "<=", end_datetime),
                "|",
                ("date_to", ">=", start_datetime),
                ("date_to", "=", False),
            ]
        )
        concerned_leaves = concerned_leaves.filtered(
            lambda leave: (
                leave.holiday_status_id in accrual_allocations.holiday_status_id
            )
        )
        reason = _("the accrued amount is insufficient for that duration.")
        leaves_by_type_and_date = defaultdict(lambda: self.env["hr.leave"])
        for leave in concerned_leaves:
            leaves_by_type_and_date[
                (leave.holiday_status_id, leave.date_from.date())
            ] |= leave
        for (leave_type, date), leaves in sorted(
            leaves_by_type_and_date.items(), key=lambda item: item[0][1], reverse=True
        ):
            leave_type_data = leave_type.get_allocation_data(leaves.employee_id, date)
            excess_limit = (
                leave_type.max_allowed_negative if leave_type.allows_negative else 0
            )
            for leave in leaves:
                employee_data = leave_type_data[leave.employee_id][0][1]
                if (
                    not employee_data["max_leaves"]
                    or employee_data["total_virtual_excess"] > excess_limit
                ):
                    leave._force_cancel(reason, "mail.mt_note")
