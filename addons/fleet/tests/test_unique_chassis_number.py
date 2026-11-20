# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('-at_install', 'post_install')
class TestUniqueChassisNumber(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        brand = cls.env['fleet.vehicle.model.brand'].create({'name': 'Super Speedy Cider Squeezy'})
        cls.model = cls.env['fleet.vehicle.model'].create({
            'brand_id': brand.id,
            'name': 'V6000',
        })
        cls.existing_vehicles = cls._create_vehicles('VIN-001', 'VIN-002')

    @classmethod
    def _create_vehicles(cls, *chassis_numbers):
        return cls.env['fleet.vehicle'].create([
            {'model_id': cls.model.id, 'vin_sn': vin_sn}
            for vin_sn in chassis_numbers
        ])

    def test_new_chassis_number(self):
        """
        A vehicle can be created with a chassis number no other vehicle has,
        but not with one that is already taken
        """
        vehicle = self._create_vehicles('VIN-003')
        self.assertEqual(
            vehicle.vin_sn, 'VIN-003',
            "The vehicle must be created with the chassis number it was given",
        )

        taken_vehicle = self.existing_vehicles[0]
        with self.assertRaises(ValidationError) as error:
            self._create_vehicles(taken_vehicle.vin_sn)
        self.assertEqual(
            str(error.exception),
            f"The chassis number {taken_vehicle.vin_sn} is already taken by vehicle {taken_vehicle.name}",
            "The error must name the vehicle that already has this chassis number",
        )

    def test_multiple_new_chassis_numbers(self):
        """
        Several vehicles can be created at once as long as their chassis
        numbers are all different
        """
        vehicles = self._create_vehicles('VIN-003', 'VIN-004')
        self.assertEqual(
            vehicles.mapped('vin_sn'), ['VIN-003', 'VIN-004'],
            "Every vehicle must be created with its own chassis number",
        )

    def test_multiple_chassis_numbers_already_taken(self):
        """
        Creating several vehicles at once fails when some of their chassis
        numbers are already taken, and every conflict is listed
        """
        with self.assertRaises(ValidationError) as error:
            self._create_vehicles('VIN-003', 'VIN-001', 'VIN-002')
        message = str(error.exception)
        expected_duplicates = [
            f"  - {vehicle.name} already has chassis number {vehicle.vin_sn}"
            for vehicle in self.existing_vehicles
        ]
        # the header line plus one line per conflicting vehicle
        self.assertEqual(
            len(message.splitlines()), len(expected_duplicates) + 1,
            "The error must list every chassis number that is already taken",
        )
        for duplicate in expected_duplicates:
            self.assertIn(
                duplicate, message,
                "The error must list every chassis number that is already taken",
            )

    def test_duplicated_chassis_number_in_batch(self):
        """
        Vehicles created together cannot share a chassis number: the error
        tells how many of them do
        """
        chassis_number = 'VIN-003'
        count = 3
        with self.assertRaises(ValidationError) as error:
            self._create_vehicles(*([chassis_number] * count))
        self.assertEqual(
            str(error.exception),
            f"You are trying to create {count} vehicles with the same chassis number ({chassis_number}).\n"
            "The chassis number should be unique for every vehicle.",
        )
