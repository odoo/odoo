# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import timedelta, timezone

from odoo import api, fields, models
from odoo.tools import float_utils

# This will generate quarter of days
ROUNDING_FACTOR = 4


class ResourceMixin(models.AbstractModel):
    _name = "resource.mixin"
    _description = 'Resource Mixin'

    resource_id = fields.Many2one(
        'resource.resource', 'Resource',
        auto_join=True, index=True, ondelete='restrict', required=True)
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env['res.company']._company_default_get(),
        index=True, related='resource_id.company_id', store=True)
    resource_calendar_id = fields.Many2one(
        'resource.calendar', 'Working Hours',
        default=lambda self: self.env['res.company']._company_default_get().resource_calendar_id,
        index=True, related='resource_id.calendar_id', store=True)

    @api.model
    def create(self, values):
        if not values.get('resource_id'):
            resource = self.env['resource.resource'].create({
                'name': values.get(self._rec_name)
            })
            values['resource_id'] = resource.id
        return super(ResourceMixin, self).create(values)

    @api.multi
    def copy_data(self, default=None):
        if default is None:
            default = {}
        resource = self.resource_id.copy()
        default['resource_id'] = resource.id
        default['company_id'] = resource.company_id.id
        default['resource_calendar_id'] = resource.calendar_id.id
        return super(ResourceMixin, self).copy_data(default)

    def get_work_days_data(self, from_datetime, to_datetime, compute_leaves=True, calendar=None, domain=None):
        """
            By default the resource calendar is used, but it can be
            changed using the `calendar` argument.

            `domain` is used in order to recognise the leaves to take,
            None means default value ('time_type', '=', 'leave')

            Returns a dict {'days': n, 'hours': h} containing the
            quantity of working time expressed as days and as hours.
        """

        calendar = calendar or self.resource_calendar_id

        # naive datetimes are made explicit in UTC
        if not from_datetime.tzinfo:
            from_datetime = from_datetime.replace(tzinfo=timezone.utc)
        if not to_datetime.tzinfo:
            to_datetime = to_datetime.replace(tzinfo=timezone.utc)

        # retrieve attendances and leaves (with one extra day margin)
        from_full = from_datetime + timedelta(days=-1)
        to_full = to_datetime + timedelta(days=1)
        attendances = calendar._attendance_intervals(from_full, to_full)
        leaves = calendar._leave_intervals(from_full, to_full, self.resource_id, domain)

        # compute actual and total hours per day
        day_total = defaultdict(float)
        for start, stop, meta in (attendances):
            day_total[start.date()] += (stop - start).total_seconds() / 3600


        day_hours = defaultdict(float)
        hours = (attendances - leaves) if compute_leaves else attendances
        for start, stop, meta in hours:
            start, stop = max(start, from_datetime), min(stop, to_datetime)
            if start < stop:
                day_hours[start.date()] += (stop - start).total_seconds() / 3600

        # compute number of days as quarters
        days = sum(
            float_utils.round(ROUNDING_FACTOR * day_hours[day] / day_total[day]) / ROUNDING_FACTOR
            for day in day_hours
        )
        return {
            'days': days,
            'hours': sum(day_hours.values()),
        }

    def get_leave_days_data(self, from_datetime, to_datetime, calendar=None, domain=None):
        """
            By default the resource calendar is used, but it can be
            changed using the `calendar` argument.

            `domain` is used in order to recognise the leaves to take,
            None means default value ('time_type', '=', 'leave')

            Returns a dict {'days': n, 'hours': h} containing the number of leaves
            expressed as days and as hours.
        """

        calendar = calendar or self.resource_calendar_id

        # naive datetimes are made explicit in UTC
        if not from_datetime.tzinfo:
            from_datetime = from_datetime.replace(tzinfo=timezone.utc)
        if not to_datetime.tzinfo:
            to_datetime = to_datetime.replace(tzinfo=timezone.utc)

        # retrieve attendances and leaves (with one extra day margin)
        from_full = from_datetime + timedelta(days=-1)
        to_full = to_datetime + timedelta(days=1)
        attendances = calendar._attendance_intervals(from_full, to_full)
        leaves = calendar._leave_intervals(from_full, to_full, self.resource_id, domain)

        # compute actual and total hours per day
        day_total = defaultdict(float)
        for start, stop, meta in attendances:
            day_total[start.date()] += (stop - start).total_seconds() / 3600

        day_hours = defaultdict(float)
        for start, stop, meta in (attendances & leaves):
            start, stop = max(start, from_datetime), min(stop, to_datetime)
            if start < stop:
                day_hours[start.date()] += (stop - start).total_seconds() / 3600

        # compute number of days as quarters
        days = sum(
            float_utils.round(ROUNDING_FACTOR * day_hours[day] / day_total[day]) / ROUNDING_FACTOR
            for day in day_hours
        )
        return {
            'days': days,
            'hours': sum(day_hours.values()),
        }

    def list_work_time_per_day(self, from_datetime, to_datetime, calendar=None, domain=None):
        """
            By default the resource calendar is used, but it can be
            changed using the `calendar` argument.

            `domain` is used in order to recognise the leaves to take,
            None means default value ('time_type', '=', 'leave')

            Returns a list of tuples (day, hours) for each day
            containing at least an attendance.
        """

        calendar = calendar or self.resource_calendar_id
        result = defaultdict(float)

        for work in calendar._work_intervals(from_datetime, to_datetime, resource=self.resource_id, domain=domain):
            hours = (work[1] - work[0]).total_hours()
            result[work[0].date()] += hours
        return sorted(result.items())

    def list_leaves(self, from_datetime, to_datetime, calendar=None, domain=None):
        """
            By default the resource calendar is used, but it can be
            changed using the `calendar` argument.

            `domain` is used in order to recognise the leaves to take,
            None means default value ('time_type', '=', 'leave')

            Returns a list of tuples (day, hours, resource.calendar.leaves)
            for each leave in the calendar.
        """

        calendar = calendar or self.resource_calendar_id
        result = []

        attendances = calendar._attendance_intervals(from_datetime, to_datetime)
        leaves = calendar._leave_intervals(from_datetime, to_datetime, resource=self.resource_id, domain=domain)

        for leave in (leaves & attendances):
            hours = (leave[1] - leave[0]).total_hours()
            result.append((leave[0].date(), hours, leave[-1]))
        return result
