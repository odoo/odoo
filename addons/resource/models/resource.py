# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import math
import pytz

from collections import namedtuple
from datetime import timedelta
from dateutil import rrule
from dateutil.relativedelta import relativedelta
from operator import itemgetter

from odoo import api, fields, models, _
from odoo.addons.base.res.res_partner import _tz_get
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare


def float_to_time(float_hour):
    return datetime.time(int(math.modf(float_hour)[1]), int(60 * math.modf(float_hour)[0]), 0)


def to_naive_user_tz(datetime, record):
    tz_name = record._context.get('tz') or record.env.user.tz
    tz = tz_name and pytz.timezone(tz_name) or pytz.UTC
    return pytz.UTC.localize(datetime.replace(tzinfo=None), is_dst=False).astimezone(tz).replace(tzinfo=None)


def to_naive_utc(datetime, record):
    tz_name = record._context.get('tz') or record.env.user.tz
    tz = tz_name and pytz.timezone(tz_name) or pytz.UTC
    return tz.localize(datetime.replace(tzinfo=None), is_dst=False).astimezone(pytz.UTC).replace(tzinfo=None)


def to_tz(datetime, tz_name):
    tz = pytz.timezone(tz_name)
    return pytz.UTC.localize(datetime.replace(tzinfo=None), is_dst=False).astimezone(tz).replace(tzinfo=None)


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
    _description = "Resource Calendar"
    _interval_obj = namedtuple('Interval', ('start_datetime', 'end_datetime', 'data'))

    @api.model
    def default_get(self, fields):
        res = super(ResourceCalendar, self).default_get(fields)
        if not res.get('name') and res.get('company_id'):
            res['name'] = _('Working Hours of %s') % self.env['res.company'].browse(res['company_id']).name
        return res

    def _get_default_attendance_ids(self):
        return [
            (0, 0, {'name': _('Monday Morning'), 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12}),
            (0, 0, {'name': _('Monday Evening'), 'dayofweek': '0', 'hour_from': 13, 'hour_to': 17}),
            (0, 0, {'name': _('Tuesday Morning'), 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12}),
            (0, 0, {'name': _('Tuesday Evening'), 'dayofweek': '1', 'hour_from': 13, 'hour_to': 17}),
            (0, 0, {'name': _('Wednesday Morning'), 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12}),
            (0, 0, {'name': _('Wednesday Evening'), 'dayofweek': '2', 'hour_from': 13, 'hour_to': 17}),
            (0, 0, {'name': _('Thursday Morning'), 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12}),
            (0, 0, {'name': _('Thursday Evening'), 'dayofweek': '3', 'hour_from': 13, 'hour_to': 17}),
            (0, 0, {'name': _('Friday Morning'), 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12}),
            (0, 0, {'name': _('Friday Evening'), 'dayofweek': '4', 'hour_from': 13, 'hour_to': 17})
        ]

    name = fields.Char(required=True)
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env['res.company']._company_default_get())
    attendance_ids = fields.One2many(
        'resource.calendar.attendance', 'calendar_id', 'Working Time',
        copy=True, default=_get_default_attendance_ids)
    leave_ids = fields.One2many(
        'resource.calendar.leaves', 'calendar_id', 'Leaves')
    global_leave_ids = fields.One2many(
        'resource.calendar.leaves', 'calendar_id', 'Global Leaves',
        domain=[('resource_id', '=', False)]
        )

    # --------------------------------------------------
    # Utility methods
    # --------------------------------------------------

    def _merge_kw(self, kw, kw_ext):
        new_kw = dict(kw, **kw_ext)
        new_kw.update(
            attendances=kw.get('attendances', self.env['resource.calendar.attendance']) | kw_ext.get('attendances', self.env['resource.calendar.attendance']),
            leaves=kw.get('leaves', self.env['resource.calendar.leaves']) | kw_ext.get('leaves', self.env['resource.calendar.leaves'])
        )
        return new_kw

    def _interval_new(self, start_datetime, end_datetime, kw=None):
        kw = kw if kw is not None else dict()
        kw.setdefault('attendances', self.env['resource.calendar.attendance'])
        kw.setdefault('leaves', self.env['resource.calendar.leaves'])
        return self._interval_obj(start_datetime, end_datetime, kw)

    def _interval_exclude_left(self, interval, interval_dst):
        return self._interval_obj(
            interval.start_datetime > interval_dst.end_datetime and interval.start_datetime or interval_dst.end_datetime,
            interval.end_datetime,
            self._merge_kw(interval.data, interval_dst.data)
        )

    def _interval_exclude_right(self, interval, interval_dst):
        return self._interval_obj(
            interval.start_datetime,
            interval.end_datetime < interval_dst.start_datetime and interval.end_datetime or interval_dst.start_datetime,
            self._merge_kw(interval.data, interval_dst.data)
        )

    def _interval_or(self, interval, interval_dst):
        return self._interval_obj(
            interval.start_datetime < interval_dst.start_datetime and interval.start_datetime or interval_dst.start_datetime,
            interval.end_datetime > interval_dst.end_datetime and interval.end_datetime or interval_dst.end_datetime,
            self._merge_kw(interval.data, interval_dst.data)
        )

    def _interval_and(self, interval, interval_dst):
        return self._interval_obj(
            interval.start_datetime > interval_dst.start_datetime and interval.start_datetime or interval_dst.start_datetime,
            interval.end_datetime < interval_dst.end_datetime and interval.end_datetime or interval_dst.end_datetime,
            self._merge_kw(interval.data, interval_dst.data)
        )

    def _interval_merge(self, intervals):
        """ Sort intervals based on starting datetime and merge overlapping intervals.

        :return list cleaned: sorted intervals merged without overlap """
        intervals = sorted(intervals, key=itemgetter(0))  # sort on first datetime
        cleaned = []
        working_interval = None
        while intervals:
            current_interval = intervals.pop(0)
            if not working_interval:  # init
                working_interval = self._interval_new(*current_interval)
            elif working_interval[1] < current_interval[0]:  # interval is disjoint
                cleaned.append(working_interval)
                working_interval = self._interval_new(*current_interval)
            elif working_interval[1] < current_interval[1]:  # union of greater intervals
                working_interval = self._interval_or(working_interval, current_interval)
        if working_interval:  # handle void lists
            cleaned.append(working_interval)
        return cleaned

    @api.model
    def _interval_remove_leaves(self, interval, leave_intervals):
        """ Remove leave intervals from a base interval

        :param tuple interval: an interval (see above) that is the base interval
                               from which the leave intervals will be removed
        :param list leave_intervals: leave intervals to remove
        :return list intervals: ordered intervals with leaves removed """
        intervals = []
        leave_intervals = self._interval_merge(leave_intervals)
        current_interval = interval
        for leave in leave_intervals:
            # skip if ending before the current start datetime
            if leave[1] <= current_interval[0]:
                continue
            # skip if starting after current end datetime; break as leaves are ordered and
            # are therefore all out of range
            if leave[0] >= current_interval[1]:
                break
            # begins within current interval: close current interval and begin a new one
            # that begins at the leave end datetime
            if current_interval[0] < leave[0] < current_interval[1]:
                intervals.append(self._interval_exclude_right(current_interval, leave))
                current_interval = self._interval_exclude_left(interval, leave)
            # ends within current interval: set current start datetime as leave end datetime
            if current_interval[0] <= leave[1]:
                current_interval = self._interval_exclude_left(interval, leave)
        if current_interval and current_interval[0] < interval[1]:  # remove intervals moved outside base interval due to leaves
            intervals.append(current_interval)
        return intervals

    @api.model
    def _interval_schedule_hours(self, intervals, hour, backwards=False):
        """ Schedule hours in intervals. The last matching interval is truncated
        to match the specified hours. This method can be applied backwards meaning
        scheduling hours going in the past. In that case truncating last interval
        is done accordingly. If number of hours to schedule is greater than possible
        scheduling in the given intervals, returned result equals intervals.

        :param list intervals:  a list of time intervals
        :param int/float hours: number of hours to schedule. It will be converted
                                into a timedelta, but should be submitted as an
                                int or float
        :param boolean backwards: schedule starting from last hour

        :return list results: a list of time intervals """
        if backwards:
            intervals.reverse()  # first interval is the last working interval of the day
        results = []
        res = timedelta()
        limit = timedelta(hours=hour)
        for interval in intervals:
            res += interval[1] - interval[0]
            if res > limit and not backwards:
                interval = (interval[0], interval[1] + relativedelta(seconds=(limit - res).total_seconds()))
            elif res > limit:
                interval = (interval[0] + relativedelta(seconds=(res - limit).total_seconds()), interval[1])
            results.append(interval)
            if res > limit:
                break
        if backwards:
            results.reverse()  # return interval with increasing starting times
        return results

    # --------------------------------------------------
    # Date and hours computation
    # --------------------------------------------------

    @api.multi
    def _get_day_attendances(self, day_date, start_time, end_time):
        """ Given a day date, return matching attendances. Those can be limited
        by starting and ending time objects. """
        self.ensure_one()
        weekday = day_date.weekday()
        attendances = self.env['resource.calendar.attendance']

        for attendance in self.attendance_ids.filtered(
            lambda att:
                int(att.dayofweek) == weekday and
                not (att.date_from and fields.Date.from_string(att.date_from) > day_date) and
                not (att.date_to and fields.Date.from_string(att.date_to) < day_date)):
            if start_time and float_to_time(attendance.hour_to) < start_time:
                continue
            if end_time and float_to_time(attendance.hour_from) > end_time:
                continue
            attendances |= attendance
        return attendances

    @api.multi
    def _get_weekdays(self):
        """ Return the list of weekdays that contain at least one working
        interval. """
        self.ensure_one()
        return list(set(map(int, (self.attendance_ids.mapped('dayofweek')))))

    @api.multi
    def _get_next_work_day(self, day_date):
        """ Get following date of day_date, based on resource.calendar. """
        self.ensure_one()
        weekdays = self._get_weekdays()
        weekday = next((item for item in weekdays if item > day_date.weekday()), weekdays[0])
        days = weekday - day_date.weekday()
        if days < 0:
            days = 7 + days

        return day_date + relativedelta(days=days)

    @api.multi
    def _get_previous_work_day(self, day_date):
        """ Get previous date of day_date, based on resource.calendar. """
        self.ensure_one()
        weekdays = self._get_weekdays()
        weekdays.reverse()
        weekday = next((item for item in weekdays if item < day_date.weekday()), weekdays[0])
        days = weekday - day_date.weekday()
        if days > 0:
            days = days - 7

        return day_date + relativedelta(days=days)

    @api.multi
    def _get_leave_intervals(self, resource_id=None, start_datetime=None, end_datetime=None):
        """Get the leaves of the calendar. Leaves can be filtered on the resource,
        and on a start and end datetime.

        Leaves are encoded from a given timezone given by their tz field. COnverting
        them in naive user timezone require to use the leave timezone, not the current
        user timezone. For example people managing leaves could be from different
        timezones and the correct one is the one used when encoding them.

        :return list leaves: list of time intervals """
        self.ensure_one()
        if resource_id:
            domain = ['|', ('resource_id', '=', resource_id), ('resource_id', '=', False)]
        else:
            domain = [('resource_id', '=', False)]
        if start_datetime:
            # domain += [('date_to', '>', fields.Datetime.to_string(to_naive_utc(start_datetime, self.env.user)))]
            domain += [('date_to', '>', fields.Datetime.to_string(start_datetime + timedelta(days=-1)))]
        if end_datetime:
            # domain += [('date_from', '<', fields.Datetime.to_string(to_naive_utc(end_datetime, self.env.user)))]
            domain += [('date_from', '<', fields.Datetime.to_string(start_datetime + timedelta(days=1)))]
        leaves = self.env['resource.calendar.leaves'].search(domain + [('calendar_id', '=', self.id)])

        filtered_leaves = self.env['resource.calendar.leaves']
        for leave in leaves:
            if start_datetime:
                leave_date_to = to_tz(fields.Datetime.from_string(leave.date_to), leave.tz)
                if not leave_date_to >= start_datetime:
                    continue
            if end_datetime:
                leave_date_from = to_tz(fields.Datetime.from_string(leave.date_from), leave.tz)
                if not leave_date_from <= end_datetime:
                    continue
            filtered_leaves += leave

        return [self._interval_new(
            to_tz(fields.Datetime.from_string(leave.date_from), leave.tz),
            to_tz(fields.Datetime.from_string(leave.date_to), leave.tz),
            {'leaves': leave}) for leave in filtered_leaves]

    def _iter_day_attendance_intervals(self, day_date, start_time, end_time):
        """ Get an iterator of all interval of current day attendances. """
        for calendar_working_day in self._get_day_attendances(day_date, start_time, end_time):
            from_time = float_to_time(calendar_working_day.hour_from)
            to_time = float_to_time(calendar_working_day.hour_to)

            dt_f = datetime.datetime.combine(day_date, max(from_time, start_time))
            dt_t = datetime.datetime.combine(day_date, min(to_time, end_time))

            yield self._interval_new(dt_f, dt_t, {'attendances': calendar_working_day})

    @api.multi
    def _get_day_work_intervals(self, day_date, start_time=None, end_time=None, compute_leaves=False, resource_id=None):
        """ Get the working intervals of the day given by day_date based on
        current calendar. Input should be given in current user timezone and
        output is given in naive UTC, ready to be used by the orm or webclient.

        :param time start_time: time object that is the beginning hours in user TZ
        :param time end_time: time object that is the ending hours in user TZ
        :param boolean compute_leaves: indicates whether to compute the
                                       leaves based on calendar and resource.
        :param int resource_id: the id of the resource to take into account when
                                computing the work intervals. Leaves notably are
                                filtered according to the resource.

        :return list intervals: list of time intervals in UTC """
        self.ensure_one()

        if not start_time:
            start_time = datetime.time.min
        if not end_time:
            end_time = datetime.time.max

        working_intervals = [att_interval for att_interval in self._iter_day_attendance_intervals(day_date, start_time, end_time)]

        # filter according to leaves
        if compute_leaves:
            leaves = self._get_leave_intervals(
                resource_id=resource_id,
                start_datetime=datetime.datetime.combine(day_date, start_time),
                end_datetime=datetime.datetime.combine(day_date, end_time))
            working_intervals = [
                sub_interval
                for interval in working_intervals
                for sub_interval in self._interval_remove_leaves(interval, leaves)]

        # adapt tz
        return [self._interval_new(
            to_naive_utc(interval[0], self.env.user),
            to_naive_utc(interval[1], self.env.user),
            interval[2]) for interval in working_intervals]

    def _get_day_leave_intervals(self, day_date, start_time, end_time, resource_id):
        """ Get the leave intervals of the day given by day_date based on current
        calendar. Input should be given in current user timezone and
        output is given in naive UTC, ready to be used by the orm or webclient.

        :param time start_time: time object that is the beginning hours in user TZ
        :param time end_time: time object that is the ending hours in user TZ
        :param int resource_id: the id of the resource to take into account when
                                computing the leaves.

        :return list intervals: list of time intervals in UTC """
        self.ensure_one()

        if not start_time:
            start_time = datetime.time.min
        if not end_time:
            end_time = datetime.time.max

        working_intervals = [att_interval for att_interval in self._iter_day_attendance_intervals(day_date, start_time, end_time)]

        leaves_intervals = self._get_leave_intervals(
            resource_id=resource_id,
            start_datetime=datetime.datetime.combine(day_date, start_time),
            end_datetime=datetime.datetime.combine(day_date, end_time))

        final_intervals = [
            self._interval_and(leave_interval, work_interval)
            for leave_interval in leaves_intervals
            for work_interval in working_intervals]

        # adapt tz
        return [self._interval_new(
            to_naive_utc(interval[0], self.env.user),
            to_naive_utc(interval[1], self.env.user),
            interval[2]) for interval in final_intervals]

    # --------------------------------------------------
    # Main computation API
    # --------------------------------------------------

    def _iter_work_intervals(self, start_dt, end_dt, resource_id, compute_leaves=True):
        """ Lists the current resource's work intervals between the two provided
        datetimes (inclusive) expressed in UTC, for each worked day. """
        if not end_dt:
            end_dt = datetime.datetime.combine(start_dt.date(), datetime.time.max)

        start_dt = to_naive_user_tz(start_dt, self.env.user)
        end_dt = to_naive_user_tz(end_dt, self.env.user)

        for day in rrule.rrule(rrule.DAILY,
                               dtstart=start_dt,
                               until=end_dt,
                               byweekday=self._get_weekdays()):
            start_time = day.date() == start_dt.date() and start_dt.time() or datetime.time.min
            end_time = day.date() == end_dt.date() and end_dt.time() or datetime.time.max

            intervals = self._get_day_work_intervals(
                day.date(),
                start_time=start_time,
                end_time=end_time,
                compute_leaves=compute_leaves,
                resource_id=resource_id)
            if intervals:
                yield intervals

    def _iter_leave_intervals(self, start_dt, end_dt, resource_id):
        """ Lists the current resource's leave intervals between the two provided
        datetimes (inclusive) expressed in UTC. """
        if not end_dt:
            end_dt = datetime.datetime.combine(start_dt.date(), datetime.time.max)

        start_dt = to_naive_user_tz(start_dt, self.env.user)
        end_dt = to_naive_user_tz(end_dt, self.env.user)

        for day in rrule.rrule(rrule.DAILY,
                               dtstart=start_dt,
                               until=end_dt,
                               byweekday=self._get_weekdays()):
            start_time = day.date() == start_dt.date() and start_dt.time() or datetime.time.min
            end_time = day.date() == end_dt.date() and end_dt.time() or datetime.time.max

            intervals = self._get_day_leave_intervals(
                day.date(),
                start_time,
                end_time,
                resource_id)

            if intervals:
                yield intervals

    def _iter_work_days(self, from_date, to_date, resource_id):
        """ Lists the current resource's work days between the two provided
        dates (inclusive) expressed in naive UTC.

        Work days are the company or service's open days (as defined by the
        resource.calendar) minus the resource's own leaves.

        :param datetime.date from_date: start of the interval to check for
                                        work days (inclusive)
        :param datetime.date to_date: end of the interval to check for work
                                      days (inclusive)
        :rtype: list(datetime.date)
        """
        for interval in self._iter_work_intervals(
                datetime.datetime(from_date.year, from_date.month, from_date.day),
                datetime.datetime(to_date.year, to_date.month, to_date.day),
                resource_id):
            yield interval[0][0].date()

    @api.multi
    def _is_work_day(self, date, resource_id):
        """ Whether the provided date is a work day for the subject resource.

        :type date: datetime.date
        :rtype: bool """
        return bool(next(self._iter_work_days(date, date, resource_id), False))

    @api.multi
    def get_work_hours_count(self, start_dt, end_dt, resource_id, compute_leaves=True):
        """ Count number of work hours between two datetimes. For compute_leaves,
        resource_id: see _get_day_work_intervals. """
        res = timedelta()
        for intervals in self._iter_work_intervals(start_dt, end_dt, resource_id, compute_leaves=compute_leaves):
            for interval in intervals:
                res += interval[1] - interval[0]
        return res.total_seconds() / 3600.0

    # --------------------------------------------------
    # Scheduling API
    # --------------------------------------------------

    @api.multi
    def _schedule_hours(self, hours, day_dt, compute_leaves=False, resource_id=None):
        """ Schedule hours of work, using a calendar and an optional resource to
        compute working and leave days. This method can be used backwards, i.e.
        scheduling days before a deadline. For compute_leaves, resource_id:
        see _get_day_work_intervals. This method does not use rrule because
        rrule does not allow backwards computation.

        :param int hours: number of hours to schedule. Use a negative number to
                          compute a backwards scheduling.
        :param datetime day_dt: reference date to compute working days. If days is
                                > 0 date is the starting date. If days is < 0
                                date is the ending date.

        :return list intervals: list of time intervals in naive UTC """
        self.ensure_one()
        backwards = (hours < 0)
        intervals = []
        remaining_hours, iterations = abs(hours * 1.0), 0
        current_datetime = day_dt

        call_args = dict(compute_leaves=compute_leaves, resource_id=resource_id)

        while float_compare(remaining_hours, 0.0, precision_digits=2) in (1, 0) and iterations < 1000:
            if backwards:
                call_args['end_time'] = current_datetime.time()
            else:
                call_args['start_time'] = current_datetime.time()

            working_intervals = self._get_day_work_intervals(current_datetime.date(), **call_args)

            if working_intervals:
                new_working_intervals = self._interval_schedule_hours(working_intervals, remaining_hours, backwards=backwards)

                res = timedelta()
                for interval in working_intervals:
                    res += interval[1] - interval[0]
                remaining_hours -= res.total_seconds() / 3600.0

                intervals = intervals + new_working_intervals if not backwards else new_working_intervals + intervals
            # get next day
            if backwards:
                current_datetime = datetime.datetime.combine(self._get_previous_work_day(current_datetime), datetime.time(23, 59, 59))
            else:
                current_datetime = datetime.datetime.combine(self._get_next_work_day(current_datetime), datetime.time())
            # avoid infinite loops
            iterations += 1

        return intervals

    @api.multi
    def plan_hours(self, hours, day_dt, compute_leaves=False, resource_id=None):
        """ Return datetime after having planned hours """
        res = self._schedule_hours(hours, day_dt, compute_leaves, resource_id)
        return res and res[0][0] or False

    @api.multi
    def _schedule_days(self, days, day_dt, compute_leaves=False, resource_id=None):
        """Schedule days of work, using a calendar and an optional resource to
        compute working and leave days. This method can be used backwards, i.e.
        scheduling days before a deadline. For compute_leaves, resource_id:
        see _get_day_work_intervals. This method does not use rrule because
        rrule does not allow backwards computation.

        :param int days: number of days to schedule. Use a negative number to
                         compute a backwards scheduling.
        :param date day_dt: reference datetime to compute working days. If days is > 0
                            date is the starting date. If days is < 0 date is the
                            ending date.

        :return list intervals: list of time intervals in naive UTC """
        backwards = (days < 0)
        intervals = []
        planned_days, iterations = 0, 0
        current_datetime = day_dt.replace(hour=0, minute=0, second=0, microsecond=0)

        while planned_days < abs(days) and iterations < 100:
            working_intervals = self._get_day_work_intervals(
                current_datetime.date(),
                compute_leaves=compute_leaves, resource_id=resource_id)
            if not self or working_intervals:  # no calendar -> no working hours, but day is considered as worked
                planned_days += 1
                intervals += working_intervals
            # get next day
            if backwards:
                current_datetime = self._get_previous_work_day(current_datetime)
            else:
                current_datetime = self._get_next_work_day(current_datetime)
            # avoid infinite loops
            iterations += 1

        return intervals

    @api.multi
    def plan_days(self, days, day_dt, compute_leaves=False, resource_id=None):
        """ Returns the datetime of a days scheduling. """
        res = self._schedule_days(days, day_dt, compute_leaves, resource_id)
        return res and res[-1][1] or False


