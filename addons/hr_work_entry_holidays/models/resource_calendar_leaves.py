# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz

from odoo import models, fields


class ResourceCalendarLeave(models.Model):
    _inherit = 'resource.calendar.leaves'

    def _get_work_entry_type(self):
        self.ensure_one()
        return self.holiday_id.holiday_status_id.work_entry_type_id or super()._get_work_entry_type()

    def _get_more_vals_leave_interval(self, interval, leave_intervals):
        result = super()._get_more_vals_leave_interval(interval, leave_intervals)
        for leave_interval in leave_intervals:
            if interval[0] >= leave_interval[0] and interval[1] <= leave_interval[1]:
                result.append(('leave_id', leave_interval[2].holiday_id.id))
        return result

    def _get_interval_leave_work_entry_type(self, interval, leave_intervals, employee, bypassing_codes):
        # returns the work entry time related to the leave that
        # includes the whole interval.
        # Overriden in hr_work_entry_contract_holiday to select the
        # global time off first (eg: Public Holiday > Home Working)
        if 'work_entry_type_id' in interval[2] and interval[2].work_entry_type_id.code in bypassing_codes:
            return interval[2].work_entry_type_id

        interval_start = interval[0].astimezone(pytz.utc).replace(tzinfo=None)
        interval_stop = interval[1].astimezone(pytz.utc).replace(tzinfo=None)
        including_rcleaves = [l[2] for l in leave_intervals if l[2] and interval_start >= l[2].date_from and interval_stop <= l[2].date_to]
        including_global_rcleaves = [l for l in including_rcleaves if not l.holiday_id]
        including_holiday_rcleaves = [l for l in including_rcleaves if l.holiday_id]
        rc_leave = False

        # Example: In CP200: Long term sick > Public Holidays (which is global)
        if bypassing_codes:
            bypassing_rc_leave = [l for l in including_holiday_rcleaves if l.holiday_id.holiday_status_id.work_entry_type_id.code in bypassing_codes]
        else:
            bypassing_rc_leave = []

        if bypassing_rc_leave:
            rc_leave = bypassing_rc_leave[0]
        elif including_global_rcleaves:
            rc_leave = including_global_rcleaves[0]
        elif including_holiday_rcleaves:
            rc_leave = including_holiday_rcleaves[0]
        if rc_leave:
            return rc_leave._get_leave_work_entry_type_dates(interval_start, interval_stop, employee)
        return self.env.ref('hr_work_entry.work_entry_type_leave')
