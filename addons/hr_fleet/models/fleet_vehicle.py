# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    mobility_card = fields.Char(compute='_compute_mobility_card', store=True)
    driver_employee_id = fields.Many2one(
        'hr.employee', 'Driver (Employee)',
        compute='_compute_driver_employee_id', store=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        tracking=True,
    )
    driver_employee_name = fields.Char(related="driver_employee_id.name")
    future_driver_employee_id = fields.Many2one(
        'hr.employee', 'Future Driver (Employee)',
        compute='_compute_future_driver_employee_id', store=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        tracking=True,
    )

    @api.depends('driver_id')
    def _compute_driver_employee_id(self):
        for vehicle in self:
            if vehicle.driver_id:
                vehicle.driver_employee_id = self.env['hr.employee'].search([
                    ('address_home_id', '=', vehicle.driver_id.id),
                ], limit=1)
            else:
                vehicle.driver_employee_id = False

    @api.depends('future_driver_id')
    def _compute_future_driver_employee_id(self):
        for vehicle in self:
            if vehicle.future_driver_id:
                vehicle.future_driver_employee_id = self.env['hr.employee'].search([
                    ('address_home_id', '=', vehicle.future_driver_id.id),
                ], limit=1)
            else:
                vehicle.future_driver_employee_id = False

    @api.depends('driver_id')
    def _compute_mobility_card(self):
        for vehicle in self:
            employee = self.env['hr.employee']
            if vehicle.driver_id:
                employee = employee.search([('address_home_id', '=', vehicle.driver_id.id)], limit=1)
                if not employee:
                    employee = employee.search([('user_id.partner_id', '=', vehicle.driver_id.id)], limit=1)
            vehicle.mobility_card = employee.mobility_card

    def _update_create_write_vals(self, vals):
        if 'driver_employee_id' in vals:
            partner = False
            if vals['driver_employee_id']:
                employee = self.env['hr.employee'].sudo().browse(vals['driver_employee_id'])
                partner = employee.address_home_id.id
            vals['driver_id'] = partner
        elif 'driver_id' in vals:
            # Reverse the process if we can find a single employee
            employee = False
            if vals['driver_id']:
                # Limit to 2, we only care about the first one if he is the only one
                employee_ids = self.env['hr.employee'].sudo().search([
                    ('address_home_id', '=', vals['driver_id'])
                ], limit=2)
                if len(employee_ids) == 1:
                    employee = employee_ids[0].id
            vals['driver_employee_id'] = employee

        # Same for future driver
        if 'future_driver_employee_id' in vals:
            partner = False
            if vals['future_driver_employee_id']:
                employee = self.env['hr.employee'].sudo().browse(vals['future_driver_employee_id'])
                partner = employee.address_home_id.id
            vals['future_driver_id'] = partner
        elif 'future_driver_id' in vals:
            # Reverse the process if we can find a single employee
            employee = False
            if vals['future_driver_id']:
                # Limit to 2, we only care about the first one if he is the only one
                employee_ids = self.env['hr.employee'].sudo().search([
                    ('address_home_id', '=', vals['future_driver_id'])
                ], limit=2)
                if len(employee_ids) == 1:
                    employee = employee_ids[0].id
            vals['future_driver_employee_id'] = employee

    @api.model
    def create(self, vals):
        self._update_create_write_vals(vals)
        return super().create(vals)

    def write(self, vals):
        self._update_create_write_vals(vals)
        if 'driver_employee_id' in vals:
            for vehicle in self:
                if vehicle.driver_employee_id and vehicle.driver_employee_id.id != vals['driver_employee_id']:
                    partners_to_unsubscribe = vehicle.driver_id.ids
                    employee = vehicle.driver_employee_id
                    if employee and employee.user_id.partner_id:
                        partners_to_unsubscribe.append(employee.user_id.partner_id.id)
                    vehicle.message_unsubscribe(partner_ids=partners_to_unsubscribe)
        return super().write(vals)

    def action_open_employee(self):
        self.ensure_one()
        return {
            'name': _('Related Employee'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee',
            'view_mode': 'form',
            'res_id': self.driver_employee_id.id,
        }
