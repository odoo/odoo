# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged, common


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestHrFleetDriver(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.test_employee = cls.env['hr.employee'].create({
            'name': 'Test Employee'
        })

        cls.test_user = cls.env['res.users'].create({
            'login': 'test',
            'name': 'The King',
            'email': 'noop@example.com',
        })

        cls.brand = cls.env["fleet.vehicle.model.brand"].create({
            "name": "Audi",
        })

        cls.model = cls.env["fleet.vehicle.model"].create({
            "brand_id": cls.brand.id,
            "name": "A3",
        })

        cls.car = cls.env["fleet.vehicle"].create({
            "model_id": cls.model.id,
            "future_driver_id": cls.test_employee.work_contact_id.id,
            "plan_to_change_vehicle": False,
            "fuel_type": "diesel"
        })

        cls.car2 = cls.env["fleet.vehicle"].create({
            "model_id": cls.model.id,
            "plan_to_change_vehicle": False,
            "fuel_type": "diesel"
        })

    def test_driver_sync_with_employee(self):
        """
        If an employee has a car and their partner has changed, the update should be synced with the fleet
        """
        self.assertEqual(self.car.future_driver_id, self.test_employee.work_contact_id)
        self.test_employee.user_id = self.test_user
        self.assertEqual(self.test_employee.work_contact_id, self.test_user.partner_id)
        self.car.action_accept_driver_change()
        self.assertEqual(self.car.driver_id, self.test_user.partner_id)

    def test_driver_sync_with_employee_without_contact(self):
        """
        When we create an employee with a user_id, he doesn't have a
        work_contact_id and we don't want to assign him all unassigned
        cars.
        """
        self.assertEqual(self.car2.future_driver_id.id, False)
        self.assertEqual(self.car2.driver_id.id, False)
        self.env['hr.employee'].create({
            'name': 'Test Employee 2',
            'user_id': self.test_user.id,
        })
        self.assertEqual(self.car2.future_driver_id.id, False)
        self.assertEqual(self.car2.driver_id.id, False)

    def test_driver_employee_multi_company(self):
        other_company = self.env['res.company'].create({
            'name': 'Other Company'
        })
        test_employee2 = self.env['hr.employee'].with_company(other_company).create({
            'name': 'Test Employee 2',
            'work_contact_id': self.test_employee.work_contact_id.id
        })
        car = self.env['fleet.vehicle'].with_company(other_company).create({
            'model_id': self.model.id,
            'driver_id': test_employee2.work_contact_id.id
        })
        self.assertEqual(car.driver_employee_id, test_employee2)

        assignation_log = self.env['fleet.vehicle.assignation.log'].search([
            ('vehicle_id', '=', car.id)
        ])
        self.assertEqual(len(assignation_log), 1)
        self.assertEqual(assignation_log.driver_employee_id, test_employee2)

    def test_assignation_log_create_sets_vehicle_driver(self):
        """
        Creating a fleet.vehicle.assignation.log should assign vehicle.driver_id
        only if vehicle has no driver and today is within assignation period.
        """

        today = fields.Date.today()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)

        # vehicle with no driver yet
        vehicle = self.car2
        vehicle.write({"plan_to_change_vehicle": True})
        self.assertFalse(vehicle.driver_id, "Precondition: vehicle2 has no driver")

        # Create assignation log with valid today-included date range
        self.env["fleet.vehicle.assignation.log"].create({
            "vehicle_id": vehicle.id,
            "driver_id": self.test_employee.work_contact_id.id,
            "date_start": yesterday,
            "date_end": tomorrow,
        })
        self.assertEqual(
            vehicle.driver_id,
            self.test_employee.work_contact_id,
            "Vehicle driver should be set when date includes today and no driver assigned",
        )
        self.assertFalse(vehicle.plan_to_change_vehicle, "Plan to change car should be set to False")
        # Create another assignation for same vehicle, driver should NOT be changed because vehicle has driver
        self.env["fleet.vehicle.assignation.log"].create({
            "vehicle_id": vehicle.id,
            "driver_id": self.test_user.partner_id.id,
            "date_start": tomorrow + timedelta(days=1),
            "date_end": tomorrow + timedelta(days=3),
        })
        # driver stays unchanged
        self.assertEqual(
            vehicle.driver_id,
            self.test_employee.work_contact_id,
            "Vehicle driver should not change if already assigned",
        )

        # Create assignation where date range excludes today, driver should NOT be assigned
        vehicle3 = self.car
        vehicle3.driver_id = False  # reset driver for test
        self.env["fleet.vehicle.assignation.log"].create({
            "vehicle_id": vehicle3.id,
            "driver_id": self.test_user.partner_id.id,
            "date_start": today + timedelta(days=2),
            "date_end": today + timedelta(days=3),
        })
        self.assertFalse(vehicle3.driver_id, "Vehicle driver should not be set if today not in assignation period")

    def test_assignation_overlap_validation(self):
        """Overlapping assignation logs for the same vehicle should raise a ValidationError."""

        today = fields.Date.today()
        vehicle = self.car

        # Base assignation: yesterday → tomorrow
        self.env['fleet.vehicle.assignation.log'].create({
            'vehicle_id': vehicle.id,
            'driver_id': self.test_employee.work_contact_id.id,
            'date_start': today - timedelta(days=1),
            'date_end': today + timedelta(days=1),
        })

        # No overlap (ends before the first starts)
        self.env['fleet.vehicle.assignation.log'].create({
            'vehicle_id': vehicle.id,
            'driver_id': self.test_user.partner_id.id,
            'date_start': today - timedelta(days=5),
            'date_end': today - timedelta(days=3),
        })

        # Overlaps at the start
        with self.assertRaises(ValidationError, msg="Overlap at the start should raise ValidationError"):
            self.env['fleet.vehicle.assignation.log'].create({
                'vehicle_id': vehicle.id,
                'driver_id': self.test_user.partner_id.id,
                'date_start': today - timedelta(days=2),
                'date_end': today,
            })

        # Overlaps at the end
        with self.assertRaises(ValidationError, msg="Overlap at the end should raise ValidationError"):
            self.env['fleet.vehicle.assignation.log'].create({
                'vehicle_id': vehicle.id,
                'driver_id': self.test_user.partner_id.id,
                'date_start': today,
                'date_end': today + timedelta(days=2),
            })

        # Fully enclosed inside first assignation
        with self.assertRaises(ValidationError, msg="Enclosed overlap should raise ValidationError"):
            self.env['fleet.vehicle.assignation.log'].create({
                'vehicle_id': vehicle.id,
                'driver_id': self.test_user.partner_id.id,
                'date_start': today,
                'date_end': today,
            })

        # Overlaps open-ended assignation (no date_end)
        self.env['fleet.vehicle.assignation.log'].create({
            'vehicle_id': vehicle.id,
            'driver_id': self.test_employee.work_contact_id.id,
            'date_start': today + timedelta(days=5),
            'date_end': False,
        })
        with self.assertRaises(ValidationError, msg="Open-ended overlap should raise ValidationError"):
            self.env['fleet.vehicle.assignation.log'].create({
                'vehicle_id': vehicle.id,
                'driver_id': self.test_user.partner_id.id,
                'date_start': today + timedelta(days=6),
                'date_end': today + timedelta(days=10),
            })
