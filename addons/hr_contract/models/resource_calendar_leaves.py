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

        Resource = self.env['resource.resource']
        CalendarLeaves = self.env['resource.calendar.leaves']
        leaves_by_resource = defaultdict(lambda: CalendarLeaves, {Resource: CalendarLeaves})
        for leave in self:
            leaves_by_resource[leave.resource_id] += leave
        # pass leaves without resource_id to super
        remaining = leaves_by_resource.pop(Resource)

        for resource, leaves in leaves_by_resource.items():
            contract = resource.employee_id.contract_id
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
