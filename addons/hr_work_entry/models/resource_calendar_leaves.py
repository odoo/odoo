# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz

from odoo import models, fields


class ResourceCalendarLeave(models.Model):
    _inherit = 'resource.calendar.leaves'

    work_entry_type_id = fields.Many2one(
        'hr.work.entry.type', 'Work Entry Type',
        groups="hr.group_hr_user")

    def _copy_leave_vals(self):
        res = super()._copy_leave_vals()
        res['work_entry_type_id'] = self.work_entry_type_id.id
        return res

    def _get_leave_work_entry_type_dates(self, date_from, date_to, employee):
        self.ensure_one()
        return self._get_work_entry_type()

    def _get_work_entry_type(self):
        self.ensure_one()
        return self.work_entry_type_id

    # Is used to add more values, for example leave_id (in hr_work_entry_holidays)
    def _get_more_vals_leave_interval(self, interval, leave_intervals):
        return []

    def _get_interval_leave_work_entry_type(self, interval, leave_intervals, employee, bypassing_codes):
        # returns the work entry time related to the leave that
        # includes the whole interval.
        # Overriden in hr_work_entry_contract_holiday to select the
        # global time off first (eg: Public Holiday > Home Working)
        self.ensure_one()
        for leave_interval in leave_intervals:
            if interval[0] >= leave_interval[0] and interval[1] <= leave_interval[1] and leave_interval[2]:
                interval_start = interval[0].astimezone(pytz.utc).replace(tzinfo=None)
                interval_stop = interval[1].astimezone(pytz.utc).replace(tzinfo=None)
                return self._get_leave_work_entry_type_dates(leave_interval[2], interval_start, interval_stop, employee)
        return self.env.ref('hr_work_entry.work_entry_type_leave')
