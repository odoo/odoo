# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class Employee(models.Model):
    _inherit = 'hr.employee'

    employee_cars_count = fields.Integer(compute="_compute_employee_cars_count", string="Cars", groups="fleet.fleet_group_manager")
    car_ids = fields.One2many(
        'fleet.vehicle', 'driver_employee_id', string='Vehicles (private)',
        groups="fleet.fleet_group_manager,hr.group_hr_user",
    )
    mobility_card = fields.Char(groups="fleet.fleet_group_user")

    def action_open_employee_cars(self):
        self.ensure_one()

        return {
            "type": "ir.actions.act_window",
            "res_model": "fleet.vehicle.assignation.log",
            "views": [[self.env.ref("hr_fleet.fleet_vehicle_assignation_log_employee_view_list").id, "tree"], [False, "form"]],
            "domain": [("driver_employee_id", "in", self.ids)],
            "context": dict(self._context, default_driver_id=self.user_id.partner_id.id, default_driver_employee_id=self.id),
            "name": "History Employee Cars",
        }

    def _compute_employee_cars_count(self):
        rg = self.env['fleet.vehicle.assignation.log']._read_group([
            ('driver_employee_id', 'in', self.ids),
        ], ['driver_employee_id'], ['driver_employee_id'])
        cars_count = {r['driver_employee_id'][0]: r['driver_employee_id_count'] for r in rg}
        for employee in self:
            employee.employee_cars_count = cars_count.get(employee.id, 0)

    @api.constrains('address_home_id')
    def _check_address_home_id(self):
        no_address = self.filtered(lambda r: not r.address_home_id)
        car_ids = self.env['fleet.vehicle'].sudo().search([
            ('driver_employee_id', 'in', no_address.ids),
        ])
        # Prevent from removing employee address when linked to a car
        if car_ids:
            raise ValidationError(_('Cannot remove address from employees with linked cars.'))


    def write(self, vals):
        res = super().write(vals)
        #Update car partner when it is changed on the employee
        if 'address_home_id' in vals:
            car_ids = self.env['fleet.vehicle'].sudo().search([
                ('driver_employee_id', 'in', self.ids),
                ('driver_id', 'in', self.mapped('address_home_id').ids),
            ])
            if car_ids:
                car_ids.write({'driver_id': vals['address_home_id']})
        if 'mobility_card' in vals:
            #NOTE: keeping it as a search on driver_id but we might be able to use driver_employee_id in the future
            vehicles = self.env['fleet.vehicle'].search([('driver_id', 'in', (self.user_id.partner_id | self.sudo().address_home_id).ids)])
            vehicles._compute_mobility_card()
        return res

class EmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    mobility_card = fields.Char(readonly=True)
