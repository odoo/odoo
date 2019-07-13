# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import common
from odoo.exceptions import except_orm


class TestWarehouse(common.TestMrpCommon):
    def setUp(self):
        super(TestWarehouse, self).setUp()

        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.depot_location = self.env['stock.location'].create({
            'name': 'Depot',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })
        putaway = self.env['product.putaway'].create({
            'name': 'putaway stock->depot',
            'fixed_location_ids': [(0, 0, {
                'category_id': self.env.ref('product.product_category_all').id,
                'fixed_location_id': self.depot_location.id,
            })]
        })
        self.stock_location.write({
            'putaway_strategy_id': putaway.id,
        })

        self.laptop = self.env.ref("product.product_product_25")
        graphics_card = self.env.ref("product.product_product_24")
        unit = self.env.ref("uom.product_uom_unit")
        mrp_routing = self.env.ref("mrp.mrp_routing_0")

        bom_laptop = self.env['mrp.bom'].create({
            'product_tmpl_id': self.laptop.product_tmpl_id.id,
            'product_qty': 1,
            'product_uom_id': unit.id,
            'bom_line_ids': [(0, 0, {
                'product_id': graphics_card.id,
                'product_qty': 1,
                'product_uom_id': unit.id
            })],
            'routing_id': mrp_routing.id
        })

        # Return a new Manufacturing Order for laptop
        def new_mo_laptop():
            return self.env['mrp.production'].create({
                'product_id': self.laptop.id,
                'product_qty': 1,
                'product_uom_id': unit.id,
                'bom_id': bom_laptop.id
            })
        self.new_mo_laptop = new_mo_laptop

    def test_manufacturing_route(self):
        warehouse_1_stock_manager = self.warehouse_1.sudo(self.user_stock_manager)
        manu_rule = self.env['stock.rule'].search([
            ('action', '=', 'manufacture'),
            ('warehouse_id', '=', self.warehouse_1.id)])
        self.assertEqual(self.warehouse_1.manufacture_pull_id, manu_rule)
        manu_route = manu_rule.route_id
        self.assertIn(manu_route, warehouse_1_stock_manager._get_all_routes())
        warehouse_1_stock_manager.write({
            'manufacture_to_resupply': False
        })
        self.assertFalse(self.warehouse_1.manufacture_pull_id.active)
        self.assertFalse(self.warehouse_1.manu_type_id.active)
        self.assertNotIn(manu_route, warehouse_1_stock_manager._get_all_routes())
        warehouse_1_stock_manager.write({
            'manufacture_to_resupply': True
        })
        manu_rule = self.env['stock.rule'].search([
            ('action', '=', 'manufacture'),
            ('warehouse_id', '=', self.warehouse_1.id)])
        self.assertEqual(self.warehouse_1.manufacture_pull_id, manu_rule)
        self.assertTrue(self.warehouse_1.manu_type_id.active)
        self.assertIn(manu_route, warehouse_1_stock_manager._get_all_routes())

    def test_manufacturing_scrap(self):
        """
            Testing to do a scrap of consumed material.
        """

        # Update demo products
        (self.product_4 | self.product_2).write({
            'tracking': 'lot',
        })

        # Update Bill Of Material to remove product with phantom bom.
        self.bom_3.bom_line_ids.filtered(lambda x: x.product_id == self.product_5).unlink()

        # Create Inventory Adjustment For Stick and Stone Tools with lot.
        lot_product_4 = self.env['stock.production.lot'].create({
            'name': '0000000000001',
            'product_id': self.product_4.id,
        })
        lot_product_2 = self.env['stock.production.lot'].create({
            'name': '0000000000002',
            'product_id': self.product_2.id,
        })

        stock_inv_product_4 = self.env['stock.inventory'].create({
            'name': 'Stock Inventory for Stick',
            'filter': 'product',
            'product_id': self.product_4.id,
            'line_ids': [
                (0, 0, {'product_id': self.product_4.id, 'product_uom_id': self.product_4.uom_id.id, 'product_qty': 8, 'prod_lot_id': lot_product_4.id, 'location_id': self.ref('stock.stock_location_14')}),
            ]})

        stock_inv_product_2 = self.env['stock.inventory'].create({
            'name': 'Stock Inventory for Stone Tools',
            'filter': 'product',
            'product_id': self.product_2.id,
            'line_ids': [
                (0, 0, {'product_id': self.product_2.id, 'product_uom_id': self.product_2.uom_id.id, 'product_qty': 12, 'prod_lot_id': lot_product_2.id, 'location_id': self.ref('stock.stock_location_14')})
            ]})
        (stock_inv_product_4 | stock_inv_product_2).action_start()
        stock_inv_product_2.action_validate()
        stock_inv_product_4.action_validate()

        #Create Manufacturing order.
        production_3 = self.env['mrp.production'].create({
            'name': 'MO-Test003',
            'product_id': self.product_6.id,
            'product_qty': 12,
            'bom_id': self.bom_3.id,
            'product_uom_id': self.product_6.uom_id.id,
        })
        production_3.action_assign()

        # Check Manufacturing order's availability.
        self.assertEqual(production_3.availability, 'assigned', "Production order's availability should be Available.")

        location_id = production_3.move_raw_ids.filtered(lambda x: x.state not in ('done', 'cancel')) and production_3.location_src_id.id or production_3.location_dest_id.id,

        # Scrap Product Wood without lot to check assert raise ?.
        scrap_id = self.env['stock.scrap'].with_context(active_model='mrp.production', active_id=production_3.id).create({'product_id': self.product_2.id, 'scrap_qty': 1.0, 'product_uom_id': self.product_2.uom_id.id, 'location_id': location_id, 'production_id': production_3.id})
        with self.assertRaises(except_orm):
            scrap_id.do_scrap()

        # Scrap Product Wood with lot.
        self.env['stock.scrap'].with_context(active_model='mrp.production', active_id=production_3.id).create({'product_id': self.product_2.id, 'scrap_qty': 1.0, 'product_uom_id': self.product_2.uom_id.id, 'location_id': location_id, 'lot_id': lot_product_2.id, 'production_id': production_3.id})

        #Check scrap move is created for this production order.
        #TODO: should check with scrap objects link in between

