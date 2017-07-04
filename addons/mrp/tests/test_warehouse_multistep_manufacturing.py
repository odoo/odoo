# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mrp.tests.common import TestMrpCommon


class TestMultistepManufacturingWarehouse(TestMrpCommon):

    def setUp(self):
        super(TestMultistepManufacturingWarehouse, self).setUp()
        # Create warehouse
        self.warehouse = self.env['stock.warehouse'].create({
            'name': 'Test Warehouse',
            'code': 'TWH',
        })

    def _check_location_and_routes(self):
        # Check manufacturing pull rule.
        self.assertTrue(self.warehouse.manufacture_pull_id)
        self.assertTrue(self.warehouse.manufacture_pull_id.active, self.warehouse.manufacture_to_resupply)
        self.assertTrue(self.warehouse.manufacture_pull_id.route_id)
        # Check new routes created or not.
        self.assertTrue(self.warehouse.multistep_manu_route_id)
        # Check location should be created and linked to warehouse.
        self.assertTrue(self.warehouse.wh_input_manu_loc_id)
        self.assertEqual(self.warehouse.wh_input_manu_loc_id.active, self.warehouse.manufacture_steps != 'manu_only', "Input location must be de-active for single step only.")
        self.assertTrue(self.warehouse.manu_type_id.active)
        self.assertEqual(self.warehouse.wh_input_manu_loc_id.active if self.warehouse.manufacture_steps != 'manu_only' else False, self.warehouse.manufacture_steps != 'manu_only')

    def test_00_create_warehouse(self):
        """ Warehouse testing for Step-1 """
        self.warehouse.manufacture_steps = 'manu_only'
        self._check_location_and_routes()
        # TODO : Check locations of existing pull rule
        # TODO : Check picking types
        self.assertEqual(self.warehouse.manufacture_pull_id.location_id.id, self.warehouse.lot_stock_id.id)
        self.assertEqual(self.warehouse.manufacture_pull_id.location_src_id.id, self.warehouse.lot_stock_id.id)

    def test_01_warehouse_twostep_manufacturing(self):
        """ Warehouse testing for Step-2 """
        self.warehouse.manufacture_steps = 'pick_manu'
        self._check_location_and_routes()
        self.assertEqual(self.warehouse.manufacture_pull_id.location_id.id, self.warehouse.lot_stock_id.id)
        self.assertEqual(self.warehouse.manufacture_pull_id.location_src_id.id, self.warehouse.wh_input_manu_loc_id.id)
