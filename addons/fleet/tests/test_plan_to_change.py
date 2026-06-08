# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged, new_test_user
from .test_access_rights import TestFleet


@tagged('post_install', '-at_install')
class TestFleetVehicleDriverCancellation(TestFleet):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.bob = new_test_user(
            cls.env,
            login='bob_user',
            name='Bob',
            groups="base.group_user",
        )

        cls.alice = new_test_user(
            cls.env,
            login='alice_user',
            name='Alice',
            groups="base.group_user",
        )

    def test_01_cancel_plan_to_change_car(self):
        """
        Test the core scenario:
        Bob is driver of car A, he receives his link and sign with another car B
            Car A : Driver Bob + Plan to change = true
            Car B : Future Driver : Bob
        Bob changes his mind and finally takes back his car A
            Car A : Driver Bob
            Car B :
        """
        car_a = self.env["fleet.vehicle"].create({
            "model_id": self.car_model.id,
            "driver_id": self.bob.partner_id.id,
            "plan_to_change_vehicle": True,
        })
        car_b = self.env["fleet.vehicle"].create({
            "model_id": self.car_model.id,
            "future_driver_id": self.bob.partner_id.id,
        })

        car_a.write({"future_driver_id": self.bob.partner_id.id})

        self.assertFalse(car_a.plan_to_change_vehicle, "CarA plan to change should be False.")
        self.assertFalse(car_a.future_driver_id, "CarA Future Driver should be cleared.")
        self.assertFalse(car_b.future_driver_id, "Car B Future Driver should be cleared.")

    def test_02_cancel_plan_to_change_bike(self):
        """
        Test the core scenario:
        Bob is driver of Bike A, he receives his link and sign with another Bike B.
            Bike A : Driver Bob + Plan to change = true
            Bike B : Future Driver : Bob
        Bob changes his mind and finally takes back his Bike A
            Bike A : Driver Bob
            Bike B :
        """
        bike_a = self.env["fleet.vehicle"].create({
            "model_id": self.bike_model.id,
            "driver_id": self.bob.partner_id.id,
            "plan_to_change_vehicle": True,
        })
        bike_b = self.env["fleet.vehicle"].create({
            "model_id": self.bike_model.id,
            "future_driver_id": self.bob.partner_id.id,
        })

        bike_a.write({"future_driver_id": self.bob.partner_id.id})

        self.assertFalse(bike_a.plan_to_change_vehicle, "BikeA plan to change should be False.")
        self.assertFalse(bike_a.future_driver_id, "BikeA Future Driver should be cleared.")
        self.assertFalse(bike_b.future_driver_id, "BikeB Future Driver should be cleared.")

    def test_03_cancel_plan_to_change_multi_users(self):
        """
        Test crossing users & vehicles scenario:
        Bob is driver of car A, he receives his link and sign with another car B
            Car A : Driver Bob + Plan to change = true
            Car B : Driver Alice + Future Driver : Bob
        Alice is driver of car B, he receives his link and sign with another car A
            Car A : Driver Bob + Plan to change = true + Future Driver : Alice
            Car B : Driver Alice + Plan to change = true + Future Driver : Bob
        Then,
        Alice changes his mind and finally takes back his Car B
            Car A : Driver Bob + Plan to change = true
            Car B : Driver Alice
        """
        car_a = self.env["fleet.vehicle"].create({
            "model_id": self.car_model.id,
            "driver_id": self.bob.partner_id.id,
            "future_driver_id": self.alice.partner_id.id,
            "plan_to_change_vehicle": True,
        })

        car_b = self.env["fleet.vehicle"].create({
            "model_id": self.car_model.id,
            "driver_id": self.alice.partner_id.id,
            "future_driver_id": self.bob.partner_id.id,
            "plan_to_change_vehicle": True,
        })

        car_b.write({"future_driver_id": self.alice.partner_id.id})

        self.assertEqual(car_b.driver_id, self.alice.partner_id, "Car B driver remains Alice.")
        self.assertFalse(car_b.future_driver_id, "Car B Future Driver should be cleared.")
        self.assertFalse(car_b.plan_to_change_vehicle, "Car B Plan to change should be False.")

        self.assertEqual(car_a.driver_id, self.bob.partner_id, "Car A driver remains Bob.")
        self.assertFalse(car_a.future_driver_id, "Car A Future Driver should be cleared.")
        self.assertTrue(car_a.plan_to_change_vehicle, "Car A Plan to change remains True.")

    def test_04_cancel_plan_to_change_multiple_intersecting_vehicles(self):
        """
        Test Complex scenario with multiple intersecting vehicles:
        Alice is driver of car B, she receives her link and signs with another car D
            Car B : Driver Alice + Plan to change = true + Future Driver = Bob
            Car D : Future Driver : Alice
        Bob is driver of car A, he receives his link and signs with another car B
            Car A : Driver Bob + Plan to change = true
            Car B : Driver Alice + Future Driver : Bob
        Bob is driver of car A, he receives another link and signs with another car C
            Car A : Driver Bob + Plan to change = true
            Car C : Future Driver : Bob

        Then,
        Bob changes his mind and finally takes back his car A
            Car A : Driver Bob
            Car B : Driver Alice + Plan to change = true
            Car C :
            Car D : Future Driver : Alice

        Bike E is unrelated (different type)
        """
        car_a = self.env["fleet.vehicle"].create({
            "model_id": self.car_model.id,
            "driver_id": self.bob.partner_id.id,
            "plan_to_change_vehicle": True,
        })

        car_b = self.env["fleet.vehicle"].create({
            "model_id": self.car_model.id,
            "driver_id": self.alice.partner_id.id,
            "future_driver_id": self.bob.partner_id.id,
            "plan_to_change_vehicle": True,
        })

        car_c = self.env["fleet.vehicle"].create({
            "model_id": self.car_model.id,
            "future_driver_id": self.bob.partner_id.id,
        })

        car_d = self.env["fleet.vehicle"].create({
            "model_id": self.car_model.id,
            "future_driver_id": self.alice.partner_id.id,
        })

        bike_e = self.env["fleet.vehicle"].create({
            "model_id": self.bike_model.id,
            "future_driver_id": self.bob.partner_id.id,
        })

        car_a.write({"future_driver_id": self.bob.partner_id.id})

        self.assertEqual(car_a.driver_id, self.bob.partner_id, "Car A (Bob) remains the driver")
        self.assertFalse(car_a.future_driver_id, "Car A future driver cleared")
        self.assertFalse(car_a.plan_to_change_vehicle, "Car A plan_to_change cleared")

        self.assertEqual(car_b.driver_id, self.alice.partner_id, "Car B (Alice) must remain unchanged")
        self.assertFalse(car_b.future_driver_id, "Car B future driver cleared")
        self.assertTrue(car_b.plan_to_change_vehicle, "Car B plan_to_change  must remain unchanged")

        self.assertFalse(car_c.future_driver_id, "Car C future driver cleared")
        self.assertEqual(car_d.future_driver_id, self.alice.partner_id, "Car D (Alice) must remain unchanged")

        self.assertEqual(bike_e.future_driver_id, self.bob.partner_id, "Bike E must not be affected (different vehicle type)")

    def test_05_plan_to_change_with_driving_two_different_vehicle_types_at_same_time(self):
        """
        Test Car & Bike drive at the same time scenario:
        Bob is driver of car A and Bike A, he receives his link and sign with another car Z
            Car A : Driver Bob + Plan to change = true
            Car Z: Future Driver : Bob
            Bike A: Driver Bob
        Bob changes his mind and finally takes back his car A
            Car A : Driver Bob
            Bike A: Driver Bob

        Alice is driver of car B and Bike B, she receives her link and signs with another Bike Y
            Car B : Driver Alice
            Bike B: Driver Alice  + Plan to change = true
            Bike Y: Future Driver Alice
        Alice changes her mind and finally takes back her Bike B
            Car B : Driver Alice
            Bike B: Driver Alice
        """
        car_a = self.env["fleet.vehicle"].create({
            "model_id": self.car_model.id,
            "driver_id": self.bob.partner_id.id,
            "plan_to_change_vehicle": True,
        })
        bike_a = self.env["fleet.vehicle"].create({
            "model_id": self.bike_model.id,
            "driver_id": self.bob.partner_id.id,
        })
        car_z = self.env["fleet.vehicle"].create({
            "model_id": self.car_model.id,
            "future_driver_id": self.bob.partner_id.id,
        })

        car_b = self.env["fleet.vehicle"].create({
            "model_id": self.car_model.id,
            "driver_id": self.alice.partner_id.id,
        })
        bike_b = self.env["fleet.vehicle"].create({
            "model_id": self.bike_model.id,
            "driver_id": self.alice.partner_id.id,
            "plan_to_change_vehicle": True,
        })
        bike_y = self.env["fleet.vehicle"].create({
            "model_id": self.bike_model.id,
            "future_driver_id": self.alice.partner_id.id,
        })

        car_a.future_driver_id = self.bob.partner_id
        bike_b.future_driver_id = self.alice.partner_id

        # Trigger the write on both at the same time
        (car_a + bike_b).write({'description': 'Batch Cancellation'})

        self.assertEqual(car_a.driver_id, self.bob.partner_id, "Car A (Bob) remains the driver")
        self.assertEqual(bike_a.driver_id, self.bob.partner_id, "Bike A (Bob) remains the driver")
        self.assertFalse(car_a.future_driver_id, "Car A future driver cleared")
        self.assertFalse(car_a.plan_to_change_vehicle, "Car A plan_to_change cleared")
        self.assertFalse(car_z.future_driver_id, "Car Z future driver cleared")

        self.assertEqual(car_b.driver_id, self.alice.partner_id, "Car B (Alice) remains the driver")
        self.assertEqual(bike_b.driver_id, self.alice.partner_id, "Bike B (Alice) remains the driver")
        self.assertFalse(bike_b.future_driver_id, "Bike B future driver cleared")
        self.assertFalse(bike_b.plan_to_change_vehicle, "Bike B plan_to_change cleared")
        self.assertFalse(bike_y.future_driver_id, "Bike Y future driver cleared")
