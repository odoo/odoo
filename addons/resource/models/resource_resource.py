# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from dateutil.relativedelta import relativedelta
from pytz import timezone

from odoo import api, fields, models
from odoo.addons.base.models.res_partner import _tz_get

from .utils import timezone_datetime, make_aware, Intervals


class ResourceResource(models.Model):
    _name = "resource.resource"
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
    user_id = fields.Many2one('res.users', string='User', help='Related user name for the resource to manage its access.')
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
        default=lambda self: self._context.get('tz') or self.env.user.tz or 'UTC')

    _sql_constraints = [
        ('check_time_efficiency', 'CHECK(time_efficiency>0)', 'Time efficiency must be strictly positive'),
    ]

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

    def write(self, values):
        if self.env.context.get('check_idempotence') and len(self) == 1:
            values = {
                fname: value
                for fname, value in values.items()
                if self._fields[fname].convert_to_write(self[fname], self) != value
            }
        if not values:
            return True
        return super().write(values)

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
        start, revert_start_tz = make_aware(start)
        end, revert_end_tz = make_aware(end)
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
        start_datetime = timezone_datetime(start)
        end_datetime = timezone_datetime(end)
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

    def _is_flexible(self):
        """ An employee is considered flexible if the field flexible_hours is True on the calendar
            or the employee is not assigned any calendar, in which case is considered as Fully flexible.
        """
        self.ensure_one()
        return self._is_fully_flexible() or (self.calendar_id and self.calendar_id.flexible_hours)
