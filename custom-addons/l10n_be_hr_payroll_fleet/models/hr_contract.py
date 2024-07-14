# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression
from odoo.addons.fleet.models.fleet_vehicle_model import FUEL_TYPES


class HrContract(models.Model):
    _inherit = 'hr.contract'

    @api.model
    def _get_available_vehicles_domain(self, driver_ids=None, vehicle_type='car'):
        domain = expression.AND([
            expression.OR([
                [('company_id', '=', False)],
                [('company_id', '=', self.company_id.id)]
            ]),
            expression.AND([
                expression.AND([
                    expression.OR([
                        [('future_driver_id', '=', False)],
                        [('future_driver_id', 'in', driver_ids.ids if driver_ids else [])],
                    ]),
                    [('model_id.vehicle_type', '=', vehicle_type)],
                ]),
                expression.OR([
                    [('driver_id', '=', False)],
                    [('driver_id', 'in', driver_ids.ids if driver_ids else [])],
                    [('plan_to_change_car', '=', True)] if vehicle_type == 'car' else [('plan_to_change_bike', '=', True)]
                ])
            ]),
            [('write_off_date', '=', False)],
        ])
        waiting_stage = self.env.ref('fleet.fleet_vehicle_state_waiting_list', raise_if_not_found=False)
        if waiting_stage:
            domain = expression.AND([[('state_id', '!=', waiting_stage.id)], domain])
        return domain

    def _get_possible_model_domain(self, vehicle_type='car'):
        return [('can_be_requested', '=', True), ('vehicle_type', '=', vehicle_type)]

    car_id = fields.Many2one(
        'fleet.vehicle', string='Company Car',
        tracking=True, compute="_compute_car_id", store=True, readonly=False,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id), ('vehicle_type', '=', 'car')]",
        groups='fleet.fleet_group_manager')
    car_atn = fields.Float(compute='_compute_car_atn_and_costs', string='Car BIK', help='Benefit in Kind (Company Car)', store=True, compute_sudo=True)
    wishlist_car_total_depreciated_cost = fields.Float(compute='_compute_car_atn_and_costs', store=True, compute_sudo=True)
    company_car_total_depreciated_cost = fields.Float(compute='_compute_car_atn_and_costs', store=True, compute_sudo=True)
    available_cars_amount = fields.Integer(compute='_compute_available_cars_amount', string='Number of available cars')
    new_car = fields.Boolean(
        'Requested a new car', compute='_compute_new_car_model_id', store=True, readonly=False)
    new_car_model_id = fields.Many2one(
        'fleet.vehicle.model', string="New Company Car", domain=lambda self: self._get_possible_model_domain(),
        compute='_compute_new_car_model_id', store=True, readonly=False)
    # Useful on sign to use only one box to sign the contract instead of 2
    car_model_name = fields.Char(compute='_compute_car_model_name', compute_sudo=True)
    max_unused_cars = fields.Integer(compute='_compute_max_unused_cars')
    acquisition_date = fields.Date(related='car_id.acquisition_date', readonly=False, groups="fleet.fleet_group_manager")
    car_value = fields.Float(related="car_id.car_value", readonly=False, groups="fleet.fleet_group_manager")
    fuel_type = fields.Selection(selection=lambda self: FUEL_TYPES, compute="_compute_fuel_type", readonly=False, groups="fleet.fleet_group_manager")
    co2 = fields.Float(related="car_id.co2", readonly=False, groups="fleet.fleet_group_manager")
    driver_id = fields.Many2one('res.partner', related="car_id.driver_id", readonly=False, groups="fleet.fleet_group_manager")
    car_open_contracts_count = fields.Integer(compute='_compute_car_open_contracts_count', groups="fleet.fleet_group_manager")
    recurring_cost_amount_depreciated = fields.Float(
        groups="fleet.fleet_group_manager",
        compute='_compute_recurring_cost_amount_depreciated',
        inverse="_inverse_recurring_cost_amount_depreciated")
    transport_mode_bike = fields.Boolean('Uses Bike')
    bike_id = fields.Many2one(
        'fleet.vehicle', string="Company Bike",
        tracking=True,
        compute='_compute_bike_id', store=True, readonly=False,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id), ('vehicle_type', '=', 'bike')]",
        groups='fleet.fleet_group_manager')
    company_bike_depreciated_cost = fields.Float(compute='_compute_company_bike_depreciated_cost', store=True, compute_sudo=True)
    new_bike = fields.Boolean(
        'Requested a new bike', compute='_compute_new_bike', store=True, readonly=False)
    new_bike_model_id = fields.Many2one(
        'fleet.vehicle.model', string="New Company Bike",
        domain=lambda self: self._get_possible_model_domain(vehicle_type='bike'),
        compute='_compute_new_bike_model_id', store=True, readonly=False)
    transport_mode_private_car = fields.Boolean(store=True, readonly=False)

    @api.depends('new_bike', 'new_bike_model_id')
    def _compute_bike_id(self):
        for contract in self:
            if contract.new_bike or contract.new_bike_model_id:
                contract.bike_id = False

    @api.depends('bike_id')
    def _compute_new_bike_model_id(self):
        for contract in self:
            if contract.bike_id:
                contract.update({
                    'new_bike_model_id': False,
                    'new_bike': False,
                })

    @api.depends('new_bike_model_id')
    def _compute_new_bike(self):
        for contract in self:
            if contract.new_bike_model_id:
                contract.new_bike = True

    @api.depends('car_id', 'transport_mode_private_car')
    def _compute_new_car_model_id(self):
        for contract in self:
            if contract.car_id or contract.transport_mode_private_car:
                contract.update({
                    'new_car_model_id': False,
                    'new_car': False,
                })

    @api.depends('car_id', 'new_car_model_id')
    def _compute_car_model_name(self):
        for contract in self:
            if contract.car_id:
                contract.car_model_name = contract.car_id.model_id.display_name
            elif contract.new_car_model_id:
                contract.car_model_name = contract.new_car_model_id.display_name
            else:
                contract.car_model_name = False

    @api.depends('employee_id', 'new_car', 'new_car_model_id', 'transport_mode_private_car')
    def _compute_car_id(self):
        contracts_to_reset = self.filtered(lambda c: c.new_car or c.new_car_model_id or c.transport_mode_private_car or not c.transport_mode_car)
        contracts_to_reset.car_id = False
        remaining_contracts = self - contracts_to_reset
        if not remaining_contracts:
            return
        employees_partners = remaining_contracts.employee_id.work_contact_id
        cars = self.env['fleet.vehicle'].search([
            ('vehicle_type', '=', 'car'),
            '|', ('driver_id', 'in', employees_partners.ids), ('future_driver_id', 'in', employees_partners.ids)
        ], order='future_driver_id, driver_id')
        dict_car = {
            (car.driver_id or car.future_driver_id).id: car.id for car in cars
        }
        for contract in remaining_contracts:
            if contract.car_id:
                continue
            partner_id = contract.employee_id.work_contact_id.id
            if partner_id in dict_car:
                contract.car_id = dict_car[partner_id]
                contract.transport_mode_car = True
            else:
                contract.car_id = False

    @api.depends('car_id', 'new_car_model_id')
    def _compute_fuel_type(self):
        for contract in self:
            contract.fuel_type = contract.car_id.fuel_type if contract.car_id else contract.new_car_model_id.default_fuel_type or False

    @api.depends('car_id', 'new_car', 'new_car_model_id', 'car_id.total_depreciated_cost',
        'car_id.atn', 'new_car_model_id.default_atn', 'new_car_model_id.default_total_depreciated_cost')
    def _compute_car_atn_and_costs(self):
        self.car_atn = False
        self.company_car_total_depreciated_cost = False
        self.wishlist_car_total_depreciated_cost = False
        for contract in self:
            if not contract.new_car and contract.car_id:
                contract.car_atn = contract.car_id.atn
                contract.company_car_total_depreciated_cost = contract.car_id.total_depreciated_cost
                contract.wishlist_car_total_depreciated_cost = 0
            elif contract.new_car and contract.new_car_model_id:
                car_model = contract.new_car_model_id.with_company(contract.company_id)
                contract.car_atn = car_model.default_atn
                contract.company_car_total_depreciated_cost = car_model.default_total_depreciated_cost
                contract.wishlist_car_total_depreciated_cost = car_model.default_total_depreciated_cost


    @api.depends('new_bike', 'bike_id', 'new_bike_model_id', 'bike_id.total_depreciated_cost',
        'bike_id.co2_fee', 'new_bike_model_id.default_total_depreciated_cost', 'transport_mode_bike')
    def _compute_company_bike_depreciated_cost(self):
        for contract in self:
            contract.company_bike_depreciated_cost = False
            if not contract.new_bike and contract.transport_mode_bike and contract.bike_id:
                contract.company_bike_depreciated_cost = contract.bike_id.total_depreciated_cost
            elif not contract.transport_mode_bike and contract.new_bike and contract.new_bike_model_id:
                contract.company_bike_depreciated_cost = contract.new_bike_model_id.default_recurring_cost_amount_depreciated

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
            contract.available_cars_amount = self.env['fleet.vehicle'].sudo().search_count(contract._get_available_vehicles_domain(contract.employee_id.work_contact_id))

    @api.depends('name')
    def _compute_max_unused_cars(self):
        params = self.env['ir.config_parameter'].sudo()
        max_unused_cars = params.get_param('l10n_be_hr_payroll_fleet.max_unused_cars', default=1000)
        for contract in self:
            contract.max_unused_cars = 999999 if contract.env.context.get('is_applicant') else int(max_unused_cars)

    @api.onchange('new_car', 'transport_mode_car')
    def _onchange_transport_mode_car(self):
        if self.new_car:
            self.transport_mode_car = False
            self.car_id = False
            self.transport_mode_private_car = False

    @api.onchange('new_bike')
    def _onchange_new_bike(self):
        if self.new_bike:
            self.bike_id = False
            self.transport_mode_bike = False

    @api.onchange('transport_mode_bike', 'transport_mode_car', 'transport_mode_train', 'transport_mode_public')
    def _onchange_transport_mode(self):
        super(HrContract, self)._onchange_transport_mode()
        if self.transport_mode_bike:
            self.new_bike = False
            self.new_bike_model_id = False
        if self.transport_mode_car:
            self.new_car = False
            self.new_car_model_id = False
        if self.car_id:
            self.transport_mode_private_car = False

    def _get_fields_that_recompute_payslip(self):
        # Returns the fields that should recompute the payslip
        return super()._get_fields_that_recompute_payslip() + [
            'car_id',
        ]
