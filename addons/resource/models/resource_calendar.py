# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import datetime, time, timedelta, UTC
from itertools import chain
from functools import partial
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta
from dateutil.rrule import DAILY, rrule

from odoo import api, fields, models
from odoo.exceptions import ValidationError, UserError
from odoo.fields import Command, Domain
from odoo.tools import float_compare, ormcache
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
        if 'attendance_ids' in fields and not res.get('attendance_ids'):
            company_id = res.get('company_id', self.env.company.id)
            company = self.env['res.company'].browse(company_id)
            res["attendance_ids"] = self._get_default_attendance_ids(company)
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
        domain=[('resource_id', '=', False)], copy=True,
    )
    hours_per_day = fields.Float("Average Hour per Day", store=True, compute="_compute_hours_per_day", digits=(2, 2), readonly=False,
        help="Average hours per day a resource is supposed to work with this calendar.")
    hours_per_week = fields.Float(
        string="Hours per Week",
        compute="_compute_hours_per_week", store=True, readonly=False, copy=False)
    is_fulltime = fields.Boolean(compute='_compute_work_time_rate', string="Is Full Time")
    work_resources_count = fields.Integer("Work Resources count", compute='_compute_work_resources_count')
    work_time_rate = fields.Float(string='Work Time Rate', compute='_compute_work_time_rate', search='_search_work_time_rate',
        help='Work time rate versus full time working schedule, should be between 0 and 100 %.')

    # --------------------------------------------------
    # Constrains
    # --------------------------------------------------

    @api.constrains('attendance_ids')
    def _check_attendance_ids(self):
        for res_calendar in self:
            # Avoid superimpose in attendance
            attendance_ids = res_calendar.attendance_ids.filtered(
                lambda attendance: not attendance.display_type)
            res_calendar._check_overlap(attendance_ids)

    # --------------------------------------------------
    # Compute Methods
    # --------------------------------------------------

    @api.depends('hours_per_week', 'company_id.resource_calendar_id.hours_per_week')
    def _compute_full_time_required_hours(self):
        for calendar in self.filtered("company_id"):
            calendar.full_time_required_hours = calendar.company_id.resource_calendar_id.hours_per_week

    @api.depends('company_id')
    def _compute_attendance_ids(self):
        for calendar in self.filtered(lambda c: not c._origin or (c._origin.company_id != c.company_id and c.company_id)):
            company_calendar = calendar.company_id.resource_calendar_id
            calendar.update({
                'attendance_ids': [(5, 0, 0)] + [
                    (0, 0, attendance._copy_attendance_vals()) for attendance in company_calendar.attendance_ids],
            })

    @api.depends('company_id')
    def _compute_global_leave_ids(self):
        for calendar in self.filtered(lambda c: not c._origin or c._origin.company_id != c.company_id):
            calendar.update({
                'global_leave_ids': [(5, 0, 0)] + [
                    (0, 0, leave._copy_leave_vals()) for leave in calendar.company_id.resource_calendar_id.global_leave_ids],
            })

    @api.depends('attendance_ids', 'attendance_ids.hour_from', 'attendance_ids.hour_to')
    def _compute_hours_per_day(self):
        """ Compute the average hours per day.
            Cannot directly depend on hours_per_week because of rounding issues. """
        for calendar in self:
            calendar.hours_per_day = float_round(calendar._get_hours_per_day(), precision_digits=2)

    @api.depends('attendance_ids', 'attendance_ids.hour_from', 'attendance_ids.hour_to')
    def _compute_hours_per_week(self):
        """ Compute the average hours per week """
        for calendar in self:
            calendar.hours_per_week = float_round(calendar._get_hours_per_week(), precision_digits=2)

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

        domain = Domain.AND([
            Domain(domain or Domain.TRUE),
            Domain('calendar_id', '=', self.id),
            Domain('display_type', '=', False),
        ])

        attendances = self.env['resource.calendar.attendance'].search(domain)
        duration_based_attendances = attendances.filtered('duration_based')
        all_duration_based_attendances = attendances.calendar_id.attendance_ids.filtered('duration_based')
        # Resource specific attendances
        # Calendar attendances per day of the week
        attendances_per_day = [self.env['resource.calendar.attendance']] * 7
        weekdays = set()
        for attendance in attendances:
            weekday = int(attendance.dayofweek)
            weekdays.add(weekday)
            attendances_per_day[weekday] |= attendance

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
        # Generate once with utc as timezone
        days = rrule(DAILY, start.date(), until=end.date(), byweekday=weekdays)
        base_result = []
        for day in days:
            attendances = attendances_per_day[day.weekday()]

            # If all attendance lines are duration based, compute correct intervals
            if all(att.duration_based for att in attendances):
                day_all_duration_based_attendances = all_duration_based_attendances.filtered(lambda att: int(att.dayofweek) == day.weekday())
                day_duration_based_attendances = duration_based_attendances.filtered(lambda att: int(att.dayofweek) == day.weekday())
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
                    base_result.append((day_from, day_to, attendance))
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
            domain = [('time_type', '=', 'leave')]
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

    # --------------------------------------------------
    # Private Methods / Helpers
    # --------------------------------------------------

    def _check_overlap(self, attendance_ids):
        """ attendance_ids correspond to attendance of a week,
            will check for each day of week that there are no superimpose. """
        result = []
        hours_based_weekdays = set()
        duration_based_weekdays = set()
        for attendance in attendance_ids:
            if attendance.duration_based and attendance.dayofweek in hours_based_weekdays or not attendance.duration_based and attendance.dayofweek in duration_based_weekdays:
                raise ValidationError(self.env._("You cannot define hours and duration based attendances for the same day."))
            if attendance.duration_based:
                duration_based_weekdays.add(attendance.dayofweek)
            else:
                hours_based_weekdays.add(attendance.dayofweek)
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

    def _get_days_per_week(self):
        # If the employee didn't work a full day, it is still counted, i.e. 19h / week (M/T/W(half day)) -> 3 days
        self.ensure_one()
        attendances = self._get_global_attendances()
        return len(set(attendances.mapped('dayofweek')))

    def _get_hours_per_week(self):
        """ Calculate the average hours worked per week. """
        self.ensure_one()
        hour_count = 0.0
        for attendance in self._get_global_attendances():
            if attendance.duration_based:
                hour_count += attendance.duration_hours
            else:
                hour_count += attendance.hour_to - attendance.hour_from
        return hour_count

    def _get_hours_per_day(self):
        """ Calculate the average hours worked per workday. """
        hour_per_week = self._get_hours_per_week()
        number_of_days = self._get_days_per_week()
        return hour_per_week / number_of_days if number_of_days else 0

    def _get_global_attendances(self):
        return self.attendance_ids.filtered(lambda attendance: not attendance.display_type)

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
                Command.create({
                    'dayofweek': attendance.dayofweek,
                    'duration_hours': attendance.duration_hours,
                    'hour_from': attendance.hour_from,
                    'hour_to': attendance.hour_to,
                    'display_type': attendance.display_type,
                })
                for attendance in attendances
            ]
        return [
            Command.create({'dayofweek': '0', 'duration_hours': 8, 'hour_from': 0, 'hour_to': 0}),
            Command.create({'dayofweek': '1', 'duration_hours': 8, 'hour_from': 0, 'hour_to': 0}),
            Command.create({'dayofweek': '2', 'duration_hours': 8, 'hour_from': 0, 'hour_to': 0}),
            Command.create({'dayofweek': '3', 'duration_hours': 8, 'hour_from': 0, 'hour_to': 0}),
            Command.create({'dayofweek': '4', 'duration_hours': 8, 'hour_from': 0, 'hour_to': 0}),
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
        None means default value ('time_type', '=', 'leave')

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
        self.ensure_one()

        working_days = self._get_working_hours()
        dayofweek = str(date.weekday())
        return working_days[dayofweek]

    def _is_duration_based_on_date(self, date):
        self.ensure_one()
        return any(att.duration_based for att in self.attendance_ids.filtered(lambda a: int(a.dayofweek) == date.weekday()))

    def _get_duration_based_work_hours_on_date(self, date):
        return sum(self.attendance_ids.filtered(lambda a: int(a.dayofweek) == date.weekday()).mapped('duration_hours'))

    @ormcache('self.id')
    def _get_working_hours(self):
        self.ensure_one()

        working_days = defaultdict(lambda: False)
        for attendance in self.attendance_ids:
            working_days[attendance.dayofweek] = True
        return working_days
