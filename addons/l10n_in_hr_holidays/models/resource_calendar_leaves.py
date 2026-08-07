# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResourceCalendarLeaves(models.Model):
    _inherit = "resource.calendar.leaves"

    is_exceptional_days = fields.Boolean("Is Exceptional Day")
    working_start_date = fields.Datetime("Compensatory Off Start Date")
    working_end_date = fields.Datetime("Compensatory Off End Date")

    @api.constrains("is_exceptional_days", "date_from", "date_to", "working_start_date", "working_end_date")
    def _check_exceptional_day_compensation(self):
        for record in self:
            if not record.is_exceptional_days:
                continue

            if not record.working_start_date or not record.working_end_date:
                raise ValidationError(self.env._("Please set the compensatory off start and end dates."))

            if record.working_end_date < record.working_start_date:
                raise ValidationError(self.env._("Compensatory end date cannot be before the start date."))

            if record.date_from.date() != record.date_to.date():
                raise ValidationError(self.env._("Exceptional working day must be exactly one day."))

            if record.working_start_date.date() != record.working_end_date.date():
                raise ValidationError(self.env._("Compensatory off must be exactly one day."))

            exceptional_day = record.date_from.date()
            compensatory_day = record.working_start_date.date()

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
