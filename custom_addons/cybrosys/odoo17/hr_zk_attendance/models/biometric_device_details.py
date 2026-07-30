# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Ammu Raj (odoo@cybrosys.com)
#
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3)
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
################################################################################
import logging
import pytz
import time
from datetime import datetime as dt, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from zk import ZK, const
from psycopg2 import OperationalError

_logger = logging.getLogger(__name__)


class BiometricDeviceDetails(models.Model):
    _name = 'biometric.device.details'
    _description = 'Biometric Device Details'

    name = fields.Char(string='Name', required=True, help='Record Name')
    device_ip = fields.Char(string='Device IP', required=True, help='The IP address of the Device')
    port_number = fields.Integer(string='Port Number', required=True, help='The Port Number of the Device')
    tz = fields.Selection(
        selection='_get_tz_list',
        string='Device Timezone',
        default='Asia/Riyadh',  # Set to your device's timezone (UTC+3)
        help='Timezone of the biometric device'
    )
    last_download_time = fields.Datetime(string='Last Download Time', help='Last time attendance was downloaded')
    download_batch_size = fields.Integer(string='Download Batch Size', default=1000,
                                        help='Maximum number of records to download in a single batch')
    download_timeout = fields.Integer(string='Download Timeout', default=60,
                                     help='Timeout in seconds for download operation')
    auto_download = fields.Boolean(string='Auto Download', default=True,
                                  help='Enable automatic download via scheduled actions')
    year_filter = fields.Selection(
        selection=lambda self: [(str(year), str(year)) for year in range(2018, dt.now().year + 1)],
        string='Year Filter',
        default=lambda self: str(dt.now().year),
        help='Filter attendance data by year to reduce processing time and prevent timeouts'
    )

    address_id = fields.Many2one('res.partner', string='Working Address', help='Working address of the partner')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id.id,
                                 help='Current Company')

    @api.model
    def _get_tz_list(self):
        """Populate timezone selection with all available timezones"""
        return [(tz, tz) for tz in pytz.all_timezones]


    def device_connect(self, zk):
        """Connect to the biometric device"""
        try:
            conn = zk.connect()
            return conn
        except Exception as e:
            _logger.error(f"Connection failed: {e}")
            return False

    def action_test_connection(self):
        """Test device connectivity"""
        zk = ZK(self.device_ip, port=self.port_number, timeout=30, password=False, ommit_ping=False)
        if self.device_connect(zk):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'Successfully Connected',
                    'type': 'success',
                    'sticky': False
                }
            }
        else:
            raise UserError(_("Connection Failed. Check IP/Port."))


    def action_clear_attendance(self):
        """Clear attendance logs from device and Odoo"""
        for info in self:
            machine_ip = info.device_ip
            zk_port = info.port_number
            zk = ZK(machine_ip, port=zk_port, timeout=30, password=False, force_udp=False, ommit_ping=False)
            conn = self.device_connect(zk)
            if conn:
                conn.enable_device()
                clear_data = zk.get_attendance()
                if clear_data:
                    conn.clear_attendance()
                    self._cr.execute("DELETE FROM zk_machine_attendance")
                    conn.disconnect()
                else:
                    raise UserError(_('Attendance log is empty.'))
            else:
                raise UserError(_('Unable to connect to the device.'))

    def action_download_attendance(self, incremental=True, force=False):
        """Download attendance logs from the device"""
        if not self.device_ip:
            raise UserError(_("Please configure IP address for the device."))

        if not force and not self.auto_download:
            _logger.info(f"Auto download not enabled for device {self.name}")
            return

        # Store device name at the beginning to avoid accessing in a failed transaction later
        device_name = self.name
        device_id = self.id

        # Create counters for tracking results
        total_created = 0
        total_updated = 0

        # Start with a clean transaction
        self.env.cr.commit()

        try:
            biometric_data = self.get_biometric_attendance(incremental=incremental)
            _logger.info(f"Retrieved {len(biometric_data)} attendance records to process")
        except Exception as e:
            _logger.error(f"Failed to fetch attendance data: {e}", exc_info=True)
            raise UserError(_("Failed to fetch attendance data: %s" % e))

        grouped_data = {}

        # Process and group the data
        for record in biometric_data:
            timestamp = dt.strptime(record['timestamp'], "%Y-%m-%d %H:%M:%S")
            biometric_user_id = record['user_id']

            employee = self.env['hr.employee'].search([
                ('biometric_user_id', '=', biometric_user_id)
            ], limit=1)

            if not employee:
                _logger.warning(f"No employee found for biometric ID: {biometric_user_id}")
                continue

            # NEW: Enhanced grouping logic for night shifts
            # Check if employee has night shift calendar (calendar ID 17 or very specific pattern detection)
            employee_calendar = employee.resource_calendar_id or employee.company_id.resource_calendar_id
            is_night_shift_employee = False
            
            if employee_calendar:
                # Primary check: Only calendar 17 is definitively night shift
                if employee_calendar.id == 17:
                    is_night_shift_employee = True
                    _logger.info(f"Employee {employee.name} identified as night shift (Calendar ID 17)")
                else:
                    # VERY RESTRICTIVE secondary check: Only if it's clearly an overnight shift pattern
                    # Must have start time > end time AND start after 20:00 (8 PM)
                    schedules = self.env['resource.calendar.attendance'].search([
                        ('calendar_id', '=', employee_calendar.id),
                        ('day_period', '!=', 'lunch')
                    ])

                    night_patterns = 0
                    total_schedules = len(schedules)

                    for schedule in schedules:
                        # Only count as night shift if:
                        # 1. Start time > end time (crosses midnight) AND
                        # 2. Start time is after 8 PM (20:00) AND
                        # 3. End time is before 10 AM (10:00)
                        if (schedule.hour_from > schedule.hour_to and
                            schedule.hour_from >= 20.0 and
                            schedule.hour_to <= 10.0):
                            night_patterns += 1

                    # Only consider night shift if MAJORITY of schedules follow night pattern
                    if night_patterns > 0 and night_patterns >= (total_schedules * 0.7):
                        is_night_shift_employee = True
                        _logger.info(f"Employee {employee.name} identified as night shift by pattern "
                                   f"({night_patterns}/{total_schedules} overnight schedules)")
                    else:
                        _logger.info(f"Employee {employee.name} is regular day shift "
                                   f"(Calendar: {employee_calendar.name}, ID: {employee_calendar.id})")

            # Use different grouping logic based on shift type
            if is_night_shift_employee:
                # For night shift employees: Use 12 PM boundary for work day grouping
                # Any punch before 12 PM belongs to previous work day
                if timestamp.hour < 12:
                    date_key = (timestamp - timedelta(days=1)).date()
                    _logger.info(f"Night shift employee {employee.name}: Punch {timestamp} assigned to work day {date_key}")
                else:
                    date_key = timestamp.date()
                    _logger.info(f"Night shift employee {employee.name}: Punch {timestamp} assigned to work day {date_key}")
            else:
                # For regular employees: Use normal calendar date grouping
                date_key = timestamp.date()

            if employee.id not in grouped_data:
                grouped_data[employee.id] = {}
            if date_key not in grouped_data[employee.id]:
                grouped_data[employee.id][date_key] = {
                    'check_in': timestamp,
                    'check_out': timestamp,
                    'timestamps': [timestamp],
                    'is_night_shift': is_night_shift_employee
                }
            else:
                if timestamp < grouped_data[employee.id][date_key]['check_in']:
                    grouped_data[employee.id][date_key]['check_in'] = timestamp
                if timestamp > grouped_data[employee.id][date_key]['check_out']:
                    grouped_data[employee.id][date_key]['check_out'] = timestamp
                grouped_data[employee.id][date_key]['timestamps'].append(timestamp)

        # Log validation information for overnight shifts
        for emp_id, days_data in grouped_data.items():
            employee = self.env['hr.employee'].browse(emp_id)
            for work_date, times in days_data.items():
                check_in = times['check_in']
                check_out = times['check_out']
                all_timestamps = sorted(times['timestamps'])

                if check_out.date() != check_in.date():
                    _logger.info(f"OVERNIGHT SHIFT: Employee {employee.name}, Work day {work_date}: {check_in} to {check_out}")
                    _logger.info(f"  All timestamps: {[str(ts) for ts in all_timestamps]}")

        _logger.info(f"Grouped data for {len(grouped_data)} employees with overnight shift support")

        # Process employees in chunks to avoid server timeouts
        employee_ids = list(grouped_data.keys())
        employee_batch_size = 5  # Process 5 employees at a time
        day_batch_size = 20      # Process 20 days at a time for each employee

        for emp_chunk_start in range(0, len(employee_ids), employee_batch_size):
            emp_chunk_end = min(emp_chunk_start + employee_batch_size, len(employee_ids))
            employee_chunk = employee_ids[emp_chunk_start:emp_chunk_end]

            _logger.info(f"Processing employee chunk {emp_chunk_start+1} to {emp_chunk_end} of {len(employee_ids)}")

            # Clean up any leftover connections and commit current transaction
            self.env.cr.commit()

            # Process each employee in the chunk
            for emp_id in employee_chunk:
                try:
                    # Create a new environment and cursor for each employee
                    new_cr = self.pool.cursor()
                    try:
                        # Create a new environment with the new cursor
                        env = api.Environment(new_cr, self.env.uid, self.env.context)

                        employee = env['hr.employee'].browse(emp_id)
                        _logger.info(f"Processing attendance for employee ID {emp_id}")

                        employee_updated = 0
                        employee_created = 0

                        # Process in smaller sub-batches to avoid timeouts
                        day_items = list(grouped_data[emp_id].items())

                        for i in range(0, len(day_items), day_batch_size):
                            sub_batch = day_items[i:i+day_batch_size]
                            sub_batch_updated = 0
                            sub_batch_created = 0

                            _logger.info(f"Processing days {i+1} to {min(i+day_batch_size, len(day_items))} of {len(day_items)} for employee ID {emp_id}")

                            # Create a savepoint for this sub-batch
                            new_cr.execute("SAVEPOINT batch_savepoint")

                            try:
                                for day, times in sub_batch:
                                    # Search existing attendance with a simpler query to reduce load
                                    attendance = env['hr.attendance'].search([
                                        ('employee_id', '=', emp_id),
                                        ('check_in', '>=', day),
                                        ('check_in', '<', day + timedelta(days=1)),
                                    ], limit=1)

                                    if attendance:
                                        # Update existing record with direct SQL for efficiency
                                        try:
                                            # Use SQL to first retrieve the current values
                                            new_cr.execute("""
                                            SELECT check_in, check_out FROM hr_attendance WHERE id = %s
                                            """, (attendance.id,))
                                            result = new_cr.fetchone()
                                            current_check_in = result[0]
                                            current_check_out = result[1]

                                            # Convert strings to datetime objects if needed
                                            if isinstance(current_check_in, str):
                                                current_check_in = dt.strptime(current_check_in, "%Y-%m-%d %H:%M:%S")
                                            if isinstance(current_check_out, str):
                                                current_check_out = dt.strptime(current_check_out, "%Y-%m-%d %H:%M:%S")

                                            # Determine the earliest check-in time
                                            new_check_in = min(current_check_in, times['check_in']) if current_check_in else times['check_in']

                                            # Determine the latest check-out time
                                            new_check_out = max(current_check_out, times['check_out']) if current_check_out else times['check_out']

                                            # Format datetimes for SQL
                                            check_in_str = new_check_in.strftime("%Y-%m-%d %H:%M:%S")
                                            check_out_str = new_check_out.strftime("%Y-%m-%d %H:%M:%S")

                                            # Update the record with the earliest check-in and latest check-out
                                            query = """
                                            UPDATE hr_attendance 
                                            SET check_in = %s, check_out = %s, write_date = NOW(), write_uid = %s 
                                            WHERE id = %s
                                            """
                                            new_cr.execute(query, (check_in_str, check_out_str, self.env.uid, attendance.id))
                                            sub_batch_updated += 1
                                            _logger.info(f"Updated attendance for employee ID {emp_id} on {day}: " 
                                                        f"check_in: {check_in_str}, check_out: {check_out_str}")
                                        except Exception as e:
                                            _logger.error(f"Error updating attendance for employee ID {emp_id} on {day}: {e}")
                                            continue
                                    else:
                                        # Create new record with direct SQL for efficiency
                                        try:
                                            # Use SQL to bypass complex validations for biometric imports
                                            check_in_str = times['check_in'].strftime("%Y-%m-%d %H:%M:%S")
                                            check_out_str = times['check_out'].strftime("%Y-%m-%d %H:%M:%S")

                                            query = """
                                            INSERT INTO hr_attendance (employee_id, check_in, check_out, create_date, create_uid, write_date, write_uid)
                                            VALUES (%s, %s, %s, NOW(), %s, NOW(), %s)
                                            """
                                            new_cr.execute(query, (emp_id, check_in_str, check_out_str, self.env.uid, self.env.uid))
                                            sub_batch_created += 1
                                        except Exception as e:
                                            _logger.error(f"Error creating attendance for employee ID {emp_id} on {day}: {e}")
                                            continue

                                # Commit this sub-batch
                                new_cr.execute("RELEASE SAVEPOINT batch_savepoint")
                                new_cr.commit()

                                # Update counters
                                employee_updated += sub_batch_updated
                                employee_created += sub_batch_created

                                _logger.info(f"Processed sub-batch for employee ID {emp_id}: {sub_batch_created} created, {sub_batch_updated} updated")

                            except Exception as e:
                                _logger.error(f"Error processing sub-batch for employee ID {emp_id}: {e}")
                                new_cr.execute("ROLLBACK TO SAVEPOINT batch_savepoint")
                                # Continue with next sub-batch

                        # Update counters
                        total_updated += employee_updated
                        total_created += employee_created

                        _logger.info(f"Completed employee ID {emp_id}: {employee_created} created, {employee_updated} updated")

                        # Final commit for this employee
                        new_cr.commit()
                    except Exception as e:
                        _logger.error(f"Error processing employee ID {emp_id}: {e}")
                        new_cr.rollback()
                    finally:
                        new_cr.close()
                except Exception as e:
                    _logger.error(f"Critical error processing employee ID {emp_id}: {e}")
                    # Continue with next employee

            # After each employee chunk, update progress
            _logger.info(f"Completed employee chunk {emp_chunk_start+1} to {emp_chunk_end} of {len(employee_ids)}")
            self.env.cr.commit()  # Commit main transaction to avoid bloat

        # Update last download time with a new cursor to avoid transaction issues
        if not incremental:
            try:
                new_cr = self.pool.cursor()
                try:
                    # Use direct SQL for updating the last_download_time
                    now = fields.Datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    new_cr.execute("""
                        UPDATE biometric_device_details 
                        SET last_download_time = %s, write_date = NOW(), write_uid = %s 
                        WHERE id = %s
                    """, (now, self.env.uid, device_id))
                    new_cr.commit()
                    _logger.info(f"Updated last_download_time for device ID {device_id}")
                except Exception as e:
                    _logger.error(f"Error updating last_download_time: {e}")
                    new_cr.rollback()
                finally:
                    new_cr.close()
            except Exception as e:
                _logger.error(f"Critical error updating last_download_time: {e}")

        _logger.info(f"Attendance sync complete for device ID {device_id}: {total_created} created, {total_updated} updated")

        # Return a success message
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f"Attendance sync complete: {total_created} created, {total_updated} updated",
                'type': 'success',
                'sticky': False
            }
        }

    def action_download_all_attendance(self):
        """Download all attendance logs (manual trigger with force and no cutoff)"""
        self.env.cr.execute("SELECT relname FROM pg_class WHERE relname='hr_attendance'")
        if not self.env.cr.fetchone():
            raise UserError(_("HR Attendance table not found. Please ensure the hr_attendance module is installed."))

        _logger.info("====== STARTING FULL ATTENDANCE DOWNLOAD (MANUAL) ======")
        result = self.action_download_attendance(incremental=False, force=True)
        _logger.info("====== COMPLETED FULL ATTENDANCE DOWNLOAD (MANUAL) ======")
        return result

    def action_download_incremental_attendance(self):
        """Download only new attendance logs since last download (with force)"""
        self.env.cr.execute("SELECT relname FROM pg_class WHERE relname='hr_attendance'")
        if not self.env.cr.fetchone():
            raise UserError(_("HR Attendance table not found. Please ensure the hr_attendance module is installed."))

        _logger.info("====== STARTING INCREMENTAL ATTENDANCE DOWNLOAD (MANUAL) ======")
        result = self.action_download_attendance(incremental=True, force=True)
        _logger.info("====== COMPLETED INCREMENTAL ATTENDANCE DOWNLOAD (MANUAL) ======")
        return result

    @api.model
    def cron_download_incremental(self):
        """
        Cron job to download incremental attendance data from biometric devices.
        Runs 24/7 every 30 minutes without time restrictions and handles all failures gracefully.
        This method NEVER raises exceptions to ensure the cron job continues running reliably.
        """
        cron_start_time = fields.Datetime.now()
        _logger.info("=" * 100)
        _logger.info(f"BIOMETRIC ATTENDANCE CRON JOB STARTED - {cron_start_time}")
        _logger.info("=" * 100)

        success_count = 0
        error_count = 0
        skipped_count = 0
        devices_processed = 0

        try:
            # Get user's timezone from preferences or use UTC
            user = self.env.user
            user_tz = pytz.timezone(user.tz or 'UTC')

            # Convert UTC time to user's timezone (for logging purposes only)
            current_datetime = fields.Datetime.now()
            local_datetime = pytz.utc.localize(current_datetime).astimezone(user_tz)
            current_hour = local_datetime.hour

            _logger.info(f"Current time: {current_datetime} UTC | {local_datetime} {user_tz}")

            # Get all devices with auto_download enabled
            machines = self.env['biometric.device.details'].search([
                ('auto_download', '=', True)
            ])

            _logger.info(f"Found {len(machines)} device(s) with auto_download enabled")

            if not machines:
                _logger.warning("No devices configured for auto-download. Exiting cron job.")
                _logger.info("=" * 100 + "\n")
                return True

            for idx, machine in enumerate(machines, 1):
                devices_processed = idx
                device_name = machine.name
                device_ip = machine.device_ip

                _logger.info(f"\n[{idx}/{len(machines)}] Processing device: {device_name} ({device_ip})")

                # Validate device configuration
                if not device_ip:
                    _logger.warning(f"Device {device_name} has no IP address configured. Skipping.")
                    skipped_count += 1
                    continue

                # Retry logic with exponential backoff
                max_retries = 3
                retry_delays = [5, 15, 30]  # Seconds between retries (5s, 15s, 30s)
                device_success = False

                for attempt in range(max_retries):
                    try:
                        _logger.info(f"  Attempt {attempt + 1}/{max_retries}: Downloading attendance for {device_name}")

                        # Call the main download method with incremental flag
                        machine.action_download_attendance(incremental=True, force=True)

                        device_success = True
                        success_count += 1
                        _logger.info(f"  ✓ Successfully synced attendance for {device_name}")
                        break  # Exit retry loop if successful

                    except OperationalError as e:
                        # Database serialization error - retry with exponential backoff
                        error_msg = str(e)
                        if 'could not serialize access' in error_msg or 'concurrent update' in error_msg.lower():
                            if attempt < max_retries - 1:
                                wait_time = retry_delays[attempt]
                                _logger.warning(
                                    f"  ⚠ Database lock detected (Attempt {attempt + 1}/{max_retries}). "
                                    f"Retrying in {wait_time} seconds..."
                                )
                                time.sleep(wait_time)  # Exponential backoff
                            else:
                                _logger.error(
                                    f"  ✗ Database serialization error after {max_retries} attempts: {e}"
                                )
                                error_count += 1
                        else:
                            _logger.error(f"  ✗ Database error (non-serialization): {e}")
                            error_count += 1
                            break

                    except UserError as e:
                        # Configuration or connection error - don't retry
                        _logger.error(f"  ✗ Configuration/Connection error for {device_name}: {e}")
                        error_count += 1
                        break

                    except Exception as e:
                        # Unexpected error - try once more, then give up
                        if attempt < max_retries - 1:
                            wait_time = retry_delays[attempt]
                            _logger.warning(
                                f"  ⚠ Unexpected error (Attempt {attempt + 1}/{max_retries}): {type(e).__name__}: {e}. "
                                f"Retrying in {wait_time} seconds..."
                            )
                            time.sleep(wait_time)
                        else:
                            _logger.error(f"  ✗ Failed to sync {device_name} after {max_retries} attempts: {type(e).__name__}: {e}")
                            error_count += 1

            # Log summary
            cron_end_time = fields.Datetime.now()
            duration = (cron_end_time - cron_start_time).total_seconds()
            
            _logger.info(f"\n{'=' * 100}")
            _logger.info(f"CRON JOB SUMMARY")
            _logger.info(f"{'=' * 100}")
            _logger.info(f"Start Time: {cron_start_time}")
            _logger.info(f"End Time: {cron_end_time}")
            _logger.info(f"Duration: {duration:.2f} seconds")
            _logger.info(f"Total devices: {len(machines)}")
            _logger.info(f"✓ Successfully synced: {success_count}")
            _logger.info(f"✗ Failed: {error_count}")
            _logger.info(f"⊘ Skipped: {skipped_count}")
            _logger.info(f"Next cron run: In 30 minutes")
            _logger.info(f"{'=' * 100}\n")

            # Log to a file as well for easy monitoring
            try:
                summary = f"[{cron_end_time}] (Duration: {duration:.2f}s) Success: {success_count}, Error: {error_count}, Skipped: {skipped_count}\n"
                log_file = '/tmp/odoo_biometric_cron.log'
                with open(log_file, 'a') as f:
                    f.write(summary)
                _logger.info(f"Summary written to {log_file}")
            except Exception as e:
                _logger.warning(f"Could not write to cron log file: {e}")

            return True

        except Exception as e:
            # CRITICAL: Catch absolutely all errors to ensure cron never crashes
            _logger.error(f"CRITICAL ERROR in cron_download_incremental: {type(e).__name__}: {e}", exc_info=True)
            _logger.error(f"Devices processed before error: {devices_processed}")
            _logger.error("CRON JOB WILL RETRY IN 30 MINUTES")
            _logger.info("=" * 100 + "\n")
            # Return True to prevent cron from being disabled
            return True

    def action_download_attendance(self, incremental=True, force=False):
        """Download attendance logs from the device"""
        if not self.device_ip:
            raise UserError(_("Please configure IP address for the device."))

        if not force and not self.auto_download:
            _logger.info(f"Auto download not enabled for device {self.name}")
            return

        # Store device name at the beginning to avoid accessing in a failed transaction later
        device_name = self.name
        device_id = self.id

        # Create counters for tracking results
        total_created = 0
        total_updated = 0

        # Start with a clean transaction
        self.env.cr.commit()

        try:
            biometric_data = self.get_biometric_attendance(incremental=incremental)
            _logger.info(f"Retrieved {len(biometric_data)} attendance records to process")
        except Exception as e:
            _logger.error(f"Failed to fetch attendance data: {e}", exc_info=True)
            raise UserError(_("Failed to fetch attendance data: %s" % e))

        grouped_data = {}

        # Process and group the data
        for record in biometric_data:
            timestamp = dt.strptime(record['timestamp'], "%Y-%m-%d %H:%M:%S")
            biometric_user_id = record['user_id']

            employee = self.env['hr.employee'].search([
                ('biometric_user_id', '=', biometric_user_id)
            ], limit=1)

            if not employee:
                _logger.warning(f"No employee found for biometric ID: {biometric_user_id}")
                continue

            # NEW: Enhanced grouping logic for night shifts
            # Check if employee has night shift calendar (calendar ID 17 or very specific pattern detection)
            employee_calendar = employee.resource_calendar_id or employee.company_id.resource_calendar_id
            is_night_shift_employee = False

            if employee_calendar:
                # Primary check: Only calendar 17 is definitively night shift
                if employee_calendar.id == 17:
                    is_night_shift_employee = True
                    _logger.info(f"Employee {employee.name} identified as night shift (Calendar ID 17)")
                else:
                    # VERY RESTRICTIVE secondary check: Only if it's clearly an overnight shift pattern
                    # Must have start time > end time AND start after 20:00 (8 PM)
                    schedules = self.env['resource.calendar.attendance'].search([
                        ('calendar_id', '=', employee_calendar.id),
                        ('day_period', '!=', 'lunch')
                    ])

                    night_patterns = 0
                    total_schedules = len(schedules)

                    for schedule in schedules:
                        # Only count as night shift if:
                        # 1. Start time > end time (crosses midnight) AND
                        # 2. Start time is after 8 PM (20:00) AND
                        # 3. End time is before 10 AM (10:00)
                        if (schedule.hour_from > schedule.hour_to and
                            schedule.hour_from >= 20.0 and
                            schedule.hour_to <= 10.0):
                            night_patterns += 1

                    # Only consider night shift if MAJORITY of schedules follow night pattern
                    if night_patterns > 0 and night_patterns >= (total_schedules * 0.7):
                        is_night_shift_employee = True
                        _logger.info(f"Employee {employee.name} identified as night shift by pattern "
                                   f"({night_patterns}/{total_schedules} overnight schedules)")
                    else:
                        _logger.info(f"Employee {employee.name} is regular day shift "
                                   f"(Calendar: {employee_calendar.name}, ID: {employee_calendar.id})")

            # Use different grouping logic based on shift type
            if is_night_shift_employee:
                # For night shift employees: Use 12 PM boundary for work day grouping
                # Any punch before 12 PM belongs to previous work day
                if timestamp.hour < 12:
                    date_key = (timestamp - timedelta(days=1)).date()
                    _logger.info(f"Night shift employee {employee.name}: Punch {timestamp} assigned to work day {date_key}")
                else:
                    date_key = timestamp.date()
                    _logger.info(f"Night shift employee {employee.name}: Punch {timestamp} assigned to work day {date_key}")
            else:
                # For regular employees: Use normal calendar date grouping
                date_key = timestamp.date()

            if employee.id not in grouped_data:
                grouped_data[employee.id] = {}
            if date_key not in grouped_data[employee.id]:
                grouped_data[employee.id][date_key] = {
                    'check_in': timestamp,
                    'check_out': timestamp,
                    'timestamps': [timestamp],
                    'is_night_shift': is_night_shift_employee
                }
            else:
                if timestamp < grouped_data[employee.id][date_key]['check_in']:
                    grouped_data[employee.id][date_key]['check_in'] = timestamp
                if timestamp > grouped_data[employee.id][date_key]['check_out']:
                    grouped_data[employee.id][date_key]['check_out'] = timestamp
                grouped_data[employee.id][date_key]['timestamps'].append(timestamp)

        # Log validation information for overnight shifts
        for emp_id, days_data in grouped_data.items():
            employee = self.env['hr.employee'].browse(emp_id)
            for work_date, times in days_data.items():
                check_in = times['check_in']
                check_out = times['check_out']
                all_timestamps = sorted(times['timestamps'])

                if check_out.date() != check_in.date():
                    _logger.info(f"OVERNIGHT SHIFT: Employee {employee.name}, Work day {work_date}: {check_in} to {check_out}")
                    _logger.info(f"  All timestamps: {[str(ts) for ts in all_timestamps]}")

        _logger.info(f"Grouped data for {len(grouped_data)} employees with overnight shift support")

        # Process employees in chunks to avoid server timeouts
        employee_ids = list(grouped_data.keys())
        employee_batch_size = 5  # Process 5 employees at a time
        day_batch_size = 20      # Process 20 days at a time for each employee

        for emp_chunk_start in range(0, len(employee_ids), employee_batch_size):
            emp_chunk_end = min(emp_chunk_start + employee_batch_size, len(employee_ids))
            employee_chunk = employee_ids[emp_chunk_start:emp_chunk_end]

            _logger.info(f"Processing employee chunk {emp_chunk_start+1} to {emp_chunk_end} of {len(employee_ids)}")

            # Clean up any leftover connections and commit current transaction
            self.env.cr.commit()

            # Process each employee in the chunk
            for emp_id in employee_chunk:
                try:
                    # Create a new environment and cursor for each employee
                    new_cr = self.pool.cursor()
                    try:
                        # Create a new environment with the new cursor
                        env = api.Environment(new_cr, self.env.uid, self.env.context)

                        employee = env['hr.employee'].browse(emp_id)
                        _logger.info(f"Processing attendance for employee ID {emp_id}")

                        employee_updated = 0
                        employee_created = 0

                        # Process in smaller sub-batches to avoid timeouts
                        day_items = list(grouped_data[emp_id].items())

                        for i in range(0, len(day_items), day_batch_size):
                            sub_batch = day_items[i:i+day_batch_size]
                            sub_batch_updated = 0
                            sub_batch_created = 0

                            _logger.info(f"Processing days {i+1} to {min(i+day_batch_size, len(day_items))} of {len(day_items)} for employee ID {emp_id}")

                            # Create a savepoint for this sub-batch
                            new_cr.execute("SAVEPOINT batch_savepoint")

                            try:
                                for day, times in sub_batch:
                                    # Search existing attendance with a simpler query to reduce load
                                    attendance = env['hr.attendance'].search([
                                        ('employee_id', '=', emp_id),
                                        ('check_in', '>=', day),
                                        ('check_in', '<', day + timedelta(days=1)),
                                    ], limit=1)

                                    if attendance:
                                        # Update existing record with direct SQL for efficiency
                                        try:
                                            # Use SQL to first retrieve the current values
                                            new_cr.execute("""
                                            SELECT check_in, check_out FROM hr_attendance WHERE id = %s
                                            """, (attendance.id,))
                                            result = new_cr.fetchone()
                                            current_check_in = result[0]
                                            current_check_out = result[1]

                                            # Convert strings to datetime objects if needed
                                            if isinstance(current_check_in, str):
                                                current_check_in = dt.strptime(current_check_in, "%Y-%m-%d %H:%M:%S")
                                            if isinstance(current_check_out, str):
                                                current_check_out = dt.strptime(current_check_out, "%Y-%m-%d %H:%M:%S")

                                            # Determine the earliest check-in time
                                            new_check_in = min(current_check_in, times['check_in']) if current_check_in else times['check_in']

                                            # Determine the latest check-out time
                                            new_check_out = max(current_check_out, times['check_out']) if current_check_out else times['check_out']

                                            # Format datetimes for SQL
                                            check_in_str = new_check_in.strftime("%Y-%m-%d %H:%M:%S")
                                            check_out_str = new_check_out.strftime("%Y-%m-%d %H:%M:%S")

                                            # Update the record with the earliest check-in and latest check-out
                                            query = """
                                            UPDATE hr_attendance 
                                            SET check_in = %s, check_out = %s, write_date = NOW(), write_uid = %s 
                                            WHERE id = %s
                                            """
                                            new_cr.execute(query, (check_in_str, check_out_str, self.env.uid, attendance.id))
                                            sub_batch_updated += 1
                                            _logger.info(f"Updated attendance for employee ID {emp_id} on {day}: " 
                                                        f"check_in: {check_in_str}, check_out: {check_out_str}")
                                        except Exception as e:
                                            _logger.error(f"Error updating attendance for employee ID {emp_id} on {day}: {e}")
                                            continue
                                    else:
                                        # Create new record with direct SQL for efficiency
                                        try:
                                            # Use SQL to bypass complex validations for biometric imports
                                            check_in_str = times['check_in'].strftime("%Y-%m-%d %H:%M:%S")
                                            check_out_str = times['check_out'].strftime("%Y-%m-%d %H:%M:%S")

                                            query = """
                                            INSERT INTO hr_attendance (employee_id, check_in, check_out, create_date, create_uid, write_date, write_uid)
                                            VALUES (%s, %s, %s, NOW(), %s, NOW(), %s)
                                            """
                                            new_cr.execute(query, (emp_id, check_in_str, check_out_str, self.env.uid, self.env.uid))
                                            sub_batch_created += 1
                                        except Exception as e:
                                            _logger.error(f"Error creating attendance for employee ID {emp_id} on {day}: {e}")
                                            continue

                                # Commit this sub-batch
                                new_cr.execute("RELEASE SAVEPOINT batch_savepoint")
                                new_cr.commit()

                                # Update counters
                                employee_updated += sub_batch_updated
                                employee_created += sub_batch_created

                                _logger.info(f"Processed sub-batch for employee ID {emp_id}: {sub_batch_created} created, {sub_batch_updated} updated")

                            except Exception as e:
                                _logger.error(f"Error processing sub-batch for employee ID {emp_id}: {e}")
                                new_cr.execute("ROLLBACK TO SAVEPOINT batch_savepoint")
                                # Continue with next sub-batch

                        # Update counters
                        total_updated += employee_updated
                        total_created += employee_created

                        _logger.info(f"Completed employee ID {emp_id}: {employee_created} created, {employee_updated} updated")

                        # Final commit for this employee
                        new_cr.commit()
                    except Exception as e:
                        _logger.error(f"Error processing employee ID {emp_id}: {e}")
                        new_cr.rollback()
                    finally:
                        new_cr.close()
                except Exception as e:
                    _logger.error(f"Critical error processing employee ID {emp_id}: {e}")
                    # Continue with next employee

            # After each employee chunk, update progress
            _logger.info(f"Completed employee chunk {emp_chunk_start+1} to {emp_chunk_end} of {len(employee_ids)}")
            self.env.cr.commit()  # Commit main transaction to avoid bloat

        # Update last download time with a new cursor to avoid transaction issues
        if not incremental:
            try:
                new_cr = self.pool.cursor()
                try:
                    # Use direct SQL for updating the last_download_time
                    now = fields.Datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    new_cr.execute("""
                        UPDATE biometric_device_details 
                        SET last_download_time = %s, write_date = NOW(), write_uid = %s 
                        WHERE id = %s
                    """, (now, self.env.uid, device_id))
                    new_cr.commit()
                    _logger.info(f"Updated last_download_time for device ID {device_id}")
                except Exception as e:
                    _logger.error(f"Error updating last_download_time: {e}")
                    new_cr.rollback()
                finally:
                    new_cr.close()
            except Exception as e:
                _logger.error(f"Critical error updating last_download_time: {e}")

        _logger.info(f"Attendance sync complete for device ID {device_id}: {total_created} created, {total_updated} updated")

        # Return a success message
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f"Attendance sync complete: {total_created} created, {total_updated} updated",
                'type': 'success',
                'sticky': False
            }
        }

    def get_biometric_attendance(self, incremental=False):
        """
        Fetch attendance logs from ZKTeco device.

        Args:
            incremental (bool): If True, only fetch logs since last download
        """
        self.ensure_one()
        device_ip = self.device_ip
        device_port = self.port_number
        timeout = self.download_timeout or 60
        zk = ZK(device_ip, port=device_port, timeout=timeout, password=False, force_udp=False)
        conn = None
        logs = []

        _logger.info(f"Starting attendance download from {self.name} ({device_ip}:{device_port}), incremental={incremental}")

        try:
            # Connect with timeout parameter
            _logger.info(f"Connecting to device {self.name}...")
            conn = zk.connect()
            if not conn:
                _logger.error(f"Failed to connect to device {self.name}")
                raise UserError(_("Failed to connect to the device"))
            _logger.info(f"Successfully connected to device {self.name}")

            # Get valid biometric IDs (ones that are assigned to employees)
            employees_with_bio = self.env['hr.employee'].search([
                ('biometric_user_id', '!=', False)
            ])

            # Create a set of valid biometric IDs (both as int and str for flexibility)
            valid_biometric_ids_str = set()
            valid_biometric_ids_int = set()

            for employee in employees_with_bio:
                # Handle the case where biometric_user_id might be a string or an integer
                if isinstance(employee.biometric_user_id, str):
                    valid_biometric_ids_str.add(employee.biometric_user_id)
                    # Try to convert to int if possible
                    try:
                        valid_biometric_ids_int.add(int(employee.biometric_user_id))
                    except (ValueError, TypeError):
                        pass
                else:
                    # Handle numeric IDs
                    valid_biometric_ids_int.add(employee.biometric_user_id)
                    valid_biometric_ids_str.add(str(employee.biometric_user_id))

            _logger.info(f"Found {len(employees_with_bio)} employees with assigned biometric IDs: {sorted(list(valid_biometric_ids_int))}")

            if not valid_biometric_ids_int and not valid_biometric_ids_str:
                _logger.warning("No employees with assigned biometric IDs found. Skipping download.")
                return []

            # Get attendance logs
            _logger.info(f"Fetching attendance logs from device {self.name}...")
            attendance_logs = conn.get_attendance()
            _logger.info(f"Retrieved {len(attendance_logs) if attendance_logs else 0} attendance logs from device")

            if not attendance_logs:
                _logger.info(f"No attendance logs found on device {self.name}")
                return []

            device_tz = pytz.timezone(self.tz or 'UTC')
            cutoff_time = False

            # For incremental downloads, use the last download time
            if incremental and self.last_download_time:
                cutoff_time = self.last_download_time
                _logger.info(f"Using cutoff time for incremental download: {cutoff_time}")

            # Apply year filter
            year_filter = self.year_filter
            if year_filter:
                year_start = dt(int(year_filter), 1, 1)
                year_end = dt(int(year_filter) + 1, 1, 1)
                _logger.info(f"Applying year filter: {year_filter} ({year_start} to {year_end})")
            else:
                # Default to current year if no filter set
                current_year = dt.now().year
                year_start = dt(current_year, 1, 1)
                year_end = dt(current_year + 1, 1, 1)
                _logger.info(f"No year filter set, defaulting to current year: {current_year}")

            processed_count = 0
            skipped_invalid_id_count = 0
            skipped_cutoff_count = 0
            skipped_year_filter_count = 0
            batch_size = self.download_batch_size or 1000

            # Debug - check a sample of biometric IDs from the logs
            sample_ids = []
            for i, log in enumerate(attendance_logs[:10]):
                sample_ids.append(log.user_id)
            _logger.info(f"Sample biometric IDs from device logs: {sample_ids}")

            for log in attendance_logs:
                # Skip processing if we've reached the batch size limit
                if processed_count >= batch_size:
                    _logger.info(f"Reached batch size limit of {batch_size} records")
                    break

                # Check if biometric ID exists in valid IDs (either as int or str)
                log_user_id = log.user_id
                if log_user_id not in valid_biometric_ids_int and str(log_user_id) not in valid_biometric_ids_str:
                    skipped_invalid_id_count += 1
                    continue

                # Convert timestamp to UTC (naive datetime)
                if not log.timestamp.tzinfo:
                    localized_time = device_tz.localize(log.timestamp)
                else:
                    localized_time = log.timestamp.astimezone(device_tz)

                utc_time = localized_time.astimezone(pytz.utc).replace(tzinfo=None)

                # Apply year filter
                if utc_time < year_start or utc_time >= year_end:
                    skipped_year_filter_count += 1
                    continue

                # Skip records before the cutoff time for incremental downloads
                if cutoff_time and utc_time <= cutoff_time:
                    skipped_cutoff_count += 1
                    continue

                logs.append({
                    'user_id': log_user_id,
                    'timestamp': utc_time.strftime("%Y-%m-%d %H:%M:%S"),
                })
                processed_count += 1

                # Debug - log some successful matches to understand the format
                if processed_count <= 5:
                    _logger.info(f"Successfully matched log: user_id={log_user_id}, timestamp={utc_time}")

            # Update the last download time if we're doing incremental downloads
            if incremental:
                self.last_download_time = fields.Datetime.now()

            _logger.info(f"Download stats: Processed={processed_count}, Skipped (invalid ID)={skipped_invalid_id_count}, Skipped (year filter)={skipped_year_filter_count}, Skipped (old records)={skipped_cutoff_count}")
            if not logs:
                _logger.info("No new attendance data found for assigned biometric IDs")

            return logs

        except Exception as e:
            _logger.error(f"Error fetching logs from {self.name}: {e}", exc_info=True)
            raise UserError(_("Failed to fetch attendance logs: %s") % e)
        finally:
            if conn:
                conn.disconnect()
                _logger.info(f"Disconnected from device {self.name}")

    def action_restart_device(self):
        """Restart the biometric device"""
        zk = ZK(self.device_ip, port=self.port_number, timeout=15, password=False, force_udp=False, ommit_ping=False)
        conn = self.device_connect(zk)
        if conn:
            conn.restart()
            conn.disconnect()
        else:
            raise UserError(_("Connection Failed. Check IP/Port."))

    def get_unmapped_biometric_ids(self):
        """Get a list of biometric IDs from the device that aren't mapped to employees"""
        self.ensure_one()

        # Connect to the device and get all user IDs
        device_ip = self.device_ip
        device_port = self.port_number
        timeout = self.download_timeout or 60
        zk = ZK(device_ip, port=device_port, timeout=timeout, password=False, force_udp=False)
        conn = None
        biometric_ids = []

        try:
            conn = zk.connect()
            if not conn:
                raise UserError(_("Failed to connect to the device"))

            # Get all users from the device
            users = conn.get_users()
            if not users:
                return []

            # Extract all biometric IDs
            for user in users:
                biometric_ids.append(str(user.user_id))

            # Find which biometric IDs are already mapped
            mapped_ids = self.env['hr.employee'].search([
                ('biometric_user_id', 'in', biometric_ids)
            ]).mapped('biometric_user_id')

            # Return only unmapped IDs
            return list(set(biometric_ids) - set(mapped_ids))

        except Exception as e:
            _logger.error("Error fetching users: %s", e)
            raise UserError(_("Failed to fetch users from the device: %s") % e)
        finally:
            if conn:
                conn.disconnect()

    def action_map_biometric_ids(self):
        """Open wizard to map biometric IDs to employees"""
        self.ensure_one()

        # Get unmapped biometric IDs
        unmapped_ids = self.get_unmapped_biometric_ids()
        if not unmapped_ids:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('All biometric IDs are already mapped to employees.'),
                    'type': 'info',
                    'sticky': False
                }
            }

        # Open the mapping wizard
        return {
            'name': _('Map Biometric IDs to Employees'),
            'type': 'ir.actions.act_window',
            'res_model': 'biometric.mapping.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_device_id': self.id,
            }
        }

    def get_all_biometric_ids(self):
        """Get a list of all biometric IDs from the device"""
        self.ensure_one()

        # Connect to the device and get all user IDs
        device_ip = self.device_ip
        device_port = self.port_number
        timeout = self.download_timeout or 60
        zk = ZK(device_ip, port=device_port, timeout=timeout, password=False, force_udp=False)
        conn = None
        biometric_ids = []

        try:
            conn = zk.connect()
            if not conn:
                raise UserError(_("Failed to connect to the device"))

            # Get all users from the device
            users = conn.get_users()
            if not users:
                return []

            # Extract all biometric IDs
            for user in users:
                biometric_ids.append(str(user.user_id))

            return biometric_ids

        except Exception as e:
            _logger.error("Error fetching users: %s", e)
            raise UserError(_("Failed to fetch users from the device: %s") % e)
        finally:
            if conn:
                conn.disconnect()
