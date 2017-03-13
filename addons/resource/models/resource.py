# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import pytz

from datetime import timedelta
from dateutil import rrule
from dateutil.relativedelta import relativedelta
from operator import itemgetter

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare


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

    name = fields.Char(required=True)
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env['res.company']._company_default_get())
    attendance_ids = fields.One2many(
        'resource.calendar.attendance', 'calendar_id', string='Working Time',
        copy=True)
    manager = fields.Many2one('res.users', string='Workgroup Manager', default=lambda self: self.env.uid)
    leave_ids = fields.One2many(
        'resource.calendar.leaves', 'calendar_id', string='Leaves')

    # --------------------------------------------------
    # Utility methods
    # --------------------------------------------------

    def interval_clean(self, intervals):
        """ Utility method that sorts and removes overlapping inside datetime
        intervals. The intervals are sorted based on increasing starting datetime.
        Overlapping intervals are merged into a single one.

        :param list intervals: list of intervals; each interval is a tuple
                               (datetime_from, datetime_to)
        :return list cleaned: list of sorted intervals without overlap """
        intervals = sorted(intervals, key=itemgetter(0))  # sort on first datetime
        cleaned = []
        working_interval = None
        while intervals:
            current_interval = intervals.pop(0)
            if not working_interval:  # init
                working_interval = [current_interval[0], current_interval[1]]
            elif working_interval[1] < current_interval[0]:  # interval is disjoint
                cleaned.append(tuple(working_interval))
                working_interval = [current_interval[0], current_interval[1]]
            elif working_interval[1] < current_interval[1]:  # union of greater intervals
                working_interval[1] = current_interval[1]
        if working_interval:  # handle void lists
            cleaned.append(tuple(working_interval))
        return cleaned

    @api.model
    def interval_remove_leaves(self, interval, leave_intervals):
        """ Utility method that remove leave intervals from a base interval:

         - clean the leave intervals, to have an ordered list of not-overlapping
           intervals
         - initiate the current interval to be the base interval
         - for each leave interval:

          - finishing before the current interval: skip, go to next
          - beginning after the current interval: skip and get out of the loop
            because we are outside range (leaves are ordered)
          - beginning within the current interval: close the current interval
            and begin a new current interval that begins at the end of the leave
            interval
          - ending within the current interval: update the current interval begin
            to match the leave interval ending

        :param tuple interval: a tuple (beginning datetime, ending datetime) that
                               is the base interval from which the leave intervals
                               will be removed
        :param list leave_intervals: a list of tuples (beginning datetime, ending datetime)
                                    that are intervals to remove from the base interval
        :return list intervals: a list of tuples (begin datetime, end datetime)
                                that are the remaining valid intervals """
        if not interval:
            return interval
        if leave_intervals is None:
            leave_intervals = []
        intervals = []
        leave_intervals = self.interval_clean(leave_intervals)
        current_interval = [interval[0], interval[1]]
        for leave in leave_intervals:
            if leave[1] <= current_interval[0]:
                continue
            if leave[0] >= current_interval[1]:
                break
            if current_interval[0] < leave[0] < current_interval[1]:
                current_interval[1] = leave[0]
                intervals.append((current_interval[0], current_interval[1]))
                current_interval = [leave[1], interval[1]]
            if current_interval[0] <= leave[1]:
                current_interval[0] = leave[1]
        if current_interval and current_interval[0] < interval[1]:  # remove intervals moved outside base interval due to leaves
            intervals.append((current_interval[0], current_interval[1]))
        return intervals

    def interval_schedule_hours(self, intervals, hour, remove_at_end=True):
        """ Schedule hours in intervals. The last matching interval is truncated
        to match the specified hours.

        It is possible to truncate the last interval at its beginning or ending.
        However this does nothing on the given interval order that should be
        submitted accordingly.

        :param list intervals:  a list of tuples (beginning datetime, ending datetime)
        :param int/float hours: number of hours to schedule. It will be converted
                                into a timedelta, but should be submitted as an
                                int or float.
        :param boolean remove_at_end: remove extra hours at the end of the last
                                      matching interval. Otherwise, do it at the
                                      beginning.

        :return list results: a list of intervals. If the number of hours to schedule
        is greater than the possible scheduling in the intervals, no extra-scheduling
        is done, and results == intervals. """
        results = []
        res = timedelta()
        limit = timedelta(hours=hour)
        for interval in intervals:
            res += interval[1] - interval[0]
            if res > limit and remove_at_end:
                interval = (interval[0], interval[1] + relativedelta(seconds=seconds(limit - res)))
            elif res > limit:
                interval = (interval[0] + relativedelta(seconds=seconds(res - limit)), interval[1])
            results.append(interval)
            if res > limit:
                break
        return results

    # --------------------------------------------------
    # Date and hours computation
    # --------------------------------------------------

    @api.multi
    def get_attendances_for_weekday(self, day_dt):
        """ Given a day datetime, return matching attendances """
        self.ensure_one()
        weekday = day_dt.weekday()
        attendances = self.env['resource.calendar.attendance']

        for attendance in self.attendance_ids.filtered(
            lambda att:
                int(att.dayofweek) == weekday and
                not (att.date_from and fields.Date.from_string(att.date_from) > day_dt.date()) and
                not (att.date_to and fields.Date.from_string(att.date_to) < day_dt.date())):
            attendances |= attendance
        return attendances

    @api.multi
    def get_weekdays(self, default_weekdays=None):
        """ Return the list of weekdays that contain at least one working interval.
        If no id is given (no calendar), return default weekdays. """
        if not self:
            return default_weekdays if default_weekdays is not None else [0, 1, 2, 3, 4]
        self.ensure_one()
        weekdays = set(map(int, (self.attendance_ids.mapped('dayofweek'))))
        return list(weekdays)

    @api.multi
    def get_next_day(self, day_date):
        """ Get following date of day_date, based on resource.calendar. If no
        calendar is provided, just return the next day.

        :param date day_date: current day as a date

        :return date: next day of calendar, or just next day """
        if not self:
            return day_date + relativedelta(days=1)
        self.ensure_one()
        weekdays = self.get_weekdays()

        base_index = -1
        for weekday in weekdays:
            if weekday > day_date.weekday():
                break
            base_index += 1

        new_index = (base_index + 1) % len(weekdays)
        days = (weekdays[new_index] - day_date.weekday())
        if days < 0:
            days = 7 + days

        return day_date + relativedelta(days=days)

    @api.multi
    def get_previous_day(self, day_date):
        """ Get previous date of day_date, based on resource.calendar. If no
        calendar is provided, just return the previous day.

        :param date day_date: current day as a date

        :return date: previous day of calendar, or just previous day """
        if not self:
            return day_date + relativedelta(days=-1)
        self.ensure_one()
        weekdays = self.get_weekdays()
        weekdays.reverse()

        base_index = -1
        for weekday in weekdays:
            if weekday < day_date.weekday():
                break
            base_index += 1

        new_index = (base_index + 1) % len(weekdays)
        days = (weekdays[new_index] - day_date.weekday())
        if days > 0:
            days = days - 7

        return day_date + relativedelta(days=days)

    @api.multi
    def get_leave_intervals(self, resource_id=None,
                            start_datetime=None, end_datetime=None):
        """Get the leaves of the calendar. Leaves can be filtered on the resource,
        the start datetime or the end datetime.

        :param int resource_id: the id of the resource to take into account when
                                computing the leaves. If not set, only general
                                leaves are computed. If set, generic and
                                specific leaves are computed.
        :param datetime start_datetime: if provided, do not take into account leaves
                                        ending before this date.
        :param datetime end_datetime: if provided, do not take into account leaves
                                        beginning after this date.

        :return list leaves: list of tuples (start_datetime, end_datetime) of
                             leave intervals
        """
        self.ensure_one()
        leaves = []
        for leave in self.leave_ids:
            if leave.resource_id and not resource_id == leave.resource_id.id:
                continue
            date_from = fields.Datetime.from_string(leave.date_from)
            if end_datetime and date_from > end_datetime:
                continue
            date_to = fields.Datetime.from_string(leave.date_to)
            if start_datetime and date_to < start_datetime:
                continue
            leaves.append((date_from, date_to))
        return leaves

    @api.multi
    def get_working_intervals_of_day(self, start_dt=None, end_dt=None,
                                     leaves=None, compute_leaves=False, resource_id=None,
                                     default_interval=None):
        """ Get the working intervals of the day based on calendar. This method
        handle leaves that come directly from the leaves parameter or can be computed.

        :param datetime start_dt: datetime object that is the beginning hours
                                  for the working intervals computation; any
                                  working interval beginning before start_dt
                                  will be truncated. If not set, set to end_dt
                                  or today() if no end_dt at 00.00.00.
        :param datetime end_dt: datetime object that is the ending hour
                                for the working intervals computation; any
                                working interval ending after end_dt
                                will be truncated. If not set, set to start_dt()
                                at 23.59.59.
        :param list leaves: a list of tuples(start_datetime, end_datetime) that
                            represent leaves.
        :param boolean compute_leaves: if set and if leaves is None, compute the
                                       leaves based on calendar and resource.
                                       If leaves is None and compute_leaves false
                                       no leaves are taken into account.
        :param int resource_id: the id of the resource to take into account when
                                computing the leaves. If not set, only general
                                leaves are computed. If set, generic and
                                specific leaves are computed.
        :param tuple default_interval: if no id, try to return a default working
                                       day using default_interval[0] as beginning
                                       hour, and default_interval[1] as ending hour.
                                       Example: default_interval = (8, 16).
                                       Otherwise, a void list of working intervals
                                       is returned when id is None.

        :return list intervals: a list of tuples (start_datetime, end_datetime)
                                of work intervals """

        # Computes start_dt, end_dt (with default values if not set) + off-interval work limits
        work_limits = []
        if start_dt is None and end_dt is not None:
            start_dt = end_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        elif start_dt is None:
            start_dt = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            work_limits.append((start_dt.replace(hour=0, minute=0, second=0, microsecond=0), start_dt))
        if end_dt is None:
            end_dt = start_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        else:
            work_limits.append((end_dt, end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)))
        assert start_dt.date() == end_dt.date(), 'get_working_intervals_of_day is restricted to one day'

        intervals = []
        work_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)

        # no calendar: try to use the default_interval, then return directly
        if not self:
            working_interval = []
            if default_interval:
                working_interval = (start_dt.replace(hour=default_interval[0], minute=0, second=0, microsecond=0),
                                    start_dt.replace(hour=default_interval[1], minute=0, second=0, microsecond=0))
            intervals = self.interval_remove_leaves(working_interval, work_limits)
            return intervals

        working_intervals = []
        tz_info = fields.Datetime.context_timestamp(self, work_dt).tzinfo
        for calendar_working_day in self.get_attendances_for_weekday(start_dt):
            dt_f = work_dt.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(seconds=(calendar_working_day.hour_from * 3600))
            dt_t = work_dt.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(seconds=(calendar_working_day.hour_to * 3600))

            # adapt tz
            working_interval = (
                dt_f.replace(tzinfo=tz_info).astimezone(pytz.UTC).replace(tzinfo=None),
                dt_t.replace(tzinfo=tz_info).astimezone(pytz.UTC).replace(tzinfo=None),
                calendar_working_day.id
            )
            working_intervals += self.interval_remove_leaves(working_interval, work_limits)

        # find leave intervals
        if leaves is None and compute_leaves:
            leaves = self.get_leave_intervals(resource_id=resource_id)

        # filter according to leaves
        for interval in working_intervals:
            work_intervals = self.interval_remove_leaves(interval, leaves)
            intervals += work_intervals

        return intervals

    @api.multi
    def get_working_hours_of_date(self, start_dt=None, end_dt=None,
                                  leaves=None, compute_leaves=False, resource_id=None,
                                  default_interval=None):
        """ Get the working hours of the day based on calendar. This method uses
        get_working_intervals_of_day to have the work intervals of the day. It
        then calculates the number of hours contained in those intervals. """
        res = timedelta()
        intervals = self.get_working_intervals_of_day(
            start_dt, end_dt, leaves,
            compute_leaves, resource_id,
            default_interval)
        for interval in intervals:
            res += interval[1] - interval[0]
        return seconds(res) / 3600.0

    @api.multi
    def get_working_hours(self, start_dt, end_dt, compute_leaves=False,
                          resource_id=None, default_interval=None):
        hours = 0.0
        for day in rrule.rrule(rrule.DAILY, dtstart=start_dt,
                               until=(end_dt + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0),
                               byweekday=self.get_weekdays()):
            day_start_dt = day.replace(hour=0, minute=0, second=0, microsecond=0)
            if start_dt and day.date() == start_dt.date():
                day_start_dt = start_dt
            day_end_dt = day.replace(hour=23, minute=59, second=59, microsecond=999999)
            if end_dt and day.date() == end_dt.date():
                day_end_dt = end_dt
            hours += self.get_working_hours_of_date(
                start_dt=day_start_dt, end_dt=day_end_dt,
                compute_leaves=compute_leaves, resource_id=resource_id,
                default_interval=default_interval)
        return hours

    # --------------------------------------------------
    # Hours scheduling
    # --------------------------------------------------

    @api.multi
    def _schedule_hours(self, hours, day_dt=None,
                        compute_leaves=False, resource_id=None,
                        default_interval=None):
        """ Schedule hours of work, using a calendar and an optional resource to
        compute working and leave days. This method can be used backwards, i.e.
        scheduling days before a deadline.

        :param int hours: number of hours to schedule. Use a negative number to
                          compute a backwards scheduling.
        :param datetime day_dt: reference date to compute working days. If days is
                                > 0 date is the starting date. If days is < 0
                                date is the ending date.
        :param boolean compute_leaves: if set, compute the leaves based on calendar
                                       and resource. Otherwise no leaves are taken
                                       into account.
        :param int resource_id: the id of the resource to take into account when
                                computing the leaves. If not set, only general
                                leaves are computed. If set, generic and
                                specific leaves are computed.
        :param tuple default_interval: if no id, try to return a default working
                                       day using default_interval[0] as beginning
                                       hour, and default_interval[1] as ending hour.
                                       Example: default_interval = (8, 16).
                                       Otherwise, a void list of working intervals
                                       is returned when id is None.

        :return tuple (datetime, intervals): datetime is the beginning/ending date
                                             of the schedulign; intervals are the
                                             working intervals of the scheduling.

        Note: Why not using rrule.rrule ? Because rrule does not seem to allow
        getting back in time.
        """
        if day_dt is None:
            day_dt = datetime.datetime.now()
        backwards = (hours < 0)
        hours = abs(hours)
        intervals = []
        remaining_hours = hours * 1.0
        iterations = 0
        current_datetime = day_dt

        call_args = dict(compute_leaves=compute_leaves, resource_id=resource_id, default_interval=default_interval)

        while float_compare(remaining_hours, 0.0, precision_digits=2) in (1, 0) and iterations < 1000:
            if backwards:
                call_args['end_dt'] = current_datetime
            else:
                call_args['start_dt'] = current_datetime

            working_intervals = self.get_working_intervals_of_day(**call_args)

            if not self and not working_intervals:  # no calendar -> consider working 8 hours
                remaining_hours -= 8.0
            elif working_intervals:
                if backwards:
                    working_intervals.reverse()
                new_working_intervals = self.interval_schedule_hours(working_intervals, remaining_hours, not backwards)
                if backwards:
                    new_working_intervals.reverse()

                res = timedelta()
                for interval in working_intervals:
                    res += interval[1] - interval[0]
                remaining_hours -= (seconds(res) / 3600.0)
                if backwards:
                    intervals = new_working_intervals + intervals
                else:
                    intervals = intervals + new_working_intervals
            # get next day
            if backwards:
                current_datetime = datetime.datetime.combine(self.get_previous_day(current_datetime), datetime.time(23, 59, 59))
            else:
                current_datetime = datetime.datetime.combine(self.get_next_day(current_datetime), datetime.time())
            # avoid infinite loops
            iterations += 1

        return intervals

    @api.multi
    def schedule_hours_get_date(self, hours, day_dt=None,
                                compute_leaves=False, resource_id=None,
                                default_interval=None):
        """ Wrapper on _schedule_hours: return the beginning/ending datetime of
        an hours scheduling. """
        res = self._schedule_hours(hours, day_dt, compute_leaves, resource_id, default_interval)
        return res and res[0][0] or False

    @api.multi
    def schedule_hours(self, hours, day_dt=None,
                       compute_leaves=False, resource_id=None,
                       default_interval=None):
        """ Wrapper on _schedule_hours: return the working intervals of an hours
        scheduling. """
        return self._schedule_hours(hours, day_dt, compute_leaves, resource_id, default_interval)

    # --------------------------------------------------
    # Days scheduling
    # --------------------------------------------------

    @api.multi
    def _schedule_days(self, days, day_date=None, compute_leaves=False,
                       resource_id=None, default_interval=None):
        """Schedule days of work, using a calendar and an optional resource to
        compute working and leave days. This method can be used backwards, i.e.
        scheduling days before a deadline.

        :param int days: number of days to schedule. Use a negative number to
                         compute a backwards scheduling.
        :param date day_date: reference date to compute working days. If days is > 0
                              date is the starting date. If days is < 0 date is the
                              ending date.
        :param boolean compute_leaves: if set, compute the leaves based on calendar
                                       and resource. Otherwise no leaves are taken
                                       into account.
        :param int resource_id: the id of the resource to take into account when
                                computing the leaves. If not set, only general
                                leaves are computed. If set, generic and
                                specific leaves are computed.
        :param tuple default_interval: if no id, try to return a default working
                                       day using default_interval[0] as beginning
                                       hour, and default_interval[1] as ending hour.
                                       Example: default_interval = (8, 16).
                                       Otherwise, a void list of working intervals
                                       is returned when id is None.

        :return tuple (datetime, intervals): datetime is the beginning/ending date
                                             of the schedulign; intervals are the
                                             working intervals of the scheduling.

        Implementation note: rrule.rrule is not used because rrule it des not seem
        to allow getting back in time.
        """
        if day_date is None:
            day_date = datetime.datetime.now()
        backwards = (days < 0)
        days = abs(days)
        intervals = []
        planned_days = 0
        iterations = 0
        current_datetime = day_date.replace(hour=0, minute=0, second=0, microsecond=0)

        while planned_days < days and iterations < 100:
            working_intervals = self.get_working_intervals_of_day(
                current_datetime,
                compute_leaves=compute_leaves, resource_id=resource_id,
                default_interval=default_interval)
            if not self or working_intervals:  # no calendar -> no working hours, but day is considered as worked
                planned_days += 1
                intervals += working_intervals
            # get next day
            if backwards:
                current_datetime = self.get_previous_day(current_datetime)
            else:
                current_datetime = self.get_next_day(current_datetime)
            # avoid infinite loops
            iterations += 1

        return intervals

    @api.multi
    def schedule_days_get_date(self, days, day_date=None, compute_leaves=False,
                               resource_id=None, default_interval=None):
        """ Wrapper on _schedule_days: return the beginning/ending datetime of
        a days scheduling. """
        res = self._schedule_days(days, day_date, compute_leaves, resource_id, default_interval)
        return res and res[-1][1] or False

    @api.multi
    def schedule_days(self, days, day_date=None, compute_leaves=False,
                      resource_id=None, default_interval=None):
        """ Wrapper on _schedule_days: return the working intervals of a days
        scheduling. """
        return self._schedule_days(days, day_date, compute_leaves, resource_id, default_interval)

    # --------------------------------------------------
    # Compatibility / to clean / to remove
    # --------------------------------------------------

    @api.multi
    def working_hours_on_day(self, day):
        """ Used in hr_payroll/hr_payroll.py

        :deprecated: Odoo saas-3. Use get_working_hours_of_date instead. Note:
        since saas-3, take hour/minutes into account, not just the whole day."""
        if isinstance(day, datetime.datetime):
            day = day.replace(hour=0, minute=0)
        return self.get_working_hours_of_date(start_dt=day)

    @api.multi
    def interval_min_get(self, dt_from, hours, resource=False):
        """ Schedule hours backwards. Used in mrp_operations/mrp_operations.py.

        :deprecated: Odoo saas-3. Use schedule_hours instead. Note: since
        saas-3, counts leave hours instead of all-day leaves."""
        return self.schedule_hours(
            hours * -1.0,
            day_dt=dt_from.replace(minute=0, second=0, microsecond=0),
            compute_leaves=True, resource_id=resource,
            default_interval=(8, 16)
        )

    @api.model
    def interval_get_multi(self, date_and_hours_by_cal, resource=False, byday=True):
        """ Used in mrp_operations/mrp_operations.py (default parameters) and in
        interval_get()

        :deprecated: Odoo saas-3. Use schedule_hours instead. Note:
        Byday was not used. Since saas-3, counts Leave hours instead of all-day leaves."""
        res = {}
        for dt_str, hours, calendar_id in date_and_hours_by_cal:
            result = self.browse(calendar_id).schedule_hours(
                hours,
                day_dt=fields.Datetime.from_string(dt_str).replace(second=0),
                compute_leaves=True, resource_id=resource,
                default_interval=(8, 16)
            )
            res[(dt_str, hours, calendar_id)] = result
        return res

    @api.multi
    def interval_get(self, dt_from, hours, resource=False, byday=True):
        """ Unifier of interval_get_multi. Used in: mrp_operations/mrp_operations.py,
        crm/crm_lead.py (res given).

        :deprecated: Odoo saas-3. Use get_working_hours instead."""
        self.ensure_one()
        res = self.interval_get_multi(
            [(fields.Datetime.to_string(dt_from), hours, self.id)], resource, byday)[(fields.Datetime.to_string(dt_from), hours, self.id)]
        return res

    @api.multi
    def interval_hours_get(self, dt_from, dt_to, resource=False):
        """ Unused wrapper.

        :deprecated: Odoo saas-3. Use get_working_hours instead."""
        return self._interval_hours_get(dt_from, dt_to, resource_id=resource)

    @api.multi
    def _interval_hours_get(self, dt_from, dt_to, resource_id=False, timezone_from_uid=None, exclude_leaves=True):
        """ Computes working hours between two dates, taking always same hour/minuts.
        :deprecated: Odoo saas-3. Use get_working_hours instead. Note: since saas-3,
        now resets hour/minuts. Now counts leave hours instead of all-day leaves."""
        return self.get_working_hours(
            dt_from, dt_to,
            compute_leaves=(not exclude_leaves), resource_id=resource_id,
            default_interval=(8, 16))


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


