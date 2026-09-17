from datetime import UTC, date, datetime, time
from typing import Any

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.libs.datetime import timezone
from odoo.models import ValuesType

from odoo.addons.base.models.res_partner import _selection_timezones

_DAY_END_HOUR = 24 - 1 / 3600


def _hour_of(dt: datetime) -> float:
    return dt.hour + dt.minute / 60 + dt.second / 3600


def _to_local(dt: datetime | None, tz) -> datetime | None:
    return dt and dt.replace(tzinfo=UTC).astimezone(tz)


def _to_utc(day: date, hour: float, tz) -> datetime:
    local = datetime.combine(day, time.min).replace(tzinfo=tz) + relativedelta(
        seconds=round(hour * 3600)
    )
    return local.astimezone(UTC).replace(tzinfo=None)


class ResourceScheduleException(models.Model):
    _name = "resource.schedule.exception"
    _inherit = ["mixin.resource.ledger"]
    _description = "Schedule Exception"
    _order = "date_from"
    _check_company_auto = True

    name = fields.Char(string="Reason")
    company_id = fields.Many2one(
        comodel_name="res.company",
        compute="_compute_company_id",
        default=lambda self: self.env.company,
        store=True,
        readonly=True,
    )
    calendar_id = fields.Many2one(
        comodel_name="resource.calendar",
        string="Working Hours",
        compute="_compute_calendar_id",
        store=True,
        index=True,
        readonly=False,
        domain="[('company_id', 'in', [company_id, False])]",
        ondelete="cascade",
        check_company=True,
    )
    resource_id = fields.Many2one(
        comodel_name="resource.resource",
        index=True,
        ondelete="cascade",
        check_company=True,
        help="If empty, this is a generic time off for the company. If a resource is set, the time off is only for this resource",
    )
    time_type_id = fields.Many2one(
        comodel_name="resource.time.type",
        string="Kind of Time",
        default=lambda self: self.env["resource.time.type"]._get_leave_type(),
        required=True,
        ondelete="restrict",
        help="What this exception takes out of the schedule. An absence is subtracted from working time; a kind that counts as working time (a training, say) carves out the period without shortening the day.",
    )
    date_from = fields.Datetime(
        string="Start Date",
        required=True,
    )
    date_to = fields.Datetime(
        string="End Date",
        compute="_compute_date_to",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
    )
    tz = fields.Selection(
        selection=_selection_timezones,
        string="Timezone",
        compute="_compute_tz",
        help="The time zone this exception's hours are read in: the resource's work zone, or the schedule's own zone when it closes the whole company.",
    )
    local_date_from = fields.Date(
        string="Start Day",
        compute="_compute_local_dates",
        inverse="_inverse_local_dates",
    )
    local_date_to = fields.Date(
        string="End Day",
        compute="_compute_local_dates",
        inverse="_inverse_local_dates",
    )
    local_hour_from = fields.Float(
        string="Start Hour",
        compute="_compute_local_dates",
        inverse="_inverse_local_dates",
    )
    local_hour_to = fields.Float(
        string="End Hour",
        compute="_compute_local_dates",
        inverse="_inverse_local_dates",
        help="The local hour the exception ends at, 0 meaning the end of the day.",
    )

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        if self.filtered(lambda leave: leave.date_from > leave.date_to):
            raise ValidationError(
                self.env._(
                    "The start date of the time off must be earlier than the end date."
                )
            )

    @api.model
    def default_get(self, fields: list[str]) -> dict[str, Any]:
        res = super().default_get(fields)
        if (
            "date_from" in fields
            and "date_to" in fields
            and not res.get("date_from")
            and not res.get("date_to")
        ):
            calendar = self.env.company.resource_calendar_id
            if "calendar_id" in res:
                calendar = self.env["resource.calendar"].browse(res["calendar_id"])
            tz = timezone(calendar.tz or "UTC")
            today = datetime.now(tz).date()
            date_from = datetime.combine(today, time.min).replace(tzinfo=tz)
            date_to = datetime.combine(today, time.max).replace(tzinfo=tz)
            res.update(
                date_from=date_from.astimezone(UTC).replace(tzinfo=None),
                date_to=date_to.astimezone(UTC).replace(tzinfo=None),
            )
        return res

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._on_schedule_changed(records._get_schedule_scopes())
        return records

    def write(self, vals):
        if self._get_fields_schedule_scope().isdisjoint(vals):
            return super().write(vals)
        scopes = self._get_schedule_scopes()
        res = super().write(vals)
        self._on_schedule_changed(scopes + self._get_schedule_scopes())
        return res

    def unlink(self):
        scopes = self._get_schedule_scopes()
        model = self.browse()
        res = super().unlink()
        model._on_schedule_changed(scopes)
        return res

    @api.depends("resource_id.calendar_id")
    def _compute_calendar_id(self):
        for leave in self.filtered("resource_id"):
            leave.calendar_id = leave.resource_id.calendar_id

    @api.depends("calendar_id", "resource_id.company_id")
    def _compute_company_id(self):
        for leave in self:
            leave.company_id = (
                leave.calendar_id.company_id
                or leave.resource_id.company_id
                or self.env.company
            )

    @api.depends("resource_id.tz", "calendar_id.tz", "company_id")
    def _compute_tz(self):
        for leave in self:
            leave.tz = (
                leave.resource_id.tz
                or leave.calendar_id.tz
                or leave.company_id.resource_calendar_id.tz
                or "UTC"
            )

    @api.depends("date_from", "tz")
    def _compute_date_to(self):
        for leave in self:
            if not leave.date_from or (
                leave.date_to and leave.date_to > leave.date_from
            ):
                continue
            local_date_from = _to_local(leave.date_from, timezone(leave.tz or "UTC"))
            local_date_to = local_date_from + relativedelta(
                hour=23, minute=59, second=59
            )
            leave.date_to = local_date_to.astimezone(UTC).replace(tzinfo=None)

    @api.depends("date_from", "date_to", "tz")
    def _compute_local_dates(self):
        for leave in self:
            tz = timezone(leave.tz or "UTC")
            start = _to_local(leave.date_from, tz)
            stop = _to_local(leave.date_to, tz)
            leave.local_date_from = start and start.date()
            leave.local_hour_from = start and _hour_of(start)
            leave.local_date_to = stop and stop.date()
            leave.local_hour_to = stop and _hour_of(stop)

    def _inverse_local_dates(self):
        for leave in self.filtered("local_date_from"):
            tz = timezone(leave.tz or "UTC")
            leave.write(
                {
                    "date_from": _to_utc(
                        leave.local_date_from, leave.local_hour_from, tz
                    ),
                    "date_to": _to_utc(
                        leave.local_date_to or leave.local_date_from,
                        leave.local_hour_to or _DAY_END_HOUR,
                        tz,
                    ),
                }
            )

    def _copy_leave_vals(self) -> ValuesType:
        self.check_singleton()
        return {
            "name": self.name,
            "date_from": self.date_from,
            "date_to": self.date_to,
            "time_type_id": self.time_type_id.id,
        }

    @api.model
    def _get_domain_public_holidays(
        self,
        date_from: date | None = None,
        date_to: date | None = None,
        companies: models.BaseModel | None = None,
        calendars: models.BaseModel | None = None,
    ) -> Domain:
        if isinstance(date_from, date) and not isinstance(date_from, datetime):
            date_from = datetime.combine(date_from, time.min)
        if isinstance(date_to, date) and not isinstance(date_to, datetime):
            date_to = datetime.combine(date_to, time.max)
        domain = Domain("resource_id", "=", False)
        if date_to is not None:
            domain &= Domain("date_from", "<=", date_to)
        if date_from is not None:
            domain &= Domain("date_to", ">=", date_from)
        if companies is not None:
            domain &= Domain("company_id", "in", companies.ids)
        if calendars is not None:
            domain &= Domain("calendar_id", "in", [False, *calendars.ids])
        return domain

    @api.model
    def _get_fields_schedule_scope(self) -> frozenset[str]:
        return frozenset(
            {
                "resource_id",
                "calendar_id",
                "company_id",
                "date_from",
                "date_to",
                "time_type_id",
            }
        )

    def _get_schedule_scopes(self) -> list[dict[str, Any]]:
        return [
            {
                "resource_id": exception.resource_id.id,
                "calendar_id": exception.calendar_id.id,
                "company_id": exception.company_id.id,
                "date_from": exception.date_from,
                "date_to": exception.date_to,
                "time_type_id": exception.time_type_id.id,
            }
            for exception in self
        ]

    @api.model
    def _on_schedule_changed(self, scopes: list[dict[str, Any]]) -> None:
        return
