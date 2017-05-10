# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import api, fields, models


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
        index=True, related='resource_id.calendar_id')

    @api.model
    def create(self, values):
        if not values.get('resource_id'):
            resource = self.env['resource.resource'].create({
                'name': values.get(self._rec_name)
            })
            values['resource_id'] = resource.id
        return super(ResourceMixin, self).create(values)

    def get_work_days_count(self, from_datetime, to_datetime, calendar=None):
        """ Return the number of work days for the resource, taking into account
        leaves. An optional calendar can be given in case multiple calendars can
        be used on the resource. """
        return self.get_work_days_data(from_datetime, to_datetime, calendar=calendar)['days']

    def get_work_days_data(self, from_datetime, to_datetime, calendar=None):
        days_count = 0.0
        total_work_time = timedelta()
        calendar = calendar or self.resource_calendar_id
        for day_intervals in calendar._iter_work_intervals(
                from_datetime, to_datetime, self.resource_id.id,
                compute_leaves=True):
            theoric_hours = self.get_day_work_hours_count(day_intervals[0][0].date(), calendar=calendar)
            work_time = sum((interval[1] - interval[0] for interval in day_intervals), timedelta())
            total_work_time += work_time
            days_count += round((work_time.total_seconds() / 3600 / theoric_hours) * 4) / 4
        return {
            'days': days_count,
            'hours': total_work_time.total_seconds() / 3600,
        }

    def iter_works(self, from_datetime, to_datetime, calendar=None):
        calendar = calendar or self.resource_calendar_id
        return calendar._iter_work_intervals(from_datetime, to_datetime, self.resource_id.id)

    def iter_work_hours_count(self, from_datetime, to_datetime, calendar=None):
        calendar = calendar or self.resource_calendar_id
        return calendar._iter_work_hours_count(from_datetime, to_datetime, self.resource_id.id)

    def get_leaves_day_count(self, from_datetime, to_datetime, calendar=None):
        """ Return the number of leave days for the resource, taking into account
        attendances. An optional calendar can be given in case multiple calendars
        can be used on the resource. """
        days_count = 0.0
        calendar = calendar or self.resource_calendar_id
        for day_intervals in calendar._iter_leave_intervals(from_datetime, to_datetime, self.resource_id.id):
            theoric_hours = self.get_day_work_hours_count(day_intervals[0][0].date(), calendar=calendar)
            leave_time = sum((interval[1] - interval[0] for interval in day_intervals), timedelta())
            days_count += round((leave_time.total_seconds()/3600 / theoric_hours) * 4) / 4
        return days_count

    def iter_leaves(self, from_datetime, to_datetime, calendar=None):
        calendar = calendar or self.resource_calendar_id
        return calendar._iter_leave_intervals(from_datetime, to_datetime, self.resource_id.id)

    def get_start_work_hour(self, day_dt, calendar=None):
        calendar = calendar or self.resource_calendar_id
        work_intervals = calendar._get_day_work_intervals(day_dt, resource_id=self.resource_id.id)
        return work_intervals and work_intervals[0][0]

    def get_end_work_hour(self, day_dt, calendar=None):
        calendar = calendar or self.resource_calendar_id
        work_intervals = calendar._get_day_work_intervals(day_dt, resource_id=self.resource_id.id)
        return work_intervals and work_intervals[-1][1]

    def get_day_work_hours_count(self, day_date, calendar=None):
        calendar = calendar or self.resource_calendar_id
        attendances = calendar._get_day_attendances(day_date, False, False)
        if not attendances:
            return 0
        return sum(float(i.hour_to) - float(i.hour_from) for i in attendances)
