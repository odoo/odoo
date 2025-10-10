# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import common
from odoo.exceptions import RedirectWarning


class TestDuplicateLicensePlate(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.brand = cls.env["fleet.vehicle.model.brand"].create({
            "name": "Audi",
        })
        cls.model = cls.env["fleet.vehicle.model"].create({
            "brand_id": cls.brand.id,
            "name": "A3",
        })

    def test_unique_license_plate(self):
        """Test that a vehicle with a unique license plate can be created successfully."""
        vehicle = self.env["fleet.vehicle"].create({
            "model_id": self.model.id,
            "license_plate": "ABC-123",
        })
        self.assertEqual(vehicle.license_plate, "ABC-123")

    def test_duplicate_license_plate_on_create(self):
        """Test that creating a vehicle with a duplicate license plate clears it and raises RedirectWarning."""
        vehicle1 = self.env["fleet.vehicle"].create({
            "model_id": self.model.id,
            "license_plate": "XYZ-789",
        })
        self.assertEqual(vehicle1.license_plate, "XYZ-789")

        with self.assertRaises(RedirectWarning):
            self.env["fleet.vehicle"].create({
                "model_id": self.model.id,
                "license_plate": "XYZ-789",
            })

    def test_duplicate_license_plate_on_write(self):
        """Test that updating a vehicle to have a duplicate license plate clears it."""
        self.env["fleet.vehicle"].create({
            "model_id": self.model.id,
            "license_plate": "DEF-456",
        })
        vehicle2 = self.env["fleet.vehicle"].create({
            "model_id": self.model.id,
            "license_plate": "GHI-789",
        })

        with self.assertRaises(RedirectWarning):
            vehicle2.license_plate = "DEF-456"

    def test_batch_creation_with_duplicate_plates(self):
        """Test that creating multiple vehicles with the same plate in batch clears all duplicates."""
        vehicle1 = self.env["fleet.vehicle"].create({
            "model_id": self.model.id,
            "license_plate": "001",
        })
        vehicle2 = self.env["fleet.vehicle"].create({
            "model_id": self.model.id,
            "license_plate": "002",
        })
        vehicles = self.env["fleet.vehicle"].create([
            {
                "model_id": self.model.id,
                "license_plate": "001",
            },
            {
                "model_id": self.model.id,
                "license_plate": "001",
            },
            {
                "model_id": self.model.id,
                "license_plate": "002",
            },
            {
                "model_id": self.model.id,
                "license_plate": "003",
            },
        ])

        self.assertEqual(vehicle1.license_plate, "001")
        self.assertEqual(vehicle2.license_plate, "002")
        self.assertFalse(vehicles[0].license_plate, "Duplicate plate '001' in batch should be cleared")
        self.assertFalse(vehicles[1].license_plate, "Duplicate plate '001' in batch should be cleared")
        self.assertFalse(vehicles[2].license_plate, "Plate '002' conflicts with existing vehicle")
        self.assertEqual(vehicles[3].license_plate, "003", "Unique plate '003' should be kept")

    def test_redirect_warning_points_to_duplicate(self):
        """Test that RedirectWarning correctly points to the duplicate vehicle."""
        vehicle1 = self.env["fleet.vehicle"].create({
            "model_id": self.model.id,
            "license_plate": "TEST-999",
        })

        try:
            self.env["fleet.vehicle"].create({
                "model_id": self.model.id,
                "license_plate": "TEST-999",
            })
        except RedirectWarning as e:
            self.assertEqual(e.args[1]['res_id'], vehicle1.id)
            self.assertEqual(e.args[1]['res_model'], 'fleet.vehicle')
            self.assertIn("Check the other vehicle", str(e))
