# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.addons.pos_restaurant.tests.test_frontend import TestFrontendCommon

@tagged('post_install', '-at_install')
class TestPosRestaurantFlow(TestFrontendCommon):

    def test_floor_plans_archive(self):
        floors = self.main_floor + self.second_floor
        floors.action_archive()
        # All floors should be archived successfully
        self.assertTrue(all(floor.active is False for floor in floors), "All floors should be archived")
