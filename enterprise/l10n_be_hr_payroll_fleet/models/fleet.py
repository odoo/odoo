# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.tools.misc import format_date

from odoo.fields import Datetime, Date


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    co2_fee = fields.Float(compute='_compute_co2_fee', string="CO2 Fee")
    total_depreciated_cost = fields.Float(compute='_compute_total_depreciated_cost',
        string="Total Cost (Depreciated)", tracking=True, compute_sudo=True,
        help="This includes all the depreciated costs and the CO2 fee")
    total_cost = fields.Float(compute='_compute_total_cost', string="Total Cost", help="This include all the costs and the CO2 fee")
    fuel_type = fields.Selection(required=True, default='diesel')
    atn = fields.Float(compute='_compute_car_atn', string="BIK")
    acquisition_date = fields.Date(required=True)
    tax_deduction = fields.Float(compute='_compute_tax_deduction')

    def _from_be(self):
        if self:
            return self.company_id.country_id.code == "BE"
        else:
            return self.env.company.country_id.code == "BE"

    @api.depends('co2_fee', 'log_contracts', 'log_contracts.state', 'log_contracts.recurring_cost_amount_depreciated')
    def _compute_total_depreciated_cost(self):
        for car in self:
            if car.log_contracts:
                car.total_depreciated_cost = car.co2_fee + \
                    sum(car.log_contracts.filtered(
                        lambda contract: contract.state == 'open'
                    ).mapped('recurring_cost_amount_depreciated'))
            else:
                car.total_depreciated_cost = car.model_id.with_company(car.company_id).default_total_depreciated_cost


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

    def _get_tax_deduction(self, co2, fuel, coefficients, horsepower):
        if fuel == 'electric':
            return 1
        if co2 >= 200:
            return 0.4
        if coefficients and fuel in coefficients:
            coeff = coefficients[fuel]
            # Special case for cng which has a different coeff depending on horweposer
            if fuel == 'cng' and horsepower < coefficients.get('cng_hp_lower_bound', 12):
                coeff = coefficients.get('cng_low', coeff)
            return min(max(1.2 - (0.005 * coeff * co2), 0.5), 1)
        return 0

    @api.depends('fuel_type', 'co2', 'horsepower')
    def _compute_tax_deduction(self):
        be_vehicles = self.filtered(lambda vehicle: vehicle.company_id.country_id.code == "BE")
        (self - be_vehicles).tax_deduction = 0
        coefficients = self.env['hr.rule.parameter'].sudo()._get_parameter_from_code('tax_deduction_fuel_coefficients', raise_if_not_found=False) if be_vehicles else None
        for vehicle in be_vehicles:
            if vehicle.vehicle_type == "bike":
                vehicle.tax_deduction = 1
            else:
                vehicle.tax_deduction = vehicle._get_tax_deduction(vehicle.co2, vehicle.fuel_type, coefficients, vehicle.horsepower)

    def _get_co2_fee(self, co2, fuel_type):
        # Reference: https://www.socialsecurity.be/employer/instructions/dmfa/fr/latest/instructions/special_contributions/companycar.html
        if not self._from_be() or self.vehicle_type == 'bike':
            return 0
        date = self.env.context.get('co2_fee_date', fields.Date.today())
        fuel_coefficient = self.env['hr.rule.parameter']._get_parameter_from_code('fuel_coefficient', date)
        co2_fee_min = self.env['hr.rule.parameter']._get_parameter_from_code('co2_fee_min', date)
        co2_fee = co2_fee_min
        if fuel_type and fuel_type in ['gasoline', 'diesel', 'lpg']:
            health_indice = self.env['hr.rule.parameter']._get_parameter_from_code('health_indice', date)
            health_indice_reference = self.env['hr.rule.parameter']._get_parameter_from_code('health_indice_reference', date)
            co2_fee = (((co2 * 9.0) - fuel_coefficient.get(fuel_type)) / 12.0 * health_indice) / health_indice_reference
        return max(co2_fee, co2_fee_min)

    @api.depends('co2', 'fuel_type', 'company_id.country_id')
    def _compute_co2_fee(self):
        for car in self:
            car.co2_fee = car._get_co2_fee(car.co2, car.fuel_type)

    @api.depends('fuel_type', 'car_value', 'acquisition_date', 'co2', 'company_id.country_id')
    def _compute_car_atn(self):
        for car in self:
            car.atn = car._get_car_atn()

    @api.depends('model_id', 'license_plate', 'log_contracts', 'acquisition_date',
                 'co2_fee', 'log_contracts', 'log_contracts.state', 'log_contracts.recurring_cost_amount_depreciated')
    def _compute_vehicle_name(self):
        super(FleetVehicle, self)._compute_vehicle_name()
        for vehicle in self:
            acquisition_date = vehicle._get_acquisition_date()
            vehicle.name += u" \u2022 " + acquisition_date

    def _get_analytic_name(self):
        # This function is used in fleet_account
        name = super(FleetVehicle, self)._get_analytic_name()
        if self.tax_deduction:
            return '%s, %s%s' % (name, round(self.tax_deduction * 100, 2), "%")
        else:
            return name

    def _get_acquisition_date(self):
        self.ensure_one()
        return format_date(self.env, self.acquisition_date, date_format='MMMM y')

    def _get_car_atn(self, date=None):
        return self._get_car_atn_from_values(self.acquisition_date, self.car_value, self.fuel_type, self.co2, date)

    @api.model
    def _get_car_atn_from_values(self, acquisition_date, car_value, fuel_type, co2, date=None):
        if not self._from_be():
            return 0

        date = date or Date.today()
        if acquisition_date:
            car_age = relativedelta(date, acquisition_date).years
            value_loss_per_year = 0.06  # 6% of car value lost each year
            age_coefficient = 1.00 - car_age * value_loss_per_year
            age_coefficient = max(age_coefficient, 0.70)

            min_co2_prc = self.env['hr.rule.parameter']._get_parameter_from_code('min_co2_prc', date, raise_if_not_found=False) or 0.04
            max_co2_prc = self.env['hr.rule.parameter']._get_parameter_from_code('max_co2_prc', date, raise_if_not_found=False) or 0.18

            if date >= datetime.date(2025, 1, 1):
                if (fuel_type in ['electric', 'hydrogen'] or
                        (fuel_type in ['plug_in_hybrid_diesel', 'plug_in_hybrid_gasoline'] and co2 <= 50)):
                    co2_percentage = min_co2_prc
                else:
                    if fuel_type == 'diesel':
                        co2_ref = self.env['hr.rule.parameter']._get_parameter_from_code('co2_reference_diesel', date)
                    else:
                        co2_ref = self.env['hr.rule.parameter']._get_parameter_from_code('co2_reference_petrol_lpg', date)

                    co2_percentage = (0.055 + 0.001 * (co2 - co2_ref))
                    co2_percentage = max(min_co2_prc, min(max_co2_prc, co2_percentage))
            else:
                if fuel_type in ['electric', 'hydrogen']:
                    co2_percentage = min_co2_prc
                else:
                    if fuel_type in ['diesel', 'full_hybrid', 'plug_in_hybrid_diesel']:
                        co2_ref = self.env['hr.rule.parameter']._get_parameter_from_code('co2_reference_diesel', date)
                    else:
                        co2_ref = self.env['hr.rule.parameter']._get_parameter_from_code('co2_reference_petrol_lpg', date)
                    co2_percentage = (0.055 + 0.001 * (co2 - co2_ref))
                    co2_percentage = max(min_co2_prc, min(max_co2_prc, co2_percentage))
            min_car_atn = self.env['hr.rule.parameter']._get_parameter_from_code('min_car_atn', date)
            atn = car_value * age_coefficient * co2_percentage * 6 / 7
            return max(min_car_atn, atn) / 12

        return 0.0

    @api.onchange('model_id')
    def _onchange_model_id(self):
        self.car_value = self.model_id.default_car_value
        self.co2 = self.model_id.default_co2
        self.fuel_type = self.model_id.default_fuel_type


