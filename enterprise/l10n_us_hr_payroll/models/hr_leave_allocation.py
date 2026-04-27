# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import models


class HolidaysAllocation(models.Model):
    _inherit = "hr.leave.allocation"

    def _l10n_us_get_total_allocated(self, date):
        total_allocated_hours = 0
        for alloc in self:
            if alloc.date_from > date:
                continue

            number_of_days_field_id = self.env['ir.model.fields']._get(alloc._name, 'number_of_days').id
            value_changes = alloc.message_ids.tracking_value_ids.filtered_domain([
                ('field_id', '=', number_of_days_field_id),
                ('create_date', '<=', date + relativedelta(hour=23, minute=59, second=59)),
            ]).sorted(key=lambda x: x.create_date)

            total_allocated_days = value_changes[-1].new_value_float if value_changes else alloc.number_of_days
            hours_per_day = alloc.employee_id._get_calendars(date)[alloc.employee_id.id].hours_per_day or 8.0
            total_allocated_hours += total_allocated_days * hours_per_day
        return total_allocated_hours
