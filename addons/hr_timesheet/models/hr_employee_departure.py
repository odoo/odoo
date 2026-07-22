from odoo import models
from odoo.fields import Domain


class HrEmployeeDeparture(models.Model):
    _inherit = 'hr.employee.departure'

    def _get_future_timesheets(self):
        employee_domains = []
        for departure in self:
            if departure.departure_date and departure.employee_id:
                employee_domains.append(Domain.AND([
                    Domain('employee_id', '=', departure.employee_id.id),
                    Domain('date', '>', departure.departure_date),
                ]))
        if not employee_domains:
            return self.env['account.analytic.line']
        final_domain = Domain.AND([
            Domain.OR(employee_domains),
            Domain('project_id', '!=', False),
        ])
        return self.env['account.analytic.line'].sudo().search(final_domain)

    def action_register(self):
        self._get_future_timesheets().unlink()
        return super().action_register()
