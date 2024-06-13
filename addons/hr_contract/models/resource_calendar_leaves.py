# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import datetime
from pytz import timezone, utc

from odoo import models


class ResourceCalendarLeaves(models.Model):
    _inherit = 'resource.calendar.leaves'

    def _compute_calendar_id(self):
        def date2datetime(date, tz):
            dt = datetime.fromordinal(date.toordinal())
            return tz.localize(dt).astimezone(utc).replace(tzinfo=None)

        contracts = self.env['hr.contract'].search([
            ('state', '=', 'open'),
            ('employee_id.resource_id', 'in', self.resource_id.ids),
        ])

        CalendarLeaves = self.env['resource.calendar.leaves']
        leaves_by_resource_id = defaultdict(lambda: CalendarLeaves, {False: CalendarLeaves})
        for leave in self:
            leaves_by_resource_id[leave.resource_id.id] += leave
        # pass leaves without resource_id to super
        remaining = leaves_by_resource_id.pop(False)

        for resource_id, leaves in leaves_by_resource_id.items():
            contract = contracts.filtered_domain([('employee_id.resource_id', '=', resource_id)])
            if not contract:
                remaining += leaves
                continue
            tz = timezone(contract.resource_calendar_id.tz or 'UTC')
            start_dt = date2datetime(contract.date_start, tz)
            end_dt = date2datetime(contract.date_end, tz) if contract.date_end else datetime.max
            # only modify leaves that fall under the active contract
            leaves.filtered(
                lambda leave: start_dt <= leave.date_from < end_dt
            ).calendar_id = contract.resource_calendar_id

        super(ResourceCalendarLeaves, remaining)._compute_calendar_id()
