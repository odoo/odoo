# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import babel.dates

from odoo import api, fields, models

from odoo.fields import Datetime


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    co2_fee = fields.Float(compute='_compute_co2_fee', string="CO2 Fee")
    total_depreciated_cost = fields.Float(compute='_compute_total_depreciated_cost',
        string="Total Cost (Depreciated)", help="This includes all the depreciated costs and the CO2 fee")
    total_cost = fields.Float(compute='_compute_total_cost', string="Total Cost", help="This include all the costs and the CO2 fee")
    fuel_type = fields.Selection(required=True, default='diesel')
    atn = fields.Float(compute='_compute_car_atn', string="ATN")
    acquisition_date = fields.Date(required=True)

    @api.depends('co2_fee', 'log_contracts', 'log_contracts.state', 'log_contracts.recurring_cost_amount_depreciated')
    def _compute_total_depreciated_cost(self):
        for car in self:
            car.total_depreciated_cost = car.co2_fee + \
                sum(car.log_contracts.filtered(
                    lambda contract: contract.state == 'open'
                ).mapped('recurring_cost_amount_depreciated'))

    @api.depends('co2_fee', 'log_contracts', 'log_contracts.state', 'log_contracts.cost_generated')
    def _compute_total_cost(self):
        for car in self:
            car.total_cost = car.co2_fee
            contracts = car.log_contracts.filtered(
                lambda contract: contract.state == 'open' and contract.cost_frequency != 'no'
            )
            for contract in contracts:
                if contract.cost_frequency == "daily":
                    car.total_cost += contract.cost_generated * 30.0
                elif contract.cost_frequency == "weekly":
                    car.total_cost += contract.cost_generated * 4.0
                elif contract.cost_frequency == "monthly":
                    car.total_cost += contract.cost_generated
                elif contract.cost_frequency == "yearly":
                    car.total_cost += contract.cost_generated / 12.0

    def _get_co2_fee(self, co2):
        return max((((co2 * 9.0) - 600.0) * 1.2488) / 12.0, 0.0)

    @api.depends('co2')
    def _compute_co2_fee(self):
        for car in self:
            car.co2_fee = self._get_co2_fee(car.co2)

    @api.depends('fuel_type', 'car_value', 'acquisition_date')
    def _compute_car_atn(self):
        for car in self:
            car.atn = car._get_car_atn(car.acquisition_date, car.car_value, car.fuel_type, car.co2)

    @api.depends('model_id', 'license_plate', 'log_contracts', 'total_depreciated_cost', 'acquisition_date')
    def _compute_vehicle_name(self):
        super(FleetVehicle, self)._compute_vehicle_name()
        for vehicle in self:
            acquisition_date = self._get_acquisition_date()
            vehicle.name += u" \u2022 " + str(round(vehicle.total_depreciated_cost, 2)) + u" \u2022 " + acquisition_date

    def _get_acquisition_date(self):
        self.ensure_one()
        return babel.dates.format_date(
            date=Datetime.from_string(self.acquisition_date),
            format='MMMM y',
            locale=self._context.get('lang', 'en_US')
        )

    def _get_car_atn(self, acquisition_date, car_value, fuel_type, co2):
        # Compute the correction coefficient from the age of the car
        now = Datetime.from_string(Datetime.now())
        start = Datetime.from_string(acquisition_date)
        if start:
            number_of_month = (now.year - start.year) * 12.0 + now.month - start.month + int(bool(now.day - start.day + 1))
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

class FleetVehicleModel(models.Model):
    _inherit = 'fleet.vehicle.model'

    default_recurring_cost_amount_depreciated = fields.Float(string="Cost (Depreciated)",
        help="Default recurring cost amount that should be applied to a new car from this model")
    default_co2 = fields.Float(string="CO2 emissions")
    default_fuel_type = fields.Selection([('gasoline', 'Gasoline'), ('diesel', 'Diesel'), ('electric', 'Electric'), ('hybrid', 'Hybrid')], 'Fuel Type', help='Fuel Used by the vehicle')
    default_car_value = fields.Float(string="Catalog Value (VAT Incl.)")
    can_be_requested = fields.Boolean(string="Can be requested", help="Can be requested on a contract as a new car")
    default_atn = fields.Float(compute='_compute_atn', string="ATN")
    default_total_depreciated_cost = fields.Float(compute='_compute_default_total_depreciated_cost', string="Total Cost (Depreciated)")
    co2_fee = fields.Float(compute='_compute_co2_fee', string="CO2 fee")

    @api.depends('default_car_value', 'default_co2', 'default_fuel_type')
    def _compute_atn(self):
        now = Datetime.now()
        for model in self:
            model.default_atn = self.env['fleet.vehicle']._get_car_atn(now, model.default_car_value, model.default_fuel_type, model.default_co2)

    @api.depends('co2_fee', 'default_recurring_cost_amount_depreciated')
    def _compute_default_total_depreciated_cost(self):
        for model in self:
            model.default_total_depreciated_cost = model.co2_fee + model.default_recurring_cost_amount_depreciated

    @api.multi
    @api.depends('name', 'brand_id')
    def name_get(self):
        res = super(FleetVehicleModel, self).name_get()
        new_res = []
        for res_item in res:
            model = self.browse(res_item[0])
            if model.default_total_depreciated_cost != 0.0:
                new_res.append((res_item[0], res_item[1] + u" \u2022 " + str(model.default_total_depreciated_cost)))
            else:
                new_res.append(res_item)
        return new_res

    @api.depends('default_co2')
    def _compute_co2_fee(self):
        for model in self:
            model.co2_fee = self.env['fleet.vehicle']._get_co2_fee(model.default_co2)