class FleetVehicleLogContract(models.Model):
    _inherit = 'fleet.vehicle.log.contract'

    cost_generated = fields.Monetary(compute='_compute_cost', store=True, readonly=False)
    recurring_cost_amount_depreciated = fields.Float(
        "Depreciated Cost Amount", tracking=True,
        compute='_compute_cost', store=True, readonly=False)

    @api.depends('vehicle_id')
    def _compute_cost(self):
        for log_contract in self:
            last_contract = log_contract.vehicle_id.log_contracts[:1]
            if last_contract:
                log_contract.cost_generated = last_contract.cost_generated
                log_contract.recurring_cost_amount_depreciated = last_contract.recurring_cost_amount_depreciated
            else:
                default_cost = log_contract.vehicle_id.model_id.default_recurring_cost_amount_depreciated
                if not default_cost:
                    continue
                log_contract.cost_generated = default_cost
                log_contract.recurring_cost_amount_depreciated = default_cost


class FleetVehicleModel(models.Model):
    _inherit = 'fleet.vehicle.model'

    default_recurring_cost_amount_depreciated = fields.Float(string="Cost (Depreciated)",
        tracking=True,
        help="Default recurring cost amount that should be applied to a new vehicle from this model")
    default_car_value = fields.Float(string="Catalog Value (VAT Incl.)", tracking=True)
    can_be_requested = fields.Boolean(
        string="Can be requested", company_dependent=True,
        tracking=True,
        help="Can be requested on a contract as a new vehicle")
    default_atn = fields.Float(compute='_compute_atn', string="BIK")
    default_total_depreciated_cost = fields.Float(compute='_compute_default_total_depreciated_cost', compute_sudo=True, string="Total Cost (Depreciated)")
    default_co2 = fields.Float(compute='_compute_default_co2', readonly=False, store=True, tracking=True)
    co2_fee = fields.Float(compute='_compute_co2_fee', string="CO2 fee")
    tax_deduction = fields.Float(compute='_compute_tax_deduction')

    current_country_code = fields.Char(compute='_compute_current_country_code')

    @api.depends('default_car_value', 'default_co2', 'default_fuel_type')
    def _compute_atn(self):
        now = Datetime.now()
        for model in self:
            model.default_atn = self.env['fleet.vehicle']._get_car_atn_from_values(now, model.default_car_value, model.default_fuel_type, model.default_co2)

    @api.depends('co2_fee', 'default_recurring_cost_amount_depreciated')
    def _compute_default_total_depreciated_cost(self):
        for model in self:
            model.default_total_depreciated_cost = model.co2_fee + model.default_recurring_cost_amount_depreciated

    @api.depends('default_co2', 'default_fuel_type')
    def _compute_co2_fee(self):
        for model in self:
            if model.vehicle_type == 'bike':
                model.co2_fee = 0
            else:
                model.co2_fee = self.env['fleet.vehicle']._get_co2_fee(model.default_co2, model.default_fuel_type)

    @api.depends('default_fuel_type')
    def _compute_default_co2(self):
        # Fill in a default co2 depending on the fuel type only if it is zero
        default_co2_map = {
            'diesel': 195,
            'electric': 0,
        }
        for model in self:
            if not model.default_co2:
                model.default_co2 = default_co2_map.get(model.default_fuel_type, 205)

    @api.depends('default_co2', 'default_fuel_type', 'horsepower')
    def _compute_tax_deduction(self):
        coefficients = self.env['hr.rule.parameter'].sudo()._get_parameter_from_code('tax_deduction_fuel_coefficients', raise_if_not_found=False)
        for model in self:
            if model.vehicle_type == "bike":
                model.tax_deduction = 1
            else:
                model.tax_deduction = self.env['fleet.vehicle']._get_tax_deduction(
                    model.default_co2, model.default_fuel_type, coefficients, model.horsepower)

    @api.depends_context('uid')
    def _compute_current_country_code(self):
        for model in self:
            model.current_country_code = self.env.company.country_id.code
