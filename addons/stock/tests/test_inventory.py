# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestInventory(TransactionCase):
    def setUp(self):
        super(TestInventory, self).setUp()
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.pack_location = self.env.ref('stock.location_pack_zone')
        self.pack_location.active = True
        self.customer_location = self.env.ref('stock.stock_location_customers')
        self.uom_unit = self.env.ref('uom.product_uom_unit')
        self.product1 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
        })
        self.product2 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
            'tracking': 'serial',
            'categ_id': self.env.ref('product.product_category_all').id,
        })

    def test_inventory_1(self):
        """ Check that making an inventory adjustment to remove all products from stock is working
        as expected.
        """
        # make some stock
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 100)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product1, self.stock_location)), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 100.0)

        # remove them with an inventory adjustment
        inventory = self.env['stock.inventory'].create({
            'name': 'remove product1',
            'filter': 'product',
            'location_id': self.stock_location.id,
            'product_id': self.product1.id,
        })
        inventory.action_start()
        self.assertEqual(len(inventory.line_ids), 1)
        self.assertEqual(inventory.line_ids.theoretical_qty, 100)
        inventory.line_ids.product_qty = 0  # Put the quantity back to 0
        inventory.action_validate()

        # check
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0.0)
        self.assertEqual(sum(self.env['stock.quant']._gather(self.product1, self.stock_location).mapped('quantity')), 0.0)

    def test_inventory_2(self):
        """ Check that adding a tracked product through an inventory adjustment work as expected.
        """
        inventory = self.env['stock.inventory'].create({
            'name': 'remove product1',
            'filter': 'product',
            'location_id': self.stock_location.id,
            'product_id': self.product2.id,
            'exhausted': True,  # should be set by an onchange
        })
        inventory.action_start()
        self.assertEqual(len(inventory.line_ids), 1)
        self.assertEqual(inventory.line_ids.theoretical_qty, 0)

        lot1 = self.env['stock.production.lot'].create({
            'name': 'sn2',
            'product_id': self.product2.id,
        })

        inventory.line_ids.prod_lot_id = lot1
        inventory.line_ids.product_qty = 1

        inventory.action_validate()

        # check
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location, lot_id=lot1), 1.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product2, self.stock_location, lot_id=lot1)), 1.0)
        self.assertEqual(lot1.product_qty, 1.0)

    def test_inventory_3(self):
        """ Check that it's not posisble to have multiple products with a serial number through an
        inventory adjustment
        """
        inventory = self.env['stock.inventory'].create({
            'name': 'remove product1',
            'filter': 'product',
            'location_id': self.stock_location.id,
            'product_id': self.product2.id,
            'exhausted': True,  # should be set by an onchange
        })
        inventory.action_start()
        self.assertEqual(len(inventory.line_ids), 1)
        self.assertEqual(inventory.line_ids.theoretical_qty, 0)

        lot1 = self.env['stock.production.lot'].create({
            'name': 'sn2',
            'product_id': self.product2.id,
        })

        inventory.line_ids.prod_lot_id = lot1
        inventory.line_ids.product_qty = 2

        with self.assertRaises(ValidationError):
            inventory.action_validate()

    def test_inventory_4(self):
        """ Check that even if a product is tracked by serial number, it's possible to add
        untracked one in an inventory adjustment.
        """
        inventory = self.env['stock.inventory'].create({
            'name': 'remove product1',
            'filter': 'product',
            'location_id': self.stock_location.id,
            'product_id': self.product2.id,
            'exhausted': True,  # should be set by an onchange
        })
        inventory.action_start()
        self.assertEqual(len(inventory.line_ids), 1)
        self.assertEqual(inventory.line_ids.theoretical_qty, 0)

        lot1 = self.env['stock.production.lot'].create({
            'name': 'sn2',
            'product_id': self.product2.id,
        })

        inventory.line_ids.prod_lot_id = lot1
        inventory.line_ids.product_qty = 1

        self.env['stock.inventory.line'].create({
            'inventory_id': inventory.id,
            'product_id': self.product2.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 10,
            'location_id': self.stock_location.id,
        })
        res_dict_for_warning_lot = inventory.action_validate()
        wizard_warning_lot = self.env[(res_dict_for_warning_lot.get('res_model'))].browse(res_dict_for_warning_lot.get('res_id'))
        wizard_warning_lot.action_confirm()

        # check
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location, lot_id=lot1, strict=True), 1.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location, strict=True), 10.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location), 11.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product2, self.stock_location, lot_id=lot1, strict=True)), 1.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product2, self.stock_location, strict=True)), 1.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product2, self.stock_location)), 2.0)

    def test_inventory_5(self):
        """ Check that assigning an owner does work.
        """
        owner1 = self.env['res.partner'].create({'name': 'test_inventory_5'})

        inventory = self.env['stock.inventory'].create({
            'name': 'remove product1',
            'filter': 'product',
            'location_id': self.stock_location.id,
            'product_id': self.product1.id,
            'exhausted': True,
        })
        inventory.action_start()
        self.assertEqual(len(inventory.line_ids), 1)
        self.assertEqual(inventory.line_ids.theoretical_qty, 0)
        inventory.line_ids.partner_id = owner1
        inventory.line_ids.product_qty = 5
        inventory.action_validate()

        quant = self.env['stock.quant']._gather(self.product1, self.stock_location)
        self.assertEqual(len(quant), 1)
        self.assertEqual(quant.quantity, 5)
        self.assertEqual(quant.owner_id.id, owner1.id)

    def test_inventory_6(self):
        """ Test that for chained moves, making an inventory adjustment to reduce a quantity that
        has been reserved correctly free the reservation. After that, add products in stock and check
        that they're used if the user encodes more than what's available through the chain
        """
        # add 10 products in stock
        inventory = self.env['stock.inventory'].create({
            'name': 'add 10 products 1',
            'filter': 'product',
            'location_id': self.stock_location.id,
            'product_id': self.product1.id,
            'exhausted': True,  # should be set by an onchange
        })
        inventory.action_start()
        inventory.line_ids.product_qty = 10
        inventory.action_validate()
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 10.0)

        # Make a chain of two moves, validate the first and check that 10 products are reserved
        # in the second one.
        move_stock_pack = self.env['stock.move'].create({
            'name': 'test_link_2_1',
            'location_id': self.stock_location.id,
            'location_dest_id': self.pack_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        move_pack_cust = self.env['stock.move'].create({
            'name': 'test_link_2_2',
            'location_id': self.pack_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 10.0,
        })
        move_stock_pack.write({'move_dest_ids': [(4, move_pack_cust.id, 0)]})
        move_pack_cust.write({'move_orig_ids': [(4, move_stock_pack.id, 0)]})
        (move_stock_pack + move_pack_cust)._action_confirm()
        move_stock_pack._action_assign()
        self.assertEqual(move_stock_pack.state, 'assigned')
        move_stock_pack.move_line_ids.qty_done = 10
        move_stock_pack._action_done()
        self.assertEqual(move_stock_pack.state, 'done')
        self.assertEqual(move_pack_cust.state, 'assigned')
        self.assertEqual(self.env['stock.quant']._gather(self.product1, self.pack_location).quantity, 10.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.pack_location), 0.0)

        # Make and inventory adjustment and remove two products from the pack location. This should
        # free the reservation of the second move.
        inventory = self.env['stock.inventory'].create({
            'name': 'remove 2 products 1',
            'filter': 'product',
            'location_id': self.pack_location.id,
            'product_id': self.product1.id,
        })
        inventory.action_start()
        inventory.line_ids.product_qty = 8
        inventory.action_validate()
        self.assertEqual(self.env['stock.quant']._gather(self.product1, self.pack_location).quantity, 8.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.pack_location), 0)
        self.assertEqual(move_pack_cust.state, 'partially_available')
        self.assertEqual(move_pack_cust.reserved_availability, 8)

        # If the user tries to assign again, only 8 products are available and thus the reservation
        # state should not change.
        move_pack_cust._action_assign()
        self.assertEqual(move_pack_cust.state, 'partially_available')
        self.assertEqual(move_pack_cust.reserved_availability, 8)

        # Make a new inventory adjustment and bring two now products.
        inventory = self.env['stock.inventory'].create({
            'name': 'remove 2 products 1',
            'filter': 'product',
            'location_id': self.pack_location.id,
            'product_id': self.product1.id,
        })
        inventory.action_start()
        inventory.line_ids.product_qty = 10
        inventory.action_validate()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.pack_location), 2)

        # Nothing should have changed for our pack move
        self.assertEqual(move_pack_cust.state, 'partially_available')
        self.assertEqual(move_pack_cust.reserved_availability, 8)

        # Running _action_assign will now find the new available quantity. Indeed, as the products
        # are not discernabl (not lot/pack/owner), even if the new available quantity is not directly
        # brought by the chain, the system fill take them into account.
        move_pack_cust._action_assign()
        self.assertEqual(move_pack_cust.state, 'assigned')

        # move all the things
        move_pack_cust.move_line_ids.qty_done = 10
        move_stock_pack._action_done()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.pack_location), 0)

    def test_inventory_7(self):
        """ Check that duplicated quants create a single inventory line.
        """
        owner1 = self.env['res.partner'].create({'name': 'test_inventory_7'})
        vals = {
            'product_id': self.product1.id,
            'product_uom_id': self.uom_unit.id,
            'owner_id': owner1.id,
            'location_id': self.stock_location.id,
            'quantity': 1,
            'reserved_quantity': 0,
        }
        self.env['stock.quant'].create(vals)
        self.env['stock.quant'].create(vals)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product1, self.stock_location)), 2.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 2.0)
        
        inventory = self.env['stock.inventory'].create({
            'name': 'product1',
            'filter': 'product',
            'location_id': self.stock_location.id,
            'product_id': self.product1.id,
        })
        inventory.action_start()
        self.assertEqual(len(inventory.line_ids), 1)
        self.assertEqual(inventory.line_ids.theoretical_qty, 2)

