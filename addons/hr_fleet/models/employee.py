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
    license_plate = fields.Char(compute="_compute_license_plate", search="_search_license_plate", groups="hr.group_hr_user")
    mobility_card = fields.Char(groups="fleet.fleet_group_user")

    def action_open_employee_cars(self):
        self.ensure_one()

        return {
            "type": "ir.actions.act_window",
            "res_model": "fleet.vehicle.assignation.log",
            "views": [[self.env.ref("hr_fleet.fleet_vehicle_assignation_log_employee_view_list").id, "list"], [False, "form"]],
            "domain": [("driver_employee_id", "in", self.ids)],
            "context": dict(self._context, default_driver_id=self.user_id.partner_id.id, default_driver_employee_id=self.id),
            "name": "History Employee Cars",
        }

    @api.depends('private_car_plate', 'car_ids.license_plate')
    def _compute_license_plate(self):
        for employee in self:
            if employee.private_car_plate and employee.car_ids.license_plate:
                employee.license_plate = ' '.join(employee.car_ids.filtered('license_plate').mapped('license_plate') + [employee.private_car_plate])
            else:
                employee.license_plate = ' '.join(employee.car_ids.filtered('license_plate').mapped('license_plate')) or employee.private_car_plate

    def _search_license_plate(self, operator, value):
        employees = self.env['hr.employee'].search(['|', ('car_ids.license_plate', operator, value), ('private_car_plate', operator, value)])
        return [('id', 'in', employees.ids)]

    def _compute_employee_cars_count(self):
        rg = self.env['fleet.vehicle.assignation.log']._read_group([
            ('driver_employee_id', 'in', self.ids),
        ], ['driver_employee_id'], ['__count'])
        cars_count = {driver_employee.id: count for driver_employee, count in rg}
        for employee in self:
            employee.employee_cars_count = cars_count.get(employee.id, 0)

    @api.constrains('work_contact_id')
    def _check_work_contact_id(self):
        no_address = self.filtered(lambda r: not r.work_contact_id)
        car_ids = self.env['fleet.vehicle'].sudo().search([
            ('driver_employee_id', 'in', no_address.ids),
        ])
        # Prevent from removing employee address when linked to a car
        if car_ids:
            raise ValidationError(_('Cannot remove address from employees with linked cars.'))

    def write(self, vals):
        if 'user_id' in vals:
            self._sync_employee_cars(self.env['res.users'].browse(vals['user_id']))
        res = super().write(vals)
        #Update car partner when it is changed on the employee
        if 'work_contact_id' in vals:
            car_ids = self.env['fleet.vehicle'].sudo().search([
                ('driver_employee_id', 'in', self.ids),
                ('driver_id', 'in', self.mapped('work_contact_id').ids),
            ])
            if car_ids:
                car_ids.write({'driver_id': vals['work_contact_id']})
        if 'mobility_card' in vals:
            #NOTE: keeping it as a search on driver_id but we might be able to use driver_employee_id in the future
            vehicles = self.env['fleet.vehicle'].search([('driver_id', 'in', (self.user_id.partner_id | self.sudo().work_contact_id).ids)])
            vehicles._compute_mobility_card()
        return res

    def _sync_employee_cars(self, user):
        if self.work_contact_id and self.work_contact_id != user.partner_id:
            cars = self.env['fleet.vehicle'].search(['|', ('future_driver_id', '=', self.work_contact_id.id), ('driver_id', '=', self.work_contact_id.id), ('company_id', '=', self.company_id.id)])
            for car in cars:
                if car.future_driver_id == self.work_contact_id:
                    car.future_driver_id = user.partner_id
                if car.driver_id == self.work_contact_id:
                    car.driver_id = user.partner_id


class EmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    mobility_card = fields.Char(readonly=True)
