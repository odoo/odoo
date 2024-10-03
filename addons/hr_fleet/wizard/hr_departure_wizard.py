# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrDepartureWizard(models.TransientModel):
    _inherit = 'hr.departure.wizard'

    release_campany_car = fields.Boolean("Release Company Car", default=lambda self: self.env.user.has_group('fleet.fleet_group_user'))

    def action_register_departure(self):
        super(HrDepartureWizard, self).action_register_departure()
        if self.release_campany_car:
            self._free_company_car()

    def _free_company_car(self):
        """Find all fleet.vehichle.assignation.log records that link to the employee, if there is no 
        end date or end date > departure date, update the date. Also check fleet.vehicle to see if 
        there is any record with its driver_id to be the employee, set them to False."""
        employees = self.with_context(active_test=False).employee_ids  # find archived (in super)
        drivers = employees.user_id.partner_id | employees.sudo().work_contact_id
        assignations = self.env['fleet.vehicle.assignation.log'].search([
            ('driver_id', 'in', drivers.ids),
            '|',
                ('date_end', '=', False),
                ('date_end', '>', self.departure_date),
        ])
        assignations.write({'date_end': self.departure_date})
        cars = self.env['fleet.vehicle'].search([('driver_id', 'in', drivers.ids)])
        cars.write({'driver_id': False, 'driver_employee_id': False})