def hours_time_string(hours):
    """ convert a number of hours (float) into a string with format '%H:%M' """
    minutes = int(round(hours * 60))
    return "%02d:%02d" % divmod(minutes, 60)


class ResourceResource(models.Model):
    _name = "resource.resource"
    _description = "Resource Detail"

    name = fields.Char(required=True)
    code = fields.Char(copy=False)
    active = fields.Boolean(track_visibility='onchange', default=True,
        help="If the active field is set to False, it will allow you to hide the resource record without removing it.")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env['res.company']._company_default_get())
    resource_type = fields.Selection([
        ('user', 'Human'),
        ('material', 'Material')
        ], string='Resource Type', required=True, default='user')
    user_id = fields.Many2one('res.users', string='User', help='Related user name for the resource to manage its access.')
    time_efficiency = fields.Float(string='Efficiency Factor', required=True, default=100,
        help="This field is used to calculate the the expected duration of a work order at this work center. For example, if a work order takes one hour and the efficiency factor is 100%, then the expected duration will be one hour. If the efficiency factor is 200%, however the expected duration will be 30 minutes.")
    calendar_id = fields.Many2one("resource.calendar", string='Working Time', help="Define the schedule of resource")

    @api.multi
    def copy(self, default=None):
        self.ensure_one()
        if default is None:
            default = {}
        if not default.get('name'):
            default.update(name=_('%s (copy)') % (self.name))
        return super(ResourceResource, self).copy(default)

    def _is_work_day(self, date):
        """ Whether the provided date is a work day for the subject resource.

        :type date: datetime.date
        :rtype: bool
        """
        return bool(next(self._iter_work_days(date, date), False))

    def _iter_work_days(self, from_date, to_date):
        """ Lists the current resource's work days between the two provided
        dates (inclusive).

        Work days are the company or service's open days (as defined by the
        resource.calendar) minus the resource's own leaves.

        :param datetime.date from_date: start of the interval to check for
                                        work days (inclusive)
        :param datetime.date to_date: end of the interval to check for work
                                      days (inclusive)
        :rtype: list(datetime.date)
        """
        working_intervals = self.calendar_id.get_working_intervals_of_day
        # rrule coerces date inputs to datetimes (with time=0) and yields
        # datetimes (with time=0 if freq >= daily)
        for dt in rrule.rrule(rrule.DAILY, dtstart=from_date, until=to_date):
            intervals = working_intervals(dt, compute_leaves=True, resource_id=self.id)

            # FIXME: get_working_intervals is new-API mapped to return a list of lists of intervals
            if intervals and intervals[0]:
                yield dt.date()

class ResourceCalendarLeaves(models.Model):
    _name = "resource.calendar.leaves"
    _description = "Leave Detail"

    name = fields.Char()
    company_id = fields.Many2one('res.company', related='calendar_id.company_id', string="Company", store=True, readonly=True)
    calendar_id = fields.Many2one('resource.calendar', string='Working Time')
    date_from = fields.Datetime(string='Start Date', required=True)
    date_to = fields.Datetime(string='End Date', required=True)
    resource_id = fields.Many2one("resource.resource", string='Resource',
        help="If empty, this is a generic holiday for the company. If a resource is set, the holiday/leave is only for this resource")

    @api.constrains('date_from', 'date_to')
    def check_dates(self):
        if self.filtered(lambda leave: leave.date_from > leave.date_to):
            raise ValidationError(_('Error! leave start-date must be lower then leave end-date.'))

    @api.onchange('resource_id')
    def onchange_resource(self):
        self.calendar_id = self.resource_id.calendar_id

def seconds(td):
    assert isinstance(td, timedelta)

    return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10.**6
