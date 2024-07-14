# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast

from markupsafe import Markup

from odoo import api, fields, models, _


class HrContract(models.Model):
    _inherit = 'hr.contract'

    image_1920_filename = fields.Char()
    id_card_filename = fields.Char()
    id_card = fields.Binary(related='employee_id.id_card', groups="hr_contract.group_hr_contract_manager", readonly=False)
    driving_license_filename = fields.Char()
    driving_license = fields.Binary(related='employee_id.driving_license', groups="hr_contract.group_hr_contract_manager", readonly=False)
    mobile_invoice_filename = fields.Char()
    mobile_invoice = fields.Binary(related='employee_id.mobile_invoice', groups="hr_contract.group_hr_contract_manager", readonly=False)
    sim_card_filename = fields.Char()
    sim_card = fields.Binary(related='employee_id.sim_card', groups="hr_contract.group_hr_contract_manager", readonly=False)
    internet_invoice_filename = fields.Char()
    internet_invoice = fields.Binary(related="employee_id.internet_invoice", groups="hr_contract.group_hr_contract_manager", readonly=False)
    double_holiday_wage = fields.Monetary(compute='_compute_double_holiday_wage')
    contract_type_id = fields.Many2one('hr.contract.type', "Contract Type",
                                       default=lambda self: self.env.ref('l10n_be_hr_payroll.l10n_be_contract_type_cdi',
                                                                         raise_if_not_found=False))
    l10n_be_bicyle_cost = fields.Float(compute='_compute_l10n_be_bicyle_cost')

    @api.depends('has_bicycle')
    def _compute_l10n_be_bicyle_cost(self):
        for contract in self:
            if not contract.has_bicycle:
                contract.l10n_be_bicyle_cost = 0
            else:
                contract.l10n_be_bicyle_cost = self._get_private_bicycle_cost(contract.employee_id.km_home_work)

    @api.model
    def _get_private_bicycle_cost(self, distance):
        amount_per_km = self.env['hr.rule.parameter'].sudo()._get_parameter_from_code('cp200_cycle_reimbursement_per_km', raise_if_not_found=False) or 0.20
        amount_max = self.env['hr.rule.parameter'].sudo()._get_parameter_from_code('cp200_cycle_reimbursement_max', raise_if_not_found=False) or 8
        return 4 * min(amount_max, amount_per_km * distance * 2)

    @api.depends(
        'wage_with_holidays', 'wage_on_signature', 'state',
        'employee_id.l10n_be_scale_seniority', 'job_id.l10n_be_scale_category',
        'work_time_rate', 'time_credit', 'resource_calendar_id.work_time_rate')
    def _compute_l10n_be_is_below_scale(self):
        super()._compute_l10n_be_is_below_scale()

    @api.depends('wage_with_holidays')
    def _compute_double_holiday_wage(self):
        for contract in self:
            contract.double_holiday_wage = contract.wage_with_holidays * 0.92

    def _get_redundant_salary_data(self):
        res = super()._get_redundant_salary_data()
        cars = self.mapped('car_id').filtered(lambda car: not car.active and not car.license_plate)
        vehicle_contracts = cars.with_context(active_test=False).mapped('log_contracts').filtered(
            lambda contract: not contract.active)
        return res + [cars, vehicle_contracts]

    @api.model
    def _benefit_white_list(self):
        return super()._benefit_white_list() + [
            'private_car_reimbursed_amount',
            'yearly_commission_cost',
            'meal_voucher_average_monthly_amount',
            'l10n_be_bicyle_cost',
            'double_holiday_wage',
        ]

    def _get_benefit_values_company_car_total_depreciated_cost(self, contract, benefits):
        has_car = benefits['fold_company_car_total_depreciated_cost']
        selected_car = benefits.get('select_company_car_total_depreciated_cost')
        if not has_car or not selected_car:
            return {
                'transport_mode_car': False,
                'new_car': False,
                'new_car_model_id': False,
                'car_id': False,
            }
        car, car_id = selected_car.split('-')
        new_car = car == 'new'
        if new_car:
            return {
                'transport_mode_car': True,
                'new_car': True,
                'new_car_model_id': int(car_id),
                'car_id': False,
            }
        return {
            'transport_mode_car': True,
            'new_car': False,
            'new_car_model_id': False,
            'car_id': int(car_id),
        }

    def _get_benefit_values_company_bike_depreciated_cost(self, contract, benefits):
        has_bike = benefits['fold_company_bike_depreciated_cost']
        selected_bike = benefits.get('select_company_bike_depreciated_cost', None)
        if not has_bike or not selected_bike:
            return {
                'transport_mode_bike': False,
                'new_bike_model_id': False,
                'bike_id': False,
            }
        bike, bike_id = selected_bike.split('-')
        new_bike = bike == 'new'
        if new_bike:
            return {
                'transport_mode_bike': False,
                'new_bike': True,
                'new_bike_model_id': int(bike_id),
                'bike_id': False,
            }
        return {
            'transport_mode_bike': True,
            'new_bike': False,
            'new_bike_model_id': False,
            'bike_id': int(bike_id),
        }

    def _get_benefit_values_wishlist_car_total_depreciated_cost(self, contract, benefits):
        # make sure the key `fold_wishlist_car_total_depreciated_cost` is present, super() needs it
        benefits['fold_wishlist_car_total_depreciated_cost'] = benefits.get('fold_wishlist_car_total_depreciated_cost')
        return {}

    def _get_benefit_values_insured_relative_spouse(self, contract, benefits):
        return {'insured_relative_spouse': benefits['fold_insured_relative_spouse']}

    def _get_benefit_values_l10n_be_ambulatory_insured_spouse(self, contract, benefits):
        return {'l10n_be_ambulatory_insured_spouse': benefits['fold_l10n_be_ambulatory_insured_spouse']}

    def _get_description_company_car_total_depreciated_cost(self, new_value=None):
        benefit = self.env.ref('l10n_be_hr_contract_salary.l10n_be_transport_company_car')
        description = benefit.description or ""
        if not new_value:
            if self.car_id:
                new_value = 'old-%s' % self.car_id.id
            elif self.new_car_model_id:
                new_value = 'new-%s' % self.new_car_model_id.id
            else:
                return description
        car_option, vehicle_id = new_value.split('-')
        try:
            vehicle_id = int(vehicle_id)
        except:
            return description
        if car_option == "new":
            vehicle = self.env['fleet.vehicle.model'].with_company(self.company_id).sudo().browse(vehicle_id)

        else:
            vehicle = self.env['fleet.vehicle'].with_company(self.company_id).sudo().browse(vehicle_id)

        is_new = bool(car_option == "new")

        car_elements = self._get_company_car_description_values(vehicle, is_new)
        description += Markup('<ul>%s</ul>') % Markup().join([Markup('<li>%s: %s</li>') % (key, value) for key, value in car_elements.items() if value])
        return description

    def _get_description_company_bike_depreciated_cost(self, new_value):
        benefit = self.env.ref('l10n_be_hr_contract_salary.l10n_be_transport_company_bike')
        description = benefit.description or ""
        if not new_value:
            if self.bike_id:
                new_value = 'old-%s' % self.bike_id.id
            else:
                return description
        bike_option, bike_id = new_value.split('-')
        if bike_option == "new":
            bike = self.env['fleet.vehicle.model'].with_company(self.company_id).sudo().browse(int(bike_id))
        else:
            bike = self.env['fleet.vehicle'].with_company(self.company_id).sudo().browse(int(bike_id))

        bike_elements = {
            'Monthly Cost': _("%s € (Rent)", bike.total_depreciated_cost if bike_option == "old" else bike.default_total_depreciated_cost),
            'Electric Assistance': _("Yes") if bike.electric_assistance else _("No"),
            'Color': bike.color,
            'Bike Frame Type': bike.frame_type if bike_option == "old" else False,
            'Frame Size (cm)': bike.frame_size if bike_option == "old" else False,
        }

        description += Markup('<ul>%s</ul>') % Markup().join(Markup('<li>%s: %s</li>') % (key, value) for key, value in bike_elements.items() if value)

        return description

    def _get_company_car_description_values(self, vehicle_id, is_new):
        if is_new:
            co2 = vehicle_id.default_co2
            fuel_type = vehicle_id.default_fuel_type
            transmission = vehicle_id.transmission
            door_number = odometer = immatriculation = trailer_hook = False
            bik_display = "%s €" % round(vehicle_id.default_atn, 2)
            monthly_cost_display = _("%s € (CO2 Fee) + %s € (Rent)", round(vehicle_id.co2_fee, 2), round(vehicle_id.default_total_depreciated_cost - vehicle_id.co2_fee, 2))
        else:
            co2 = vehicle_id.co2
            fuel_type = vehicle_id.fuel_type
            door_number = vehicle_id.doors
            odometer = vehicle_id.odometer
            immatriculation = vehicle_id.acquisition_date
            transmission = vehicle_id.transmission
            trailer_hook = "Yes" if vehicle_id.trailer_hook else "No"
            bik_display = "%s €" % round(vehicle_id.atn, 2)
            monthly_cost_display = _("%s € (CO2 Fee) + %s € (Rent)", round(vehicle_id.co2_fee, 2), round(vehicle_id.total_depreciated_cost - vehicle_id.co2_fee, 2))

        car_elements = {
            'CO2 Emission': co2,
            'Monthly Cost': monthly_cost_display,
            'Fuel Type': fuel_type,
            'BIK': bik_display,
            'Transmission': transmission,
            'Doors Number': door_number,
            'Trailer Hook': trailer_hook,
            'Odometer': odometer,
            'Immatriculation Date': immatriculation
        }
        return car_elements

    def _get_description_commission_on_target(self, new_value=None):
        self.ensure_one()
        return '<span class="form-text">The commission is scalable and starts from the 1st € sold. The commission plan has stages with accelerators. At 100%%, 3 months are paid in Warrant which results to a monthly NET commission value of %s € and 9 months in cash which result in a GROSS monthly commission of %s €, taxable like your usual monthly pay.</span>' % (round(self.warrant_value_employee, 2), round(self.commission_on_target, 2))

    def _get_benefit_values_ip_value(self, contract, benefits):
        if not benefits['ip_value'] or not ast.literal_eval(benefits['ip_value']):
            return {
                'ip': False,
                'ip_wage_rate': contract.ip_wage_rate
            }
        return {
            'ip': True,
            'ip_wage_rate': contract.ip_wage_rate
        }
