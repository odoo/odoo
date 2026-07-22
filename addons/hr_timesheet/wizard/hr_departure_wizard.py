from odoo import models


class HrDepartureWizard(models.TransientModel):
    _inherit = 'hr.departure.wizard'

    def _get_future_timesheets(self):
        if not self.departure_date or not self.employee_ids:
            return self.env['account.analytic.line']

        return self.env['account.analytic.line'].sudo().search([
            ('employee_id', 'in', self.employee_ids.ids),
            ('date', '>', self.departure_date),
            ('project_id', '!=', False),
        ])

    def action_register_departure(self):
        future_timesheets = self._get_future_timesheets()
        future_timesheets.unlink()
        return super().action_register_departure()
