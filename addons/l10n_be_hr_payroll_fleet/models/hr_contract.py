# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrContract(models.Model):
    _inherit = 'hr.contract'

    car_id = fields.Many2one('fleet.vehicle', string='Company Car',
        domain=lambda self: self._get_available_cars_domain(),
        default=lambda self: self.env['fleet.vehicle'].search([('driver_id', '=', self.employee_id.address_home_id.id)], limit=1),
        help="Employee's company car.")
    car_atn = fields.Float(compute='_compute_car_atn_and_costs', string='ATN Company Car')
    company_car_total_depreciated_cost = fields.Float(compute='_compute_car_atn_and_costs')
    available_cars_amount = fields.Integer(compute='_compute_available_cars_amount', string='Number of available cars')
    new_car = fields.Boolean('Request a new car')
    new_car_model_id = fields.Many2one('fleet.vehicle.model', string="Model", domain=lambda self: self._get_possible_model_domain())
    max_unused_cars = fields.Integer(compute='_compute_max_unused_cars')

    @api.depends('car_id', 'new_car', 'new_car_model_id')
    def _compute_car_atn_and_costs(self):
        for contract in self:
            if contract.car_id:
                contract.car_atn = contract.car_id.atn
                contract.company_car_total_depreciated_cost = contract.car_id.total_depreciated_cost
            elif contract.new_car and contract.new_car_model_id:
                contract.car_atn = contract.new_car_model_id.default_atn
                contract.company_car_total_depreciated_cost = contract.new_car_model_id.default_total_depreciated_cost

    @api.depends('name')
    def _compute_available_cars_amount(self):
        for contract in self:
            contract.available_cars_amount = self.env['fleet.vehicle'].search_count([('driver_id', '=', False)])

    @api.depends('name')
    def _compute_max_unused_cars(self):
        params = self.env['ir.config_parameter'].sudo()
        max_unused_cars = params.get_param('l10n_be_hr_payroll_fleet.max_unused_cars', default=3)
        for contract in self:
            contract.max_unused_cars = int(max_unused_cars)

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        super(HrContract, self)._onchange_employee_id()
        self.car_id = self.env['fleet.vehicle'].search([('driver_id', '=', self.employee_id.address_home_id.id)], limit=1)
        return {'domain': {'car_id': self._get_available_cars_domain()}}

    def _get_available_cars_domain(self):
        return ['|', ('driver_id', '=', False), ('driver_id', '=', self.employee_id.address_home_id.id)]

    def _get_possible_model_domain(self):
        return [('can_be_requested', '=', True)]
