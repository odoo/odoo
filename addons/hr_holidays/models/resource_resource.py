# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

from odoo import fields, models
from odoo.tools import babel_locale_parse
from odoo.tools.date_utils import weeknumber


class ResourceResource(models.Model):
    _inherit = "resource.resource"

    leave_date_to = fields.Date(related="user_id.leave_date_to")

    def _format_leave(self, leave, resource_hours_per_day, resource_hours_per_week, ranges_to_remove, start_day, end_day, locale):
        leave_start = leave[0]
        leave_record = leave[2]
        holiday_id = leave_record.holiday_id
        tz = ZoneInfo(self.tz or self.env.user.tz)

        if holiday_id.work_entry_type_request_unit == 'half_day':
            # Half day leaves are limited to half a day within a single day
            leave_day = leave_start.date()
            half_start_datetime = datetime.combine(leave_day, datetime.min.time() if holiday_id.request_date_from_period == "am" else time(12), tzinfo=tz)
            half_end_datetime = datetime.combine(leave_day, time(12) if holiday_id.request_date_from_period == "am" else datetime.max.time(), tzinfo=tz)
            ranges_to_remove.append((half_start_datetime, half_end_datetime, self.env['resource.calendar.attendance']))

            if not self._is_fully_flexible():
                # only days inside the original period
                if start_day <= leave_day <= end_day:
                    resource_hours_per_day[self.id][leave_day] -= holiday_id.number_of_hours
                week = weeknumber(babel_locale_parse(locale), leave_day)
                resource_hours_per_week[self.id][week] -= holiday_id.number_of_hours
        elif holiday_id.work_entry_type_request_unit == 'hour':
            # Custom leaves are limited to a specific number of hours within a single day
            leave_day = leave_start.date()
            range_start_datetime = leave_record.date_from.replace(tzinfo=UTC).astimezone(tz)
            range_end_datetime = leave_record.date_to.replace(tzinfo=UTC).astimezone(tz)
            ranges_to_remove.append((range_start_datetime, range_end_datetime, self.env['resource.calendar.attendance']))

            if not self._is_fully_flexible():
                # only days inside the original period
                if start_day <= leave_day <= end_day:
                    resource_hours_per_day[self.id][leave_day] -= holiday_id.number_of_hours
                week = weeknumber(babel_locale_parse(locale), leave_day)
                resource_hours_per_week[self.id][week] -= holiday_id.number_of_hours
        else:
            super()._format_leave(leave, resource_hours_per_day, resource_hours_per_week, ranges_to_remove, start_day, end_day, locale)
