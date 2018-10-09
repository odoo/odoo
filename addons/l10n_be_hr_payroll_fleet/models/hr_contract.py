# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrContract(models.Model):
    _inherit = 'hr.contract'

    car_id = fields.Many2one('fleet.vehicle', string='Company Car',
        default=lambda self: self.env['fleet.vehicle'].search([('driver_id', '=', self.employee_id.address_home_id.id)], limit=1),
        track_visibility="onchange",
        help="Employee's company car.")
    car_atn = fields.Float(compute='_compute_car_atn_and_costs', string='ATN Company Car', store=True)
    company_car_total_depreciated_cost = fields.Float(compute='_compute_car_atn_and_costs', store=True)
    available_cars_amount = fields.Integer(compute='_compute_available_cars_amount', string='Number of available cars')
    new_car = fields.Boolean('Request a new car')
    # YTI: Check if could be removed
    new_car_model_id = fields.Many2one('fleet.vehicle.model', string="Model", domain=lambda self: self._get_possible_model_domain())
    max_unused_cars = fields.Integer(compute='_compute_max_unused_cars')
    acquisition_date = fields.Date(related='car_id.acquisition_date', readonly=False)
    car_value = fields.Float(related="car_id.car_value", readonly=False)
    fuel_type = fields.Selection(related="car_id.fuel_type", readonly=False)
    co2 = fields.Float(related="car_id.co2", readonly=False)
    driver_id = fields.Many2one('res.partner', related="car_id.driver_id", readonly=False)
    car_open_contracts_count = fields.Integer(compute='_compute_car_open_contracts_count')
    recurring_cost_amount_depreciated = fields.Float(
        compute='_compute_recurring_cost_amount_depreciated',
        inverse="_inverse_recurring_cost_amount_depreciated")

    @api.depends('car_id', 'new_car', 'new_car_model_id', 'car_id.total_depreciated_cost',
        'car_id.atn', 'new_car_model_id.default_atn', 'new_car_model_id.default_total_depreciated_cost')
    def _compute_car_atn_and_costs(self):
        for contract in self:
            if not contract.new_car and contract.car_id:
                contract.car_atn = contract.car_id.atn
                contract.company_car_total_depreciated_cost = contract.car_id.total_depreciated_cost
            elif contract.new_car and contract.new_car_model_id:
                contract.car_atn = contract.new_car_model_id.default_atn
                contract.company_car_total_depreciated_cost = contract.new_car_model_id.default_total_depreciated_cost

    @api.depends('car_id.log_contracts.state')
    def _compute_car_open_contracts_count(self):
        for contract in self:
            contract.car_open_contracts_count = len(contract.car_id.log_contracts.filtered(
                lambda c: c.state == 'open').ids)

    @api.depends('car_open_contracts_count', 'car_id.log_contracts.recurring_cost_amount_depreciated')
    def _compute_recurring_cost_amount_depreciated(self):
        for contract in self:
            if contract.car_open_contracts_count == 1:
                contract.recurring_cost_amount_depreciated = contract.car_id.log_contracts.filtered(
                    lambda c: c.state == 'open'
                ).recurring_cost_amount_depreciated
            else:
                contract.recurring_cost_amount_depreciated = 0.0

    def _inverse_recurring_cost_amount_depreciated(self):
        for contract in self:
            if contract.car_open_contracts_count == 1:
                contract.car_id.log_contracts.filtered(
                    lambda c: c.state == 'open'
                ).recurring_cost_amount_depreciated = contract.recurring_cost_amount_depreciated

    @api.depends('name')
    def _compute_available_cars_amount(self):
        for contract in self:
            contract.available_cars_amount = self.env['fleet.vehicle'].search_count([('driver_id', '=', False)])

    @api.depends('name')
    def _compute_max_unused_cars(self):
        params = self.env['ir.config_parameter'].sudo()
        max_unused_cars = params.get_param('l10n_be_hr_payroll_fleet.max_unused_cars', default=1000)
        for contract in self:
            contract.max_unused_cars = int(max_unused_cars)

    @api.onchange('transport_mode_car', 'transport_mode_public', 'transport_mode_others')
    def _onchange_transport_mode(self):
        super(HrContract, self)._onchange_transport_mode()
        if not self.transport_mode_car:
            self.car_id = False
            self.new_car_model_id = False

    def _get_available_cars_domain(self):
        return ['|', ('driver_id', '=', False), ('driver_id', '=', self.employee_id.address_home_id.id)]

    def _get_possible_model_domain(self):
        return [('can_be_requested', '=', True)]
