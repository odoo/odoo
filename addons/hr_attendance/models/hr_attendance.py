# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz

from calendar import monthrange
from collections import defaultdict
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from operator import itemgetter
from pytz import timezone
from random import randint

from odoo import models, fields, api, exceptions, _
from odoo.addons.resource.models.utils import Intervals
from odoo.tools import format_datetime
from odoo.osv.expression import AND, OR
from odoo.tools.float_utils import float_is_zero
from odoo.exceptions import AccessDenied, AccessError
from odoo.tools import convert, format_duration

def get_google_maps_url(latitude, longitude):
    return "https://maps.google.com?q=%s,%s" % (latitude, longitude)


class HrAttendance(models.Model):
    _name = "hr.attendance"
    _description = "Attendance"
    _order = "check_in desc"
    _inherit = "mail.thread"

    def _default_employee(self):
        return self.env.user.employee_id

    employee_id = fields.Many2one('hr.employee', string="Employee", default=_default_employee, required=True,
        ondelete='cascade', index=True, group_expand='_read_group_employee_id')
    department_id = fields.Many2one('hr.department', string="Department", related="employee_id.department_id",
        readonly=True)
    manager_id = fields.Many2one(comodel_name='hr.employee', related="employee_id.parent_id", readonly=True,
        export_string_translation=False)
    check_in = fields.Datetime(string="Check In", default=fields.Datetime.now, required=True, tracking=True)
    check_out = fields.Datetime(string="Check Out", tracking=True)
    worked_hours = fields.Float(string='Worked Hours', compute='_compute_worked_hours', store=True, readonly=True)
    color = fields.Integer(compute='_compute_color')
    overtime_hours = fields.Float(string="Over Time", compute='_compute_overtime_hours', store=True)
    overtime_status = fields.Selection(selection=[('to_approve', "To Approve"),
                                                  ('approved', "Approved"),
                                                  ('refused', "Refused")], compute="_compute_overtime_status", store=True, tracking=True)
    validated_overtime_hours = fields.Float(string="Extra Hours", compute='_compute_validated_overtime_hours', store=True, readonly=False, tracking=True)
    in_latitude = fields.Float(string="Latitude", digits=(10, 7), readonly=True, aggregator=None)
    in_longitude = fields.Float(string="Longitude", digits=(10, 7), readonly=True, aggregator=None)
    in_country_name = fields.Char(string="Country", help="Based on IP Address", readonly=True)
    in_city = fields.Char(string="City", readonly=True)
    in_ip_address = fields.Char(string="IP Address", readonly=True)
    in_browser = fields.Char(string="Browser", readonly=True)
    in_mode = fields.Selection(string="Mode",
                               selection=[('kiosk', "Kiosk"),
                                          ('systray', "Systray"),
                                          ('manual', "Manual"),
                                          ('technical', 'Technical')],
                               readonly=True,
                               default='manual')
    out_latitude = fields.Float(digits=(10, 7), readonly=True, aggregator=None)
    out_longitude = fields.Float(digits=(10, 7), readonly=True, aggregator=None)
    out_country_name = fields.Char(help="Based on IP Address", readonly=True)
    out_city = fields.Char(readonly=True)
    out_ip_address = fields.Char(readonly=True)
    out_browser = fields.Char(readonly=True)
    out_mode = fields.Selection(selection=[('kiosk', "Kiosk"),
                                           ('systray', "Systray"),
                                           ('manual', "Manual"),
                                           ('technical', 'Technical'),
                                           ('auto_check_out', 'Automatic Check-Out')],
                                readonly=True,
                                default='manual')
    expected_hours = fields.Float(compute="_compute_expected_hours", store=True, aggregator="sum")

    @api.depends("worked_hours", "overtime_hours")
    def _compute_expected_hours(self):
        for attendance in self:
            attendance.expected_hours = attendance.worked_hours - attendance.overtime_hours

    def _compute_color(self):
        for attendance in self:
            if attendance.check_out:
                attendance.color = 1 if attendance.worked_hours > 16 or attendance.out_mode == 'technical' else 0
            else:
                attendance.color = 1 if attendance.check_in < (datetime.today() - timedelta(days=1)) else 10

    @api.depends('worked_hours')
    def _compute_overtime_hours(self):
        att_progress_values = dict()
        negative_overtime_attendances = defaultdict(lambda: False)
        if self.employee_id:
            self.env['hr.attendance'].flush_model(['worked_hours'])
            self.env['hr.attendance.overtime'].flush_model(['duration'])
            self.env.cr.execute('''
                WITH employee_time_zones AS (
                    SELECT employee.id AS employee_id,
                           calendar.tz AS timezone
                      FROM hr_employee employee
                INNER JOIN resource_calendar calendar
                        ON calendar.id = employee.resource_calendar_id
                )
                SELECT att.id AS att_id,
                       att.worked_hours AS att_wh,
                       ot.id AS ot_id,
                       ot.duration AS ot_d,
                       ot.date AS od,
                       att.check_in AS ad
                  FROM hr_attendance att
            INNER JOIN employee_time_zones etz
                    ON att.employee_id = etz.employee_id
            INNER JOIN hr_attendance_overtime ot
                    ON date_trunc('day',
                                  CAST(att.check_in
                                           AT TIME ZONE 'utc'
                                           AT TIME ZONE etz.timezone
                                  as date)) = date_trunc('day', ot.date)
                   AND att.employee_id = ot.employee_id
                   AND att.employee_id IN %s
              ORDER BY att.check_in DESC
            ''', (tuple(self.employee_id.ids),))
            a = self.env.cr.dictfetchall()
            grouped_dict = dict()
            for row in a:
                if row['ot_id'] and row['att_wh']:
                    if row['ot_id'] not in grouped_dict:
                        grouped_dict[row['ot_id']] = {'attendances': [(row['att_id'], row['att_wh'])], 'overtime_duration': row['ot_d']}
                    else:
                        grouped_dict[row['ot_id']]['attendances'].append((row['att_id'], row['att_wh']))

            for overtime in grouped_dict:
                overtime_reservoir = grouped_dict[overtime]['overtime_duration']
                if overtime_reservoir > 0:
                    for attendance in grouped_dict[overtime]['attendances']:
                        if overtime_reservoir > 0:
                            sub_time = attendance[1] - overtime_reservoir
                            if sub_time < 0:
                                att_progress_values[attendance[0]] = 0
                                overtime_reservoir -= attendance[1]
                            else:
                                att_progress_values[attendance[0]] = float(((attendance[1] - overtime_reservoir) / attendance[1]) * 100)
                                overtime_reservoir = 0
                        else:
                            att_progress_values[attendance[0]] = 100
                elif overtime_reservoir < 0 and grouped_dict[overtime]['attendances']:
                    att_id = grouped_dict[overtime]['attendances'][0][0]
                    att_progress_values[att_id] = overtime_reservoir
                    negative_overtime_attendances[att_id] = True
        for attendance in self:
            if negative_overtime_attendances[attendance.id]:
                attendance.overtime_hours = att_progress_values.get(attendance.id, 0)
            else:
                attendance.overtime_hours = attendance.worked_hours * ((100 - att_progress_values.get(attendance.id, 100)) / 100)

    @api.depends('employee_id', 'overtime_status', 'overtime_hours')
    def _compute_validated_overtime_hours(self):
        no_validation = self.filtered(lambda a: a.employee_id.company_id.attendance_overtime_validation == 'no_validation')
        with_validation = self - no_validation

        for attendance in with_validation:
            if attendance.overtime_status not in ['approved', 'refused']:
                attendance.validated_overtime_hours = attendance.overtime_hours

        for attendance in no_validation:
            attendance.validated_overtime_hours = attendance.overtime_hours

    @api.depends('employee_id')
    def _compute_overtime_status(self):
        for attendance in self:
            if not attendance.overtime_status:
                attendance.overtime_status = "to_approve" if attendance.employee_id.company_id.attendance_overtime_validation == 'by_manager' else "approved"

    @api.depends('employee_id', 'check_in', 'check_out')
    def _compute_display_name(self):
        for attendance in self:
            if not attendance.check_out:
                attendance.display_name = _(
                    "From %s",
                    format_datetime(self.env, attendance.check_in, dt_format="HH:mm"),
                )
            else:
                attendance.display_name = _(
                    "%(worked_hours)s (%(check_in)s-%(check_out)s)",
                    worked_hours=format_duration(attendance.worked_hours),
                    check_in=format_datetime(self.env, attendance.check_in, dt_format="HH:mm"),
                    check_out=format_datetime(self.env, attendance.check_out, dt_format="HH:mm"),
                )

    def _get_employee_calendar(self):
        self.ensure_one()
        return self.employee_id.resource_calendar_id or self.employee_id.company_id.resource_calendar_id

    @api.depends('check_in', 'check_out')
    def _compute_worked_hours(self):
        """ Computes the worked hours of the attendance record.
            The worked hours of resource with flexible calendar is computed as the difference
            between check_in and check_out, without taking into account the lunch_interval"""
        for attendance in self:
            if attendance.check_out and attendance.check_in and attendance.employee_id:
                calendar = attendance._get_employee_calendar()
                resource = attendance.employee_id.resource_id
                tz = timezone(resource.tz) if not calendar else timezone(calendar.tz)
                check_in_tz = attendance.check_in.astimezone(tz)
                check_out_tz = attendance.check_out.astimezone(tz)
                lunch_intervals = []
                if not attendance.employee_id.is_flexible:
                    lunch_intervals = attendance.employee_id._employee_attendance_intervals(check_in_tz, check_out_tz, lunch=True)
                attendance_intervals = Intervals([(check_in_tz, check_out_tz, attendance)]) - lunch_intervals
                delta = sum((i[1] - i[0]).total_seconds() for i in attendance_intervals)
                attendance.worked_hours = delta / 3600.0
            else:
                attendance.worked_hours = False

    @api.constrains('check_in', 'check_out')
    def _check_validity_check_in_check_out(self):
        """ verifies if check_in is earlier than check_out. """
        for attendance in self:
            if attendance.check_in and attendance.check_out:
                if attendance.check_out < attendance.check_in:
                    raise exceptions.ValidationError(_('"Check Out" time cannot be earlier than "Check In" time.'))

    @api.constrains('check_in', 'check_out', 'employee_id')
    def _check_validity(self):
        """ Verifies the validity of the attendance record compared to the others from the same employee.
            For the same employee we must have :
                * maximum 1 "open" attendance record (without check_out)
                * no overlapping time slices with previous employee records
        """
        for attendance in self:
            # we take the latest attendance before our check_in time and check it doesn't overlap with ours
            last_attendance_before_check_in = self.env['hr.attendance'].search([
                ('employee_id', '=', attendance.employee_id.id),
                ('check_in', '<=', attendance.check_in),
                ('id', '!=', attendance.id),
            ], order='check_in desc', limit=1)
            if last_attendance_before_check_in and last_attendance_before_check_in.check_out and last_attendance_before_check_in.check_out > attendance.check_in:
                raise exceptions.ValidationError(_("Cannot create new attendance record for %(empl_name)s, the employee was already checked in on %(datetime)s",
                                                   empl_name=attendance.employee_id.name,
                                                   datetime=format_datetime(self.env, attendance.check_in, dt_format=False)))

            if not attendance.check_out:
                # if our attendance is "open" (no check_out), we verify there is no other "open" attendance
                no_check_out_attendances = self.env['hr.attendance'].search([
                    ('employee_id', '=', attendance.employee_id.id),
                    ('check_out', '=', False),
                    ('id', '!=', attendance.id),
                ], order='check_in desc', limit=1)
                if no_check_out_attendances:
                    raise exceptions.ValidationError(_("Cannot create new attendance record for %(empl_name)s, the employee hasn't checked out since %(datetime)s",
                                                       empl_name=attendance.employee_id.name,
                                                       datetime=format_datetime(self.env, no_check_out_attendances.check_in, dt_format=False)))
            else:
                # we verify that the latest attendance with check_in time before our check_out time
                # is the same as the one before our check_in time computed before, otherwise it overlaps
                last_attendance_before_check_out = self.env['hr.attendance'].search([
                    ('employee_id', '=', attendance.employee_id.id),
                    ('check_in', '<', attendance.check_out),
                    ('id', '!=', attendance.id),
                ], order='check_in desc', limit=1)
                if last_attendance_before_check_out and last_attendance_before_check_in != last_attendance_before_check_out:
                    raise exceptions.ValidationError(_("Cannot create new attendance record for %(empl_name)s, the employee was already checked in on %(datetime)s",
                                                       empl_name=attendance.employee_id.name,
                                                       datetime=format_datetime(self.env, last_attendance_before_check_out.check_in, dt_format=False)))

    @api.model
    def _get_day_start_and_day(self, employee, dt):
        #Returns a tuple containing the datetime in naive UTC of the employee's start of the day
        # and the date it was for that employee
        if not dt.tzinfo:
            date_employee_tz = pytz.utc.localize(dt).astimezone(pytz.timezone(employee._get_tz()))
        else:
            date_employee_tz = dt
        start_day_employee_tz = date_employee_tz.replace(hour=0, minute=0, second=0)
        return (start_day_employee_tz.astimezone(pytz.utc).replace(tzinfo=None), start_day_employee_tz.date())

    def _get_attendances_dates(self):
        # Returns a dictionnary {employee_id: set((datetimes, dates))}
        attendances_emp = defaultdict(set)
        for attendance in self.filtered(lambda a: a.check_in):
            check_in_day_start = attendance._get_day_start_and_day(attendance.employee_id, attendance.check_in)
            attendances_emp[attendance.employee_id].add(check_in_day_start)
            if attendance.check_out:
                check_out_day_start = attendance._get_day_start_and_day(attendance.employee_id, attendance.check_out)
                attendances_emp[attendance.employee_id].add(check_out_day_start)
        return attendances_emp

    def _get_overtime_leave_domain(self):
        return []

    def _update_overtime(self, employee_attendance_dates=None):
        if employee_attendance_dates is None:
            employee_attendance_dates = self._get_attendances_dates()

        overtime_to_unlink = self.env['hr.attendance.overtime']
        overtime_vals_list = []
        affected_employees = self.env['hr.employee']
        for emp, attendance_dates in employee_attendance_dates.items():
            # get_attendances_dates returns the date translated from the local timezone without tzinfo,
            # and contains all the date which we need to check for overtime
            attendance_domain = []
            for attendance_date in attendance_dates:
                attendance_domain = OR([attendance_domain, [
                    ('check_in', '>=', attendance_date[0]), ('check_in', '<', attendance_date[0] + timedelta(hours=24)),
                ]])
            attendance_domain = AND([[('employee_id', '=', emp.id)], attendance_domain])

            # Attendances per LOCAL day
            attendances_per_day = defaultdict(lambda: self.env['hr.attendance'])
            all_attendances = self.env['hr.attendance'].search(attendance_domain)
            for attendance in all_attendances:
                check_in_day_start = attendance._get_day_start_and_day(attendance.employee_id, attendance.check_in)
                attendances_per_day[check_in_day_start[1]] += attendance

            # As _attendance_intervals_batch and _leave_intervals_batch both take localized dates we need to localize those date
            start = pytz.utc.localize(min(attendance_dates, key=itemgetter(0))[0])
            stop = pytz.utc.localize(max(attendance_dates, key=itemgetter(0))[0] + timedelta(hours=24))

            # Retrieve expected attendance intervals
            calendar = emp.resource_calendar_id or emp.company_id.resource_calendar_id
            expected_attendances = emp._employee_attendance_intervals(start, stop)

            # working_times = {date: [(start, stop)]}
            working_times = defaultdict(lambda: [])
            for expected_attendance in expected_attendances:
                # Exclude resource.calendar.attendance
                working_times[expected_attendance[0].date()].append(expected_attendance[:2])

            overtimes = self.env['hr.attendance.overtime'].sudo().search([
                ('employee_id', '=', emp.id),
                ('date', 'in', [day_data[1] for day_data in attendance_dates]),
                ('adjustment', '=', False),
            ])

            company_threshold = emp.company_id.overtime_company_threshold / 60.0
            employee_threshold = emp.company_id.overtime_employee_threshold / 60.0

            for day_data in attendance_dates:
                attendance_date = day_data[1]
                attendances = attendances_per_day.get(attendance_date, self.browse())
                unfinished_shifts = attendances.filtered(lambda a: not a.check_out)
                overtime_duration = 0
                overtime_duration_real = 0
                # Overtime is not counted if any shift is not closed or if there are no attendances for that day,
                # this could happen when deleting attendances.
                if not unfinished_shifts and attendances:
                    # The employee is working flexible hours
                    if emp.is_flexible:
                        work_duration = 0
                        for attendance in attendances:
                            local_check_in = pytz.utc.localize(attendance.check_in)
                            local_check_out = pytz.utc.localize(attendance.check_out)
                            work_duration += (local_check_out - local_check_in).total_seconds() / 3600.0
                        # In case of fully flexible employee, no overtime is computed
                        if not emp.is_fully_flexible and work_duration > emp.resource_id.calendar_id.hours_per_day:
                            overtime_duration = work_duration - emp.resource_id.calendar_id.hours_per_day
                            overtime_duration_real = overtime_duration

                    # The employee usually doesn't work on that day
                    elif not working_times[attendance_date]:
                        # User does not have any resource_calendar_attendance for that day (week-end for example)
                        overtime_duration = sum(attendances.mapped('worked_hours'))
                        overtime_duration_real = overtime_duration
                    # The employee usually work on that day
                    else:
                        # Compute start and end time for that day
                        planned_start_dt, planned_end_dt = False, False
                        planned_work_duration = 0
                        for calendar_attendance in working_times[attendance_date]:
                            planned_start_dt = min(planned_start_dt, calendar_attendance[0]) if planned_start_dt else calendar_attendance[0]
                            planned_end_dt = max(planned_end_dt, calendar_attendance[1]) if planned_end_dt else calendar_attendance[1]
                            planned_work_duration += (calendar_attendance[1] - calendar_attendance[0]).total_seconds() / 3600.0
                        # Count time before, during and after 'working hours'
                        pre_work_time, work_duration, post_work_time = 0, 0, 0

                        for attendance in attendances:
                            # consider check_in as planned_start_dt if within threshold
                            # if delta_in < 0: Checked in after supposed start of the day
                            # if delta_in > 0: Checked in before supposed start of the day
                            local_check_in = pytz.utc.localize(attendance.check_in)
                            delta_in = (planned_start_dt - local_check_in).total_seconds() / 3600.0

                            # Started before or after planned date within the threshold interval
                            if (delta_in > 0 and delta_in <= company_threshold) or\
                                (delta_in < 0 and abs(delta_in) <= employee_threshold):
                                local_check_in = planned_start_dt
                            local_check_out = pytz.utc.localize(attendance.check_out)

                            # same for check_out as planned_end_dt
                            delta_out = (local_check_out - planned_end_dt).total_seconds() / 3600.0
                            # if delta_out < 0: Checked out before supposed start of the day
                            # if delta_out > 0: Checked out after supposed start of the day

                            # Finised before or after planned date within the threshold interval
                            if (delta_out > 0 and delta_out <= company_threshold) or\
                                (delta_out < 0 and abs(delta_out) <= employee_threshold):
                                local_check_out = planned_end_dt

                            # There is an overtime at the start of the day
                            if local_check_in < planned_start_dt:
                                pre_work_time += (min(planned_start_dt, local_check_out) - local_check_in).total_seconds() / 3600.0
                            # Interval inside the working hours -> Considered as working time
                            if local_check_in <= planned_end_dt and local_check_out >= planned_start_dt:
                                start_dt = max(planned_start_dt, local_check_in)
                                stop_dt = min(planned_end_dt, local_check_out)
                                work_duration += (stop_dt - start_dt).total_seconds() / 3600.0
                                # remove lunch time from work duration
                                lunch_intervals = emp._employee_attendance_intervals(start_dt, stop_dt, lunch=True)
                                work_duration -= sum((i[1] - i[0]).total_seconds() / 3600.0 for i in lunch_intervals)

                            # There is an overtime at the end of the day
                            if local_check_out > planned_end_dt:
                                post_work_time += (local_check_out - max(planned_end_dt, local_check_in)).total_seconds() / 3600.0

                        # Overtime within the planned work hours + overtime before/after work hours is > company threshold
                        overtime_duration = work_duration - planned_work_duration
                        if pre_work_time > company_threshold:
                            overtime_duration += pre_work_time
                        if post_work_time > company_threshold:
                            overtime_duration += post_work_time
                        # Global overtime including the thresholds
                        overtime_duration_real = sum(attendances.mapped('worked_hours')) - planned_work_duration

                overtime = overtimes.filtered(lambda o: o.date == attendance_date)
                if not float_is_zero(overtime_duration, 2) or unfinished_shifts:
                    # Do not create if any attendance doesn't have a check_out, update if exists
                    if unfinished_shifts:
                        overtime_duration = 0
                    if not overtime and overtime_duration:
                        overtime_vals_list.append({
                            'employee_id': emp.id,
                            'date': attendance_date,
                            'duration': overtime_duration,
                            'duration_real': overtime_duration_real,
                        })
                    elif overtime:
                        overtime.sudo().write({
                            'duration': overtime_duration,
                            'duration_real': overtime_duration
                        })
                        affected_employees |= overtime.employee_id
                elif overtime:
                    overtime_to_unlink |= overtime
        created_overtimes = self.env['hr.attendance.overtime'].sudo().create(overtime_vals_list)
        employees_worked_hours_to_compute = (affected_employees.ids +
                                             created_overtimes.employee_id.ids +
                                             overtime_to_unlink.employee_id.ids)
        overtime_to_unlink.sudo().unlink()
        to_recompute = self.search([('employee_id', 'in', employees_worked_hours_to_compute)])
        self.env.add_to_compute(self._fields['overtime_hours'],
                                to_recompute)
        self.env.add_to_compute(self._fields['validated_overtime_hours'],
                                to_recompute)
        self.env.add_to_compute(self._fields['expected_hours'],
                                to_recompute)

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res._update_overtime()
        return res

    def write(self, vals):
        if vals.get('employee_id') and \
            vals['employee_id'] not in self.env.user.employee_ids.ids and \
            not self.env.user.has_group('hr_attendance.group_hr_attendance_officer'):
            raise AccessError(_("Do not have access, user cannot edit the attendances that are not his own."))
        attendances_dates = self._get_attendances_dates()
        result = super(HrAttendance, self).write(vals)
        if any(field in vals for field in ['employee_id', 'check_in', 'check_out']):
            # Merge attendance dates before and after write to recompute the
            # overtime if the attendances have been moved to another day
            for emp, dates in self._get_attendances_dates().items():
                attendances_dates[emp] |= dates
            self._update_overtime(attendances_dates)
        return result

    def unlink(self):
        attendances_dates = self._get_attendances_dates()
        res = super().unlink()
        self._update_overtime(attendances_dates)
        return res

    def copy(self, default=None):
        raise exceptions.UserError(_('You cannot duplicate an attendance.'))

    def action_in_attendance_maps(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': get_google_maps_url(self.in_latitude, self.in_longitude),
            'target': 'new'
        }

    def action_out_attendance_maps(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': get_google_maps_url(self.out_latitude, self.out_longitude),
            'target': 'new'
        }

    def get_kiosk_url(self):
        return self.get_base_url() + "/hr_attendance/" + self.env.company.attendance_kiosk_key

    @api.model
    def has_demo_data(self):
        if not self.env.user.has_group("hr_attendance.group_hr_attendance_manager"):
            return True
        # This record only exists if the scenario has been already launched
        demo_tag = self.env.ref('hr_attendance.resource_calendar_std_38h', raise_if_not_found=False)
        return bool(demo_tag) or bool(self.env['ir.module.module'].search_count([('demo', '=', True)]))

    def _load_demo_data(self):
        if self.has_demo_data():
            return
        self.env['hr.employee']._load_scenario()
        # Load employees, schedules, departments and partners
        convert.convert_file(self.env, 'hr_attendance', 'data/scenarios/hr_attendance_scenario.xml', None, mode='init', kind='data')

        employee_sj = self.env.ref('hr.employee_sj')
        employee_mw = self.env.ref('hr.employee_mw')
        employee_eg = self.env.ref('hr.employee_eg')

        # Retrieve employee from xml file
        # Calculate attendances records for the previous month and the current until today
        now = datetime.now()
        previous_month_datetime = (now - relativedelta(months=1))
        date_range = now.day + monthrange(previous_month_datetime.year, previous_month_datetime.month)[1]
        city_coordinates = (50.27, 5.31)
        city_coordinates_exception = (51.01, 2.82)
        city_dict = {
                    'latitude': city_coordinates_exception[0],
                    'longitude': city_coordinates_exception[1],
                    'city': 'Rellemstraat'
                }
        city_exception_dict = {
            'latitude': city_coordinates[0],
            'longitude': city_coordinates[1],
            'city': 'Waillet'
        }
        attendance_values = []
        for i in range(1, date_range):
            check_in_date = now.replace(hour=6, minute=0, second=randint(0, 59)) + timedelta(days=-i, minutes=randint(-2, 3))
            if check_in_date.weekday() not in range(0, 5):
                continue
            check_out_date = now.replace(hour=10, minute=0, second=randint(0, 59)) + timedelta(days=-i, minutes=randint(-2, -1))
            check_in_date_after_lunch = now.replace(hour=11, minute=0, second=randint(0, 59)) + timedelta(days=-i, minutes=randint(-2, -1))
            check_out_date_after_lunch = now.replace(hour=15, minute=0, second=randint(0, 59)) + timedelta(days=-i, minutes=randint(1, 3))

            # employee_eg doesn't work on friday
            eg_data = []
            if check_in_date.weekday() != 4:
                # employee_eg will compensate her work's hours between weeks.
                if check_in_date.isocalendar().week % 2:
                    employee_eg_hours = {
                        'check_in_date': check_in_date + timedelta(hours=1),
                        'check_out_date': check_out_date,
                        'check_in_date_after_lunch': check_in_date_after_lunch,
                        'check_out_date_after_lunch': check_out_date_after_lunch + timedelta(hours=-1),
                    }
                else:
                    employee_eg_hours = {
                        'check_in_date': check_in_date,
                        'check_out_date': check_out_date,
                        'check_in_date_after_lunch': check_in_date_after_lunch,
                        'check_out_date_after_lunch': check_out_date_after_lunch + timedelta(hours=1, minutes=30),
                    }
                eg_data = [{
                    'employee_id': employee_eg.id,
                    'check_in': employee_eg_hours['check_in_date'],
                    'check_out': employee_eg_hours['check_out_date'],
                    'in_mode': "kiosk",
                    'out_mode': "kiosk"
                }, {
                    'employee_id': employee_eg.id,
                    'check_in': employee_eg_hours['check_in_date_after_lunch'],
                    'check_out': employee_eg_hours['check_out_date_after_lunch'],
                    'in_mode': "kiosk",
                    'out_mode': "kiosk",
                }]

            # calculate GPS coordination for employee_mw (systray attendance)
            if randint(1, 10) == 1:
                city_data = city_exception_dict
            else:
                city_data = city_dict
            mw_data = [{
                'employee_id': employee_mw.id,
                'check_in': check_in_date,
                'check_out': check_out_date,
                'in_mode': "systray",
                'out_mode': "systray",
                'in_longitude': city_data['longitude'],
                'out_longitude': city_data['longitude'],
                'in_latitude': city_data['latitude'],
                'out_latitude': city_data['latitude'],
                'in_city': city_data['city'],
                'out_city': city_data['city'],
                'in_ip_address': "127.0.0.1",
                'out_ip_address': "127.0.0.1",
                'in_browser': 'chrome',
                'out_browser': 'chrome'
            }, {
                'employee_id': employee_mw.id,
                'check_in': check_in_date_after_lunch,
                'check_out': check_out_date_after_lunch,
                'in_mode': "systray",
                'out_mode': "systray",
                'in_longitude': city_data['longitude'],
                'out_longitude': city_data['longitude'],
                'in_latitude': city_data['latitude'],
                'out_latitude': city_data['latitude'],
                'in_city': city_data['city'],
                'out_city': city_data['city'],
                'in_ip_address': "127.0.0.1",
                'out_ip_address': "127.0.0.1",
                'in_browser': 'chrome',
                'out_browser': 'chrome'
            }]
            sj_data = [{
                'employee_id': employee_sj.id,
                'check_in': check_in_date + timedelta(minutes=randint(-10, -5)),
                'check_out': check_out_date,
                'in_mode': "manual",
                'out_mode': "manual"
            }, {
                'employee_id': employee_sj.id,
                'check_in': check_in_date_after_lunch,
                'check_out': check_out_date_after_lunch + timedelta(hours=1, minutes=randint(-20, 10)),
                'in_mode': "manual",
                'out_mode': "manual"
            }]
            attendance_values.extend(eg_data + mw_data + sj_data)
        self.env['hr.attendance'].create(attendance_values)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_try_kiosk(self):
        if not self.env.user.has_group("hr_attendance.group_hr_attendance_manager"):
            return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': _("You don't have the rights to execute that action."),
                        'type': 'info',
                    }
            }
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': self.env.company.attendance_kiosk_url + '?from_trial_mode=True'
        }

    def _read_group_employee_id(self, resources, domain):
        user_domain = self.env.context.get('user_domain')
        if not user_domain:
            return self.env['hr.employee'].search([('company_id', 'in', self.env.context.get('allowed_company_ids', []))])
        else:
            employee_name_domain = []
            for leaf in user_domain:
                if len(leaf) == 3 and leaf[0] == 'employee_id':
                    employee_name_domain.append([('name', leaf[1], leaf[2])])
            return resources | self.env['hr.employee'].search(OR(employee_name_domain))

    def action_approve_overtime(self):
        self.write({
            'overtime_status': 'approved'
        })

    def action_refuse_overtime(self):
        self.write({
            'overtime_status': 'refused'
        })

    def _cron_auto_check_out(self):
        to_verify = self.env['hr.attendance'].search(
            [('check_out', '=', False),
             ('employee_id.company_id.auto_check_out', '=', True)]
        )

        if not to_verify:
            return

        previous_duration = self.env['hr.attendance']._read_group(
            domain=[
                ('employee_id', 'in', to_verify.mapped('employee_id').ids),
                ('check_in', '>', (fields.Datetime.now() - relativedelta(days=1)).replace(hour=0, minute=0, second=0)),
                ('check_out', '!=', False)], groupby=['check_in:day', 'employee_id'], aggregates=['worked_hours:sum'])

        mapped_previous_duration = defaultdict(lambda: defaultdict(float))
        for rec in previous_duration:
            mapped_previous_duration[rec[1]][rec[0].date()] += rec[2]

        all_companies = to_verify.employee_id.company_id

        for company in all_companies:
            max_tol = company.auto_check_out_tolerance
            to_verify_company = to_verify.filtered(lambda a: a.employee_id.company_id.id == company.id)

            # Attendances where Last open attendance worked time + previously worked time on that day + tolerance greater than the planned worked hours in his calendar
            to_check_out = to_verify_company.filtered(lambda a: (fields.Datetime.now() - a.check_in).seconds + mapped_previous_duration[a.employee_id][a.check_in.date()] - max_tol > (sum(a.employee_id.resource_calendar_id.attendance_ids.filtered(lambda att: att.dayofweek == str(a.check_in.weekday())).mapped('duration_hours'))))
            body = _('This attendance was automatically checked out because the employee exceeded the allowed time for their scheduled work hours.')

            for att in to_check_out:
                delta_duration = max(1, (sum(att.employee_id.resource_calendar_id.attendance_ids.filtered(lambda a: a.dayofweek == str(att.check_in.weekday())).mapped('duration_hours')) + max_tol - mapped_previous_duration[att.employee_id][att.check_in.date()]) * 3600)
                att.write({
                    "check_out": att.check_in + relativedelta(seconds=delta_duration),
                    "out_mode": "auto_check_out"
                })
                att.message_post(body=body)

    def _cron_absence_detection(self):
        """
        Objective is to create technical attendances on absence days to have negative overtime created for that day
        """
        yesterday = datetime.today().replace(hour=0, minute=0, second=0) - relativedelta(days=1)
        companies = self.env['res.company'].search([('absence_management', '=', True)])
        if not companies:
            return

        checked_in_employees = self.env['hr.attendance.overtime'].search([('date', '=', yesterday),
                                                                          ('adjustment', '=', False)]).employee_id

        technical_attendances_vals = []
        absent_employees = self.env['hr.employee'].search([('id', 'not in', checked_in_employees.ids),
                                                           ('company_id', 'in', companies.ids)])
        for emp in absent_employees:
            local_day_start = pytz.utc.localize(yesterday).astimezone(pytz.timezone(emp._get_tz()))
            technical_attendances_vals.append({
                'check_in': local_day_start.strftime('%Y-%m-%d %H:%M:%S'),
                'check_out': (local_day_start + relativedelta(seconds=1)).strftime('%Y-%m-%d %H:%M:%S'),
                'in_mode': 'technical',
                'out_mode': 'technical',
                'employee_id': emp.id
            })

        technical_attendances = self.env['hr.attendance'].create(technical_attendances_vals)
        to_unlink = technical_attendances.filtered(lambda a: a.overtime_hours == 0)

        body = _('This attendance was automatically created to cover an unjustified absence on that day.')
        for technical_attendance in technical_attendances - to_unlink:
            technical_attendance.message_post(body=body)

        to_unlink.unlink()
