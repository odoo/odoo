# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    mobility_card = fields.Char(compute='_compute_mobility_card', store=True)
    driver_employee_id = fields.Many2one(
        'hr.employee', 'Driver (Employee)',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        tracking=True,
    )
    driver_employee_name = fields.Char(related="driver_employee_id.name")
    future_driver_employee_id = fields.Many2one(
        'hr.employee', 'Future Driver (Employee)',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        tracking=True,
    )

    @api.depends('driver_id')
    def _compute_mobility_card(self):
        for vehicle in self:
            employee = self.env['hr.employee']
            if vehicle.driver_id:
                employee = employee.search([('user_id.partner_id', '=', vehicle.driver_id.id)], limit=1)
            vehicle.mobility_card = employee.mobility_card

    def _update_create_write_vals(self, vals):
        if 'driver_employee_id' in vals:
            partner = False
            if vals['driver_employee_id']:
                employee = self.env['hr.employee'].sudo().browse(vals['driver_employee_id'])
                partner = employee.user_id.partner_id.id
            vals['driver_id'] = partner

        # Same for future driver
        if 'future_driver_employee_id' in vals:
            partner = False
            if vals['future_driver_employee_id']:
                employee = self.env['hr.employee'].sudo().browse(vals['future_driver_employee_id'])
                partner = employee.user_id.partner_id.id
            vals['future_driver_id'] = partner

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._update_create_write_vals(vals)
        return super().create(vals_list)

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

    def open_assignation_logs(self):
        action = super().open_assignation_logs()
        action['views'] = [[self.env.ref('hr_fleet.fleet_vehicle_assignation_log_view_list').id, 'tree']]
        return action
