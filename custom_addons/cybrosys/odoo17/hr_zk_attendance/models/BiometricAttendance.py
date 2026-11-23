from odoo import models, fields, api
from datetime import datetime, timedelta
import pytz
import logging

_logger = logging.getLogger(__name__)

class BiometricAttendance(models.Model):
    _name = 'biometric.attendance'
    _description = 'Biometric Attendance Sync'

    def get_biometric_data(self):
        """Placeholder method to fetch data from biometric device"""
        # This should be implemented based on your biometric device integration
        return []

    def sync_attendance(self):
        """Sync attendance data from biometric device"""
        biometric_data = self.get_biometric_data()

        for record in biometric_data:
            employee = self.env['hr.employee'].search([('biometric_id', '=', record['user_id'])])
            if not employee:
                continue

            # Convert biometric timestamp to UTC
            local_tz = pytz.timezone(employee.tz or 'UTC')
            local_timestamp = local_tz.localize(datetime.strptime(record['timestamp'], "%Y-%m-%d %H:%M:%S"))
            utc_timestamp = local_timestamp.astimezone(pytz.utc)

            # Use work day logic instead of calendar date
            # If timestamp is before 6 AM, it belongs to the previous work day
            shift_boundary_hour = 6
            if utc_timestamp.hour < shift_boundary_hour:
                work_date = (utc_timestamp - timedelta(days=1)).date()
                _logger.info(f"Employee {employee.name}: Timestamp {utc_timestamp} assigned to work day {work_date} (overnight shift)")
            else:
                work_date = utc_timestamp.date()
                _logger.info(f"Employee {employee.name}: Timestamp {utc_timestamp} assigned to work day {work_date} (regular shift)")

            # Find or create attendance for the work day
            attendance = self.env['hr.attendance'].search([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', work_date),
                ('check_in', '<', work_date + timedelta(days=1)),
            ], limit=1)

            if attendance:
                # Update check_in if the new timestamp is earlier
                if utc_timestamp < attendance.check_in:
                    _logger.info(f"Updating check_in for {employee.name} from {attendance.check_in} to {utc_timestamp}")
                    attendance.check_in = utc_timestamp
                # Update check_out if the new timestamp is later
                if not attendance.check_out or utc_timestamp > attendance.check_out:
                    _logger.info(f"Updating check_out for {employee.name} from {attendance.check_out} to {utc_timestamp}")
                    attendance.check_out = utc_timestamp

                # Log if this is an overnight shift
                if attendance.check_out and attendance.check_out.date() != attendance.check_in.date():
                    _logger.info(f"OVERNIGHT SHIFT DETECTED: Employee {employee.name}, Work day {work_date}: {attendance.check_in} to {attendance.check_out}")
            else:
                # Create new attendance record
                self.env['hr.attendance'].create({
                    'employee_id': employee.id,
                    'check_in': utc_timestamp,
                    'check_out': False,
                })
                _logger.info(f"Created new attendance for {employee.name} on work day {work_date}: check_in={utc_timestamp}")
