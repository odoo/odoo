from odoo import models


class HrDepartureWizard(models.TransientModel):
    _inherit = 'hr.departure.wizard'

    def action_register_departure(self):
        future_timesheets = self._get_future_timesheets()
        future_timesheets.write({
            'holiday_id': False,
            'global_leave_id': False,
        })
        return super().action_register_departure()
