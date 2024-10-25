# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrEmployeeDeparture(models.Model):
    _inherit = ['hr.employee.departure']

    do_unassign_campany_car = fields.Boolean("Release Company Car", default=lambda self: self.env.user.has_group('fleet.fleet_group_user'))

    def action_register_departure(self):
        super().action_register_departure()
        if self.do_unassign_campany_car:
            self._unassign_campany_car()

    def _unassign_campany_car(self):
        """Find all fleet.vehichle.assignation.log records that link to the employee, if there is no
        end date or end date > departure date, update the date. Also check fleet.vehicle to see if
        there is any record with its dirver_id to be the employee, set them to False."""
        drivers = self.employee_id.user_id.partner_id | self.employee_id.sudo().work_contact_id
        assignations = self.env['fleet.vehicle.assignation.log'].search([
            ('driver_id', 'in', drivers.ids),
            '|',
                ('date_end', '=', False),
                ('date_end', '>', self.departure_date),
        ])
        assignations.write({'date_end': self.departure_date})

        cars = self.env['fleet.vehicle'].search([('driver_id', 'in', drivers.ids)])
        if cars:
            cars.write({'driver_id': False, 'driver_employee_id': False})
            for car in cars:
                self.employee_id.message_post(body=self.env._("The vehicle %s has been freed", car.display_name))
                car.message_post(body=self.env._("The vehicle has been freed due to the end of collaboration with %s", self.employee_id.name))

        cars = self.env['fleet.vehicle'].search([('future_driver_id', 'in', drivers.ids)])
        if cars:
            cars.write({'future_driver_id': False, 'future_driver_employee_id': False})
            for car in cars:
                self.employee_id.message_post(body=self.env._("Employee has been removed from %s future driver list", car.display_name))
                car.message_post(body=self.env._("The future driver has been freed due to the end of collaboration with %s", self.employee_id.name))
