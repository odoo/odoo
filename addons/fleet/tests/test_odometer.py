from odoo.tests import common, new_test_user


class TestFleet(common.TransactionCase):

    def test_new_driver_odometer(self):
        user1 = new_test_user(self.env, "test user 1", groups="base.group_user")
        user2 = new_test_user(self.env, "test user 2", groups="base.group_user")

        brand = self.env["fleet.vehicle.model.brand"].create({
            "name": "Audi",
        })
        model = self.env["fleet.vehicle.model"].create({
            "brand_id": brand.id,
            "name": "A3",
        })
        vehicle = self.env["fleet.vehicle"].create({
            "model_id": model.id,
            "driver_id": user1.partner_id.id,
            "plan_to_change_car": False
        })

        odometer1 = self.env["fleet.vehicle.odometer"].create({
            "value": 100,
            "vehicle_id": vehicle.id
        })

        self.assertEqual(odometer1.driver_id, user1.partner_id)

        vehicle.driver_id = user2.partner_id.id
        odometer2 = self.env["fleet.vehicle.odometer"].create({
            "value": 100,
            "vehicle_id": vehicle.id
        })

        self.assertEqual(odometer2.driver_id, user2.partner_id)
        self.assertEqual(odometer1.driver_id, user1.partner_id)
