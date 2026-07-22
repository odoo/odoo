from odoo import models


class HrEmployeeDeparture(models.Model):
    _inherit = 'hr.employee.departure'

    def _get_future_timesheets(self):
        future_timesheets = super()._get_future_timesheets()
        return future_timesheets.filtered(
            lambda t: not t.reinvoice_move_id or t.reinvoice_move_id.state != 'posted'
        )
