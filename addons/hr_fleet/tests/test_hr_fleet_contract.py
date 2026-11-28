# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form, TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestHrFleetContract(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.abigail, cls.marc = cls.env['hr.employee'].create([
            {'name': 'Abigail'},
            {'name': 'Marc'},
        ])
        brand = cls.env['fleet.vehicle.model.brand'].create({'name': 'Audi'})
        model = cls.env['fleet.vehicle.model'].create({'brand_id': brand.id, 'name': 'A3'})
        cls.car = cls.env['fleet.vehicle'].create({
            'model_id': model.id,
            'driver_employee_id': cls.abigail.id,
            'plan_to_change_vehicle': False,
        })
        cls.Contract = cls.env['fleet.vehicle.log.contract']

    def test_contract_keeps_employee_after_vehicle_driver_change(self):
        contract_1 = self.Contract.create({'vehicle_id': self.car.id})
        self.assertEqual(contract_1.purchaser_id, self.abigail.work_contact_id)
        self.assertEqual(contract_1.purchaser_employee_id, self.abigail)

        self.car.driver_employee_id = self.marc
        self.assertEqual(self.car.driver_id, self.marc.work_contact_id)
        self.assertEqual(contract_1.purchaser_id, self.abigail.work_contact_id)
        self.assertEqual(contract_1.purchaser_employee_id, self.abigail)
        self.assertEqual(contract_1.action_open_employee()['res_id'], self.abigail.id)

        contract_2 = self.Contract.create({'vehicle_id': self.car.id})
        self.assertEqual(contract_2.purchaser_employee_id, self.marc)

    def test_employee_follows_explicit_driver(self):
        contract = self.Contract.create({
            'vehicle_id': self.car.id,
            'purchaser_id': self.marc.work_contact_id.id,
        })
        self.assertEqual(contract.purchaser_id, self.marc.work_contact_id)
        self.assertEqual(contract.purchaser_employee_id, self.marc)

    def test_employee_follows_driver_edit(self):
        contract = self.Contract.create({'vehicle_id': self.car.id})
        with Form(contract) as contract_form:
            contract_form.purchaser_id = self.marc.work_contact_id
        self.assertEqual(contract.purchaser_employee_id, self.marc)
        self.assertEqual(contract.action_open_employee()['res_id'], self.marc.id)
        self.assertEqual(self.car.driver_employee_id, self.abigail, "The vehicle's driver must not change")
