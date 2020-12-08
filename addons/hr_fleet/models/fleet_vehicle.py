# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    mobility_card = fields.Char(compute='_compute_mobility_card', store=True)

    @api.depends('driver_id', 'driver_id.user_ids.employee_id.mobility_card')
    def _compute_mobility_card(self):
        for vehicle in self:
            vehicle.mobility_card = vehicle.driver_id.user_ids[:1].employee_id.mobility_card

    def create_driver_history(self, driver_id):
        super().create_driver_history(driver_id)
        driver = self.env['res.partner'].browse(driver_id)
        self._update_license_plate(driver)

    def _update_license_plate(self, driver, old_drivers=False):
        HrEmployee = self.env['hr.employee'].sudo()
        # replace old driver license plate as blank
        if old_drivers:
            employee = old_drivers.mapped('user_ids.employee_id') | HrEmployee.search([('address_home_id', 'in', old_drivers.ids)])
            employee.sudo().write({'license_plate': False})
        if driver:
            for vehicle in self:
                employees = driver.mapped('user_ids.employee_id') | HrEmployee.search([('address_home_id', '=', driver.id)])
                employees.sudo().write({'license_plate': vehicle.license_plate})

    def write(self, vals):
        old_drivers = self.mapped('driver_id')
        res = super().write(vals)
        if any(key in ['driver_id', 'license_plate'] for key in vals):
            for vehicle in self:
                vehicle._update_license_plate(vehicle.driver_id, old_drivers)
        return res