#        scrap_move = production_3.move_raw_ids.filtered(lambda x: x.product_id == self.product_2 and x.scrapped)
#        self.assertTrue(scrap_move, "There are no any scrap move created for production order.")

    def test_putaway_after_manufacturing_1(self):
        """ This test checks a manufactured product without tracking will go to
        location defined in putaway strategy.
        """
        mo_laptop = self.new_mo_laptop()

        mo_laptop.button_plan()
        workorder = mo_laptop.workorder_ids[0]

        workorder.button_start()
        workorder.record_production()
        mo_laptop.button_mark_done()

        # We check if the laptop go in the depot and not in the stock
        move = mo_laptop.move_finished_ids
        location_dest = move.move_line_ids.location_dest_id
        self.assertEqual(location_dest.id, self.depot_location.id)
        self.assertNotEqual(location_dest.id, self.stock_location.id)

    def test_putaway_after_manufacturing_2(self):
        """ This test checks a tracked manufactured product will go to location
        defined in putaway strategy.
        """
        self.laptop.tracking = 'serial'
        mo_laptop = self.new_mo_laptop()

        mo_laptop.button_plan()
        workorder = mo_laptop.workorder_ids[0]

        workorder.button_start()
        serial = self.env['stock.production.lot'].create({'product_id': self.laptop.id})
        workorder.final_lot_id = serial
        workorder.record_production()
        mo_laptop.button_mark_done()

        # We check if the laptop go in the depot and not in the stock
        move = mo_laptop.move_finished_ids
        location_dest = move.move_line_ids.location_dest_id
        self.assertEqual(location_dest.id, self.depot_location.id)
        self.assertNotEqual(location_dest.id, self.stock_location.id)

    def test_putaway_after_manufacturing_3(self):
        """ This test checks a tracked manufactured product will go to location
        defined in putaway strategy when the production is recorded with
        product.produce wizard.
        """
        self.laptop.tracking = 'serial'
        mo_laptop = self.new_mo_laptop()
        serial = self.env['stock.production.lot'].create({'product_id': self.laptop.id})

        product_produce = self.env['mrp.product.produce'].with_context({
            'active_id': mo_laptop.id,
            'active_ids': [mo_laptop.id],
        }).create({
            'product_qty': 1.0,
            'lot_id': serial.id,
        })
        product_produce.do_produce()
        mo_laptop.button_mark_done()

        # We check if the laptop go in the depot and not in the stock
        move = mo_laptop.move_finished_ids
        location_dest = move.move_line_ids.location_dest_id
        self.assertEqual(location_dest.id, self.depot_location.id)
        self.assertNotEqual(location_dest.id, self.stock_location.id)
