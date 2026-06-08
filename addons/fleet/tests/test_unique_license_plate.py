# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged, common
from odoo.tools import mute_logger
from psycopg2 import IntegrityError


@tagged('at_install', '-post_install')
class TestUniqueLicensePlate(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.car_brand = cls.env["fleet.vehicle.model.brand"].create({
            "name": "Toyota",
        })
        cls.car_model = cls.env["fleet.vehicle.model"].create({
            "brand_id": cls.car_brand.id,
            "name": "Corolla",
        })

    def test_unique_license_plate_constraint(self):
        """Test that license plates must be unique across all vehicles"""
        vehicle1 = self.env["fleet.vehicle"].create({
            "model_id": self.car_model.id,
            "license_plate": "ABC-123",
        })
        self.assertTrue(vehicle1.id)
        with mute_logger('odoo.sql_db'), self.assertRaises(IntegrityError):
            self.env["fleet.vehicle"].create({
                "model_id": self.car_model.id,
                "license_plate": "ABC-123",
            })

    def test_unique_license_plate_allows_different_plates(self):
        """Test that vehicles with different license plates can be created"""
        vehicle1 = self.env["fleet.vehicle"].create({
            "model_id": self.car_model.id,
            "license_plate": "ABC-123",
        })
        vehicle2 = self.env["fleet.vehicle"].create({
            "model_id": self.car_model.id,
            "license_plate": "XYZ-789",
        })
        self.assertTrue(vehicle1.id)
        self.assertTrue(vehicle2.id)
        self.assertNotEqual(vehicle1.license_plate, vehicle2.license_plate)

    def test_unique_license_plate_allows_none(self):
        """Test that multiple vehicles can have no license plate (NULL values)"""
        vehicle1 = self.env["fleet.vehicle"].create({
            "model_id": self.car_model.id,
            "license_plate": False,
        })
        vehicle2 = self.env["fleet.vehicle"].create({
            "model_id": self.car_model.id,
            "license_plate": False,
        })
        self.assertTrue(vehicle1.id)
        self.assertTrue(vehicle2.id)
        self.assertFalse(vehicle1.license_plate)
        self.assertFalse(vehicle2.license_plate)
