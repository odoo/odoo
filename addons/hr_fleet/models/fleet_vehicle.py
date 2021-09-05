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
    future_driver_employee_id = fields.Many2one(
        'hr.employee', 'Future Driver (Employee)',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        tracking=True,
    )
    fleet_is_internal = fields.Boolean(related='fleet_id.internal')

    @api.depends('driver_id')
    def _compute_mobility_card(self):
        for vehicle in self:
            employee = self.env['hr.employee']
            if vehicle.driver_id:
                employee = employee.search([('address_home_id', '=', vehicle.driver_id.id)], limit=1)
                if not employee:
                    employee = employee.search([('user_id.partner_id', '=', vehicle.driver_id.id)], limit=1)
            vehicle.mobility_card = employee.mobility_card

    @api.constrains('driver_employee_id', 'future_driver_employee_id')
    def _constrain_employee_has_address(self):
        wrongs = self.filtered(lambda v: (
            (v.driver_employee_id and not v.driver_employee_id.address_home_id) or
            (v.future_driver_employee_id and not v.future_driver_employee_id.address_home_id)
        ))
        if wrongs:
            raise ValidationError(_(
                'The following vehicles have invalid employees: %s\n'
                'Please assign addresses to the employees you want to assign a car to.'
            ) % wrongs.mapped('name'))

    def _get_driver_history_data(self, vals):
        res = super()._get_driver_history_data(vals)
        if self.fleet_is_internal and 'driver_employee_id' in vals:
            res['driver_employee_id'] = vals['driver_employee_id']
        return res

    def action_accept_driver_change(self):
        super(FleetVehicle, self.filtered(lambda v: not v.fleet_id.internal)).action_accept_driver_change()
        #Unfortunate code duplication to avoid creating unwanted vehicle logs
        internals = self.filtered(lambda v: v.fleet_id.internal)
        for vehicle in internals:
            if vehicle.vehicle_type == 'bike':
                vehicle.future_driver_id.sudo().write({'plan_to_change_bike': False})
            if vehicle.vehicle_type == 'car':
                vehicle.future_driver_id.sudo().write({'plan_to_change_car': False})
            vehicle.driver_employee_id = vehicle.future_driver_employee_id
            vehicle.future_driver_employee_id = False

    def _update_create_write_vals(self, vals):
        # wbr NOTE: can't use inverse without breaking history
        # We do not want to link vehicles to employee when their fleet is not internal
        #  but since this method is called within the write function we are not guaranteed
        #  to always have one record, check if all fleet are internal
        # This is an edge case, it is better not to link an employee to a car when they should than to link
        #  against cars when they shouldn't, usually you will not update multiple vehicles from many different fleets
        is_internal = len(self) > 0 and len(self.filtered(lambda v: not v.fleet_id.internal)) == 0
        # Use fleet_id in vals if it gets updated
        if 'fleet_id' in vals:
            fleet_id = self.env['fleet.category'].sudo().browse(vals['fleet_id'])
            is_internal = fleet_id.internal

        # Compute partner from employee
        if 'driver_employee_id' in vals:
            partner = False
            if vals['driver_employee_id']:
                employee = self.env['hr.employee'].sudo().browse(vals['driver_employee_id'])
                partner = employee.address_home_id.id
            vals['driver_id'] = partner
        elif 'driver_id' in vals and is_internal:
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
        elif 'future_driver_id' in vals and is_internal:
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

        # Cases when fleet_id changes but driver_id and future_driver_id do not
        # 1: not internal -> remove eployee related data
        # 2: internal -> compute employee for each vehicle in the case no employee can be computed for the address
        #       we remove it's current driver_id
        if 'fleet_id' in vals:
            if not is_internal:
                vals['driver_employee_id'] = False
                vals['future_driver_employee_id'] = False
            else:
                # Prefetch all employees we will need
                employees = self.env['hr.employee'].search([
                    ('address_home_id', 'in', (self.driver_id | self.future_driver_id).ids),
                ])
                for vehicle in self:
                    if 'driver_employee_id' not in vals:
                        driver_id = vals['driver_id'] if 'driver_id' in vals else vehicle.driver_id.id
                        driver_employee_id = employees.filtered(lambda e: e.address_home_id.id == driver_id)
                        if len(driver_employee_id) == 1:
                            vehicle.driver_employee_id = driver_employee_id
                        else:
                            vehicle.write({
                                'driver_id': False,
                                'driver_employee_id': False,
                            })
                    if 'future_driver_employee_id' not in vals:
                        future_driver_id = vals['future_driver_id'] if 'future_driver_id' in vals else \
                            vehicle.future_driver_id.id
                        future_driver_employee_id = employees.filtered(lambda e: (
                            e.address_home_id.id == future_driver_id
                        ))
                        if len(future_driver_employee_id) == 1:
                            vehicle.future_driver_employee_id = future_driver_employee_id
                        else:
                            vehicle.write({
                                'future_driver_id': False,
                                'future_driver_employee_id': False,
                            })

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
