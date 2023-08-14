# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
import math
from datetime import datetime, time, timedelta
from dateutil.relativedelta import relativedelta
from dateutil.rrule import rrule, DAILY, WEEKLY
from functools import partial
from itertools import chain
from pytz import timezone, utc

from odoo import api, fields, models, _
from odoo.addons.base.models.res_partner import _tz_get
from odoo.exceptions import ValidationError
from odoo.osv import expression
from odoo.tools.float_utils import float_round

from odoo.tools import date_utils, float_utils
from .resource_mixin import timezone_datetime

# Default hour per day value. The one should
# only be used when the one from the calendar
# is not available.
HOURS_PER_DAY = 8
# This will generate 16th of days
ROUNDING_FACTOR = 16


def make_aware(dt):
    """ Return ``dt`` with an explicit timezone, together with a function to
        convert a datetime to the same (naive or aware) timezone as ``dt``.
    """
    if dt.tzinfo:
        return dt, lambda val: val.astimezone(dt.tzinfo)
    else:
        return dt.replace(tzinfo=utc), lambda val: val.astimezone(utc).replace(tzinfo=None)


def string_to_datetime(value):
    """ Convert the given string value to a datetime in UTC. """
    return utc.localize(fields.Datetime.from_string(value))


def datetime_to_string(dt):
    """ Convert the given datetime (converted in UTC) to a string value. """
    return fields.Datetime.to_string(dt.astimezone(utc))


def float_to_time(hours):
    """ Convert a number of hours into a time object. """
    if hours == 24.0:
        return time.max
    fractional, integral = math.modf(hours)
    return time(int(integral), int(float_round(60 * fractional, precision_digits=0)), 0)


def _boundaries(intervals, opening, closing):
    """ Iterate on the boundaries of intervals. """
    for start, stop, recs in intervals:
        if start < stop:
            yield (start, opening, recs)
            yield (stop, closing, recs)


class Intervals(object):
    """ Collection of ordered disjoint intervals with some associated records.
        Each interval is a triple ``(start, stop, records)``, where ``records``
        is a recordset.
    """
    def __init__(self, intervals=()):
        self._items = []
        if intervals:
            # normalize the representation of intervals
            append = self._items.append
            starts = []
            recses = []
            for value, flag, recs in sorted(_boundaries(intervals, 'start', 'stop')):
                if flag == 'start':
                    starts.append(value)
                    recses.append(recs)
                else:
                    start = starts.pop()
                    if not starts:
                        append((start, value, recses[0].union(*recses)))
                        recses.clear()

    def __bool__(self):
        return bool(self._items)

    def __len__(self):
        return len(self._items)

    def __iter__(self):
        return iter(self._items)

    def __reversed__(self):
        return reversed(self._items)

    def __or__(self, other):
        """ Return the union of two sets of intervals. """
        return Intervals(chain(self._items, other._items))

    def __and__(self, other):
        """ Return the intersection of two sets of intervals. """
        return self._merge(other, False)

    def __sub__(self, other):
        """ Return the difference of two sets of intervals. """
        return self._merge(other, True)

    def _merge(self, other, difference):
        """ Return the difference or intersection of two sets of intervals. """
        result = Intervals()
        append = result._items.append

        # using 'self' and 'other' below forces normalization
        bounds1 = _boundaries(self, 'start', 'stop')
        bounds2 = _boundaries(other, 'switch', 'switch')

        start = None                    # set by start/stop
        recs1 = None                    # set by start
        enabled = difference            # changed by switch
        for value, flag, recs in sorted(chain(bounds1, bounds2)):
            if flag == 'start':
                start = value
                recs1 = recs
            elif flag == 'stop':
                if enabled and start < value:
                    append((start, value, recs1))
                start = None
            else:
                if not enabled and start is not None:
                    start = value
                if enabled and start is not None and start < value:
                    append((start, value, recs1))
                enabled = not enabled

        return result


