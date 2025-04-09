# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrEmployeeDepartureWizard(models.TransientModel):
    _inherit = 'hr.employee.departure.wizard'

    do_cancel_time_off_requests = fields.Boolean(
        string="Cancel Time Off Requests",
        default=True,
        help="Set the running allocations validity's end and delete future time off.")

    def _get_departure_values(self):
        res = super()._get_departure_values()
        res['departure_do_cancel_time_off_requests'] = self.do_cancel_time_off_requests
        return res
