# Part of Odoo. See LICENSE file for full copyright and licensing details.
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
