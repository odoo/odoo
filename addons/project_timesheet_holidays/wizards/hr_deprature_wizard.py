from odoo import models


class HrDepartureWizard(models.TransientModel):
    _inherit = 'hr.departure.wizard'

    def action_register_departure(self):
        if self.departure_date and self.employee_ids:
            future_timesheets = self.env['account.analytic.line'].sudo().search([
                ('employee_id', 'in', self.employee_ids.ids),
                ('date', '>', self.departure_date),
            ])
            if future_timesheets:
                future_timesheets.write({
                    'holiday_id': False,
                    'global_leave_id': False,
                })
        return super().action_register_departure()
