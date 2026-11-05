# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestVehicleModelFields(TransactionCase):

    def test_vehicle_range_from_model(self):
        brand = self.env['fleet.vehicle.model.brand'].create({'name': 'Brand'})
        model = self.env['fleet.vehicle.model'].create({
            'brand_id': brand.id,
            'name': 'Electric',
            'vehicle_range': 450,
        })
        vehicle = self.env['fleet.vehicle'].create({'model_id': model.id})
        self.assertEqual(vehicle.vehicle_range, 450)
        # still editable on the vehicle
        vehicle.vehicle_range = 400
        self.assertEqual(vehicle.vehicle_range, 400)

    def test_model_co2_required(self):
        brand = self.env['fleet.vehicle.model.brand'].create({'name': 'Volvo'})
        with self.assertRaises(ValidationError):
            self.env['fleet.vehicle.model'].create({
                'brand_id': brand.id, 'name': 'Volvo V60', 'default_fuel_type': 'diesel', 'default_co2': 0,
            })
        self.env['fleet.vehicle.model'].create({
            'brand_id': brand.id, 'name': 'Volvo EX30', 'default_fuel_type': 'electric', 'default_co2': 0,
        })
        self.env['fleet.vehicle.model'].create({
            'brand_id': brand.id, 'name': 'Toyota Mirai', 'default_fuel_type': 'hydrogen', 'default_co2': 0,
        })

    def test_vehicle_co2_required(self):
        brand = self.env['fleet.vehicle.model.brand'].create({'name': 'Volvo'})
        model = self.env['fleet.vehicle.model'].create({'brand_id': brand.id, 'name': 'Volvo EX40'})
        vehicle = self.env['fleet.vehicle'].create({'model_id': model.id})
        with self.assertRaises(ValidationError):
            vehicle.fuel_type = 'diesel'
        vehicle.write({'fuel_type': 'diesel', 'co2': 120})
        self.assertEqual(vehicle.co2, 120)
