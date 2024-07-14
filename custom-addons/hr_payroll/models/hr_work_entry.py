# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import datetime, date, time
import pytz

from odoo import fields, models, _
from odoo.exceptions import UserError

class HrWorkEntry(models.Model):
    _inherit = 'hr.work.entry'

    is_credit_time = fields.Boolean(
        string='Credit time', readonly=True,
        help="This is a credit time work entry.")

    def _get_leaves_entries_outside_schedule(self):
        return super()._get_leaves_entries_outside_schedule().filtered(lambda w: not w.is_credit_time)

    def _get_duration_is_valid(self):
        return super()._get_duration_is_valid() and not self.is_credit_time

    def _get_work_duration(self, date_start, date_stop):
        """
        Returns the amount of hours worked from date_start to date_stop related to the work entry.

        This method is meant to be overriden, see hr_work_entry_contract_attendance
        """
        dt = date_stop - date_start
        return dt.days * 24 + dt.seconds / 3600

    def _check_undefined_slots(self, interval_start, interval_end):
        """
        Check if a time slot in the given interval is not covered by a work entry
        """
        work_entries_by_contract = defaultdict(lambda: self.env['hr.work.entry'])
        for work_entry in self:
            work_entries_by_contract[work_entry.contract_id] |= work_entry

        for contract, work_entries in work_entries_by_contract.items():
            if contract.work_entry_source != 'calendar':
                continue
            tz = pytz.timezone(contract.resource_calendar_id.tz)
            calendar_start = tz.localize(datetime.combine(max(contract.date_start, interval_start), time.min))
            calendar_end = tz.localize(datetime.combine(min(contract.date_end or date.max, interval_end), time.max))
            outside = contract.resource_calendar_id._attendance_intervals_batch(calendar_start, calendar_end)[False] - work_entries._to_intervals()
            if outside:
                time_intervals_str = "\n - ".join(['', *["%s -> %s" % (s[0], s[1]) for s in outside._items]])
                employee_name = contract.employee_id.name
                msg = _("Watch out for gaps in %(employee_name)s's calendar\n\nPlease complete the missing work entries of %(employee_name)s:%(time_intervals_str)s "
                    "\n\nMissing work entries are like the Bermuda Triangle for paychecks. Let's keep your colleague's earnings from vanishing into thin air!"
                    , employee_name=employee_name, time_intervals_str=time_intervals_str)
                raise UserError(msg)
