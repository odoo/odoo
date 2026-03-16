# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import models


class BiometricAttendanceSyncKSW(models.AbstractModel):
    _inherit = 'biometric.attendance.sync'

    def _sync_attendance_record(self, new_cr, env, emp_id, day, times, emp_tz):
        created, updated = super()._sync_attendance_record(
            new_cr, env, emp_id, day, times, emp_tz)

        # Patch net columns = raw columns for the record just inserted/updated.
        # At sync time no approved leave exists, so net == raw.
        new_cr.execute(
            "UPDATE hr_attendance "
            "SET x_net_late_minutes = x_late_minutes, "
            "    x_net_early_leave_minutes = x_early_leave_minutes, "
            "    x_net_worked_hours = worked_hours, "
            "    x_net_is_absent = x_is_absent "
            "WHERE employee_id = %s "
            "  AND check_in >= %s AND check_in < %s",
            (emp_id,
             day.strftime("%Y-%m-%d"),
             (day + timedelta(days=1)).strftime("%Y-%m-%d")))

        return created, updated