class ResourceCalendar(models.Model):
    """ Calendar model for a resource. It has

     - attendance_ids: list of resource.calendar.attendance that are a working
                       interval in a given weekday.
     - leave_ids: list of leaves linked to this calendar. A leave can be general
                  or linked to a specific resource, depending on its resource_id.

    All methods in this class use intervals. An interval is a tuple holding
    (begin_datetime, end_datetime). A list of intervals is therefore a list of
    tuples, holding several intervals of work or leaves. """
    _name = "resource.calendar"
    _description = "Resource Working Time"

    @api.model
    def default_get(self, fields):
        res = super(ResourceCalendar, self).default_get(fields)
        if not res.get('name') and res.get('company_id'):
            res['name'] = _('Working Hours of %s', self.env['res.company'].browse(res['company_id']).name)
        if 'attendance_ids' in fields and not res.get('attendance_ids'):
            company_id = res.get('company_id', self.env.company.id)
            company = self.env['res.company'].browse(company_id)
            company_attendance_ids = company.resource_calendar_id.attendance_ids
            if not company.resource_calendar_id.two_weeks_calendar and company_attendance_ids:
                res['attendance_ids'] = [
                    (0, 0, {
                        'name': attendance.name,
                        'dayofweek': attendance.dayofweek,
                        'hour_from': attendance.hour_from,
                        'hour_to': attendance.hour_to,
                        'day_period': attendance.day_period,
                    })
                    for attendance in company_attendance_ids
                ]
            else:
                res['attendance_ids'] = [
                    (0, 0, {'name': _('Monday Morning'), 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': _('Monday Afternoon'), 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                    (0, 0, {'name': _('Tuesday Morning'), 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': _('Tuesday Afternoon'), 'dayofweek': '1', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                    (0, 0, {'name': _('Wednesday Morning'), 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': _('Wednesday Afternoon'), 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                    (0, 0, {'name': _('Thursday Morning'), 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': _('Thursday Afternoon'), 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'}),
                    (0, 0, {'name': _('Friday Morning'), 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                    (0, 0, {'name': _('Friday Afternoon'), 'dayofweek': '4', 'hour_from': 13, 'hour_to': 17, 'day_period': 'afternoon'})
                ]
        return res

    name = fields.Char(required=True)
    active = fields.Boolean("Active", default=True,
                            help="If the active field is set to false, it will allow you to hide the Working Time without removing it.")
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env.company)
    attendance_ids = fields.One2many(
        'resource.calendar.attendance', 'calendar_id', 'Working Time',
        compute='_compute_attendance_ids', store=True, readonly=False, copy=True)
    leave_ids = fields.One2many(
        'resource.calendar.leaves', 'calendar_id', 'Time Off')
    global_leave_ids = fields.One2many(
        'resource.calendar.leaves', 'calendar_id', 'Global Time Off',
        compute='_compute_global_leave_ids', store=True, readonly=False,
        domain=[('resource_id', '=', False)], copy=True,
    )
    hours_per_day = fields.Float("Average Hour per Day", default=HOURS_PER_DAY,
                                 help="Average hours per day a resource is supposed to work with this calendar.")
    tz = fields.Selection(
        _tz_get, string='Timezone', required=True,
        default=lambda self: self._context.get('tz') or self.env.user.tz or self.env.ref('base.user_admin').tz or 'UTC',
        help="This field is used in order to define in which timezone the resources will work.")
    tz_offset = fields.Char(compute='_compute_tz_offset', string='Timezone offset', invisible=True)
    two_weeks_calendar = fields.Boolean(string="Calendar in 2 weeks mode")
    two_weeks_explanation = fields.Char('Explanation', compute="_compute_two_weeks_explanation")

    @api.depends('company_id')
    def _compute_attendance_ids(self):
        for calendar in self.filtered(lambda c: not c._origin or c._origin.company_id != c.company_id and c.company_id):
            company_calendar = calendar.company_id.resource_calendar_id
            calendar.write({
                'two_weeks_calendar': company_calendar.two_weeks_calendar,
                'hours_per_day': company_calendar.hours_per_day,
                'tz': company_calendar.tz,
                'attendance_ids': [(5, 0, 0)] + [
                    (0, 0, attendance._copy_attendance_vals()) for attendance in company_calendar.attendance_ids if not attendance.resource_id]
            })

    @api.depends('company_id')
    def _compute_global_leave_ids(self):
        for calendar in self.filtered(lambda c: not c._origin or c._origin.company_id != c.company_id):
            calendar.write({
                'global_leave_ids': [(5, 0, 0)] + [
                    (0, 0, leave._copy_leave_vals()) for leave in calendar.company_id.resource_calendar_id.global_leave_ids]
            })

    @api.depends('tz')
    def _compute_tz_offset(self):
        for calendar in self:
            calendar.tz_offset = datetime.now(timezone(calendar.tz or 'GMT')).strftime('%z')

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        if default is None:
            default = {}
        if not default.get('name'):
            default.update(name=_('%s (copy)') % (self.name))
        return super(ResourceCalendar, self).copy(default)

    @api.constrains('attendance_ids')
    def _check_attendance_ids(self):
        for resource in self:
            if (resource.two_weeks_calendar and
                    resource.attendance_ids.filtered(lambda a: a.display_type == 'line_section') and
                    not resource.attendance_ids.sorted('sequence')[0].display_type):
                raise ValidationError(_("In a calendar with 2 weeks mode, all periods need to be in the sections."))

    @api.depends('two_weeks_calendar')
    def _compute_two_weeks_explanation(self):
        today = fields.Date.today()
        week_type = self.env['resource.calendar.attendance'].get_week_type(today)
        week_type_str = _("second") if week_type else _("first")
        first_day = date_utils.start_of(today, 'week')
        last_day = date_utils.end_of(today, 'week')
        self.two_weeks_explanation = _("The current week (from %s to %s) correspond to the  %s one.", first_day,
                                       last_day, week_type_str)

    def _get_global_attendances(self):
        return self.attendance_ids.filtered(lambda attendance:
            not attendance.date_from and not attendance.date_to
            and not attendance.resource_id and not attendance.display_type)

    def _compute_hours_per_day(self, attendances):
        if not attendances:
            return 0

        hour_count = 0.0
        for attendance in attendances:
            hour_count += attendance.hour_to - attendance.hour_from

        if self.two_weeks_calendar:
            number_of_days = len(set(attendances.filtered(lambda cal: cal.week_type == '1').mapped('dayofweek')))
            number_of_days += len(set(attendances.filtered(lambda cal: cal.week_type == '0').mapped('dayofweek')))
        else:
            number_of_days = len(set(attendances.mapped('dayofweek')))

        return float_round(hour_count / float(number_of_days), precision_digits=2)

    @api.onchange('attendance_ids', 'two_weeks_calendar')
    def _onchange_hours_per_day(self):
        attendances = self._get_global_attendances()
        self.hours_per_day = self._compute_hours_per_day(attendances)

    def switch_calendar_type(self):
        if not self.two_weeks_calendar:
            self.attendance_ids.unlink()
            self.attendance_ids = [
                (0, 0, {
                    'name': 'First week',
                    'dayofweek': '0',
                    'sequence': '0',
                    'hour_from': 0,
                    'day_period': 'morning',
                    'week_type': '0',
                    'hour_to': 0,
                    'display_type':
                    'line_section'}),
                (0, 0, {
                    'name': 'Second week',
                    'dayofweek': '0',
                    'sequence': '25',
                    'hour_from': 0,
                    'day_period': 'morning',
                    'week_type': '1',
                    'hour_to': 0,
                    'display_type': 'line_section'}),
            ]

            self.two_weeks_calendar = True
            default_attendance = self.default_get('attendance_ids')['attendance_ids']
            for idx, att in enumerate(default_attendance):
                att[2]["week_type"] = '0'
                att[2]["sequence"] = idx + 1
            self.attendance_ids = default_attendance
            for idx, att in enumerate(default_attendance):
                att[2]["week_type"] = '1'
                att[2]["sequence"] = idx + 26
            self.attendance_ids = default_attendance
        else:
            self.two_weeks_calendar = False
            self.attendance_ids.unlink()
            self.attendance_ids = self.default_get('attendance_ids')['attendance_ids']
        self._onchange_hours_per_day()

    @api.onchange('attendance_ids')
    def _onchange_attendance_ids(self):
        if not self.two_weeks_calendar:
            return

        even_week_seq = self.attendance_ids.filtered(lambda att: att.display_type == 'line_section' and att.week_type == '0')
        odd_week_seq = self.attendance_ids.filtered(lambda att: att.display_type == 'line_section' and att.week_type == '1')
        if len(even_week_seq) != 1 or len(odd_week_seq) != 1:
            raise ValidationError(_("You can't delete section between weeks."))

        even_week_seq = even_week_seq.sequence
        odd_week_seq = odd_week_seq.sequence

        for line in self.attendance_ids.filtered(lambda att: att.display_type is False):
            if even_week_seq > odd_week_seq:
                line.week_type = '1' if even_week_seq > line.sequence else '0'
            else:
                line.week_type = '0' if odd_week_seq > line.sequence else '1'

    def _check_overlap(self, attendance_ids):
        """ attendance_ids correspond to attendance of a week,
            will check for each day of week that there are no superimpose. """
        result = []
        for attendance in attendance_ids.filtered(lambda att: not att.date_from and not att.date_to):
            # 0.000001 is added to each start hour to avoid to detect two contiguous intervals as superimposing.
            # Indeed Intervals function will join 2 intervals with the start and stop hour corresponding.
            result.append((int(attendance.dayofweek) * 24 + attendance.hour_from + 0.000001, int(attendance.dayofweek) * 24 + attendance.hour_to, attendance))

        if len(Intervals(result)) != len(result):
            raise ValidationError(_("Attendances can't overlap."))

    @api.constrains('attendance_ids')
    def _check_attendance(self):
        # Avoid superimpose in attendance
        for calendar in self:
            attendance_ids = calendar.attendance_ids.filtered(lambda attendance: not attendance.resource_id and attendance.display_type is False)
            if calendar.two_weeks_calendar:
                calendar._check_overlap(attendance_ids.filtered(lambda attendance: attendance.week_type == '0'))
                calendar._check_overlap(attendance_ids.filtered(lambda attendance: attendance.week_type == '1'))
            else:
                calendar._check_overlap(attendance_ids)

    # --------------------------------------------------
    # Computation API
    # --------------------------------------------------
    def _attendance_intervals_batch(self, start_dt, end_dt, resources=None, domain=None, tz=None):
        """ Return the attendance intervals in the given datetime range.
            The returned intervals are expressed in specified tz or in the resource's timezone.
        """
        self.ensure_one()
        resources = self.env['resource.resource'] if not resources else resources
        assert start_dt.tzinfo and end_dt.tzinfo
        self.ensure_one()
        combine = datetime.combine
        required_tz = tz

        resources_list = list(resources) + [self.env['resource.resource']]
        resource_ids = [r.id for r in resources_list]
        domain = domain if domain is not None else []
        domain = expression.AND([domain, [
            ('calendar_id', '=', self.id),
            ('resource_id', 'in', resource_ids),
            ('display_type', '=', False),
        ]])

        # for each attendance spec, generate the intervals in the date range
        cache_dates = defaultdict(dict)
        cache_deltas = defaultdict(dict)
        result = defaultdict(list)
        for attendance in self.env['resource.calendar.attendance'].search(domain):
            for resource in resources_list:
                # express all dates and times in specified tz or in the resource's timezone
                tz = required_tz if required_tz else timezone((resource or self).tz)
                if (tz, start_dt) in cache_dates:
                    start = cache_dates[(tz, start_dt)]
                else:
                    start = start_dt.astimezone(tz)
                    cache_dates[(tz, start_dt)] = start
                if (tz, end_dt) in cache_dates:
                    end = cache_dates[(tz, end_dt)]
                else:
                    end = end_dt.astimezone(tz)
                    cache_dates[(tz, end_dt)] = end

                start = start.date()
                if attendance.date_from:
                    start = max(start, attendance.date_from)
                until = end.date()
                if attendance.date_to:
                    until = min(until, attendance.date_to)
                if attendance.week_type:
                    start_week_type = self.env['resource.calendar.attendance'].get_week_type(start)
                    if start_week_type != int(attendance.week_type):
                        # start must be the week of the attendance
                        # if it's not the case, we must remove one week
                        start = start + relativedelta(weeks=-1)
                weekday = int(attendance.dayofweek)

                if self.two_weeks_calendar and attendance.week_type:
                    days = rrule(WEEKLY, start, interval=2, until=until, byweekday=weekday)
                else:
                    days = rrule(DAILY, start, until=until, byweekday=weekday)

                for day in days:
                    # We need to exclude incorrect days according to re-defined start previously
                    # with weeks=-1 (Note: until is correctly handled)
                    if (self.two_weeks_calendar and attendance.date_from and attendance.date_from > day.date()):
                        continue
                    # attendance hours are interpreted in the resource's timezone
                    hour_from = attendance.hour_from
                    if (tz, day, hour_from) in cache_deltas:
                        dt0 = cache_deltas[(tz, day, hour_from)]
                    else:
                        dt0 = tz.localize(combine(day, float_to_time(hour_from)))
                        cache_deltas[(tz, day, hour_from)] = dt0

                    hour_to = attendance.hour_to
                    if (tz, day, hour_to) in cache_deltas:
                        dt1 = cache_deltas[(tz, day, hour_to)]
                    else:
                        dt1 = tz.localize(combine(day, float_to_time(hour_to)))
                        cache_deltas[(tz, day, hour_to)] = dt1
                    result[resource.id].append((max(cache_dates[(tz, start_dt)], dt0), min(cache_dates[(tz, end_dt)], dt1), attendance))
        return {r.id: Intervals(result[r.id]) for r in resources_list}

    def _leave_intervals(self, start_dt, end_dt, resource=None, domain=None, tz=None):
        if resource is None:
            resource = self.env['resource.resource']
        return self._leave_intervals_batch(
            start_dt, end_dt, resources=resource, domain=domain, tz=tz
        )[resource.id]

    def _leave_intervals_batch(self, start_dt, end_dt, resources=None, domain=None, tz=None):
        """ Return the leave intervals in the given datetime range.
            The returned intervals are expressed in specified tz or in the calendar's timezone.
        """
        resources = self.env['resource.resource'] if not resources else resources
        assert start_dt.tzinfo and end_dt.tzinfo
        self.ensure_one()

        # for the computation, express all datetimes in UTC
        resources_list = list(resources) + [self.env['resource.resource']]
        resource_ids = [r.id for r in resources_list]
        if domain is None:
            domain = [('time_type', '=', 'leave')]
        domain = domain + [
            ('calendar_id', 'in', [False, self.id]),
            ('resource_id', 'in', resource_ids),
            ('date_from', '<=', datetime_to_string(end_dt)),
            ('date_to', '>=', datetime_to_string(start_dt)),
        ]

        # retrieve leave intervals in (start_dt, end_dt)
        result = defaultdict(lambda: [])
        tz_dates = {}
        for leave in self.env['resource.calendar.leaves'].search(domain):
            for resource in resources_list:
                if leave.resource_id.id not in [False, resource.id]:
                    continue
                tz = tz if tz else timezone((resource or self).tz)
                if (tz, start_dt) in tz_dates:
                    start = tz_dates[(tz, start_dt)]
                else:
                    start = start_dt.astimezone(tz)
                    tz_dates[(tz, start_dt)] = start
                if (tz, end_dt) in tz_dates:
                    end = tz_dates[(tz, end_dt)]
                else:
                    end = end_dt.astimezone(tz)
                    tz_dates[(tz, end_dt)] = end
                dt0 = string_to_datetime(leave.date_from).astimezone(tz)
                dt1 = string_to_datetime(leave.date_to).astimezone(tz)
                result[resource.id].append((max(start, dt0), min(end, dt1), leave))

        return {r.id: Intervals(result[r.id]) for r in resources_list}

    def _work_intervals_batch(self, start_dt, end_dt, resources=None, domain=None, tz=None):
        """ Return the effective work intervals between the given datetimes. """
        if not resources:
            resources = self.env['resource.resource']
            resources_list = [resources]
        else:
            resources_list = list(resources)

        attendance_intervals = self._attendance_intervals_batch(start_dt, end_dt, resources, tz=tz)
        leave_intervals = self._leave_intervals_batch(start_dt, end_dt, resources, domain, tz=tz)
        return {
            r.id: (attendance_intervals[r.id] - leave_intervals[r.id]) for r in resources_list
        }

    def _unavailable_intervals(self, start_dt, end_dt, resource=None, domain=None, tz=None):
        if resource is None:
            resource = self.env['resource.resource']
        return self._unavailable_intervals_batch(
            start_dt, end_dt, resources=resource, domain=domain, tz=tz
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
            work_intervals = [(start, stop) for start, stop, meta in resources_work_intervals[resource.id]]
            # start + flatten(intervals) + end
            work_intervals = [start_dt] + list(chain.from_iterable(work_intervals)) + [end_dt]
            # put it back to UTC
            work_intervals = list(map(lambda dt: dt.astimezone(utc), work_intervals))
            # pick groups of two
            work_intervals = list(zip(work_intervals[0::2], work_intervals[1::2]))
            result[resource.id] = work_intervals
        return result

    # --------------------------------------------------
    # Private Methods / Helpers
    # --------------------------------------------------

    def _get_days_data(self, intervals, day_total):
        """
        helper function to compute duration of `intervals`
        expressed in days and hours.
        `day_total` is a dict {date: n_hours} with the number of hours for each day.
        """
        day_hours = defaultdict(float)
        for start, stop, meta in intervals:
            day_hours[start.date()] += (stop - start).total_seconds() / 3600

        # compute number of days as quarters
        days = sum(
            float_utils.round(ROUNDING_FACTOR * day_hours[day] / day_total[day]) / ROUNDING_FACTOR if day_total[day] else 0
            for day in day_hours
        )
        return {
            'days': days,
            'hours': sum(day_hours.values()),
        }

    def _get_resources_day_total(self, from_datetime, to_datetime, resources=None):
        """
        @return dict with hours of attendance in each day between `from_datetime` and `to_datetime`
        """
        self.ensure_one()
        resources = self.env['resource.resource'] if not resources else resources
        resources_list = list(resources) + [self.env['resource.resource']]
        # total hours per day:  retrieve attendances with one extra day margin,
        # in order to compute the total hours on the first and last days
        from_full = from_datetime - timedelta(days=1)
        to_full = to_datetime + timedelta(days=1)
        intervals = self._attendance_intervals_batch(from_full, to_full, resources=resources)

        result = defaultdict(lambda: defaultdict(float))
        for resource in resources_list:
            day_total = result[resource.id]
            for start, stop, meta in intervals[resource.id]:
                day_total[start.date()] += (stop - start).total_seconds() / 3600
        return result

    def _get_closest_work_time(self, dt, match_end=False, resource=None, search_range=None):
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

        if not dt.tzinfo or search_range and not (search_range[0].tzinfo and search_range[1].tzinfo):
            raise ValueError('Provided datetimes needs to be timezoned')

        dt = dt.astimezone(timezone(tz))

        if not search_range:
            range_start = dt + relativedelta(hour=0, minute=0, second=0)
            range_end = dt + relativedelta(days=1, hour=0, minute=0, second=0)
        else:
            range_start, range_end = search_range

        if not range_start <= dt <= range_end:
            return None
        work_intervals = sorted(
            self._work_intervals_batch(range_start, range_end, resource)[resource.id],
            key=lambda i: abs(interval_dt(i) - dt),
        )
        return interval_dt(work_intervals[0]) if work_intervals else None

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
        from_datetime, dummy = make_aware(from_datetime)
        to_datetime, dummy = make_aware(to_datetime)

        day_total = self._get_resources_day_total(from_datetime, to_datetime)[False]

        # actual hours per day
        if compute_leaves:
            intervals = self._work_intervals_batch(from_datetime, to_datetime, domain=domain)[False]
        else:
            intervals = self._attendance_intervals_batch(from_datetime, to_datetime, domain=domain)[False]

        return self._get_days_data(intervals, day_total)

    def plan_hours(self, hours, day_dt, compute_leaves=False, domain=None, resource=None):
        """
        `compute_leaves` controls whether or not this method is taking into
        account the global leaves.

        `domain` controls the way leaves are recognized.
        None means default value ('time_type', '=', 'leave')

        Return datetime after having planned hours
        """
        day_dt, revert = make_aware(day_dt)

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
                for start, stop, meta in get_intervals(dt, dt + delta)[resource_id]:
                    interval_hours = (stop - start).total_seconds() / 3600
                    if hours <= interval_hours:
                        return revert(start + timedelta(hours=hours))
                    hours -= interval_hours
            return False
        else:
            hours = abs(hours)
            delta = timedelta(days=14)
            for n in range(100):
                dt = day_dt - delta * n
                for start, stop, meta in reversed(get_intervals(dt - delta, dt)[resource_id]):
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
        day_dt, revert = make_aware(day_dt)

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
                for start, stop, meta in get_intervals(dt, dt + delta)[False]:
                    found.add(start.date())
                    if len(found) == days:
                        return revert(stop)
            return False

        elif days < 0:
            days = abs(days)
            found = set()
            delta = timedelta(days=14)
            for n in range(100):
                dt = day_dt - delta * n
                for start, stop, meta in reversed(get_intervals(dt - delta, dt)[False]):
                    found.add(start.date())
                    if len(found) == days:
                        return revert(start)
            return False

        else:
            return revert(day_dt)

    def _get_max_number_of_hours(self, start, end):
        self.ensure_one()
        if not self.attendance_ids:
            return 0
        mapped_data = defaultdict(lambda: 0)
        for attendance in self.attendance_ids.filtered(lambda a: (not a.date_from or not a.date_to) or (a.date_from <= end.date() and a.date_to >= start.date())):
            mapped_data[(attendance.week_type, attendance.dayofweek)] += attendance.hour_to - attendance.hour_from
        return max(mapped_data.values())


class ResourceCalendarAttendance(models.Model):
    _name = "resource.calendar.attendance"
    _description = "Work Detail"
    _order = 'week_type, dayofweek, hour_from'

    name = fields.Char(required=True)
    dayofweek = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday')
        ], 'Day of Week', required=True, index=True, default='0')
    date_from = fields.Date(string='Starting Date')
    date_to = fields.Date(string='End Date')
    hour_from = fields.Float(string='Work from', required=True, index=True,
        help="Start and End time of working.\n"
             "A specific value of 24:00 is interpreted as 23:59:59.999999.")
    hour_to = fields.Float(string='Work to', required=True)
    calendar_id = fields.Many2one("resource.calendar", string="Resource's Calendar", required=True, ondelete='cascade')
    day_period = fields.Selection([('morning', 'Morning'), ('afternoon', 'Afternoon')], required=True, default='morning')
    resource_id = fields.Many2one('resource.resource', 'Resource')
    week_type = fields.Selection([
        ('1', 'Second'),
        ('0', 'First')
        ], 'Week Number', default=False)
    two_weeks_calendar = fields.Boolean("Calendar in 2 weeks mode", related='calendar_id.two_weeks_calendar')
    display_type = fields.Selection([
        ('line_section', "Section")], default=False, help="Technical field for UX purpose.")
    sequence = fields.Integer(default=10,
        help="Gives the sequence of this line when displaying the resource calendar.")

    @api.onchange('hour_from', 'hour_to')
    def _onchange_hours(self):
        # avoid negative or after midnight
        self.hour_from = min(self.hour_from, 23.99)
        self.hour_from = max(self.hour_from, 0.0)
        self.hour_to = min(self.hour_to, 24)
        self.hour_to = max(self.hour_to, 0.0)

        # avoid wrong order
        self.hour_to = max(self.hour_to, self.hour_from)

    @api.model
    def get_week_type(self, date):
        # week_type is defined by
        #  * counting the number of days from January 1 of year 1
        #    (extrapolated to dates prior to the first adoption of the Gregorian calendar)
        #  * converted to week numbers and then the parity of this number is asserted.
        # It ensures that an even week number always follows an odd week number. With classical week number,
        # some years have 53 weeks. Therefore, two consecutive odd week number follow each other (53 --> 1).
        return int(math.floor((date.toordinal() - 1) / 7) % 2)

    def _compute_display_name(self):
        super()._compute_display_name()
        this_week_type = str(self.get_week_type(fields.Date.context_today(self)))
        section_names = {'0': _('First week'), '1': _('Second week')}
        section_info = {True: _('this week'), False: _('other week')}
        for record in self.filtered(lambda l: l.display_type == 'line_section'):
            section_name = "%s (%s)" % (section_names[record.week_type], section_info[this_week_type == record.week_type])
            record.display_name = section_name

    def _copy_attendance_vals(self):
        self.ensure_one()
        return {
            'name': self.name,
            'dayofweek': self.dayofweek,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'hour_from': self.hour_from,
            'hour_to': self.hour_to,
            'day_period': self.day_period,
            'week_type': self.week_type,
            'display_type': self.display_type,
            'sequence': self.sequence,
        }


class ResourceResource(models.Model):
    _name = "resource.resource"
    _description = "Resources"
    _order = "name"

    @api.model
    def default_get(self, fields):
        res = super(ResourceResource, self).default_get(fields)
        if not res.get('calendar_id') and res.get('company_id'):
            company = self.env['res.company'].browse(res['company_id'])
            res['calendar_id'] = company.resource_calendar_id.id
        return res

    name = fields.Char(required=True)
    active = fields.Boolean(
        'Active', default=True,
        help="If the active field is set to False, it will allow you to hide the resource record without removing it.")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    resource_type = fields.Selection([
        ('user', 'Human'),
        ('material', 'Material')], string='Type',
        default='user', required=True)
    user_id = fields.Many2one('res.users', string='User', help='Related user name for the resource to manage its access.')
    time_efficiency = fields.Float(
        'Efficiency Factor', default=100, required=True,
        help="This field is used to calculate the expected duration of a work order at this work center. For example, if a work order takes one hour and the efficiency factor is 100%, then the expected duration will be one hour. If the efficiency factor is 200%, however the expected duration will be 30 minutes.")
    calendar_id = fields.Many2one(
        "resource.calendar", string='Working Time',
        default=lambda self: self.env.company.resource_calendar_id,
        required=True, domain="[('company_id', '=', company_id)]",
        help="Define the schedule of resource")
    tz = fields.Selection(
        _tz_get, string='Timezone', required=True,
        default=lambda self: self._context.get('tz') or self.env.user.tz or 'UTC',
        help="This field is used in order to define in which timezone the resources will work.")

    _sql_constraints = [
        ('check_time_efficiency', 'CHECK(time_efficiency>0)', 'Time efficiency must be strictly positive'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if values.get('company_id') and not values.get('calendar_id'):
                values['calendar_id'] = self.env['res.company'].browse(values['company_id']).resource_calendar_id.id
            if not values.get('tz'):
                # retrieve timezone on user or calendar
                tz = (self.env['res.users'].browse(values.get('user_id')).tz or
                      self.env['resource.calendar'].browse(values.get('calendar_id')).tz)
                if tz:
                    values['tz'] = tz
        return super(ResourceResource, self).create(vals_list)

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        if default is None:
            default = {}
        if not default.get('name'):
            default.update(name=_('%s (copy)') % (self.name))
        return super(ResourceResource, self).copy(default)

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id:
            self.calendar_id = self.company_id.resource_calendar_id.id

    @api.onchange('user_id')
    def _onchange_user_id(self):
        if self.user_id:
            self.tz = self.user_id.tz

    def _get_work_interval(self, start, end):
        # Deprecated method. Use `_adjust_to_calendar` instead
        return self._adjust_to_calendar(start, end)

    def _adjust_to_calendar(self, start, end):
        """Adjust the given start and end datetimes to the closest effective hours encoded
        in the resource calendar. Only attendances in the same day as `start` and `end` are
        considered (respectively). If no attendance is found during that day, the closest hour
        is None.
        e.g. simplified example:
             given two attendances: 8am-1pm and 2pm-5pm, given start=9am and end=6pm
             resource._adjust_to_calendar(start, end)
             >>> {resource: (8am, 5pm)}
        :return: Closest matching start and end of working periods for each resource
        :rtype: dict(resource, tuple(datetime | None, datetime | None))
        """
        start, revert_start_tz = make_aware(start)
        end, revert_end_tz = make_aware(end)
        result = {}
        for resource in self:
            calendar_start = resource.calendar_id._get_closest_work_time(start, resource=resource)
            search_range = None
            tz = timezone(resource.tz)
            if calendar_start and start.astimezone(tz).date() == end.astimezone(tz).date():
                end = end.astimezone(tz)
                # Make sure to only search end after start
                search_range = (
                    start,
                    end + relativedelta(days=1, hour=0, minute=0, second=0),
                )
            calendar_end = resource.calendar_id._get_closest_work_time(end, match_end=True, resource=resource, search_range=search_range)
            result[resource] = (
                calendar_start and revert_start_tz(calendar_start),
                calendar_end and revert_end_tz(calendar_end),
            )
        return result


    def _get_unavailable_intervals(self, start, end):
        """ Compute the intervals during which employee is unavailable with hour granularity between start and end
            Note: this method is used in enterprise (forecast and planning)

        """
        start_datetime = timezone_datetime(start)
        end_datetime = timezone_datetime(end)
        resource_mapping = {}
        calendar_mapping = defaultdict(lambda: self.env['resource.resource'])
        for resource in self:
            calendar_mapping[resource.calendar_id] |= resource

        for calendar, resources in calendar_mapping.items():
            resources_unavailable_intervals = calendar._unavailable_intervals_batch(start_datetime, end_datetime, resources, tz=timezone(calendar.tz))
            resource_mapping.update(resources_unavailable_intervals)
        return resource_mapping


class ResourceCalendarLeaves(models.Model):
    _name = "resource.calendar.leaves"
    _description = "Resource Time Off Detail"
    _order = "date_from"

    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'date_from' in fields_list and 'date_to' in fields_list and not res.get('date_from') and not res.get('date_to'):
            # Then we give the current day and we search the begin and end hours for this day in resource.calendar of the current company
            today = fields.Datetime.now()
            user_tz = timezone(self.env.user.tz or self._context.get('tz') or self.company_id.resource_calendar_id.tz or 'UTC')
            date_from = user_tz.localize(datetime.combine(today, time.min))
            date_to = user_tz.localize(datetime.combine(today, time.max))
            intervals = self.env.company.resource_calendar_id._work_intervals_batch(date_from.replace(tzinfo=utc), date_to.replace(tzinfo=utc))[False]
            if intervals:  # Then we stop and return the dates given in parameter
                list_intervals = [(start, stop) for start, stop, records in intervals]  # Convert intervals in interval list
                date_from = list_intervals[0][0]  # We take the first date in the interval list
                date_to = list_intervals[-1][1]  # We take the last date in the interval list
            res.update(
                date_from=date_from.astimezone(utc).replace(tzinfo=None),
                date_to=date_to.astimezone(utc).replace(tzinfo=None)
            )
        return res

    name = fields.Char('Reason')
    company_id = fields.Many2one(
        'res.company', string="Company", readonly=True, store=True,
        default=lambda self: self.env.company, compute='_compute_company_id')
    calendar_id = fields.Many2one('resource.calendar', 'Working Hours', domain="[('company_id', 'in', [company_id, False])]", check_company=True, index=True)
    date_from = fields.Datetime('Start Date', required=True)
    date_to = fields.Datetime('End Date', required=True)
    resource_id = fields.Many2one(
        "resource.resource", 'Resource', index=True,
        help="If empty, this is a generic time off for the company. If a resource is set, the time off is only for this resource")
    time_type = fields.Selection([('leave', 'Time Off'), ('other', 'Other')], default='leave',
                                 help="Whether this should be computed as a time off or as work time (eg: formation)")

    @api.depends('calendar_id')
    def _compute_company_id(self):
        for leave in self:
            leave.company_id = leave.calendar_id.company_id or self.env.company

    @api.constrains('date_from', 'date_to')
    def check_dates(self):
        if self.filtered(lambda leave: leave.date_from > leave.date_to):
            raise ValidationError(_('The start date of the time off must be earlier than the end date.'))

    @api.onchange('resource_id')
    def onchange_resource(self):
        if self.resource_id:
            self.calendar_id = self.resource_id.calendar_id

    def _copy_leave_vals(self):
        self.ensure_one()
        return {
            'name': self.name,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'time_type': self.time_type,
        }
