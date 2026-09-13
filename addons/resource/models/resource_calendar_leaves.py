from datetime import UTC, datetime, time
from typing import Any

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.datetime import timezone
from odoo.models import ValuesType


class ResourceCalendarLeaves(models.Model):
    _name = "resource.calendar.leaves"
    _description = "Resource Time Off Detail"
    _order = "date_from"
    _check_company_auto = True

    name = fields.Char("Reason")
    company_id = fields.Many2one(
        "res.company",
        readonly=True,
        default=lambda self: self.env.company,
        compute="_compute_company_id",
        store=True,
    )
    calendar_id = fields.Many2one(
        "resource.calendar",
        "Working Hours",
        compute="_compute_calendar_id",
        store=True,
        readonly=False,
        domain="[('company_id', 'in', [company_id, False])]",
        check_company=True,
        index=True,
        ondelete="cascade",
    )
    resource_id = fields.Many2one(
        "resource.resource",
        index=True,
        check_company=True,
        ondelete="cascade",
        help="If empty, this is a generic time off for the company. If a resource is set, the time off is only for this resource",
    )
    time_type = fields.Selection(
        [("leave", "Time Off"), ("other", "Other")],
        default="leave",
        help="Whether this should be computed as a time off or as work time (eg: formation)",
    )
    date_from = fields.Datetime("Start Date", required=True)
    date_to = fields.Datetime(
        "End Date",
        compute="_compute_date_to",
        readonly=False,
        required=True,
        store=True,
        precompute=True,
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