class ResourceCalendarAttendance(models.Model):
    _name = "resource.calendar.attendance"
    _description = "Work Detail"
    _order = 'dayofweek, hour_from'

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
    hour_from = fields.Float(string='Work from', required=True, index=True, help="Start and End time of working.")
    hour_to = fields.Float(string='Work to', required=True)
    calendar_id = fields.Many2one("resource.calendar", string="Resource's Calendar", required=True, ondelete='cascade')


class ResourceResource(models.Model):
    _name = "resource.resource"
    _description = "Resource Detail"

    @api.model
    def default_get(self, fields):
        res = super(ResourceResource, self).default_get(fields)
        if not res.get('calendar_id') and res.get('company_id'):
            company = self.env['res.company'].browse(res['company_id'])
            res['calendar_id'] = company.resource_calendar_id.id
        return res

    name = fields.Char(required=True)
    active = fields.Boolean(
        'Active', default=True, track_visibility='onchange',
        help="If the active field is set to False, it will allow you to hide the resource record without removing it.")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env['res.company']._company_default_get())
    resource_type = fields.Selection([
        ('user', 'Human'),
        ('material', 'Material')], string='Resource Type',
        default='user', required=True)
    user_id = fields.Many2one('res.users', string='User', help='Related user name for the resource to manage its access.')
    time_efficiency = fields.Float(
        'Efficiency Factor', default=100, required=True,
        help="This field is used to calculate the the expected duration of a work order at this work center. For example, if a work order takes one hour and the efficiency factor is 100%, then the expected duration will be one hour. If the efficiency factor is 200%, however the expected duration will be 30 minutes.")
    calendar_id = fields.Many2one(
        "resource.calendar", string='Working Time',
        default=lambda self: self.env['res.company']._company_default_get().resource_calendar_id,
        required=True,
        help="Define the schedule of resource")

    @api.model
    def create(self, values):
        if values.get('company_id') and not values.get('calendar_id'):
            values['calendar_id'] = self.env['res.company'].browse(values['company_id']).resource_calendar_id.id
        return super(ResourceResource, self).create(values)

    @api.multi
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


class ResourceCalendarLeaves(models.Model):
    _name = "resource.calendar.leaves"
    _description = "Leave Detail"

    name = fields.Char('Reason')
    company_id = fields.Many2one(
        'res.company', related='calendar_id.company_id', string="Company",
        readonly=True, store=True)
    calendar_id = fields.Many2one('resource.calendar', 'Working Hours')
    date_from = fields.Datetime('Start Date', required=True)
    date_to = fields.Datetime('End Date', required=True)
    tz = fields.Selection(
        _tz_get, string='Timezone', default=lambda self: self._context.get('tz', self.env.user.tz),
        help="Timezone used when encoding the leave. It is used to correctly"
             "localize leave hours when computing time intervals.")
    resource_id = fields.Many2one(
        "resource.resource", 'Resource',
        help="If empty, this is a generic holiday for the company. If a resource is set, the holiday/leave is only for this resource")

    @api.constrains('date_from', 'date_to')
    def check_dates(self):
        if self.filtered(lambda leave: leave.date_from > leave.date_to):
            raise ValidationError(_('Error! leave start-date must be lower then leave end-date.'))

    @api.onchange('resource_id')
    def onchange_resource(self):
        if self.resource_id:
            self.calendar_id = self.resource_id.calendar_id
