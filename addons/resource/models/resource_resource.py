from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from typing import TYPE_CHECKING, Any, Self
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.libs.datetime import timezone
from odoo.libs.intervals import Intervals
from odoo.models import ValuesType
from odoo.tools import SQL
from odoo.tools.date_utils import (
    localized,
    to_timezone,
)

from .utils import (
    CUSTODY_ROLE_BY_FIELD,
    CUSTODY_SYNC,
    DEFAULT_HANDOVER_DELAY,
    MANAGER_ROLE,
    OPERATOR_ROLE,
    ResourceSchedule,
)
from odoo.addons.base.models.res_partner import _selection_timezones

if TYPE_CHECKING:
    from odoo.addons.base.models.res_company import ResCompany


class ResourceResource(models.Model):
    _name = "resource.resource"
    _inherit = ["mixin.color"]
    _description = "Resources"
    _order = "name"

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )
    name = fields.Char(
        compute="_compute_name",
        inverse="_inverse_name",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
    )
    active = fields.Boolean(
        default=True,
        help="If the active field is set to False, it will allow you to hide the resource record without removing it.",
    )
    color = fields.Integer(default=lambda self: self._default_color())
    resource_type = fields.Selection(
        selection=[("user", "Human"), ("material", "Material")],
        string="Type",
        default="user",
        required=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Party",
        index="btree_not_null",
        copy=False,
        ondelete="restrict",
        help="The person this resource is. A material resource has none.",
    )
    phone_ids = fields.Many2many(
        related="partner_id.phone_ids",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        compute="_compute_user_id",
        precompute=True,
        store=True,
        index="btree_not_null",
        readonly=False,
        help="The login of the person this resource is: their party's internal user. Choosing another user makes the resource that user's person.",
    )
    avatar_128 = fields.Image(compute="_compute_avatar_128")
    share = fields.Boolean(related="user_id.share")
    email = fields.Char(
        compute="_compute_email",
        inverse="_inverse_email",
        search="_search_email",
    )

    calendar_id = fields.Many2one(
        comodel_name="resource.calendar",
        string="Working Time",
        default=lambda self: self.env.company.resource_calendar_id,
        index="btree_not_null",
        domain="[('company_id', 'in', [company_id, False])]",
        help="Define the working schedule of the resource. If not set, the resource will have fully flexible working hours.",
    )
    tz = fields.Selection(
        selection=_selection_timezones,
        string="Timezone",
        compute="_compute_tz",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
        help="The time zone where this resource works. Its working schedule is read in this zone: an 08:00-17:00 schedule means 08:00-17:00 here, whatever zone the schedule names. For an employee deployed away from the corporate office, set the zone of the place of work.",
    )
    time_efficiency = fields.Float(
        string="Efficiency Factor",
        default=100,
        required=True,
        help="This field is used to calculate the expected duration of a work order at this work center. For example, if a work order takes one hour and the efficiency factor is 100%, then the expected duration will be one hour. If the efficiency factor is 200%, however the expected duration will be 30 minutes.",
    )
    capacity = fields.Integer(
        default=1,
        required=True,
        help="How many claims the resource can hold at once: seats at a table, concurrent users of a machine. A reservation's allocated percentage is a share of this.",
    )

    role_ids = fields.Many2many(
        comodel_name="resource.role",
        relation="resource_resource_role_rel",
        column1="resource_resource_id",
        column2="role_id",
        string="Roles",
    )
    default_role_id = fields.Many2one(
        comodel_name="resource.role",
        compute="_compute_default_role_id",
        inverse="_inverse_default_role_id",
        store=True,
        readonly=False,
        help="Preferred role when assigning this resource. The default is always included in its roles.",
    )

    assignment_ids = fields.One2many(
        comodel_name="resource.assignment",
        inverse_name="resource_id",
        string="Assignments",
    )
    holder_id = fields.Many2one(
        comodel_name="resource.resource",
        string="Current Holder",
        compute="_compute_holder_id",
        search="_search_holder_id",
    )
    operator_id = fields.Many2one(
        comodel_name="resource.resource",
        string="Operator",
        compute="_compute_custody",
        inverse="_inverse_operator_id",
        search="_search_operator_id",
        domain="[('resource_type', '=', 'user'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="Who operates the resource now: the live operator assignment.",
    )
    manager_id = fields.Many2one(
        comodel_name="resource.resource",
        string="Manager",
        compute="_compute_custody",
        inverse="_inverse_manager_id",
        search="_search_manager_id",
        domain="[('resource_type', '=', 'user'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="Who answers for the resource: the live manager assignment.",
    )
    future_operator_id = fields.Many2one(
        comodel_name="resource.resource",
        string="Future Operator",
        compute="_compute_future_operator",
        inverse="_inverse_future_operator",
        search="_search_future_operator_id",
        domain="[('resource_type', '=', 'user'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="Who takes the resource over next: the planned operator assignment.",
    )
    date_future_operator = fields.Datetime(
        string="Hand-over Date",
        compute="_compute_future_operator",
        inverse="_inverse_future_operator",
        help="When the next operator takes over. A hand-over without a date takes effect in a week unless accepted before.",
    )

    reservation_ids = fields.One2many(
        comodel_name="resource.reservation",
        inverse_name="resource_id",
        string="Reservations",
    )

    booking_limit_percentage = fields.Float(
        string="Booking Ceiling %",
        default=100.0,
        required=True,
        help="Maximum simultaneous allocation for enforced bookings. 100% permits full booking; 120% permits 20% overbooking. Warning-only reservations can exceed this ceiling when resource enforcement is disabled.",
    )
    enforce_booking_limit = fields.Boolean(
        string="Enforce Booking Ceiling",
        help="Reject any reservation that exceeds this resource's booking ceiling, including manual meetings and shifts. Individual bookings may enforce the ceiling even when this option is disabled.",
    )

    _party_company_uniq = models.UniqueIndex(
        "(partner_id, company_id) NULLS NOT DISTINCT WHERE resource_type = 'user'",
        "A person is one human resource per company.",
    )
    _check_booking_limit = models.Constraint(
        "CHECK(booking_limit_percentage >= 0 AND booking_limit_percentage < 'Infinity'::float8)",
        "The booking ceiling must be finite and nonnegative.",
    )
    _check_time_efficiency = models.Constraint(
        "CHECK(time_efficiency>0)",
        "Time efficiency must be strictly positive",
    )
    _check_capacity = models.Constraint(
        "CHECK(capacity>0)",
        "Capacity must be strictly positive",
    )
    _check_human_has_party = models.Constraint(
        "CHECK(resource_type != 'user' OR partner_id IS NOT NULL)",
        "A human resource is a person: it needs a party.",
    )

    @api.constrains("booking_limit_percentage", "enforce_booking_limit")
    def _check_booking_limit_reservations(self):
        self._lock_for_scheduling()
        self.env["resource.reservation"].sudo().search(
            [
                ("resource_id", "in", self.ids),
            ]
        )._check_hard_overlap()

    @api.constrains("tz")
    def _check_tz(self):
        for resource in self:
            if not resource.tz:
                raise ValidationError(
                    self.env._(
                        "A resource needs a timezone: %s has none.", resource.name
                    )
                )

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        self._update_party_vals(vals_list)
        for values in vals_list:
            # a falsy zone handed in, such as a user's unset tz, means "seed
            # it": left in the values it would skip the precompute and insert NULL
            if "tz" in values and not values["tz"]:
                del values["tz"]
            if values.get("partner_id"):
                party = self.env["res.partner"].sudo().browse(values["partner_id"])
                if party.name:
                    values.pop("name", None)
            if values.get("company_id") and "calendar_id" not in values:
                values["calendar_id"] = (
                    self.env["res.company"]
                    .browse(values["company_id"])
                    .resource_calendar_id.id
                )
        return super().create(vals_list)

    def write(self, vals: ValuesType) -> bool:
        if self.env.context.get("check_idempotence") and len(self) == 1:
            vals = {
                fname: value
                for fname, value in vals.items()
                if self._fields[fname].convert_to_write(self[fname], self) != value
            }
        if not vals:
            return True
        if vals.get("user_id") and "partner_id" not in vals:
            humans = self.filtered(lambda resource: resource.resource_type == "user")
            if humans:
                party = self.env["res.users"].sudo().browse(vals["user_id"]).partner_id
                humans.write({**vals, "partner_id": party.id})
                return (self - humans).write(vals)
        result = super().write(vals)
        if {"capacity", "tz"} & vals.keys():
            reservations = (
                self.env["resource.reservation"]
                .sudo()
                .search(
                    [
                        ("resource_id", "in", self.ids),
                        ("res_model", "!=", False),
                    ]
                )
            )
            for model_name, rows in reservations.grouped("res_model").items():
                if (
                    model_name in self.env
                    and "reservation_ids" in self.env[model_name]._fields
                ):
                    self.env[model_name].sudo().browse(
                        rows.mapped("res_id")
                    ).exists()._sync_reservations()
        return result

    def copy_data(self, default: ValuesType | None = None) -> list[ValuesType]:
        vals_list = super().copy_data(default=default)
        given = set(default or ())
        copies = []
        for resource, vals in zip(self, vals_list, strict=True):
            vals = dict(vals, name=self.env._("%s (copy)", resource.name))
            company = self.env["res.company"].browse(
                vals.get("company_id") or resource.company_id.id
            )
            calendar_company = resource.calendar_id.company_id
            if (
                "calendar_id" not in given
                and calendar_company
                and calendar_company != company
            ):
                vals["calendar_id"] = company.resource_calendar_id.id
            copies.append(vals)
        return copies

    @api.model
    def default_get(self, fields: list[str]) -> dict[str, Any]:
        res = super().default_get(fields)
        if not res.get("calendar_id") and res.get("company_id"):
            company = self.env["res.company"].browse(res["company_id"])
            res["calendar_id"] = company.resource_calendar_id.id
        return res

    @api.depends("role_ids")
    def _compute_default_role_id(self):
        for resource in self:
            if resource.default_role_id not in resource.role_ids:
                resource.default_role_id = resource.role_ids[:1]

    @api.depends(
        "assignment_ids.assignee_id",
        "assignment_ids.date_start",
        "assignment_ids.date_end",
    )
    def _compute_holder_id(self):
        assignment_model = self.env["resource.assignment"]
        for resource in self:
            resource.holder_id = assignment_model._get_holder(resource)

    @api.depends(
        "assignment_ids.assignee_id",
        "assignment_ids.custody_role",
        "assignment_ids.date_start",
        "assignment_ids.date_end",
        "assignment_ids.active",
    )
    def _compute_custody(self):
        Assignment = self.env["resource.assignment"]
        for field_name, role in CUSTODY_ROLE_BY_FIELD.items():
            live = Assignment._search_custody(self, roles=(role,))
            first = live._get_first_by_resource(reverse=True)
            for resource in self:
                assignment = first.get(resource.id)
                resource[field_name] = assignment.assignee_id if assignment else False

    @api.depends(
        "assignment_ids.assignee_id",
        "assignment_ids.custody_role",
        "assignment_ids.date_start",
        "assignment_ids.date_end",
        "assignment_ids.active",
    )
    def _compute_future_operator(self):
        planned = self.env["resource.assignment"]._search_custody(
            self, roles=(OPERATOR_ROLE,), when="planned"
        )
        first = planned._get_first_by_resource(reverse=False)
        for resource in self:
            assignment = first.get(resource.id)
            resource.future_operator_id = (
                assignment.assignee_id if assignment else False
            )
            resource.date_future_operator = (
                assignment.date_start if assignment else False
            )

    @api.depends("partner_id.name")
    def _compute_name(self):
        for resource in self:
            resource.name = resource.partner_id.name or resource.name

    @api.depends(
        "resource_type", "partner_id.user_ids.active", "partner_id.user_ids.share"
    )
    def _compute_user_id(self):
        for resource in self:
            if resource.resource_type != "user":
                resource.user_id = resource.user_id
                continue
            users = resource.partner_id.sudo().with_context(active_test=False).user_ids
            if resource.user_id in users:
                resource.user_id = resource.user_id
                continue
            logins = users.filtered(lambda user: user.active and not user.share)
            resource.user_id = logins.id if len(logins) == 1 else False

    @api.depends("partner_id.email")
    def _compute_email(self):
        for resource in self:
            resource.email = resource.partner_id.sudo().email

    @api.depends("partner_id.avatar_128", "user_id.avatar_128")
    def _compute_avatar_128(self):
        for resource in self:
            resource.avatar_128 = (
                resource.partner_id.avatar_128 or resource.user_id.avatar_128
            )

    def _inverse_operator_id(self):
        self._sync_custody("operator_id")

    def _inverse_manager_id(self):
        self._sync_custody("manager_id")

    def _inverse_future_operator(self):
        now = fields.Datetime.now()
        Assignment = self.env["resource.assignment"]
        planned = Assignment._search_custody(
            self, roles=(OPERATOR_ROLE,), when="planned"
        )
        planned_by_resource = defaultdict(planned.browse)
        for assignment in planned:
            planned_by_resource[assignment.resource_id.id] |= assignment
        holder_field = self._fields["future_operator_id"]
        date_field = self._fields["date_future_operator"]
        cache = self.env.cache
        new_vals_list = []
        changes = {}
        for resource in self:
            current = planned_by_resource[resource.id].sorted("date_start")[:1]
            holder = (
                resource.future_operator_id
                if cache.contains(resource, holder_field)
                else current.assignee_id
            )
            date_start = (
                resource.date_future_operator
                if cache.contains(resource, date_field)
                else current.date_start
            ) or now + DEFAULT_HANDOVER_DELAY
            if (
                holder
                and current.assignee_id == holder
                and current.date_start == date_start
            ):
                continue
            planned_by_resource[resource.id]._end(now)
            if holder:
                if date_start <= now:
                    raise UserError(
                        self.env._("A scheduled hand-over must start in the future.")
                    )
                new_vals_list.append(
                    {
                        "resource_id": resource.id,
                        "assignee_id": holder.id,
                        "custody_role": OPERATOR_ROLE,
                        "date_start": date_start,
                    }
                )
            changes[resource.id] = (current.assignee_id[:1], holder)
            if holder:
                resource.future_operator_id = holder
                resource.date_future_operator = date_start
        if new_vals_list:
            Assignment.sudo().create(new_vals_list)
        self.browse(changes)._on_custody_changed(OPERATOR_ROLE, changes, planned=True)

    def _inverse_default_role_id(self):
        for resource in self:
            if resource.default_role_id:
                resource.role_ids |= resource.default_role_id
            else:
                resource.default_role_id = resource.role_ids[:1]

    def _inverse_email(self):
        for resource in self.filtered("partner_id"):
            party = resource.partner_id.sudo()
            if party.email != resource.email:
                party.email = resource.email

    def _inverse_name(self):
        for resource in self.filtered("partner_id"):
            party = resource.partner_id.sudo()
            if party.name != resource.name:
                party.name = resource.name

    def _search_custody(self, role, operator, value, when="live"):
        live = Domain("custody_role", "=", role) & self.env[
            "resource.assignment"
        ]._get_custody_domain(when=when)
        if operator in ("in", "not in"):
            ids = [value] if isinstance(value, (int, bool)) else list(value)
            resource_ids = [i for i in ids if i]
            wants_empty = len(resource_ids) < len(ids)
        elif operator in ("any", "not any"):
            resource_ids = self.with_context(active_test=False)._search(value)
            wants_empty = False
        else:
            return NotImplemented
        domain = Domain(
            "assignment_ids", "any", live & Domain("assignee_id", "in", resource_ids)
        )
        if wants_empty:
            domain |= ~Domain("assignment_ids", "any", live)
        return ~domain if operator.startswith("not") else domain

    def _search_operator_id(self, operator, value):
        return self._search_custody(OPERATOR_ROLE, operator, value)

    def _search_manager_id(self, operator, value):
        return self._search_custody(MANAGER_ROLE, operator, value)

    def _search_future_operator_id(self, operator, value):
        return self._search_custody(OPERATOR_ROLE, operator, value, when="planned")

    def _search_email(self, operator, value):
        return Domain("partner_id.email", operator, value)

    def _search_holder_id(self, operator, value):
        if operator not in ("=", "in", "!=", "not in"):
            return NotImplemented
        now = fields.Datetime.now()
        live = self.env["resource.assignment"].search(
            Domain("date_start", "<=", now)
            & (Domain("date_end", "=", False) | Domain("date_end", ">", now))
        )
        current_assignee_id_by_resource_id = {}
        for assignment in live.sorted("date_start", reverse=True):
            current_assignee_id_by_resource_id.setdefault(
                assignment.resource_id.id, assignment.assignee_id.id
            )
        values = list(value) if operator in ("in", "not in") else [value]
        domain = Domain(
            "id",
            "in",
            [
                resource_id
                for resource_id, assignee_id in current_assignee_id_by_resource_id.items()
                if assignee_id in values
            ],
        )
        if False in values:
            domain |= Domain("id", "not in", list(current_assignee_id_by_resource_id))
        if operator in ("!=", "not in"):
            domain = ~domain
        return domain

    @api.onchange("company_id")
    def _onchange_company_id(self):
        if self.company_id:
            self.calendar_id = self.company_id.resource_calendar_id.id

    def _on_custody_changed(self, role, changes, planned=False):
        pass

    def _end_custody(self, at=None):
        # What it held, whoever held it, ends: archiving and disposal call this.
        self.env["resource.assignment"]._search_custody(
            self, when="open", archived=True
        )._end(at)

    def _sync_custody(self, field_name):
        role = CUSTODY_ROLE_BY_FIELD[field_name]
        now = fields.Datetime.now()
        Assignment = self.env["resource.assignment"]
        live = Assignment._search_custody(self, roles=(role,), archived=True)
        live_by_resource = defaultdict(live.browse)
        for assignment in live:
            live_by_resource[assignment.resource_id.id] |= assignment
        new_vals_list = []
        changes = {}
        for resource in self:
            current = live_by_resource[resource.id]
            holder = resource[field_name]
            if holder and current.assignee_id == holder:
                continue
            if not holder and not current:
                continue
            changes[resource.id] = (current.assignee_id[:1], holder)
            current._end(now)
            if holder:
                new_vals_list.append(
                    {
                        "resource_id": resource.id,
                        "assignee_id": holder.id,
                        "custody_role": role,
                        "date_start": now,
                    }
                )
        if new_vals_list:
            # The rivals are ended above; the create hook has nothing to supersede.
            Assignment.sudo().with_context(**{CUSTODY_SYNC: True}).create(new_vals_list)
        changed = self.browse(changes)
        changed._on_custody_changed(role, changes)
        return changed

    def _update_party_vals(self, vals_list: list[ValuesType]) -> None:
        default_type = self.default_get(["resource_type"]).get("resource_type")
        unbound = []
        for values in vals_list:
            if (
                values.get("partner_id")
                or values.get("resource_type", default_type) != "user"
            ):
                continue
            if user := self.env["res.users"].sudo().browse(values.get("user_id")):
                values["partner_id"] = user.partner_id.id
            elif values.get("name"):
                unbound.append(values)
        parties = (
            self.env["res.partner"]
            .sudo()
            .create(
                [
                    {"name": values["name"], "tz": values.get("tz") or False}
                    for values in unbound
                ]
            )
        )
        for values, party in zip(unbound, parties, strict=True):
            values["partner_id"] = party.id

    def _lock_for_scheduling(self):
        if self:
            self.env.cr.execute(
                SQL(
                    """
                WITH locked AS MATERIALIZED (
                    SELECT id FROM resource_resource
                     WHERE id = ANY(%s) ORDER BY id FOR NO KEY UPDATE
                )
                UPDATE resource_resource AS resource
                   SET write_date = resource.write_date
                  FROM locked WHERE resource.id = locked.id
                """,
                    self.ids,
                )
            )

    def _compute_tz(self):
        for resource in self:
            resource.tz = (
                resource.tz
                or resource.calendar_id.tz
                or resource.company_id.resource_calendar_id.tz
                or resource.partner_id.sudo().tz
                or resource.user_id.sudo().tz
                or self.env.context.get("tz")
                or self.env.user.tz
                or "UTC"
            )

    def _adjust_to_calendar(
        self,
        start: datetime,
        end: datetime,
        compute_leaves: bool = True,
    ) -> dict[Self, tuple[datetime | None, datetime | None]]:
        revert_start_tz = to_timezone(start.tzinfo)
        revert_end_tz = to_timezone(end.tzinfo)
        start = localized(start)
        end = localized(end)
        empty_meta = self.env["resource.calendar.attendance"]
        windows = {}
        by_calendar = defaultdict(lambda: self.env["resource.resource"])
        result = {}
        for resource in self:
            resource_tz = timezone(resource.tz)
            local_start = start.astimezone(resource_tz)
            local_end = end.astimezone(resource_tz)
            day_start = local_start + relativedelta(hour=0, minute=0, second=0)
            day_end = local_end + relativedelta(days=1, hour=0, minute=0, second=0)
            calendar = (
                resource.calendar_id
                or resource.company_id.resource_calendar_id
                or self.env.company.resource_calendar_id
            )
            if resource._is_flexible():
                calendar_start = calendar._get_closest_work_time(
                    local_start,
                    resource=resource,
                    search_range=[day_start, day_end],
                    compute_leaves=compute_leaves,
                )
                calendar_end = calendar._get_closest_work_time(
                    max(local_start, local_end),
                    match_end=True,
                    resource=resource,
                    search_range=[local_start, day_end],
                    compute_leaves=compute_leaves,
                )
                result[resource] = (
                    calendar_start and revert_start_tz(calendar_start),
                    calendar_end and revert_end_tz(calendar_end),
                )
                continue
            windows[resource] = (local_start, local_end, day_start, day_end)
            by_calendar[calendar] |= resource

        for calendar, resources in by_calendar.items():
            batch_start = min(windows[r][2] for r in resources)
            batch_end = max(windows[r][3] for r in resources)
            intervals_batch = calendar._work_intervals_batch(
                batch_start, batch_end, resources, compute_leaves=compute_leaves
            )
            for resource in resources:
                local_start, local_end, day_start, day_end = windows[resource]
                intervals = intervals_batch[resource.id]
                calendar_start = None
                if day_start <= local_start <= day_end:
                    own = intervals & Intervals([(day_start, day_end, empty_meta)])
                    calendar_start = min(
                        (interval[0] for interval in own),
                        key=lambda dt: abs(dt - local_start),
                        default=None,
                    )
                calendar_end = None
                target = max(local_start, local_end)
                if local_start <= target <= day_end:
                    own = intervals & Intervals([(local_start, day_end, empty_meta)])
                    calendar_end = min(
                        (interval[1] for interval in own),
                        key=lambda dt: abs(dt - target),
                        default=None,
                    )
                result[resource] = (
                    calendar_start and revert_start_tz(calendar_start),
                    calendar_end and revert_end_tz(calendar_end),
                )
        return result

    def _get_unavailable_intervals(
        self, start: datetime, end: datetime
    ) -> dict[int, Intervals]:
        start_datetime = localized(start)
        end_datetime = localized(end)
        resource_mapping = {}
        calendar_mapping = defaultdict(lambda: self.env["resource.resource"])
        for resource in self:
            calendar_mapping[
                resource.calendar_id or resource.company_id.resource_calendar_id
            ] |= resource

        for calendar, resources in calendar_mapping.items():
            if not calendar:
                continue
            resources_unavailable_intervals = calendar._unavailable_intervals_batch(
                start_datetime, end_datetime, resources
            )
            resource_mapping.update(resources_unavailable_intervals)
        return resource_mapping

    def _find_free_window(
        self,
        start: datetime,
        hours: float,
        horizon_days: int = 700,
    ) -> tuple[datetime, datetime] | tuple[None, None]:
        length = timedelta(hours=hours or 1)
        window_start = start
        limit = start + timedelta(days=horizon_days)
        Reservation = self.env["resource.reservation"]
        while window_start <= limit:
            window_end = window_start + length
            busy = Reservation.sudo().search(
                [
                    ("resource_id", "in", self.ids),
                    ("active", "=", True),
                    ("date_start", "<", window_end),
                    ("date_end", ">", window_start),
                ]
            )
            if not busy:
                return window_start, window_end
            window_start = max(busy.mapped("date_end"))
        return None, None

    def _get_calendars_validity_within_period(
        self,
        start: datetime,
        end: datetime,
        default_company: ResCompany | None = None,
    ) -> dict[int | bool, dict]:
        if not (start.tzinfo and end.tzinfo):
            raise ValueError("start and end datetimes must be timezone-aware")
        resource_calendars_within_period = defaultdict(lambda: defaultdict(Intervals))
        default_calendar = (
            default_company and default_company.resource_calendar_id
        ) or self.env.company.resource_calendar_id
        if not self:
            resource_calendars_within_period[False][default_calendar] = Intervals(
                [(start, end, self.env["resource.calendar.attendance"])]
            )
        for resource in self:
            calendar = (
                resource.calendar_id
                or resource.company_id.resource_calendar_id
                or default_calendar
            )
            resource_calendars_within_period[resource.id][calendar] = Intervals(
                [(start, end, self.env["resource.calendar.attendance"])]
            )
        return resource_calendars_within_period

    def _get_work_schedule(
        self,
        start: datetime,
        end: datetime,
        calendars: tuple | None = None,
        compute_leaves: bool = True,
        leave_domain: list | None = None,
    ) -> ResourceSchedule:
        flexible = self.filtered(lambda resource: resource._is_flexible())
        intervals, calendar_intervals = (self - flexible)._get_valid_work_intervals(
            start,
            end,
            calendars=calendars,
            compute_leaves=compute_leaves,
            domain=leave_domain,
        )
        flexible_intervals, hours_per_day, hours_per_week = (
            flexible._get_flexible_resource_valid_work_intervals(
                start, end, compute_leaves=compute_leaves, leave_domain=leave_domain
            )
        )
        intervals.update(flexible_intervals)
        return ResourceSchedule(
            intervals=defaultdict(Intervals, intervals),
            calendar_intervals=calendar_intervals,
            hours_per_day=defaultdict(dict, hours_per_day),
            hours_per_week=defaultdict(dict, hours_per_week),
            flexible_ids=frozenset(flexible.ids),
        )

    def _get_valid_work_intervals(
        self,
        start: datetime,
        end: datetime,
        calendars: tuple | None = None,
        compute_leaves: bool = True,
        domain: list | None = None,
    ) -> tuple[dict[int, Intervals], dict[int, Intervals]]:
        if not (start.tzinfo and end.tzinfo):
            raise ValueError("start and end datetimes must be timezone-aware")
        calendar_resources = defaultdict(lambda: self.env["resource.resource"])
        resource_work_intervals = defaultdict(Intervals)
        calendar_work_intervals = {}

        resource_calendar_validity_intervals = (
            self.sudo()._get_calendars_validity_within_period(start, end)
        )
        for resource in self:
            for calendar in resource_calendar_validity_intervals[resource.id]:
                calendar_resources[calendar] |= resource
        for calendar in calendars or []:
            calendar_resources[calendar] |= self.env["resource.resource"]
        for calendar, resources in calendar_resources.items():
            if not calendar:
                for resource in resources:
                    resource_work_intervals[resource.id] |= Intervals(
                        [(start, end, self.env["resource.calendar.attendance"])]
                    )
                continue
            work_intervals_batch = calendar._work_intervals_batch(
                start,
                end,
                resources=resources,
                domain=domain,
                compute_leaves=compute_leaves,
            )
            for resource in resources:
                resource_work_intervals[resource.id] |= (
                    work_intervals_batch[resource.id]
                    & resource_calendar_validity_intervals[resource.id][calendar]
                )
            calendar_work_intervals[calendar.id] = work_intervals_batch[False]

        return resource_work_intervals, calendar_work_intervals

    def _get_calendar_at(
        self, date_target: datetime, tz: ZoneInfo | None = None
    ) -> dict:
        return {resource: resource.calendar_id for resource in self}

    def _get_flexible_resources_default_work_intervals(
        self,
        start: datetime,
        end: datetime,
    ) -> dict[int, Intervals]:
        if not (start.tzinfo and end.tzinfo):
            raise ValueError("start and end datetimes must be timezone-aware")

        res = {}

        resources_per_tz = defaultdict(list)
        for resource in self:
            resources_per_tz[timezone(resource.tz)].append(resource)

        for tz, resources in resources_per_tz.items():
            day = start.astimezone(tz).date()
            end_date = end.astimezone(tz).date()
            ranges = []
            while day <= end_date:
                start_datetime = datetime.combine(day, datetime.min.time()).replace(
                    tzinfo=tz
                )
                end_datetime = datetime.combine(day, datetime.max.time()).replace(
                    tzinfo=tz
                )
                ranges.append(
                    (
                        start_datetime,
                        end_datetime,
                        self.env["resource.calendar.attendance"],
                    )
                )
                day += timedelta(days=1)

            for resource in resources:
                res[resource.id] = Intervals(ranges)

        return res

    def _get_flexible_resources_calendars_validity_within_period(
        self,
        start: datetime,
        end: datetime,
    ) -> dict[int, dict]:
        if not (start.tzinfo and end.tzinfo):
            raise ValueError("start and end datetimes must be timezone-aware")
        resource_default_work_intervals = (
            self._get_flexible_resources_default_work_intervals(start, end)
        )

        calendars_within_period_per_resource = defaultdict(
            lambda: defaultdict(Intervals)
        )
        for resource in self:
            calendars_within_period_per_resource[resource.id][resource.calendar_id] = (
                resource_default_work_intervals[resource.id]
            )

        return calendars_within_period_per_resource

    @api.model
    def _flexible_week_key(self, day: date) -> tuple[int, int]:
        return day.isocalendar()[:2]

    def _get_flexible_week_bounds(self, start, end):
        """UTC bounds covering the ISO weeks touched in each resource's timezone."""
        if not (start.tzinfo and end.tzinfo):
            raise ValueError("start and end datetimes must be timezone-aware")
        starts, stops = [], []
        last = end - timedelta(microseconds=1) if end > start else end
        for tz in {timezone(resource.tz) for resource in self}:
            first_day = start.astimezone(tz).date()
            last_day = last.astimezone(tz).date()
            monday = first_day - timedelta(days=first_day.weekday())
            next_monday = last_day + timedelta(days=7 - last_day.weekday())
            starts.append(datetime.combine(monday, time.min, tz).astimezone(UTC))
            stops.append(datetime.combine(next_monday, time.min, tz).astimezone(UTC))
        return min(starts, default=start), max(stops, default=end)

    def _format_leave(
        self,
        leave,
        resource_hours_per_day,
        resource_hours_per_week,
        ranges_to_remove,
        start_day,
        end_day,
    ):
        tz = timezone(self.tz)
        leave_start_day = leave[0].astimezone(tz).date()
        # Leave intervals are half-open: midnight belongs to the next day.
        leave_end_day = (leave[1] - timedelta(microseconds=1)).astimezone(tz).date()

        while leave_start_day <= leave_end_day:
            if not self._is_fully_flexible():
                hours = self.calendar_id.hours_per_day
                if leave_start_day >= start_day and leave_start_day <= end_day:
                    resource_hours_per_day[self.id][leave_start_day] -= hours
                year_and_week = self._flexible_week_key(leave_start_day)
                resource_hours_per_week[self.id][year_and_week] -= hours

            range_start_datetime = datetime.combine(
                leave_start_day, datetime.min.time()
            ).replace(tzinfo=tz)
            range_end_datetime = datetime.combine(
                leave_start_day, datetime.max.time()
            ).replace(tzinfo=tz)
            ranges_to_remove.append(
                (
                    range_start_datetime,
                    range_end_datetime,
                    self.env["resource.calendar.attendance"],
                )
            )
            leave_start_day += timedelta(days=1)

    def _get_flexible_resource_valid_work_intervals(
        self,
        start: datetime,
        end: datetime,
        compute_leaves: bool = True,
        leave_domain: list | None = None,
    ) -> tuple[dict[int, Intervals], dict, dict]:
        if not self:
            return {}, {}, {}

        if not all(record._is_flexible() for record in self):
            raise ValueError("all resources must be flexible")
        if not (start.tzinfo and end.tzinfo):
            raise ValueError("start and end datetimes must be timezone-aware")

        min_start_date, max_end_date = self._get_flexible_week_bounds(start, end)
        last = end - timedelta(microseconds=1) if end > start else end
        days_by_resource = {
            resource.id: (
                start.astimezone(timezone(resource.tz)).date(),
                last.astimezone(timezone(resource.tz)).date(),
            )
            for resource in self
        }

        resource_work_intervals = defaultdict(Intervals)
        calendar_resources = defaultdict(lambda: self.env["resource.resource"])

        resource_calendar_validity_intervals = (
            self._get_flexible_resources_calendars_validity_within_period(
                min_start_date, max_end_date
            )
        )
        for resource in self:
            for calendar, work_intervals in resource_calendar_validity_intervals[
                resource.id
            ].items():
                calendar_resources[calendar] |= resource
                resource_work_intervals[resource.id] |= work_intervals

        resource_by_id = {resource.id: resource for resource in self}

        resource_hours_per_day = defaultdict(lambda: defaultdict(float))
        resource_hours_per_week = defaultdict(lambda: defaultdict(float))

        for resource in self:
            if resource._is_fully_flexible():
                continue
            start_day, end_day = days_by_resource[resource.id]
            start_week_key = self._flexible_week_key(start_day)
            end_week_key = self._flexible_week_key(end_day)
            duration_per_day = defaultdict(float)
            resource_intervals = resource_work_intervals.get(resource.id, Intervals())
            for interval_start, interval_end, _dummy in resource_intervals:
                day = interval_start.date()
                duration_per_day[day] += (
                    interval_end - interval_start
                ).total_seconds() / 3600

            for day, hours in duration_per_day.items():
                day_working_hours = min(hours, resource.calendar_id.hours_per_day)
                if day >= start_day and day <= end_day:
                    resource_hours_per_day[resource.id][day] = day_working_hours

                year_week = self._flexible_week_key(day)
                if start_week_key <= year_week <= end_week_key:
                    cap = resource.calendar_id._get_flexible_hours_per_week()
                    resource_hours_per_week[resource.id][year_week] = min(
                        cap,
                        day_working_hours
                        + resource_hours_per_week[resource.id][year_week],
                    )

        if compute_leaves:
            for calendar, resources in calendar_resources.items():
                domain = (
                    leave_domain
                    if leave_domain is not None
                    else ([("calendar_id", "=", False)] if not calendar else None)
                )
                leave_intervals = (
                    calendar or self.env["resource.calendar"]
                )._leave_intervals_batch(
                    min_start_date, max_end_date, resources, domain
                )
                for resource_id, leaves in leave_intervals.items():
                    if not resource_id:
                        continue

                    ranges_to_remove = []
                    start_day, end_day = days_by_resource[resource_id]
                    for leave in leaves:
                        resource_by_id[resource_id]._format_leave(
                            leave,
                            resource_hours_per_day,
                            resource_hours_per_week,
                            ranges_to_remove,
                            start_day,
                            end_day,
                        )

                    resource_work_intervals[resource_id] -= Intervals(ranges_to_remove)

        for resource_id, work_intervals in resource_work_intervals.items():
            tz = timezone(resource_by_id[resource_id].tz)
            resource_work_intervals[resource_id] = work_intervals & Intervals(
                [
                    (
                        start.astimezone(tz),
                        end.astimezone(tz),
                        self.env["resource.calendar.attendance"],
                    )
                ]
            )

        return resource_work_intervals, resource_hours_per_day, resource_hours_per_week

    def _get_flexible_booking_hours_per_day(self, bookings_by_resource, start, end):
        resources = self.filtered(
            lambda resource: (
                bookings_by_resource.get(resource.id)
                and not resource._is_fully_flexible()
            )
        )
        intervals, day_limits, week_limits = resources.with_context(
            resource_capacity_aware=True
        )._get_flexible_resource_valid_work_intervals(start, end)
        result = defaultdict(lambda: defaultdict(float))
        for resource in resources:
            for booking_start, booking_end, percentage in bookings_by_resource.get(
                resource.id, []
            ):
                booking_intervals = (
                    Intervals(
                        [(localized(booking_start), localized(booking_end), set())]
                    )
                    & intervals[resource.id]
                )
                hours_per_day = defaultdict(float)
                resource._get_flexible_resource_work_hours(
                    booking_intervals,
                    day_limits[resource.id],
                    week_limits[resource.id],
                    hours_per_day,
                )
                for day, hours in hours_per_day.items():
                    result[resource.id][day] += hours * percentage / 100
        return result

    def _get_flexible_resource_work_hours(
        self,
        intervals: Intervals,
        flexible_resources_hours_per_day: dict,
        flexible_resources_hours_per_week: dict,
        work_hours_per_day: dict | None = None,
    ) -> float:
        if not self._is_flexible():
            raise ValueError("resource must be flexible")

        if self._is_fully_flexible():
            return round(
                sum(
                    (end.astimezone(UTC) - start.astimezone(UTC)).total_seconds() / 3600
                    for start, end, _dummy in intervals
                ),
                2,
            )

        duration_per_day = dict(flexible_resources_hours_per_day)
        duration_per_week = dict(flexible_resources_hours_per_week)

        interval_duration_per_day = defaultdict(float)
        tz = timezone(self.tz)
        for start, end, _dummy in intervals:
            start, end = start.astimezone(tz), end.astimezone(tz)
            end_utc = end.astimezone(UTC)
            if end.time() == time.max:
                end_utc += timedelta(microseconds=1)
            duration = (end_utc - start.astimezone(UTC)).total_seconds() / 3600
            interval_duration_per_day[start.date()] += duration

        work_hours = 0.0
        for day, hours in interval_duration_per_day.items():
            week = self._flexible_week_key(day)
            day_working_hours = max(
                0.0,
                min(
                    hours,
                    duration_per_day.get(day, 0.0),
                    duration_per_week.get(week, 0.0),
                ),
            )
            work_hours += day_working_hours
            duration_per_week[week] = (
                duration_per_week.get(week, 0.0) - day_working_hours
            )

            if work_hours_per_day is not None:
                work_hours_per_day[day] += day_working_hours

        return work_hours

    def _is_fully_flexible(self) -> bool:
        self.check_singleton()
        return not self.calendar_id

    def _is_flexible(self) -> bool:
        self.check_singleton()
        return self._is_fully_flexible() or self.calendar_id.flexible_hours
