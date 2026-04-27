# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from datetime import datetime, timedelta, time


class ResourceCalendarInherit(models.Model):
    _inherit = 'resource.calendar'

    def _handle_flexible_leave_interval(self, dt0, dt1, leave):
        """
        Adjusts the start and end datetime for flexible leave intervals.
        If the leave has half-day granularity, it sets the hours accordingly.
        Otherwise, it sets the start to 00:00 and the end to 23:59.
        """
        leave_data = self.env['hr.leave'].search([
            ('employee_id', '=', leave.resource_id.employee_id.id),
            ('request_date_from', '=', leave.date_from),
            ('request_date_to', '=', leave.date_to),
            ('state', '!=', 'refuse'),
            ('request_unit_half', '=', True),
        ])
        # Check if the leave contains a half-day granularity
        tz = dt0.tzinfo
        if len(leave_data) == 1 and leave_data.request_date_from_period:
            if leave_data.request_date_from_period == 'am':
                dt0 = datetime.combine(dt0.date(), time.min).replace(tzinfo=tz)
                dt1 = datetime.combine(dt1.date(), time.min).replace(hour=12, tzinfo=tz)
            elif leave_data.request_date_from_period == 'pm':
                dt0 = datetime.combine(dt0.date(), time.min).replace(hour=12, tzinfo=tz)
                dt1 = datetime.combine(dt1.date(), time.max).replace(tzinfo=tz)
            return dt0, dt1
        return super()._handle_flexible_leave_interval(dt0, dt1, leave)
