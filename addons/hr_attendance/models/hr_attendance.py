# Part of Odoo. See LICENSE file for full copyright and licensing details.

from calendar import monthrange
from collections import defaultdict
from datetime import UTC, datetime, time, timedelta
from itertools import chain
from random import randint
from zoneinfo import ZoneInfo

from dateutil.relativedelta import MO, SU, relativedelta
from dateutil.rrule import DAILY, rrule

from odoo import _, api, exceptions, fields, models
from odoo.exceptions import AccessError
from odoo.fields import Domain
from odoo.http import request
from odoo.tools import convert, format_datetime, format_duration, format_time
from odoo.tools.date_utils import sum_intervals
from odoo.tools.intervals import Intervals


def get_google_maps_url(latitude, longitude):
    return "https://maps.google.com?q=%s,%s" % (latitude, longitude)


class HrAttendance(models.Model):
    _name = 'hr.attendance'
    _description = "Attendance"
    _order = "check_in desc"
    _inherit = ["mail.thread"]

    def _default_employee(self):
        return self.env.user.employee_id

    employee_id = fields.Many2one('hr.employee', string="Employee", default=_default_employee, required=True,
        ondelete='cascade', index=True)
    department_id = fields.Many2one('hr.department', string="Department", related="employee_id.department_id",
        readonly=True)
    manager_id = fields.Many2one(comodel_name='hr.employee', related="employee_id.parent_id", readonly=True,
        export_string_translation=False)
    attendance_manager_id = fields.Many2one('res.users', related="employee_id.attendance_manager_id",
        export_string_translation=False)
    is_manager = fields.Boolean(compute="_compute_is_manager")
    is_own = fields.Boolean(compute="_compute_is_manager")
    can_edit = fields.Boolean(compute="_compute_can_edit")
    check_in = fields.Datetime(string="Check In", default=fields.Datetime.now, required=True, tracking=True, index=True)
    check_out = fields.Datetime(string="Check Out", tracking=True)
    date = fields.Date(string="Date", compute='_compute_date', store=True, index=True, precompute=True, required=True)
    worked_hours = fields.Float(string='Worked Hours', compute='_compute_worked_hours', store=True, readonly=True)
    color = fields.Integer(compute='_compute_color')
    overtime_hours = fields.Float(string="Over Time", compute='_compute_overtime_hours', store=True)
    overtime_status = fields.Selection(selection=[('to_approve', "To Approve"),
                                                  ('approved', "Approved"),
                                                  ('refused', "Refused")], compute="_compute_overtime_status", store=True, tracking=True, readonly=False)
    validated_overtime_hours = fields.Float(string="Extra Hours", compute='_compute_validated_overtime_hours', tracking=True, store=True, readonly=True)
    in_latitude = fields.Float(string="Latitude", digits=(10, 7), readonly=True, aggregator=None)
    in_longitude = fields.Float(string="Longitude", digits=(10, 7), readonly=True, aggregator=None)
    in_location = fields.Char(help="Based on GPS-Coordinates if available or on IP Address")
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
    out_location = fields.Char(help="Based on GPS-Coordinates if available or on IP Address")
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
    device_tracking_enabled = fields.Boolean(related="employee_id.company_id.attendance_device_tracking")
    linked_overtime_ids = fields.Many2many('hr.attendance.overtime.line', compute='_compute_linked_overtime_ids', readonly=False)

    @api.depends("check_in", "employee_id")
    def _compute_date(self):
        for attendance in self:
            if not attendance.employee_id or not attendance.check_in:  # weird precompute edge cases. Never after creation
                attendance.date = datetime.today()
                continue
            tz = ZoneInfo(attendance.employee_id._get_tz())
            attendance.date = attendance.check_in.replace(tzinfo=UTC).astimezone(tz).date()

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

    @api.depends('check_in', 'check_out', 'employee_id')
    def _compute_overtime_status(self):
        for attendance in self:
            if not attendance.linked_overtime_ids:
                attendance.overtime_status = False
            elif all(attendance.linked_overtime_ids.mapped(lambda ot: ot.status == 'approved')):
                attendance.overtime_status = 'approved'
            elif all(attendance.linked_overtime_ids.mapped(lambda ot: ot.status == 'refused')):
                attendance.overtime_status = 'refused'
            else:
                attendance.overtime_status = 'to_approve'

    @api.depends('check_in', 'check_out', 'employee_id')
    def _compute_overtime_hours(self):
        for attendance in self:
            attendance.overtime_hours = sum(attendance.linked_overtime_ids.mapped('manual_duration'))

    @api.depends('check_in', 'check_out', 'employee_id')
    def _compute_validated_overtime_hours(self):
        for attendance in self:
            attendance.validated_overtime_hours = sum(attendance.linked_overtime_ids.filtered_domain([('status', '=', 'approved')]).mapped('manual_duration'))

    @api.depends('check_in', 'check_out', 'employee_id')
    def _compute_linked_overtime_ids(self):
        overtimes_by_attendance = self._linked_overtimes().grouped(lambda ot: (ot.employee_id, ot.time_start))
        for attendance in self:
            attendance.linked_overtime_ids = overtimes_by_attendance.get((attendance.employee_id, attendance.check_in), False)

    @api.depends('employee_id', 'check_in', 'check_out')
    def _compute_display_name(self):
        tz = request.httprequest.cookies.get('tz') if request else None
        for attendance in self:
            if not attendance.check_out:
                attendance.display_name = _(
                    "From %s",
                    format_time(self.env, attendance.check_in, time_format=None, tz=tz, lang_code=self.env.lang),
                )
            else:
                attendance.display_name = _(
                    "%(worked_hours)s (%(check_in)s-%(check_out)s)",
                    worked_hours=format_duration(attendance.worked_hours),
                    check_in=format_time(self.env, attendance.check_in, time_format=None, tz=tz, lang_code=self.env.lang),
                    check_out=format_time(self.env, attendance.check_out, time_format=None, tz=tz, lang_code=self.env.lang),
                )

    @api.depends_context('uid')
    @api.depends('employee_id')
    def _compute_is_manager(self):
        have_manager_right = self.env.user.has_group('hr_attendance.group_hr_attendance_user')
        have_officer_right = self.env.user.has_group('hr_attendance.group_hr_attendance_officer')
        have_own_right = self.env.user.has_group('hr_attendance.group_hr_attendance_own')
        for attendance in self:
            attendance.is_manager = have_manager_right or \
                (have_officer_right and attendance.attendance_manager_id.id == self.env.user.id)
            attendance.is_own = have_own_right and attendance.employee_id.user_id == self.env.user

    @api.depends('employee_id.company_id.attendance_overtime_validation', 'is_manager', 'is_own', 'overtime_status')
    def _compute_can_edit(self):
        for attendance in self:
            validation = attendance.employee_id.company_id.attendance_overtime_validation
            if attendance.is_manager:
                attendance.can_edit = True
            elif attendance.is_own:
                attendance.can_edit = not (attendance.overtime_status == 'approved' and validation == 'by_manager')
            else:
                attendance.can_edit = False

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
                attendance.worked_hours = attendance._get_worked_hours_in_range(attendance.check_in, attendance.check_out)
            else:
                attendance.worked_hours = False

    def _get_worked_hours_in_range(self, start_dt, end_dt):
        """Returns the amount of hours worked because of this attendance during the
        interval defined by [start_dt, end_dt]

        :param start_dt: datetime starting the interval.
        :param end_dt: datetime ending the interval.
        :returns: float, hours worked
        """
        self.ensure_one()
        tz = ZoneInfo(self.employee_id._get_tz(self.check_in))
        start_dt_tz = max(self.check_in, start_dt).astimezone(tz)
        end_dt_tz = min(self.check_out, end_dt).astimezone(tz)

        if end_dt_tz < start_dt_tz:
            return 0.0

        attendance_intervals = Intervals([(start_dt_tz, end_dt_tz, self)])
        return sum_intervals(attendance_intervals)

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
    def _get_day_start_and_day(self, employee, dt):  # TODO probably no longer need by the end
        # Returns a tuple containing the datetime in naive UTC of the employee's start of the day
        # and the date it was for that employee
        if not dt.tzinfo:
            employee_tz = employee._get_tz(dt)[employee.id]
            date_employee_tz = dt.replace(tzinfo=UTC).astimezone(ZoneInfo(employee_tz))
        else:
            date_employee_tz = dt
        start_day_employee_tz = date_employee_tz.replace(hour=0, minute=0, second=0)
        return (start_day_employee_tz.astimezone(UTC).replace(tzinfo=None), start_day_employee_tz.date())

    def _get_week_date_range(self):
        assert self
        dates = self.mapped('date')
        date_start, date_end = min(dates), max(dates)
        date_start = date_start - relativedelta(days=date_start.weekday())
        date_end = date_end + relativedelta(days=6 - date_end.weekday())
        return date_start, date_end

    def _get_overtimes_to_update_domain(self):
        if not self:
            return Domain.FALSE
        domain_list = [Domain.AND([
            Domain('employee_id', '=', employee.id),
            Domain('date', '<=', max(attendances.mapped('check_out')).date() + relativedelta(SU)),
            Domain('date', '>=', min(attendances.mapped('check_in')).date() + relativedelta(MO(-1))),
        ]) for employee, attendances in self.filtered(lambda att: att.check_out).grouped('employee_id').items()]
        if not domain_list:
            return Domain.FALSE
        return Domain.OR(domain_list) if len(domain_list) > 1 else domain_list[0]

    def _update_overtime(self, attendance_domain=None):
        if not attendance_domain:
            attendance_domain = self._get_overtimes_to_update_domain()
        self.env['hr.attendance.overtime.line'].search(attendance_domain).unlink()
        all_attendances = (self | self.env['hr.attendance'].search(attendance_domain)).filtered_domain([('check_out', '!=', False)])
        if not all_attendances:
            return

        start_check_in = min(all_attendances.mapped('check_in')).date() - relativedelta(days=1)  # for timezone
        min_check_in = datetime.combine(start_check_in, time.min).replace(tzinfo=UTC)

        end_check_out = max(all_attendances.mapped('check_out')).date() + relativedelta(days=1)
        max_check_out = datetime.combine(end_check_out, time.max).replace(tzinfo=UTC)  # for timezone

        version_periods_by_employee = all_attendances.employee_id.sudo()._get_version_periods(start_check_in, end_check_out)
        version_periods_by_employee = {
            emp: [
                (
                    datetime.combine(p_start, time.min).replace(tzinfo=UTC),
                    datetime.combine(p_stop, time.min).replace(tzinfo=UTC),
                    v)
                for p_start, p_stop, v in periods
            ]
            for emp, periods in version_periods_by_employee.items()
        }
        attendances_by_employee = all_attendances.grouped('employee_id')
        attendances_by_ruleset = defaultdict(lambda: self.env['hr.attendance'])
        for employee, emp_attendance in attendances_by_employee.items():
            if employee not in version_periods_by_employee:
                continue
            for attendance in emp_attendance:
                attendance_intervals = Intervals([(
                    attendance.check_in.replace(tzinfo=UTC),
                    attendance.check_out.replace(tzinfo=UTC),
                    self.env['hr.version'])])
                inter = Intervals(version_periods_by_employee[employee]) & attendance_intervals
                if not inter:
                    continue
                version = inter._items[0][2]
                ruleset = version.ruleset_id
                if ruleset:
                    attendances_by_ruleset[ruleset] += attendance
        employees = all_attendances.employee_id
        schedules_intervals_by_employee = employees._get_schedules_by_employee_by_work_type(min_check_in, max_check_out, version_periods_by_employee)
        overtime_vals_list = []
        for ruleset, ruleset_attendances in attendances_by_ruleset.items():
            attendances_dates = list(chain(*ruleset_attendances._get_dates().values()))
            overtime_vals_list.extend(
                ruleset.rule_ids._generate_overtime_vals_v2(min(attendances_dates), max(attendances_dates), ruleset_attendances, schedules_intervals_by_employee)
            )
        self.env['hr.attendance.overtime.line'].create(overtime_vals_list)
        self.env.add_to_compute(self._fields['overtime_hours'], all_attendances)
        self.env.add_to_compute(self._fields['validated_overtime_hours'], all_attendances)
        self.env.add_to_compute(self._fields['overtime_status'], all_attendances)

    # Split the Attendance Shift If it across the employee local midnight and save in UTC
    def _split_attendance_intervals(self, employee, check_in, check_out):
        if check_out < check_in:
            return
        tz = ZoneInfo(employee._get_tz())
        current_start_utc = check_in
        while current_start_utc < check_out:
            local_start = current_start_utc.replace(tzinfo=UTC).astimezone(tz)
            next_day_date = local_start.date() + timedelta(days=1)
            local_midnight = datetime.combine(next_day_date, datetime.min.time(), tzinfo=tz)
            midnight_utc = local_midnight.astimezone(UTC).replace(tzinfo=None)
            current_end_utc = min(midnight_utc, check_out)
            yield (current_start_utc, current_end_utc)
            current_start_utc = current_end_utc

    def _check_cross_day_shift(self, vals, attendance=None):
        employee_id = self.env['hr.employee'].browse(vals['employee_id']) if vals.get('employee_id') else attendance.employee_id if attendance else None
        check_in = fields.Datetime.from_string(vals.get('check_in')) if vals.get('check_in') else attendance.check_in if attendance else None
        check_out = fields.Datetime.from_string(vals.get('check_out')) if vals.get('check_out') else attendance.check_out if attendance else None
        if not (employee_id and check_in and check_out):
            return [vals]

        tz = ZoneInfo(employee_id._get_tz())
        # Same Day Shift
        if check_out.astimezone(tz).date() <= check_in.astimezone(tz).date():
            current_vals = vals.copy()
            current_vals.update({
                'employee_id': employee_id.id,
                'check_in': fields.Datetime.to_string(check_in),
                'check_out': fields.Datetime.to_string(check_out),
            })
            return [current_vals]

        # Cross Day Shift
        intervals = list(self._split_attendance_intervals(employee_id, check_in, check_out))
        new_vals_list = []
        for current_check_in, current_check_out in intervals:
            current_vals = vals.copy()
            current_vals.update({
                'employee_id': employee_id.id,
                'check_in': fields.Datetime.to_string(current_check_in),
                'check_out': fields.Datetime.to_string(current_check_out),
            })
            new_vals_list.append(current_vals)
        return new_vals_list

    @api.model_create_multi
    def create(self, vals_list):
        final_vals_list = []
        for vals in vals_list:
            final_vals_list.extend(self._check_cross_day_shift(vals))
        res = super().create(final_vals_list)
        res._update_overtime()
        return res

    def write(self, vals):
        if vals.get('employee_id') and \
            vals['employee_id'] not in self.env.user.employee_ids.ids and \
            not self.env.user.has_group('hr_attendance.group_hr_attendance_officer'):
            raise AccessError(_("Do not have access, user cannot edit the attendances that are not his own."))
        domain_pre = self._get_overtimes_to_update_domain()

        if ('check_out' in vals):
            for attendance in self:
                new_vals_list = self._check_cross_day_shift(vals, attendance)
                vals['check_in'] = new_vals_list[0]['check_in']
                vals['check_out'] = new_vals_list[0]['check_out']
                vals['employee_id'] = new_vals_list[0].get('employee_id', attendance.employee_id.id)
                for extra_vals in new_vals_list[1:]:
                    self.env['hr.attendance'].create(extra_vals)
        result = super(HrAttendance, self).write(vals)
        if any(field in vals for field in ['employee_id', 'check_in', 'check_out']):
            # Merge attendance dates before and after write to recompute the
            # overtime if the attendances have been moved to another day
            domain_post = self._get_overtimes_to_update_domain()
            self._update_overtime(Domain.OR([domain_pre, domain_post]))
        return result

    def unlink(self):
        domain = self._get_overtimes_to_update_domain()
        res = super().unlink()
        self.exists()._update_overtime(domain)
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
        if not self.env.user.has_group("hr_attendance.group_hr_attendance_user"):
            return True
        # This record only exists if the scenario has been already launched
        demo_tag = self.env.ref('hr_attendance.resource_calendar_std_38h', raise_if_not_found=False)
        return bool(demo_tag) or bool(self.env['ir.module.module'].search_count([('demo', '=', True)]))

    def _load_demo_data(self):
        if self.has_demo_data():
            return
        env_sudo = self.sudo().with_context({}).env
        env_sudo['hr.employee']._load_scenario()
        # Load employees, schedules, departments and partners
        convert.convert_file(env_sudo, 'hr_attendance', 'data/scenarios/hr_attendance_scenario.xml', None, mode='init')

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
                'in_location': city_data['city'],
                'out_location': city_data['city'],
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
                'in_location': city_data['city'],
                'out_location': city_data['city'],
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
        if not self.env.user.has_group("hr_attendance.group_hr_attendance_user"):
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

    def _linked_overtimes(self):
        return self.env['hr.attendance.overtime.line'].search([
            ('time_start', 'in', self.mapped('check_in')),
            ('employee_id', 'in', self.employee_id.ids),
        ])

    def action_approve_overtime(self):
        self.linked_overtime_ids.action_approve()

    def action_refuse_overtime(self):
        self.linked_overtime_ids.action_refuse()

    def _cron_auto_check_out(self):
        def check_in_tz(attendance):
            """Returns check-in time in calendar's timezone."""
            return attendance.check_in.astimezone(ZoneInfo(attendance.employee_id._get_tz()))

        to_verify = self.env['hr.attendance'].search(
            [('check_out', '=', False),
             ('employee_id.company_id.auto_check_out', '=', True),
             ('employee_id.resource_calendar_id', '!=', False)]
        )

        if not to_verify:
            return

        to_verify_min_date = min(to_verify.mapped('check_in')).replace(hour=0, minute=0, second=0)
        previous_attendances = self.env['hr.attendance'].search([
                    ('employee_id', 'in', to_verify.mapped('employee_id').ids),
                    ('check_in', '>', to_verify_min_date),
                    ('check_out', '!=', False)
        ])

        mapped_previous_duration = defaultdict(lambda: defaultdict(float))
        for previous in previous_attendances:
            mapped_previous_duration[previous.employee_id][check_in_tz(previous).date()] += previous.worked_hours

        all_companies = to_verify.employee_id.company_id

        for company in all_companies:
            max_tol = company.auto_check_out_tolerance
            to_verify_company = to_verify.filtered(lambda a: a.employee_id.company_id.id == company.id)

            for att in to_verify_company:

                employee_timezone = ZoneInfo(att.employee_id._get_tz())
                check_in_datetime = check_in_tz(att)
                now_datetime = fields.Datetime.now().astimezone(employee_timezone)
                current_attendance_duration = (now_datetime - check_in_datetime).total_seconds() / 3600
                previous_attendances_duration = mapped_previous_duration[att.employee_id][check_in_datetime.date()]

                expected_worked_hours = sum(
                    att.employee_id.resource_calendar_id.attendance_ids.filtered(
                        lambda a: a.dayofweek == str(check_in_datetime.weekday())
                    ).mapped("duration_hours")
                )

                # Attendances where Last open attendance time + previously worked time on that day + tolerance greater than the attendances hours (including lunch) in his calendar
                if (current_attendance_duration + previous_attendances_duration - max_tol) > expected_worked_hours:
                    tz = ZoneInfo(att.employee_id._get_tz())
                    check_in_local = att.check_in.replace(tzinfo=UTC).astimezone(tz)
                    estimated_checkout_local = check_in_local.replace(hour=23, minute=59, second=59)
                    estimated_checkout = estimated_checkout_local.astimezone(UTC).replace(tzinfo=None)
                    att.check_out = estimated_checkout

                    excess_hours = att.worked_hours - (expected_worked_hours + max_tol - previous_attendances_duration)
                    att.write({
                        "check_out": max(att.check_out - relativedelta(hours=excess_hours), att.check_in + relativedelta(seconds=1)),
                        "out_mode": "auto_check_out"
                    })
                    att.message_post(
                        body=_('This attendance was automatically checked out because the employee exceeded the allowed time for their scheduled work hours.')
                    )

    def _cron_absence_detection(self):
        """
        Objective is to create technical attendances on absence days to have negative overtime created for that day
        """
        yesterday = datetime.today().replace(hour=0, minute=0, second=0) - relativedelta(days=1)
        companies = self.env['res.company'].search([('absence_management', '=', True)])
        if not companies:
            return

        checked_in_employees = self.env['hr.attendance.overtime.line'].search([('date', '=', yesterday)]).employee_id

        technical_attendances_vals = []
        absent_employees = self.env['hr.employee'].search([
            ('id', 'not in', checked_in_employees.ids),
            ('company_id', 'in', companies.ids),
            ('resource_calendar_id', '!=', False),
            ('current_version_id.contract_date_start', '<=', fields.Date.today() - relativedelta(days=1))
        ])

        for emp in absent_employees:
            local_day_start = yesterday.replace(tzinfo=UTC).astimezone(ZoneInfo(emp._get_tz()))
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

    def _get_localized_times(self):
        self.ensure_one()
        tz = ZoneInfo(self.employee_id.sudo()._get_version(self.check_in.date()).tz)
        localized_start = self.check_in.replace(tzinfo=UTC).astimezone(tz).replace(tzinfo=None)
        localized_end = self.check_out.replace(tzinfo=UTC).astimezone(tz).replace(tzinfo=None)
        return localized_start, localized_end

    def _get_dates(self):
        result = {}
        for attendance in self:
            localized_start, localized_end = attendance._get_localized_times()
            result[attendance] = list(rrule(DAILY, dtstart=localized_start, until=localized_end))
        return result

    def _get_attendance_by_periods_by_employee(self):
        attendance_by_employee_by_day = defaultdict(lambda: defaultdict(lambda: Intervals([], keep_distinct=True)))
        attendance_by_employee_by_week = defaultdict(lambda: defaultdict(lambda: Intervals([], keep_distinct=True)))

        for attendance in self.sorted('check_in'):
            employee = attendance.employee_id
            check_in, check_out = attendance._get_localized_times()
            for day in rrule(dtstart=check_in.date(), until=check_out.date(), freq=DAILY):
                week_date = day + relativedelta(days=6 - day.weekday())

                start_datetime = datetime.combine(day, time.min)
                stop_datetime_for_day = datetime.combine(day, time.max)
                day_interval = Intervals([(start_datetime, stop_datetime_for_day, self.env['resource.calendar'])])

                stop_datetime_for_week = datetime.combine(week_date, time.max)
                week_interval = Intervals([(start_datetime, stop_datetime_for_week, self.env['resource.calendar'])])

                attendance_interval = Intervals([(check_in, check_out, attendance)])
                attendance_by_employee_by_day[employee][day] |= attendance_interval & day_interval
                attendance_by_employee_by_week[employee][week_date] |= attendance_interval & week_interval

        return {
            'day': attendance_by_employee_by_day,
            'week': attendance_by_employee_by_week
        }
