# Part of Odoo. See LICENSE file for full copyright and licensing details.

from calendar import monthrange
from collections import defaultdict
from datetime import UTC, datetime, time, timedelta
from random import randint
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta
from dateutil.rrule import DAILY, rrule

from odoo import _, api, exceptions, fields, models
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.tools import convert, format_datetime, format_duration, format_time
from odoo.tools.date_utils import float_to_time, sum_intervals
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
    in_image = fields.Binary(string="Check-In Image")
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
    device_tracking_enabled = fields.Boolean(related="employee_id.company_id.attendance_device_tracking")
    day_of_date = fields.Selection(
        compute='_compute_day_of_date',
        store=True,
        string="Day",
        index=True,
        selection=[('0', "Monday"), ('1', "Tuesday"), ('2', "Wednesday"), ('3', "Thursday"), ('4', "Friday"), ('5', "Saturday"), ('6', "Sunday")],
    )
    resource_calendar_id = fields.Many2one(related='employee_id.resource_calendar_id', string="Working Schedule")
    work_entry_type_id = fields.Many2one(
        'hr.work.entry.type', string="Work Entry Type", index=True,
        default=lambda self: self.env.company.attendance_work_entry_type_id,
    )

    # time rule engine output fields
    is_time_rule_output = fields.Boolean(default=False, index=True)
    time_rule_id = fields.Many2one('hr.time.rule', index=True)
    source_attendance_id = fields.Many2one('hr.attendance', ondelete='cascade', index=True)
    overtime_attendance_ids = fields.One2many('hr.attendance', 'source_attendance_id')

    # aliases
    date_from = fields.Datetime(related='check_in', string="Date From")
    date_to = fields.Datetime(related='check_out', string="Date To")

    @api.depends('date')
    def _compute_day_of_date(self):
        for record in self:
            if record.date:
                record.day_of_date = str(record.date.weekday())
            else:
                record.day_of_date = False

    @api.depends("check_in", "employee_id")
    def _compute_date(self):
        for attendance in self:
            if not attendance.employee_id or not attendance.check_in:  # weird precompute edge cases. Never after creation
                attendance.date = datetime.today()
                continue
            tz = ZoneInfo(attendance.employee_id._get_tz())
            attendance.date = attendance.check_in.replace(tzinfo=UTC).astimezone(tz).date()

    def _compute_color(self):
        for attendance in self:
            if attendance.check_out:
                attendance.color = 1 if attendance.worked_hours > 16 or attendance.out_mode == 'technical' else 0
            else:
                attendance.color = 1 if attendance.check_in < (datetime.today() - timedelta(days=1)) else 10

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

    @api.depends('is_manager', 'is_own')
    def _compute_can_edit(self):
        for attendance in self:
            attendance.can_edit = attendance.is_manager or attendance.is_own

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
        start_dt_tz = max(self.check_in, start_dt).replace(tzinfo=UTC).astimezone(tz)
        end_dt_tz = min(self.check_out, end_dt).replace(tzinfo=UTC).astimezone(tz)

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
        """Verify attendance records don't overlap; skip time rule engine output records."""
        if self.env.context.get('skip_time_rules'):
            return
        for attendance in self.filtered(lambda a: not a.is_time_rule_output):
            src_domain = [
                ('employee_id', '=', attendance.employee_id.id),
                ('id', '!=', attendance.id),
                ('is_time_rule_output', '=', False),
            ]
            last_before_check_in = self.env['hr.attendance'].search(
                src_domain + [('check_in', '<=', attendance.check_in)],
                order='check_in desc', limit=1,
            )
            if (last_before_check_in and last_before_check_in.check_out
                    and last_before_check_in.check_out > attendance.check_in):
                raise exceptions.ValidationError(_(
                    "Cannot create new attendance record for %(empl_name)s, "
                    "the employee was already checked in on %(datetime)s",
                    empl_name=attendance.employee_id.name,
                    datetime=format_datetime(self.env, attendance.check_in, dt_format=False),
                ))
            if not attendance.check_out:
                no_co = self.env['hr.attendance'].search(
                    src_domain + [('check_out', '=', False)],
                    order='check_in desc', limit=1,
                )
                if no_co:
                    raise exceptions.ValidationError(_(
                        "Cannot create new attendance record for %(empl_name)s, "
                        "the employee hasn't checked out since %(datetime)s",
                        empl_name=attendance.employee_id.name,
                        datetime=format_datetime(self.env, no_co.check_in, dt_format=False),
                    ))
            else:
                last_before_check_out = self.env['hr.attendance'].search(
                    src_domain + [('check_in', '<', attendance.check_out)],
                    order='check_in desc', limit=1,
                )
                if last_before_check_out and last_before_check_in != last_before_check_out:
                    raise exceptions.ValidationError(_(
                        "Cannot create new attendance record for %(empl_name)s, "
                        "the employee was already checked in on %(datetime)s",
                        empl_name=attendance.employee_id.name,
                        datetime=format_datetime(self.env, last_before_check_out.check_in, dt_format=False),
                    ))

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

    def write(self, vals):
        if vals.get('employee_id') and \
            vals['employee_id'] not in self.env.user.employee_ids.ids and \
            not self.env.user.has_group('hr_attendance.group_hr_attendance_manager') and \
            self.env['hr.employee'].sudo().browse(vals['employee_id']).attendance_manager_id.id != self.env.user.id:
            raise AccessError(_("Do not have access, user cannot edit the attendances that are not their own or if they are not the attendance manager of the employee."))
        result = super().write(vals)
        if not self.env.context.get('skip_time_rules') and any(
            f in vals for f in ('employee_id', 'check_in', 'check_out', 'work_entry_type_id')
        ):
            self._process_time_rules()
        return result

    def unlink(self):
        return super().unlink()

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

    def _cron_auto_check_out(self):
        self._cron_auto_check_out_tolerance()
        self._cron_auto_check_out_specific_time()

    def _cron_auto_check_out_tolerance(self):
        def check_in_tz(attendance):
            """Returns check-in time in calendar's timezone."""
            return attendance.check_in.astimezone(ZoneInfo(attendance.employee_id._get_tz(attendance.date)))

        to_verify = self.env['hr.attendance'].search(
            [('check_out', '=', False),
             ('employee_id.company_id.auto_check_out', '=', True),
             ('employee_id.company_id.auto_check_out_mode', '=', 'tolerance'),
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

                employee_timezone = ZoneInfo(att.employee_id._get_tz(att.date))
                check_in_datetime = check_in_tz(att)
                now_datetime = fields.Datetime.now().astimezone(employee_timezone)
                current_attendance_duration = (now_datetime - check_in_datetime).total_seconds() / 3600
                previous_attendances_duration = mapped_previous_duration[att.employee_id][check_in_datetime.date()]

                check_in_day_start = check_in_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
                expected_worked_hours = sum_intervals(
                    att.employee_id._get_expected_attendances(
                        check_in_day_start,
                        check_in_day_start + timedelta(days=1),
                    )
                )

                # Attendances where Last open attendance time + previously worked time on that day + tolerance greater than the attendances hours (including lunch) in his calendar
                if (current_attendance_duration + previous_attendances_duration - max_tol) > expected_worked_hours:
                    att.with_context(skip_time_rules=True).check_out = check_in_datetime.replace(hour=23, minute=59, second=59).astimezone(UTC).replace(tzinfo=None)
                    excess_hours = att.worked_hours - (expected_worked_hours + max_tol - previous_attendances_duration)
                    att.write({
                        "check_out": max(att.check_out - relativedelta(hours=excess_hours), att.check_in + relativedelta(seconds=1)),
                        "out_mode": "auto_check_out"
                    })
                    att.message_post(
                        body=_('This attendance was automatically checked out because the employee exceeded the allowed time for their scheduled work hours.')
                    )

    def _cron_absence_detection(self):
        """Create a 1-second technical attendance for each employee who did not check in yesterday.

        This triggers the time rule pipeline so that undertime rules can generate
        output attendances for the missed schedule hours.  The attendance type is set
        to the company's default so condition filters on undertime rules match it.
        Technical attendances that produce no time rule output are discarded afterwards.
        """
        yesterday = datetime.today().replace(hour=0, minute=0, second=0) - relativedelta(days=1)
        companies = self.env['res.company'].search([('absence_management', '=', True)])
        if not companies:
            return

        checked_in_employees = self.env['hr.attendance'].search([('date', '=', yesterday)]).employee_id

        technical_attendances_vals = []
        absent_employees = self.env['hr.employee'].search([
            ('id', 'not in', checked_in_employees.ids),
            ('company_id', 'in', companies.ids),
            ('resource_calendar_id', '!=', False),
            ('current_version_id.contract_date_start', '<=', fields.Date.today() - relativedelta(days=1))
        ])

        for emp in absent_employees:
            local_day_start = yesterday.replace(tzinfo=ZoneInfo(emp._get_tz()))
            check_in_utc = local_day_start.astimezone(UTC)
            technical_attendances_vals.append({
                'check_in': check_in_utc.strftime('%Y-%m-%d %H:%M:%S'),
                'check_out': (check_in_utc + relativedelta(seconds=1)).strftime('%Y-%m-%d %H:%M:%S'),
                'work_entry_type_id': emp.company_id.attendance_work_entry_type_id.id,
                'in_mode': 'technical',
                'out_mode': 'technical',
                'employee_id': emp.id
            })

        technical_attendances = self.env['hr.attendance'].create(technical_attendances_vals)
        to_unlink = technical_attendances.filtered(lambda a: not a.overtime_attendance_ids)
        body = _('This attendance was automatically created to cover an unjustified absence on that day.')
        for technical_attendance in technical_attendances:
            technical_attendance.message_post(body=body)

        to_unlink.unlink()

    def _cron_auto_check_out_specific_time(self):
        """
        Automatically check-out all employees still checked in
        when company is in 'specific_time' mode.
        """
        current_utc_dt = fields.Datetime.now()
        utc_tz = ZoneInfo('UTC')
        all_open_attendances = self.search([
            ('check_out', '=', False),
            ('employee_id.company_id', 'any', [
                ('auto_check_out', '=', True),
                ('auto_check_out_mode', '=', 'specific_time'),
            ]),
        ])

        for company, company_attendances in all_open_attendances.grouped(lambda att: att.employee_id.company_id).items():
            cutoff_time = float_to_time(company.auto_check_out_specific_time)
            cutoff_hour, cutoff_minute = cutoff_time.hour, cutoff_time.minute
            for att in company_attendances:
                employee_tz = ZoneInfo(att.employee_id._get_tz())
                current_employee_dt = current_utc_dt.astimezone(employee_tz)
                check_in_employee_dt = att.check_in.astimezone(employee_tz)
                same_day_cutoff_dt = check_in_employee_dt.replace(
                    hour=cutoff_hour, minute=cutoff_minute, second=0, microsecond=0,
                )

                if check_in_employee_dt.time() < same_day_cutoff_dt.time():
                    next_cutoff = same_day_cutoff_dt
                else:
                    next_cutoff = same_day_cutoff_dt + relativedelta(days=1)

                if current_employee_dt < next_cutoff:
                    continue

                employee_checkout = next_cutoff.astimezone(utc_tz).replace(tzinfo=None)
                employee_checkout = max(employee_checkout, att.check_in + relativedelta(seconds=1))

                att.write({
                    'check_out': employee_checkout,
                    'out_mode': 'auto_check_out',
                })

                att.message_post(body=self.env._(
                    'This attendance was automatically checked out based on company specific time configuration.',
                ))

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
            result[attendance] = list(rrule(DAILY, dtstart=localized_start.date(), until=localized_end.date()))
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
                intersected_day_interval = attendance_interval & day_interval
                intersected_week_interval = attendance_interval & week_interval
                if intersected_day_interval:
                    attendance_by_employee_by_day[employee][day] |= intersected_day_interval
                if intersected_week_interval:
                    attendance_by_employee_by_week[employee][week_date] |= intersected_week_interval

        return {
            'day': attendance_by_employee_by_day,
            'week': attendance_by_employee_by_week
        }

    def init(self):
        super().init()
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS hr_attendance_check_in_check_out_employee_id
            ON hr_attendance (check_in, check_out, employee_id);
        """)

    def _process_time_rules(self):
        """Recompute time rule output attendances for employees/dates affected by self."""
        source = self.filtered(lambda a: not a.is_time_rule_output and a.check_in and a.check_out)
        if not source:
            return
        affected = [(a.employee_id, a.check_in, a.check_out) for a in source]
        self._process_time_rules_for(affected)

    def _process_time_rules_for(self, affected):
        if not affected:
            return

        rules = self.env['hr.time.rule'].sudo().search([
            '|', ('company_id', '=', False),
            ('company_id', 'in', self.env.companies.ids),
            ('active', '=', True),
        ])
        if not rules:
            return

        day_rules = rules.filtered(lambda r: r.quantity_period != 'week')
        week_rules = rules.filtered(lambda r: r.quantity_period == 'week')

        day_rules_ranges = defaultdict(lambda: [None, None])
        for employee, check_in, check_out in affected:
            df = check_in.date() if hasattr(check_in, 'date') else check_in
            dt = check_out.date() if hasattr(check_out, 'date') else check_out
            r = day_rules_ranges[employee]
            r[0] = df if r[0] is None else min(r[0], df)
            r[1] = dt if r[1] is None else max(r[1], dt)

        weekly_starts = {int(r.week_start or '0') for r in week_rules}
        week_rules_ranges = {}
        if weekly_starts:
            for employee, (df, dt) in day_rules_ranges.items():
                wdf, wdt = df, dt
                for ws in weekly_starts:
                    wdf = min(wdf, wdf - timedelta(days=(wdf.weekday() - ws) % 7))
                    wdt = max(wdt, wdt + timedelta(days=(ws - 1 - wdt.weekday()) % 7))
                week_rules_ranges[employee] = (wdf, wdt)

        day_excess, day_deficit = self._collect_time_rule_outputs(day_rules, day_rules_ranges)
        week_excess, week_deficit = self._collect_time_rule_outputs(week_rules, week_rules_ranges)

        merged_excess = self._merge_rule_outputs(day_excess, week_excess)
        merged_deficit = self._merge_rule_outputs(day_deficit, week_deficit)
        (day_rules | week_rules)._apply_attendance_output(merged_excess, merged_deficit)

    def _collect_time_rule_outputs(self, rules, ranges_by_employee):
        all_excess = defaultdict(lambda: defaultdict(list))
        all_deficit = defaultdict(lambda: defaultdict(list))
        if not rules:
            return all_excess, all_deficit

        by_range = defaultdict(list)
        for employee, (date_from, date_to) in ranges_by_employee.items():
            start_dt = datetime.combine(date_from, time.min).replace(tzinfo=UTC)
            end_dt = datetime.combine(date_to, time.max).replace(tzinfo=UTC)
            by_range[start_dt, end_dt].append(employee)

        for (start_dt, end_dt), employees in by_range.items():
            employee_rs = self.env['hr.employee'].browse([e.id for e in employees])
            source_attendances = self._get_source_attendances_for_time_rules(employee_rs, start_dt, end_dt)
            if not source_attendances:
                continue

            self._restore_source_attendance_bounds(source_attendances)

            rule_ids = rules.ids
            self.env['hr.attendance'].sudo().search([
                ('source_attendance_id', 'in', source_attendances.ids),
                ('time_rule_id', 'in', rule_ids),
            ]).with_context(skip_time_rules=True).unlink()

            self.env['hr.attendance'].sudo().search([
                ('is_time_rule_output', '=', True),
                ('source_attendance_id', '=', False),
                ('employee_id', 'in', source_attendances.employee_id.ids),
                ('check_in', '<', end_dt.replace(tzinfo=None)),
                ('check_out', '>', start_dt.replace(tzinfo=None)),
                ('time_rule_id', 'in', rule_ids),
            ]).with_context(skip_time_rules=True).unlink()

            excess, deficit = rules._evaluate_rules(source_attendances, start_dt, end_dt)
            for emp, by_att in excess.items():
                for att, items in by_att.items():
                    all_excess[emp][att].extend(items)
            for emp, by_att in deficit.items():
                for att, items in by_att.items():
                    all_deficit[emp][att].extend(items)

        return all_excess, all_deficit

    def _merge_rule_outputs(self, a, b):
        merged = defaultdict(lambda: defaultdict(list))
        for outputs in (a, b):
            for emp, by_att in outputs.items():
                for att, items in by_att.items():
                    merged[emp][att].extend(items)
        return merged

    def _get_source_attendances_for_time_rules(self, employees, start_dt, end_dt):
        return self.env['hr.attendance'].sudo().search([
            ('is_time_rule_output', '=', False),
            ('source_attendance_id', '=', False),
            ('employee_id', 'in', employees.ids),
            ('check_in', '<=', end_dt.replace(tzinfo=None)),
            ('check_out', '>=', start_dt.replace(tzinfo=None)),
            ('check_out', '!=', False),
        ])

    def _restore_source_attendance_bounds(self, source_attendances):
        """Expand each source attendance to cover the bounding box of itself + its excess outputs.

        Deficit outputs (undertime) represent absent time outside the source's worked range
        and must not influence the restored bounds.
        """
        children = self.env['hr.attendance'].sudo().search([
            ('source_attendance_id', 'in', source_attendances.ids),
            ('time_rule_id.threshold_operator', '!=', 'less_than'),
        ])
        if not children:
            return
        bounds = defaultdict(lambda: [None, None])
        for child in children:
            src_id = child.source_attendance_id.id
            if bounds[src_id][0] is None or child.check_in < bounds[src_id][0]:
                bounds[src_id][0] = child.check_in
            if bounds[src_id][1] is None or child.check_out > bounds[src_id][1]:
                bounds[src_id][1] = child.check_out
        auto_ctx = dict(skip_time_rules=True, tracking_disable=True)
        for src in source_attendances:
            if src.id not in bounds:
                continue
            new_in, new_out = bounds[src.id]
            restored_in = min(src.check_in, new_in) if new_in else src.check_in
            restored_out = max(src.check_out, new_out) if new_out else src.check_out
            if restored_in != src.check_in or restored_out != src.check_out:
                src.with_context(**auto_ctx).write({
                    'check_in': restored_in,
                    'check_out': restored_out,
                })

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res.filtered(lambda a: not self.env.context.get('skip_time_rules'))._process_time_rules()
        return res

    @api.ondelete(at_uninstall=False)
    def _unlink_output_attendances(self):
        self.sudo().mapped('overtime_attendance_ids').with_context(skip_time_rules=True).unlink()
