# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import Form, TransactionCase


class TestInventory(TransactionCase):
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
            'is_storable': True,
            'categ_id': cls.env.ref('product.product_category_all').id,
        })
        cls.product2 = cls.env['product.product'].create({
            'name': 'Product A',
            'is_storable': True,
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
        inventory_quant = self.env['stock.quant'].search([
            ('location_id', '=', self.stock_location.id),
            ('product_id', '=', self.product1.id),
        ])

        self.assertEqual(len(inventory_quant), 1)
        self.assertEqual(inventory_quant.quantity, 100)
        self.assertEqual(inventory_quant.inventory_quantity, 0)

        inventory_quant.action_apply_inventory()

        # check
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 0.0)
        self.assertEqual(sum(self.env['stock.quant']._gather(self.product1, self.stock_location).mapped('quantity')), 0.0)

    def test_inventory_2(self):
        """ Check that adding a tracked product through an inventory adjustment works as expected.
        """
        inventory_quant = self.env['stock.quant'].search([
            ('location_id', '=', self.stock_location.id),
            ('product_id', '=', self.product2.id)
        ])

        self.assertEqual(len(inventory_quant), 0)

        lot1 = self.env['stock.lot'].create({
            'name': 'sn2',
            'product_id': self.product2.id,
        })
        inventory_quant = self.env['stock.quant'].create({
            'location_id': self.stock_location.id,
            'product_id': self.product2.id,
            'lot_id': lot1.id,
            'inventory_quantity': 1
        })

        self.assertEqual(inventory_quant.quantity, 0)
        self.assertEqual(inventory_quant.inventory_diff_quantity, 1)

        inventory_quant.action_apply_inventory()

        # check
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location, lot_id=lot1), 1.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product2, self.stock_location, lot_id=lot1)), 1.0)
        self.assertEqual(lot1.product_qty, 1.0)

    def test_inventory_3(self):
        """ Check that it's not possible to have multiple products with the same serial number through an
        inventory adjustment
        """
        inventory_quant = self.env['stock.quant'].search([
            ('location_id', '=', self.stock_location.id),
            ('product_id', '=', self.product2.id)
        ])
        self.assertEqual(len(inventory_quant), 0)

        lot1 = self.env['stock.lot'].create({
            'name': 'sn2',
            'product_id': self.product2.id,
        })
        inventory_quant = self.env['stock.quant'].create({
            'location_id': self.stock_location.id,
            'product_id': self.product2.id,
            'lot_id': lot1.id,
            'inventory_quantity': 2
        })

        self.assertEqual(len(inventory_quant), 1)
        self.assertEqual(inventory_quant.quantity, 0)

        with self.assertRaises(ValidationError):
            inventory_quant.action_apply_inventory()

    def test_inventory_4(self):
        """ Check that even if a product is tracked by serial number, it's possible to add an
        untracked one in an inventory adjustment.
        """
        quant_domain = [
            ('location_id', '=', self.stock_location.id),
            ('product_id', '=', self.product2.id)
        ]
        inventory_quants = self.env['stock.quant'].search(quant_domain)
        self.assertEqual(len(inventory_quants), 0)
        lot1 = self.env['stock.lot'].create({
            'name': 'sn2',
            'product_id': self.product2.id,
        })
        self.env['stock.quant'].create({
            'location_id': self.stock_location.id,
            'product_id': self.product2.id,
            'lot_id': lot1.id,
            'inventory_quantity': 1
        })

        inventory_quants = self.env['stock.quant'].search(quant_domain)
        self.assertEqual(len(inventory_quants), 1)
        self.assertEqual(inventory_quants.quantity, 0)

        self.env['stock.quant'].create({
            'location_id': self.stock_location.id,
            'product_id': self.product2.id,
            'inventory_quantity': 10
        })
        inventory_quants = self.env['stock.quant'].search(quant_domain)
        self.assertEqual(len(inventory_quants), 2)
        stock_confirmation_action = inventory_quants.action_apply_inventory()
        stock_confirmation_wizard_form = Form(
            self.env['stock.track.confirmation'].with_context(
                **stock_confirmation_action['context'])
        )

        stock_confirmation_wizard = stock_confirmation_wizard_form.save()
        stock_confirmation_wizard.action_confirm()

        # check
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location, lot_id=lot1, strict=False), 11.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location, strict=True), 10.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product2, self.stock_location), 11.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product2, self.stock_location, lot_id=lot1, strict=True).filtered(lambda q: q.lot_id)), 1.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product2, self.stock_location, strict=True)), 1.0)
        self.assertEqual(len(self.env['stock.quant']._gather(self.product2, self.stock_location)), 2.0)

    def test_inventory_5(self):
        """ Check that assigning an owner works.
        """
        owner1 = self.env['res.partner'].create({'name': 'test_inventory_5'})

        inventory_quant = self.env['stock.quant'].create({
            'location_id': self.stock_location.id,
            'product_id': self.product1.id,
            'inventory_quantity': 5,
            'owner_id': owner1.id,
        })

        self.assertEqual(inventory_quant.quantity, 0)
        inventory_quant.action_apply_inventory()

        quant = self.env['stock.quant']._gather(self.product1, self.stock_location)
        self.assertEqual(len(quant), 1)
        self.assertEqual(quant.quantity, 5)
        self.assertEqual(quant.owner_id.id, owner1.id)

    def test_inventory_6(self):
        """ Test that for chained moves, making an inventory adjustment to reduce a quantity that
        has been reserved correctly frees the reservation. After that, add products to stock and check
        that they're used if the user encodes more than what's available through the chain
        """
        # add 10 products to stock
        inventory_quant = self.env['stock.quant'].create({
            'location_id': self.stock_location.id,
            'product_id': self.product1.id,
            'inventory_quantity': 10,
        })
        inventory_quant.action_apply_inventory()
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
        move_stock_pack.move_line_ids.quantity = 10
        move_stock_pack.picked = True
        move_stock_pack._action_done()
        self.assertEqual(move_stock_pack.state, 'done')
        self.assertEqual(move_pack_cust.state, 'assigned')
        self.assertEqual(self.env['stock.quant']._gather(self.product1, self.pack_location).quantity, 10.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.pack_location), 0.0)

        # Make an inventory adjustment and remove two products from the pack location. This should
        # free the reservation of the second move.
        inventory_quant = self.env['stock.quant'].search([
            ('location_id', '=', self.pack_location.id),
            ('product_id', '=', self.product1.id)
        ])
        inventory_quant.inventory_quantity = 8
        inventory_quant.action_apply_inventory()
        self.assertEqual(self.env['stock.quant']._gather(self.product1, self.pack_location).quantity, 8.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.pack_location), 0)
        self.assertEqual(move_pack_cust.state, 'partially_available')
        self.assertEqual(move_pack_cust.quantity, 8)

        # If the user tries to assign again, only 8 products are available and thus the reservation
        # state should not change.
        move_pack_cust._action_assign()
        self.assertEqual(move_pack_cust.state, 'partially_available')
        self.assertEqual(move_pack_cust.quantity, 8)

        # Make a new inventory adjustment and add two new products.
        inventory_quant = self.env['stock.quant'].search([
            ('location_id', '=', self.pack_location.id),
            ('product_id', '=', self.product1.id)
        ])
        inventory_quant.inventory_quantity = 10
        inventory_quant.action_apply_inventory()

        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.pack_location), 2)

        # Nothing should have changed for our pack move
        self.assertEqual(move_pack_cust.state, 'partially_available')
        self.assertEqual(move_pack_cust.quantity, 8)

        # Running _action_assign will now find the new available quantity. Since the products
        # are not differentiated (no lot/pack/owner), even if the new available quantity is not directly
        # brought by the chain, the system will take them into account.
        move_pack_cust._action_assign()
        self.assertEqual(move_pack_cust.state, 'assigned')

        # move all the things
        move_pack_cust.move_line_ids.quantity = 10
        move_pack_cust.picked = True
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
        }
        self.env['stock.quant'].create(vals)
        self.env['stock.quant'].create(dict(**vals, inventory_quantity=1))
        self.assertEqual(len(self.env['stock.quant']._gather(self.product1, self.stock_location)), 2.0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(self.product1, self.stock_location), 2.0)
        self.env['stock.quant']._quant_tasks()
        inventory_quant = self.env['stock.quant'].search([
            ('location_id', '=', self.stock_location.id),
            ('product_id', '=', self.product1.id)
        ])
        self.assertEqual(len(inventory_quant), 1)
        self.assertEqual(inventory_quant.inventory_quantity, 1)
        self.assertEqual(inventory_quant.quantity, 2)

    def test_inventory_counted_quantity(self):
        """ Checks that inventory quants have a `inventory quantity` set to zero
        after an adjustment.
        """
        # Set product quantity to 42.
        inventory_quant = self.env['stock.quant'].create({
            'product_id': self.product1.id,
            'location_id': self.stock_location.id,
            'inventory_quantity': 42,
        })
        # Applies the change, the quant must have a quantity of 42 and a inventory quantity to 0.
        inventory_quant.action_apply_inventory()
        self.assertEqual(len(inventory_quant), 1)
        self.assertEqual(inventory_quant.inventory_quantity, 0)
        self.assertEqual(inventory_quant.quantity, 42)

        # Checks we can write on `inventory_quantity_set` even if we write on
        # `inventory_quantity` at the same time.
        self.assertEqual(inventory_quant.inventory_quantity_set, False)
        inventory_quant.write({'inventory_quantity': 5})
        self.assertEqual(inventory_quant.inventory_quantity_set, True)
        inventory_quant.write({
            'inventory_quantity': 12,
            'inventory_quantity_set': False,
        })
        self.assertEqual(inventory_quant.inventory_quantity_set, False)

    def test_inventory_request_count_quantity(self):
        """ Ensures when a request to count a quant for tracked product is done, other quants for
        the same product in the same location are also marked as to count."""
        # Config: enable tracking and multilocations.
        self.env.user.groups_id = [
            Command.link(self.env.ref('stock.group_production_lot').id),
            Command.link(self.env.ref('stock.group_stock_multi_locations').id)
        ]
        # Creates other locations.
        stock_location_2 = self.env['stock.location'].create({
            'name': 'stock 2',
            'location_id': self.stock_location.location_id.id,
        })
        sub_location = self.env['stock.location'].create({
            'name': 'stock 2',
            'location_id': self.stock_location.id,
        })
        # Creates some quants for product2 (tracked by serail numbers.)
        serial_numbers = self.env['stock.lot'].create([{
            'product_id': self.product2.id,
            'name': f'sn{i + 1}'
        } for i in range(4)])
        quants = self.env['stock.quant'].create([
            {
                'location_id': self.stock_location.id,
                'product_id': self.product2.id,
                'lot_id': serial_numbers[0].id,
                'inventory_quantity': 1,
            },
            {
                'location_id': self.stock_location.id,
                'product_id': self.product2.id,
                'lot_id': serial_numbers[1].id,
                'inventory_quantity': 1,
            },
            {
                'location_id': sub_location.id,
                'product_id': self.product2.id,
                'lot_id': serial_numbers[2].id,
                'inventory_quantity': 1,
            },
            {
                'location_id': stock_location_2.id,
                'product_id': self.product2.id,
                'lot_id': serial_numbers[3].id,
                'inventory_quantity': 1,
            }
        ])
        # Request count for 1 quant => The other quant in the same location
        # should also be updated, other quants shouldn't
        request_wizard = self.env['stock.request.count'].create({
            'quant_ids': quants[1].ids,
            'set_count': 'empty',
            'user_id': self.env.user.id,
        })
        request_wizard.action_request_count()
        self.assertRecordValues(quants, [
            {'lot_id': serial_numbers[0].id, 'user_id': self.env.user.id, 'location_id': self.stock_location.id},
            {'lot_id': serial_numbers[1].id, 'user_id': self.env.user.id, 'location_id': self.stock_location.id},
            {'lot_id': serial_numbers[2].id, 'user_id': False, 'location_id': sub_location.id},
            {'lot_id': serial_numbers[3].id, 'user_id': False, 'location_id': stock_location_2.id},
        ])

    def test_inventory_outdate_1(self):
        """ Checks that applying an inventory adjustment that is outdated due to
        its corresponding quant being modified after its inventory quantity is set
        opens a wizard. The wizard should warn about the conflict and its value should be
        corrected after user confirms the inventory quantity.
        """
        # Set initial quantity to 7
        self.env['stock.quant']._update_available_quantity(self.product1, self.stock_location, 7)
        inventory_quant = self.env['stock.quant'].search([
            ('location_id', '=', self.stock_location.id),
            ('product_id', '=', self.product1.id)
        ])
        # When a quant is created, it must not be marked as outdated
        # and its `inventory_quantity` must be equal to zero.
        self.assertEqual(inventory_quant.inventory_quantity, 0)

        inventory_quant.inventory_quantity = 5
        self.assertEqual(inventory_quant.inventory_diff_quantity, -2)

        # Deliver 3 units
        move_out = self.env['stock.move'].create({
            'name': 'Outgoing move of 3 units',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 3.0,
        })
        move_out._action_confirm()
        move_out._action_assign()
        move_out.move_line_ids.quantity = 3
        move_out.picked = True
        move_out._action_done()

        # Ensure that diff didn't change.
        self.assertEqual(inventory_quant.inventory_diff_quantity, -2)
        self.assertEqual(inventory_quant.inventory_quantity, 5)
        self.assertEqual(inventory_quant.quantity, 4)

        conflict_wizard_values = inventory_quant.action_apply_inventory()
        conflict_wizard_form = Form(self.env['stock.inventory.conflict'].with_context(conflict_wizard_values['context']))
        conflict_wizard = conflict_wizard_form.save()
        conflict_wizard.quant_to_fix_ids.inventory_quantity = 5
        conflict_wizard.action_keep_counted_quantity()
        self.assertEqual(inventory_quant.inventory_diff_quantity, 0)
        self.assertEqual(inventory_quant.inventory_quantity, 0)
        self.assertEqual(inventory_quant.quantity, 5)

    def test_inventory_outdate_2(self):
        """ Checks that an outdated inventory adjustment auto-corrects when
        changing its inventory quantity after its corresponding quant has been modified.
        """
        # Set initial quantity to 7
        vals = {
            'product_id': self.product1.id,
            'product_uom_id': self.uom_unit.id,
            'location_id': self.stock_location.id,
            'quantity': 7,
            'inventory_quantity': 7
        }
        quant = self.env['stock.quant'].create(vals)

        # Decrease quant to 3 and inventory line is now outdated
        move_out = self.env['stock.move'].create({
            'name': 'Outgoing move of 3 units',
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'product_id': self.product1.id,
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 4.0,
        })
        quant.invalidate_recordset()
        move_out._action_confirm()
        move_out._action_assign()
        move_out.move_line_ids.quantity = 4
        move_out.picked = True
        move_out._action_done()

        self.assertEqual(quant.inventory_quantity, 7)
        self.assertEqual(quant.inventory_diff_quantity, 0)
        # Refresh inventory line and quantity will recompute to 3
        quant.inventory_quantity = 3
        self.assertEqual(quant.inventory_quantity, 3)
        self.assertEqual(quant.inventory_diff_quantity, 0)

    def test_inventory_outdate_3(self):
        """  Checks that an inventory adjustment line without a difference
        doesn't change quant when validated.
        """
        # Set initial quantity to 10
        vals = {
            'product_id': self.product1.id,
            'product_uom_id': self.uom_unit.id,
            'location_id': self.stock_location.id,
            'quantity': 10,
        }
        quant = self.env['stock.quant'].create(vals)

        quant.inventory_quantity = 10
        quant.action_apply_inventory()
        self.assertEqual(quant.quantity, 10)
        self.assertEqual(quant.inventory_quantity, 0)

    def test_inventory_dont_outdate_1(self):
        """ Checks that inventory adjustment line isn't marked as outdated when
        a non-corresponding quant is created.
        """
        # Set initial quantity to 7 and create inventory adjustment for product1
        inventory_quant = self.env['stock.quant'].create({
            'product_id': self.product1.id,
            'product_uom_id': self.uom_unit.id,
            'location_id': self.stock_location.id,
            'quantity': 7,
            'inventory_quantity': 5
        })

        # Create quant for product3
        product3 = self.env['product.product'].create({
            'name': 'Product C',
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_all').id,
        })
        self.env['stock.quant'].create({
            'product_id': product3.id,
            'product_uom_id': self.uom_unit.id,
            'location_id': self.stock_location.id,
            'inventory_quantity': 22,
            'reserved_quantity': 0,
        })
        inventory_quant.action_apply_inventory()
        # Expect action apply do not return a wizard
        self.assertEqual(inventory_quant.quantity, 5)

    def test_cyclic_inventory(self):
        """ Check that locations with and without cyclic inventory set has its inventory
        dates auto-generate and apply relevant dates.
        """
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id)]})
        now = datetime.now()
        today = now.date()

        new_loc = self.env['stock.location'].create({
            'name': 'New Cyclic Inv Location',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })

        existing_loc2 = self.env['stock.location'].create({
            'name': 'Pre-existing Cyclic Inv Location',
            'usage': 'internal',
            'location_id': self.stock_location.id,
            'last_inventory_date': now - timedelta(days=5),
        })

        no_cyclic_loc = self.env['stock.location'].create({
            'name': 'No Cyclic Inv Location',
            'usage': 'internal',
            'location_id': self.stock_location.id,
        })
        no_cyclic_loc.company_id.write({'annual_inventory_day': str(today.day), 'annual_inventory_month': str(today.month)})
        new_loc_form = Form(new_loc)
        new_loc_form.cyclic_inventory_frequency = 2
        new_loc = new_loc_form.save()

        # check next_inventory_date is correctly calculated
        existing_loc2_form = Form(existing_loc2)
        existing_loc2_form.cyclic_inventory_frequency = 2
        existing_loc2 = existing_loc2_form.save()

        # next_inventory_date = today + cyclic_inventory_frequency
        self.assertEqual(new_loc.next_inventory_date, today + timedelta(days=2))
        # previous inventory done + cyclic_inventory_frequency < today => next_inventory_date = tomorrow
        self.assertEqual(existing_loc2.next_inventory_date, today + timedelta(days=1))
        # check that cyclic inventories are correctly autogenerated
        self.env['stock.quant']._update_available_quantity(self.product1, new_loc, 5)
        self.env['stock.quant']._update_available_quantity(self.product1, existing_loc2, 5)
        self.env['stock.quant']._update_available_quantity(self.product1, no_cyclic_loc, 5)
        # cyclic inventory locations should auto-assign their next inventory date to their quants
        quant_new_loc = self.env['stock.quant'].search([('location_id', '=', new_loc.id)])
        quant_existing_loc = self.env['stock.quant'].search([('location_id', '=', existing_loc2.id)])
        self.assertEqual(quant_new_loc.inventory_date, new_loc.next_inventory_date)
        self.assertEqual(quant_existing_loc.inventory_date, existing_loc2.next_inventory_date)
        # quant without a cyclic inventory location should default to the company's annual inventory date
        quant_non_cyclic_loc = self.env['stock.quant'].search([('location_id', '=', no_cyclic_loc.id)])
        self.assertEqual(quant_non_cyclic_loc.inventory_date.month, int(no_cyclic_loc.company_id.annual_inventory_month))
        # in case of leap year, ensure we select a feasiable day for next year since inventory_date should default to last
        # day of the month if annual_inventory_day is greater than number of days in that month
        next_annual_inventory_day = min((today + relativedelta(years=1)).day, no_cyclic_loc.company_id.annual_inventory_day)
        self.assertEqual(quant_non_cyclic_loc.inventory_date.day, next_annual_inventory_day)

        quant_new_loc.inventory_quantity = 10
        (quant_new_loc | quant_existing_loc | quant_non_cyclic_loc).action_apply_inventory()
        # check location's last inventory dates + their quants next inventory dates
        self.assertEqual(new_loc.last_inventory_date, date.today())
        self.assertEqual(existing_loc2.last_inventory_date, date.today())
        self.assertEqual(no_cyclic_loc.last_inventory_date, date.today())
        self.assertEqual(new_loc.next_inventory_date, date.today() + timedelta(days=2))
        self.assertEqual(existing_loc2.next_inventory_date, date.today() + timedelta(days=2))
        self.assertEqual(quant_new_loc.inventory_date, date.today() + timedelta(days=2))
        self.assertEqual(quant_existing_loc.inventory_date, date.today() + timedelta(days=2))
        self.assertEqual(quant_non_cyclic_loc.inventory_date, date.today() + relativedelta(years=1))
