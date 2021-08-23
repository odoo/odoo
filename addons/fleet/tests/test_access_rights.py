# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import common, new_test_user


class TestFleet(common.TransactionCase):

    def test_manager_create_vehicle(self):
        manager = new_test_user(self.env, "test fleet manager", groups="fleet.fleet_group_manager,base.group_partner_manager")
        user = new_test_user(self.env, "test base user", groups="base.group_user")
        brand = self.env["fleet.vehicle.model.brand"].create({
            "name": "Audi",
        })
        model = self.env["fleet.vehicle.model"].create({
            "brand_id": brand.id,
            "name": "A3",
        })
        self.env["fleet.vehicle"].with_user(manager).create({
            "model_id": model.id,
            "driver_id": user.partner_id.id,
            "plan_to_change_car": False
        })
