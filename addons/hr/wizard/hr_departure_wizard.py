# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrDepartureWizard(models.TransientModel):
    _name = 'hr.departure.wizard'
    _description = 'Departure Wizard'

    departure_reason = fields.Selection([
        ('fired', 'Fired'),
        ('resigned', 'Resigned'),
        ('retired', 'Retired')
    ], string="Departure Reason", default="fired")
    departure_description = fields.Text(string="Additional Information")
    departure_date = fields.Date(string="Departure Date", required=True, default=fields.Date.today)
    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True,
        default=lambda self: self.env.context.get('active_id', None),
    )
    archive_private_address = fields.Boolean('Archive Private Address', default=True)

    def action_register_departure(self):
        employee = self.employee_id
        employee.departure_reason = self.departure_reason
        employee.departure_description = self.departure_description
        employee.departure_date = self.departure_date

        if self.archive_private_address:
            # ignore contact links to internal users
            private_address = employee.address_home_id
            if private_address and private_address.active and not self.env['res.users'].search([('partner_id', '=', private_address.id)]):
                private_address.toggle_active()
