from datetime import UTC, date, datetime, time
from typing import Any

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.libs.datetime import timezone
from odoo.models import ValuesType


class ResourceCalendarLeaves(models.Model):
    _name = "resource.calendar.leaves"
    _description = "Resource Time Off Detail"
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
    time_type = fields.Selection(
        selection=[("leave", "Time Off"), ("other", "Other")],
        default="leave",
        help="Whether this should be computed as a time off or as work time (eg: formation)",
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

    @api.depends("date_from")
    def _compute_date_to(self):
        user_tz_name = self.env.context.get("tz") or self.env.user.tz
        for leave in self:
            if not leave.date_from or (
                leave.date_to and leave.date_to > leave.date_from
            ):
                continue
            tz_name = (
                leave.calendar_id.tz
                or leave.company_id.resource_calendar_id.tz
                or user_tz_name
                or "UTC"
            )
            local_date_from = leave.date_from.replace(tzinfo=UTC).astimezone(
                timezone(tz_name)
            )
            local_date_to = local_date_from + relativedelta(
                hour=23, minute=59, second=59
            )
            leave.date_to = local_date_to.astimezone(UTC).replace(tzinfo=None)

    def _copy_leave_vals(self) -> ValuesType:
        self.check_singleton()
        return {
            "name": self.name,
            "date_from": self.date_from,
            "date_to": self.date_to,
            "time_type": self.time_type,
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
