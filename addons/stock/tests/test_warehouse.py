# -*- coding: utf-8 -*-

from odoo.addons.stock.tests.common2 import TestStockCommon


class TestInventory(TestStockCommon):

    def test_inventory_product(self):
        # TDE NOTE: replaces test/inventory.yml present until saas-10
        inventory = self.env['stock.inventory'].sudo(self.user_stock_manager).create({
            'name': 'Starting for product_1',
            'filter': 'product',
            'location_id': self.warehouse_1.lot_stock_id.id,
            'product_id': self.product_1.id,
        })
        inventory.prepare_inventory()

        # As done in common.py, there is already an inventory line existing
        self.assertEqual(len(inventory.line_ids), 1)
        self.assertEqual(inventory.line_ids.theoretical_qty, 50.0)
        self.assertEqual(inventory.line_ids.product_id, self.product_1)
        self.assertEqual(inventory.line_ids.product_uom_id, self.product_1.uom_id)

        # Update the line, set to 35
        inventory.line_ids.write({'product_qty': 35.0})
        inventory.action_done()

        # Check related move and quants
        self.assertIn(inventory.name, inventory.move_ids.name)
        self.assertEqual(inventory.move_ids.product_qty, 15.0)
        self.assertEqual(inventory.move_ids.location_id, self.warehouse_1.lot_stock_id)
        self.assertEqual(inventory.move_ids.location_dest_id, self.env.ref('stock.location_inventory'))  # Inventory loss
        self.assertEqual(inventory.move_ids.state, 'done')
        self.assertEqual(inventory.move_ids.quant_ids.location_id, self.env.ref('stock.location_inventory'))  # Inventory loss
        self.assertEqual(inventory.move_ids.quant_ids.qty, 15.0)
        self.assertEqual(inventory.move_ids.quant_ids.history_ids[0].product_qty, 50.0)

        # Check quantity of product in various locations: current, its parent, brother and other
        self.assertEqual(self.product_1.with_context(location=self.warehouse_1.lot_stock_id.id).qty_available, 35.0)
        self.assertEqual(self.product_1.with_context(location=self.warehouse_1.lot_stock_id.location_id.id).qty_available, 35.0)
        self.assertEqual(self.product_1.with_context(location=self.warehouse_1.view_location_id.id).qty_available, 35.0)
        self.assertEqual(self.product_1.with_context(location=self.warehouse_1.wh_input_stock_loc_id.id).qty_available, 0.0)
        self.assertEqual(self.product_1.with_context(location=self.env.ref('stock.stock_location_stock').id).qty_available, 0.0)

    def test_inventory_wizard(self):
        # Check inventory performed in setup was effectivley performed
        self.assertEqual(self.product_1.virtual_available, 50.0)
        self.assertEqual(self.product_1.qty_available, 50.0)

        # Check inventory obj details (1 inventory with 1 line, because 1 product change)
        inventory = self.env['stock.inventory'].search([('id', 'not in', self.existing_inventories.ids)])
        self.assertEqual(len(inventory), 1)
        self.assertIn('INV: %s' % self.product_1.name, inventory.name)
        self.assertEqual(len(inventory.line_ids), 1)
        self.assertEqual(inventory.line_ids.product_id, self.product_1)
        self.assertEqual(inventory.line_ids.product_qty, 50.0)

        # Check associated quants: 1 quant for the product and the quantity
        quant = self.env['stock.quant'].search([('id', 'not in', self.existing_quants.ids)])
        self.assertEqual(len(quant), 1)
        # print quant.name, quant.product_id, quant.location_id
        # TDE TODO: expand this test

    def test_basic_move(self):
        # TDE NOTE: replaces test/move.yml present until saas-10, including onchanges
        Move = self.env['stock.move'].sudo(self.user_stock_manager)
        product = self.product_3.sudo(self.user_stock_manager)

        # simulate create + onchange
        customer_move = self._create_move(product, self.warehouse_1.lot_stock_id, self.env.ref('stock.stock_location_customers'), product_uom_qty=5)

        # test move values
        self.assertEqual(customer_move.product_uom, product.uom_id)
        self.assertEqual(customer_move.location_id, self.warehouse_1.lot_stock_id)
        self.assertEqual(customer_move.location_dest_id, self.env.ref('stock.stock_location_customers'))

        # confirm move, check quantity on hand and virtually available, without location context
        customer_move.action_confirm()
        self.assertEqual(product.qty_available, 0.0)
        self.assertEqual(product.virtual_available, -5.0)

        customer_move.action_done()
        self.assertEqual(product.qty_available, -5.0)
        self.assertEqual(product.with_context(location=self.env.ref('stock.stock_location_customers').id).qty_available, 5.0)

        # compensate negative quants by receiving products from supplier
        receive_move = self._create_move(product, self.env.ref('stock.stock_location_suppliers'), self.warehouse_1.lot_stock_id, product_uom_qty=15)

        receive_move.action_confirm()
        receive_move.action_done()

        self.assertEqual(product.qty_available, 10.0)
        self.assertEqual(product.virtual_available, 10.0)

        # new move towards customer
        customer_move_2 = self._create_move(product, self.warehouse_1.lot_stock_id, self.env.ref('stock.stock_location_customers'), product_uom_qty=2)

        customer_move_2.action_confirm()
        self.assertEqual(product.qty_available, 10.0)
        self.assertEqual(product.virtual_available, 8.0)

        customer_move_2.action_done()
        self.assertEqual(product.qty_available, 8.0)
        self.assertEqual(product.with_context(location=self.env.ref('stock.stock_location_customers').id).qty_available, 7.0)


class TestResupply(TestStockCommon):
    def setUp(self):
        super(TestResupply, self).setUp()

        self.warehouse_2 = self.env['stock.warehouse'].create({
            'name': 'Small Warehouse',
            'code': 'SWH',
            'default_resupply_wh_id': self.warehouse_1.id,
            'resupply_wh_ids': [(6, 0, [self.warehouse_1.id])]
        })

        # minimum stock rule for test product on this warehouse
        self.env['stock.warehouse.orderpoint'].create({
            'warehouse_id': self.warehouse_2.id,
            'location_id': self.warehouse_2.lot_stock_id.id,
            'product_id': self.product_1.id,
            'product_min_qty': 10,
            'product_max_qty': 100,
            'product_uom': self.uom_unit.id,
        })

    def test_resupply_from_wh(self):
        # TDE NOTE: replaces tests/test_resupply.py, present until saas-10
        OrderScheduler = self.env['procurement.order']
        OrderScheduler.run_scheduler()
        # we generated 2 procurements for product A: one on small wh and the other one on the transit location
        procs = OrderScheduler.search([('product_id', '=', self.product_1.id)])
        self.assertEqual(len(procs), 2)

        proc1 = procs.filtered(lambda order: order.warehouse_id == self.warehouse_2)
        self.assertEqual(proc1.state, 'running')

        proc2 = procs.filtered(lambda order: order.warehouse_id == self.warehouse_1)
        self.assertEqual(proc2.location_id.usage, 'transit')
        self.assertNotEqual(proc2.state, 'exception')

        proc2.run()
        self.assertEqual(proc2.state, 'running')
        self.assertTrue(proc2.rule_id)
