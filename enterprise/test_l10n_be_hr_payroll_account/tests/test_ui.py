# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

import odoo.tests
from . import common


@odoo.tests.tagged('-at_install', 'post_install', 'salary')
class Testl10nBeHrPayrollAccountUi(common.TestPayrollAccountCommon):
    def test_ui(self):
        with freeze_time("2022-01-01 10:00:00"):
            self.start_tour("/", 'hr_contract_salary_tour', login='admin', timeout=350)

            new_contract_id = self.env['hr.contract'].search([('name', 'ilike', 'nathalie')])
            self.assertTrue(new_contract_id, 'A contract has been created')
            new_employee_id = new_contract_id.employee_id
            self.assertTrue(new_employee_id, 'An employee has been created')
            self.assertFalse(new_employee_id.active, 'Employee is not yet active')

            # asserts that '0' values automatically filled are actually being saved
            children_count = self.env['sign.request.item.value'].search([
                ('sign_item_id.name', '=', "employee_id.children"),
                ('sign_request_id', '=', new_contract_id.sign_request_ids.id)
            ], limit=1)
            self.assertEqual(children_count.value, '0')

        with freeze_time("2022-01-01 11:00:00"):
            self.start_tour("/", 'hr_contract_salary_tour_hr_sign', login='admin', timeout=350)
            # Contract is signed by new employee and HR, the new car must be created, and the allocation should be created and validated
            vehicle = self.env['fleet.vehicle'].search([('company_id', '=', self.company_id.id), ('model_id', '=', self.model_a3.id)])
            self.assertTrue(vehicle, 'A vehicle Exists')
            self.assertEqual(vehicle.future_driver_id, new_employee_id.work_contact_id, 'Futur driver is set')
            self.assertEqual(vehicle.company_id, new_contract_id.company_id, 'Vehicle is in the right company')
            self.assertEqual(vehicle, new_contract_id.car_id, 'Car id is set properly')
            allocation = self.env['hr.leave.allocation'].search([('employee_id', '=', new_employee_id.id), ('holiday_status_id', '=', self.extra_days_time_off_type.id)])
            self.assertTrue(allocation, 'Allocation has been created')
            self.assertEqual(allocation.number_of_days, 3, 'Correct number of extra days allocated')
            self.assertEqual(allocation.state, 'validate', 'Allocation has been validated')
            self.assertTrue(new_employee_id.active, 'Employee is now active')

            # In the new contract, we can choose to order a car in the wishlist.
            self.env['ir.config_parameter'].sudo().set_param('l10n_be_hr_payroll_fleet.max_unused_cars', 1)

        with freeze_time("2022-01-01 12:00:00"):
            self.start_tour("/", 'hr_contract_salary_tour_2', login='admin', timeout=350)
            new_contract_id = self.env['hr.contract'].search([('name', 'ilike', 'Mitchell Admin 3')])
            self.assertTrue(new_contract_id, 'A contract has been created')
            new_employee_id = new_contract_id.employee_id
            self.assertTrue(new_employee_id, 'An employee has been created')
            self.assertTrue(new_employee_id.active, 'Employee is active')
            self.assertEqual(new_contract_id.new_car_model_id, self.model_corsa, 'Car is right model')

            vehicle = self.env['fleet.vehicle'].search([('company_id', '=', self.company_id.id), ('model_id', '=', self.model_corsa.id)])
            self.assertFalse(vehicle, 'A vehicle has not been created')

        with freeze_time("2022-01-01 13:00:00"):
            # We now fully sign the offer to see if the vehicle to order is created correctly
            self.start_tour("/", 'hr_contract_salary_tour_counter_sign', login='admin', timeout=350, step_delay=300)

            vehicle = self.env['fleet.vehicle'].search([('company_id', '=', self.company_id.id), ('model_id', '=', self.model_corsa.id)])
            self.assertTrue(vehicle, 'A vehicle has been created')
            self.assertEqual(vehicle.model_id, self.model_corsa, 'Car is right model')
            self.assertEqual(vehicle.future_driver_id, new_employee_id.work_contact_id, 'Future Driver is set correctly')
            self.assertEqual(vehicle, new_contract_id.ordered_car_id, 'Ordered Car appears in contract')
            self.assertEqual(vehicle.state_id, self.env.ref('fleet.fleet_vehicle_state_new_request'), 'Car created in right state')
            self.assertEqual(vehicle.company_id, new_contract_id.company_id, 'Vehicle is in the right company')
