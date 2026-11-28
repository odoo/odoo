# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form, TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestContractDriver(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.abigail, cls.marc = cls.env['res.partner'].create([
            {'name': 'Abigail'},
            {'name': 'Marc'},
        ])
        brand = cls.env['fleet.vehicle.model.brand'].create({'name': 'Audi'})
        model = cls.env['fleet.vehicle.model'].create({'brand_id': brand.id, 'name': 'A3'})
        cls.car_abigail, cls.car_marc = cls.env['fleet.vehicle'].create([
            {'model_id': model.id, 'driver_id': cls.abigail.id, 'plan_to_change_vehicle': False},
            {'model_id': model.id, 'driver_id': cls.marc.id, 'plan_to_change_vehicle': False},
        ])
        cls.Contract = cls.env['fleet.vehicle.log.contract']

    def test_new_contract_takes_vehicle_driver(self):
        contract = self.Contract.create({'vehicle_id': self.car_abigail.id})
        self.assertEqual(contract.purchaser_id, self.abigail)

    def test_explicit_driver_at_creation_is_kept(self):
        contract = self.Contract.create({'vehicle_id': self.car_abigail.id, 'purchaser_id': self.marc.id})
        self.assertEqual(contract.purchaser_id, self.marc)
        self.assertEqual(self.car_abigail.driver_id, self.abigail, "The vehicle's driver must not change")

    def test_driver_kept_after_vehicle_driver_change(self):
        contract_1 = self.Contract.create({'vehicle_id': self.car_abigail.id})
        self.car_abigail.driver_id = self.marc
        self.assertEqual(contract_1.purchaser_id, self.abigail, "An existing contract keeps its driver")

        contract_2 = self.Contract.create({'vehicle_id': self.car_abigail.id})
        self.assertEqual(contract_2.purchaser_id, self.marc, "A new contract takes the current driver")

    def test_vehicle_change_recomputes_driver(self):
        contract = self.Contract.create({'vehicle_id': self.car_abigail.id})
        with Form(contract) as contract_form:
            contract_form.vehicle_id = self.car_marc
            self.assertEqual(contract_form.purchaser_id, self.marc)
        self.assertEqual(contract.purchaser_id, self.marc)
