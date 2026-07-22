from odoo import models


class HrDepartureWizard(models.TransientModel):
    _inherit = 'hr.departure.wizard'

    def _get_future_timesheets(self):
        future_timesheets = super()._get_future_timesheets()
        return future_timesheets.filtered(
            lambda t: not t.timesheet_invoice_id or t.timesheet_invoice_id.state != 'posted'
        )
