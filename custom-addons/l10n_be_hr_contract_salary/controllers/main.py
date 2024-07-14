# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import OrderedDict

from odoo import fields, _
from odoo.addons.hr_contract_salary.controllers import main
from odoo.addons.sign.controllers.main import Sign
from odoo.http import route, request

ODOMETER_UNITS = {'kilometers': 'km', 'miles': 'mi'}

class SignContract(Sign):

    def _update_contract_on_signature(self, request_item, contract, offer):
        super()._update_contract_on_signature(request_item, contract, offer)
        # Only the applicant/employee has signed
        if request_item.sign_request_id.nb_closed == 1 and contract.car_id:
            if contract.car_id and contract.driver_id != contract.employee_id.work_contact_id:
                contract.car_id.future_driver_id = contract.employee_id.work_contact_id
        # Both applicant/employee and HR responsible have signed
        if request_item.sign_request_id.nb_closed == 2:
            if contract.new_car or contract.new_bike_model_id:
                state_new_request = request.env.ref('fleet.fleet_vehicle_state_new_request', raise_if_not_found=False)
                Vehicle = request.env['fleet.vehicle'].sudo()
                vehicle_vals = {
                    'state_id': state_new_request and state_new_request.id,
                    'future_driver_id': contract.employee_id.work_contact_id.id,
                    'company_id': contract.company_id.id,
                }
                contracts_vals = {
                    'cost_frequency': 'no',
                    'purchaser_id': contract.employee_id.work_contact_id.id,
                }
            if contract.new_car:
                model = contract.new_car_model_id.sudo()
                contract.update({
                    'new_car': False,
                    'new_car_model_id': False,
                    'transport_mode_car': True,
                })
                contract.car_id = Vehicle.create(dict(vehicle_vals, **{
                    'model_id': model.id,
                    'car_value': model.default_car_value,
                    'co2': model.default_co2,
                    'fuel_type': model.default_fuel_type,
                }))
                vehicle_contract = contract.car_id.log_contracts and contract.car_id.log_contracts[0]
                if vehicle_contract:
                    vehicle_contract.write(dict(contracts_vals, **{
                        'recurring_cost_amount_depreciated': model.default_recurring_cost_amount_depreciated,
                        'cost_generated': model.default_recurring_cost_amount_depreciated,
                    }))
            if contract.new_bike_model_id:
                model = contract.new_bike_model_id.sudo()
                contract.update({
                    'new_bike': False,
                    'new_bike_model_id': False,
                    'transport_mode_bike': True,
                })
                contract.bike_id = Vehicle.create(dict(vehicle_vals, **{
                    'model_id': model.id,
                    'car_value': model.default_car_value,
                    'co2': model.default_co2,
                    'fuel_type': model.default_fuel_type,
                }))
                vehicle_contract = contract.bike_id.log_contracts and contract.bike_id.log_contracts[0]
                if vehicle_contract:
                    vehicle_contract.write(dict(contracts_vals, **{
                        'recurring_cost_amount_depreciated': model.default_recurring_cost_amount_depreciated,
                        'cost_generated': model.default_recurring_cost_amount_depreciated,
                    }))

