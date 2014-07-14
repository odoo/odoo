# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-TODAY OpenERP SA (http://www.openerp.com)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import datetime
from dateutil import rrule
from dateutil.relativedelta import relativedelta
from operator import itemgetter

from openerp import tools
from openerp.osv import fields, osv
from openerp.tools.float_utils import float_compare
from openerp.tools.translate import _

class resource_calendar(osv.osv):
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

    _columns = {
        'name': fields.char("Name", required=True),
        'company_id': fields.many2one('res.company', 'Company', required=False),
        'attendance_ids': fields.one2many('resource.calendar.attendance', 'calendar_id', 'Working Time', copy=True),
        'manager': fields.many2one('res.users', 'Workgroup Manager'),
        'leave_ids': fields.one2many(
            'resource.calendar.leaves', 'calendar_id', 'Leaves',
            help=''
        ),
    }
    _defaults = {
        'company_id': lambda self, cr, uid, context: self.pool.get('res.company')._company_default_get(cr, uid, 'resource.calendar', context=context)
    }

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
            # if current_interval[0] <= leave[1] <= current_interval[1]:
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
        res = datetime.timedelta()
        limit = datetime.timedelta(hours=hour)
        for interval in intervals:
            res += interval[1] - interval[0]
            if res > limit and remove_at_end:
                interval = (interval[0], interval[1] + relativedelta(seconds=seconds(limit-res)))
            elif res > limit:
                interval = (interval[0] + relativedelta(seconds=seconds(res-limit)), interval[1])
            results.append(interval)
            if res > limit:
                break
        return results

    # --------------------------------------------------
    # Date and hours computation
    # --------------------------------------------------

    def get_attendances_for_weekdays(self, cr, uid, id, weekdays, context=None):
        """ Given a list of weekdays, return matching resource.calendar.attendance"""
        calendar = self.browse(cr, uid, id, context=None)
        return [att for att in calendar.attendance_ids if int(att.dayofweek) in weekdays]

    def get_weekdays(self, cr, uid, id, default_weekdays=None, context=None):
        """ Return the list of weekdays that contain at least one working interval.
        If no id is given (no calendar), return default weekdays. """
        if id is None:
            return default_weekdays if default_weekdays is not None else [0, 1, 2, 3, 4]
        calendar = self.browse(cr, uid, id, context=None)
        weekdays = set()
        for attendance in calendar.attendance_ids:
            weekdays.add(int(attendance.dayofweek))
        return list(weekdays)

    def get_next_day(self, cr, uid, id, day_date, context=None):
        """ Get following date of day_date, based on resource.calendar. If no
        calendar is provided, just return the next day.

        :param int id: id of a resource.calendar. If not given, simply add one day
                       to the submitted date.
        :param date day_date: current day as a date

        :return date: next day of calendar, or just next day """
        if not id:
            return day_date + relativedelta(days=1)
        weekdays = self.get_weekdays(cr, uid, id, context)

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

    def get_previous_day(self, cr, uid, id, day_date, context=None):
        """ Get previous date of day_date, based on resource.calendar. If no
        calendar is provided, just return the previous day.

        :param int id: id of a resource.calendar. If not given, simply remove
                       one day from the submitted date.
        :param date day_date: current day as a date

        :return date: previous day of calendar, or just previous day """
        if not id:
            return day_date + relativedelta(days=-1)
        weekdays = self.get_weekdays(cr, uid, id, context)
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

    def get_leave_intervals(self, cr, uid, id, resource_id=None,
                            start_datetime=None, end_datetime=None,
                            context=None):
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
        resource_calendar = self.browse(cr, uid, id, context=context)
        leaves = []
        for leave in resource_calendar.leave_ids:
            if leave.resource_id and not resource_id == leave.resource_id.id:
                continue
            date_from = datetime.datetime.strptime(leave.date_from, tools.DEFAULT_SERVER_DATETIME_FORMAT)
            if end_datetime and date_from > end_datetime:
                continue
            date_to = datetime.datetime.strptime(leave.date_to, tools.DEFAULT_SERVER_DATETIME_FORMAT)
            if start_datetime and date_to < start_datetime:
                continue
            leaves.append((date_from, date_to))
        return leaves

    def get_working_intervals_of_day(self, cr, uid, id, start_dt=None, end_dt=None,
                                     leaves=None, compute_leaves=False, resource_id=None,
                                     default_interval=None, context=None):
        """ Get the working intervals of the day based on calendar. This method
        handle leaves that come directly from the leaves parameter or can be computed.

        :param int id: resource.calendar id; take the first one if is a list
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
        if isinstance(id, (list, tuple)):
            id = id[0]

        # Computes start_dt, end_dt (with default values if not set) + off-interval work limits
        work_limits = []
        if start_dt is None and end_dt is not None:
            start_dt = end_dt.replace(hour=0, minute=0, second=0)
        elif start_dt is None:
            start_dt = datetime.datetime.now().replace(hour=0, minute=0, second=0)
        else:
            work_limits.append((start_dt.replace(hour=0, minute=0, second=0), start_dt))
        if end_dt is None:
            end_dt = start_dt.replace(hour=23, minute=59, second=59)
        else:
            work_limits.append((end_dt, end_dt.replace(hour=23, minute=59, second=59)))
        assert start_dt.date() == end_dt.date(), 'get_working_intervals_of_day is restricted to one day'

        intervals = []
        work_dt = start_dt.replace(hour=0, minute=0, second=0)

        # no calendar: try to use the default_interval, then return directly
        if id is None:
            if default_interval:
                intervals.append((start_dt.replace(hour=default_interval[0]), start_dt.replace(hour=default_interval[1])))
            return intervals

        working_intervals = []
        for calendar_working_day in self.get_attendances_for_weekdays(cr, uid, id, [start_dt.weekday()], context):
            working_interval = (
                work_dt.replace(hour=int(calendar_working_day.hour_from)),
                work_dt.replace(hour=int(calendar_working_day.hour_to))
            )
            working_intervals += self.interval_remove_leaves(working_interval, work_limits)

        # find leave intervals
        if leaves is None and compute_leaves:
            leaves = self.get_leave_intervals(cr, uid, id, resource_id=resource_id, context=None)

        # filter according to leaves
        for interval in working_intervals:
            work_intervals = self.interval_remove_leaves(interval, leaves)
            intervals += work_intervals

        return intervals

    def get_working_hours_of_date(self, cr, uid, id, start_dt=None, end_dt=None,
                                  leaves=None, compute_leaves=False, resource_id=None,
                                  default_interval=None, context=None):
        """ Get the working hours of the day based on calendar. This method uses
        get_working_intervals_of_day to have the work intervals of the day. It
        then calculates the number of hours contained in those intervals. """
        res = datetime.timedelta()
        intervals = self.get_working_intervals_of_day(
            cr, uid, id,
            start_dt, end_dt, leaves,
            compute_leaves, resource_id,
            default_interval, context)
        for interval in intervals:
            res += interval[1] - interval[0]
        return seconds(res) / 3600.0

    def get_working_hours(self, cr, uid, id, start_dt, end_dt, compute_leaves=False,
                          resource_id=None, default_interval=None, context=None):
        hours = 0.0
        for day in rrule.rrule(rrule.DAILY, dtstart=start_dt,
                               until=end_dt + datetime.timedelta(days=1),
                               byweekday=self.get_weekdays(cr, uid, id, context=context)):
            hours += self.get_working_hours_of_date(
                cr, uid, id, start_dt=day,
                compute_leaves=compute_leaves, resource_id=resource_id,
                default_interval=default_interval,
                context=context)
        return hours

    # --------------------------------------------------
    # Hours scheduling
    # --------------------------------------------------

    def _schedule_hours(self, cr, uid, id, hours, day_dt=None,
                        compute_leaves=False, resource_id=None,
                        default_interval=None, context=None):
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

        call_args = dict(compute_leaves=compute_leaves, resource_id=resource_id, default_interval=default_interval, context=context)

        while float_compare(remaining_hours, 0.0, precision_digits=2) in (1, 0) and iterations < 1000:
            if backwards:
                call_args['end_dt'] = current_datetime
            else:
                call_args['start_dt'] = current_datetime

            working_intervals = self.get_working_intervals_of_day(cr, uid, id, **call_args)

            if id is None and not working_intervals:  # no calendar -> consider working 8 hours
                remaining_hours -= 8.0
            elif working_intervals:
                if backwards:
                    working_intervals.reverse()
                new_working_intervals = self.interval_schedule_hours(working_intervals, remaining_hours, not backwards)
                if backwards:
                    new_working_intervals.reverse()

                res = datetime.timedelta()
                for interval in working_intervals:
                    res += interval[1] - interval[0]
                remaining_hours -= (seconds(res) / 3600.0)
                if backwards:
                    intervals = new_working_intervals + intervals
                else:
                    intervals = intervals + new_working_intervals
            # get next day
            if backwards:
                current_datetime = datetime.datetime.combine(self.get_previous_day(cr, uid, id, current_datetime, context), datetime.time(23, 59, 59))
            else:
                current_datetime = datetime.datetime.combine(self.get_next_day(cr, uid, id, current_datetime, context), datetime.time())
            # avoid infinite loops
            iterations += 1

        return intervals

    def schedule_hours_get_date(self, cr, uid, id, hours, day_dt=None,
                                compute_leaves=False, resource_id=None,
                                default_interval=None, context=None):
        """ Wrapper on _schedule_hours: return the beginning/ending datetime of
        an hours scheduling. """
        res = self._schedule_hours(cr, uid, id, hours, day_dt, compute_leaves, resource_id, default_interval, context)
        return res and res[0][0] or False

    def schedule_hours(self, cr, uid, id, hours, day_dt=None,
                       compute_leaves=False, resource_id=None,
                       default_interval=None, context=None):
        """ Wrapper on _schedule_hours: return the working intervals of an hours
        scheduling. """
        return self._schedule_hours(cr, uid, id, hours, day_dt, compute_leaves, resource_id, default_interval, context)

    # --------------------------------------------------
    # Days scheduling
    # --------------------------------------------------

    def _schedule_days(self, cr, uid, id, days, day_date=None, compute_leaves=False,
                       resource_id=None, default_interval=None, context=None):
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
        if backwards:
            current_datetime = day_date.replace(hour=23, minute=59, second=59)
        else:
            current_datetime = day_date.replace(hour=0, minute=0, second=0)

        while planned_days < days and iterations < 1000:
            working_intervals = self.get_working_intervals_of_day(
                cr, uid, id, current_datetime,
                compute_leaves=compute_leaves, resource_id=resource_id,
                default_interval=default_interval,
                context=context)
            if id is None or working_intervals:  # no calendar -> no working hours, but day is considered as worked
                planned_days += 1
                intervals += working_intervals
            # get next day
            if backwards:
                current_datetime = self.get_previous_day(cr, uid, id, current_datetime, context)
            else:
                current_datetime = self.get_next_day(cr, uid, id, current_datetime, context)
            # avoid infinite loops
            iterations += 1

        return intervals

    def schedule_days_get_date(self, cr, uid, id, days, day_date=None, compute_leaves=False,
                               resource_id=None, default_interval=None, context=None):
        """ Wrapper on _schedule_days: return the beginning/ending datetime of
        a days scheduling. """
        res = self._schedule_days(cr, uid, id, days, day_date, compute_leaves, resource_id, default_interval, context)
        return res and res[-1][1] or False

    def schedule_days(self, cr, uid, id, days, day_date=None, compute_leaves=False,
                      resource_id=None, default_interval=None, context=None):
        """ Wrapper on _schedule_days: return the working intervals of a days
        scheduling. """
        return self._schedule_days(cr, uid, id, days, day_date, compute_leaves, resource_id, default_interval, context)

    # --------------------------------------------------
    # Compatibility / to clean / to remove
    # --------------------------------------------------

    def working_hours_on_day(self, cr, uid, resource_calendar_id, day, context=None):
        """ Used in hr_payroll/hr_payroll.py

        :deprecated: OpenERP saas-3. Use get_working_hours_of_date instead. Note:
        since saas-3, take hour/minutes into account, not just the whole day."""
        if isinstance(day, datetime.datetime):
            day = day.replace(hour=0, minute=0)
        return self.get_working_hours_of_date(cr, uid, resource_calendar_id.id, start_dt=day, context=None)

    def interval_min_get(self, cr, uid, id, dt_from, hours, resource=False):
        """ Schedule hours backwards. Used in mrp_operations/mrp_operations.py.

        :deprecated: OpenERP saas-3. Use schedule_hours instead. Note: since
        saas-3, counts leave hours instead of all-day leaves."""
        return self.schedule_hours(
            cr, uid, id, hours * -1.0,
            day_dt=dt_from.replace(minute=0, second=0),
            compute_leaves=True, resource_id=resource,
            default_interval=(8, 16)
        )

    def interval_get_multi(self, cr, uid, date_and_hours_by_cal, resource=False, byday=True):
        """ Used in mrp_operations/mrp_operations.py (default parameters) and in
        interval_get()

        :deprecated: OpenERP saas-3. Use schedule_hours instead. Note:
        Byday was not used. Since saas-3, counts Leave hours instead of all-day leaves."""
        res = {}
        for dt_str, hours, calendar_id in date_and_hours_by_cal:
            result = self.schedule_hours(
                cr, uid, calendar_id, hours,
                day_dt=datetime.datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S').replace(minute=0, second=0),
                compute_leaves=True, resource_id=resource,
                default_interval=(8, 16)
            )
            res[(dt_str, hours, calendar_id)] = result
        return res

    def interval_get(self, cr, uid, id, dt_from, hours, resource=False, byday=True):
        """ Unifier of interval_get_multi. Used in: mrp_operations/mrp_operations.py,
        crm/crm_lead.py (res given).

        :deprecated: OpenERP saas-3. Use get_working_hours instead."""
        res = self.interval_get_multi(
            cr, uid, [(dt_from.strftime('%Y-%m-%d %H:%M:%S'), hours, id)], resource, byday)[(dt_from.strftime('%Y-%m-%d %H:%M:%S'), hours, id)]
        return res

    def interval_hours_get(self, cr, uid, id, dt_from, dt_to, resource=False):
        """ Unused wrapper.

        :deprecated: OpenERP saas-3. Use get_working_hours instead."""
        return self._interval_hours_get(cr, uid, id, dt_from, dt_to, resource_id=resource)

    def _interval_hours_get(self, cr, uid, id, dt_from, dt_to, resource_id=False, timezone_from_uid=None, exclude_leaves=True, context=None):
        """ Computes working hours between two dates, taking always same hour/minuts.

        :deprecated: OpenERP saas-3. Use get_working_hours instead. Note: since saas-3,
        now resets hour/minuts. Now counts leave hours instead of all-day leaves."""
        return self.get_working_hours(
            cr, uid, id, dt_from, dt_to,
            compute_leaves=(not exclude_leaves), resource_id=resource_id,
            default_interval=(8, 16), context=context)


class resource_calendar_attendance(osv.osv):
    _name = "resource.calendar.attendance"
    _description = "Work Detail"

    _columns = {
        'name' : fields.char("Name", required=True),
        'dayofweek': fields.selection([('0','Monday'),('1','Tuesday'),('2','Wednesday'),('3','Thursday'),('4','Friday'),('5','Saturday'),('6','Sunday')], 'Day of Week', required=True, select=True),
        'date_from' : fields.date('Starting Date'),
        'hour_from' : fields.float('Work from', required=True, help="Start and End time of working.", select=True),
        'hour_to' : fields.float("Work to", required=True),
        'calendar_id' : fields.many2one("resource.calendar", "Resource's Calendar", required=True),
    }

    _order = 'dayofweek, hour_from'

    _defaults = {
        'dayofweek' : '0'
    }

def hours_time_string(hours):
    """ convert a number of hours (float) into a string with format '%H:%M' """
    minutes = int(round(hours * 60))
    return "%02d:%02d" % divmod(minutes, 60)

class resource_resource(osv.osv):
    _name = "resource.resource"
    _description = "Resource Detail"
    _columns = {
        'name': fields.char("Name", required=True),
        'code': fields.char('Code', size=16, copy=False),
        'active' : fields.boolean('Active', help="If the active field is set to False, it will allow you to hide the resource record without removing it."),
        'company_id' : fields.many2one('res.company', 'Company'),
        'resource_type': fields.selection([('user','Human'),('material','Material')], 'Resource Type', required=True),
        'user_id' : fields.many2one('res.users', 'User', help='Related user name for the resource to manage its access.'),
        'time_efficiency' : fields.float('Efficiency Factor', size=8, required=True, help="This field depict the efficiency of the resource to complete tasks. e.g  resource put alone on a phase of 5 days with 5 tasks assigned to him, will show a load of 100% for this phase by default, but if we put a efficiency of 200%, then his load will only be 50%."),
        'calendar_id' : fields.many2one("resource.calendar", "Working Time", help="Define the schedule of resource"),
    }
    _defaults = {
        'resource_type' : 'user',
        'time_efficiency' : 1,
        'active' : True,
        'company_id': lambda self, cr, uid, context: self.pool.get('res.company')._company_default_get(cr, uid, 'resource.resource', context=context)
    }


    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        if not default.get('name', False):
            default.update(name=_('%s (copy)') % (self.browse(cr, uid, id, context=context).name))
        return super(resource_resource, self).copy(cr, uid, id, default, context)

    def generate_resources(self, cr, uid, user_ids, calendar_id, context=None):
        """
        Return a list of  Resource Class objects for the resources allocated to the phase.

        NOTE: Used in project/project.py
        """
        resource_objs = {}
        user_pool = self.pool.get('res.users')
        for user in user_pool.browse(cr, uid, user_ids, context=context):
            resource_objs[user.id] = {
                 'name' : user.name,
                 'vacation': [],
                 'efficiency': 1.0,
            }

            resource_ids = self.search(cr, uid, [('user_id', '=', user.id)], context=context)
            if resource_ids:
                for resource in self.browse(cr, uid, resource_ids, context=context):
                    resource_objs[user.id]['efficiency'] = resource.time_efficiency
                    resource_cal = resource.calendar_id.id
                    if resource_cal:
                        leaves = self.compute_vacation(cr, uid, calendar_id, resource.id, resource_cal, context=context)
                        resource_objs[user.id]['vacation'] += list(leaves)
        return resource_objs

    def compute_vacation(self, cr, uid, calendar_id, resource_id=False, resource_calendar=False, context=None):
        """
        Compute the vacation from the working calendar of the resource.

        @param calendar_id : working calendar of the project
        @param resource_id : resource working on phase/task
        @param resource_calendar : working calendar of the resource

        NOTE: used in project/project.py, and in generate_resources
        """
        resource_calendar_leaves_pool = self.pool.get('resource.calendar.leaves')
        leave_list = []
        if resource_id:
            leave_ids = resource_calendar_leaves_pool.search(cr, uid, ['|', ('calendar_id', '=', calendar_id),
                                                                       ('calendar_id', '=', resource_calendar),
                                                                       ('resource_id', '=', resource_id)
                                                                      ], context=context)
        else:
            leave_ids = resource_calendar_leaves_pool.search(cr, uid, [('calendar_id', '=', calendar_id),
                                                                      ('resource_id', '=', False)
                                                                      ], context=context)
        leaves = resource_calendar_leaves_pool.read(cr, uid, leave_ids, ['date_from', 'date_to'], context=context)
        for i in range(len(leaves)):
            dt_start = datetime.datetime.strptime(leaves[i]['date_from'], '%Y-%m-%d %H:%M:%S')
            dt_end = datetime.datetime.strptime(leaves[i]['date_to'], '%Y-%m-%d %H:%M:%S')
            no = dt_end - dt_start
            [leave_list.append((dt_start + datetime.timedelta(days=x)).strftime('%Y-%m-%d')) for x in range(int(no.days + 1))]
            leave_list.sort()
        return leave_list

    def compute_working_calendar(self, cr, uid, calendar_id=False, context=None):
        """
        Change the format of working calendar from 'Openerp' format to bring it into 'Faces' format.
        @param calendar_id : working calendar of the project

        NOTE: used in project/project.py
        """
        if not calendar_id:
            # Calendar is not specified: working days: 24/7
            return [('fri', '8:0-12:0','13:0-17:0'), ('thu', '8:0-12:0','13:0-17:0'), ('wed', '8:0-12:0','13:0-17:0'),
                   ('mon', '8:0-12:0','13:0-17:0'), ('tue', '8:0-12:0','13:0-17:0')]
        resource_attendance_pool = self.pool.get('resource.calendar.attendance')
        time_range = "8:00-8:00"
        non_working = ""
        week_days = {"0": "mon", "1": "tue", "2": "wed","3": "thu", "4": "fri", "5": "sat", "6": "sun"}
        wk_days = {}
        wk_time = {}
        wktime_list = []
        wktime_cal = []
        week_ids = resource_attendance_pool.search(cr, uid, [('calendar_id', '=', calendar_id)], context=context)
        weeks = resource_attendance_pool.read(cr, uid, week_ids, ['dayofweek', 'hour_from', 'hour_to'], context=context)
        # Convert time formats into appropriate format required
        # and create a list like [('mon', '8:00-12:00'), ('mon', '13:00-18:00')]
        for week in weeks:
            res_str = ""
            day = None
            if week_days.get(week['dayofweek'],False):
                day = week_days[week['dayofweek']]
                wk_days[week['dayofweek']] = week_days[week['dayofweek']]
            else:
                raise osv.except_osv(_('Configuration Error!'),_('Make sure the Working time has been configured with proper week days!'))
            hour_from_str = hours_time_string(week['hour_from'])
            hour_to_str = hours_time_string(week['hour_to'])
            res_str = hour_from_str + '-' + hour_to_str
            wktime_list.append((day, res_str))
        # Convert into format like [('mon', '8:00-12:00', '13:00-18:00')]
        for item in wktime_list:
            if wk_time.has_key(item[0]):
                wk_time[item[0]].append(item[1])
            else:
                wk_time[item[0]] = [item[0]]
                wk_time[item[0]].append(item[1])
        for k,v in wk_time.items():
            wktime_cal.append(tuple(v))
        # Add for the non-working days like: [('sat, sun', '8:00-8:00')]
        for k, v in wk_days.items():
            if week_days.has_key(k):
                week_days.pop(k)
        for v in week_days.itervalues():
            non_working += v + ','
        if non_working:
            wktime_cal.append((non_working[:-1], time_range))
        return wktime_cal


class resource_calendar_leaves(osv.osv):
    _name = "resource.calendar.leaves"
    _description = "Leave Detail"
    _columns = {
        'name' : fields.char("Name"),
        'company_id' : fields.related('calendar_id','company_id',type='many2one',relation='res.company',string="Company", store=True, readonly=True),
        'calendar_id' : fields.many2one("resource.calendar", "Working Time"),
        'date_from' : fields.datetime('Start Date', required=True),
        'date_to' : fields.datetime('End Date', required=True),
        'resource_id' : fields.many2one("resource.resource", "Resource", help="If empty, this is a generic holiday for the company. If a resource is set, the holiday/leave is only for this resource"),
    }

    def check_dates(self, cr, uid, ids, context=None):
        for leave in self.browse(cr, uid, ids, context=context):
            if leave.date_from and leave.date_to and leave.date_from > leave.date_to:
                return False
        return True

    _constraints = [
        (check_dates, 'Error! leave start-date must be lower then leave end-date.', ['date_from', 'date_to'])
    ]

    def onchange_resource(self, cr, uid, ids, resource, context=None):
        result = {}
        if resource:
            resource_pool = self.pool.get('resource.resource')
            result['calendar_id'] = resource_pool.browse(cr, uid, resource, context=context).calendar_id.id
            return {'value': result}
        return {'value': {'calendar_id': []}}

def seconds(td):
    assert isinstance(td, datetime.timedelta)

    return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10.**6

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
