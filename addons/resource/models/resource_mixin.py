# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from pytz import utc

from odoo import api, fields, models
from .utils import get_attendance_intervals_days_data, timezone_datetime, WorkIntervals


class ResourceMixin(models.AbstractModel):
    _name = 'resource.mixin'
    _description = 'Resource Mixin'

    resource_id = fields.Many2one(
        'resource.resource', 'Resource',
        auto_join=True, index=True, ondelete='restrict', required=True)
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env.company,
        index=True, related='resource_id.company_id', precompute=True, store=True, readonly=False)
    resource_calendar_id = fields.Many2one(
        'resource.calendar', 'Working Hours',
        default=lambda self: self.env.company.resource_calendar_id,
        index=True, related='resource_id.calendar_id', store=True, readonly=False)
    tz = fields.Selection(
        string='Timezone', related='resource_id.tz', readonly=False,
        help="This field is used in order to define in which timezone the resources will work.")

    @api.model_create_multi
    def create(self, vals_list):
        resources_vals_list = []
        calendar_ids = [vals['resource_calendar_id'] for vals in vals_list if vals.get('resource_calendar_id')]
        calendars_tz = {calendar.id: calendar.tz for calendar in self.env['resource.calendar'].browse(calendar_ids)}
        for vals in vals_list:
            if not vals.get('resource_id'):
                resources_vals_list.append(
                    self._prepare_resource_values(
                        vals,
                        vals.pop('tz', False) or calendars_tz.get(vals.get('resource_calendar_id'))
                    )
                )
        if resources_vals_list:
            resources = self.env['resource.resource'].create(resources_vals_list)
            resources_iter = iter(resources.ids)
            for vals in vals_list:
                if not vals.get('resource_id'):
                    vals['resource_id'] = next(resources_iter)
        return super(ResourceMixin, self.with_context(check_idempotence=True)).create(vals_list)

    def _prepare_resource_values(self, vals, tz):
        resource_vals = {'name': vals.get(self._rec_name)}
        if tz:
            resource_vals['tz'] = tz
        company_id = vals.get('company_id', self.env.company.id)
        if company_id:
            resource_vals['company_id'] = company_id
        calendar_id = vals.get('resource_calendar_id')
        if calendar_id:
            resource_vals['calendar_id'] = calendar_id
        return resource_vals

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)

        resource_default = {}
        if 'company_id' in default:
            resource_default['company_id'] = default['company_id']
        if 'resource_calendar_id' in default:
            resource_default['calendar_id'] = default['resource_calendar_id']
        resources = [record.resource_id for record in self]
        resources_to_copy = self.env['resource.resource'].concat(*resources)
        new_resources = resources_to_copy.copy(resource_default)
        for resource, vals in zip(new_resources, vals_list):
            vals['resource_id'] = resource.id
            vals['company_id'] = resource.company_id.id
            vals['resource_calendar_id'] = resource.calendar_id.id
        return vals_list

    def _get_calendars(self, date_from=None):
        return {resource.id: resource.resource_calendar_id or resource.company_id.resource_calendar_id for resource in self}

    def _get_work_days_data_batch(self, from_datetime, to_datetime, compute_leaves=True, calendar=None, domain=None):
        """
            By default the resource calendar is used, but it can be
            changed using the `calendar` argument.

            `domain` is used in order to recognise the leaves to take,
            None means default value ('time_type', '=', 'leave')

            Returns a dict {'days': n, 'hours': h} containing the
            quantity of working time expressed as days and as hours.
        """
        result = defaultdict(lambda: {'days': 0, 'hours': 0})

        # naive datetimes are made explicit in UTC
        from_datetime = timezone_datetime(from_datetime)
        to_datetime = timezone_datetime(to_datetime)

        intervals = self._get_work_intervals_batch(from_datetime, to_datetime, domain, compute_leaves=compute_leaves)

        for resource in self:
            result[resource.id] = get_attendance_intervals_days_data(intervals[resource])
        return result

    def _get_leave_days_data_batch(self, from_datetime, to_datetime, domain=None):
        """
            By default the resource calendar is used, but it can be
            changed using the `calendar` argument.

            `domain` is used in order to recognise the leaves to take,
            None means default value ('time_type', '=', 'leave')

            Returns a dict {'days': n, 'hours': h} containing the number of leaves
            expressed as days and as hours.
        """

        # naive datetimes are made explicit in UTC
        from_datetime = timezone_datetime(from_datetime)
        to_datetime = timezone_datetime(to_datetime)

        attendances = self._get_attendance_intervals_batch(from_datetime, to_datetime)
        leaves = self._get_leave_intervals_batch(from_datetime, to_datetime, domain)

        return {
            resource: get_attendance_intervals_days_data(attendances[resource] & leaves[resource])
            for resource in self
        }

    def _adjust_to_calendar(self, start, end):
        resource_results = self.resource_id._adjust_to_calendar(start, end)
        # change dict keys from resources to associated records.
        return {
            record: resource_results[record.resource_id]
            for record in self
        }

    def _list_work_time_per_day(self, from_datetime, to_datetime, calendar=None, domain=None):
        """
            By default the resource calendar is used, but it can be
            changed using the `calendar` argument.

            `domain` is used in order to recognise the leaves to take,
            None means default value ('time_type', '=', 'leave')

            Returns a list of tuples (day, hours) for each day
            containing at least an attendance.
        """
        # naive datetimes are made explicit in UTC
        if not from_datetime.tzinfo:
            from_datetime = from_datetime.replace(tzinfo=utc)
        if not to_datetime.tzinfo:
            to_datetime = to_datetime.replace(tzinfo=utc)
        compute_leaves = self.env.context.get('compute_leaves', True)

        all_intervals = self._get_work_intervals_batch(from_datetime, to_datetime, domain, compute_leaves=compute_leaves)

        result = {}
        for resource in self:
            record_result = defaultdict(float)
            for start, stop, meta in all_intervals[resource]:
                record_result[start.date()] += (stop - start).total_seconds() / 3600
            result[resource.id] = sorted(record_result.items())

        return result

    def _get_calendar_periods(self, start, stop):
        """
        :param datetime start: the start of the period
        :param datetime stop: the stop of the period
        This method can be overridden in other modules where it's possible to have different resource calendars for an
        employee depending on the date.
        """
        calendar_periods_by_employee = {}
        for employee in self:
            calendar = employee.resource_calendar_id or employee.company_id.resource_calendar_id
            calendar_periods_by_employee[employee] = [(start, stop, calendar)]
        return calendar_periods_by_employee

    def _get_attendance_intervals_batch(self, start_dt, end_dt, domain=None, tz=None, calendar=False, lunch=False, inverse_result=False):
        intervals_per_resource = self.resource_id._get_attendance_intervals_batch(start_dt, end_dt, domain, tz)
        return {
            resource: intervals_per_resource.get(resource.resource_id, WorkIntervals([]))
            for resource in self
        }

    def _get_leave_intervals_batch(self, start_dt, end_dt, domain=None, tz=None):
        intervals_per_resource = self.resource_id._get_leave_intervals_batch(start_dt, end_dt, domain, tz)
        return {
            resource: intervals_per_resource.get(resource.resource_id, WorkIntervals([]))
            for resource in self
        }

    def _get_work_intervals_batch(self, start_dt, end_dt, domain=None, tz=None, calendar=None, compute_leaves=True):
        intervals_per_resource = self.resource_id._get_work_intervals_batch(start_dt, end_dt, domain, tz, calendar, compute_leaves)
        return {
            resource: intervals_per_resource.get(resource.resource_id, WorkIntervals([]))
            for resource in self
        }

    def _get_absence_intervals_batch(self, start_dt, end_dt, domain=None, tz=None, calendar=None):
        intervals_per_resource = self.resource_id._get_absence_intervals_batch(start_dt, end_dt, domain, tz, calendar)
        return {
            resource: intervals_per_resource.get(resource.resource_id, WorkIntervals([]))
            for resource in self
        }

    def _get_attendance_intervals(self, start_dt, end_dt, domain=None, tz=None, calendar=False, lunch=False, inverse_result=False):
        self.ensure_one()
        return self._get_attendance_intervals_batch(start_dt, end_dt, domain, tz)[self]

    def _get_leave_intervals(self, start_dt, end_dt, domain=None, tz=None):
        self.ensure_one()
        return self._get_leave_intervals_batch(start_dt, end_dt, domain, tz)[self]

    def _get_work_intervals(self, start_dt, end_dt, domain=None, tz=None, calendar=None, compute_leaves=True):
        self.ensure_one()
        return self._get_work_intervals_batch(start_dt, end_dt, domain, tz, calendar, compute_leaves)[self]

    def _get_absence_intervals(self, start_dt, end_dt, domain=None, tz=None, calendar=None):
        self.ensure_one()
        return self._get_absence_intervals_batch(start_dt, end_dt, domain, tz, calendar)[self]
