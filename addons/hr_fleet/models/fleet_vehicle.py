# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    mobility_card = fields.Char(compute='_compute_mobility_card', store=True)

    @api.depends('driver_id')
    def _compute_mobility_card(self):
        for vehicle in self:
            employee = self.env['hr.employee']
            if vehicle.driver_id:
                employee = employee.search([('address_home_id', '=', vehicle.driver_id.id)], limit=1)
                if not employee:
                    employee = employee.search([('user_id.partner_id', '=', vehicle.driver_id.id)], limit=1)
            vehicle.mobility_card = employee.mobility_card

    def write(self, vals):
        if 'driver_id' in vals:
            for vehicle in self:
                if vehicle.driver_id and vehicle.driver_id.id != vals['driver_id']:
                    # Retrieve private address and user's partner
                    partners_to_unsubscribe = vehicle.driver_id.ids
                    employee = self.env['hr.employee'].search([('address_home_id', '=', vehicle.driver_id.id)])
                    if employee and employee.user_id.partner_id:
                        partners_to_unsubscribe.append(employee.user_id.partner_id.id)
                    vehicle.message_unsubscribe(partner_ids=partners_to_unsubscribe)
        return super().write(vals)

class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def write(self, vals):
        res = super().write(vals)
        if 'mobility_card' in vals:
            vehicles = self.env['fleet.vehicle'].search([('driver_id', 'in', (self.user_id.partner_id | self.sudo().address_home_id).ids)])
            vehicles._compute_mobility_card()
        return res
