# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrDepartureWizard(models.TransientModel):
    _name = 'hr.departure.wizard'
    _description = 'Departure Wizard'

    def _get_employee_departure_date(self, employee):
        return employee.departure_date

    def _get_default_departure_date(self):
        if len(active_ids := self.env.context.get('active_ids', [])) == 1:
            employee = self.env['hr.employee'].browse(active_ids[0])
            departure_date = self._get_employee_departure_date(employee)
        else:
            departure_date = False

        return departure_date or fields.Date.today()

    departure_reason_id = fields.Many2one("hr.departure.reason", default=lambda self: self.env['hr.departure.reason'].search([], limit=1), required=True)
    departure_description = fields.Html(string="Additional Information")
    departure_date = fields.Date(string="Departure Date", required=True, default=_get_default_departure_date)
    employee_ids = fields.Many2many(
        'hr.employee', string='Employees', required=True,
        default=lambda self: self.env.context.get('active_ids', []),
    )

    def action_register_departure(self):
        employees = self.employee_ids
        for employee in employees:
            if self.env.context.get('toggle_active') and employee.active:
                employee.with_context(no_wizard=True).toggle_active()
        employees.write({
            'departure_reason_id': self.departure_reason_id,
            'departure_description': self.departure_description,
            'departure_date': self.departure_date,
        })
