# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
import pytz

from odoo import models
from odoo.addons.resource.models.utils import Intervals


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def _get_employee_batch_calendar_intervals(self, start, stop, leave_domain=None, lunch=False):
        self.ensure_one()
        relevant_contracts_domain = [
            '&',
            '&',
            '|',
            '|',
            '|',
            '&',
            ('date_start', '>=', start),
            ('date_end', '<=', stop),
            '&',
            ('date_start', '<=', start),
            ('date_end', '>=', start),
            '&',
            ('date_start', '<=', stop),
            ('date_end', '>=', stop),
            '&',
            ('date_start', '<=', stop),
            ('date_end', '=', False),
            ('employee_id', '=', self.id),
            ('state', 'in', ['open', 'close'])
        ]
        valid_contracts = self.env['hr.contract'].sudo().search(relevant_contracts_domain)
        if valid_contracts:
            expected_attendances = Intervals()
            for contract in valid_contracts:
                max_start = max(datetime.combine(contract.date_start, datetime.min.time()).astimezone(
                    pytz.timezone(self._get_tz())), start)
                if contract.date_end:
                    min_end = min(datetime.combine(contract.date_end, datetime.max.time()).astimezone(
                        pytz.timezone(self._get_tz())), stop)
                else:
                    min_end = stop
                expected_attendances |= contract.resource_calendar_id._attendance_intervals_batch(max_start, min_end, self.resource_id, lunch=lunch)[self.resource_id.id]
                if leave_domain:
                    leave_intervals = contract.resource_calendar_id._leave_intervals_batch(
                        start, stop, self.resource_id, domain=leave_domain
                    )
                    expected_attendances -= leave_intervals[False] | leave_intervals[self.resource_id.id]
            return expected_attendances
        else:
            return super()._get_employee_batch_calendar_intervals(start, stop, leave_domain=leave_domain, lunch=lunch)
