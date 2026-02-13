# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import UTC

from odoo import api, fields, models
from odoo.tools.date_utils import localized


class ResourceMixin(models.AbstractModel):
    _name = 'resource.mixin'
    _description = 'Resource Mixin'

    resource_id = fields.Many2one(
        'resource.resource', 'Resource',
        bypass_search_access=True, index=True, ondelete='restrict', required=True)
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env.company,
        index=True, related='resource_id.company_id', precompute=True, store=True, readonly=False)
    resource_calendar_id = fields.Many2one(
        'resource.calendar', 'Working Hours',
        default=lambda self: self.env.company.resource_calendar_id,
        index=True, related='resource_id.calendar_id', store=True, readonly=False)
    hours_per_week = fields.Float(string="Hours per Week", related='resource_id.hours_per_week', readonly=False)
    hours_per_day = fields.Float(string="Hours per Day", related='resource_id.hours_per_day', readonly=False)
    tz = fields.Selection(
        string='Timezone', related='resource_id.tz', readonly=False,
        help="This field is used in order to define in which timezone the resources will work.")

    @api.model_create_multi
    def create(self, vals_list):
        resources_vals_list = []
        company_ids = [vals['company_id'] for vals in vals_list if vals.get('company_id')]
        companies_tz = {company.id: company.tz for company in self.env['res.company'].browse(company_ids)}
        for vals in vals_list:
            if not vals.get('resource_id'):
                resources_vals_list.append(
                    self._prepare_resource_values(
                        vals,
                        vals.pop('tz', False) or companies_tz.get(vals.get('company_id'))
                    )
                )
            elif not vals.get('tz'):
                # Write the tz in the vals_list to forward to the version creation
                vals['tz'] = self.env['resource.resource'].browse(vals.get('resource_id')).tz
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
        return {resource.id: resource.resource_calendar_id for resource in self}

    def _get_hours_per_week_batch(self, date_from=None):
        return {resource.id: resource.hours_per_week for resource in self}

    def _get_hours_per_day_batch(self, date_from=None):
        return {resource.id: resource.hours_per_day for resource in self}

    def _get_work_days_data_batch(self, from_datetime, to_datetime, compute_leaves=True, calendar=None, domain=None):
        """
            By default the resource calendar is used, but it can be
            changed using the `calendar` argument.

            `domain` is used in order to recognise the leaves to take,
            None means default value ('time_type', '=', 'leave')

            Returns a dict {'days': n, 'hours': h} containing the
            quantity of working time expressed as days and as hours.
        """
        resources = self.mapped('resource_id')
        mapped_employees = {e.resource_id.id: e.id for e in self}
        result = {}

        # naive datetimes are made explicit in UTC
        from_datetime = localized(from_datetime)
        to_datetime = localized(to_datetime)

        if calendar:
            mapped_resources = {calendar: self.resource_id}
        else:
            calendar_by_resource = self._get_calendars(from_datetime)
            mapped_resources = defaultdict(lambda: self.env['resource.resource'])
            for resource in self:
                mapped_resources[calendar_by_resource[resource.id]] |= resource.resource_id

        for calendar, calendar_resources in mapped_resources.items():
            resources_per_tz = calendar_resources._get_resources_per_tz()
            # actual hours per day
            if compute_leaves:
                intervals = calendar._work_intervals_batch(from_datetime, to_datetime, resources_per_tz, domain)
            else:
                intervals = calendar._attendance_intervals_batch(from_datetime, to_datetime, resources_per_tz)

            for calendar_resource in calendar_resources:
                result[calendar_resource.id] = calendar._get_attendance_intervals_days_data(intervals[calendar_resource.id])

        # convert "resource: result" into "employee: result"
        return {mapped_employees[r.id]: result[r.id] for r in resources}

    def _get_leave_days_data_batch(self, from_datetime, to_datetime, calendar=None, domain=None):
        """
            By default the resource calendar is used, but it can be
            changed using the `calendar` argument.

            `domain` is used in order to recognise the leaves to take,
            None means default value ('time_type', '=', 'leave')

            Returns a dict {'days': n, 'hours': h} containing the number of leaves
            expressed as days and as hours.
        """
        resources = self.mapped('resource_id')
        mapped_employees = {e.resource_id.id: e.id for e in self}
        result = {}

        # naive datetimes are made explicit in UTC
        from_datetime = localized(from_datetime)
        to_datetime = localized(to_datetime)

        resource_per_calendar = defaultdict(lambda: self.env['resource.resource'])
        for resource in self:
            resource_per_calendar[calendar or resource.resource_calendar_id] |= resource.resource_id

        for calendar, resources in resource_per_calendar.items():
            # handle fully flexible resources by returning the length of the whole interval
            # since we do not take into account leaves for fully flexible resources
            if not calendar:
                days = (to_datetime - from_datetime).days
                hours = (to_datetime - from_datetime).total_seconds() / 3600
                for resource in resources:
                    result[resource.id] = {'days': days, 'hours': hours}
                continue

            # compute actual hours per day
            resources_per_tz = resources._get_resources_per_tz()
            attendances = calendar._attendance_intervals_batch(from_datetime, to_datetime, resources_per_tz)
            leaves = calendar._leave_intervals_batch(from_datetime, to_datetime, resources_per_tz, domain)

            for resource in resources:
                result[resource.id] = calendar._get_attendance_intervals_days_data(
                    attendances[resource.id] & leaves[resource.id]
                )

        # convert "resource: result" into "employee: result"
        return {mapped_employees[r.id]: result[r.id] for r in resources}

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
        result = {}
        records_by_calendar = defaultdict(lambda: self.env[self._name])
        for record in self:
            records_by_calendar[calendar or record.resource_calendar_id or record.company_id.resource_calendar_id] += record

        # naive datetimes are made explicit in UTC
        if not from_datetime.tzinfo:
            from_datetime = from_datetime.replace(tzinfo=UTC)
        if not to_datetime.tzinfo:
            to_datetime = to_datetime.replace(tzinfo=UTC)
        compute_leaves = self.env.context.get('compute_leaves', True)

        for calendar, records in records_by_calendar.items():
            resources_per_tz = records.resource_id._get_resources_per_tz()
            all_intervals = calendar._work_intervals_batch(from_datetime, to_datetime, resources_per_tz, domain, compute_leaves=compute_leaves)
            for record in records:
                intervals = all_intervals[record.resource_id.id]
                record_result = defaultdict(float)
                for start, stop, _meta in intervals:
                    record_result[start.date()] += (stop - start).total_seconds() / 3600
                result[record.id] = sorted(record_result.items())
        return result
