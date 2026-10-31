# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import UTC
from zoneinfo import ZoneInfo

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResourceCalendarLeaves(models.Model):
    _inherit = "resource.calendar.leaves"

    is_exceptional_days = fields.Boolean("Is Exceptional Day")
    working_start_date = fields.Datetime("Compensatory Off Start Date")
    working_end_date = fields.Datetime(
        "Compensatory Off End Date", compute="_compute_working_end_date", store=True,
    )

    def _l10n_in_get_local_date(self, value):
        self.ensure_one()
        timezone = self.env.tz
        if not (self.env.user.tz or self.env.context.get("tz")):
            timezone = ZoneInfo(self.company_id.tz or "UTC")
        return value.replace(tzinfo=UTC).astimezone(timezone).date()

    @api.depends("working_start_date")
    def _compute_working_end_date(self):
        for record in self:
            if not record.working_start_date:
                record.working_end_date = False
                continue
            timezone = record.env.tz
            if not (record.env.user.tz or record.env.context.get("tz")):
                timezone = ZoneInfo(record.company_id.tz or "UTC")
            local_start = record.working_start_date.replace(tzinfo=UTC).astimezone(timezone)
            local_end = local_start.replace(hour=23, minute=59, second=59, microsecond=0)
            record.working_end_date = local_end.astimezone(UTC).replace(tzinfo=None)

    @api.constrains("is_exceptional_days", "date_from", "date_to", "working_start_date", "working_end_date")
    def _check_exceptional_day_compensation(self):
        for record in self:
            if not record.is_exceptional_days:
                continue

            if not record.working_start_date or not record.working_end_date:
                raise ValidationError(self.env._("Please set the compensatory off start and end dates."))

            if record.working_end_date < record.working_start_date:
                raise ValidationError(self.env._("Compensatory end date cannot be before the start date."))

            if record._l10n_in_get_local_date(record.date_from) != record._l10n_in_get_local_date(record.date_to):
                raise ValidationError(self.env._("Exceptional working day must be exactly one day."))

            if (
                record._l10n_in_get_local_date(record.working_start_date)
                != record._l10n_in_get_local_date(record.working_end_date)
            ):
                raise ValidationError(self.env._("Compensatory off must be exactly one day."))

            exceptional_day = record._l10n_in_get_local_date(record.date_from)
            compensatory_day = record._l10n_in_get_local_date(record.working_start_date)

            if exceptional_day == compensatory_day:
                raise ValidationError(
                    self.env._("Compensatory off day cannot be the same as the exceptional working day.")
                )

            overlap = self.search([
                ("id", "!=", record.id),
                ("resource_id", "=", False),
                ("date_from", "<=", record.working_end_date),
                ("date_to", ">=", record.working_start_date),
            ], limit=1)

            if overlap:
                raise ValidationError(
                    self.env._("Compensatory off day overlaps with an existing exceptional day or public holiday.")
                )

            calendar = record.calendar_id or self.env.company.resource_calendar_id
            if not calendar._works_on_date(compensatory_day):
                raise ValidationError(
                    self.env._("%s is not a working day, so it cannot be used as a compensatory off day.") % compensatory_day
                )
