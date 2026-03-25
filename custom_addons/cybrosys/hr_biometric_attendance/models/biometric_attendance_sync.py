# -*- coding: utf-8 -*-
import logging
import time
from datetime import datetime as dt, timedelta

import pytz

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class BiometricAttendanceSync(models.AbstractModel):
    """Service model for downloading and syncing biometric attendance."""
    _name = 'biometric.attendance.sync'
    _description = 'Biometric Attendance Sync Service'

    # -- Helpers --------------------------------------------------------------

    @api.model
    def _get_valid_biometric_ids(self):
        """Return set of biometric IDs (str) mapped to employees."""
        employees = self.env['hr.employee'].search([
            ('biometric_user_id', '!=', False),
        ])
        bio_ids = set(employees.mapped(
            lambda e: str(e.biometric_user_id)))
        _logger.info("Found %d employees with biometric IDs", len(bio_ids))
        return bio_ids

    @api.model
    def _get_year_boundaries(self, device):
        year = int(device.year_filter) if device.year_filter else dt.now().year
        return dt(year, 1, 1), dt(year + 1, 1, 1)

    # -- Raw log processing ---------------------------------------------------

    @api.model
    def _process_raw_logs(self, attendance_logs, valid_bio_ids, device_tz,
                          cutoff_time, year_start, year_end, batch_size):
        """Filter and convert raw device logs to UTC dicts."""
        logs = []
        for log in attendance_logs:
            if len(logs) >= batch_size:
                _logger.info("Reached batch limit of %d", batch_size)
                break
            if str(log.user_id) not in valid_bio_ids:
                continue
            localized = (
                device_tz.localize(log.timestamp)
                if not log.timestamp.tzinfo
                else log.timestamp.astimezone(device_tz)
            )
            utc_time = localized.astimezone(pytz.utc).replace(tzinfo=None)
            if not (year_start <= utc_time < year_end):
                continue
            if cutoff_time and utc_time <= cutoff_time:
                continue
            logs.append({
                'user_id': log.user_id,
                'timestamp': utc_time.strftime("%Y-%m-%d %H:%M:%S"),
            })
        return logs

    @api.model
    def _fetch_biometric_attendance(self, device, incremental=False):
        """Fetch attendance logs from a ZKTeco device."""
        _logger.info(
            "Starting attendance download from %s (%s:%s), incremental=%s",
            device.name, device.device_ip, device.port_number, incremental)

        valid_bio_ids = self._get_valid_biometric_ids()
        if not valid_bio_ids:
            _logger.warning("No employees with biometric IDs. Skipping.")
            return []

        device_tz = pytz.timezone(device.tz or 'UTC')
        cutoff_time = (
            device.last_download_time
            if incremental and device.last_download_time
            else False
        )
        year_start, year_end = self._get_year_boundaries(device)
        batch_size = device.download_batch_size or 1000

        conn = device._connect_device()
        try:
            attendance_logs = conn.get_attendance()
            log_count = len(attendance_logs) if attendance_logs else 0
            _logger.info("Retrieved %d raw logs from device", log_count)
            if not attendance_logs:
                return []

            logs = self._process_raw_logs(
                attendance_logs, valid_bio_ids, device_tz,
                cutoff_time, year_start, year_end, batch_size)

            if incremental:
                device.last_download_time = fields.Datetime.now()

            _logger.info(
                "Download complete: %d records processed", len(logs))
            return logs
        except UserError:
            raise
        except Exception as e:
            _logger.error(
                "Error fetching logs from %s: %s",
                device.name, e, exc_info=True)
            raise UserError(
                _("Failed to fetch attendance logs: %s") % e)
        finally:
            conn.disconnect()


    # -- Absence Detection ----------------------------------------------------

    @api.model
    def _get_employee_start_date(self, employee):
        """Determine the earliest date to check for absences.

        Resolution order: employee first_contract_date -> first attendance -> year start.
        """
        today = fields.Date.context_today(self)

        # In Odoo 19, contract info is on the employee record itself
        # Try common date fields on hr.employee
        if hasattr(employee, 'first_contract_date') and employee.first_contract_date:
            return employee.first_contract_date
        if hasattr(employee, 'contract_start_date') and employee.contract_start_date:
            return employee.contract_start_date

        # Try hr.contract if the module exists (some installs may still have it)
        if 'hr.contract' in self.env:
            contract = self.env['hr.contract'].search([
                ('employee_id', '=', employee.id),
                ('state', 'in', ['open', 'close']),
            ], order='date_start asc', limit=1)
            if contract and contract.date_start:
                return contract.date_start

        # Fallback: first real attendance record
        first_att = self.env['hr.attendance'].search([
            ('employee_id', '=', employee.id),
            ('x_is_absent', '=', False),
        ], order='check_in asc', limit=1)
        if first_att:
            return first_att.check_in.date()

        return today.replace(month=1, day=1)

    @api.model
    def _has_attendance_on_date(self, employee, check_date):
        """Check if employee has a real attendance record on a given date.

        Uses UTC day boundaries (00:00–24:00 UTC) because absence records
        are stored at UTC midnight (00:00 UTC) so the date in ``check_in``
        always matches the calendar date.
        """
        day_start = dt.combine(check_date, dt.min.time())
        day_end = dt.combine(check_date + timedelta(days=1), dt.min.time())
        return bool(self.env['hr.attendance'].search([
            ('employee_id', '=', employee.id),
            ('check_in', '>=', day_start),
            ('check_in', '<', day_end),
            ('x_is_absent', '=', False),
        ], limit=1))

    @api.model
    def _has_absence_on_date(self, employee, check_date):
        """Check if an absence record already exists for a given date."""
        day_start = dt.combine(check_date, dt.min.time())
        day_end = dt.combine(check_date + timedelta(days=1), dt.min.time())
        return bool(self.env['hr.attendance'].search([
            ('employee_id', '=', employee.id),
            ('check_in', '>=', day_start),
            ('check_in', '<', day_end),
            ('x_is_absent', '=', True),
        ], limit=1))

    @api.model
    def _has_leave_on_date(self, employee, check_date):
        """Check if employee has an approved leave covering a given date."""
        return bool(self.env['hr.leave'].search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'validate'),
            ('date_from', '<=', dt.combine(check_date, dt.max.time())),
            ('date_to', '>=', dt.combine(check_date, dt.min.time())),
        ], limit=1))

    @api.model
    def _create_absence_record(self, employee, absence_date):
        """Create a single absence hr.attendance record.

        Uses **UTC midnight** (00:00 UTC) for both check_in and check_out so
        that ``check_in.date()`` always returns the correct calendar date and
        downstream logic (day naming, weekend detection, duplicate checks)
        works consistently regardless of the employee's timezone.
        """
        utc_midnight = dt.combine(absence_date, dt.min.time())

        self.env['hr.attendance'].sudo().create({
            'employee_id': employee.id,
            'check_in': utc_midnight,
            'check_out': utc_midnight,
            'worked_hours': 0.0,
            'x_late_minutes': 0.0,
            'x_early_leave_minutes': 0.0,
            'x_is_absent': True,
        })

        _logger.info(
            "Absence record created for %s on %s",
            employee.name, absence_date)

    @api.model
    def _check_absence_for_date(self, employee, check_date):
        """Check and create absence record for a single employee on a single date.

        :return: True if absence was created, False otherwise
        """
        sched_helper = self.env['biometric.schedule.helper']

        if not sched_helper.is_scheduled_workday(employee, check_date):
            return False
        if self._has_attendance_on_date(employee, check_date):
            return False
        if self._has_absence_on_date(employee, check_date):
            return False
        if self._has_leave_on_date(employee, check_date):
            return False

        self._create_absence_record(employee, check_date)
        return True

    @api.model
    def _generate_absences_date_range(self, employees, date_from, date_to):
        """Generate absence records for employees across a date range.

        :return: total number of records created
        """
        total_created = 0
        errors = 0

        for employee in employees:
            try:
                created = 0
                current_date = date_from
                while current_date <= date_to:
                    if self._check_absence_for_date(employee, current_date):
                        created += 1
                    current_date += timedelta(days=1)
                total_created += created
                if created:
                    _logger.info(
                        "Employee %s: %d absence records created",
                        employee.name, created)
                self.env.cr.commit()
            except Exception as e:
                _logger.error(
                    "Error generating absences for %s: %s",
                    employee.name, e, exc_info=True)
                self.env.cr.rollback()
                errors += 1

        _logger.info(
            "Absence generation complete: %d created, %d errors",
            total_created, errors)
        return total_created

    @api.model
    def _generate_weekend_records(self, employees, date_from, date_to):
        """Grant weekend hours only if employee attended an adjacent workday."""
        helper = self.env['biometric.schedule.helper']
        HrAttendance = self.env['hr.attendance']
        total_created = 0

        for emp in employees:
            emp_tz = helper.get_employee_tz(emp)

            # Prefetch all attendance dates for this employee in the range
            all_attendances = HrAttendance.search([
                ('employee_id', '=', emp.id),
                ('check_in', '>=', dt.combine(date_from - timedelta(days=1), dt.min.time())),
                ('check_in', '<', dt.combine(date_to + timedelta(days=2), dt.min.time())),
                ('x_is_absent', '=', False),
            ])
            attended_dates = set()
            existing_dates = set()
            for att in all_attendances:
                att_date = att.check_in.date() if isinstance(att.check_in, dt) else att.check_in
                existing_dates.add(att_date)
                if not att.x_is_weekend:
                    attended_dates.add(att_date)

            current = date_from
            while current <= date_to:
                if helper.is_scheduled_workday(emp, current):
                    current += timedelta(days=1)
                    continue

                weekend_start = current
                weekend_end = current
                while (weekend_end + timedelta(days=1)) <= date_to \
                        and not helper.is_scheduled_workday(emp, weekend_end + timedelta(days=1)):
                    weekend_end += timedelta(days=1)

                day_before = weekend_start - timedelta(days=1)
                day_after = weekend_end + timedelta(days=1)

                if day_before in attended_dates or day_after in attended_dates:
                    grant_day = weekend_start
                    while grant_day <= weekend_end:
                        if grant_day not in existing_dates:
                            ref_schedule = helper.get_employee_day_schedule(
                                emp, day_before, emp_tz
                            ) or helper.get_employee_day_schedule(
                                emp, day_after, emp_tz
                            )
                            if ref_schedule:
                                sched_start = emp_tz.localize(
                                    dt(grant_day.year, grant_day.month, grant_day.day,
                                       ref_schedule['start'].hour, ref_schedule['start'].minute))
                                sched_end = emp_tz.localize(
                                    dt(grant_day.year, grant_day.month, grant_day.day,
                                       ref_schedule['end'].hour, ref_schedule['end'].minute))
                                ci_utc = sched_start.astimezone(pytz.utc).replace(tzinfo=None)
                                co_utc = sched_end.astimezone(pytz.utc).replace(tzinfo=None)
                                ref_day = day_before if day_before in attended_dates else day_after
                                break_hours = helper.calculate_break_deduction(
                                    emp, ref_day, sched_start, sched_end, emp_tz)
                                worked = (co_utc - ci_utc).total_seconds() / 3600.0 - break_hours

                                rec = HrAttendance.sudo().create({
                                    'employee_id': emp.id,
                                    'check_in': ci_utc,
                                    'check_out': co_utc,
                                    'x_is_absent': False,
                                    'x_is_weekend': True,
                                    'x_weekend_granted': True,
                                })
                                rec.sudo().write({'worked_hours': worked})

                                existing_dates.add(grant_day)
                                total_created += 1
                                _logger.info("Weekend granted for %s on %s (%.2fh)",
                                             emp.name, grant_day, worked)
                        grant_day += timedelta(days=1)

                current = weekend_end + timedelta(days=1)

            self.env.cr.commit()

    # -- Cron: yesterday only (lightweight) ----------------------------------

    @api.model
    def cron_generate_absences(self):
        """Daily cron: check from last run to yesterday for absences."""
        cron_start = fields.Datetime.now()
        today = fields.Date.context_today(self)
        yesterday = today - timedelta(days=1)

        # lastcall is passed by ir.cron via context
        lastcall = self.env.context.get('lastcall')
        if lastcall:
            date_from = lastcall.date()
        else:
            date_from = yesterday

        if date_from > yesterday:
            _logger.info("ABSENCE CRON: nothing to check (date_from %s > yesterday %s)",
                         date_from, yesterday)
            return True

        _logger.info("=" * 80)
        _logger.info(
            "ABSENCE DETECTION CRON STARTED - %s (checking %s to %s)",
            cron_start, date_from, yesterday)
        _logger.info("=" * 80)

        employees = self.env['hr.employee'].search([
            ('biometric_user_id', '!=', False),
        ])
        _logger.info("Checking %d employees for absences from %s to %s",
                     len(employees), date_from, yesterday)

        total_created = self._generate_absences_date_range(
            employees, date_from, yesterday)

        self._generate_weekend_records(employees, date_from, yesterday)

        duration = (fields.Datetime.now() - cron_start).total_seconds()
        _logger.info("=" * 80)
        _logger.info(
            "ABSENCE CRON SUMMARY: %.2fs | employees: %d | "
            "absences created: %d | range: %s to %s",
            duration, len(employees), total_created, date_from, yesterday)
        _logger.info("=" * 80)
        return True

    # -- Manual: full historical scan ----------------------------------------

    @api.model
    def action_generate_all_absences(self):
        """Manual button: scan all historical days for all biometric employees."""
        employees = self.env['hr.employee'].search([
            ('biometric_user_id', '!=', False),
        ])
        if not employees:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("No employees with biometric IDs found."),
                    'type': 'warning',
                    'sticky': False,
                },
            }

        today = fields.Date.context_today(self)
        yesterday = today - timedelta(days=1)
        total_created = 0

        for employee in employees:
            date_from = self._get_employee_start_date(employee)
            if date_from > yesterday:
                continue
            created = self._generate_absences_date_range(
                employee, date_from, yesterday)
            total_created += created

        # --- Generate weekend records for the full historical range ---
        earliest = min(
            (self._get_employee_start_date(e) for e in employees),
            default=yesterday,
        )
        self._generate_weekend_records(employees, earliest, yesterday)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _(
                    "Historical absence scan complete: %d records created"
                ) % total_created,
                'type': 'success',
                'sticky': False,
            },
        }

    # -- Grouping -------------------------------------------------------------

    @api.model
    def _group_biometric_data(self, biometric_data):
        """Group raw biometric records by employee and date."""
        sched_helper = self.env['biometric.schedule.helper']
        grouped_data = {}

        for record in biometric_data:
            timestamp = dt.strptime(
                record['timestamp'], "%Y-%m-%d %H:%M:%S")
            biometric_user_id = record['user_id']

            employee = self.env['hr.employee'].search([
                ('biometric_user_id', '=', biometric_user_id),
            ], limit=1)
            if not employee:
                _logger.warning(
                    "No employee for biometric ID: %s", biometric_user_id)
                continue

            is_night = sched_helper.detect_night_shift(employee)
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
                entry = grouped_data[emp_id][date_key]
                if timestamp < entry['check_in']:
                    entry['check_in'] = timestamp
                if timestamp > entry['check_out']:
                    entry['check_out'] = timestamp

        _logger.info("Grouped data for %d employees", len(grouped_data))
        return grouped_data

    # -- Sync single record ---------------------------------------------------

    def _sync_attendance_record(self, new_cr, env, emp_id, day, times, emp_tz):
        """Insert or update a single hr_attendance record via raw SQL."""
        sched_helper = env['biometric.schedule.helper']
        ci = times['check_in']
        co = times['check_out']
        ci_str = ci.strftime("%Y-%m-%d %H:%M:%S")
        co_str = co.strftime("%Y-%m-%d %H:%M:%S")

        employee = env['hr.employee'].browse(emp_id)
        work_data = sched_helper.calculate_worked_time(ci, co, employee)
        worked_hours = work_data['worked_hours']
        late_minutes = work_data['late_minutes']
        early_leave_minutes = work_data['early_leave_minutes']
        overtime_hours = work_data.get('overtime_hours', 0.0)

        att_date = pytz.utc.localize(ci).astimezone(emp_tz).date()
        att_date_str = att_date.strftime("%Y-%m-%d")

        new_cr.execute(
            "SELECT id, check_in, check_out FROM hr_attendance "
            "WHERE employee_id = %s AND check_in >= %s AND check_in < %s "
            "ORDER BY check_in LIMIT 1",
            (emp_id,
             day.strftime("%Y-%m-%d"),
             (day + timedelta(days=1)).strftime("%Y-%m-%d")))
        row = new_cr.fetchone()

        if row:
            att_id, cur_ci, cur_co = row
            if isinstance(cur_ci, str):
                cur_ci = dt.strptime(cur_ci, "%Y-%m-%d %H:%M:%S")
            if isinstance(cur_co, str):
                cur_co = dt.strptime(cur_co, "%Y-%m-%d %H:%M:%S")

            new_ci = min(cur_ci, ci) if cur_ci else ci
            new_co = max(cur_co, co) if cur_co else co

            if new_ci != ci or new_co != co:
                work_data = sched_helper.calculate_worked_time(
                    new_ci, new_co, employee)
                worked_hours = work_data['worked_hours']
                late_minutes = work_data['late_minutes']
                early_leave_minutes = work_data['early_leave_minutes']
                overtime_hours = work_data.get('overtime_hours', 0.0)

            att_date = pytz.utc.localize(new_ci).astimezone(emp_tz).date()
            day_name = att_date.strftime('%A')
            new_cr.execute(
                "UPDATE hr_attendance "
                "SET check_in = %s, check_out = %s, date = %s, "
                "worked_hours = %s, "
                "x_late_minutes = %s, x_early_leave_minutes = %s, "
                "overtime_hours = %s, "
                "x_day_of_week = %s, "
                "write_date = NOW(), write_uid = %s "
                "WHERE id = %s",
                (new_ci.strftime("%Y-%m-%d %H:%M:%S"),
                 new_co.strftime("%Y-%m-%d %H:%M:%S"),
                 att_date.strftime("%Y-%m-%d"),
                 worked_hours,
                 late_minutes, early_leave_minutes,
                 overtime_hours,
                 day_name,
                 self.env.uid, att_id))

            return False, True
        else:
            day_name = att_date.strftime('%A')
            new_cr.execute(
                "INSERT INTO hr_attendance "
                "(employee_id, check_in, check_out, date, "
                "worked_hours, "
                "x_late_minutes, x_early_leave_minutes,overtime_hours, x_day_of_week, "
                "create_date, create_uid, write_date, write_uid) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s,%s, NOW(), %s, NOW(), %s)",
                (emp_id, ci_str, co_str, att_date_str,
                 worked_hours,
                 late_minutes, early_leave_minutes,overtime_hours, day_name,
                 self.env.uid, self.env.uid))
            return True, False

    # -- Main download orchestrator -------------------------------------------

    def download_attendance(self, device, incremental=True, force=False):
        """Download attendance logs from device and sync to hr.attendance."""
        if not device.device_ip:
            raise UserError(
                _("Please configure IP address for the device."))
        if not force and not device.auto_download:
            _logger.info(
                "Auto download not enabled for device %s", device.name)
            return

        sched_helper = self.env['biometric.schedule.helper']
        device_id = device.id
        total_created = 0
        total_updated = 0

        device.env.cr.commit()

        try:
            biometric_data = self._fetch_biometric_attendance(
                device, incremental=incremental)
            _logger.info(
                "Retrieved %d attendance records to process",
                len(biometric_data))
        except Exception as e:
            _logger.error(
                "Failed to fetch attendance data: %s", e, exc_info=True)
            raise UserError(
                _("Failed to fetch attendance data: %s") % e)

        if not biometric_data:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _("No new attendance records found."),
                    'type': 'info',
                    'sticky': False,
                },
            }

        grouped_data = self._group_biometric_data(biometric_data)
        employee_ids = list(grouped_data.keys())
        emp_batch_size = 5
        day_batch_size = 20

        for chunk_start in range(0, len(employee_ids), emp_batch_size):
            chunk_end = min(
                chunk_start + emp_batch_size, len(employee_ids))
            chunk = employee_ids[chunk_start:chunk_end]
            _logger.info(
                "Processing employees %d to %d of %d",
                chunk_start + 1, chunk_end, len(employee_ids))
            device.env.cr.commit()

            for emp_id in chunk:
                try:
                    with device.pool.cursor() as new_cr:
                        env = api.Environment(
                            new_cr, device.env.uid, device.env.context)
                        emp_created = 0
                        emp_updated = 0
                        day_items = list(grouped_data[emp_id].items())

                        employee = env['hr.employee'].browse(emp_id)
                        emp_tz = sched_helper.get_employee_tz(employee)

                        for i in range(0, len(day_items), day_batch_size):
                            sub = day_items[i:i + day_batch_size]
                            new_cr.execute("SAVEPOINT batch_sp")
                            try:
                                for day, times in sub:
                                    created, updated = \
                                        self._sync_attendance_record(
                                            new_cr, env, emp_id,
                                            day, times, emp_tz)
                                    emp_created += int(created)
                                    emp_updated += int(updated)
                                new_cr.execute(
                                    "RELEASE SAVEPOINT batch_sp")
                                new_cr.commit()
                            except Exception as e:
                                _logger.error(
                                    "Error in sub-batch for emp %d: %s",
                                    emp_id, e)
                                new_cr.execute(
                                    "ROLLBACK TO SAVEPOINT batch_sp")

                        total_created += emp_created
                        total_updated += emp_updated
                        _logger.info(
                            "Employee %d: %d created, %d updated",
                            emp_id, emp_created, emp_updated)
                        new_cr.commit()
                except Exception as e:
                    _logger.error(
                        "Critical error for emp %d: %s", emp_id, e)

            device.env.cr.commit()

        if not incremental:
            try:
                with device.pool.cursor() as new_cr:
                    now = fields.Datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S")
                    new_cr.execute(
                        "UPDATE biometric_device_details "
                        "SET last_download_time=%s, write_date=NOW(), "
                        "write_uid=%s WHERE id=%s",
                        (now, device.env.uid, device_id))
                    new_cr.commit()
            except Exception as e:
                _logger.error(
                    "Error updating last_download_time: %s", e)

        _logger.info(
            "Sync complete for device %d: %d created, %d updated",
            device_id, total_created, total_updated)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _(
                    "Attendance sync complete: %d created, %d updated"
                ) % (total_created, total_updated),
                'type': 'success',
                'sticky': False,
            },
        }

    # -- Cron -----------------------------------------------------------------

    @api.model
    def cron_download_incremental(self):
        """Cron job: download incremental attendance for all devices."""
        cron_start = fields.Datetime.now()
        _logger.info("=" * 80)
        _logger.info("BIOMETRIC CRON JOB STARTED - %s", cron_start)
        _logger.info("=" * 80)
        success = error = skipped = 0

        try:
            machines = self.env['biometric.device.details'].search([
                ('auto_download', '=', True),
            ])
            _logger.info(
                "Found %d device(s) with auto_download enabled",
                len(machines))
            if not machines:
                _logger.warning(
                    "No devices configured for auto-download.")
                return True

            for idx, machine in enumerate(machines, 1):
                if not machine.device_ip:
                    _logger.warning(
                        "Device %s has no IP. Skipping.", machine.name)
                    skipped += 1
                    continue

                max_retries = 3
                retry_delays = [5, 15, 30]
                for attempt in range(max_retries):
                    try:
                        _logger.info(
                            "[%d/%d] Attempt %d: %s",
                            idx, len(machines),
                            attempt + 1, machine.name)
                        self.download_attendance(
                            machine, incremental=True, force=True)
                        success += 1
                        break
                    except UserError as e:
                        _logger.error(
                            "Config error %s: %s", machine.name, e)
                        error += 1
                        break
                    except Exception as e:
                        if attempt < max_retries - 1:
                            wait = retry_delays[attempt]
                            _logger.warning(
                                "Error attempt %d for %s: %s. "
                                "Retrying in %ds...",
                                attempt + 1, machine.name, e, wait)
                            time.sleep(wait)
                        else:
                            _logger.error(
                                "Failed %s after %d attempts: %s",
                                machine.name, max_retries, e)
                            error += 1

            duration = (
                fields.Datetime.now() - cron_start).total_seconds()
            _logger.info("=" * 80)
            _logger.info(
                "CRON SUMMARY: %.2fs | success: %d | errors: %d "
                "| skipped: %d",
                duration, success, error, skipped)
            _logger.info("=" * 80)
            return True
        except Exception as e:
            _logger.error("CRITICAL CRON ERROR: %s", e, exc_info=True)
            return True
