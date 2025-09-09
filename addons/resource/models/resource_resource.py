# Part of Odoo. See LICENSE file for full copyright and licensing details.

from copy import deepcopy
from collections import defaultdict
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta, time
from pytz import timezone

from odoo import api, fields, models
from odoo.addons.base.models.res_partner import _tz_get
from odoo.tools import get_lang, babel_locale_parse
from odoo.tools.intervals import Intervals
from odoo.tools.date_utils import localized, sum_intervals, to_timezone, weeknumber, weekstart, weekend


class ResourceResource(models.Model):
    _name = 'resource.resource'
    _description = "Resources"
    _order = "name"

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
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
    user_id = fields.Many2one('res.users', string='User', index='btree_not_null', help='Related user name for the resource to manage its access.')
    avatar_128 = fields.Image(compute='_compute_avatar_128')
    share = fields.Boolean(related='user_id.share')
    email = fields.Char(related='user_id.email')
    phone = fields.Char(related='user_id.phone')

    time_efficiency = fields.Float(
        'Efficiency Factor', default=100, required=True,
        help="This field is used to calculate the expected duration of a work order at this work center. For example, if a work order takes one hour and the efficiency factor is 100%, then the expected duration will be one hour. If the efficiency factor is 200%, however the expected duration will be 30 minutes.")
    calendar_id = fields.Many2one(
        "resource.calendar", string='Working Time',
        default=lambda self: self.env.company.resource_calendar_id,
        domain="[('company_id', '=', company_id)]",
        help="Define the working schedule of the resource. If not set, the resource will have fully flexible working hours.")
    tz = fields.Selection(
        _tz_get, string='Timezone', required=True,
        default=lambda self: self.env.context.get('tz') or self.env.user.tz or 'UTC')

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
                # retrieve timezone on user or calendar
                tz = (self.env['res.users'].browse(values.get('user_id')).tz or
                      self.env['resource.calendar'].browse(values.get('calendar_id')).tz)
                if tz:
                    values['tz'] = tz
        return super().create(vals_list)

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        return [dict(vals, name=self.env._("%s (copy)", resource.name)) for resource, vals in zip(self, vals_list)]

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
            self.calendar_id = self.company_id.resource_calendar_id.id

    @api.onchange('user_id')
    def _onchange_user_id(self):
        if self.user_id:
            self.tz = self.user_id.tz

    def _get_work_interval(self, start, end):
        # Deprecated method. Use `_adjust_to_calendar` instead
        return self._adjust_to_calendar(start, end)

    def _adjust_to_calendar(self, start, end, compute_leaves=True):
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
        revert_start_tz = to_timezone(start.tzinfo)
        revert_end_tz = to_timezone(end.tzinfo)
        start = localized(start)
        end = localized(end)
        result = {}
        for resource in self:
            resource_tz = timezone(resource.tz)
            start, end = start.astimezone(resource_tz), end.astimezone(resource_tz)
            search_range = [
                start + relativedelta(hour=0, minute=0, second=0),
                end + relativedelta(days=1, hour=0, minute=0, second=0),
            ]
            calendar = resource.calendar_id or resource.company_id.resource_calendar_id or self.env.company.resource_calendar_id
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
        """ Compute the intervals during which employee is unavailable with hour granularity between start and end
            Note: this method is used in enterprise (forecast and planning)

        """
        start_datetime = localized(start)
        end_datetime = localized(end)
        resource_mapping = {}
        calendar_mapping = defaultdict(lambda: self.env['resource.resource'])
        for resource in self:
            calendar_mapping[resource.calendar_id or resource.company_id.resource_calendar_id] |= resource

        for calendar, resources in calendar_mapping.items():
            if not calendar:
                continue
            resources_unavailable_intervals = calendar._unavailable_intervals_batch(start_datetime, end_datetime, resources, tz=timezone(calendar.tz))
            resource_mapping.update(resources_unavailable_intervals)
        return resource_mapping

    def _get_calendars_validity_within_period(self, start, end, default_company=None):
        """ Gets a dict of dict with resource's id as first key and resource's calendar as secondary key
            The value is the validity interval of the calendar for the given resource.

            Here the validity interval for each calendar is the whole interval but it's meant to be overriden in further modules
            handling resource's employee contracts.
        """
        assert start.tzinfo and end.tzinfo
        resource_calendars_within_period = defaultdict(lambda: defaultdict(Intervals))  # keys are [resource id:integer][calendar:self.env['resource.calendar']]
        default_calendar = default_company and default_company.resource_calendar_id or self.env.company.resource_calendar_id
        if not self:
            # if no resource, add the company resource calendar.
            resource_calendars_within_period[False][default_calendar] = Intervals([(start, end, self.env['resource.calendar.attendance'])])
        for resource in self:
            calendar = resource.calendar_id or resource.company_id.resource_calendar_id or default_calendar
            resource_calendars_within_period[resource.id][calendar] = Intervals([(start, end, self.env['resource.calendar.attendance'])])
        return resource_calendars_within_period

    def _get_valid_work_intervals(self, start, end, calendars=None, compute_leaves=True):
        """ Gets the valid work intervals of the resource following their calendars between ``start`` and ``end``

            This methods handle the eventuality of a resource having multiple resource calendars, see _get_calendars_validity_within_period method
            for further explanation.

            For flexible calendars and fully flexible resources: -> return the whole interval
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
            work_intervals_batch = calendar._work_intervals_batch(start, end, resources=resources, compute_leaves=compute_leaves)
            for resource in resources:
                # Make the conjunction between work intervals and calendar validity
                resource_work_intervals[resource.id] |= work_intervals_batch[resource.id] & resource_calendar_validity_intervals[resource.id][calendar]
            calendar_work_intervals[calendar.id] = work_intervals_batch[False]

        return resource_work_intervals, calendar_work_intervals

    def _is_fully_flexible(self):
        """ employee has a fully flexible schedule has no working calendar set """
        self.ensure_one()
        return not self.calendar_id

    def _get_calendar_at(self, date_target, tz=False):
        return {resource: resource.calendar_id for resource in self}

    def _is_flexible(self):
        """ An employee is considered flexible if the field flexible_hours is True on the calendar
            or the employee is not assigned any calendar, in which case is considered as Fully flexible.
        """
        self.ensure_one()
        return self._is_fully_flexible() or (self.calendar_id and self.calendar_id.flexible_hours)

    def _get_flexible_resources_default_work_intervals(self, start, end):
        assert start.tzinfo and end.tzinfo

        start_date = start.date()
        end_date = end.date()
        res = {}

        resources_per_tz = defaultdict(list)
        for resource in self:
            resources_per_tz[timezone((resource or self.env.user).tz)].append(resource)

        for tz, resources in resources_per_tz.items():
            start = start_date
            ranges = []
            while start <= end_date:
                start_datetime = tz.localize(datetime.combine(start, datetime.min.time()))
                end_datetime = tz.localize(datetime.combine(start, datetime.max.time()))
                ranges.append((start_datetime, end_datetime, self.env['resource.calendar.attendance']))
                start += timedelta(days=1)

            for resource in resources:
                res[resource.id] = Intervals(ranges)

        return res

    def _get_flexible_resources_calendars_validity_within_period(self, start, end):
        assert start.tzinfo and end.tzinfo
        resource_default_work_intervals = self._get_flexible_resources_default_work_intervals(start, end)

        calendars_within_period_per_resource = defaultdict(lambda: defaultdict(Intervals))  # keys are [resource id:integer][calendar:self.env['resource.calendar']]
        for resource in self:
            calendars_within_period_per_resource[resource.id][resource.calendar_id] = resource_default_work_intervals[resource.id]

        return calendars_within_period_per_resource

    def _format_leave(self, leave, resource_hours_per_day, resource_hours_per_week, ranges_to_remove, start_day, end_day, locale):
        leave_start_day = leave[0].date()
        leave_end_day = leave[1].date()
        tz = timezone(self.tz or self.env.user.tz)

        while leave_start_day <= leave_end_day:
            if not self._is_fully_flexible():
                hours = self.calendar_id.hours_per_day
                # only days inside the original period
                if leave_start_day >= start_day and leave_start_day <= end_day:
                    resource_hours_per_day[self.id][leave_start_day] -= hours
                year_and_week = weeknumber(babel_locale_parse(locale), leave_start_day)
                resource_hours_per_week[self.id][year_and_week] -= hours

            range_start_datetime = tz.localize(datetime.combine(leave_start_day, datetime.min.time()))
            range_end_datetime = tz.localize(datetime.combine(leave_start_day, datetime.max.time()))
            ranges_to_remove.append((range_start_datetime, range_end_datetime, self.env['resource.calendar.attendance']))
            leave_start_day += timedelta(days=1)

    def _get_flexible_resource_valid_work_intervals(self, start, end):
        if not self:
            return {}, {}, {}

        assert all(record._is_flexible() for record in self)
        assert start.tzinfo and end.tzinfo

        start_day, end_day = start.date(), end.date()
        week_start_date, week_end_date = start, end
        locale = babel_locale_parse(get_lang(self.env).code)
        week_start_date = weekstart(locale, start)
        week_end_date = weekend(locale, end)
        end_week = weeknumber(locale, week_end_date)[1]

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

            for day, hours in duration_per_day.items():
                day_working_hours = min(hours, resource.calendar_id.hours_per_day)
                # only days inside the original period
                if day >= start_day and day <= end_day:
                    resource_hours_per_day[resource.id][day] = day_working_hours

                week = weeknumber(babel_locale_parse(locale), day)
                if week[1] <= end_week:
                    resource_hours_per_week[resource.id][week] = min(resource.calendar_id.full_time_required_hours, day_working_hours + resource_hours_per_week[resource.id][week])

        for calendar, resources in calendar_resources.items():
            domain = [('calendar_id', '=', False)] if not calendar else None
            leave_intervals = (calendar or self.env['resource.calendar'])._leave_intervals_batch(min_start_date, max_end_date, resources, domain)
            for resource_id, leaves in leave_intervals.items():
                if not resource_id:
                    continue

                ranges_to_remove = []
                for leave in leaves._items:
                    resource_by_id[resource_id]._format_leave(leave, resource_hours_per_day, resource_hours_per_week, ranges_to_remove, start_day, end_day, locale)

                resource_work_intervals[resource_id] -= Intervals(ranges_to_remove)

        for resource_id, work_intervals in resource_work_intervals.items():
            tz = timezone(resource_by_id[resource_id].tz or self.env.user.tz)
            resource_work_intervals[resource_id] = work_intervals & Intervals([(start.astimezone(tz), end.astimezone(tz), self.env['resource.calendar.attendance'])])

        return resource_work_intervals, resource_hours_per_day, resource_hours_per_week

    def _get_flexible_resource_work_hours(self, intervals, flexible_resources_hours_per_day, flexible_resources_hours_per_week, work_hours_per_day=None):
        assert self._is_flexible()

        if self._is_fully_flexible():
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
        for day, hours in interval_duration_per_day.items():
            week = weeknumber(babel_locale_parse(locale), day)
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
