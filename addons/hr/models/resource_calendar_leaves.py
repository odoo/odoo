# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from pytz import timezone, utc

from odoo import models


class ResourceCalendarLeaves(models.Model):
    _inherit = 'resource.calendar.leaves'

    def _compute_calendar_id(self):
        def date2datetime(date, tz):
            dt = datetime.fromordinal(date.toordinal())
            return tz.localize(dt).astimezone(utc).replace(tzinfo=None)

        leaves_by_contract = self.grouped(lambda leave: leave.resource_id.employee_id.version_id)
        # set aside leaves without version_id for super
        remaining = leaves_by_contract.pop(
            self.env['hr.version'],
            self.env['resource.calendar.leaves'],
        )
        for contract, leaves in leaves_by_contract.items():
            tz = timezone(contract.resource_calendar_id.tz or 'UTC')
            start_dt = date2datetime(contract.contract_date_start or contract.date_version, tz)
            end_dt = date2datetime(contract.contract_date_end, tz) if (contract.contract_date_end or contract.get_next_version_start()) else datetime.max
            # only modify leaves that fall under the active contract
            leaves.filtered(
                lambda leave: start_dt <= leave.date_from < end_dt
            ).calendar_id = contract.resource_calendar_id

        super(ResourceCalendarLeaves, remaining)._compute_calendar_id()
