# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrEmployeeDeparture(models.Model):
    _inherit = 'hr.employee.departure'

    do_unassign_company_car = fields.Boolean(
        string="Release Company Car",
        default=lambda self: self.env.user.has_group('fleet.fleet_group_user'),
    )

    def action_register(self):
        super().action_register()
        self.filtered('do_unassign_company_car')._unassign_company_car()

    def _unassign_company_car(self):
        """Find all fleet.vehicle.assignation.log records that link to the employee, if there is no
        end date or end date > departure date, update the date. Also check fleet.vehicle to see if
        there is any record with its driver_id to be the employee, set them to False."""
        for dep in self:
            drivers = dep.employee_id.user_id.partner_id | dep.employee_id.work_contact_id
            assignations_sudo = dep.sudo().env['fleet.vehicle.assignation.log'].search([
                ('driver_id', 'in', drivers.ids),
                '|',
                    ('date_end', '=', False),
                    ('date_end', '>', dep.departure_date),
            ])
            assignations_sudo.write({'date_end': dep.departure_date})

        all_drivers = self.employee_id.user_id.partner_id | self.employee_id.work_contact_id
        cars_sudo = self.sudo().env['fleet.vehicle'].search([('driver_id', 'in', all_drivers.ids)])
        if cars_sudo:
            for car in cars_sudo:
                car.driver_employee_id.message_post(body=self.env._(
                    "The vehicle %(car)s has been freed",
                    car=car.display_name,
                ))
                car.message_post(body=self.env._(
                    "The vehicle has been freed due to the end of collaboration with %(employee)s",
                    employee=car.driver_employee_id.name,
                ))
            cars_sudo.write({'driver_id': False, 'driver_employee_id': False})

        cars_sudo = self.sudo().env['fleet.vehicle'].search([('future_driver_id', 'in', all_drivers.ids)])
        if cars_sudo:
            for car in cars_sudo:
                car.future_driver_employee_id.message_post(body=self.env._(
                    "Employee has been removed from %(car)s future driver list",
                    car=car.display_name,
                ))
                car.message_post(body=self.env._(
                    "The future driver has been removed due to the end of collaboration with %(employee)s",
                    employee=car.future_driver_employee_id.name,
                ))
            cars_sudo.write({'future_driver_id': False, 'future_driver_employee_id': False})
