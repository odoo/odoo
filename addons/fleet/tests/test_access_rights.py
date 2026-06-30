# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import common, new_test_user


class TestFleet(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.manager = new_test_user(cls.env, "test fleet manager", groups="fleet.fleet_group_manager,base.group_partner_manager")
        cls.user = new_test_user(cls.env, "test base user", groups="base.group_user")
        cls.car_brand, cls.bike_brand = cls.env["fleet.vehicle.model.brand"].create([
            {"name": "Audi"},
            {"name": "Nakamura"},
        ])
        cls.car_model, cls.bike_model = cls.env["fleet.vehicle.model"].create([
            {
                "brand_id": cls.car_brand.id,
                "name": "A3",
            },
            {
                "brand_id": cls.bike_brand.id,
                "name": "Crossover xv",
                "vehicle_type": "bike",
            },
        ])

    def test_manager_create_vehicle(self):
        car = self.env["fleet.vehicle"].with_user(self.manager).create({
            "model_id": self.car_model.id,
            "driver_id": self.user.partner_id.id,
            "plan_to_change_car": False
        })
        car.with_user(self.manager).plan_to_change_car = True

    def test_change_future_driver(self):
        car1, car2, bike1, bike2 = self.env["fleet.vehicle"].create([
            {
                "model_id": self.car_model.id,
                "driver_id": self.user.partner_id.id,
                "plan_to_change_car": False,
            },
            {
                "model_id": self.car_model.id,
                "driver_id": self.manager.partner_id.id,
                "plan_to_change_car": False,
            },
            {
                "model_id": self.bike_model.id,
                "driver_id": self.user.partner_id.id,
                "plan_to_change_car": False,
            },
            {
                "model_id": self.bike_model.id,
                "driver_id": self.manager.partner_id.id,
                "plan_to_change_car": False,
            },
        ])
        self.assertFalse(car1.future_driver_id)
        self.assertFalse(bike1.future_driver_id)
        self.assertFalse(car1.plan_to_change_car)
        self.assertFalse(bike1.plan_to_change_bike)
        self.assertFalse(car2.future_driver_id)
        self.assertFalse(bike2.future_driver_id)
        self.assertFalse(car2.plan_to_change_car)
        self.assertFalse(bike2.plan_to_change_bike)

        (car1 + bike1).write({"future_driver_id": self.manager.partner_id.id})
        self.assertEqual(car1.future_driver_id, self.manager.partner_id)
        self.assertEqual(bike1.future_driver_id, self.manager.partner_id)
        self.assertFalse(bike1.plan_to_change_bike)
        self.assertFalse(car1.plan_to_change_car)
        self.assertFalse(car2.future_driver_id)
        self.assertFalse(bike2.future_driver_id)
        self.assertTrue(car2.plan_to_change_car)
        self.assertTrue(bike2.plan_to_change_bike)
