# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import ValidationError, UserError
from odoo.tests.common import Form, SavepointCase


class TestInventory(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestInventory, cls).setUpClass()
        cls.stock_location = cls.env.ref('stock.stock_location_stock')
        cls.pack_location = cls.env.ref('stock.location_pack_zone')
        cls.pack_location.active = True
        cls.customer_location = cls.env.ref('stock.stock_location_customers')
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.product1 = cls.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
            'categ_id': cls.env.ref('product.product_category_all').id,
        })
        cls.product2 = cls.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
            'tracking': 'serial',
            'categ_id': cls.env.ref('product.product_category_all').id,
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
            'location_ids': [(4, self.stock_location.id)],
            'product_ids': [(4, self.product1.id)],
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
            'location_ids': [(4, self.stock_location.id)],
            'product_ids': [(4, self.product2.id)]
        })
        inventory.action_start()
        self.assertEqual(len(inventory.line_ids), 0)

        lot1 = self.env['stock.production.lot'].create({
            'name': 'sn2',
            'product_id': self.product2.id,
            'company_id': self.env.company.id,
        })
        self.env['stock.inventory.line'].create({
            'inventory_id': inventory.id,
            'location_id': self.stock_location.id,
            'product_id': self.product2.id,
            'prod_lot_id': lot1.id,
            'product_qty': 1
        })
        self.assertEqual(len(inventory.line_ids), 1)
        self.assertEqual(inventory.line_ids.theoretical_qty, 0)

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
            'location_ids': [(4, self.stock_location.id)],
            'product_ids': [(4, self.product2.id)]
        })
        inventory.action_start()
        self.assertEqual(len(inventory.line_ids), 0)

        lot1 = self.env['stock.production.lot'].create({
            'name': 'sn2',
            'product_id': self.product2.id,
            'company_id': self.env.company.id,
        })
        self.env['stock.inventory.line'].create({
            'inventory_id': inventory.id,
            'location_id': self.stock_location.id,
            'product_id': self.product2.id,
            'prod_lot_id': lot1.id,
            'product_qty': 2
        })
        self.assertEqual(len(inventory.line_ids), 1)
        self.assertEqual(inventory.line_ids.theoretical_qty, 0)

        with self.assertRaises(ValidationError):
            inventory.action_validate()

    def test_inventory_4(self):
        """ Check that even if a product is tracked by serial number, it's possible to add
        untracked one in an inventory adjustment.
        """
        inventory = self.env['stock.inventory'].create({
            'name': 'remove product1',
            'location_ids': [(4, self.stock_location.id)],
            'product_ids': [(4, self.product2.id)]
        })
        inventory.action_start()
        self.assertEqual(len(inventory.line_ids), 0)
        lot1 = self.env['stock.production.lot'].create({
            'name': 'sn2',
            'product_id': self.product2.id,
            'company_id': self.env.company.id,
        })
        self.env['stock.inventory.line'].create({
            'inventory_id': inventory.id,
            'product_id': self.product2.id,
            'prod_lot_id': lot1.id,
            'product_qty': 1,
            'location_id': self.stock_location.id,
        })
        self.assertEqual(len(inventory.line_ids), 1)
        self.assertEqual(inventory.line_ids.theoretical_qty, 0)

        self.env['stock.inventory.line'].create({
            'inventory_id': inventory.id,
            'product_id': self.product2.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 10,
            'location_id': self.stock_location.id,
        })
        self.assertEqual(len(inventory.line_ids), 2)
        res_dict_for_warning_lot = inventory.action_validate()
        wizard_warning_lot = self.env[(res_dict_for_warning_lot.get('res_model'))].browse(res_dict_for_warning_lot.get('res_id'))
        wizard_warning_lot.action_confirm()

        # check
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location, lot_id=lot1, strict=True), 11.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location, strict=True), 10.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location), 11.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product2, self.stock_location, lot_id=lot1, strict=True).filtered(lambda q: q.lot_id)), 1.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product2, self.stock_location, strict=True)), 1.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product2, self.stock_location)), 2.0)

    def test_inventory_5(self):
        """ Check that assigning an owner does work.
        """
        owner1 = self.env['res.partner'].create({'name': 'test_inventory_5'})

        inventory = self.env['stock.inventory'].create({
            'name': 'remove product1',
            'location_ids': [(4, self.stock_location.id)],
            'product_ids': [(4, self.product1.id)]
        })
        inventory.action_start()
        self.assertEqual(len(inventory.line_ids), 0)

        self.env['stock.inventory.line'].create({
            'inventory_id': inventory.id,
            'product_id': self.product1.id,
            'partner_id': owner1.id,
            'product_qty': 5,
            'location_id': self.stock_location.id,
        })
        self.assertEqual(len(inventory.line_ids), 1)
        self.assertEqual(inventory.line_ids.theoretical_qty, 0)
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
            'location_ids': [(4, self.stock_location.id)],
            'product_ids': [(4, self.product1.id)]
        })
        inventory.action_start()
        self.env['stock.inventory.line'].create({
            'inventory_id': inventory.id,
            'product_id': self.product1.id,
            'product_qty': 10,
            'location_id': self.stock_location.id
        })
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
            'location_ids': [(4, self.pack_location.id)],
            'product_ids': [(4, self.product1.id)],
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
            'location_ids': [(4, self.pack_location.id)],
            'product_ids': [(4, self.product1.id)],
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
            'location_ids': [(4, self.stock_location.id)],
            'product_ids': [(4, self.product1.id)],
        })
        inventory.action_start()
        self.assertEqual(len(inventory.line_ids), 1)
        self.assertEqual(inventory.line_ids.theoretical_qty, 2)

    def test_inventory_8(self):
        """ Check inventory lines product quantity is 0 when inventory is
        started with `prefill_counted_quantity` disable.
        """
        self.env['stock.quant'].create({
            'product_id': self.product1.id,
            'product_uom_id': self.uom_unit.id,
            'location_id': self.stock_location.id,
            'quantity': 7,
            'reserved_quantity': 0,
        })
        inventory_form = Form(self.env['stock.inventory'].with_context(
                default_prefill_counted_quantity='zero',
             ), view='stock.view_inventory_form')
        inventory = inventory_form.save()
        inventory.action_start()
        self.assertNotEqual(len(inventory.line_ids), 0)
        # Checks all inventory lines quantities are correctly set.
        for line in inventory.line_ids:
            self.assertEqual(line.product_qty, 0)
            self.assertNotEqual(line.theoretical_qty, 0)

    def test_inventory_9_cancel_then_start(self):
        """ Checks when we cancel an inventory, then change its locations and/or
        products setup and restart it, it will remove all its lines and restart
        like a new inventory.
        """
        # Creates some records needed for the test...
        product2 = self.env['product.product'].create({
            'name': 'Product B',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
        })
        loc1 = self.env['stock.location'].create({
            'name': 'SafeRoom A',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })
        # Adds some quants.
        self.env['stock.quant'].create({
            'product_id': self.product1.id,
            'product_uom_id': self.uom_unit.id,
            'location_id': loc1.id,
            'quantity': 7,
            'reserved_quantity': 0,
        })
        self.env['stock.quant'].create({
            'product_id': self.product1.id,
            'product_uom_id': self.uom_unit.id,
            'location_id': self.stock_location.id,
            'quantity': 7,
            'reserved_quantity': 0,
        })
        self.env['stock.quant'].create({
            'product_id': product2.id,
            'product_uom_id': self.uom_unit.id,
            'location_id': loc1.id,
            'quantity': 7,
            'reserved_quantity': 0,
        })
        self.env['stock.quant'].create({
            'product_id': product2.id,
            'product_uom_id': self.uom_unit.id,
            'location_id': self.stock_location.id,
            'quantity': 7,
            'reserved_quantity': 0,
        })
        # Creates the inventory and configures if for product1
        inventory_form = Form(self.env['stock.inventory'], view='stock.view_inventory_form')
        inventory_form.product_ids.add(self.product1)
        inventory = inventory_form.save()
        inventory.action_start()
        # Must have two inventory lines about product1.
        self.assertEqual(len(inventory.line_ids), 2)
        for line in inventory.line_ids:
            self.assertEqual(line.product_id.id, self.product1.id)

        # Cancels the inventory and changes for product2 in its setup.
        inventory.action_cancel_draft()
        inventory_form = Form(inventory)
        inventory_form.product_ids.remove(self.product1.id)
        inventory_form.product_ids.add(product2)
        inventory = inventory_form.save()
        inventory.action_start()
        # Must have two inventory lines about product2.
        self.assertEqual(len(inventory.line_ids), 2)
        self.assertEqual(inventory.line_ids.product_id.id, product2.id)

    def test_inventory_prefill_counted_quantity(self):
        """ Checks that inventory lines have a `product_qty` set on zero or
        equals to quantity on hand, depending of the `prefill_counted_quantity`.
        """
        # Set product quantity to 42.
        vals = {
            'product_id': self.product1.id,
            'location_id': self.stock_location.id,
            'quantity': 42,
        }
        self.env['stock.quant'].create(vals)
        # Generate new inventory, its line must have a theoretical
        # quantity to 42 and a counted quantity to 42.
        inventory = self.env['stock.inventory'].create({
            'name': 'Default Qty',
            'location_ids': [(4, self.stock_location.id)],
            'product_ids': [(4, self.product1.id)],
            'prefill_counted_quantity': 'counted',
        })
        inventory.action_start()
        self.assertEqual(len(inventory.line_ids), 1)
        self.assertEqual(inventory.line_ids.theoretical_qty, 42)
        self.assertEqual(inventory.line_ids.product_qty, 42)

        # Generate new inventory, its line must have a theoretical
        # quantity to 42 and a counted quantity to 0.
        inventory = self.env['stock.inventory'].create({
            'name': 'Default Qty',
            'location_ids': [(4, self.stock_location.id)],
            'product_ids': [(4, self.product1.id)],
            'prefill_counted_quantity': 'zero',
        })
        inventory.action_start()
        self.assertEqual(len(inventory.line_ids), 1)
        self.assertEqual(inventory.line_ids.theoretical_qty, 42)
        self.assertEqual(inventory.line_ids.product_qty, 0)

    def test_inventory_outdate_1(self):
        """ Checks that inventory adjustment line is marked as outdated after
        its corresponding quant is modify and its value was correctly updated
        after user refreshed it.
        """
        # Set initial quantity to 7
        vals = {
            'product_id': self.product1.id,
            'product_uom_id': self.uom_unit.id,
            'location_id': self.stock_location.id,
            'quantity': 7,
            'reserved_quantity': 0,
        }
        self.env['stock.quant'].create(vals)

        inventory = self.env['stock.inventory'].create({
            'name': 'product1',
            'location_ids': [(4, self.stock_location.id)],
            'product_ids': [(4, self.product1.id)],
        })
        inventory.action_start()
        # When a inventory line is created, it must not be marked as outdated
        # and its `theoretical_qty` must be equals to quant quantity.
        self.assertEqual(inventory.line_ids.outdated, False)
        self.assertEqual(inventory.line_ids.theoretical_qty, 7)

        # Creates a new quant who'll update the existing one and so set product
        # quantity to 5. Then expects inventory line has been marked as outdated.
        vals = {
            'product_id': self.product1.id,
            'location_id': self.stock_location.id,
            'inventory_quantity': 5,
        }
        self.env['stock.quant'].with_context(inventory_mode=True).create(vals)
        self.assertEqual(inventory.line_ids.outdated, True)
        self.assertEqual(inventory.line_ids.theoretical_qty, 7)
        # Refreshes inventory line and expects quantity was recomputed to 5
        inventory.line_ids.action_refresh_quantity()
        self.assertEqual(inventory.line_ids.outdated, False)
        self.assertEqual(inventory.line_ids.theoretical_qty, 5)

    def test_inventory_outdate_2(self):
        """ Checks that inventory adjustment line is marked as outdated when a
        quant is manually updated and its value is correctly updated when action
        to refresh is called.
        """
        # Set initial quantity to 7
        vals = {
            'product_id': self.product1.id,
            'product_uom_id': self.uom_unit.id,
            'location_id': self.stock_location.id,
            'quantity': 7,
            'reserved_quantity': 0,
        }
        quant = self.env['stock.quant'].create(vals)

        inventory = self.env['stock.inventory'].create({
            'name': 'product1',
            'location_ids': [(4, self.stock_location.id)],
            'product_ids': [(4, self.product1.id)],
        })
        inventory.action_start()
        self.assertEqual(inventory.line_ids.outdated, False)
        self.assertEqual(inventory.line_ids.theoretical_qty, 7)

        # Decreases quant to 3 and expects inventory line is now outdated
        quant.with_context(inventory_mode=True).write({'inventory_quantity': 3})
        self.assertEqual(inventory.line_ids.outdated, True)
        self.assertEqual(inventory.line_ids.theoretical_qty, 7)
        # Refreshes inventory line and expects quantity was recomputed to 3
        inventory.line_ids.action_refresh_quantity()
        self.assertEqual(inventory.line_ids.outdated, False)
        self.assertEqual(inventory.line_ids.theoretical_qty, 3)

    def test_inventory_outdate_3(self):
        """  Checks that outdated inventory adjustment line without difference
        doesn't change quant when validated.
        """
        # Set initial quantity to 10
        vals = {
            'product_id': self.product1.id,
            'product_uom_id': self.uom_unit.id,
            'location_id': self.stock_location.id,
            'quantity': 10,
            'reserved_quantity': 0,
        }
        quant = self.env['stock.quant'].create(vals)

        inventory = self.env['stock.inventory'].create({
            'name': 'product1',
            'location_ids': [(4, self.stock_location.id)],
            'product_ids': [(4, self.product1.id)],
        })
        inventory.action_start()
        self.assertEqual(inventory.line_ids.outdated, False)
        self.assertEqual(inventory.line_ids.theoretical_qty, 10)

        # increases quant to 15 and expects inventory line is now outdated
        quant.with_context(inventory_mode=True).write({'inventory_quantity': 15})
        self.assertEqual(inventory.line_ids.outdated, True)
        # Don't refresh inventory line but valid it, and expect quantity is
        # still equal to 15
        inventory.action_validate()
        self.assertEqual(inventory.line_ids.theoretical_qty, 10)
        self.assertEqual(quant.quantity, 15)

    def test_inventory_outdate_4(self):
        """ Checks that outdated inventory adjustment line with difference
        changes quant when validated.
        """
        # Set initial quantity to 10
        vals = {
            'product_id': self.product1.id,
            'product_uom_id': self.uom_unit.id,
            'location_id': self.stock_location.id,
            'quantity': 10,
            'reserved_quantity': 0,
        }
        quant = self.env['stock.quant'].create(vals)

        inventory = self.env['stock.inventory'].create({
            'name': 'product1',
            'location_ids': [(4, self.stock_location.id)],
            'product_ids': [(4, self.product1.id)],
        })
        inventory.action_start()
        self.assertEqual(inventory.line_ids.outdated, False)
        self.assertEqual(inventory.line_ids.theoretical_qty, 10)

        # increases quant to 15 and expects inventory line is now outdated
        quant.with_context(inventory_mode=True).write({'inventory_quantity': 15})
        self.assertEqual(inventory.line_ids.outdated, True)
        # Don't refresh inventory line but changes its value and valid it, and
        # expects quantity is correctly adapted (15 + inventory line diff)
        inventory.line_ids.product_qty = 12
        inventory.action_validate()
        self.assertEqual(inventory.line_ids.theoretical_qty, 10)
        self.assertEqual(quant.quantity, 17)

    def test_inventory_outdate_5(self):
        """ Checks that inventory adjustment line is marked as outdated when an
        another inventory adjustment line with common product/location is
        validated and its value is updated when action to refresh is called.
        """
        # Set initial quantity to 7
        vals = {
            'product_id': self.product1.id,
            'product_uom_id': self.uom_unit.id,
            'location_id': self.stock_location.id,
            'quantity': 7,
            'reserved_quantity': 0,
        }
        self.env['stock.quant'].create(vals)

        inventory_1 = self.env['stock.inventory'].create({
            'name': 'product1',
            'location_ids': [(4, self.stock_location.id)],
            'product_ids': [(4, self.product1.id)],
        })
        inventory_1.action_start()
        inventory_2 = self.env['stock.inventory'].create({
            'name': 'product1',
            'location_ids': [(4, self.stock_location.id)],
            'product_ids': [(4, self.product1.id)],
        })
        inventory_2.action_start()
        self.assertEqual(inventory_1.line_ids.outdated, False)
        self.assertEqual(inventory_1.line_ids.theoretical_qty, inventory_2.line_ids.theoretical_qty)

        # Set product quantity to 8 in inventory 2 then validates it
        inventory_2.line_ids.product_qty = 8
        inventory_2.action_validate()
        # Expects line of inventory 1 is now marked as outdated
        self.assertEqual(inventory_1.line_ids.outdated, True)
        self.assertEqual(inventory_1.line_ids.theoretical_qty, 7)
        # Refreshes inventory line and expects quantity was recomputed to 8
        inventory_1.line_ids.action_refresh_quantity()
        self.assertEqual(inventory_1.line_ids.theoretical_qty, 8)

    def test_inventory_dont_outdate_1(self):
        """ Checks that inventory adjustment line isn't marked as outdated when
        a not corresponding quant is created.
        """
        # Set initial quantity to 7 and create inventory adjustment for product1
        vals = {
            'product_id': self.product1.id,
            'product_uom_id': self.uom_unit.id,
            'location_id': self.stock_location.id,
            'quantity': 7,
            'reserved_quantity': 0,
        }
        self.env['stock.quant'].create(vals)
        inventory = self.env['stock.inventory'].create({
            'name': 'product1',
            'location_ids': [(4, self.stock_location.id)],
            'product_ids': [(4, self.product1.id)],
        })
        inventory.action_start()
        self.assertEqual(inventory.line_ids.outdated, False)

        # Create quant for product3
        product3 = self.env['product.product'].create({
            'name': 'Product C',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
        })
        vals = {
            'product_id': product3.id,
            'product_uom_id': self.uom_unit.id,
            'location_id': self.stock_location.id,
            'inventory_quantity': 22,
            'reserved_quantity': 0,
        }
        self.env['stock.quant'].create(vals)
        # Expect inventory line is still up to date
        self.assertEqual(inventory.line_ids.outdated, False)

    def test_inventory_dont_outdate_2(self):
        """ Checks that inventory adjustment line isn't marked as outdated when
        an another inventory adjustment line without common product/location is
        validated.
        """
        # Set initial quantity for product1 and product3
        self.env['stock.quant'].create({
            'product_id': self.product1.id,
            'product_uom_id': self.uom_unit.id,
            'location_id': self.stock_location.id,
            'quantity': 7,
            'reserved_quantity': 0,
        })
        product3 = self.env['product.product'].create({
            'name': 'Product C',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
        })
        self.env['stock.quant'].create({
            'product_id': product3.id,
            'product_uom_id': self.uom_unit.id,
            'location_id': self.stock_location.id,
            'quantity': 10,
            'reserved_quantity': 0,
        })

        inventory_1 = self.env['stock.inventory'].create({
            'name': 'product1',
            'location_ids': [(4, self.stock_location.id)],
            'product_ids': [(4, self.product1.id)],
        })
        inventory_1.action_start()
        inventory_2 = self.env['stock.inventory'].create({
            'name': 'product3',
            'location_ids': [(4, self.stock_location.id)],
            'product_ids': [(4, product3.id)],
        })
        inventory_2.action_start()
        self.assertEqual(inventory_1.line_ids.outdated, False)

        # Set product3 quantity to 16 in inventory 2 then validates it
        inventory_2.line_ids.product_qty = 16
        inventory_2.action_validate()
        # Expect line of inventory 1 is still up to date
        self.assertEqual(inventory_1.line_ids.outdated, False)

    def test_inventory_include_exhausted_product(self):
        """ Checks that exhausted product (quant not set or == 0) is added
        to inventory line
        (only for location_ids selected or, if not set, for each main location
        (linked directly to the warehouse) of the current company)
        when the option is active """

        # location_ids SET + product_ids SET
        inventory = self.env['stock.inventory'].create({
            'name': 'loc SET - pro SET',
            'exhausted': True,
            'location_ids': [(4, self.stock_location.id)],
            'product_ids': [(4, self.product1.id)],
        })
        inventory.action_start()

        self.assertEqual(len(inventory.line_ids), 1)
        self.assertEqual(inventory.line_ids.product_id.id, self.product1.id)
        self.assertEqual(inventory.line_ids.theoretical_qty, 0)
        self.assertEqual(inventory.line_ids.location_id.id, self.stock_location.id)

        # location_ids SET + product_ids UNSET
        inventory = self.env['stock.inventory'].create({
            'name': 'loc SET - pro UNSET',
            'exhausted': True,
            'location_ids': [(4, self.stock_location.id)]
        })
        inventory.action_start()
        line_ids_p1 = [l for l in inventory.line_ids if l['product_id']['id'] == self.product1.id]
        line_ids_p2 = [l for l in inventory.line_ids if l['product_id']['id'] == self.product2.id]
        self.assertEqual(len(line_ids_p1), 1)
        self.assertEqual(len(line_ids_p2), 1)
        self.assertEqual(line_ids_p1[0].location_id.id, self.stock_location.id)
        self.assertEqual(line_ids_p2[0].location_id.id, self.stock_location.id)

        # location_ids UNSET + product_ids SET
        warehouse = self.env['stock.warehouse'].create({
            'name': 'Warhouse',
            'code': 'WAR'
        })
        child_loc = self.env['stock.location'].create({
            'name': "ChildLOC",
            'usage': 'internal',
            'location_id': warehouse.lot_stock_id.id
        })

        inventory = self.env['stock.inventory'].create({
            'name': 'loc UNSET - pro SET',
            'exhausted': True,
            'product_ids': [(4, self.product1.id)],
        })
        inventory.action_start()

        line_ids = [l for l in inventory.line_ids if l['location_id']['id'] == warehouse.lot_stock_id.id]
        self.assertEqual(len(line_ids), 1)
        self.assertEqual(line_ids[0].theoretical_qty, 0)
        self.assertEqual(line_ids[0].product_id.id, self.product1.id)

        # Only the main location have a exhausted line
        line_ids = [l for l in inventory.line_ids if l['location_id']['id'] == child_loc.id]
        self.assertEqual(len(line_ids), 0)

        # location_ids UNSET + product_ids UNSET
        inventory = self.env['stock.inventory'].create({
            'name': 'loc UNSET - pro UNSET',
            'exhausted': True
        })
        inventory.action_start()

        # Product1 & Product2 line with warehouse location
        line_ids_p1 = [l for l in inventory.line_ids if l['product_id']['id'] == self.product1.id and l['location_id']['id'] == warehouse.lot_stock_id.id]
        line_ids_p2 = [l for l in inventory.line_ids if l['product_id']['id'] == self.product2.id and l['location_id']['id'] == warehouse.lot_stock_id.id]
        self.assertEqual(len(line_ids_p1), 1)
        self.assertEqual(len(line_ids_p2), 1)
        self.assertEqual(line_ids_p1[0].theoretical_qty, 0)
        self.assertEqual(line_ids_p2[0].theoretical_qty, 0)

        # location_ids SET + product_ids SET but when product in one locations but no the other
        self.env['stock.quant'].create({
            'product_id': self.product1.id,
            'product_uom_id': self.uom_unit.id,
            'location_id': self.stock_location.id,
            'quantity': 10,
            'reserved_quantity': 0,
        })
        inventory = self.env['stock.inventory'].create({
            'name': 'loc SET - pro SET',
            'exhausted': True,
            'location_ids': [(4, self.stock_location.id), (4, warehouse.lot_stock_id.id)],
            'product_ids': [(4, self.product1.id)],
        })
        inventory.action_start()

        # need to have line for product1 for both location, one with quant the other not
        line_ids_loc1 = [l for l in inventory.line_ids if l['location_id']['id'] == self.stock_location.id]
        line_ids_loc2 = [l for l in inventory.line_ids if l['location_id']['id'] == warehouse.lot_stock_id.id]
        self.assertEqual(len(line_ids_loc1), 1)
        self.assertEqual(len(line_ids_loc2), 1)
        self.assertEqual(line_ids_loc1[0].theoretical_qty, 10)
        self.assertEqual(line_ids_loc2[0].theoretical_qty, 0)

    def test_inventory_line_duplicates(self):
        """ Checks that creating duplicated inventory lines
        raises a UserError.
        """
        inventory = self.env['stock.inventory'].create({
            'name': 'Existing Inventory',
            'exhausted': True,
            'location_ids': [(4, self.stock_location.id)],
            'product_ids': [(4, self.product1.id)]
        })
        inventory.action_start()

        dup_vals = [{
            'inventory_id': inventory.id,
            'product_id': self.product1.id,
            'location_id': self.stock_location.id,
        }]

        with self.assertRaises(UserError), self.cr.savepoint():
            self.env['stock.inventory.line'].create(dup_vals)
