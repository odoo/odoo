# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import new_test_user
from odoo.tests.common import tagged, TransactionCase

@tagged('post_install', '-at_install', 'hr_fleet_categories')
class TestFleetCategory(TransactionCase):

    def setUp(self):
        super().setUp()
        self.company = self.env['res.company'].create({
            'name': 'Taxi Dermi',
        })
        self.manager = new_test_user(self.env, login='dermi', groups='fleet.fleet_group_manager', company_id=self.company.id)
        self.addresses = self.env['res.partner'].create([
            {
                'name': 'Address 1',
                'company_id': self.company.id,
                'type': 'private',
            },
            {
                'name': 'Address 2',
                'company_id': self.company.id,
                'type': 'private',
            },
            {
                'name': 'Address 3',
                'company_id': self.company.id,
                'type': 'private',
            },
            {
                'name': 'Address 4',
                'company_id': self.company.id,
                'type': 'private',
            },
        ])
        self.employees = self.env['hr.employee'].create([
            {
                'name': 'Employee 1',
                'company_id': self.company.id,
                'address_home_id': self.addresses[0].id,
            },
            {
                'name': 'Employee 2',
                'company_id': self.company.id,
                'address_home_id': self.addresses[1].id,
            },
            {
                'name': 'Employee 3',
                'company_id': self.company.id,
                'address_home_id': self.addresses[2].id,
            },
            {
                'name': 'Employee 4',
                'company_id': self.company.id,
                'address_home_id': self.addresses[3].id,
            },
        ])

        self.brand = self.env['fleet.vehicle.model.brand'].create({
            'name': 'Test Brand',
        })
        self.model = self.env['fleet.vehicle.model'].create({
            'name': 'Test Model',
            'brand_id': self.brand.id,
        })

        self.external_fleet = self.env['fleet.category'].create({
            'name': 'External Fleet',
            'company_id': self.company.id,
            'internal': False,
        })
        self.internal_fleet = self.env['fleet.category'].create({
            'name': 'Internal Fleet',
            'company_id': self.company.id,
            'internal': True,
        })

        vehicle_create_vals = []
        for fleet in (self.external_fleet | self.internal_fleet):
            for i in range(4):
                vehicle_create_vals.append({
                    'name': 'Test Car ' + str(i) + ' ' + fleet.name,
                    'fleet_id': fleet.id,
                    'company_id': self.company.id,
                    'model_id': self.model.id,
                })
        self.env['fleet.vehicle'].create(vehicle_create_vals)

    def test_fleet_conversion(self):
        #Assign employee addresses to the fleet vehicle
        for i in range(4):
            self.external_fleet.vehicle_ids[i].driver_id = self.employees[i].address_home_id
        wizard = self.env['hr.fleet.convert.wizard'].with_context(active_id=self.external_fleet.id).new({})

        #Wizard should have a line per vehicle in the fleet
        self.assertEqual(len(self.external_fleet.vehicle_ids), len(wizard.line_ids))
        #All lines should be considered valid
        self.assertFalse(any(wizard.line_ids.filtered('invalid_driver')))

        wizard.action_validate()

        #Fleet should be internal now
        self.assertTrue(self.external_fleet.internal)
        #All vehicles should be linked to employees
        self.assertFalse(self.external_fleet.vehicle_ids.filtered(lambda v: not v.driver_employee_id))

    def test_individual_fleet_change(self):
        vehicle_id = self.external_fleet.vehicle_ids[0]
        vehicle_id.driver_id = self.addresses[0]
        #Also test future_driver
        vehicle_id.future_driver_id = self.addresses[1]

        #Manually change the fleet of the vehicle, it should compute the employee from the driver
        vehicle_id.fleet_id = self.internal_fleet
        self.assertEqual(vehicle_id.driver_employee_id, self.employees[0])
        self.assertEqual(vehicle_id.future_driver_employee_id, self.employees[1])

        #Now change it back, driver should be kept but not the employee
        vehicle_id.fleet_id = self.external_fleet
        self.assertFalse(vehicle_id.driver_employee_id)
        self.assertFalse(vehicle_id.future_driver_employee_id)

    def test_partial_conversion(self):
        #Assign employee addresses to the fleet vehicle
        for i in range(4):
            self.external_fleet.vehicle_ids[i].driver_id = self.employees[i].address_home_id
        #Remove address from employee, making the vehicle not be able to match the employee
        self.employees[2].address_home_id = False
        self.external_fleet.vehicle_ids[3].driver_id = False

        wizard = self.env['hr.fleet.convert.wizard'].with_context(active_id=self.external_fleet.id).new({})

        #Wizard should have a line per vehicle in the fleet except those without drivers
        self.assertEqual(len(self.external_fleet.vehicle_ids) - 1, len(wizard.line_ids))
        #There should be 2 valid and 1 invalid lines
        self.assertEqual(1, len(wizard.line_ids.filtered('invalid_driver')))
        self.assertEqual(2, len(wizard.line_ids.filtered(lambda l: not l.invalid_driver)))

        wizard.action_validate()
        #Fleet should be internal now
        self.assertTrue(self.external_fleet.internal)
        #There should be 2 vehicles with a driver and 2 without any
        self.assertEqual(2, len(self.external_fleet.vehicle_ids.filtered('driver_id')))
        self.assertEqual(2, len(self.external_fleet.vehicle_ids.filtered(lambda l: not l.driver_id)))
