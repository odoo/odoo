# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import date, datetime, time, timedelta, UTC
from itertools import chain
from functools import partial
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta
from dateutil.rrule import DAILY, rrule

from odoo import api, fields, models
from odoo.exceptions import UserError
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
    days_per_week = fields.Float("Days per Week", compute="_compute_days_per_week", store=True, digits=(10, 5), readonly=False)
    hours_per_day = fields.Float("Average Hour per Day", store=True, compute="_compute_hours_per_day", digits=(10, 5), readonly=False,
        help="Average hours per day a resource is supposed to work with this calendar.")
    hours_per_week = fields.Float(
        string="Hours per Week",
        compute="_compute_hours_per_week", store=True, digits=(10, 5), readonly=False, copy=False)
    is_fulltime = fields.Boolean(compute='_compute_is_fulltime', string="Is Full Time")
    work_resources_count = fields.Integer("Work Resources count", compute='_compute_work_resources_count')
    work_time_rate = fields.Float(string='Work Time Rate', compute='_compute_work_time_rate', store=True,
        help='Work time rate versus full time working schedule, should be between 0 and 100 %.')
    calendar_type = fields.Selection([
        ('fixed', 'Fixed'),
        ('variable', 'Variable')],
        string='Calendar Type', default='fixed', required=True)

    def _get_attendances_to_unlink(self, next_calendar_type=None):
        """ To retrieve attendances with date, to unlink when the calendar will be/is fixed
            Or attendance without date, to unlink when the calendar will be/is variable"""
        return self.attendance_ids.filtered(lambda a: a.date if (next_calendar_type or a.calendar_id.calendar_type) == "fixed" else not a.date)

    def _convert_single_occurrence_recurrencies(self):
        """Convert recurrent attendances with only one visible occurrence into ad-hoc attendances."""
        def _has_single_remaining_occurrence(att):
            if not att.recurrency or not att.date or att.recurrency_end_type == 'forever':
                return False
            excluded = set(att.recurrency_excluded_occurences or [])
            delta = timedelta(**{att.recurrency_type: att.recurrency_interval})
            current = att.date + delta
            while current <= att.recurrency_until:
                if fields.Date.to_string(current) not in excluded:
                    return False
                current += delta
            return True

        single_occurrence = self.attendance_ids.filtered(_has_single_remaining_occurrence)
        single_occurrence.write({'recurrency': False, 'recurrency_excluded_occurences': False})

    def _clean_excluded_occurrences(self):
        """Remove stale or duplicate entries from recurrency_excluded_occurences.

        Removes dates before the attendance start, dates past recurrency_until,
        dates that don't fall on a valid recurrency occurrence, and duplicates —
        in a single pass per attendance.
        """
        for att in self.attendance_ids.filtered(lambda a: a.recurrency and a.recurrency_excluded_occurences and a.date):
            date_str = fields.Date.to_string(att.date)
            until_str = fields.Date.to_string(att.recurrency_until) if att.recurrency_end_type != 'forever' else None
            seen = set()
            cleaned = []
            for d in att.recurrency_excluded_occurences:
                if d < date_str or (until_str and d > until_str) or d in seen:
                    continue
                diff_days = (fields.Date.from_string(d) - att.date).days
                if att.recurrency_type == 'days' and diff_days % att.recurrency_interval:
                    continue
                if att.recurrency_type == 'weeks' and (diff_days % 7 or (diff_days // 7) % att.recurrency_interval):
                    continue
                seen.add(d)
                cleaned.append(d)
            if cleaned != att.recurrency_excluded_occurences:
                att.recurrency_excluded_occurences = cleaned

    def _calendar_clean_up(self):
        """Clean up attendance records that should not be kept."""
        calendars = self or self.search([])
        calendars._get_attendances_to_unlink().unlink()
        calendars._clean_excluded_occurrences()
        calendars._convert_single_occurrence_recurrencies()

    # --------------------------------------------------
    # Compute Methods
    # --------------------------------------------------

    @api.depends('hours_per_week', 'company_id.resource_calendar_id.hours_per_week')
    def _compute_full_time_required_hours(self):
        for calendar in self.filtered("company_id"):
            calendar.full_time_required_hours = calendar.company_id.resource_calendar_id.hours_per_week

    @api.depends('company_id', 'calendar_type')
    def _compute_attendance_ids(self):
        for calendar in self:
            calendar_changed = calendar._origin and calendar._origin.company_id != calendar.company_id
            if (not calendar.id or calendar_changed) and calendar.calendar_type == "fixed" and not calendar.attendance_ids:
                calendar.attendance_ids = calendar._get_default_attendance_ids(calendar.company_id)

    @api.depends('company_id')
    def _compute_global_leave_ids(self):
        for calendar in self.filtered(lambda c: not c._origin or c._origin.company_id != c.company_id):
            calendar.update({
                'global_leave_ids': [(5, 0, 0)] + [
                    (0, 0, leave._copy_leave_vals()) for leave in calendar.company_id.resource_calendar_id.global_leave_ids],
            })

    @api.depends('attendance_ids.dayofweek', 'calendar_type')
    def _compute_days_per_week(self):
        for calendar in self:
            if calendar.calendar_type == 'variable':
                continue
            calendar.days_per_week = len(set(calendar._get_working_attendances().mapped('dayofweek')))

    @api.depends('days_per_week', 'hours_per_week')
    def _compute_hours_per_day(self):
        for calendar in self:
            calendar.hours_per_day = calendar.hours_per_week / calendar.days_per_week if calendar.days_per_week else 0

    @api.depends('attendance_ids.duration_hours', 'calendar_type')
    def _compute_hours_per_week(self):
        """ Compute the average hours per week """
        for calendar in self:
            if calendar.calendar_type == 'variable':
                continue
            attendances = calendar._get_working_attendances()
            calendar.hours_per_week = sum(attendances.mapped('duration_hours'))

    def _compute_work_resources_count(self):
        resources_per_calendar = dict(self.env['resource.resource']._read_group(
            domain=[('calendar_id', 'in', self.ids)],
            groupby=['calendar_id'],
            aggregates=['__count']))
        for calendar in self:
            calendar.work_resources_count = resources_per_calendar.get(calendar, 0)

    @api.depends('hours_per_week', 'full_time_required_hours')
    def _compute_is_fulltime(self):
        for calendar in self:
            calendar.is_fulltime = float_compare(calendar.full_time_required_hours, calendar.hours_per_week, 3) == 0

    @api.depends('hours_per_week', 'full_time_required_hours')
    def _compute_work_time_rate(self):
        for calendar in self:
            if calendar.full_time_required_hours:
                calendar.work_time_rate = calendar.hours_per_week / calendar.full_time_required_hours
            else:
                calendar.work_time_rate = 1.0

    def is_calendar_referenced(self):
        self.ensure_one()
        relations = self.env['ir.model.fields'].sudo().search([
            ('ttype', '=', 'many2one'),
            ('store', '=', True),
            ('model', 'not ilike', 'resource.calendar'),
            ('model_id.abstract', '=', False),
            ('relation', '=', "resource.calendar")
        ])
        for field in relations:
            count = self.env[field.model].sudo().search_count([(field.name, '=', self.id)], limit=1)
            if count:
                return True
        return False

    # --------------------------------------------------
    # Overrides
    # --------------------------------------------------

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        return [dict(vals, name=self.env._("%s (copy)", calendar.name)) for calendar, vals in zip(self, vals_list)]

    @api.model_create_multi
    def create(self, vals_list):
        calendars = super().create(vals_list)
        calendars._get_attendances_to_unlink().unlink()
        return calendars

    def write(self, vals):
        res = super().write(vals)
        self._get_attendances_to_unlink().unlink()
        return res

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

        domain = Domain(domain or Domain.TRUE)
        if self:
            attendances_per_day = self._get_attendances_by_date(start.date(), end.date(), domain | Domain('duration_based', '=', True))
        else:
            attendances_per_day = defaultdict(lambda: self.env['resource.calendar.attendance'])

        # Generate once with utc as timezone
        base_result = []
        for day, all_attendances in attendances_per_day.items():
            # If all attendance lines are duration based, compute correct intervals
            all_duration_based_attendances = all_attendances.filtered('duration_based')
            attendances = all_attendances.filtered(domain)
            if all(att.duration_based for att in attendances):
                total_hours = sum(all_duration_based_attendances.mapped('duration_hours'))
                hours_per_attendance = {}
                current_hour_from = 12 - total_hours / 2
                for att in all_duration_based_attendances:
                    hours_per_attendance[att] = (current_hour_from, current_hour_from + att.duration_hours)
                    current_hour_from += att.duration_hours
                for att in attendances:
                    hour_from, hour_to = hours_per_attendance[att]
                    day_from = datetime.combine(day, float_to_time(hour_from))
                    day_to = datetime.combine(day, float_to_time(hour_to))
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
                if not domain and resource and is_fully_flexible:
                    # A domain is only provided in extensions of `_work_intervals_batch` so when a domain is present,
                    # we should use the standard attendance intervals rather than the flexible employee special handling.
                    # This prevents a scenario where `_work_intervals_batch` calls this method twice and returns the same
                    # value, causing the them to cancel out.
                    #
                    # If the resource is fully flexible, return the whole period from start_dt to end_dt with a dummy attendance
                    hours = (end_dt - start_dt).total_seconds() / 3600
                    dummy_attendance = self.env['resource.calendar.attendance'].new({
                        'duration_hours': hours,
                    })
                    result_per_resource_id[resource.id] = Intervals([(start_datetime, end_datetime, dummy_attendance)], keep_distinct=True)
                elif not domain and resource and is_flexible:
                    # For flexible Calendars, we create intervals to fill in the weekly intervals with the average daily hours
                    # until the full time required hours are met. This gives us the most correct approximation when looking at a daily
                    # and weekly range for time offs and overtime calculations and work entry generation
                    start_date = start_datetime
                    end_datetime_adjusted = end_datetime - relativedelta(seconds=1)
                    end_date = end_datetime_adjusted

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
                    if leave_resource and leave_resource._is_flexible():
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
            if resource and resource._is_flexible():
                leaves = self._leave_intervals_batch(start_dt, end_dt, resources_per_tz, domain)
                if res_leaves := leaves.get(resource.id, []):
                    result[resource.id] = [(i[0].astimezone(UTC), i[1].astimezone(UTC)) for i in res_leaves]
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
        if self:
            self.ensure_one()
        day_hours = defaultdict(float)
        day_days = defaultdict(float)
        for start, stop, _ in attendance_intervals:
            # If the interval covers only a part of the original attendance, we
            # take durations in days proportionally to what is left of the interval.
            interval_hours = (stop - start).total_seconds() / 3600
            day_hours[start.date()] += interval_hours

        duration_based_attendances = self.attendance_ids.filtered('duration_based')
        for day, hours in day_hours.items():
            if attendances := duration_based_attendances._filter_by_date(day):
                hours_per_day = sum(attendances.mapped('duration_hours'))
                day_days[day] += hours / hours_per_day if hours_per_day else 0
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

    def _get_working_attendances(self):
        # If the calendar is variable, we want all attendances that have a date.
        # If the calendar is fixed, we want all attendances that don't have a date.
        return self.attendance_ids.filtered(lambda attendance:
            attendance._is_work_period() and (
                (attendance.calendar_id.calendar_type == 'fixed' and not attendance.date) or
                (attendance.calendar_id.calendar_type == 'variable' and attendance.date)
            ),
        )

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
        if company_id and company_id.resource_calendar_id.calendar_type == "fixed" and (attendances := company_id.resource_calendar_id.attendance_ids):
            return [Command.clear()] + [Command.create(attendance) for attendance in attendances._to_dict()]
        return [Command.clear()] + [
            Command.create({'dayofweek': str(dayofweek), 'duration_hours': 8, 'hour_from': 0, 'hour_to': 0})
            for dayofweek in range(5)
        ]

    # --------------------------------------------------
    # External API
    # --------------------------------------------------

    def get_work_hours_count(self, start_dt, end_dt, compute_leaves=True, domain=None):
        """
            `compute_leaves` controls whether or not this method is taking into
            account the global leaves.

            `domain` controls the way leaves are recognized.
            None means default value ('count_as', '=', 'absence')

            Counts the number of work hours between two dates/datetimes.
        """
        self.ensure_one()

        # datetime is also an instance of date
        assert isinstance(start_dt, date)
        assert isinstance(end_dt, date)

        tz = ZoneInfo(self.env.company.tz)

        # convert to datetime if object passed is date
        if not isinstance(start_dt, datetime):
            start_dt = datetime.combine(start_dt, time.min, tz)
        if not isinstance(end_dt, datetime):
            end_dt = datetime.combine(end_dt, time.max, tz)

        # Set timezone in company tz if no timezone is explicitly given
        if not start_dt.tzinfo:
            start_dt = start_dt.astimezone(tz)
        if not end_dt.tzinfo:
            end_dt = end_dt.astimezone(tz)

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
        self.ensure_one()
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
        return bool(self._get_working_attendances()._filter_by_date(date))

    def _get_attendances_by_date(self, date_from, date_to, domain=None):
        """
        Get the attendances between date_from and date_to, grouped by day, as a recordset of resource.calendar.attendance.
            - For variable schedule, only attendances with a date are considered. If an attendance has a recurrency rule, it will be repeated on the corresponding days.
            - For fixed schedule, only attendances without a date are considered. They will be grouped by their dayofweek and returned on the corresponding days.

        :param date_from: start date of the period (included)
        :param date_to: end date of the period (included)
        :param domain: optional domain to filter attendances
        """
        self.ensure_one()
        result = defaultdict(lambda: self.env['resource.calendar.attendance'])

        domain_fixed = Domain([('date', '=', False)])
        domain_variable_recurrency = Domain([
            ('recurrency', '=', True),
            ('date', '<=', date_to),
            ('recurrency_until', '>=', date_from),
        ])
        domain_variable_adhoc = Domain([
            ('recurrency', '=', False),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ])
        domain_to_fetch = Domain.AND([
            domain or Domain.TRUE,
            Domain.OR([
                domain_fixed,
                domain_variable_recurrency,
                domain_variable_adhoc,
            ]),
            Domain('calendar_id', '=', self.id),
        ])
        attendances = self.env["resource.calendar.attendance"].search_fetch(domain_to_fetch)
        recurrent_attendances = attendances.filtered("recurrency")
        ad_hoc_attendances = (attendances - recurrent_attendances).grouped(lambda a: a.date or a.dayofweek)
        for day in rrule(DAILY, date_from, until=date_to):
            result[day.date()] = ad_hoc_attendances.get(day.date(), self.env['resource.calendar.attendance'])
            result[day.date()] += ad_hoc_attendances.get(str(day.weekday()), self.env['resource.calendar.attendance'])
            result[day.date()] += recurrent_attendances._filter_by_date(day.date())
        return result

    def get_attendances(self, date_from, date_to, fields_to_fetch, domain=None):
        date_from = fields.Date.from_string(date_from)
        date_to = fields.Date.from_string(date_to)
        attendances_per_date = self._get_attendances_by_date(date_from, date_to, domain)
        formatted_attendances = defaultdict(self.env["resource.calendar.attendance"].browse)
        for att_date, attendances in attendances_per_date.items():
            new_formatted_attendances = attendances._read_format(fnames=fields_to_fetch)
            for attendance in new_formatted_attendances:
                if formatted_attendances[attendance['id']]:
                    formatted_attendances[attendance['id']]['other_dates'].append(att_date)
                else:
                    attendance['date'] = att_date
                    attendance['other_dates'] = []
                    formatted_attendances[attendance['id']] = attendance
        return list(formatted_attendances.values())
