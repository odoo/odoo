# Part of Odoo. See LICENSE file for full copyright and licensing details.

from copy import deepcopy
from collections import defaultdict
from datetime import UTC, datetime, timedelta, time
from random import randint
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta, weekdays
from dateutil.rrule import DAILY, rrule

from odoo import api, fields, models
from odoo.addons.base.models.res_partner import _tz_get
from odoo.tools import get_lang, babel_locale_parse
from odoo.fields import Domain
from odoo.tools.intervals import Intervals
from odoo.tools.date_utils import localized, sum_intervals, to_timezone, weeknumber

from .utils import localize_intervals


class ResourceResource(models.Model):
    _name = 'resource.resource'
    _description = "Resource"
    _order = "name"

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if not res.get('calendar_id') and res.get('company_id'):
            company = self.env['res.company'].browse(res['company_id'])
            res['calendar_id'] = company.resource_calendar_id.id
        return res

    def _default_color(self):
        return randint(1, 11)

    name = fields.Char(required=True)
    active = fields.Boolean(
        'Active', default=True,
        help="If the active field is set to False, it will allow you to hide the resource record without removing it.")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    resource_type = fields.Selection([
        ('user', 'Human'),
        ('material', 'Material')], string='Type',
        default='user', required=True)
    user_id = fields.Many2one('res.users', string='User', index='btree_not_null', help='Related user name for the resource to manage its access.')
    avatar_128 = fields.Image(compute='_compute_avatar_128', compute_sudo=True)
    share = fields.Boolean(related='user_id.share')
    email = fields.Char(related='user_id.email')
    phone = fields.Char(related='user_id.phone')

    time_efficiency = fields.Float(
        'Efficiency Factor', default=100, required=True,
        help="This field is used to calculate the expected duration of a work order at this work center. For example, if a work order takes one hour and the efficiency factor is 100%, then the expected duration will be one hour. If the efficiency factor is 200%, however the expected duration will be 30 minutes.")
    calendar_id = fields.Many2one(
        "resource.calendar", string='Working Time', required=True,
        default=lambda self: self.env.company.resource_calendar_id,
        domain="[('company_id', '=', company_id)]",
        help="Define the working schedule of the resource. Assign a flexible calendar for fully "
             "flexible working hours.")
    # readonly: several resources can share the same calendar, writing through would silently
    # change everyone else's hours too; edit the Working Schedule itself instead
    hours_per_week = fields.Float(string="Hours per Week", related='calendar_id.hours_per_week', readonly=True)
    hours_per_day = fields.Float(string="Hours per Day", related='calendar_id.hours_per_day', readonly=True)
    tz = fields.Selection(
        _tz_get, string='Timezone', required=True,
        default=lambda self: self.env.context.get('tz') or self.env.user.tz or 'UTC')
    color = fields.Integer(default=_default_color)

    _check_time_efficiency = models.Constraint(
        'CHECK(time_efficiency>0)',
        'Time efficiency must be strictly positive',
    )

    @api.depends('user_id')
    def _compute_avatar_128(self):
        for resource in self:
            resource.avatar_128 = resource.user_id.avatar_128

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if values.get('company_id') and not 'calendar_id' in values:
                values['calendar_id'] = self.env['res.company'].browse(values['company_id']).resource_calendar_id.id
            if not values.get('tz'):
                # retrieve timezone on user
                tz = self.env['res.users'].browse(values.get('user_id')).tz or self.env['res.company'].browse(values.get('company_id')).tz
                if tz:
                    values['tz'] = tz
        return super().create(vals_list)

    def write(self, vals):
        if self.env.context.get('check_idempotence') and len(self) == 1:
            vals = {
                fname: value
                for fname, value in vals.items()
                if self._fields[fname].convert_to_write(self[fname], self) != value
            }
        if not vals:
            return True
        return super().write(vals)

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id:
            default_calendar = self.env.context.get('default_calendar_id')
            if default_calendar:
                self.calendar_id = default_calendar
            else:
                self.calendar_id = self.company_id.resource_calendar_id.id

    @api.onchange('user_id')
    def _onchange_user_id(self):
        if self.user_id:
            self.tz = self.user_id.tz

    def _get_work_interval(self, start, end):
        """ Deprecated, use :meth:`_adjust_to_calendar`. """
        # Deprecated method. Use `_adjust_to_calendar` instead
        return self._adjust_to_calendar(start, end)

    def _adjust_to_calendar(self, start, end, compute_leaves=True):
        """ Snap ``start`` and ``end`` to the closest work interval boundaries of each
        resource's calendar (see ``resource.calendar._get_closest_work_time``), e.g. to
        propose default dates in planning or time off forms.

        ``start`` is matched against interval starts between the beginning of its day and
        the end of the day of ``end``; ``end`` is matched against interval ends between
        ``start`` and the end of its day. Computation happens in the resource timezone.

        Example: with attendances 8:00-13:00 and 14:00-17:00, ``start=9:00`` and
        ``end=18:00`` (same day) give ``(8:00, 17:00)``.

        :param datetime start: start to adjust, naive means UTC
        :param datetime end: end to adjust, naive means UTC
        :param bool compute_leaves: deduct leaves from the work intervals
        :return: ``{resource: (start, end)}``; each value is in the timezone of the given
            argument (naive UTC if it was naive), or ``None`` if no boundary was found
        :rtype: dict
        """
        revert_start_tz = to_timezone(start.tzinfo)
        revert_end_tz = to_timezone(end.tzinfo)
        start = localized(start)
        end = localized(end)
        result = {}
        for resource in self:
            resource_tz = ZoneInfo(resource.tz)
            start, end = start.astimezone(resource_tz), end.astimezone(resource_tz)
            search_range = [
                start + relativedelta(hour=0, minute=0, second=0),
                end + relativedelta(days=1, hour=0, minute=0, second=0),
            ]
            calendar = resource.calendar_id
            calendar_start = calendar._get_closest_work_time(start, resource=resource, search_range=search_range,
                                                                         compute_leaves=compute_leaves)
            search_range[0] = start
            calendar_end = calendar._get_closest_work_time(max(start, end), match_end=True,
                                                                       resource=resource, search_range=search_range,
                                                                       compute_leaves=compute_leaves)
            result[resource] = (
                calendar_start and revert_start_tz(calendar_start),
                calendar_end and revert_end_tz(calendar_end),
            )
        return result

    def _get_unavailable_intervals(self, start, end):
        """ Return the periods during which each resource does not work between ``start``
        and ``end``, according to its calendar (``resource.calendar._unavailable_intervals_batch``),
        e.g. to grey out Gantt views (planning, project, MRP).

        :param datetime start: start of the period, naive means UTC
        :param datetime end: end of the period, naive means UTC
        :return: ``{resource_id: Intervals}`` expressed in UTC (only the leaves for
            flexible resources, which are missing when they have no leave)
        :rtype: dict
        """
        start_datetime = localized(start)
        end_datetime = localized(end)
        resource_mapping = {}
        calendar_mapping = defaultdict(lambda: self.env['resource.resource'])
        for resource in self:
            calendar_mapping[resource.calendar_id] |= resource

        for calendar, resources in calendar_mapping.items():
            resources_per_tz = resources._get_resources_per_tz()
            resources_unavailable_intervals = calendar._unavailable_intervals_batch(start_datetime, end_datetime, resources_per_tz)
            # _unavailable_intervals_batch also includes a `False`-keyed entry for the calendar's
            # own generic (resource-less) unavailability; irrelevant here, this method only
            # promises unavailability for the resources in self
            resource_mapping.update({
                resource_id: intervals for resource_id, intervals in resources_unavailable_intervals.items() if resource_id
            })
        return resource_mapping

    def _get_calendars_validity_within_period(self, start, end, default_company=None):
        """ Return, for each resource, the calendars it uses within the period and when each
        of them applies. Here a resource has a single calendar valid on the whole period;
        ``hr`` overrides it so that an employee uses the calendar of each of its contract
        versions on their own validity period.

        :param datetime start: timezone-aware start of the period
        :param datetime end: timezone-aware end of the period
        :param default_company: ``res.company`` whose default calendar is used when ``self``
            is empty (current company by default)
        :return: ``{resource_id: {resource.calendar: Intervals}}`` (nested ``defaultdict``).
            When ``self`` is empty, the key ``False`` maps the default calendar to the whole
            period.
        :rtype: dict
        """
        assert start.tzinfo and end.tzinfo
        resource_calendars_within_period = defaultdict(lambda: defaultdict(Intervals))  # keys are [resource id:integer][calendar:self.env['resource.calendar']]
        default_calendar = default_company and default_company.resource_calendar_id or self.env.company.resource_calendar_id
        if not self:
            # if no resource, add the company resource calendar.
            resource_calendars_within_period[False][default_calendar] = Intervals([(start, end, self.env['resource.calendar.attendance'])])
        for resource in self:
            calendar = resource.calendar_id
            resource_calendars_within_period[resource.id][calendar] = Intervals([(start, end, self.env['resource.calendar.attendance'])])
        return resource_calendars_within_period

    def _get_valid_work_intervals(self, start, end, calendars=None, compute_leaves=True):
        """ Return the work intervals of each resource between ``start`` and ``end``, taking
        into account that a resource may use several calendars over the period (see
        :meth:`_get_calendars_validity_within_period`): the work intervals of each calendar
        are restricted to its validity period, then united.

        This is the entry point to know when resources work, e.g. in planning, project or
        MRP scheduling. Flexible calendars give the intervals described in
        ``resource.calendar._attendance_intervals_batch``; a falsy calendar (possible with
        overrides) gives the whole period.

        :param datetime start: timezone-aware start of the period
        :param datetime end: timezone-aware end of the period
        :param calendars: optional extra ``resource.calendar`` records for which the
            calendar-level work intervals are wanted in the second returned dict
        :param bool compute_leaves: deduct leaves
        :return: a pair ``(resource_work_intervals, calendar_work_intervals)``:
            ``{resource_id: Intervals}`` (in each resource's timezone) and
            ``{calendar_id: Intervals}`` (calendar-level result of every calendar used)
        :rtype: tuple
        """
        assert start.tzinfo and end.tzinfo
        resource_calendar_validity_intervals = {}
        calendar_resources = defaultdict(lambda: self.env['resource.resource'])
        resource_work_intervals = defaultdict(Intervals)
        calendar_work_intervals = dict()

        resource_calendar_validity_intervals = self.sudo()._get_calendars_validity_within_period(start, end)
        for resource in self:
            # For each resource, retrieve its calendar and their validity intervals
            for calendar in resource_calendar_validity_intervals[resource.id]:
                calendar_resources[calendar] |= resource
        for calendar in (calendars or []):
            calendar_resources[calendar] |= self.env['resource.resource']
        for calendar, resources in calendar_resources.items():
            # for fully flexible resource, return the whole interval
            if not calendar:
                for resource in resources:
                    resource_work_intervals[resource.id] |= Intervals([(start, end, self.env['resource.calendar.attendance'])])
                continue
            # For each calendar used by the resources, retrieve the work intervals for every resources using it
            resources_per_tz = resources._get_resources_per_tz()
            work_intervals_batch = calendar._work_intervals_batch(start, end, resources_per_tz=resources_per_tz, compute_leaves=compute_leaves)
            for resource in resources:
                # Make the conjunction between work intervals and calendar validity
                resource_work_intervals[resource.id] |= work_intervals_batch[resource.id] & resource_calendar_validity_intervals[resource.id][calendar]
            calendar_work_intervals[calendar.id] = work_intervals_batch[False]

        return resource_work_intervals, calendar_work_intervals

    def _is_fully_flexible(self):
        """ Return whether the resource's calendar is fully flexible (no attendance and no
        hours target), see ``resource.calendar._is_fully_flexible``. """
        self.ensure_one()
        return self.calendar_id._is_fully_flexible()

    def _get_calendar_data_at(self, date_target, tz=False):
        """ Return the calendar data applying to each resource at ``date_target``. Here it is
        the resource's own calendar; ``hr`` overrides it to use the employee's contract
        version valid at that date (``date_target`` being converted to ``tz``).

        :return: ``{resource: {'resource_calendar_id': resource.calendar,
            'hours_per_week': float, 'hours_per_day': float}}``
        :rtype: dict
        """
        return {
            resource: {
                'resource_calendar_id': resource.calendar_id,
                'hours_per_week': resource.hours_per_week,
                'hours_per_day': resource.hours_per_day,
            } for resource in self}

    def _is_flexible(self):
        """ Return whether the resource's calendar is flexible (type ``undefined``), see
        ``resource.calendar._is_flexible``. """
        self.ensure_one()
        return self.calendar_id._is_flexible()

    def _get_flexible_resources_default_work_intervals(self, start, end):
        """ Return, for each (flexible) resource, one interval per day from the day of
        ``start`` to the day of ``end``, each covering the whole day (00:00 to
        23:59:59.999999) in the resource timezone (user timezone for an empty record).

        :param datetime start: timezone-aware start
        :param datetime end: timezone-aware end
        :return: ``{resource_id: Intervals}``
        :rtype: dict
        """
        assert start.tzinfo and end.tzinfo

        start_date = start.date()
        end_date = end.date()
        res = {}

        resources_per_tz = defaultdict(list)
        for resource in self:
            resources_per_tz[ZoneInfo((resource or self.env.user).tz)].append(resource)

        for tz, resources in resources_per_tz.items():
            start = start_date
            ranges = []
            while start <= end_date:
                start_datetime = datetime.combine(start, datetime.min.time(), tzinfo=tz)
                end_datetime = datetime.combine(start, datetime.max.time(), tzinfo=tz)
                ranges.append((start_datetime, end_datetime, self.env['resource.calendar.attendance']))
                start += timedelta(days=1)

            for resource in resources:
                res[resource.id] = Intervals(ranges)

        return res

    def _get_flexible_resources_calendars_validity_within_period(self, start, end):
        """ Flexible counterpart of :meth:`_get_calendars_validity_within_period`: the
        validity of each calendar is expressed as whole-day intervals (see
        :meth:`_get_flexible_resources_default_work_intervals`). Overridden by ``hr`` for
        contract versions.

        :return: ``{resource_id: {resource.calendar: Intervals}}``
        :rtype: dict
        """
        assert start.tzinfo and end.tzinfo
        resource_default_work_intervals = self._get_flexible_resources_default_work_intervals(start, end)

        calendars_within_period_per_resource = defaultdict(lambda: defaultdict(Intervals))  # keys are [resource id:integer][calendar:self.env['resource.calendar']]
        for resource in self:
            calendars_within_period_per_resource[resource.id][resource.calendar_id] = resource_default_work_intervals[resource.id]

        return calendars_within_period_per_resource

    def _format_leave(self, leave, resource_hours_per_day, resource_hours_per_week, ranges_to_remove, start_day, end_day, locale):
        leave_start_day = leave[0].date()
        leave_end_day = leave[1].date()
        tz = ZoneInfo(self.tz or self.env.user.tz)
        week_start_day = int(get_lang(self.env).week_start) - 1

        while leave_start_day <= leave_end_day:
            if not self._is_fully_flexible():
                hours = self.calendar_id.hours_per_day if self.calendar_id else self.hours_per_day
                # only days inside the original period
                if leave_start_day >= start_day and leave_start_day <= end_day:
                    resource_hours_per_day[self.id][leave_start_day] -= hours
                year_and_week = weeknumber(babel_locale_parse(locale), leave_start_day, week_start_day)
                resource_hours_per_week[self.id][year_and_week] -= hours

            range_start_datetime = datetime.combine(leave_start_day, datetime.min.time(), tzinfo=tz)
            range_end_datetime = datetime.combine(leave_start_day, datetime.max.time(), tzinfo=tz)
            ranges_to_remove.append((range_start_datetime, range_end_datetime, self.env['resource.calendar.attendance']))
            leave_start_day += timedelta(days=1)

    def _get_flexible_resource_valid_work_intervals(self, start, end):
        """ Flexible counterpart of :meth:`_get_valid_work_intervals`, for resources that all
        have a flexible calendar. Since they have no attendance, it returns availability as
        whole days plus hour budgets, to be consumed by :meth:`_get_flexible_resource_work_hours`.

        The budgets are computed on the full weeks (per the user language's first day of the
        week) containing the period. Each leave day (leaves counted as absence only, as for
        the work intervals) is removed from the intervals and its ``hours_per_day`` deducted from
        the budgets. Fully flexible resources get intervals but no budget.

        :param datetime start: timezone-aware start of the period
        :param datetime end: timezone-aware end of the period
        :return: a triple ``(work_intervals, hours_per_day, hours_per_week)``:

            - ``{resource_id: Intervals}``: whole-day intervals in the resource timezone,
              leave days removed, restricted to ``[start, end]``;
            - ``{resource_id: {date: float}}``: daily budget (at most ``hours_per_day``),
              for the days of the period;
            - ``{resource_id: {(year, week_number): float}}``: weekly budget (at most
              ``hours_per_week``, or the calendar's full time hours).

            Three empty dicts when ``self`` is empty.
        :rtype: tuple
        """
        if not self:
            return {}, {}, {}

        assert all(record._is_flexible() for record in self)
        assert start.tzinfo and end.tzinfo

        locale = babel_locale_parse(get_lang(self.env).code)

        week_start_day = int(get_lang(self.env).week_start) - 1
        delta = relativedelta(weekday=weekdays[week_start_day](-1))
        week_start_date = start + delta
        week_end_date = end + delta + relativedelta(days=6)

        end_year, end_week = weeknumber(locale, week_end_date, week_start_day)

        min_start_date = week_start_date + relativedelta(hour=0, minute=0, second=0, microsecond=0)
        max_end_date = week_end_date + relativedelta(days=1, hour=0, minute=0, second=0, microsecond=0)

        resource_work_intervals = defaultdict(Intervals)
        calendar_resources = defaultdict(lambda: self.env['resource.resource'])

        resource_calendar_validity_intervals = self._get_flexible_resources_calendars_validity_within_period(min_start_date, max_end_date)
        for resource in self:
            # For each resource, retrieve their calendars validity intervals
            for calendar, work_intervals in resource_calendar_validity_intervals[resource.id].items():
                calendar_resources[calendar] |= resource
                resource_work_intervals[resource.id] |= work_intervals

        resource_by_id = {resource.id: resource for resource in self}
        # the days of the period must be computed in the timezone of the resource
        period_days_per_resource = {}
        for resource in self:
            tz = ZoneInfo(resource.tz or self.env.user.tz)
            period_days_per_resource[resource.id] = (start.astimezone(tz).date(), end.astimezone(tz).date())

        resource_hours_per_day = defaultdict(lambda: defaultdict(float))
        resource_hours_per_week = defaultdict(lambda: defaultdict(float))
        locale = get_lang(self.env).code

        for resource in self:
            if resource._is_fully_flexible():
                continue
            duration_per_day = defaultdict(float)
            resource_intervals = resource_work_intervals.get(resource.id, Intervals())
            for interval_start, interval_end, _dummy in resource_intervals:
                # thanks to default periods structure, start and end should be in same day (with a same timezone !!)
                day = interval_start.date()
                # custom timeoff can divide a day to > 1 intervals
                duration_per_day[day] += (interval_end - interval_start).total_seconds() / 3600

            full_time_required_hours = resource.calendar_id.full_time_required_hours if resource.calendar_id else resource.company_id.resource_calendar_id.hours_per_week
            hours_per_day = resource.calendar_id.hours_per_day if resource.calendar_id else resource.hours_per_day

            start_day, end_day = period_days_per_resource[resource.id]
            for day, hours in duration_per_day.items():
                day_working_hours = min(hours, hours_per_day)
                # only days inside the original period
                if day >= start_day and day <= end_day:
                    resource_hours_per_day[resource.id][day] = day_working_hours

                year_week = weeknumber(babel_locale_parse(locale), day, week_start_day)
                year, week = year_week
                if (year < end_year) or (year == end_year and week <= end_week):
                    # cap weekly hours to the resource's configured hours_per_week (not the
                    # company default full_time_required_hours which does not respect
                    # part-time schedules).
                    cap = resource.hours_per_week or full_time_required_hours
                    resource_hours_per_week[resource.id][year_week] = min(cap, day_working_hours + resource_hours_per_week[resource.id][year_week])
        for calendar, resources in calendar_resources.items():
            resources_per_tz = resources._get_resources_per_tz()
            leave_intervals = (calendar or self.env['resource.calendar'])._leave_intervals_batch(min_start_date, max_end_date, resources_per_tz)
            for resource_id, leaves in leave_intervals.items():
                if not resource_id:
                    continue

                ranges_to_remove = []
                start_day, end_day = period_days_per_resource[resource_id]
                for leave in leaves._items:
                    resource_by_id[resource_id]._format_leave(leave, resource_hours_per_day, resource_hours_per_week, ranges_to_remove, start_day, end_day, locale)

                resource_work_intervals[resource_id] -= Intervals(ranges_to_remove)

        for resource_id, work_intervals in resource_work_intervals.items():
            tz = ZoneInfo(resource_by_id[resource_id].tz or self.env.user.tz)
            resource_work_intervals[resource_id] = work_intervals & Intervals([(start.astimezone(tz), end.astimezone(tz), self.env['resource.calendar.attendance'])])

        return resource_work_intervals, resource_hours_per_day, resource_hours_per_week

    def _get_flexible_resource_work_hours(self, intervals, flexible_resources_hours_per_day, flexible_resources_hours_per_week, work_hours_per_day=None):
        """ Return how many hours this flexible resource can work within ``intervals``,
        capped day by day by the daily budget and the remaining weekly budget, as computed by
        :meth:`_get_flexible_resource_valid_work_intervals`. For a fully flexible resource
        (or without ``hours_per_day``), simply return the total duration of ``intervals``.

        :param intervals: intervals of the resource to evaluate, e.g. a planning slot
            intersected with its work intervals
        :param dict flexible_resources_hours_per_day: ``{date: float}`` budget of this resource
        :param dict flexible_resources_hours_per_week: ``{(year, week_number): float}`` budget
            of this resource (not modified)
        :param work_hours_per_day: optional ``defaultdict(float)`` filled in place with the
            hours retained per ``date``
        :rtype: float
        """
        assert self._is_flexible()

        if self._is_fully_flexible() or not self.hours_per_day:
            return round(sum_intervals(intervals), 2)

        # start and end for each Interval have the same day thanks to schedule_intervals_per_resource_id format for flexible employees
        # 2 intervals can cover the same day, in case of custom timeoff at the middle of the day
        duration_per_day = deepcopy(flexible_resources_hours_per_day)
        duration_per_week = deepcopy(flexible_resources_hours_per_week)

        interval_duration_per_day = defaultdict(float)
        # days with custom time off can divide a day to many intervals
        for start, end, _dummy in intervals:
            if end.time() == time.max:
                # flex resource intervals are formatted in days, each day from min time to max time, when getting the difference, one microsecond is lost
                duration = (end + timedelta(microseconds=1) - start).total_seconds() / 3600
            else:
                duration = (end - start).total_seconds() / 3600
            interval_duration_per_day[start.date()] += duration

        work_hours = 0.0
        locale = get_lang(self.env).code
        week_start_day = int(get_lang(self.env).week_start) - 1
        for day, hours in interval_duration_per_day.items():
            week = weeknumber(babel_locale_parse(locale), day, week_start_day)
            day_working_hours = max(0.0, min(
                hours,
                duration_per_day.get(day, 0.0),
                duration_per_week.get(week, 0.0),
            ))
            work_hours += day_working_hours
            duration_per_week[week] -= day_working_hours

            if work_hours_per_day is not None:
                work_hours_per_day[day] += day_working_hours

        return work_hours

    def _get_resources_per_tz(self):
        """ Group the resources by timezone, in the format expected by the
        ``resources_per_tz`` argument of the ``resource.calendar`` interval methods.

        :return: ``{ZoneInfo: resource.resource recordset}`` (empty dict for no resource)
        :rtype: dict
        """
        return self.grouped(lambda r: ZoneInfo(r.tz))

    # --------------------------------------------------
    # New API
    # --------------------------------------------------

    def _get_calendar_tz_periods(self, start, stop):
        """ Return the working schedule and timezone of each resource within ``[start, stop]``.

        Here a resource keeps its own calendar and timezone for the whole period; ``hr``
        overrides it to follow the versions (in contract) of the employee.

        :param date start: first day of the period (included)
        :param date stop: last day of the period (included)
        :return: ``{resource: [(date_from, date_to, resource.calendar, tz_name), ...]}`` with
            inclusive dates; a resource without any period gets no attendance
        :rtype: dict
        """
        return {resource: [(start, stop, resource.calendar_id, resource.tz)] for resource in self}

    def _get_period_windows(self, dt_from, dt_to):
        """ Turn the periods of :meth:`_get_calendar_tz_periods` into timezone-aware windows
        clipped to ``[dt_from, dt_to]``.

        :return: ``{resource: [(window_start, window_stop, resource.calendar, ZoneInfo), ...]}``,
            the bounds being expressed in the timezone of the period
        :rtype: dict
        """
        # widen by a day so that the periods cover [dt_from, dt_to] in every timezone
        periods = self._get_calendar_tz_periods(
            (dt_from - timedelta(days=1)).date(), (dt_to + timedelta(days=1)).date())
        windows = defaultdict(list)
        zones = {}
        for resource, resource_periods in periods.items():
            for date_from, date_to, calendar, tz in resource_periods:
                zone = zones.get(tz) or zones.setdefault(tz, ZoneInfo(tz or 'UTC'))
                start = max(dt_from, datetime.combine(date_from, time.min, tzinfo=zone))
                stop = min(dt_to, datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=zone))
                if start < stop:
                    windows[resource].append((start.astimezone(zone), stop.astimezone(zone), calendar, zone))
        return windows

    def _attendance_intervals(self, dt_from, dt_to, domain=None, availability=False):
        """ Return the attendance intervals of each resource between ``dt_from`` and ``dt_to``,
        leaves not deducted. Replaces ``resource.calendar._attendance_intervals_batch``.

        The calendar and timezone used are given by :meth:`_get_calendar_tz_periods`, so they
        may change within the period (employee versions with ``hr``). The attendances of all
        the calendars involved are computed in one call per timezone.

        - regular calendars: the attendances of the calendar (see
          ``resource.calendar._attendance_intervals``), in the timezone of the period;
        - no calendar or fully flexible calendar: the whole period;
        - flexible calendar with hours targets: up to ``hours_per_day`` per day centered on
          12:00, until ``hours_per_week`` is reached in each 7-day block of the period.

        Flexible periods get an unsaved attendance holding only ``duration_hours`` as payload,
        and no interval at all when ``domain`` is given.

        :param datetime dt_from: timezone-aware start of the period
        :param datetime dt_to: timezone-aware end of the period
        :param domain: optional domain on ``resource.calendar.attendance``
        :param bool availability: for duration-based and flexible schedules, return the whole
            day instead of hours placed around noon
        :return: ``{resource: Intervals}`` (``keep_distinct=True``) for every resource of ``self``
        :rtype: dict
        """
        assert dt_from.tzinfo and dt_to.tzinfo, "Timezone-aware datetimes are expected"
        windows = self._get_period_windows(dt_from, dt_to)
        return self._attendance_intervals_from_windows(dt_from, dt_to, windows, domain, availability)

    def _attendance_intervals_from_windows(self, dt_from, dt_to, windows, domain=None, availability=False):
        # one call per timezone, for all the regular calendars at once
        calendars_per_zone = defaultdict(lambda: self.env['resource.calendar'])
        for resource_windows in windows.values():
            for _start, _stop, calendar, zone in resource_windows:
                if calendar and not calendar._is_flexible():
                    calendars_per_zone[zone] |= calendar
        localized_per_calendar = {}
        for zone, calendars in calendars_per_zone.items():
            intervals_per_calendar = calendars._attendance_intervals(
                dt_from.astimezone(zone).replace(tzinfo=None),
                dt_to.astimezone(zone).replace(tzinfo=None),
                domain=domain,
                availability=availability,
            )
            for calendar in calendars:
                localized_per_calendar[calendar, zone] = localize_intervals(
                    intervals_per_calendar.get(calendar, Intervals(keep_distinct=True)), zone.key)

        no_attendance = self.env['resource.calendar.attendance']
        result = {}
        for resource in self:
            items = []
            for start, stop, calendar, zone in windows.get(resource, []):
                if calendar and not calendar._is_flexible():
                    items.extend(localized_per_calendar[calendar, zone] & Intervals([(start, stop, no_attendance)]))
                elif domain:
                    continue
                elif availability or not calendar or calendar._is_fully_flexible():
                    hours = (stop - start).total_seconds() / 3600
                    items.append((start, stop, no_attendance.new({'duration_hours': hours})))
                else:
                    items.extend(_flexible_attendance_intervals(
                        no_attendance, start, stop, calendar.hours_per_day, calendar.hours_per_week))
            result[resource] = Intervals(items, keep_distinct=True)
        return result

    def _leave_intervals(self, dt_from, dt_to, domain=None):
        """ Return the leave intervals of each resource between ``dt_from`` and ``dt_to``.
        Replaces ``resource.calendar._leave_intervals_batch``.

        A resource gets its own leaves, and the global leaves (no ``resource_id``) of its company
        that apply to the calendar of the period (or to every calendar). Leaves are clipped to
        ``[dt_from, dt_to]``, global ones to the periods of :meth:`_get_calendar_tz_periods`.
        Own leaves of a flexible period go through
        ``resource.calendar._handle_flexible_leave_interval`` (whole days by default).
        Overlapping leaves are merged, the payload being the union of the leave records.

        :param datetime dt_from: timezone-aware start of the period
        :param datetime dt_to: timezone-aware end of the period
        :param list domain: domain on ``resource.calendar.leaves``; ``None`` means
            ``[('count_as', '=', 'absence')]``
        :return: ``{resource: Intervals}`` for every resource of ``self``
        :rtype: dict
        """
        assert dt_from.tzinfo and dt_to.tzinfo, "Timezone-aware datetimes are expected"
        windows = self._get_period_windows(dt_from, dt_to)
        return self._leave_intervals_from_windows(dt_from, dt_to, windows, domain)

    def _leave_intervals_from_windows(self, dt_from, dt_to, windows, domain=None):
        if domain is None:
            domain = [('count_as', '=', 'absence')]
        leaves = self.env['resource.calendar.leaves'].search_fetch(Domain.AND([
            domain,
            [
                ('resource_id', 'in', [False, *self.ids]),
                ('date_from', '<=', dt_to.astimezone(UTC).replace(tzinfo=None)),
                ('date_to', '>=', dt_from.astimezone(UTC).replace(tzinfo=None)),
            ],
        ]), ['date_from', 'date_to', 'resource_id', 'company_id', 'calendar_id'])
        own_leaves = leaves.filtered('resource_id')
        own_leaves_per_resource = own_leaves.grouped('resource_id')
        global_leaves = [
            (leave.date_from.replace(tzinfo=UTC), leave.date_to.replace(tzinfo=UTC), leave)
            for leave in leaves - own_leaves
        ]
        no_calendar = self.env['resource.calendar']

        result = {}
        for resource in self:
            resource_windows = windows.get(resource, [])
            fallback_zone = ZoneInfo(resource.tz or 'UTC')
            items = []
            for leave in own_leaves_per_resource.get(resource, ()):
                leave_from = leave.date_from.replace(tzinfo=UTC)
                leave_to = leave.date_to.replace(tzinfo=UTC)
                # the period in which the leave starts gives its timezone and calendar
                calendar, zone = resource.calendar_id, fallback_zone
                for start, stop, window_calendar, window_zone in resource_windows:
                    if start <= max(leave_from, dt_from) < stop:
                        calendar, zone = window_calendar, window_zone
                        break
                leave_from, leave_to = leave_from.astimezone(zone), leave_to.astimezone(zone)
                if not calendar or calendar._is_flexible():
                    leave_from, leave_to = (calendar or no_calendar)._handle_flexible_leave_interval(
                        leave_from, leave_to, leave)
                start, stop = max(dt_from.astimezone(zone), leave_from), min(dt_to.astimezone(zone), leave_to)
                if start < stop:
                    items.append((start, stop, leave))
            for start, stop, calendar, zone in resource_windows:
                for leave_from, leave_to, leave in global_leaves:
                    if leave_to <= start or leave_from >= stop:
                        continue
                    if leave.company_id and leave.company_id != resource.company_id:
                        continue
                    if leave.calendar_id and leave.calendar_id != calendar:
                        continue
                    items.append((max(start, leave_from.astimezone(zone)), min(stop, leave_to.astimezone(zone)), leave))
            result[resource] = Intervals(items)
        return result

    def _work_intervals(self, dt_from, dt_to, domain=None, attendance_domain=None, availability=False, compute_leaves=True):
        """ Return the work intervals of each resource: attendances minus leaves.
        Replaces ``resource.calendar._work_intervals_batch``.

        :param datetime dt_from: timezone-aware start of the period
        :param datetime dt_to: timezone-aware end of the period
        :param list domain: leave domain, see :meth:`_leave_intervals`
        :param attendance_domain: attendance domain, see :meth:`_attendance_intervals`
        :param bool availability: see :meth:`_attendance_intervals`
        :param bool compute_leaves: when ``False``, leaves are not deducted
        :return: ``{resource: Intervals}`` for every resource of ``self``
        :rtype: dict
        """
        assert dt_from.tzinfo and dt_to.tzinfo, "Timezone-aware datetimes are expected"
        windows = self._get_period_windows(dt_from, dt_to)
        return self._work_intervals_from_windows(
            dt_from, dt_to, windows, domain, attendance_domain, availability, compute_leaves)

    def _work_intervals_from_windows(self, dt_from, dt_to, windows, domain=None, attendance_domain=None, availability=False, compute_leaves=True):
        """ Compute :meth:`_work_intervals` from the windows of :meth:`_get_period_windows`.
        Override this method (not :meth:`_work_intervals`) to remove other time from the work
        intervals, using ``_attendance_intervals_from_windows`` with the same ``windows``. """
        attendances = self._attendance_intervals_from_windows(dt_from, dt_to, windows, attendance_domain, availability)
        if not compute_leaves:
            return attendances
        leaves = self._leave_intervals_from_windows(dt_from, dt_to, windows, domain)
        return {resource: attendances[resource] - leaves[resource] for resource in self}


