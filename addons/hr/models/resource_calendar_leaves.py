# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta, UTC
from zoneinfo import ZoneInfo

from odoo import api, models


class ResourceCalendarLeaves(models.Model):
    _inherit = 'resource.calendar.leaves'

    @api.depends('date_from')
    def _compute_calendar_ids(self):
        """Set the calendar of resource leaves from the employee's current version.

        A leave of an employee's resource gets the calendar of the employee's
        ``version_id`` if it starts within that version's ``date_start`` /
        ``date_end`` (in the version's timezone); leaves starting outside it are
        left untouched. Leaves of resources without employee version use the
        ``resource`` behavior (the resource's calendar).
        """
        def date2datetime(date, tz):
            dt = datetime.fromordinal(date.toordinal())
            return dt.replace(tzinfo=tz).astimezone(UTC).replace(tzinfo=None)

        leaves_by_contract = self.grouped(lambda leave: leave.resource_id.employee_id.version_id)
        # set aside leaves without version_id for super
        remaining = leaves_by_contract.pop(
            self.env['hr.version'],
            self.env['resource.calendar.leaves'],
        )
        for contract, leaves in leaves_by_contract.items():
            tz = ZoneInfo(contract._get_tz())
            start_dt = date2datetime(contract.date_start, tz)
            end_dt = date2datetime(contract.date_end + timedelta(days=1), tz) if contract.date_end else datetime.max
            # only modify leaves that fall under the active contract
            leaves.filtered(
                lambda leave: leave.date_from and start_dt <= leave.date_from < end_dt
            ).calendar_ids = [contract.resource_calendar_id]

        super(ResourceCalendarLeaves, remaining)._compute_calendar_ids()
