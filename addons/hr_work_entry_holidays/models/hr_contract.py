# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz

from odoo import models
from odoo.osv.expression import OR


class HrContract(models.Model):
    _inherit = 'hr.contract'
    _description = 'Employee Contract'

    # override to add work_entry_type from leave
    def _get_leave_work_entry_type(self, leave):
        if leave.holiday_id:
            return leave.holiday_id.holiday_status_id.work_entry_type_id
        else:
            return leave.work_entry_type_id

    def _get_more_vals_leave_interval(self, interval, leaves):
        result = super()._get_more_vals_leave_interval(interval, leaves)
        for leave in leaves:
            if interval[0] >= leave[0] and interval[1] <= leave[1]:
                result.append(('leave_id', leave[2].holiday_id.id))
        return result

    def _get_interval_leave_work_entry_type(self, interval, leaves, bypassing_codes):
        # returns the work entry time related to the leave that
        # includes the whole interval.
        # Overriden in hr_work_entry_contract_holiday to select the
        # global time off first (eg: Public Holiday > Home Working)
        self.ensure_one()
        if 'work_entry_type_id' in interval[2] and interval[2].work_entry_type_id.code in bypassing_codes:
            return interval[2].work_entry_type_id

        interval_start = interval[0].astimezone(pytz.utc).replace(tzinfo=None)
        interval_stop = interval[1].astimezone(pytz.utc).replace(tzinfo=None)
        including_rcleaves = [l[2] for l in leaves if l[2] and interval_start >= l[2].date_from and interval_stop <= l[2].date_to]
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
            return self._get_leave_work_entry_type_dates(rc_leave, interval_start, interval_stop, self.employee_id)
        return self.env.ref('hr_work_entry_contract.work_entry_type_leave')

    def _get_sub_leave_domain(self):
        domain = super()._get_sub_leave_domain()
        return OR([
            domain,
            [('holiday_id.employee_id', 'in', self.employee_id.ids)] # see https://github.com/odoo/enterprise/pull/15091
        ])
