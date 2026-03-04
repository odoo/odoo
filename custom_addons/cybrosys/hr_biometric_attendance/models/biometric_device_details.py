# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Cybrosys Techno Solutions (odoo@cybrosys.com)
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
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    from zk import ZK
except ImportError:
    _logger.error("Please install pyzk library: pip3 install pyzk")
    ZK = None


class BiometricDeviceDetails(models.Model):
    """Model for configuring and connecting biometric devices with Odoo"""
    _name = 'biometric.device.details'
    _description = 'Biometric Device Details'

    name = fields.Char(
        string='Name', required=True, help='Record Name')
    device_ip = fields.Char(
        string='Device IP', required=True,
        help='The IP address of the Device')
    port_number = fields.Integer(
        string='Port Number', required=True,
        help='The Port Number of the Device')
    tz = fields.Selection(
        selection='_get_tz_list',
        string='Device Timezone',
        default='Asia/Riyadh',
        help='Timezone of the biometric device')
    last_download_time = fields.Datetime(
        string='Last Download Time',
        help='Last time attendance was downloaded')
    download_batch_size = fields.Integer(
        string='Download Batch Size', default=1000,
        help='Maximum number of records to download in a single batch')
    download_timeout = fields.Integer(
        string='Download Timeout', default=60,
        help='Timeout in seconds for download operation')
    auto_download = fields.Boolean(
        string='Auto Download', default=True,
        help='Enable automatic download via scheduled actions')
    year_filter = fields.Selection(
        selection=lambda self: [
            (str(year), str(year))
            for year in range(2018, dt.now().year + 1)
        ],
        string='Year Filter',
        default=lambda self: str(dt.now().year),
        help='Filter attendance data by year to reduce processing time')
    address_id = fields.Many2one(
        'res.partner', string='Working Address',
        help='Working address of the partner')
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company,
        help='Current Company')

    @api.model
    def _get_tz_list(self):
        """Populate timezone selection with all available timezones"""
        return [(tz, tz) for tz in pytz.all_timezones]

    # -------------------------------------------------------------------------
    # Device Connection
    # -------------------------------------------------------------------------

    def device_connect(self, zk):
        """Connect to the biometric device"""
        try:
            conn = zk.connect()
            return conn
        except Exception as e:
            _logger.error("Connection failed: %s", e)
            return False

    def action_test_connection(self):
        """Test device connectivity"""
        if not ZK:
            raise UserError(_("pyzk library not installed."))
        zk = ZK(self.device_ip, port=self.port_number, timeout=30,
                password=False, ommit_ping=False)
        if self.device_connect(zk):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('Successfully Connected'),
                    'type': 'success',
                    'sticky': False,
                },
            }
        raise UserError(_("Connection Failed. Check IP/Port."))

    def action_restart_device(self):
        """Restart the biometric device"""
        if not ZK:
            raise UserError(_("pyzk library not installed."))
        zk = ZK(self.device_ip, port=self.port_number, timeout=15,
                password=False, force_udp=False, ommit_ping=False)
        conn = self.device_connect(zk)
        if conn:
            conn.restart()
            conn.disconnect()
        else:
            raise UserError(_("Connection Failed. Check IP/Port."))

    def action_clear_attendance(self):
        """Clear attendance logs from device and Odoo"""
        if not ZK:
            raise UserError(_("pyzk library not installed."))
        for info in self:
            zk = ZK(info.device_ip, port=info.port_number, timeout=30,
                    password=False, force_udp=False, ommit_ping=False)
            conn = self.device_connect(zk)
            if conn:
                conn.enable_device()
                clear_data = zk.get_attendance()
                if clear_data:
                    conn.clear_attendance()
                    self.env.cr.execute("DELETE FROM zk_machine_attendance")
                    conn.disconnect()
                else:
                    raise UserError(_('Attendance log is empty.'))
            else:
                raise UserError(_('Unable to connect to the device.'))

    # -------------------------------------------------------------------------
    # Biometric ID Mapping
    # -------------------------------------------------------------------------

    def get_all_biometric_ids(self):
        """Get a list of all biometric IDs from the device"""
        self.ensure_one()
        if not ZK:
            raise UserError(_("pyzk library not installed."))
        timeout = self.download_timeout or 60
        zk = ZK(self.device_ip, port=self.port_number, timeout=timeout,
                password=False, force_udp=False)
        conn = None
        biometric_ids = []
        try:
            conn = zk.connect()
            if not conn:
                raise UserError(_("Failed to connect to the device"))
            users = conn.get_users()
            if not users:
                return []
            for user in users:
                biometric_ids.append(str(user.user_id))
            return biometric_ids
        except Exception as e:
            _logger.error("Error fetching users: %s", e)
            raise UserError(_("Failed to fetch users: %s") % e)
        finally:
            if conn:
                conn.disconnect()

    def get_unmapped_biometric_ids(self):
        """Get biometric IDs from device that aren't mapped to employees"""
        self.ensure_one()
        all_biometric_ids = self.get_all_biometric_ids()
        if not all_biometric_ids:
            return []
        # Find which IDs are already mapped
        mapped_employees = self.env['hr.employee'].search([
            ('biometric_user_id', '!=', False),
        ])
        mapped_ids = set()
        for emp in mapped_employees:
            mapped_ids.add(str(emp.biometric_user_id))
        return [bid for bid in all_biometric_ids if bid not in mapped_ids]

    def action_map_biometric_ids(self):
        """Open wizard to map biometric IDs to employees"""
        self.ensure_one()
        unmapped_ids = self.get_unmapped_biometric_ids()
        if not unmapped_ids:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('All biometric IDs are already mapped.'),
                    'type': 'info',
                    'sticky': False,
                },
            }
        return {
            'name': _('Map Biometric IDs to Employees'),
            'type': 'ir.actions.act_window',
            'res_model': 'biometric.mapping.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_device_id': self.id},
        }

    # -------------------------------------------------------------------------
    # Attendance Download
    # -------------------------------------------------------------------------

    def get_biometric_attendance(self, incremental=False):
        """Fetch attendance logs from ZKTeco device."""
        self.ensure_one()
        if not ZK:
            raise UserError(_("pyzk library not installed."))
        timeout = self.download_timeout or 60
        zk = ZK(self.device_ip, port=self.port_number, timeout=timeout,
                password=False, force_udp=False)
        conn = None
        logs = []
        _logger.info("Starting attendance download from %s (%s:%s), "
                      "incremental=%s", self.name, self.device_ip,
                      self.port_number, incremental)
        try:
            conn = zk.connect()
            if not conn:
                raise UserError(_("Failed to connect to the device"))
            _logger.info("Connected to device %s", self.name)

            # Get valid biometric IDs (ones assigned to employees)
            employees_with_bio = self.env['hr.employee'].search([
                ('biometric_user_id', '!=', False),
            ])
            valid_ids_int = set()
            valid_ids_str = set()
            for emp in employees_with_bio:
                valid_ids_int.add(emp.biometric_user_id)
                valid_ids_str.add(str(emp.biometric_user_id))
            _logger.info("Found %d employees with biometric IDs: %s",
                          len(employees_with_bio), sorted(valid_ids_int))
            if not valid_ids_int:
                _logger.warning("No employees with biometric IDs. Skipping.")
                return []

            # Get attendance logs
            attendance_logs = conn.get_attendance()
            _logger.info("Retrieved %d logs from device",
                          len(attendance_logs) if attendance_logs else 0)
            if not attendance_logs:
                return []

            device_tz = pytz.timezone(self.tz or 'UTC')
            cutoff_time = False
            if incremental and self.last_download_time:
                cutoff_time = self.last_download_time
                _logger.info("Incremental cutoff: %s", cutoff_time)

            # Year filter
            year_filter = self.year_filter
            if year_filter:
                year_start = dt(int(year_filter), 1, 1)
                year_end = dt(int(year_filter) + 1, 1, 1)
            else:
                current_year = dt.now().year
                year_start = dt(current_year, 1, 1)
                year_end = dt(current_year + 1, 1, 1)

            processed_count = 0
            batch_size = self.download_batch_size or 1000

            for log in attendance_logs:
                if processed_count >= batch_size:
                    _logger.info("Reached batch limit of %d", batch_size)
                    break
                log_user_id = log.user_id
                if (log_user_id not in valid_ids_int
                        and str(log_user_id) not in valid_ids_str):
                    continue
                # Convert to UTC
                if not log.timestamp.tzinfo:
                    localized_time = device_tz.localize(log.timestamp)
                else:
                    localized_time = log.timestamp.astimezone(device_tz)
                utc_time = localized_time.astimezone(
                    pytz.utc).replace(tzinfo=None)
                # Year filter
                if utc_time < year_start or utc_time >= year_end:
                    continue
                # Incremental cutoff
                if cutoff_time and utc_time <= cutoff_time:
                    continue
                logs.append({
                    'user_id': log_user_id,
                    'timestamp': utc_time.strftime("%Y-%m-%d %H:%M:%S"),
                })
                processed_count += 1

            if incremental:
                self.last_download_time = fields.Datetime.now()
            _logger.info("Download complete: %d records processed",
                          processed_count)
            return logs
        except Exception as e:
            _logger.error("Error fetching logs from %s: %s",
                           self.name, e, exc_info=True)
            raise UserError(
                _("Failed to fetch attendance logs: %s") % e)
        finally:
            if conn:
                conn.disconnect()

    def _detect_night_shift(self, employee):
        """Detect if an employee works night shift based on their calendar."""
        calendar = (employee.resource_calendar_id
                    or employee.company_id.resource_calendar_id)
        if not calendar:
            return False
        schedules = self.env['resource.calendar.attendance'].search([
            ('calendar_id', '=', calendar.id),
            ('day_period', '!=', 'lunch'),
        ])
        if not schedules:
            return False
        night_patterns = 0
        total = len(schedules)
        for sched in schedules:
            if (sched.hour_from > sched.hour_to
                    and sched.hour_from >= 20.0
                    and sched.hour_to <= 10.0):
                night_patterns += 1
        if night_patterns > 0 and night_patterns >= (total * 0.7):
            _logger.info("Employee %s: night shift detected (%d/%d)",
                          employee.name, night_patterns, total)
            return True
        return False

    def action_download_attendance(self, incremental=True, force=False):
        """Download attendance logs from the device and sync to hr.attendance"""
        if not self.device_ip:
            raise UserError(_("Please configure IP address for the device."))
        if not force and not self.auto_download:
            _logger.info("Auto download not enabled for device %s", self.name)
            return
        device_id = self.id
        total_created = 0
        total_updated = 0
        self.env.cr.commit()

        try:
            biometric_data = self.get_biometric_attendance(
                incremental=incremental)
            _logger.info("Retrieved %d attendance records to process",
                          len(biometric_data))
        except Exception as e:
            _logger.error("Failed to fetch attendance data: %s",
                           e, exc_info=True)
            raise UserError(
                _("Failed to fetch attendance data: %s") % e)

        # Group data by employee and date
        grouped_data = {}
        for record in biometric_data:
            timestamp = dt.strptime(record['timestamp'],
                                    "%Y-%m-%d %H:%M:%S")
            biometric_user_id = record['user_id']
            employee = self.env['hr.employee'].search([
                ('biometric_user_id', '=', biometric_user_id),
            ], limit=1)
            if not employee:
                _logger.warning("No employee for biometric ID: %s",
                                 biometric_user_id)
                continue

            # Night shift grouping
            is_night = self._detect_night_shift(employee)
            if is_night and timestamp.hour < 12:
                date_key = (timestamp - timedelta(days=1)).date()
            else:
                date_key = timestamp.date()

            emp_id = employee.id
            if emp_id not in grouped_data:
                grouped_data[emp_id] = {}
            if date_key not in grouped_data[emp_id]:
                grouped_data[emp_id][date_key] = {
                    'check_in': timestamp,
                    'check_out': timestamp,
                }
            else:
                if timestamp < grouped_data[emp_id][date_key]['check_in']:
                    grouped_data[emp_id][date_key]['check_in'] = timestamp
                if timestamp > grouped_data[emp_id][date_key]['check_out']:
                    grouped_data[emp_id][date_key]['check_out'] = timestamp

        _logger.info("Grouped data for %d employees", len(grouped_data))

        # Process in batches using separate cursors
        employee_ids = list(grouped_data.keys())
        batch_size = 5
        day_batch_size = 20

        for chunk_start in range(0, len(employee_ids), batch_size):
            chunk_end = min(chunk_start + batch_size, len(employee_ids))
            chunk = employee_ids[chunk_start:chunk_end]
            _logger.info("Processing employees %d to %d of %d",
                          chunk_start + 1, chunk_end, len(employee_ids))
            self.env.cr.commit()

            for emp_id in chunk:
                try:
                    with self.pool.cursor() as new_cr:
                        env = api.Environment(new_cr, self.env.uid,
                                              self.env.context)
                        emp_created = 0
                        emp_updated = 0
                        day_items = list(grouped_data[emp_id].items())
                        # Get employee timezone for date computation
                        employee = env['hr.employee'].browse(emp_id)
                        emp_tz = pytz.timezone(
                            employee.resource_calendar_id.tz
                            or employee.tz
                            or employee.company_id
                                .resource_calendar_id.tz
                            or 'UTC')

                        for i in range(0, len(day_items), day_batch_size):
                            sub = day_items[i:i + day_batch_size]
                            new_cr.execute("SAVEPOINT batch_sp")
                            try:
                                for day, times in sub:
                                    att = env['hr.attendance'].search([
                                        ('employee_id', '=', emp_id),
                                        ('check_in', '>=', day),
                                        ('check_in', '<',
                                         day + timedelta(days=1)),
                                    ], limit=1)
                                    ci = times['check_in']
                                    co = times['check_out']
                                    ci_str = ci.strftime(
                                        "%Y-%m-%d %H:%M:%S")
                                    co_str = co.strftime(
                                        "%Y-%m-%d %H:%M:%S")

                                    if att:
                                        # Update: keep earliest in, latest out
                                        new_cr.execute(
                                            "SELECT check_in, check_out "
                                            "FROM hr_attendance WHERE id=%s",
                                            (att.id,))
                                        row = new_cr.fetchone()
                                        cur_ci = row[0]
                                        cur_co = row[1]
                                        if isinstance(cur_ci, str):
                                            cur_ci = dt.strptime(
                                                cur_ci,
                                                "%Y-%m-%d %H:%M:%S")
                                        if isinstance(cur_co, str):
                                            cur_co = dt.strptime(
                                                cur_co,
                                                "%Y-%m-%d %H:%M:%S")
                                        new_ci = min(cur_ci, ci) \
                                            if cur_ci else ci
                                        new_co = max(cur_co, co) \
                                            if cur_co else co
                                        # Compute date in employee tz
                                        att_date = pytz.utc.localize(
                                            new_ci).astimezone(
                                            emp_tz).date()
                                        new_cr.execute(
                                            "UPDATE hr_attendance "
                                            "SET check_in=%s, check_out=%s, "
                                            "date=%s, "
                                            "write_date=NOW(), write_uid=%s "
                                            "WHERE id=%s",
                                            (new_ci.strftime(
                                                "%Y-%m-%d %H:%M:%S"),
                                             new_co.strftime(
                                                 "%Y-%m-%d %H:%M:%S"),
                                             att_date.strftime("%Y-%m-%d"),
                                             self.env.uid, att.id))
                                        emp_updated += 1
                                    else:
                                        # Compute date in employee tz
                                        att_date = pytz.utc.localize(
                                            ci).astimezone(
                                            emp_tz).date()
                                        # Create via SQL (bypass ORM)
                                        new_cr.execute(
                                            "INSERT INTO hr_attendance "
                                            "(employee_id, check_in, "
                                            "check_out, date, "
                                            "create_date, create_uid, "
                                            "write_date, write_uid) "
                                            "VALUES (%s,%s,%s,%s,"
                                            "NOW(),%s,NOW(),%s)",
                                            (emp_id, ci_str, co_str,
                                             att_date.strftime("%Y-%m-%d"),
                                             self.env.uid, self.env.uid))
                                        emp_created += 1

                                new_cr.execute("RELEASE SAVEPOINT batch_sp")
                                new_cr.commit()
                            except Exception as e:
                                _logger.error(
                                    "Error in sub-batch for emp %d: %s",
                                    emp_id, e)
                                new_cr.execute(
                                    "ROLLBACK TO SAVEPOINT batch_sp")

                        total_created += emp_created
                        total_updated += emp_updated
                        _logger.info("Employee %d: %d created, %d updated",
                                      emp_id, emp_created, emp_updated)
                        new_cr.commit()
                except Exception as e:
                    _logger.error("Critical error for emp %d: %s",
                                   emp_id, e)

            self.env.cr.commit()

        # Update last download time for full downloads
        if not incremental:
            try:
                with self.pool.cursor() as new_cr:
                    now = fields.Datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S")
                    new_cr.execute(
                        "UPDATE biometric_device_details "
                        "SET last_download_time=%s, write_date=NOW(), "
                        "write_uid=%s WHERE id=%s",
                        (now, self.env.uid, device_id))
                    new_cr.commit()
            except Exception as e:
                _logger.error("Error updating last_download_time: %s", e)

        _logger.info("Sync complete for device %d: %d created, %d updated",
                      device_id, total_created, total_updated)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _("Attendance sync complete: %d created, "
                             "%d updated") % (total_created, total_updated),
                'type': 'success',
                'sticky': False,
            },
        }

    # todo
    # def _check_employee_schedule(self, employee):
    #     """Check the schedule assigned for the employee"""
    #     calendar = (employee.calendar_id)
    #     if not calendar:
    #         return None
    #     schedules = self.env['resource.calendar.attendance'].search([
    #         ('calendar_id', '=', calendar.id),
    #         ('day_period', '!=', 'lunch'),
    #     ])
    #     print(schedules.mapped('hour_from'))
    #     return schedules


    # todo
    def _grace_period_check(self, punch_time):
        return

    def action_download_all_attendance(self):
        """Download all attendance logs (manual trigger)"""
        _logger.info("=== STARTING FULL ATTENDANCE DOWNLOAD ===")
        result = self.action_download_attendance(
            incremental=False, force=True)
        _logger.info("=== COMPLETED FULL ATTENDANCE DOWNLOAD ===")
        return result
        # employee = self.env['hr.employee'].browse(6)
        # self._check_employee_schedule(employee)

    def action_download_incremental_attendance(self):
        """Download only new attendance logs since last download"""
        _logger.info("=== STARTING INCREMENTAL ATTENDANCE DOWNLOAD ===")
        result = self.action_download_attendance(
            incremental=True, force=True)
        _logger.info("=== COMPLETED INCREMENTAL ATTENDANCE DOWNLOAD ===")
        return result

    @api.model
    def cron_download_incremental(self):
        """Cron job: download incremental attendance for all devices.
        Never raises exceptions so the cron keeps running."""
        cron_start = fields.Datetime.now()
        _logger.info("=" * 80)
        _logger.info("BIOMETRIC CRON JOB STARTED - %s", cron_start)
        _logger.info("=" * 80)
        success = error = skipped = 0
        try:
            machines = self.env['biometric.device.details'].search([
                ('auto_download', '=', True),
            ])
            _logger.info("Found %d device(s) with auto_download enabled",
                          len(machines))
            if not machines:
                _logger.warning("No devices configured for auto-download.")
                return True
            for idx, machine in enumerate(machines, 1):
                if not machine.device_ip:
                    _logger.warning("Device %s has no IP. Skipping.",
                                     machine.name)
                    skipped += 1
                    continue
                max_retries = 3
                retry_delays = [5, 15, 30]
                for attempt in range(max_retries):
                    try:
                        _logger.info("[%d/%d] Attempt %d: %s",
                                      idx, len(machines),
                                      attempt + 1, machine.name)
                        machine.action_download_attendance(
                            incremental=True, force=True)
                        success += 1
                        _logger.info("✓ Synced %s", machine.name)
                        break
                    except UserError as e:
                        _logger.error("✗ Config error %s: %s",
                                       machine.name, e)
                        error += 1
                        break
                    except Exception as e:
                        if attempt < max_retries - 1:
                            wait = retry_delays[attempt]
                            _logger.warning(
                                "⚠ Error attempt %d for %s: %s. "
                                "Retrying in %ds...",
                                attempt + 1, machine.name, e, wait)
                            time.sleep(wait)
                        else:
                            _logger.error(
                                "✗ Failed %s after %d attempts: %s",
                                machine.name, max_retries, e)
                            error += 1

            duration = (fields.Datetime.now() - cron_start).total_seconds()
            _logger.info("=" * 80)
            _logger.info("CRON SUMMARY: %.2fs | ✓ %d | ✗ %d | ⊘ %d",
                          duration, success, error, skipped)
            _logger.info("=" * 80)
            return True
        except Exception as e:
            _logger.error("CRITICAL CRON ERROR: %s", e, exc_info=True)
            return True
