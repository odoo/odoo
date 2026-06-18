# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, models

# ZK device clocks routinely drift behind the Odoo server clock.  If a
# punch happens within this window of the last cron run, its UTC timestamp
# can fall at-or-before `last_download_time` and be silently skipped by the
# `utc_time <= cutoff_time` filter — permanently, because the cutoff only
# moves forward.  Re-processing the last N hours is harmless: the SQL upsert
# in `_sync_attendance_record` will just UPDATE existing rows to the same
# values.
_INCREMENTAL_LOOKBACK_HOURS = 4


class BiometricAttendanceSyncKSW(models.AbstractModel):
    _inherit = 'biometric.attendance.sync'

    @api.model
    def _process_raw_logs(self, attendance_logs, valid_bio_ids, device_tz,
                          cutoff_time, year_start, year_end, batch_size):
        """Apply a lookback buffer to the incremental cutoff.

        Shifts the effective cutoff back by _INCREMENTAL_LOOKBACK_HOURS so
        records whose device-side timestamp is slightly earlier than
        `last_download_time` (due to clock drift) are always re-fetched.
        """
        if cutoff_time:
            cutoff_time = cutoff_time - timedelta(hours=_INCREMENTAL_LOOKBACK_HOURS)
        return super()._process_raw_logs(
            attendance_logs, valid_bio_ids, device_tz,
            cutoff_time, year_start, year_end, batch_size)

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