def _flexible_attendance_intervals(attendance_model, window_start, window_stop, hours_per_day, hours_per_week):
    """ Synthetic attendances of a flexible calendar with hours targets over a window, placed as
    ``resource.calendar._attendance_intervals_batch`` does: up to ``hours_per_day`` per day,
    centered on 12:00, until ``hours_per_week`` is reached in each 7-day block counted from
    ``window_start``.

    :return: list of ``(start, stop, attendance)`` with unsaved attendances
    """
    zone = window_start.tzinfo
    total_hours = (window_stop - window_start).total_seconds() / 3600
    last_day = (window_stop - timedelta(seconds=1)).date()
    items = []
    week_start = window_start.date()
    while week_start <= last_day:
        remaining = min(hours_per_week, total_hours)
        week_days = rrule(DAILY, week_start, until=min(week_start + timedelta(days=6), last_day))
        for day in (d.date() for d in week_days):
            if remaining <= 0:
                break
            day_start = max(window_start, datetime.combine(day, time.min, tzinfo=zone))
            day_stop = min(window_stop, datetime.combine(day, time.max, tzinfo=zone))
            hours = min(hours_per_day, remaining, (day_stop - day_start).total_seconds() / 3600)
            if hours <= 0:
                continue
            remaining -= hours
            midpoint = datetime.combine(day, time(12), tzinfo=zone)
            start, stop = midpoint - timedelta(hours=hours / 2), midpoint + timedelta(hours=hours / 2)
            if start < day_start:
                start, stop = day_start, day_start + timedelta(hours=hours)
            elif stop > day_stop:
                start, stop = day_stop - timedelta(hours=hours), day_stop
            items.append((start, stop, attendance_model.new({'duration_hours': hours})))
        week_start += timedelta(days=7)
    return items
