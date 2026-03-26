# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import models

# Must match the constants in hr_attendance.py
DAILY_MINUTES = 480.0   # 8 hours
DAYS_PER_MONTH = 30.0


class BiometricAttendanceSyncPayroll(models.AbstractModel):
    _inherit = 'biometric.attendance.sync'

    def _sync_attendance_record(self, new_cr, env, emp_id, day, times, emp_tz):
        """After parent sync + KSW_attendance_leave net-column patch,
        compute and persist the payroll deduction fields via SQL so they
        don't rely on an ORM recompute that never fires."""
        created, updated = super()._sync_attendance_record(
            new_cr, env, emp_id, day, times, emp_tz)

        # Fetch employee wage data
        employee = env['hr.employee'].browse(emp_id)
        version = employee.sudo().current_version_id
        if not version:
            return created, updated

        base = (
            (version.wage or 0.0)
            + (version.da or 0.0)
            + (version.travel_allowance or 0.0)
            + (version.meal_allowance or 0.0)
            + (version.medical_allowance or 0.0)
            + (version.other_allowance or 0.0)
        )
        daily_rate = base / DAYS_PER_MONTH
        hourly_rate = daily_rate / (DAILY_MINUTES / 60.0)
        # Update deduction columns via SQL.
        # At this point x_net_late_minutes / x_net_early_leave_minutes /
        # x_net_is_absent have already been set by KSW_attendance_leave's
        # override (which runs before us in the MRO).
        # NOTE: x_currency_id is a `related` field (not stored in DB).
        new_cr.execute(
            "UPDATE hr_attendance "
            "SET x_deductible_base = %s, "
            "    x_daily_rate = %s, "
            "    x_hourly_rate = %s, "
            "    x_scheduled_minutes = %s, "
            "    x_deduction_amount = CASE "
            "        WHEN x_net_is_absent THEN %s "
            "        ELSE LEAST("
            "            (COALESCE(x_net_late_minutes, 0) "
            "             + COALESCE(x_net_early_leave_minutes, 0)) "
            "            / %s * %s, "
            "            %s"
            "        ) "
            "    END "
            "WHERE employee_id = %s "
            "  AND check_in >= %s AND check_in < %s",
            (
                base, daily_rate, hourly_rate, DAILY_MINUTES,
                daily_rate,                          # absent → full daily rate
                DAILY_MINUTES, daily_rate, daily_rate,  # partial → capped
                emp_id,
                day.strftime("%Y-%m-%d"),
                (day + timedelta(days=1)).strftime("%Y-%m-%d"),
            ),
        )

        return created, updated


