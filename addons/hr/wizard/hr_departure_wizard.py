# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrDepartureWizard(models.TransientModel):
    _name = 'hr.departure.wizard'
    _description = 'Departure Wizard'

    def _get_default_departure_date(self):
        if len(active_ids := self.env.context.get('active_ids', [])) == 1:
            employee = self.env['hr.employee'].browse(active_ids[0])
            departure_date = employee and employee._get_departure_date()
        else:
            departure_date = False

        return departure_date or fields.Date.today()

    def _get_default_employee_ids(self):
        active_ids = self.env.context.get('active_ids', [])
        if active_ids:
            return self.env['hr.employee'].browse(active_ids).filtered(lambda e: e.company_id in self.env.companies)
        return self.env['hr.employee']

    def _get_domain_employee_ids(self):
        return [('active', '=', True), ('company_id', 'in', self.env.companies.ids)]

    departure_reason_id = fields.Many2one("hr.departure.reason", required=True,
        default=lambda self: self.env['hr.departure.reason'].search([], limit=1),
    )
    departure_description = fields.Html(string="Additional Information")
    departure_date = fields.Date(string="Departure Date", required=True, default=_get_default_departure_date)
    employee_ids = fields.Many2many(
        'hr.employee', string='Employees', required=True,
        default=_get_default_employee_ids,
        context={'active_test': False},
        domain=_get_domain_employee_ids,
    )

    def action_register_departure(self):
        for employee in self.employee_ids.filtered(lambda emp: emp.active):
            if self.env.context.get('employee_termination', False):
                employee.with_context(no_wizard=True).action_archive()
        self.employee_ids.write({
            'departure_reason_id': self.departure_reason_id,
            'departure_description': self.departure_description,
            'departure_date': self.departure_date,
        })
