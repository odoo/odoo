# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResourceCalendarLeaves(models.Model):
    _inherit = 'resource.calendar.leaves'

    is_exceptional_days = fields.Boolean("Is Exceptional Day")
    working_start_date = fields.Datetime("Compensatory Off Start Date")
    working_end_date = fields.Datetime("Compensatory Off End Date")

    @api.constrains('is_exceptional_days', 'working_start_date', 'working_end_date')
    def _check_exceptional_day_compensation(self):
        for rec in self:
            if not rec.is_exceptional_days:
                continue

            # Step 1: both dates must be filled
            if not rec.working_start_date or not rec.working_end_date:
                raise ValidationError(self.env._("Please set the compensatory off start and end dates."))

            if rec.working_end_date < rec.working_start_date:
                raise ValidationError(self.env._("Compensatory end date cannot be before the start date."))

            # Step 2: compensatory date can't be the same as the exceptional working date
            if rec.date_from and rec.date_to:
                if rec.working_start_date.date() <= rec.date_to.date() and rec.working_end_date.date() >= rec.date_from.date():
                    raise ValidationError(self.env._("Compensatory off date cannot be the same as the exceptional working date."))

            # Step 3: compensatory date can't already be an exceptional day or a public holiday
            other_records = self.env['resource.calendar.leaves'].search([
                ('id', '!=', rec.id),
                ('resource_id', '=', False),
                ('date_from', '<=', rec.working_end_date),
                ('date_to', '>=', rec.working_start_date),
            ])
            if other_records:
                raise ValidationError(self.env._("Compensatory off date overlaps with an existing exceptional day or public holiday."))

            # Step 4: compensatory date must be a normal working day
            calendar = rec.calendar_id or self.env.company.resource_calendar_id
            current_date = rec.working_start_date.date()
            end_date = rec.working_end_date.date()
            while current_date <= end_date:
                if not calendar._works_on_date(current_date):
                    raise ValidationError(self.env._("%s is not a working day, so it cannot be used as a compensatory off date.") % current_date)
                current_date += timedelta(days=1)
