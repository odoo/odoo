# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import datetime, time, timedelta, UTC
from itertools import chain
from functools import partial
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta
from dateutil.rrule import DAILY, rrule

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command, Domain
from odoo.tools import float_compare
from odoo.tools.date_utils import float_to_time, localized, to_timezone
from odoo.tools.float_utils import float_round
from odoo.tools.intervals import Intervals


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
        if 'full_time_required_hours' in fields and not res.get('full_time_required_hours'):
            company_id = res.get('company_id', self.env.company.id)
            company = self.env['res.company'].browse(company_id)
            res['full_time_required_hours'] = company.resource_calendar_id.full_time_required_hours
        return res

    name = fields.Char(required=True)
    active = fields.Boolean("Active", default=True,
                            help="If the active field is set to false, it will allow you to hide the Working Time without removing it.")
    attendance_ids = fields.One2many(
        'resource.calendar.attendance', 'calendar_id', 'Working Time', precompute=True,
        compute='_compute_attendance_ids', store=True, readonly=False, copy=True)
    attendance_ids_1st_week = fields.One2many('resource.calendar.attendance', 'calendar_id', 'Working Time 1st Week',
        compute="_compute_two_weeks_attendance", inverse="_inverse_two_weeks_calendar")
    attendance_ids_2nd_week = fields.One2many('resource.calendar.attendance', 'calendar_id', 'Working Time 2nd Week',
        compute="_compute_two_weeks_attendance", inverse="_inverse_two_weeks_calendar")
    company_id = fields.Many2one(
        'res.company', 'Company', domain=lambda self: [('id', 'in', self.env.companies.ids)],
        default=lambda self: self.env.company, index='btree_not_null')
    country_id = fields.Many2one(related='company_id.country_id')
    country_code = fields.Char(related='country_id.code', depends=['country_id'])
    leave_ids = fields.One2many(
        'resource.calendar.leaves', 'calendar_id', 'Time Off')
    full_time_required_hours = fields.Float(
        string="Full Time Equivalent",
        compute="_compute_full_time_required_hours", store=True, readonly=False,
        help="Number of hours to work on the company schedule to be considered as fulltime.")
    global_leave_ids = fields.One2many(
        'resource.calendar.leaves', 'calendar_id', 'Global Time Off',
        compute='_compute_global_leave_ids', store=True, readonly=False,
        domain=[('resource_id', '=', False)],
    )
    days_per_week = fields.Float("Days per Week", compute="_compute_days_per_week", store=True)
    hours_per_day = fields.Float("Average Hour per Day", store=True, compute="_compute_hours_per_day", digits=(2, 2), readonly=False,
        help="Average hours per day a resource is supposed to work with this calendar.")
    hours_per_week = fields.Float(
        string="Hours per Week",
        compute="_compute_hours_per_week", store=True, readonly=False, copy=False)
    is_fulltime = fields.Boolean(compute='_compute_work_time_rate', string="Is Full Time")
    two_weeks_calendar = fields.Boolean(string="Calendar in 2 weeks mode")
    two_weeks_explanation = fields.Char('Explanation', compute="_compute_two_weeks_explanation")
    work_resources_count = fields.Integer("Work Resources count", compute='_compute_work_resources_count')
    work_time_rate = fields.Float(string='Work Time Rate', compute='_compute_work_time_rate', search='_search_work_time_rate',
        help='Work time rate versus full time working schedule, should be between 0 and 100 %.')
    schedule_type = fields.Selection([
        ('fixed', 'Fixed'),
        ('variable', 'Variable')],
        string='Calendar Type', default='fixed', required=True)

    @api.constrains('attendance_ids', 'schedule_type')
    def _check_attendance_ids(self):
        if self.attendance_ids.filtered(lambda a: bool(a.date) if a.calendar_id.schedule_type == "fixed" else not a.date):
            raise ValidationError(self.env._("You cannot have attendances based on weekday and date in the same calendar"))

    # --------------------------------------------------
    # Compute Methods
    # --------------------------------------------------

    def write(self, vals):
        vals['attendance_ids'] = [
            *vals.get('attendance_ids', []),
            *[Command.delete(a.id) for a in self._get_attendances_to_unlink(vals.get("schedule_type"))]
        ]
        return super().write(vals)

    @api.autovacuum
    def _auto_attendance_clean(self):
        self._get_attendances_to_unlink().unlink()

    def _get_attendances_to_unlink(self, next_schedule_type=None):
        return self.attendance_ids.filtered(lambda a: bool(a.date) if (next_schedule_type or a.calendar_id.schedule_type) == "fixed" else not a.date)

    @api.depends('hours_per_week', 'company_id.resource_calendar_id.hours_per_week')
    def _compute_full_time_required_hours(self):
        for calendar in self.filtered("company_id"):
            calendar.full_time_required_hours = calendar.company_id.resource_calendar_id.hours_per_week

    @api.depends('company_id', 'schedule_type')
    def _compute_attendance_ids(self):
        for calendar in self:
            if calendar.schedule_type == "variable":
                calendar.attendance_ids = calendar._origin.attendance_ids
            elif not (calendar.attendance_ids.filtered(lambda a: not a.date)
                      or calendar._origin.company_id == calendar.company_id
                      and calendar._origin.schedule_type == calendar.schedule_type):
                calendar.attendance_ids = calendar._get_default_attendance_ids(calendar.company_id)

    @api.depends('company_id')
    def _compute_global_leave_ids(self):
        for calendar in self.filtered(lambda c: not c._origin or c._origin.company_id != c.company_id):
            calendar.update({
                'global_leave_ids': [(5, 0, 0)] + [
                    (0, 0, leave._copy_leave_vals()) for leave in calendar.company_id.resource_calendar_id.global_leave_ids],
            })

    @api.depends('attendance_ids.date', 'attendance_ids.dayofweek', 'schedule_type')
    def _compute_days_per_week(self):
        for calendar in self:
            attendances = calendar._get_global_attendances()
            days = len(set(attendances.mapped('date' if calendar.schedule_type == 'variable' else 'dayofweek')))
            weeks = len({(att.date.toordinal() - 1) // 7 for att in attendances}) if calendar.schedule_type == 'variable' else 1
            calendar.days_per_week = float_round(days / weeks if weeks else 0.0, precision_digits=2)

    @api.depends('attendance_ids.date', 'attendance_ids.dayofweek', 'attendance_ids.duration_hours', 'schedule_type')
    def _compute_hours_per_day(self):
        """ Compute the average hours per day.
            Cannot directly depend on hours_per_week because of rounding issues. """
        for calendar in self:
            attendances = calendar._get_global_attendances()
            hours = sum(attendances.mapped('duration_hours'))
            days = len(set(attendances.mapped('date' if calendar.schedule_type == 'variable' else 'dayofweek')))
            calendar.hours_per_day = float_round((hours / days) if days else 0.0, precision_digits=2)

    @api.depends('attendance_ids.date', 'attendance_ids.duration_hours', 'schedule_type')
    def _compute_hours_per_week(self):
        """ Compute the average hours per week """
        for calendar in self:
            attendances = calendar._get_global_attendances()
            hours = sum(attendances.mapped('duration_hours'))
            weeks = len({(att.date.toordinal() - 1) // 7 for att in attendances}) if calendar.schedule_type == 'variable' else 1
            calendar.hours_per_week = float_round(hours / weeks if weeks else 0.0, precision_digits=2)

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

        calendar_ids = self.env['resource.calendar'].search([])
        if operator == 'in':
            calender = calendar_ids.filtered(lambda m: m.work_time_rate in value)
        elif operator == 'not in':
            calender = calendar_ids.filtered(lambda m: m.work_time_rate not in value)
        elif operator == '<':
            calender = calendar_ids.filtered(lambda m: m.work_time_rate < value)
        elif operator == '>':
            calender = calendar_ids.filtered(lambda m: m.work_time_rate > value)
        return [('id', 'in', calender.ids)]

    def is_calendar_referenced(self):
        self.ensure_one()
        relations = self.env['ir.model.fields'].search([
            ('ttype', '=', 'many2one'),
            ('store', '=', True),
            ('model', 'not ilike', 'resource.calendar'),
            ('model_id.abstract', '=', False),
            ('relation', '=', "resource.calendar")
        ])
        for field in relations:
            count = self.env[field.model].sudo().search_count([(field.name, '=', self.id)], limit=1)
            if count > 0:
                return True
        return False

    # --------------------------------------------------
    # Overrides
    # --------------------------------------------------

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        return [dict(vals, name=self.env._("%s (copy)", calendar.name)) for calendar, vals in zip(self, vals_list)]

    # --------------------------------------------------
    # Computation API
    # --------------------------------------------------

    def _attendance_intervals_batch(self, start_dt, end_dt, resources_per_tz=None, domain=None):
        assert start_dt.tzinfo and end_dt.tzinfo
        if self:
            self.ensure_one()
        elif not resources_per_tz.values():
            raise UserError(self.env._("You cannot compute the intervals without a calendar on no resource."))

        if not resources_per_tz:
            resources_per_tz = {start_dt.tzinfo: self.env['resource.resource']}

        start = start_dt.astimezone(UTC)
        end = end_dt.astimezone(UTC)
        bounds_per_tz = {
            tz: (start_dt.astimezone(tz), end_dt.astimezone(tz))
            for tz in resources_per_tz
        }
        # Use the outer bounds from the requested timezones
        for low, high in bounds_per_tz.values():
            start = min(start, low.replace(tzinfo=UTC))
            end = max(end, high.replace(tzinfo=UTC))

        domain = Domain.AND([
            Domain('calendar_id', '=', self.id),
            Domain('display_type', '=', False),
            Domain(domain or Domain.TRUE),
        ])

        fetched_attendances = self.attendance_ids.with_prefetch()
        duration_based_attendances = fetched_attendances.filtered_domain([('duration_based', '=', True), domain])
        all_duration_based_attendances = fetched_attendances.filtered('duration_based')
        attendances_per_day = (self._get_working_hours(start.date(), end.date(), domain=domain) if self
                                else defaultdict(lambda: self.env['resource.calendar.attendance']))

        # Generate once with utc as timezone
        base_result = []
        for day, attendances in attendances_per_day.items():
            # If all attendance lines are duration based, compute correct intervals
            if all(att.duration_based for att in attendances):
                day_all_duration_based_attendances = all_duration_based_attendances._get_attendances_on_date(day)
                day_duration_based_attendances = duration_based_attendances._get_attendances_on_date(day)
                total_hours = sum(day_all_duration_based_attendances.mapped('duration_hours'))
                hours_per_attendance = {}
                current_hour_from = 12 - total_hours / 2
                for att in day_all_duration_based_attendances:
                    hours_per_attendance[att] = (current_hour_from, current_hour_from + att.duration_hours)
                    current_hour_from += att.duration_hours
                for att in day_duration_based_attendances:
                    hour_from, hour_to = hours_per_attendance[att]
                    day_from = datetime.combine(day, float_to_time(hour_from))
                    day_to = datetime.combine(day, float_to_time(hour_to))
                    base_result.append((day_from, day_to, att))
                    base_result.append((day_from, day_to, att))
                continue

            for attendance in attendances:
                if attendance.duration_based:
                    day_from = datetime.combine(day, float_to_time(12 - attendance.duration_hours / 2))
                    day_to = datetime.combine(day, float_to_time(12 + attendance.duration_hours / 2))
                    base_result.append((day_from, day_to, attendance))
                else:
                    day_from = datetime.combine(day, float_to_time(attendance.hour_from))
                    day_to = datetime.combine(day, float_to_time(attendance.hour_to))
                    base_result.append((day_from, day_to, attendance))

        # Copy the result localized once per necessary timezone
        # Strictly speaking comparing start_dt < time or start_dt.astimezone(tz) < time
        # should always yield the same result. however while working with dates it is easier
        # if all dates have the same format
        result_per_tz = {
            tz: [(max(bounds_per_tz[tz][0], val[0].replace(tzinfo=tz)),
                min(bounds_per_tz[tz][1], val[1].replace(tzinfo=tz)),
                val[2])
                    for val in base_result]
            for tz in resources_per_tz
        }
        result_per_resource_id = dict()
        for tz, tz_resources in resources_per_tz.items():
            res = result_per_tz[tz]
            calendar_data_by_resource = tz_resources._get_calendar_data_at(start_dt, tz)

            res_intervals = Intervals(res, keep_distinct=True)
            start_datetime = start_dt.astimezone(tz)
            end_datetime = end_dt.astimezone(tz)

            for resource in chain(tz_resources, (self.env['resource.resource'],) if self else ()):
                calendar_data = calendar_data_by_resource.get(resource, {})
                calendar = calendar_data.get('resource_calendar_id')
                hours_per_week = calendar_data.get('hours_per_week')
                hours_per_day = calendar_data.get('hours_per_day')
                is_fully_flexible = not calendar and not hours_per_week and not hours_per_day
                is_flexible = not calendar and (hours_per_week or hours_per_day)
                if resource and is_fully_flexible:
                    # If the resource is fully flexible, return the whole period from start_dt to end_dt with a dummy attendance
                    hours = (end_dt - start_dt).total_seconds() / 3600
                    dummy_attendance = self.env['resource.calendar.attendance'].new({
                        'duration_hours': hours,
                    })
                    result_per_resource_id[resource.id] = Intervals([(start_datetime, end_datetime, dummy_attendance)], keep_distinct=True)
                elif resource and is_flexible:
                    # For flexible Calendars, we create intervals to fill in the weekly intervals with the average daily hours
                    # until the full time required hours are met. This gives us the most correct approximation when looking at a daily
                    # and weekly range for time offs and overtime calculations and work entry generation
                    start_date = start_datetime.date()
                    end_datetime_adjusted = end_datetime - relativedelta(seconds=1)
                    end_date = end_datetime_adjusted.date()

                    full_time_required_hours = hours_per_week
                    max_hours_per_day = hours_per_day

                    intervals = []
                    current_start_day = start_date

                    while current_start_day <= end_date:
                        current_end_of_week = current_start_day + timedelta(days=6)

                        week_start = max(current_start_day, start_date)
                        week_end = min(current_end_of_week, end_date)

                        if current_start_day < start_date:
                            prior_days = (start_date - current_start_day).days
                            prior_hours = min(full_time_required_hours, max_hours_per_day * prior_days)
                        else:
                            prior_hours = 0

                        remaining_hours = max(0, full_time_required_hours - prior_hours)
                        remaining_hours = min(remaining_hours, (end_dt - start_dt).total_seconds() / 3600)

                        current_day = week_start
                        while current_day <= week_end:
                            if remaining_hours > 0:
                                day_start = datetime.combine(current_day, time.min, tzinfo=tz)
                                day_end = datetime.combine(current_day, time.max, tzinfo=tz)
                                day_period_start = max(start_datetime, day_start)
                                day_period_end = min(end_datetime, day_end)
                                allocate_hours = min(max_hours_per_day, remaining_hours, (day_period_end - day_period_start).total_seconds() / 3600)
                                remaining_hours -= allocate_hours

                                # Create interval centered at 12:00 PM
                                midpoint = datetime.combine(current_day, time(12, 0), tzinfo=tz)
                                start_time = midpoint - timedelta(hours=allocate_hours / 2)
                                end_time = midpoint + timedelta(hours=allocate_hours / 2)

                                if start_time < day_period_start:
                                    start_time = day_period_start
                                    end_time = start_time + timedelta(hours=allocate_hours)
                                elif end_time > day_period_end:
                                    end_time = day_period_end
                                    start_time = end_time - timedelta(hours=allocate_hours)

                                dummy_attendance = self.env['resource.calendar.attendance'].new({
                                    'duration_hours': allocate_hours,
                                })

                                intervals.append((start_time, end_time, dummy_attendance))

                            current_day += timedelta(days=1)

                        current_start_day += timedelta(days=7)

                    result_per_resource_id[resource.id] = Intervals(intervals, keep_distinct=True)
                else:
                    result_per_resource_id[resource.id] = res_intervals
        return result_per_resource_id

    def _handle_flexible_leave_interval(self, dt0, dt1, leave):
        """Hook method to handle flexible leave intervals. Can be overridden in other modules."""
        tz = dt0.tzinfo  # Get the timezone information from dt0
        dt0 = datetime.combine(dt0.date(), time.min, tzinfo=tz)
        dt1 = datetime.combine(dt1.date(), time.max, tzinfo=tz)
        return dt0, dt1

    def _leave_intervals(self, start_dt, end_dt, resource=None, domain=None, tz=None):
        if resource is None:
            resource = self.env['resource.resource']
        resources_per_tz = resource._get_resources_per_tz()
        return self._leave_intervals_batch(start_dt, end_dt, resources_per_tz=resources_per_tz, domain=domain)[resource.id]

    def _leave_intervals_batch(self, start_dt, end_dt, resources_per_tz=None, domain=None):
        """ Return the leave intervals in the given datetime range.
            The returned intervals are expressed in specified tz or in the calendar's timezone.
        """
        assert start_dt.tzinfo and end_dt.tzinfo

        if domain is None:
            domain = [('count_as', '=', 'absence')]
        if self:
            domain = domain + [('calendar_id', 'in', [False] + self.ids)]

        all_resources = set()
        if not resources_per_tz or self:
            all_resources.add(self.env['resource.resource'])
            resources_per_tz = resources_per_tz or {start_dt.tzinfo: self.env['resource.resource']}
        if resources_per_tz:
            for _, resources in resources_per_tz.items():
                all_resources |= set(resources)

        # for the computation, express all datetimes in UTC
        # Public leave don't have a resource_id
        domain = domain + [
            ('resource_id', 'in', [False] + [r.id for r in all_resources]),
            ('date_from', '<=', end_dt.astimezone(UTC).replace(tzinfo=None)),
            ('date_to', '>=', start_dt.astimezone(UTC).replace(tzinfo=None)),
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
            for tz, resources in resources_per_tz.items():
                for resource in chain(resources, (self.env['resource.resource'],) if self else ()):
                    if leave_resource.id not in [False, resource.id] or (not leave_resource and resource and resource.company_id != leave_company):
                        continue
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

        return {r.id: Intervals(result[r.id]) for r in all_resources}

    def _work_intervals_batch(self, start_dt, end_dt, resources_per_tz=None, domain=None, compute_leaves=True):
        """ Return the effective work intervals between the given datetimes. """
        all_resources = set()
        if not resources_per_tz or self:
            all_resources.add(self.env['resource.resource'])
        if resources_per_tz:
            for _, resources in resources_per_tz.items():
                all_resources |= set(resources)

        attendance_intervals = self._attendance_intervals_batch(start_dt, end_dt, resources_per_tz)
        if compute_leaves:
            leave_intervals = self._leave_intervals_batch(start_dt, end_dt, resources_per_tz, domain)
            return {
                r.id: (attendance_intervals[r.id] - leave_intervals[r.id]) for r in all_resources
            }
        return {
            r.id: attendance_intervals[r.id] for r in all_resources
        }

    def _unavailable_intervals(self, start_dt, end_dt, resource=None, domain=None, tz=None):
        if resource is None:
            resource = self.env['resource.resource']
        resources_per_tz = resource._get_resources_per_tz()
        return self._unavailable_intervals_batch(
            start_dt, end_dt, resources_per_tz=resources_per_tz, domain=domain,
        )[resource.id]

    def _unavailable_intervals_batch(self, start_dt, end_dt, resources_per_tz=None, domain=None):
        """ Return the unavailable intervals between the given datetimes. """
        all_resources = set()
        if not resources_per_tz or self:
            all_resources.add(self.env['resource.resource'])
        if resources_per_tz:
            for _, resources in resources_per_tz.items():
                all_resources |= set(resources)
        resources_work_intervals = self._work_intervals_batch(start_dt, end_dt, resources_per_tz, domain)
        result = {}
        for resource in all_resources:
            if resource and resource._is_fully_flexible():
                continue
            work_intervals = resources_work_intervals[resource.id]
            utc_work_intervals = []
            for (start, stop, meta) in work_intervals:
                utc_work_intervals.append((start.astimezone(UTC), stop.astimezone(UTC), meta))

            utc_work_intervals = Intervals(utc_work_intervals)
            full_interval_UTC = Intervals([(
                start_dt.astimezone(UTC),
                end_dt.astimezone(UTC),
                self.env['resource.calendar'],
            )])

            result[resource.id] = full_interval_UTC - utc_work_intervals
        return result

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
        for start, stop, _ in attendance_intervals:
            # If the interval covers only a part of the original attendance, we
            # take durations in days proportionally to what is left of the interval.
            interval_hours = (stop - start).total_seconds() / 3600
            day_hours[start.date()] += interval_hours

        for day, hours in day_hours.items():
            if len(self) == 1 and self._is_duration_based_on_date(day):
                hours_per_day = self._get_duration_based_work_hours_on_date(day)
                day_days[start.date()] += hours / hours_per_day if hours_per_day else 0
            else:
                day_days[day] = 0.5 if hours <= self.hours_per_day * 3 / 4 else 1

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

        tz = resource.tz if resource else 'UTC'
        if resource is None:
            resource = self.env['resource.resource']

        if not dt.tzinfo or (search_range and not (search_range[0].tzinfo and search_range[1].tzinfo)):
            raise ValueError(self.env._('Provided datetimes needs to be timezoned'))

        dt = dt.astimezone(ZoneInfo(tz))

        if not search_range:
            range_start = dt + relativedelta(hour=0, minute=0, second=0)
            range_end = dt + relativedelta(days=1, hour=0, minute=0, second=0)
        else:
            range_start, range_end = search_range

        if not range_start <= dt <= range_end:
            return None
        resources_per_tz = resource._get_resources_per_tz()
        work_intervals = sorted(
            self._work_intervals_batch(range_start, range_end, resources_per_tz, compute_leaves=compute_leaves)[resource.id],
            key=lambda i: abs(interval_dt(i) - dt),
        )
        return interval_dt(work_intervals[0]) if work_intervals else None

    def _get_global_attendances(self):
        return self.attendance_ids.filtered(lambda attendance: attendance.date if attendance.calendar_id.schedule_type == 'variable' else not attendance.date)

    def _get_unusual_days(self, start_dt, end_dt, company_id=False, resource=None):
        if self:
            self.ensure_one()
        if not start_dt.tzinfo:
            start_dt = start_dt.replace(tzinfo=UTC)
        if not end_dt.tzinfo:
            end_dt = end_dt.replace(tzinfo=UTC)

        domain = []
        if company_id:
            domain = [('company_id', 'in', (company_id.id, False))]
        if resource and resource._is_flexible():
            leave_intervals = self._leave_intervals_batch(start_dt, end_dt, domain=domain, resources_per_tz=resource._get_resources_per_tz())[resource.id]
            works = set()
            for start_int, end_int, _ in leave_intervals:
                works.update(start_int.date() + timedelta(days=i) for i in range((end_int.date() - start_int.date()).days + 1))
            return {fields.Date.to_string(day.date()): (day.date() in works) for day in rrule(DAILY, start_dt, until=end_dt)}
        works = {d[0].date() for d in self._work_intervals_batch(start_dt, end_dt, domain=domain)[False]}
        return {fields.Date.to_string(day.date()): (day.date() not in works) for day in rrule(DAILY, start_dt, until=end_dt)}

    def _get_default_attendance_ids(self, company_id=None):
        """ return a copy of the company's calendar attendance or default 40 hours/week """
        if company_id and (attendances := company_id.resource_calendar_id.attendance_ids):
            return [
                Command.create(attendance._copy_attendance_vals())
                for attendance in attendances
            ]
        return [
            Command.create({'dayofweek': '0', 'duration_hours': 8, 'hour_from': 0, 'hour_to': 0}),
            Command.create({'dayofweek': '1', 'duration_hours': 8, 'hour_from': 0, 'hour_to': 0}),
            Command.create({'dayofweek': '2', 'duration_hours': 8, 'hour_from': 0, 'hour_to': 0}),
            Command.create({'dayofweek': '3', 'duration_hours': 8, 'hour_from': 0, 'hour_to': 0}),
            Command.create({'dayofweek': '4', 'duration_hours': 8, 'hour_from': 0, 'hour_to': 0}),
        ]

    def _get_two_weeks_attendance(self):
        final_attendances = []
        for idx, att in enumerate(self.attendance_ids):
            final_attendances.append(Command.create(dict(att._copy_attendance_vals(), week_type='0', sequence=idx + 1)))
            final_attendances.append(Command.create(dict(att._copy_attendance_vals(), week_type='1', sequence=idx + 26)))
        return final_attendances

    # --------------------------------------------------
    # External API
    # --------------------------------------------------

    def get_attendances(self, target_date):
        if isinstance(target_date, datetime):
            target_date = target_date.date()
        self.ensure_one()
        weektype = False
        if self.two_weeks_calendar:
            weektype = str(self.env['resource.calendar.attendance'].get_week_type(target_date))
        return self.attendance_ids.filtered(lambda a: a.week_type == weektype and a.dayofweek == str(target_date.weekday()))

    def get_work_hours_count(self, start_dt, end_dt, compute_leaves=True, domain=None):
        """
            `compute_leaves` controls whether or not this method is taking into
            account the global leaves.

            `domain` controls the way leaves are recognized.
            None means default value ('count_as', '=', 'absence')

            Counts the number of work hours between two datetimes.
        """
        self.ensure_one()
        # Set timezone in company tz if no timezone is explicitly given
        if not start_dt.tzinfo:
            start_dt = start_dt.astimezone(ZoneInfo(self.env.company.tz))
        if not end_dt.tzinfo:
            end_dt = end_dt.astimezone(ZoneInfo(self.env.company.tz))

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
            None means default value ('count_as', '=', 'absence')

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
        None means default value ('count_as', '=', 'absence')

        Return datetime after having planned hours
        """
        revert = to_timezone(day_dt.tzinfo)
        day_dt = day_dt.astimezone(ZoneInfo(resource.tz if resource else self.env.company.tz))

        if resource is None:
            resource = self.env['resource.resource']

        # which method to use for retrieving intervals
        if compute_leaves:
            resources_per_tz = resource._get_resources_per_tz()
            get_intervals = partial(self._work_intervals_batch, domain=domain, resources_per_tz=resources_per_tz)
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
        None means default value ('count_as', '=', 'absence')

        Returns the datetime of a days scheduling.
        """
        revert = to_timezone(day_dt.tzinfo)
        day_dt = day_dt.astimezone(ZoneInfo(self.env.company.tz))

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
        return bool(self._get_global_attendances()._get_attendances_on_date(date))

    def _is_duration_based_on_date(self, date):
        self.ensure_one()
        return any(self.attendance_ids._get_attendances_on_date(date).mapped('duration_based'))

    def _get_duration_based_work_hours_on_date(self, date):
        return sum(self.attendance_ids._get_attendances_on_date(date).mapped('duration_hours'))

    def _get_working_hours(self, date_from, date_to, domain=None):
        self.ensure_one()
        result = defaultdict(lambda: self.env['resource.calendar.attendance'])

        attendances = self.attendance_ids.filtered_domain(domain) if domain else self._get_global_attendances()
        if not attendances:
            return result
        attendances = attendances.with_prefetch()

        if self.schedule_type == 'variable':
            result.update(attendances.filtered(lambda att: att.date and date_from <= att.date <= date_to).grouped('date'))
        else:
            grouped_attendances = attendances.grouped('dayofweek')
            result.update({
                day.date(): grouped_attendances[str(day.weekday())]
                for day in rrule(DAILY, date_from, until=date_to, byweekday=set(attendances.mapped(lambda att: int(att.dayofweek))))
            })
        return result

    def copy_from(self, date_from, date_to, force=False):
        self.ensure_one()
        date_from = fields.Date.from_string(date_from)
        date_to = fields.Date.from_string(date_to)
        assert self.schedule_type == 'variable'
        week_start = int(self.env["res.lang"]._lang_get(self.env.user.lang).week_start) - 1

        source_start = date_from - timedelta(days=(date_from.weekday() - week_start) % 7)
        target_start = date_to - timedelta(days=(date_to.weekday() - week_start) % 7)
        source_end = source_start + timedelta(days=6)
        target_end = target_start + timedelta(days=6)

        source_attendances = self.attendance_ids.filtered(lambda att: att.date and source_start <= att.date <= source_end)
        target_attendances = self.attendance_ids.filtered(lambda att: att.date and target_start <= att.date <= target_end)
        if target_attendances and not force:
            return False
        target_attendances.unlink()

        vals_list = []
        for source_date, attendances in source_attendances.grouped('date').items():
            target_date = source_date + timedelta(days=(target_start - source_start).days)
            for att in attendances:
                vals_list.append({
                    **att._copy_attendance_vals(),
                    'calendar_id': self.id,
                    'date': target_date,
                    'dayofweek': str(target_date.weekday()),
                })

        return self.env['resource.calendar.attendance'].create(vals_list)