class HrContractSalary(main.HrContractSalary):

    @route()
    def salary_package(self, offer_id=None, **kw):
        contract = request.env['hr.contract.salary.offer'].sudo().browse(offer_id).contract_template_id
        if contract._get_work_time_rate() == 0:
            return request.render('http_routing.http_error', {
                'status_code': _('Oops'),
                'status_message': _('This contract is a full time credit time... No simulation can be done for this type of contract as its wage is equal to 0.')})
        return super().salary_package(offer_id, **kw)

    @route()
    def onchange_benefit(self, benefit_field, new_value, contract_id, benefits):
        res = super().onchange_benefit(benefit_field, new_value, contract_id, benefits)
        insurance_fields = [
            'insured_relative_children', 'insured_relative_adults',
            'fold_insured_relative_spouse', 'has_hospital_insurance']
        ambulatory_insurance_fields = [
            'l10n_be_ambulatory_insured_children', 'l10n_be_ambulatory_insured_adults',
            'fold_l10n_be_ambulatory_insured_spouse', 'l10n_be_has_ambulatory_insurance']
        if benefit_field == "km_home_work":
            new_value = new_value if new_value else 0
            res['extra_values'] = [
                ('private_car_reimbursed_amount_manual', new_value),
                ('l10n_be_bicyle_cost_manual', new_value),
                ('l10n_be_bicyle_cost', round(request.env['hr.contract']._get_private_bicycle_cost(float(new_value)), 2) if benefits['contract']['fold_l10n_be_bicyle_cost'] else 0),
                ('private_car_reimbursed_amount', round(request.env['hr.contract']._get_private_car_reimbursed_amount(float(new_value)), 2)  if benefits['contract']['fold_private_car_reimbursed_amount'] else 0),
            ]
        if benefit_field == 'public_transport_reimbursed_amount':
            new_value = new_value if new_value else 0
            res['new_value'] = round(request.env['hr.contract']._get_public_transport_reimbursed_amount(float(new_value)), 2)
        elif benefit_field == 'train_transport_reimbursed_amount':
            new_value = new_value if new_value else 0
            res['new_value'] = round(request.env['hr.contract']._get_train_transport_reimbursed_amount(float(new_value)), 2)
        elif benefit_field == 'private_car_reimbursed_amount':
            new_value = new_value if new_value else 0
            res['new_value'] = round(request.env['hr.contract']._get_private_car_reimbursed_amount(float(new_value)), 2)
            res['extra_values'] = [
                ('km_home_work', new_value),
                ('l10n_be_bicyle_cost_manual', new_value),
                ('l10n_be_bicyle_cost', round(request.env['hr.contract']._get_private_bicycle_cost(float(new_value)), 2) if benefits['contract']['fold_l10n_be_bicyle_cost'] else 0),
            ]
        elif benefit_field == 'ip_value':
            contract = self._check_access_rights(contract_id)
            res['new_value'] = contract.ip_wage_rate if float(new_value) else 0
        elif benefit_field in ['company_car_total_depreciated_cost', 'company_bike_depreciated_cost'] and new_value:
            car_options, vehicle_id = new_value.split('-')
            contract = self._check_access_rights(contract_id)
            if car_options == 'new':
                res['new_value'] = round(request.env['fleet.vehicle.model'].sudo().with_company(contract.company_id).browse(int(vehicle_id)).default_total_depreciated_cost, 2)
            else:
                res['new_value'] = round(request.env['fleet.vehicle'].sudo().with_company(contract.company_id).browse(int(vehicle_id)).total_depreciated_cost, 2)
        elif benefit_field == 'wishlist_car_total_depreciated_cost':
            res['new_value'] = 0
        elif benefit_field == 'fold_company_car_total_depreciated_cost' and not res['new_value']:
            res['extra_values'] = [('company_car_total_depreciated_cost', 0)]
        elif benefit_field == 'fold_wishlist_car_total_depreciated_cost' and not res['new_value']:
            res['extra_values'] = [('wishlist_car_total_depreciated_cost', 0)]
        elif benefit_field == 'fold_company_bike_depreciated_cost' and not res['new_value']:
            res['extra_values'] = [('company_bike_depreciated_cost', 0)]
        elif benefit_field in insurance_fields:
            child_amount = float(request.env['ir.config_parameter'].sudo().get_param('hr_contract_salary.hospital_insurance_amount_child', default=7.2))
            adult_amount = float(request.env['ir.config_parameter'].sudo().get_param('hr_contract_salary.hospital_insurance_amount_adult', default=20.5))
            adv = benefits['contract']
            child_count = int(adv['insured_relative_children_manual'] or False)
            has_hospital_insurance = float(adv['has_hospital_insurance_radio']) == 1.0 if 'has_hospital_insurance_radio' in adv else False
            adult_count = int(adv['insured_relative_adults_manual'] or False) + int(adv['fold_insured_relative_spouse']) + int(has_hospital_insurance)
            insurance_amount = request.env['hr.contract']._get_insurance_amount(child_amount, child_count, adult_amount, adult_count)
            res['extra_values'] = [('has_hospital_insurance', insurance_amount)]
        if benefit_field in ambulatory_insurance_fields:
            child_amount = float(request.env['ir.config_parameter'].sudo().get_param('hr_contract_salary.ambulatory_insurance_amount_child', default=7.2))
            adult_amount = float(request.env['ir.config_parameter'].sudo().get_param('hr_contract_salary.ambulatory_insurance_amount_adult', default=20.5))
            adv = benefits['contract']
            child_count = int(adv['l10n_be_ambulatory_insured_children_manual'] or False)
            l10n_be_has_ambulatory_insurance = float(adv['l10n_be_has_ambulatory_insurance_radio']) == 1.0 if 'l10n_be_has_ambulatory_insurance_radio' in adv else False
            adult_count = int(adv['l10n_be_ambulatory_insured_adults_manual'] or False) \
                        + int(adv['fold_l10n_be_ambulatory_insured_spouse']) \
                        + int(l10n_be_has_ambulatory_insurance)
            insurance_amount = request.env['hr.contract']._get_insurance_amount(
                child_amount, child_count,
                adult_amount, adult_count)
            res['extra_values'] = [('l10n_be_has_ambulatory_insurance', insurance_amount)]
        if benefit_field == 'l10n_be_bicyle_cost':
            new_value = new_value if new_value else 0
            res['new_value'] = round(request.env['hr.contract']._get_private_bicycle_cost(float(new_value)), 2)
            res['extra_values'] = [
                ('km_home_work', new_value),
                ('private_car_reimbursed_amount_manual', new_value),
                ('private_car_reimbursed_amount', round(request.env['hr.contract']._get_private_car_reimbursed_amount(float(new_value)), 2)  if benefits['contract']['fold_private_car_reimbursed_amount'] else 0),
            ]
        if benefit_field == 'fold_l10n_be_bicyle_cost':
            distance = benefits['employee']['km_home_work'] or '0'
            res['extra_values'] = [('l10n_be_bicyle_cost', round(request.env['hr.contract']._get_private_bicycle_cost(float(distance)), 2) if benefits['contract']['fold_l10n_be_bicyle_cost'] else 0)]
        if benefit_field == 'fold_private_car_reimbursed_amount':
            distance = benefits['employee']['km_home_work'] or '0'
            res['extra_values'] = [('private_car_reimbursed_amount', round(request.env['hr.contract']._get_private_car_reimbursed_amount(float(distance)), 2)  if benefits['contract']['fold_private_car_reimbursed_amount'] else 0)]
        return res

    def _get_default_template_values(self, contract, offer):
        values = super()._get_default_template_values(contract, offer)
        values['l10n_be_canteen_cost'] = contract.l10n_be_canteen_cost
        values['contract_type_id'] = offer.contract_type_id.id
        return values

    def _get_benefits(self, contract, offer):
        res = super()._get_benefits(contract, offer)
        force_new_car = offer.new_car
        if offer.applicant_id or force_new_car or contract.available_cars_amount < contract.max_unused_cars:
            res -= request.env.ref('l10n_be_hr_contract_salary.l10n_be_transport_new_car')
        return res

    def _get_benefits_values(self, contract, offer):
        mapped_benefits, mapped_dependent_benefits, mandatory_benefits, mandatory_benefits_names, benefit_types, dropdown_options, dropdown_group_options, initial_values = super()._get_benefits_values(contract, offer)

        available_cars = request.env['fleet.vehicle'].sudo().with_company(contract.company_id).search(
            contract._get_available_vehicles_domain(contract.employee_id.work_contact_id)).sorted(key=lambda car: car.total_depreciated_cost)
        available_bikes = request.env['fleet.vehicle'].sudo().with_company(contract.company_id).search(
            contract._get_available_vehicles_domain(contract.employee_id.work_contact_id, vehicle_type='bike')).sorted(key=lambda car: car.total_depreciated_cost)
        force_car = offer.car_id
        if force_car:
            available_cars |= force_car
            contract.car_id = force_car
        available_bikes |= contract.bike_id

        def generate_dropdown_group_data(available, can_be_requested, only_new, allow_new_cars, vehicle_type='Car'):
            # Creates the necessary data for the dropdown group, looks like this
            # {
            #     'category_name': [
            #         (value, value),
            #         (value, value),...
            #     ],
            #     'other_category': ...
            # }
            model_categories = (available.category_id | available.model_id.category_id | can_be_requested.category_id)
            model_categories_ids = model_categories.sorted(key=lambda c: (c.sequence, c.id)).ids
            model_categories_ids.append(0) # Case when no category
            result = OrderedDict()
            for category in model_categories_ids:
                category_id = model_categories.filtered(lambda c: c.id == category)
                car_values = []
                if not only_new:
                    if not category:  # "No Category"
                        domain = [
                            ('category_id', '=', False),
                            ('model_id.category_id', '=', False),
                        ]
                    else:
                        domain = [
                            '|',
                                ('category_id', '=', category),
                                '&',
                                    ('category_id', '=', False),
                                    ('model_id.category_id', '=', category),
                        ]

                    cars = available.filtered_domain(domain)
                    car_values.extend([(
                        'old-%s' % (car.id),
                        '%s/%s \u2022 %s € \u2022 %s%s%s' % (
                            car.model_id.brand_id.name,
                            car.model_id.name,
                            round(car.total_depreciated_cost, 2),
                            car._get_acquisition_date() if vehicle_type == 'Car' else '',
                            _('\u2022 Available in %s', car.next_assignation_date.strftime('%B %Y')) if car.next_assignation_date else u'',
                            ' \u2022 %s %s' % (car.odometer, ODOMETER_UNITS[car.odometer_unit]) if vehicle_type == 'Car' else '',
                        )
                    ) for car in cars])

                if allow_new_cars:
                    requestables = can_be_requested.filtered_domain([
                        ('category_id', '=', category)
                    ])
                    car_values.extend([(
                        'new-%s' % (model.id),
                        '%s \u2022 %s € \u2022 New %s' % (
                            model.display_name,
                            round(model.default_total_depreciated_cost, 2),
                            vehicle_type,
                        )
                    ) for model in requestables])

                if car_values:
                    result[category_id.name or _("No Category")] = car_values
            return result

        def generate_dropdown_data(available, can_be_requested, only_new_cars, allow_new_cars, vehicle_type='Car'):
            result = []
            if not only_new_cars:
                result.extend([(
                    'old-%s' % (car.id),
                    '%s/%s \u2022 %s € \u2022 %s%s%s' % (
                        car.model_id.brand_id.name,
                        car.model_id.name,
                        round(car.total_depreciated_cost, 2),
                        car._get_acquisition_date() if vehicle_type == 'Car' else '',
                        _('\u2022 Available in %s', car.next_assignation_date.strftime('%B %Y')) if car.next_assignation_date else u'',
                        ' \u2022 %s %s' % (car.odometer, ODOMETER_UNITS[car.odometer_unit]) if vehicle_type == 'Car' else '',
                    )
                ) for car in available])
            if allow_new_cars:
                result.extend([(
                    'new-%s' % (model.id),
                    '%s \u2022 %s € \u2022 New %s' % (
                        model.display_name,
                        round(model.default_total_depreciated_cost, 2),
                        vehicle_type,
                    )
                ) for model in can_be_requested_models])
            return result

        benefits = self._get_benefits(contract, offer)
        car_benefit = benefits.filtered(
            lambda a: a.res_field_id.name == 'company_car_total_depreciated_cost'
        )
        bike_benefit = benefits.filtered(
            lambda a: a.res_field_id.name == 'company_bike_depreciated_cost'
        )
        wishlist_car_benefit = benefits.filtered(
            lambda a: a.res_field_id.name == 'wishlist_car_total_depreciated_cost'
        )

        # Car stuff
        can_be_requested_models = request.env['fleet.vehicle.model'].sudo().with_company(contract.company_id).search(
        contract._get_possible_model_domain()).sorted(key=lambda model: model.default_total_depreciated_cost)

        force_new_car = offer.new_car
        allow_new_cars = False
        wishlist_new_cars = False
        if force_new_car or contract.available_cars_amount < contract.max_unused_cars:
            allow_new_cars = True
        else:
            wishlist_new_cars = True

        if car_benefit.display_type == 'dropdown-group':
            dropdown_group_options['company_car_total_depreciated_cost'] = \
                generate_dropdown_group_data(available_cars, can_be_requested_models, False, allow_new_cars)
        else:
            dropdown_options['company_car_total_depreciated_cost'] = \
                generate_dropdown_data(available_cars, can_be_requested_models, False, allow_new_cars)

        if wishlist_new_cars:
            if wishlist_car_benefit.display_type == 'dropdown-group':
                dropdown_group_options['wishlist_car_total_depreciated_cost'] = \
                    generate_dropdown_group_data(available_cars, can_be_requested_models, True, True)
            else:
                dropdown_options['wishlist_car_total_depreciated_cost'] = \
                    generate_dropdown_data(available_cars, can_be_requested_models, True, True)
            initial_values['fold_wishlist_car_total_depreciated_cost'] = False
            initial_values['wishlist_car_total_depreciated_cost'] = 0

        # Bike stuff
        can_be_requested_models = request.env['fleet.vehicle.model'].sudo().with_company(contract.company_id).search(
        contract._get_possible_model_domain(vehicle_type='bike')).sorted(key=lambda model: model.default_total_depreciated_cost)
        if bike_benefit.display_type == 'dropdown-group':
            dropdown_group_options['company_bike_depreciated_cost'] = \
                generate_dropdown_group_data(available_bikes, can_be_requested_models, False, True, 'Bike')
        else:
            dropdown_options['company_bike_depreciated_cost'] = \
                generate_dropdown_data(available_bikes, can_be_requested_models, False, True, 'Bike')

        if force_car:
            initial_values['select_company_car_total_depreciated_cost'] = 'old-%s' % force_car.id
            initial_values['fold_company_car_total_depreciated_cost'] = True
            initial_values['company_car_total_depreciated_cost'] = force_car.total_depreciated_cost
        elif contract.car_id:
            initial_values['select_company_car_total_depreciated_cost'] = 'old-%s' % contract.car_id.id
            initial_values['fold_company_car_total_depreciated_cost'] = True
            initial_values['company_car_total_depreciated_cost'] = contract.car_id.total_depreciated_cost
        elif contract.new_car_model_id:
            initial_values['select_company_car_total_depreciated_cost'] = 'new-%s' % contract.new_car_model_id.id
            initial_values['fold_company_car_total_depreciated_cost'] = True
            initial_values['company_car_total_depreciated_cost'] = contract.new_car_model_id.default_total_depreciated_cost
        else:
            initial_values['fold_company_car_total_depreciated_cost'] = False
        if contract.bike_id:
            initial_values['select_company_bike_depreciated_cost'] = 'old-%s' % contract.bike_id.id
        elif contract.new_bike_model_id:
            initial_values['select_company_bike_depreciated_cost'] = 'new-%s' % contract.new_bike_model_id.id

        hospital_insurance_child_amount = float(request.env['ir.config_parameter'].sudo().get_param('hr_contract_salary.hospital_insurance_amount_child', default=7.2))
        hospital_insurance_adult_amount = float(request.env['ir.config_parameter'].sudo().get_param('hr_contract_salary.hospital_insurance_amount_adult', default=20.5))
        ambulatory_insurance_child_amount = float(request.env['ir.config_parameter'].sudo().get_param('hr_contract_salary.ambulatory_insurance_amount_child', default=7.2))
        ambulatory_insurance_adult_amount = float(request.env['ir.config_parameter'].sudo().get_param('hr_contract_salary.ambulatory_insurance_amount_adult', default=20.5))

        hospital_insurance_child_count = contract.insured_relative_children
        hospital_insurance_adult_count = contract.insured_relative_adults_total
        ambulatory_insurance_child_count = contract.l10n_be_ambulatory_insured_children
        ambulatory_insurance_adult_count = contract.l10n_be_ambulatory_insured_adults_total

        hospital_insurance_amount = request.env['hr.contract']._get_insurance_amount(
            hospital_insurance_child_amount, hospital_insurance_child_count,
            hospital_insurance_adult_amount, hospital_insurance_adult_count)
        ambulatory_insurance_amount = request.env['hr.contract']._get_insurance_amount(
            ambulatory_insurance_child_amount, ambulatory_insurance_child_count,
            ambulatory_insurance_adult_amount, ambulatory_insurance_adult_count)

        initial_values['has_hospital_insurance'] = hospital_insurance_amount
        initial_values['l10n_be_has_ambulatory_insurance'] = ambulatory_insurance_amount

        return mapped_benefits, mapped_dependent_benefits, mandatory_benefits, mandatory_benefits_names, benefit_types, dropdown_options, dropdown_group_options, initial_values

    def _get_new_contract_values(self, contract, employee, benefits, offer):
        res = super()._get_new_contract_values(contract, employee, benefits, offer)
        fields_to_copy = [
            'has_laptop', 'time_credit', 'work_time_rate',
            'rd_percentage', 'no_onss', 'no_withholding_taxes', 'meal_voucher_amount',
        ]
        for field_to_copy in fields_to_copy:
            if field_to_copy in contract:
                res[field_to_copy] = contract[field_to_copy]
        field_ids_to_copy = ['time_credit_type_id']
        for field_id_to_copy in field_ids_to_copy:
            if field_id_to_copy in contract:
                res[field_id_to_copy] = contract[field_id_to_copy].id
        res['has_hospital_insurance'] = float(benefits['has_hospital_insurance_radio']) == 1.0 if 'has_hospital_insurance_radio' in benefits else False
        res['l10n_be_has_ambulatory_insurance'] = float(benefits['l10n_be_has_ambulatory_insurance_radio']) == 1.0 if 'l10n_be_has_ambulatory_insurance_radio' in benefits else False
        res['l10n_be_canteen_cost'] = benefits['l10n_be_canteen_cost'] if 'l10n_be_canteen_cost' in benefits else False
        res['ip'] = bool(benefits['ip_value_radio']) if 'ip_value_radio' in benefits else False
        res['ip_wage_rate'] = benefits['ip_value'] if 'ip_value' in benefits else 0
        return res

    def create_new_contract(self, contract, offer_id, benefits, no_write=False, **kw):
        new_contract, contract_diff = super().create_new_contract(contract, offer_id, benefits, no_write=no_write, **kw)
        offer = request.env['hr.contract.salary.offer'].sudo().browse(offer_id).exists()
        if new_contract.time_credit:
            new_contract.date_end = contract.date_end
        if kw.get('package_submit', False):
            # If the chosen existing car is already taken by someone else (for example if the
            # window was open for a long time)
            if new_contract.transport_mode_car and not new_contract.new_car:
                # In case in the car was reserved for the applicant
                partner_ids = offer.applicant_id.partner_id | new_contract.employee_id.work_contact_id
                available_cars_domain = new_contract._get_available_vehicles_domain(partner_ids)
                if (new_contract.car_id not in request.env['fleet.vehicle'].sudo().search(available_cars_domain)) \
                        and (new_contract.car_id != offer.car_id):
                    return {'error': True, 'error_msg': _("Sorry, the selected car has been selected by someone else. Please refresh and try again.")}

            # Don't create simulation cars but create the wishlist car is set
            wishlist_car = benefits['contract'].get('fold_wishlist_car_total_depreciated_cost', False)
            if wishlist_car:
                dummy, model_id = benefits['contract']['select_wishlist_car_total_depreciated_cost'].split('-')
                model = request.env['fleet.vehicle.model'].sudo().with_company(new_contract.company_id).browse(int(model_id))
                state_waiting_list = request.env.ref('fleet.fleet_vehicle_state_waiting_list', raise_if_not_found=False)
                car = request.env['fleet.vehicle'].sudo().create({
                    'model_id': model.id,
                    'state_id': state_waiting_list and state_waiting_list.id,
                    'car_value': model.default_car_value,
                    'co2': model.default_co2,
                    'fuel_type': model.default_fuel_type,
                    'acquisition_date': new_contract.car_id.acquisition_date or fields.Date.today(),
                    'company_id': new_contract.company_id.id,
                    'future_driver_id': new_contract.employee_id.work_contact_id.id
                })
            return new_contract, contract_diff

        if new_contract.transport_mode_car and new_contract.new_car:
            employee = new_contract.employee_id
            model = request.env['fleet.vehicle.model'].sudo().with_company(new_contract.company_id).browse(int(new_contract.new_car_model_id))
            state_new_request = request.env.ref('fleet.fleet_vehicle_state_new_request', raise_if_not_found=False)
            new_contract.car_id = request.env['fleet.vehicle'].sudo().with_company(new_contract.company_id).create({
                'model_id': model.id,
                'state_id': state_new_request and state_new_request.id,
                'driver_id': employee.work_contact_id.id,
                'car_value': model.default_car_value,
                'co2': model.default_co2,
                'fuel_type': model.default_fuel_type,
                'company_id': new_contract.company_id.id,
            })
        return new_contract, contract_diff

    def _get_compute_results(self, new_contract):
        result = super()._get_compute_results(new_contract)
        result['double_holiday_wage'] = round(new_contract.double_holiday_wage, 2)
        # Horrible hack: Add a sequence / display condition fields on salary resume model in master
        resume = result['resume_lines_mapped']['Monthly Salary']
        if 'SALARY' in resume and resume.get('wage_with_holidays') and resume['wage_with_holidays'][1] != resume['SALARY'][1]:
            ordered_fields = ['wage_with_holidays', 'SALARY', 'NET']
            if new_contract.env.context.get('simulation_working_schedule', '100') != '100':
                salary_tuple = result['resume_lines_mapped']['Monthly Salary']['SALARY']
                salary_tuple = (_('Gross (Part Time)'), salary_tuple[1], salary_tuple[2])
                result['resume_lines_mapped']['Monthly Salary']['SALARY'] = salary_tuple
        else:
            ordered_fields = ['wage_with_holidays', 'NET']
        result['resume_lines_mapped']['Monthly Salary'] = {field: resume.get(field, 0) for field in ordered_fields}
        return result

    def _generate_payslip(self, new_contract):
        payslip = super()._generate_payslip(new_contract)
        if new_contract.car_id:
            payslip.vehicle_id = new_contract.car_id
        if new_contract.commission_on_target:
            payslip.input_line_ids = [(0, 0, {
                'input_type_id': request.env.ref('l10n_be_hr_payroll.input_fixed_commission').id,
                'amount': new_contract.commission_on_target,
            })]
        if new_contract.l10n_be_bicyle_cost:
            payslip.input_line_ids = [(0, 0, {
                'input_type_id': request.env.ref('l10n_be_hr_payroll.cp200_input_cycle_transportation').id,
                'amount': 4,  # Considers cycling one day per week
            })]
        return payslip

    def _get_payslip_line_values(self, payslip, codes):
        res = super()._get_payslip_line_values(payslip, codes + ['BASIC', 'COMMISSION'])
        res['SALARY'][payslip.id]['total'] = res['BASIC'][payslip.id]['total'] + res['COMMISSION'][payslip.id]['total']
        return res

    def _get_personal_infos_langs(self, contract, personal_info):
        active_langs = super()._get_personal_infos_langs(contract, personal_info)
        personal_info_lang = request.env.ref('l10n_be_hr_contract_salary.hr_contract_salary_personal_info_lang')
        if contract._is_struct_from_country('BE') and personal_info == personal_info_lang:
            belgian_langs = active_langs.filtered(lambda l: l.code in ["fr_BE", "fr_FR", "nl_BE", "nl_NL", "de_BE", "de_DE"])
            return active_langs if not belgian_langs else belgian_langs
        return active_langs
