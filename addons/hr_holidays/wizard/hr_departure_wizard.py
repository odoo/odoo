# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrDepartureWizard(models.TransientModel):
    _inherit = 'hr.departure.wizard'

    do_cancel_time_off_requests = fields.Boolean(
        string="Cancel Time Off Requests",
        default=True,
        help="Set the running allocations validity's end and delete future time off.")
