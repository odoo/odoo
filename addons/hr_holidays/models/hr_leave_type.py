import logging
from collections import defaultdict
from datetime import date, datetime

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.libs.numbers import float_round
from odoo.tools import DOMAIN_PREDICATES, SET_DOMAIN_OPERATORS, format_date
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class HrLeaveType(models.Model):
    _name = "hr.leave.type"
    _description = "Time Off Type"
    _order = "sequence"
    _search_visibility_fields = ()

    @api.model
    def _model_sorting_key(self, leave_type):
        remaining = leave_type.virtual_remaining_leaves > 0
        taken = leave_type.leaves_taken > 0
        return (
            -1 * leave_type.sequence,
            not leave_type.employee_requests and remaining,
            leave_type.employee_requests and remaining,
            taken,
        )

    name = fields.Char(
        string="Time Off Type",
        translate=True,
        required=True,
    )
    sequence = fields.Integer(
        default=100,
        help="The type with the smallest sequence is the default value in time off request",
    )
    create_calendar_meeting = fields.Boolean(
        string="Display Time Off in Calendar",
        default=True,
    )
    color = fields.Integer(
        help="The color selected here will be used in every screen with the time off type."
    )
    icon_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="Cover Image",
        domain="[('res_model', '=', 'hr.leave.type'), ('res_field', '=', 'icon_id')]",
    )
    active = fields.Boolean(
        default=True,
        help="If the active field is set to false, it will allow you to hide the time off type without removing it.",
    )
    hide_on_dashboard = fields.Boolean(
        default=False,
        help="Non-visible allocations can still be selected when taking a leave, but will simply not be displayed on the leave dashboard.",
    )

    max_leaves = fields.Float(
        string="Maximum Allowed",
        compute="_compute_leaves",
        search="_search_max_leaves",
        help="This value is given by the sum of all time off requests with a positive value.",
    )
    leaves_taken = fields.Float(
        string="Time off Already Taken",
        compute="_compute_leaves",
        help="This value is given by the sum of all time off requests with a negative value.",
    )
    virtual_remaining_leaves = fields.Float(
        string="Virtual Remaining Time Off",
        compute="_compute_leaves",
        search="_search_virtual_remaining_leaves",
        help="Maximum Time Off Allowed - Time Off Already Taken - Time Off Waiting Approval",
    )

    allocation_count = fields.Integer(
        string="Allocations",
        compute="_compute_allocation_count",
    )
    group_days_leave = fields.Float(
        string="Group Time Off",
        compute="_compute_group_days_leave",
    )
    is_used = fields.Boolean(compute="_compute_is_used")
    company_id = fields.Many2one(
        comodel_name="res.company",
        domain=lambda self: [("id", "in", self.env.companies.ids)],
    )
    country_id = fields.Many2one(
        comodel_name="res.country",
        compute="_compute_country_id",
        default=lambda self: self.env.company.country_id,
        store=True,
        domain=lambda self: [("id", "in", self.env.companies.country_id.ids)],
    )
    country_code = fields.Char(
        related="country_id.code",
        depends=["country_id"],
        readonly=True,
    )
    responsible_ids = fields.Many2many(
        comodel_name="res.users",
        relation="hr_leave_type_res_users_rel",
        column1="hr_leave_type_id",
        column2="res_users_id",
        string="Notify HR",
        domain=lambda self: [
            (
                "all_group_ids",
                "in",
                self.env.ref("hr_holidays.group_hr_holidays_user").id,
            ),
            ("share", "=", False),
            ("company_ids", "in", self.env.company.id),
        ],
        help="Choose the Time Off Officers who will be notified to approve allocation or Time Off Request. If empty, nobody will be notified",
    )
    leave_validation_type = fields.Selection(
        selection=[
            ("no_validation", "None needed"),
            ("hr", "By Time Off Officer"),
            ("manager", "By Employee's Approver"),
            ("both", "By Employee's Approver and Time Off Officer"),
        ],
        string="Time Off Validation",
        default="hr",
    )
    requires_allocation = fields.Boolean(
        string="Requires allocation",
        default=True,
        required=True,
    )
    employee_requests = fields.Boolean(
        string="Allow Employee Requests",
        default=False,
        required=True,
        help="""Extra Days Requests Allowed: User can request an allocation for himself.\n
        Not Allowed: User cannot request an allocation.""",
    )
    allocation_validation_type = fields.Selection(
        selection=[
            ("no_validation", "None needed"),
            ("hr", "By Time Off Officer"),
            ("manager", "By Employee's Approver"),
            ("both", "By Employee's Approver and Time Off Officer"),
        ],
        string="Approval",
        default="hr",
        help="""Select the level of approval needed in case of request by employee
            #     - No validation needed: The employee's request is automatically approved.
            #     - Approved by Time Off Officer: The employee's request need to be manually approved
            #       by the Time Off Officer, Employee's Approver or both.""",
    )

    has_valid_allocation = fields.Boolean(
        compute="_compute_has_valid_allocation",
        search="_search_has_valid_allocation",
        help="This indicates if it is still possible to use this type of leave",
    )
    time_type_is_work = fields.Boolean(
        related="time_type_id.is_work",
        string="Counts as Working Time",
        help="Read by the form: a view expression cannot walk to the kind's own field.",
    )
    time_type_id = fields.Many2one(
        comodel_name="resource.time.type",
        string="Kind of Time Off",
        default=lambda self: self.env["resource.time.type"]._get_leave_type(),
        required=True,
        ondelete="restrict",
        help="What time off of this type counts as in the working schedule. An absence is subtracted from working time; a kind that counts as working time (a training, say) is not, and an accrual plan's rate reads the same distinction.",
    )
    request_unit = fields.Selection(
        selection=[("day", "Day"), ("half_day", "Half-Day"), ("hour", "Hours")],
        string="Duration Type",
        default="day",
        required=True,
    )
    unpaid = fields.Boolean(
        string="Is Unpaid",
        default=False,
    )
    include_public_holidays_in_duration = fields.Boolean(
        string="Ignore Public Holidays",
        default=False,
        help="Public holidays should be counted in the leave duration when applying for leaves",
    )
    leave_notif_subtype_id = fields.Many2one(
        comodel_name="mail.message.subtype",
        string="Time Off Notification Subtype",
        default=lambda self: self.env.ref(
            "hr_holidays.mt_leave", raise_if_not_found=False
        ),
    )
    allocation_notif_subtype_id = fields.Many2one(
        comodel_name="mail.message.subtype",
        string="Allocation Notification Subtype",
        default=lambda self: self.env.ref(
            "hr_holidays.mt_leave_allocation", raise_if_not_found=False
        ),
    )
    support_document = fields.Boolean(string="Supporting Document")
    allow_request_on_top = fields.Boolean(
        string="Allow Request on Top",
        default=False,
        help="If checked, users can request another leave on top of the ones of this type.",
    )
    eligible_for_accrual_rate = fields.Boolean(
        string="Eligible for Accrual Rate",
        compute="_compute_eligible_for_accrual_rate",
        store=True,
        readonly=False,
        help="If checked, this time off type will be taken into account for accruals computation.",
    )
    accruals_ids = fields.One2many(
        comodel_name="hr.leave.accrual.plan",
        inverse_name="time_off_type_id",
    )
    accrual_count = fields.Float(
        string="Accruals count",
        compute="_compute_accrual_count",
    )
    allows_negative = fields.Boolean(
        string="Allow Negative Cap",
        help="If checked, users request can exceed the allocated days and balance can go in negative.",
    )
    max_allowed_negative = fields.Integer(
        string="Maximum Excess Amount",
        help="Define the maximum level of negative days this kind of time off can reach. Value must be at least 1.",
    )

    _check_negative = models.Constraint(
        "CHECK(NOT allows_negative OR max_allowed_negative > 0)",
        "The maximum excess amount should be greater than 0. If you want to set 0, disable the negative cap instead.",
    )

    @api.model
    def _search_has_valid_allocation(self, operator, value):
        if operator not in ("in", "not in"):
            return NotImplemented

        if {"default_date_from", "default_date_to", "tz"} <= set(self.env.context):
            default_date_from_dt = fields.Datetime.to_datetime(
                self.env.context.get("default_date_from")
            )
            default_date_to_dt = fields.Datetime.to_datetime(
                self.env.context.get("default_date_to")
            )

            date_from = fields.Date.context_today(self, default_date_from_dt)
            date_to = fields.Date.context_today(self, default_date_to_dt)

        else:
            current_year = fields.Date.today().year
            date_from = date(current_year, 1, 1)
            date_to = date(current_year, 12, 31)

        employee_id = (
            self.env.context.get(
                "default_employee_id", self.env.context.get("employee_id")
            )
            or self.env.user.employee_id.id
        )

        leave_types = (
            self.env["hr.leave.allocation"]
            .search(
                [
                    ("employee_id", "=", employee_id),
                    ("state", "=", "validate"),
                    ("date_from", "<=", date_to),
                    "|",
                    ("date_to", ">=", date_from),
                    ("date_to", "=", False),
                ]
            )
            .holiday_status_id
        )

        return [("id", operator, leave_types.ids)]

    @api.constrains("allow_request_on_top")
    def _check_allow_request_on_top(self):
        for leave in self:
            if not leave.time_type_id.is_work and leave.allow_request_on_top:
                raise ValidationError(
                    self.env._(
                        "You cannot allow requests on top of leaves of type 'Absence'."
                    )
                )

    @api.constrains("eligible_for_accrual_rate")
    def _check_eligible_for_accrual_rate(self):
        for leave in self:
            if leave.time_type_id.is_work and not leave.eligible_for_accrual_rate:
                raise ValidationError(
                    self.env._(
                        "leaves of type 'Worked Time' should be always eligible for accrual rate."
                    )
                )

    @api.model
    def _get_domain_current_year(self):
        year = fields.Date.context_today(self).year
        return [
            ("holiday_status_id", "in", self.ids),
            ("date_from", ">=", datetime(year, 1, 1)),
            ("date_from", "<=", datetime(year, 12, 31, 23, 59, 59)),
            ("state", "in", ("validate", "validate1", "confirm")),
        ]

    @api.constrains("include_public_holidays_in_duration")
    def _check_overlapping_public_holidays(self):
        leaves = self.env["hr.leave"].search(self._get_domain_current_year())
        if not leaves:
            return

        companies = self.company_id | self.env.company
        public_holiday_leaves = self.env["resource.schedule.exception"]
        public_holidays = public_holiday_leaves.search(
            public_holiday_leaves._get_domain_public_holidays(
                min(leaves.mapped("date_from")),
                max(leaves.mapped("date_to")),
                companies=companies,
            )
        )
        if not public_holidays:
            return

        holiday_spans = [
            (holiday.date_from.date(), holiday.date_to.date())
            for holiday in public_holidays
        ]
        overlaps = any(
            leave.date_from.date() <= holiday_to
            and leave.date_to.date() >= holiday_from
            for leave in leaves
            for holiday_from, holiday_to in holiday_spans
        )
        if overlaps:
            raise ValidationError(
                _(
                    "You cannot modify the 'Public Holiday Included' setting since one or more leaves for that \
                        time off type are overlapping with public holidays, meaning that the balance of those employees would be affected by this change."
                )
            )

    @api.depends("requires_allocation", "max_leaves", "virtual_remaining_leaves")
    @api.depends_context(
        "uid",
        "default_date_from",
        "default_date_to",
        "default_employee_id",
        "employee_id",
    )
    def _compute_has_valid_allocation(self):
        current_year = fields.Date.today().year
        default_date_from = date(current_year, 1, 1)
        default_date_to = date(current_year, 12, 31)
        date_from = self.env.context.get("default_date_from", default_date_from)
        date_to = self.env.context.get("default_date_to", default_date_to)
        employee_id = self.env.context.get(
            "default_employee_id",
            self.env.context.get("employee_id", self.env.user.employee_id.id),
        )
        allocation_by_leave_type = dict(
            self.env["hr.leave.allocation"]._read_group(
                domain=Domain(
                    [
                        (
                            "holiday_status_id",
                            "in",
                            self.filtered(
                                lambda leave_type: leave_type.requires_allocation
                            ).ids,
                        ),
                        ("employee_id", "=", employee_id),
                        ("date_from", "<=", date_from),
                        "|",
                        ("date_to", ">=", date_to),
                        ("date_to", "=", False),
                    ]
                ),
                groupby=["holiday_status_id"],
                aggregates=["id:recordset"],
            )
        )
        for leave_type in self:
            if leave_type.requires_allocation:
                allocations = allocation_by_leave_type.get(
                    leave_type, self.env["hr.leave.allocation"]
                )
                allowed_excess = (
                    leave_type.max_allowed_negative if leave_type.allows_negative else 0
                )
                allocations = allocations.filtered(
                    lambda alloc, allowed_excess=allowed_excess: (
                        alloc.allocation_type == "accrual"
                        or (
                            alloc.max_leaves > 0
                            and alloc.virtual_remaining_leaves > -allowed_excess
                        )
                    )
                )
                leave_type.has_valid_allocation = bool(allocations)
            else:
                leave_type.has_valid_allocation = True

    def _load_records_write(self, values):
        if (
            "requires_allocation" in values
            and self.requires_allocation == values["requires_allocation"]
        ):
            values.pop("requires_allocation")
        return super()._load_records_write(values)

    @api.constrains("requires_allocation")
    def check_allocation_requirement_edit_validity(self):
        if not self.env.context.get("install_mode") and self.env[
            "hr.leave"
        ].search_count([("holiday_status_id", "in", self.ids)], limit=1):
            raise UserError(
                _(
                    "The allocation requirement of a time off type cannot be changed once leaves of that type have been taken. You should create a new time off type instead."
                )
            )

    @api.depends("company_id")
    def _compute_country_id(self):
        for holiday_type in self:
            if holiday_type.company_id:
                holiday_type.country_id = holiday_type.company_id.country_id

    def _search_balance(self, field_name, operator, value, always_matches=None):
        """Search a balance field by the value its compute would report.

        Every balance on this model is a view of ``get_allocation_data`` for
        the employee in context, so the only spelling of the search that can
        agree with the compute is to run the compute. An allocation-level
        aggregate cannot: it is in days where the field is in hours, and it
        misses every type that has no allocation row at all -- including the
        ones whose balance is legitimately zero.
        """
        op = DOMAIN_PREDICATES.get(operator)
        if not op:
            return NotImplemented
        if operator not in SET_DOMAIN_OPERATORS:
            value = float(value)
        leave_types = self.search([])
        matching = leave_types.filtered(
            lambda leave_type: (
                (always_matches is not None and always_matches(leave_type))
                or op(leave_type[field_name], value)
            )
        )
        _debug.logic(
            "balance_search",
            field=field_name,
            operator=operator,
            value=value,
            matched=len(matching),
            candidates=len(leave_types),
        )
        return [("id", "in", matching.ids)]

    def _search_max_leaves(self, operator, value):
        return self._search_balance("max_leaves", operator, value)

    def _search_virtual_remaining_leaves(self, operator, value):
        return self._search_balance(
            "virtual_remaining_leaves",
            operator,
            value,
            always_matches=lambda leave_type: not leave_type.requires_allocation,
        )

    @api.depends_context(
        "employee_id", "default_employee_id", "leave_date_from", "default_date_from"
    )
    def _compute_leaves(self):
        employee = self.env["hr.employee"]._get_contextual_employee()
        target_date = self.env.context.get("leave_date_from") or self.env.context.get(
            "default_date_from"
        )
        data_days = self.get_allocation_data(employee, target_date)[employee]
        data_by_leave_type_id = {item[3]: item[1] for item in data_days}
        for holiday_status in self:
            data = data_by_leave_type_id.get(holiday_status.id, {})
            holiday_status.max_leaves = data.get("max_leaves", 0)
            holiday_status.leaves_taken = data.get("leaves_taken", 0)
            holiday_status.virtual_remaining_leaves = data.get(
                "virtual_remaining_leaves", 0
            )

    def _compute_allocation_count(self):
        grouped_res = self.env["hr.leave.allocation"]._read_group(
            self._get_domain_current_year(),
            ["holiday_status_id"],
            ["__count"],
        )
        grouped_dict = {
            holiday_status.id: count for holiday_status, count in grouped_res
        }
        for leave_type in self:
            leave_type.allocation_count = grouped_dict.get(leave_type.id, 0)

    def _compute_group_days_leave(self):
        grouped_res = self.env["hr.leave"]._read_group(
            self._get_domain_current_year(),
            ["holiday_status_id"],
            ["__count"],
        )
        grouped_dict = {
            holiday_status.id: count for holiday_status, count in grouped_res
        }
        for leave_type in self:
            leave_type.group_days_leave = grouped_dict.get(leave_type.id, 0)

    def _compute_accrual_count(self):
        accrual_allocations = self.env["hr.leave.accrual.plan"]._read_group(
            [("time_off_type_id", "in", self.ids)], ["time_off_type_id"], ["__count"]
        )
        mapped_data = {
            time_off_type.id: count for time_off_type, count in accrual_allocations
        }
        for leave_type in self:
            leave_type.accrual_count = mapped_data.get(leave_type.id, 0)

    def _compute_is_used(self):
        leaves_count = self._leaves_count_by_leave_type_id()
        allocations_count = self._allocations_count_by_leave_type_id()
        for leave_type in self:
            leave_type.is_used = leaves_count.get(
                leave_type.id, 0
            ) or allocations_count.get(leave_type.id, 0)

    def _leaves_count_by_leave_type_id(self):
        leave_domain = [
            ("holiday_status_id", "in", self.ids),
        ]
        leaves_count = self.env["hr.leave"]._read_group(
            leave_domain,
            ["holiday_status_id"],
            ["__count"],
        )
        return {holiday_status.id: count for holiday_status, count in leaves_count}

    def _allocations_count_by_leave_type_id(self):
        allocation_domain = [
            ("holiday_status_id", "in", self.ids),
        ]
        allocations_count = self.env["hr.leave.allocation"]._read_group(
            allocation_domain,
            ["holiday_status_id"],
            ["__count"],
        )
        return {holiday_status.id: count for holiday_status, count in allocations_count}

    def requested_display_name(self):
        return self.env.context.get(
            "holiday_status_display_name", True
        ) and self.env.context.get("employee_id")

    @api.depends(
        "requires_allocation", "virtual_remaining_leaves", "max_leaves", "request_unit"
    )
    @api.depends_context("holiday_status_display_name", "employee_id")
    def _compute_display_name(self):
        if not self.requested_display_name():
            return super()._compute_display_name()
        for record in self:
            name = record.name
            if record.requires_allocation:
                remaining_time = (
                    float_round(record.virtual_remaining_leaves, precision_digits=2)
                    or 0.0
                )
                maximum = float_round(record.max_leaves, precision_digits=2) or 0.0

                if record.request_unit == "hour":
                    name = _(
                        "%(name)s (%(time)g remaining out of %(maximum)g hours)",
                        name=record.name,
                        time=remaining_time,
                        maximum=maximum,
                    )
                else:
                    name = _(
                        "%(name)s (%(time)g remaining out of %(maximum)g days)",
                        name=record.name,
                        time=remaining_time,
                        maximum=maximum,
                    )
            record.display_name = name
        return None

    @api.depends("time_type_id.is_work")
    def _compute_eligible_for_accrual_rate(self):
        for leave_type in self:
            leave_type.eligible_for_accrual_rate = leave_type.time_type_id.is_work

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, **kwargs):
        employee = self.env["hr.employee"]._get_contextual_employee()
        if order == self._order and employee:
            leaves = self.browse(super()._search(domain, **kwargs))
            leaves = leaves.sorted(key=self._model_sorting_key, reverse=True)
            leaves = leaves[offset : (offset + limit) if limit else None]
            return leaves._as_query()
        return super()._search(domain, offset, limit, order, **kwargs)

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        return [
            dict(vals, name=self.env._("%s (copy)", leave_type.name))
            for leave_type, vals in zip(self, vals_list, strict=False)
        ]

    def copy_translations(self, new, excluded=()):
        super().copy_translations(new, excluded=(*excluded, "name"))
        self._copy_translations_of_renamed_field(
            new, "name", lambda record, term: record.env._("%s (copy)", term)
        )

    def action_see_days_allocated(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "hr_holidays.hr_leave_allocation_action_all"
        )
        action["domain"] = [
            ("holiday_status_id", "in", self.ids),
        ]
        action["context"] = {
            "employee_id": False,
            "default_holiday_status_id": self.ids[0],
            "search_default_approved_state": 1,
            "search_default_year": 1,
        }
        return action

    def action_see_group_leaves(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "hr_holidays.hr_leave_action_action_approve_department"
        )
        action["domain"] = [
            ("holiday_status_id", "=", self.ids[0]),
        ]
        action["context"] = {
            "default_holiday_status_id": self.ids[0],
        }
        return action

    def action_see_accrual_plans(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "hr_holidays.open_view_accrual_plans"
        )
        action["domain"] = [
            ("time_off_type_id", "=", self.id),
        ]
        action["context"] = {
            "default_time_off_type_id": self.id,
        }
        return action

    @api.model
    def has_accrual_allocation(self):
        employee = self.env["hr.employee"]._get_contextual_employee()
        if not employee:
            return False
        return bool(
            self.env["hr.leave.allocation"].search_count(
                [
                    ("employee_id", "=", employee.id),
                    ("state", "=", "validate"),
                    ("allocation_type", "=", "accrual"),
                    "|",
                    ("date_to", ">", fields.Date.context_today(self)),
                    ("date_to", "=", False),
                ],
                limit=1,
            )
        )

    @api.model
    def get_allocation_data_request(self, target_date=None, hidden_allocations=True):
        domain = [
            "|",
            ("company_id", "in", self.env.companies.ids),
            ("company_id", "=", False),
        ]
        if not hidden_allocations:
            domain.append(("hide_on_dashboard", "=", False))
        leave_types = self.search(domain, order="id")
        employee = self.env["hr.employee"]._get_contextual_employee()
        if employee:
            allocation_data = leave_types.get_allocation_data(employee, target_date)[
                employee
            ]
            return [
                data for data in allocation_data if data[1].get("max_leaves", False)
            ]
        return []

    def get_allocation_data(self, employees, target_date=None):
        allocation_data = defaultdict(list)
        if target_date and isinstance(target_date, str):
            target_date = datetime.fromisoformat(target_date).date()
        elif target_date and isinstance(target_date, datetime):
            target_date = target_date.date()
        elif not target_date:
            target_date = fields.Date.context_today(self)
        today = fields.Date.context_today(self)

        allocations_leaves_consumed, extra_data = employees.with_context(
            ignored_leave_ids=self.env.context.get("ignored_leave_ids")
        )._get_consumed_leaves(self, target_date)
        leave_type_requires_allocation = self.filtered(
            lambda lt: lt.requires_allocation
        )
        expiring_duration_cache = {}
        icon_url_by_type = {
            leave_type: leave_type.icon_id.url
            for leave_type in leave_type_requires_allocation.sudo()
        }

        for employee in employees:
            for leave_type in leave_type_requires_allocation:
                lt_info = (
                    leave_type.name,
                    {
                        "remaining_leaves": 0,
                        "virtual_remaining_leaves": 0,
                        "max_leaves": 0,
                        "accrual_bonus": 0,
                        "leaves_taken": 0,
                        "virtual_leaves_taken": 0,
                        "leaves_requested": 0,
                        "leaves_approved": 0,
                        "closest_allocation_remaining": 0,
                        "closest_allocation_expire": False,
                        "holds_changes": False,
                        "total_virtual_excess": 0,
                        "virtual_excess_data": {},
                        "exceeding_duration": extra_data[employee][leave_type][
                            "exceeding_duration"
                        ],
                        "request_unit": leave_type.request_unit,
                        "icon": icon_url_by_type[leave_type],
                        "allows_negative": leave_type.allows_negative,
                        "max_allowed_negative": leave_type.max_allowed_negative,
                        "employee_company": employee.company_id.id,
                    },
                    leave_type.requires_allocation,
                    leave_type.id,
                )
                for (excess_date, leave_id), excess_days in extra_data[employee][
                    leave_type
                ]["excess_days"].items():
                    amount = excess_days["amount"]
                    lt_info[1]["virtual_excess_data"].update(
                        {f"{excess_date:%Y-%m-%d}-{leave_id}": excess_days}
                    )
                    lt_info[1]["total_virtual_excess"] += amount
                    if not leave_type.allows_negative:
                        continue
                    lt_info[1]["virtual_leaves_taken"] += amount
                    lt_info[1]["virtual_remaining_leaves"] -= amount
                    if excess_days["is_virtual"]:
                        lt_info[1]["leaves_requested"] += amount
                    else:
                        lt_info[1]["leaves_approved"] += amount
                        lt_info[1]["leaves_taken"] += amount
                        lt_info[1]["remaining_leaves"] -= amount
                allocations_now = self.env["hr.leave.allocation"]
                allocations_date = self.env["hr.leave.allocation"]
                allocations_with_remaining_leaves = self.env["hr.leave.allocation"]
                for allocation, data in allocations_leaves_consumed[employee][
                    leave_type
                ].items():
                    if allocation:
                        if allocation.date_from <= today and (
                            not allocation.date_to or allocation.date_to >= today
                        ):
                            allocations_now |= allocation
                        if allocation.date_from <= target_date and (
                            not allocation.date_to or allocation.date_to >= target_date
                        ):
                            allocations_date |= allocation
                        if allocation.date_from > target_date:
                            continue
                        if allocation.date_to and allocation.date_to < target_date:
                            continue
                    lt_info[1]["remaining_leaves"] += data["remaining_leaves"]
                    lt_info[1]["virtual_remaining_leaves"] += data[
                        "virtual_remaining_leaves"
                    ]
                    lt_info[1]["max_leaves"] += data["max_leaves"]
                    lt_info[1]["accrual_bonus"] += data["accrual_bonus"]
                    lt_info[1]["leaves_taken"] += data["leaves_taken"]
                    lt_info[1]["virtual_leaves_taken"] += data["virtual_leaves_taken"]
                    lt_info[1]["leaves_requested"] += (
                        data["virtual_leaves_taken"] - data["leaves_taken"]
                    )
                    lt_info[1]["leaves_approved"] += data["leaves_taken"]
                    if data["virtual_remaining_leaves"] > 0:
                        allocations_with_remaining_leaves |= allocation
                closest_expiration_date, closest_allocation_remaining = (
                    self._get_closest_expiring_leaves_date_and_count(
                        allocations_with_remaining_leaves,
                        allocations_leaves_consumed[employee][leave_type],
                        target_date,
                    )
                )
                if closest_expiration_date:
                    closest_allocation_expire = format_date(
                        self.env, closest_expiration_date
                    )
                    cache_key = (employee, closest_expiration_date)
                    if cache_key not in expiring_duration_cache:
                        expiring_duration_cache[cache_key] = (
                            employee._get_duration_until(
                                target_date, closest_expiration_date
                            )
                        )
                    closest_allocation_dict = expiring_duration_cache[cache_key]
                    if leave_type.request_unit == "hour":
                        closest_allocation_duration = closest_allocation_dict["hours"]
                    else:
                        closest_allocation_duration = closest_allocation_dict["days"]
                else:
                    closest_allocation_expire = False
                    closest_allocation_duration = False
                holds_changes = (
                    lt_info[1]["accrual_bonus"] > 0
                    or bool(allocations_date - allocations_now)
                    or bool(allocations_now - allocations_date)
                ) and target_date != today
                lt_info[1].update(
                    {
                        "closest_allocation_remaining": closest_allocation_remaining,
                        "closest_allocation_expire": closest_allocation_expire,
                        "closest_allocation_duration": closest_allocation_duration,
                        "holds_changes": holds_changes,
                    }
                )
                allocation_data[employee].append(lt_info)
        for employee in allocation_data:
            for leave_type_data in allocation_data[employee]:
                for key, value in leave_type_data[1].items():
                    if isinstance(value, float):
                        leave_type_data[1][key] = round(value, 2)
        return allocation_data

    def _get_closest_expiring_leaves_date_and_count(
        self, allocations, remaining_leaves, target_date
    ):
        expiry_per_allocation = {}
        carried_over_days_expiration_data = self._get_carried_over_days_expiration_data(
            allocations, target_date
        )
        for allocation in allocations:
            accrual_plan_level = allocation.sudo()._get_current_accrual_plan_level_id(
                target_date
            )[0]
            carryover_date = False
            if accrual_plan_level and (
                accrual_plan_level.action_with_unused_accruals == "lost"
                or accrual_plan_level.carryover_options == "limited"
            ):
                carryover_date = allocation.sudo()._get_carryover_date(target_date)
                if carryover_date == target_date:
                    carryover_date += relativedelta(years=1)
            expiry_per_allocation[allocation] = {
                "expiration_date": allocation.date_to,
                "carryover_date": carryover_date,
                "carried_over_days_expiration_date": carried_over_days_expiration_data[
                    allocation
                ]["expiration_date"],
                "accrual_plan_level": accrual_plan_level,
            }

        expiration_dates = sorted(
            expiry_date
            for expiry in expiry_per_allocation.values()
            for key, expiry_date in expiry.items()
            if key != "accrual_plan_level" and expiry_date is not False
        )
        for closest_expiration_date in expiration_dates:
            expiring_leaves_count = 0
            for allocation, expiry in expiry_per_allocation.items():
                virtual_remaining = remaining_leaves[allocation][
                    "virtual_remaining_leaves"
                ]
                if expiry["expiration_date"] == closest_expiration_date:
                    expiring_leaves_count += virtual_remaining
                elif expiry["carryover_date"] == closest_expiration_date:
                    expiring_leaves_count += max(
                        0,
                        virtual_remaining
                        - expiry["accrual_plan_level"].postpone_max_days,
                    )
                elif (
                    expiry["carried_over_days_expiration_date"]
                    == closest_expiration_date
                ):
                    expiring_leaves_count += carried_over_days_expiration_data[
                        allocation
                    ]["no_expiring_days"]

            if expiring_leaves_count != 0:
                return closest_expiration_date, expiring_leaves_count

        return False, 0

    def _get_carried_over_days_expiration_data(self, allocations, target_date):
        carried_over_days_expiration_data = {
            allocation: {"expiration_date": False, "no_expiring_days": 0}
            for allocation in allocations
        }
        projected = self.env["hr.leave.allocation"].with_context(
            default_date_from=target_date
        )
        fake_allocations = projected.browse()
        for allocation in allocations.filtered(
            lambda allocation: allocation.allocation_type == "accrual"
        ):
            fake_allocations |= projected.new(origin=allocation)
        fake_allocations.sudo()._process_accrual_plans(target_date, log=False)
        for fake_allocation in fake_allocations:
            carried_over_days_expiration_data[fake_allocation._origin] = {
                "expiration_date": fake_allocation.carried_over_days_expiration_date,
                "no_expiring_days": max(
                    0,
                    fake_allocation.expiring_carryover_days
                    - fake_allocation.leaves_taken,
                ),
            }
        fake_allocations.invalidate_recordset()
        return carried_over_days_expiration_data
