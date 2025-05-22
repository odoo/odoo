# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
import pytz

from odoo import api, fields, models
from odoo.tools.intervals import Intervals


class ResourceCalendar(models.Model):
    _inherit = "resource.calendar"

    associated_leaves_count = fields.Integer("Time Off Count", compute='_compute_associated_leaves_count')
    global_leave_ids = fields.Many2many('hr.leave.public.holiday', 'calendar_public_holiday_rel', 'calendar_id', 'leave_id',
        string='Global Time Off')

    def _compute_associated_leaves_count(self):
        leaves_read_group = self.env['resource.calendar.leaves']._read_group(
            [('resource_id', '=', False), ('calendar_id', 'in', self.ids)],
            ['calendar_id'],
            ['__count'],
        )
        result = {calendar.id if calendar else 'global': count for calendar, count in leaves_read_group}
        global_leave_count = result.get('global', 0)
        for calendar in self:
            calendar.associated_leaves_count = result.get(calendar.id, 0) + global_leave_count

    def _leave_intervals_batch(self, start_dt, end_dt, resources=None, domain=None, tz=None, any_calendar=False):
        base = super()._leave_intervals_batch(start_dt, end_dt, resources=resources, domain=domain, tz=tz, any_calendar=any_calendar)
        if not resources:
            resources = self.env['resource.resource']
            resources_list = [resources]
        else:
            resources_list = list(resources) + [self.env['resource.resource']]
        result = defaultdict(list)
        tz_dates = {}
        domain = [
            ('date_from', '<=', end_dt.astimezone(pytz.utc).replace(tzinfo=None)),
            ('date_to', '>=', start_dt.astimezone(pytz.utc).replace(tzinfo=None)),
        ]
        if not any_calendar:
            domain = domain + [('resource_calendar_ids', 'in', [False, self.id])]

        all_leaves = self.env['hr.leave.public.holiday'].search(domain)
        for leave in all_leaves:
            leave_date_from = leave.date_from
            leave_date_to = leave.date_to
            leave_company = leave.company_id
            tz = tz or pytz.timezone(self.tz)
            if (tz, start_dt) in tz_dates:
                start = tz_dates[tz, start_dt]
            else:
                start = start_dt.astimezone(tz)
                tz_dates[tz, start_dt] = start
            if (tz, end_dt) in tz_dates:
                end = tz_dates[tz, end_dt]
            else:
                end = end_dt.astimezone(tz)
                tz_dates[tz, end_dt] = end
            dt0 = leave_date_from.astimezone(tz)
            dt1 = leave_date_to.astimezone(tz)
            for resource in resources_list:
                if resource and leave_company != resource.company_id:
                    continue
                result[resource.id].append((max(start, dt0), min(end, dt1), self.env['resource.calendar.leaves']))
        for resource in base:
            if resource not in result:
                continue
            base[resource] |= Intervals(result[resource])
        return base
