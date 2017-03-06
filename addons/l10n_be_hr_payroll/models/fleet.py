# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

from odoo.fields import Datetime


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    co2_fee = fields.Float(compute='_compute_co2_fee', string="CO2 fee (monthly)")
    total_depreciated_cost = fields.Float(compute='_compute_total_depreciated_cost',
        string="Total depreciated cost", help="This includes the services and the CO2 fee")
    last_contract = fields.Many2one('fleet.vehicle.log.contract', compute='_compute_last_contract', string='Last Contract')
    fuel_type = fields.Selection(required=True, default='diesel')
    atn = fields.Float(compute='_compute_car_atn')
    acquisition_date = fields.Date(required=True)

    @api.depends('log_contracts')
    def _compute_last_contract(self):
        for car in self:
            car.last_contract = car.log_contracts.sorted('create_date', reverse=True)

    @api.depends('last_contract', 'co2_fee', 'last_contract.total_depreciated_cost')
    def _compute_total_depreciated_cost(self):
        for car in self:
            if car.last_contract:
                car.total_depreciated_cost = car.co2_fee + car.last_contract.total_depreciated_cost
            # else:
            #     car.total_depreciated_cost = car.co2_fee + car.model_id.default_recurring_cost_amount_depreciated

    def _get_co2_fee(self, co2):
        return max((((co2 * 9.0) - 600.0) * 1.1641) / 12.0, 0.0)

    @api.depends('co2')
    def _compute_co2_fee(self):
        for car in self:
            car.co2_fee = self._get_co2_fee(car.co2)

    @api.depends('fuel_type', 'car_value', 'acquisition_date')
    def _compute_car_atn(self):
        for car in self:
            car.atn = car._get_car_atn(car.acquisition_date, car.car_value, car.fuel_type, car.co2)

    def _get_car_atn(self, acquisition_date, car_value, fuel_type, co2):
        # Compute the correction coefficient from the age of the car
        now = Datetime.from_string(Datetime.now())
        start = Datetime.from_string(acquisition_date)
        if start:
            number_of_month = (now.year - start.year) * 12.0 + now.month - start.month + int(bool(now.day - start.day + 1))
            print number_of_month
            if number_of_month <= 12:
                age_coefficient = 1.00
            elif number_of_month <= 24:
                age_coefficient = 0.94
            elif number_of_month <= 36:
                age_coefficient = 0.88
            elif number_of_month <= 48:
                age_coefficient = 0.82
            elif number_of_month <= 60:
                age_coefficient = 0.76
            else:
                age_coefficient = 0.70
            car_value = car_value * age_coefficient
            # Compute atn value from corrected car_value
            magic_coeff = 6.0 / 7.0  # Don't ask me why
            if fuel_type == 'electric':
                atn = 0.0
            else:
                if fuel_type in ['diesel', 'hybrid']:
                    reference = 87.0
                else:
                    reference = 105.0

                if co2 <= reference:
                    atn = car_value * max(0.04, (0.055 - 0.001 * (reference - co2))) * magic_coeff
                else:
                    atn = car_value * min(0.18, (0.055 + 0.001 * (co2 - reference))) * magic_coeff
            return max(1280, atn) / 12.0


class FleetVehicleLogContract(models.Model):
    _inherit = 'fleet.vehicle.log.contract'

    recurring_cost_amount_depreciated = fields.Float("Recurring Cost Amount (depreciated)")
    total_depreciated_cost = fields.Float(compute='_compute_total_depreciated_cost',
        string="Total Depreciated Cost (incl. services)", readonly=True)

    @api.depends('recurring_cost_amount_depreciated', 'sum_cost')
    def _compute_total_depreciated_cost(self):
        self.total_depreciated_cost = self.recurring_cost_amount_depreciated + self.sum_cost

class FleetVehicleModel(models.Model):
    _inherit = 'fleet.vehicle.model'

    default_recurring_cost_amount_depreciated = fields.Float(string="Default recurring cost amount (depreciated)",
        help="Default recurring cost amount that should be applied to a new car from this model")
    default_co2 = fields.Float(string="Default CO2 emissions")
    default_fuel_type = fields.Selection([('gasoline', 'Gasoline'), ('diesel', 'Diesel'), ('electric', 'Electric'), ('hybrid', 'Hybrid')], 'Fuel Type', help='Fuel Used by the vehicle')
    default_car_value = fields.Float(string="Default car value")
    can_be_requested = fields.Boolean(string="Can be requested", help="Can be requested on a contract as a new car")
    default_atn = fields.Float(compute='_compute_atn', string="Default car ATN")
    default_total_depreciated_cost = fields.Float(compute='_compute_default_total_depreciated_cost')

    @api.depends('default_car_value', 'default_co2', 'default_fuel_type')
    def _compute_atn(self):
        now = Datetime.now()
        for model in self:
            model.default_atn = self.env['fleet.vehicle']._get_car_atn(now, model.default_car_value, model.default_fuel_type, model.default_co2)

    @api.depends('default_co2', 'default_recurring_cost_amount_depreciated')
    def _compute_default_total_depreciated_cost(self):
        for model in self:
            model.default_total_depreciated_cost = model.default_co2 + model.default_recurring_cost_amount_depreciated
