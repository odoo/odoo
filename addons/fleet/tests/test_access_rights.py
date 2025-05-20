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
        car, bike = self.env["fleet.vehicle"].create([
            {
                "model_id": self.car_model.id,
                "driver_id": self.user.partner_id.id,
                "plan_to_change_car": False
            },
            {
                "model_id": self.bike_model.id,
                "driver_id": self.user.partner_id.id,
                "plan_to_change_car": False,
            }
        ])
        self.assertFalse(car.future_driver_id)
        self.assertFalse(bike.future_driver_id)
        self.assertFalse(self.manager.partner_id.plan_to_change_bike)
        self.assertFalse(self.manager.partner_id.plan_to_change_car)

        (car + bike).write({"future_driver_id": self.manager.partner_id.id})
        self.assertEqual(car.future_driver_id, self.manager.partner_id)
        self.assertEqual(bike.future_driver_id, self.manager.partner_id)
        self.assertTrue(self.manager.partner_id.plan_to_change_bike)
        self.assertTrue(self.manager.partner_id.plan_to_change_car)
