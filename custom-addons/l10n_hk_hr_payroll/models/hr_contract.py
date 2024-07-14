# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz

from odoo import fields, models


class HrContract(models.Model):
    _inherit = "hr.contract"

    l10n_hk_internet = fields.Monetary(
        string="HK: Internet Subscription",
        tracking=True,
        help="A benefit in kind is paid for the employee's internet subcription.")

    def _get_bypassing_work_entry_type_codes(self):
        return super()._get_bypassing_work_entry_type_codes() + [
            'HKLEAVE210',  # Maternity Leave
            'HKLEAVE211',  # Maternity Leave 80%
            'HKLEAVE220',  # Paternity Leave
        ]

    def _get_interval_leave_work_entry_type(self, interval, leaves, bypassing_codes):
        self.ensure_one()
        if not self._is_struct_from_country('HK'):
            return super()._get_interval_leave_work_entry_type(interval, leaves, bypassing_codes)

        interval_start = interval[0].astimezone(pytz.utc).replace(tzinfo=None)
        interval_stop = interval[1].astimezone(pytz.utc).replace(tzinfo=None)

        including_rcleaves = [leave[2] for leave in leaves if leave[2] and interval_start >= leave[2].date_from and interval_stop <= leave[2].date_to]
        including_global_rcleaves = [leave for leave in including_rcleaves if not leave.holiday_id]
        including_holiday_rcleaves = [leave for leave in including_rcleaves if leave.holiday_id]
        statutory_holiday_rcleaves = [leave for leave in including_global_rcleaves if leave.work_entry_type_id.code == 'HKLEAVE500']

        bypassing_rc_leave = False
        if bypassing_codes:
            bypassing_rc_leave = [leave for leave in including_holiday_rcleaves if leave.holiday_id.holiday_status_id.work_entry_type_id.code in bypassing_codes]
        bypassing_weekend_codes = ['LEAVE90', 'LEAVE110', 'HKLEAVE111']
        bypassing_weekend_rc_leave = [leave for leave in including_holiday_rcleaves if leave.holiday_id.holiday_status_id.work_entry_type_id.code in bypassing_weekend_codes]

        # Maternity Leave, Paternity Leave > Statutory Holiday > Unpaid Leave, Sick Leave > Public Holiday
        rc_leave = False
        if bypassing_rc_leave:
            rc_leave = bypassing_rc_leave[0]
        elif statutory_holiday_rcleaves:
            rc_leave = statutory_holiday_rcleaves[0]
        elif bypassing_weekend_rc_leave:
            rc_leave = bypassing_weekend_rc_leave[0]
        elif including_global_rcleaves:
            rc_leave = including_global_rcleaves[0]
        if rc_leave:
            return self._get_leave_work_entry_type_dates(rc_leave, interval_start, interval_stop, self.employee_id)

        # Weekend > Other Leave > AL
        if 'work_entry_type_id' in interval[2] and interval[2].work_entry_type_id.code == 'HKLEAVE600':
            return interval[2].work_entry_type_id
        if including_holiday_rcleaves:
            return self._get_leave_work_entry_type_dates(including_holiday_rcleaves[0], interval_start, interval_stop, self.employee_id)
        return self.env.ref('hr_work_entry_contract.work_entry_type_leave')

    def _get_fields_that_recompute_payslip(self):
        return super()._get_fields_that_recompute_payslip() + ['l10n_hk_internet']
