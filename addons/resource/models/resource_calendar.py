# Part of Odoo. See LICENSE file for full copyright and licensing details.

import itertools
from collections import defaultdict
from datetime import datetime, time, timedelta
from functools import partial
from itertools import chain

from dateutil.relativedelta import relativedelta
from dateutil.rrule import DAILY, rrule
from pytz import timezone, utc

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Command, Domain
from odoo.tools import date_utils, float_compare, ormcache
from odoo.tools.date_utils import float_to_time, localized, to_timezone
from odoo.tools.float_utils import float_round
from odoo.tools.intervals import Intervals

from odoo.addons.base.models.res_partner import _tz_get


class ResourceCalendar(models.Model):
    """ Calendar model for a resource. It has

    - attendance_ids: list of resource.calendar.attendance that are a working
                    interval in a given weekday.
    - leave_ids: list of leaves linked to this calendar. A leave can be general
                or linked to a specific resource, depending on its resource_id.

    All methods in this class use intervals. An interval is a tuple holding
    (begin_datetime, end_datetime). A list of intervals is therefore a list of
    tuples, holding several intervals of work or leaves. """
    _name = 'resource.calendar'
    _description = "Resource Working Time"

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if not res.get('name') and res.get('company_id'):
            res['name'] = self.env._('Working Hours of %s', self.env['res.company'].browse(res['company_id']).name)
        if 'attendance_ids' in fields and not res.get('attendance_ids'):
            company_id = res.get('company_id', self.env.company.id)
            company = self.env['res.company'].browse(company_id)
            res["attendance_ids"] = self._get_default_attendance_ids(company)
            res["two_weeks_calendar"] = company.resource_calendar_id.two_weeks_calendar
        if 'full_time_required_hours' in fields and not res.get('full_time_required_hours'):
            company_id = res.get('company_id', self.env.company.id)
            company = self.env['res.company'].browse(company_id)
            res['full_time_required_hours'] = company.resource_calendar_id.full_time_required_hours
        return res

    name = fields.Char(required=True)
    active = fields.Boolean("Active", default=True,
                            help="If the active field is set to false, it will allow you to hide the Working Time without removing it.")
    attendance_ids = fields.One2many(
        'resource.calendar.attendance', 'calendar_id', 'Working Time',
        compute='_compute_attendance_ids', store=True, readonly=False, copy=True)
    attendance_ids_1st_week = fields.One2many('resource.calendar.attendance', 'calendar_id', 'Working Time 1st Week',
        compute="_compute_two_weeks_attendance", inverse="_inverse_two_weeks_calendar")
    attendance_ids_2nd_week = fields.One2many('resource.calendar.attendance', 'calendar_id', 'Working Time 2nd Week',
        compute="_compute_two_weeks_attendance", inverse="_inverse_two_weeks_calendar")
    company_id = fields.Many2one(
        'res.company', 'Company', domain=lambda self: [('id', 'in', self.env.companies.ids)],
        default=lambda self: self.env.company, index='btree_not_null')
    leave_ids = fields.One2many(
        'resource.calendar.leaves', 'calendar_id', 'Time Off')
    schedule_type = fields.Selection(
        [
            ('flexible', 'Flexible'),
            ('fully_fixed', 'Fully Fixed'),
        ],
        string='Schedule Type',
        required=True,
        default='fully_fixed',
        help="Choose which level of definition you want to define on your Schedule\n"
            "- Flexible : Define an amount of hours to work on the week.\n"
            "- Fully Fixed : define the days, periods and the start & end time for each period of the day",
    )
    flexible_hours = fields.Boolean(string="Flexible Hours",
        compute="_compute_flexible_hours", inverse="_inverse_flexible_hours", store=True,
        help="When enabled, it will allow employees to work flexibly, without relying on the company's working schedule (working hours).")
    full_time_required_hours = fields.Float(
        string="Company Full Time",
        compute="_compute_full_time_required_hours", store=True, readonly=False,
        help="Number of hours to work on the company schedule to be considered as fulltime.")
    global_leave_ids = fields.One2many(
        'resource.calendar.leaves', 'calendar_id', 'Global Time Off',
        compute='_compute_global_leave_ids', store=True, readonly=False,
        domain=[('resource_id', '=', False)], copy=True,
    )
    hours_per_day = fields.Float("Average Hour per Day", store=True, compute="_compute_hours_per_day", digits=(2, 2), readonly=False,
        help="Average hours per day a resource is supposed to work with this calendar.")
    hours_per_week = fields.Float(
        string="Hours per Week",
        compute="_compute_hours_per_week", store=True, readonly=False, copy=False)
    is_fulltime = fields.Boolean(compute='_compute_work_time_rate', string="Is Full Time")
    two_weeks_calendar = fields.Boolean(string="Calendar in 2 weeks mode")
    two_weeks_explanation = fields.Char('Explanation', compute="_compute_two_weeks_explanation")
    tz = fields.Selection(
        _tz_get, string='Timezone', required=True,
        default=lambda self: self.env.context.get('tz') or self.env.user.tz or self.env.ref('base.user_admin').tz or 'UTC',
        help="This field is used in order to define in which timezone the resources will work.")
    tz_offset = fields.Char(compute='_compute_tz_offset', string='Timezone offset')
    work_resources_count = fields.Integer("Work Resources count", compute='_compute_work_resources_count')
    work_time_rate = fields.Float(string='Work Time Rate', compute='_compute_work_time_rate', search='_search_work_time_rate',
        help='Work time rate versus full time working schedule, should be between 0 and 100 %.')

    # --------------------------------------------------
    # Constrains
    # --------------------------------------------------

    @api.constrains('attendance_ids')
    def _check_attendance_ids(self):
        for res_calendar in self:
            if (res_calendar.two_weeks_calendar and
                    res_calendar.attendance_ids.filtered(lambda a: a.display_type == 'line_section') and
                    not res_calendar.attendance_ids.sorted('sequence')[0].display_type):
                raise ValidationError(self.env._("In a calendar with 2 weeks mode, all periods need to be in the sections."))

            # Avoid superimpose in attendance
            attendance_ids = res_calendar.attendance_ids.filtered(
                lambda attendance: not attendance.resource_id and attendance.display_type is False)
            if res_calendar.two_weeks_calendar:
                res_calendar._check_overlap(attendance_ids.filtered(lambda attendance: attendance.week_type == '0'))
                res_calendar._check_overlap(attendance_ids.filtered(lambda attendance: attendance.week_type == '1'))
            else:
                res_calendar._check_overlap(attendance_ids)

    # --------------------------------------------------
    # Compute Methods
    # --------------------------------------------------

    @api.depends('two_weeks_calendar')
    def _compute_two_weeks_attendance(self):
        for calendar in self:
            if not calendar.two_weeks_calendar:
                continue
            calendar.attendance_ids_1st_week = calendar.attendance_ids.filtered(lambda a: a.week_type == '0')
            calendar.attendance_ids_2nd_week = calendar.attendance_ids.filtered(lambda a: a.week_type == '1')

    def _inverse_two_weeks_calendar(self):
        for calendar in self:
            if not calendar.two_weeks_calendar:
                continue
            calendar.attendance_ids = calendar.attendance_ids_1st_week + calendar.attendance_ids_2nd_week

    @api.depends('hours_per_week', 'company_id.resource_calendar_id.hours_per_week')
    def _compute_full_time_required_hours(self):
        for calendar in self.filtered("company_id"):
            calendar.full_time_required_hours = calendar.company_id.resource_calendar_id.hours_per_week

    @api.depends("schedule_type")
    def _compute_flexible_hours(self):
        for calendar in self:
            calendar.flexible_hours = calendar.schedule_type == 'flexible'

    def _inverse_flexible_hours(self):
        for calendar in self:
            calendar.schedule_type = 'flexible' if calendar.flexible_hours else 'fully_fixed'

    @api.depends('company_id')
    def _compute_attendance_ids(self):
        for calendar in self.filtered(lambda c: not c._origin or (c._origin.company_id != c.company_id and c.company_id)):
            company_calendar = calendar.company_id.resource_calendar_id
            calendar.update({
                'two_weeks_calendar': company_calendar.two_weeks_calendar,
                'tz': company_calendar.tz,
                'attendance_ids': [(5, 0, 0)] + [
                    (0, 0, attendance._copy_attendance_vals()) for attendance in company_calendar.attendance_ids if not attendance.resource_id],
            })

    @api.onchange('attendance_ids')
    def _onchange_attendance_ids(self):
        if not self.two_weeks_calendar:
            return

        even_week_seq = self.attendance_ids.filtered(lambda att: att.display_type == 'line_section' and att.week_type == '0')
        odd_week_seq = self.attendance_ids.filtered(lambda att: att.display_type == 'line_section' and att.week_type == '1')
        if len(even_week_seq) != 1 or len(odd_week_seq) != 1:
            raise ValidationError(self.env._("You can't delete section between weeks."))

        even_week_seq = even_week_seq.sequence
        odd_week_seq = odd_week_seq.sequence

        for line in self.attendance_ids.filtered(lambda att: att.display_type is False):
            if even_week_seq > odd_week_seq:
                line.week_type = '1' if even_week_seq > line.sequence else '0'
            else:
                line.week_type = '0' if odd_week_seq > line.sequence else '1'

    @api.depends('company_id')
    def _compute_global_leave_ids(self):
        for calendar in self.filtered(lambda c: not c._origin or c._origin.company_id != c.company_id):
            calendar.update({
                'global_leave_ids': [(5, 0, 0)] + [
                    (0, 0, leave._copy_leave_vals()) for leave in calendar.company_id.resource_calendar_id.global_leave_ids],
            })

    @api.depends('attendance_ids', 'attendance_ids.hour_from', 'attendance_ids.hour_to', 'two_weeks_calendar', 'flexible_hours')
    def _compute_hours_per_day(self):
        """ Compute the average hours per day.
            Cannot directly depend on hours_per_week because of rounding issues. """
        for calendar in self.filtered(lambda c: not c.flexible_hours):
            calendar.hours_per_day = float_round(calendar._get_hours_per_day(), precision_digits=2)

    @api.depends('attendance_ids', 'attendance_ids.hour_from', 'attendance_ids.hour_to', 'two_weeks_calendar', 'flexible_hours')
    def _compute_hours_per_week(self):
        """ Compute the average hours per week """
        for calendar in self.filtered(lambda c: not c.flexible_hours):
            calendar.hours_per_week = float_round(calendar._get_hours_per_week(), precision_digits=2)

    @api.depends('two_weeks_calendar')
    def _compute_two_weeks_explanation(self):
        today = fields.Date.today()
        week_type = self.env['resource.calendar.attendance'].get_week_type(today)
        week_type_str = self.env._("even") if week_type else self.env._("odd")
        first_day = date_utils.start_of(today, 'week')
        last_day = date_utils.end_of(today, 'week')
        self.two_weeks_explanation = self.env._(
            "The current week (from %(first_day)s to %(last_day)s) corresponds to %(number)s week.",
            first_day=first_day,
            last_day=last_day,
            number=week_type_str,
        )

    @api.depends('tz')
    def _compute_tz_offset(self):
        for calendar in self:
            calendar.tz_offset = datetime.now(timezone(calendar.tz or 'GMT')).strftime('%z')

    def _compute_work_resources_count(self):
        resources_per_calendar = dict(self.env['resource.resource']._read_group(
            domain=[('calendar_id', 'in', self.ids)],
            groupby=['calendar_id'],
            aggregates=['__count']))
        for calendar in self:
            calendar.work_resources_count = resources_per_calendar.get(calendar, 0)

    @api.depends('hours_per_week', 'full_time_required_hours')
    def _compute_work_time_rate(self):
        for calendar in self:
            if calendar.full_time_required_hours:
                calendar.work_time_rate = calendar.hours_per_week / calendar.full_time_required_hours * 100
            else:
                calendar.work_time_rate = 100

            calendar.is_fulltime = float_compare(calendar.full_time_required_hours, calendar.hours_per_week, 3) == 0

    @api.model
    def _search_work_time_rate(self, operator, value):
        if operator in ('in', 'not in'):
            if not all(isinstance(v, int) for v in value):
                return NotImplemented
        elif operator in ('<', '>'):
            if not isinstance(value, int):
                return NotImplemented
        else:
            return NotImplemented

        calendar_ids = self.env['resource.calendar']._search(Domain('work_time', operator, value))
        return [('id', 'in', calendar_ids)]

    # --------------------------------------------------
    # Overrides
    # --------------------------------------------------

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        return [dict(vals, name=self.env._("%s (copy)", calendar.name)) for calendar, vals in zip(self, vals_list)]

    # --------------------------------------------------
    # Actions
    # --------------------------------------------------

    def switch_calendar_type(self):
        self.ensure_one()
        if not self.two_weeks_calendar:
            self.two_weeks_calendar = True
            final_attendances = [
                Command.create({
                    'name': 'First week',
                    'dayofweek': '0',
                    'sequence': '0',
                    'hour_from': 0,
                    'day_period': 'morning',
                    'week_type': '0',
                    'hour_to': 0,
                    'display_type':
                    'line_section'}),
                Command.create({
                    'name': 'Second week',
                    'dayofweek': '0',
                    'sequence': '25',
                    'hour_from': 0,
                    'day_period': 'morning',
                    'week_type': '1',
                    'hour_to': 0,
                    'display_type': 'line_section'}),
            ]
            for idx, att in enumerate(self.attendance_ids):
                final_attendances.append(Command.create(dict(att._copy_attendance_vals(), week_type='0', sequence=idx + 1)))
                final_attendances.append(Command.create(dict(att._copy_attendance_vals(), week_type='1', sequence=idx + 26)))
            self.attendance_ids = [Command.clear()] + final_attendances

        else:
            self.two_weeks_calendar = False
            self.attendance_ids.unlink()
            self.attendance_ids = self._get_default_attendance_ids(self.company_id)

    # --------------------------------------------------
    # Computation API
    # --------------------------------------------------

    def _attendance_intervals_batch(self, start_dt, end_dt, resources=None, domain=None, tz=None, lunch=False):
        assert start_dt.tzinfo and end_dt.tzinfo
        self.ensure_one()
        if not resources:
            resources = self.env['resource.resource']
            resources_list = [resources]
        else:
            resources_list = list(resources) + [self.env['resource.resource']]
        resource_ids = [r.id for r in resources_list]
        domain = Domain.AND([
            Domain(domain or Domain.TRUE),
            Domain('calendar_id', '=', self.id),
            Domain('resource_id', 'in', resource_ids),
            Domain('display_type', '=', False),
            Domain('day_period', '!=' if not lunch else '=', 'lunch'),
        ])

        attendances = self.env['resource.calendar.attendance'].search(domain)
        # Since we only have one calendar to take in account
        # Group resources per tz they will all have the same result
        resources_per_tz = defaultdict(list)
        for resource in resources_list:
            resources_per_tz[tz or timezone((resource or self).tz)].append(resource)
        # Resource specific attendances
        attendance_per_resource = defaultdict(lambda: self.env['resource.calendar.attendance'])
        # Calendar attendances per day of the week
        # * 7 days per week * 2 for two week calendars
        attendances_per_day = [self.env['resource.calendar.attendance']] * 7 * 2
        weekdays = set()
        for attendance in attendances:
            if attendance.resource_id:
                attendance_per_resource[attendance.resource_id] |= attendance
            weekday = int(attendance.dayofweek)
            weekdays.add(weekday)
            if self.two_weeks_calendar:
                weektype = int(attendance.week_type)
                attendances_per_day[weekday + 7 * weektype] |= attendance
            else:
                attendances_per_day[weekday] |= attendance
                attendances_per_day[weekday + 7] |= attendance

        start = start_dt.astimezone(utc)
        end = end_dt.astimezone(utc)
        bounds_per_tz = {
            tz: (start_dt.astimezone(tz), end_dt.astimezone(tz))
            for tz in resources_per_tz
        }
        # Use the outer bounds from the requested timezones
        for low, high in bounds_per_tz.values():
            start = min(start, low.replace(tzinfo=utc))
            end = max(end, high.replace(tzinfo=utc))
        # Generate once with utc as timezone
        days = rrule(DAILY, start.date(), until=end.date(), byweekday=weekdays)
        ResourceCalendarAttendance = self.env['resource.calendar.attendance']
        base_result = []
        per_resource_result = defaultdict(list)
        for day in days:
            week_type = ResourceCalendarAttendance.get_week_type(day)
            attendances = attendances_per_day[day.weekday() + 7 * week_type]
            for attendance in attendances:
                if (attendance.date_from and day.date() < attendance.date_from) or\
                    (attendance.date_to and attendance.date_to < day.date()):
                    continue
                day_from = datetime.combine(day, float_to_time(attendance.hour_from))
                day_to = datetime.combine(day, float_to_time(attendance.hour_to))
                if attendance.resource_id:
                    per_resource_result[attendance.resource_id].append((day_from, day_to, attendance))
                else:
                    base_result.append((day_from, day_to, attendance))

        # Copy the result localized once per necessary timezone
        # Strictly speaking comparing start_dt < time or start_dt.astimezone(tz) < time
        # should always yield the same result. however while working with dates it is easier
        # if all dates have the same format
        result_per_tz = {
            tz: [(max(bounds_per_tz[tz][0], tz.localize(val[0])),
                min(bounds_per_tz[tz][1], tz.localize(val[1])),
                val[2])
                    for val in base_result]
            for tz in resources_per_tz
        }
        result_per_resource_id = dict()
        for tz, resources in resources_per_tz.items():
            res = result_per_tz[tz]

            res_intervals = Intervals(res, keep_distinct=True)
            start_datetime = start_dt.astimezone(tz)
            end_datetime = end_dt.astimezone(tz)

            for resource in resources:
                if resource and resource._is_fully_flexible():
                    # If the resource is fully flexible, return the whole period from start_dt to end_dt with a dummy attendance
                    hours = (end_dt - start_dt).total_seconds() / 3600
                    days = hours / 24
                    dummy_attendance = self.env['resource.calendar.attendance'].new({
                        'duration_hours': hours,
                        'duration_days': days,
                    })
                    result_per_resource_id[resource.id] = Intervals([(start_dt, end_dt, dummy_attendance)], keep_distinct=True)
                elif resource and resource.calendar_id.flexible_hours:
                    # For flexible Calendars, we create intervals to fill in the weekly intervals with the average daily hours
                    # until the full time required hours are met. This gives us the most correct approximation when looking at a daily
                    # and weekly range for time offs and overtime calculations and work entry generation
                    start_date = start_datetime.date()
                    end_datetime_adjusted = end_datetime - relativedelta(seconds=1)
                    end_date = end_datetime_adjusted.date()

                    full_time_required_hours = resource.calendar_id.full_time_required_hours
                    max_hours_per_day = resource.calendar_id.hours_per_day

                    intervals = []
                    current_monday = start_date - timedelta(days=start_date.weekday())

                    while current_monday <= end_date:
                        current_sunday = current_monday + timedelta(days=6)

                        week_start = max(current_monday, start_date)
                        week_end = min(current_sunday, end_date)

                        if current_monday < start_date:
                            prior_days = (start_date - current_monday).days
                            prior_hours = min(full_time_required_hours, max_hours_per_day * prior_days)
                        else:
                            prior_hours = 0

                        remaining_hours = max(0, full_time_required_hours - prior_hours)

                        current_day = week_start
                        while current_day <= week_end:
                            if remaining_hours > 0:
                                allocate_hours = min(max_hours_per_day, remaining_hours)
                                remaining_hours -= allocate_hours

                                # Create interval centered at 12:00 PM
                                midpoint = tz.localize(datetime.combine(current_day, time(12, 0)))
                                start_time = midpoint - timedelta(hours=allocate_hours / 2)
                                end_time = midpoint + timedelta(hours=allocate_hours / 2)

                                dummy_attendance = self.env['resource.calendar.attendance'].new({
                                    'duration_hours': allocate_hours,
                                    'duration_days': 1,
                                })

                                intervals.append((start_time, end_time, dummy_attendance))

                            current_day += timedelta(days=1)

                        current_monday += timedelta(days=7)

                    result_per_resource_id[resource.id] = Intervals(intervals, keep_distinct=True)
                elif resource in per_resource_result:
                    resource_specific_result = [(max(bounds_per_tz[tz][0], tz.localize(val[0])), min(bounds_per_tz[tz][1], tz.localize(val[1])), val[2]) for val in per_resource_result[resource]]
                    result_per_resource_id[resource.id] = Intervals(itertools.chain(res, resource_specific_result), keep_distinct=True)
                else:
                    result_per_resource_id[resource.id] = res_intervals
        return result_per_resource_id

    def _handle_flexible_leave_interval(self, dt0, dt1, leave):
        """Hook method to handle flexible leave intervals. Can be overridden in other modules."""
        tz = dt0.tzinfo  # Get the timezone information from dt0
        dt0 = datetime.combine(dt0.date(), time.min).replace(tzinfo=tz)
        dt1 = datetime.combine(dt1.date(), time.max).replace(tzinfo=tz)
        return dt0, dt1

    def _leave_intervals(self, start_dt, end_dt, resource=None, domain=None, tz=None):
        if resource is None:
            resource = self.env['resource.resource']
        return self._leave_intervals_batch(
            start_dt, end_dt, resources=resource, domain=domain, tz=tz,
        )[resource.id]

    def _leave_intervals_batch(self, start_dt, end_dt, resources=None, domain=None, tz=None, any_calendar=False):
        """ Return the leave intervals in the given datetime range.
            The returned intervals are expressed in specified tz or in the calendar's timezone.
        """
        assert start_dt.tzinfo and end_dt.tzinfo
        self.ensure_one()

        if not resources:
            resources = self.env['resource.resource']
            resources_list = [resources]
        else:
            resources_list = list(resources) + [self.env['resource.resource']]
        if domain is None:
            domain = [('time_type', '=', 'leave')]
        if not any_calendar:
            domain = domain + [('calendar_id', 'in', [False, self.id])]
        # for the computation, express all datetimes in UTC
        # Public leave don't have a resource_id
        domain = domain + [
            ('resource_id', 'in', [False] + [r.id for r in resources_list]),
            ('date_from', '<=', end_dt.astimezone(utc).replace(tzinfo=None)),
            ('date_to', '>=', start_dt.astimezone(utc).replace(tzinfo=None)),
        ]

        # retrieve leave intervals in (start_dt, end_dt)
        result = defaultdict(list)
        tz_dates = {}
        all_leaves = self.env['resource.calendar.leaves'].search(domain)
        for leave in all_leaves:
            leave_resource = leave.resource_id
            leave_company = leave.company_id
            leave_date_from = leave.date_from
            leave_date_to = leave.date_to
            for resource in resources_list:
                if leave_resource.id not in [False, resource.id] or (not leave_resource and resource and resource.company_id != leave_company):
                    continue
                tz = tz if tz else timezone((resource or self).tz)
                if (tz, start_dt) in tz_dates:
                    start = tz_dates[tz, start_dt]
                else:
                    start = start_dt.astimezone(tz)
                    tz_dates[tz, start_dt] = start
                if (tz, end_dt) in tz_dates:
                    end = tz_dates[tz, end_dt]
                else:
                    end = end_dt.astimezone(tz)
                    tz_dates[tz, end_dt] = end
                dt0 = leave_date_from.astimezone(tz)
                dt1 = leave_date_to.astimezone(tz)
                if leave_resource and leave_resource._is_fully_flexible():
                    dt0, dt1 = self._handle_flexible_leave_interval(dt0, dt1, leave)
                result[resource.id].append((max(start, dt0), min(end, dt1), leave))

        return {r.id: Intervals(result[r.id]) for r in resources_list}

    def _work_intervals_batch(self, start_dt, end_dt, resources=None, domain=None, tz=None, compute_leaves=True):
        """ Return the effective work intervals between the given datetimes. """
        if not resources:
            resources = self.env['resource.resource']
            resources_list = [resources]
        else:
            resources_list = list(resources) + [self.env['resource.resource']]

        attendance_intervals = self._attendance_intervals_batch(start_dt, end_dt, resources, tz=tz or self.env.context.get("employee_timezone"))
        if compute_leaves:
            leave_intervals = self._leave_intervals_batch(start_dt, end_dt, resources, domain, tz=tz)
            return {
                r.id: (attendance_intervals[r.id] - leave_intervals[r.id]) for r in resources_list
            }
        return {
            r.id: attendance_intervals[r.id] for r in resources_list
        }

    def _unavailable_intervals(self, start_dt, end_dt, resource=None, domain=None, tz=None):
        if resource is None:
            resource = self.env['resource.resource']
        return self._unavailable_intervals_batch(
            start_dt, end_dt, resources=resource, domain=domain, tz=tz,
        )[resource.id]

    def _unavailable_intervals_batch(self, start_dt, end_dt, resources=None, domain=None, tz=None):
        """ Return the unavailable intervals between the given datetimes. """
        if not resources:
            resources = self.env['resource.resource']
            resources_list = [resources]
        else:
            resources_list = list(resources)

        resources_work_intervals = self._work_intervals_batch(start_dt, end_dt, resources, domain, tz)
        result = {}
        for resource in resources_list:
            if resource and resource._is_fully_flexible():
                continue
            work_intervals = [(start, stop) for start, stop, meta in resources_work_intervals[resource.id]]
            # start + flatten(intervals) + end
            work_intervals = [start_dt] + list(chain.from_iterable(work_intervals)) + [end_dt]
            # put it back to UTC
            work_intervals = [dt.astimezone(utc) for dt in work_intervals]
            # pick groups of two
            work_intervals = list(zip(work_intervals[0::2], work_intervals[1::2]))
            result[resource.id] = work_intervals
        return result

    # --------------------------------------------------
    # Private Methods / Helpers
    # --------------------------------------------------

    def _check_overlap(self, attendance_ids):
        """ attendance_ids correspond to attendance of a week,
            will check for each day of week that there are no superimpose. """
        result = []
        for attendance in attendance_ids.filtered(lambda att: not att.date_from and not att.date_to):
            # 0.000001 is added to each start hour to avoid to detect two contiguous intervals as superimposing.
            # Indeed Intervals function will join 2 intervals with the start and stop hour corresponding.
            result.append((int(attendance.dayofweek) * 24 + attendance.hour_from + 0.000001, int(attendance.dayofweek) * 24 + attendance.hour_to, attendance))

        if len(Intervals(result)) != len(result):
            raise ValidationError(self.env._("Attendances can't overlap."))

    def _get_attendance_intervals_days_data(self, attendance_intervals):
        """
        helper function to compute duration of `intervals` that have
        'resource.calendar.attendance' records as payload (3rd element in tuple).
        expressed in days and hours.

        resource.calendar.attendance records have durations associated
        with them so this method merely calculates the proportion that is
        covered by the intervals.
        """
        day_hours = defaultdict(float)
        day_days = defaultdict(float)
        for start, stop, meta in attendance_intervals:
            # If the interval covers only a part of the original attendance, we
            # take durations in days proportionally to what is left of the interval.
            interval_hours = (stop - start).total_seconds() / 3600
            day_hours[start.date()] += interval_hours
            if len(self) == 1 and self.flexible_hours:
                day_days[start.date()] += interval_hours / self.hours_per_day if self.hours_per_day else 0
            else:
                day_days[start.date()] += sum(meta.mapped('duration_days')) * interval_hours / sum(meta.mapped('duration_hours'))

        return {
            # Round the number of days to the closest 16th of a day.
            'days': float_round(sum(day_days[day] for day in day_days), precision_rounding=0.001),
            'hours': sum(day_hours.values()),
        }

    def _get_closest_work_time(self, dt, match_end=False, resource=None, search_range=None, compute_leaves=True):
        """Return the closest work interval boundary within the search range.
        Consider only starts of intervals unless `match_end` is True. It will then only consider
        ends of intervals.
        :param dt: reference datetime
        :param match_end: wether to search for the begining of an interval or the end.
        :param search_range: time interval considered. Defaults to the entire day of `dt`
        :rtype: datetime | None
        """
        def interval_dt(interval):
            return interval[1 if match_end else 0]

        tz = resource.tz if resource else self.tz
        if resource is None:
            resource = self.env['resource.resource']

        if not dt.tzinfo or (search_range and not (search_range[0].tzinfo and search_range[1].tzinfo)):
            raise ValueError(self.env._('Provided datetimes needs to be timezoned'))

        dt = dt.astimezone(timezone(tz))

        if not search_range:
            range_start = dt + relativedelta(hour=0, minute=0, second=0)
            range_end = dt + relativedelta(days=1, hour=0, minute=0, second=0)
        else:
            range_start, range_end = search_range

        if not range_start <= dt <= range_end:
            return None
        work_intervals = sorted(
            self._work_intervals_batch(range_start, range_end, resource, compute_leaves=compute_leaves)[resource.id],
            key=lambda i: abs(interval_dt(i) - dt),
        )
        return interval_dt(work_intervals[0]) if work_intervals else None

    def _get_days_per_week(self):
        # If the employee didn't work a full day, it is still counted, i.e. 19h / week (M/T/W(half day)) -> 3 days
        self.ensure_one()
        attendances = self._get_global_attendances()
        if self.two_weeks_calendar:
            number_of_days = len(set(attendances.filtered(lambda cal: cal.week_type == '1').mapped('dayofweek')))
            number_of_days += len(set(attendances.filtered(lambda cal: cal.week_type == '0').mapped('dayofweek')))
        else:
            number_of_days = len(set(attendances.mapped('dayofweek')))
        return number_of_days / 2 if self.two_weeks_calendar else number_of_days

    def _get_hours_per_week(self):
        """ Calculate the average hours worked per week. """
        self.ensure_one()
        hour_count = 0.0
        for attendance in self._get_global_attendances():
            hour_count += attendance.hour_to - attendance.hour_from
        return hour_count / 2 if self.two_weeks_calendar else hour_count

    def _get_hours_per_day(self):
        """ Calculate the average hours worked per workday. """
        hour_per_week = self._get_hours_per_week()
        number_of_days = self._get_days_per_week()
        return hour_per_week / number_of_days if number_of_days else 0

    def _get_global_attendances(self):
        return self.attendance_ids.filtered(lambda attendance:
            attendance.day_period != 'lunch'
            and not attendance.date_from and not attendance.date_to
            and not attendance.resource_id and not attendance.display_type)

    def _get_unusual_days(self, start_dt, end_dt, company_id=False):
        if not self:
            return {}
        self.ensure_one()
        if not start_dt.tzinfo:
            start_dt = start_dt.replace(tzinfo=utc)
        if not end_dt.tzinfo:
            end_dt = end_dt.replace(tzinfo=utc)

        domain = []
        if company_id:
            domain = [('company_id', 'in', (company_id.id, False))]
        if self.flexible_hours:
            works = {d[0].date() for d in self._leave_intervals_batch(start_dt, end_dt, domain=domain)[False]}
            return {fields.Date.to_string(day.date()): (day.date() in works) for day in rrule(DAILY, start_dt, until=end_dt)}
        works = {d[0].date() for d in self._work_intervals_batch(start_dt, end_dt, domain=domain)[False]}
        return {fields.Date.to_string(day.date()): (day.date() not in works) for day in rrule(DAILY, start_dt, until=end_dt)}

    def _get_default_attendance_ids(self, company_id=None):
        """ return a copy of the company's calendar attendance or default 40 hours/week """
        if company_id and (attendances := company_id.resource_calendar_id.attendance_ids):
            return [
                Command.create({
                    'name': attendance.name,
                    'dayofweek': attendance.dayofweek,
                    'week_type': attendance.week_type,
                    'hour_from': attendance.hour_from,
                    'hour_to': attendance.hour_to,
                    'day_period': attendance.day_period,
                    'date_from': attendance.date_from,
                    'date_to': attendance.date_to,
                    'display_type': attendance.display_type,
                })
                for attendance in attendances
            ]
        return [
            Command.create({'name': self.env._('Monday Morning'), 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
            Command.create({'name': self.env._('Monday Lunch'), 'dayofweek': '0', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
            Command.create({'name': self.env._('Monday Afternoon'), 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
            Command.create({'name': self.env._('Tuesday Morning'), 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
            Command.create({'name': self.env._('Tuesday Lunch'), 'dayofweek': '1', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
            Command.create({'name': self.env._('Tuesday Afternoon'), 'dayofweek': '1', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
            Command.create({'name': self.env._('Wednesday Morning'), 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
            Command.create({'name': self.env._('Wednesday Lunch'), 'dayofweek': '2', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
            Command.create({'name': self.env._('Wednesday Afternoon'), 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
            Command.create({'name': self.env._('Thursday Morning'), 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
            Command.create({'name': self.env._('Thursday Lunch'), 'dayofweek': '3', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
            Command.create({'name': self.env._('Thursday Afternoon'), 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
            Command.create({'name': self.env._('Friday Morning'), 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
            Command.create({'name': self.env._('Friday Lunch'), 'dayofweek': '4', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
            Command.create({'name': self.env._('Friday Afternoon'), 'dayofweek': '4', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
        ]

    # --------------------------------------------------
    # External API
    # --------------------------------------------------

    def get_work_hours_count(self, start_dt, end_dt, compute_leaves=True, domain=None):
        """
            `compute_leaves` controls whether or not this method is taking into
            account the global leaves.

            `domain` controls the way leaves are recognized.
            None means default value ('time_type', '=', 'leave')

            Counts the number of work hours between two datetimes.
        """
        self.ensure_one()
        # Set timezone in UTC if no timezone is explicitly given
        if not start_dt.tzinfo:
            start_dt = start_dt.replace(tzinfo=utc)
        if not end_dt.tzinfo:
            end_dt = end_dt.replace(tzinfo=utc)

        if compute_leaves:
            intervals = self._work_intervals_batch(start_dt, end_dt, domain=domain)[False]
        else:
            intervals = self._attendance_intervals_batch(start_dt, end_dt)[False]

        return sum(
            (stop - start).total_seconds() / 3600
            for start, stop, meta in intervals
        )

    def get_work_duration_data(self, from_datetime, to_datetime, compute_leaves=True, domain=None):
        """
            Get the working duration (in days and hours) for a given period, only
            based on the current calendar. This method does not use resource to
            compute it.

            `domain` is used in order to recognise the leaves to take,
            None means default value ('time_type', '=', 'leave')

            Returns a dict {'days': n, 'hours': h} containing the
            quantity of working time expressed as days and as hours.
        """
        # naive datetimes are made explicit in UTC
        from_datetime = localized(from_datetime)
        to_datetime = localized(to_datetime)

        # actual hours per day
        if compute_leaves:
            intervals = self._work_intervals_batch(from_datetime, to_datetime, domain=domain)[False]
        else:
            intervals = self._attendance_intervals_batch(from_datetime, to_datetime, domain=domain)[False]

        return self._get_attendance_intervals_days_data(intervals)

    def plan_hours(self, hours, day_dt, compute_leaves=False, domain=None, resource=None):
        """
        `compute_leaves` controls whether or not this method is taking into
        account the global leaves.

        `domain` controls the way leaves are recognized.
        None means default value ('time_type', '=', 'leave')

        Return datetime after having planned hours
        """
        revert = to_timezone(day_dt.tzinfo)
        day_dt = localized(day_dt)

        if resource is None:
            resource = self.env['resource.resource']

        # which method to use for retrieving intervals
        if compute_leaves:
            get_intervals = partial(self._work_intervals_batch, domain=domain, resources=resource)
            resource_id = resource.id
        else:
            get_intervals = self._attendance_intervals_batch
            resource_id = False

        if hours >= 0:
            delta = timedelta(days=14)
            for n in range(100):
                dt = day_dt + delta * n
                for start, stop, _meta in get_intervals(dt, dt + delta)[resource_id]:
                    interval_hours = (stop - start).total_seconds() / 3600
                    if hours <= interval_hours:
                        return revert(start + timedelta(hours=hours))
                    hours -= interval_hours
            return False
        hours = abs(hours)
        delta = timedelta(days=14)
        for n in range(100):
            dt = day_dt - delta * n
            for start, stop, _meta in reversed(get_intervals(dt - delta, dt)[resource_id]):
                interval_hours = (stop - start).total_seconds() / 3600
                if hours <= interval_hours:
                    return revert(stop - timedelta(hours=hours))
                hours -= interval_hours
        return False

    def plan_days(self, days, day_dt, compute_leaves=False, domain=None):
        """
        `compute_leaves` controls whether or not this method is taking into
        account the global leaves.

        `domain` controls the way leaves are recognized.
        None means default value ('time_type', '=', 'leave')

        Returns the datetime of a days scheduling.
        """
        revert = to_timezone(day_dt.tzinfo)
        day_dt = localized(day_dt)

        # which method to use for retrieving intervals
        if compute_leaves:
            get_intervals = partial(self._work_intervals_batch, domain=domain)
        else:
            get_intervals = self._attendance_intervals_batch

        if days > 0:
            found = set()
            delta = timedelta(days=14)
            for n in range(100):
                dt = day_dt + delta * n
                for start, stop, _meta in get_intervals(dt, dt + delta)[False]:
                    found.add(start.date())
                    if len(found) == days:
                        return revert(stop)
            return False

        if days < 0:
            days = abs(days)
            found = set()
            delta = timedelta(days=14)
            for n in range(100):
                dt = day_dt - delta * n
                for start, _stop, _meta in reversed(get_intervals(dt - delta, dt)[False]):
                    found.add(start.date())
                    if len(found) == days:
                        return revert(start)
            return False

        return revert(day_dt)

    def _works_on_date(self, date):
        self.ensure_one()

        working_days = self._get_working_hours()
        dayofweek = str(date.weekday())
        if self.two_weeks_calendar:
            weektype = str(self.env['resource.calendar.attendance'].get_week_type(date))
            return working_days[weektype][dayofweek]
        return working_days[False][dayofweek]

    @ormcache('self.id')
    def _get_working_hours(self):
        self.ensure_one()

        working_days = defaultdict(lambda: defaultdict(lambda: False))
        for attendance in self.attendance_ids:
            working_days[attendance.week_type][attendance.dayofweek] = True
        return working_days
