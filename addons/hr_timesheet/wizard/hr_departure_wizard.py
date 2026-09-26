from odoo import models


class HrDepartureWizard(models.TransientModel):
    _inherit = 'hr.departure.wizard'

    def action_register_departure(self):
        employee_ids = self.employee_ids.ids
        departure_date = self.departure_date
        action = super().action_register_departure()
        if departure_date and employee_ids:
            future_timesheets = self.env['account.analytic.line'].sudo().search([
                ('employee_id', 'in', employee_ids),
                ('date', '>', departure_date),
            ])
            if future_timesheets:
                future_timesheets.unlink()
        return action
