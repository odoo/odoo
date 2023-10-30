# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import UserError
from odoo.tests import tagged, common, Form
from odoo.tools import float_compare, float_is_zero


@tagged('post_install', '-at_install')
class TestRepair(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Partners
        cls.res_partner_1 = cls.env['res.partner'].create({'name': 'Wood Corner'})
        cls.res_partner_address_1 = cls.env['res.partner'].create({'name': 'Willie Burke', 'parent_id': cls.res_partner_1.id})
        cls.res_partner_12 = cls.env['res.partner'].create({'name': 'Partner 12'})

        # Products
        cls.product_product_3 = cls.env['product.product'].create({'name': 'Desk Combination'})
        cls.product_product_11 = cls.env['product.product'].create({
            'name': 'Conference Chair',
            'lst_price': 30.0,
            })
        cls.product_product_5 = cls.env['product.product'].create({'name': 'Product 5'})
        cls.product_product_6 = cls.env['product.product'].create({'name': 'Large Cabinet'})
        cls.product_product_12 = cls.env['product.product'].create({'name': 'Office Chair Black'})
        cls.product_product_13 = cls.env['product.product'].create({'name': 'Corner Desk Left Sit'})

        # Storable products
        cls.product_storable_no = cls.env['product.product'].create({
            'name': 'Product Storable No Tracking',
            'type': 'product',
            'tracking': 'none',
        })
        cls.product_storable_serial = cls.env['product.product'].create({
            'name': 'Product Storable Serial',
            'type': 'product',
            'tracking': 'serial',
        })
        cls.product_storable_lot = cls.env['product.product'].create({
            'name': 'Product Storable Lot',
            'type': 'product',
            'tracking': 'lot',
        })

        # 'Create Repair' Products
        cls.product_consu_order_repair = cls.env['product.product'].create({
            'name': 'Repair Consumable',
            'type': 'consu',
            'create_repair': True,
        })
        cls.product_storable_order_repair = cls.env['product.product'].create({
            'name': 'Repair Storable',
            'type': 'product',
            'create_repair': True,
        })
        cls.product_service_order_repair = cls.env['product.product'].create({
            'name': 'Repair Service',
            'type': 'service',
            'create_repair': True,
        })

        # Location
        cls.stock_warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.env.company.id)], limit=1)
        cls.stock_location_14 = cls.env['stock.location'].create({
            'name': 'Shelf 2',
            'location_id': cls.stock_warehouse.lot_stock_id.id,
        })

        # Repair Orders
        cls.repair1 = cls.env['repair.order'].create({
            'product_id': cls.product_product_3.id,
            'product_uom': cls.env.ref('uom.product_uom_unit').id,
            'picking_type_id': cls.stock_warehouse.repair_type_id.id,
            'move_ids': [
                (0, 0, {
                    'product_id': cls.product_product_11.id,
                    'product_uom_qty': 1.0,
                    'state': 'draft',
                    'repair_line_type': 'add',
                    'company_id': cls.env.company.id,
                })
            ],
            'partner_id': cls.res_partner_12.id,
        })

        cls.repair0 = cls.env['repair.order'].create({
            'product_id': cls.product_product_5.id,
            'product_uom': cls.env.ref('uom.product_uom_unit').id,
            'user_id': False,
            'picking_type_id': cls.stock_warehouse.repair_type_id.id,
            'move_ids': [
                (0, 0, {
                    'product_id': cls.product_product_12.id,
                    'product_uom_qty': 1.0,
                    'state': 'draft',
                    'repair_line_type': 'add',
                    'company_id': cls.env.company.id,
                })
            ],
            'partner_id': cls.res_partner_12.id,
        })

        cls.repair2 = cls.env['repair.order'].create({
            'product_id': cls.product_product_6.id,
            'product_uom': cls.env.ref('uom.product_uom_unit').id,
            'user_id': False,
            'picking_type_id': cls.stock_warehouse.repair_type_id.id,
            'move_ids': [
                (0, 0, {
                    'product_id': cls.product_product_13.id,
                    'product_uom_qty': 1.0,
                    'state': 'draft',
                    'repair_line_type': 'add',
                    'company_id': cls.env.company.id,
                })
            ],
            'partner_id': cls.res_partner_12.id,
        })

        cls.env.user.groups_id |= cls.env.ref('stock.group_stock_user')

    def _create_simple_repair_order(self):
        product_to_repair = self.product_product_5
        return self.env['repair.order'].create({
            'product_id': product_to_repair.id,
            'product_uom': product_to_repair.uom_id.id,
            'picking_type_id': self.stock_warehouse.repair_type_id.id,
            'partner_id': self.res_partner_12.id
        })

    def _create_simple_part_move(self, repair_id=False, qty=0.0, product=False):
        if not product:
            product = self.product_product_5
        return self.env['stock.move'].create({
            'repair_line_type': 'add',
            'product_id': product.id,
            'product_uom_qty': qty,
            'repair_id': repair_id,
            'company_id': self.env.company.id,
        })

    @classmethod
    def create_quant(cls, product, qty, offset=0, name="L"):
        i = 1
        if product.tracking == 'serial':
            i, qty = qty, 1
            if name == "L":
                name = "S"

        vals = []
        for x in range(1, i + 1):
            qDict = {
                'location_id': cls.stock_warehouse.lot_stock_id.id,
                'product_id': product.id,
                'inventory_quantity': qty,
            }

            if product.tracking != 'none':
                qDict['lot_id'] = cls.env['stock.lot'].create({
                    'name': name + str(offset + x),
                    'product_id': product.id,
                    'company_id': cls.env.company.id
                }).id
            vals.append(qDict)

        return cls.env['stock.quant'].create(vals)

    def test_01_repair_states_transition(self):
        repair = self._create_simple_repair_order()
        # Draft -> Confirmed -> Cancel -> Draft -> Done -> Failing Cancel
        # draft -> confirmed (action_validate -> _action_repair_confirm)
            # PRE
                # lines' qty >= 0 !-> UserError
                # product's qty IS available !-> Warning w/ choice
            # POST
                # state = confirmed
                # move_ids in (partially reserved, fully reserved, waiting availability)

        #  Line A with qty < 0 --> UserError
        lineA = self._create_simple_part_move(repair.id, -1.0, self.product_storable_no)
        repair.move_ids |= lineA
        with self.assertRaises(UserError):
            repair.action_validate()

        #  Line A with qty > 0 & not available, Line B with qty >= 0 & available --> Warning (stock.warn.insufficient.qty.repair)
        lineA.product_uom_qty = 2.0
        lineB = self._create_simple_part_move(repair.id, 2.0, self.product_storable_lot)
        repair.move_ids |= lineB
        quant = self.create_quant(self.product_storable_no, 1)
        quant |= self.create_quant(self.product_storable_lot, 3)
        quant.action_apply_inventory()

        lineC = self._create_simple_part_move(repair.id, 1.0, self.product_storable_order_repair)
        repair.move_ids |= lineC

        repair.product_id = self.product_storable_serial
        validate_action = repair.action_validate()
        self.assertEqual(validate_action.get("res_model"), "stock.warn.insufficient.qty.repair")
        # Warn qty Wizard only apply to "product TO repair"
        warn_qty_wizard = Form(
            self.env['stock.warn.insufficient.qty.repair']
            .with_context(**validate_action['context'])
            ).save()
        warn_qty_wizard.action_done()

        self.assertEqual(repair.state, "confirmed", 'Repair order should be in "Confirmed" state.')
        self.assertEqual(lineA.state, "partially_available", 'Repair line #1 should be in "Partial Availability" state.')
        self.assertEqual(lineB.state, "assigned", 'Repair line #2 should be in "Available" state.')
        self.assertEqual(lineC.state, "confirmed", 'Repair line #3 should be in "Waiting Availability" state.')

        # Create quotation
        # No partner warning -> working case -> already linked warning

        # Ensure SO doesn't exist
        self.assertEqual(len(repair.sale_order_id), 0)
        repair.partner_id = None
        with self.assertRaises(UserError) as err:
            repair.action_create_sale_order()
        self.assertIn("You need to define a customer", err.exception.args[0])
        repair.partner_id = self.res_partner_12.id
        repair.action_create_sale_order()
        # Ensure SO and SOL were created
        self.assertNotEqual(len(repair.sale_order_id), 0)
        self.assertEqual(len(repair.sale_order_id.order_line), 3)
        with self.assertRaises(UserError) as err:
            repair.action_create_sale_order()

        # (*) -> cancel (action_repair_cancel)
            # PRE
                # state != done !-> UserError (cf. end of this test)
            # POST
                # moves_ids state == cancelled
                # 'Lines" SOL product_uom_qty == 0
                # state == cancel

        self.assertNotEqual(repair.state, "done")
        repair.action_repair_cancel()
        self.assertEqual(repair.state, "cancel")
        self.assertTrue(all(m.state == "cancel" for m in repair.move_ids))
        self.assertTrue(all(float_is_zero(sol.product_uom_qty, 2) for sol in repair.sale_order_id.order_line))

        # (*)/cancel -> draft (action_repair_cancel_draft)
            # PRE
                # state == cancel !-> action_repair_cancel()
                # state != done !~> UserError (transitive..., don't care)
            # POST
                # move_ids.state == draft
                # state == draft

        repair.action_repair_cancel_draft()
        self.assertEqual(repair.state, "draft")
        self.assertTrue(all(m.state == "draft" for m in repair.move_ids))

        # draft -> confirmed
            # Enforce product_id availability to skip warning
        quant = self.create_quant(self.product_storable_serial, 1)
        quant.action_apply_inventory()
        repair.lot_id = quant.lot_id
        repair.action_validate()
        self.assertEqual(repair.state, "confirmed")

        # confirmed -> under_repair (action_repair_start)
            # Purely informative state
        repair.action_repair_start()
        self.assertEqual(repair.state, "under_repair")

        # under_repair -> done (action_repair_end -> action_repair_done)
            # PRE
                # state == under_repair !-> UserError
                # lines' quantity >= lines' product_uom_qty !-> Warning
                # line tracked => line has lot_ids !-> ValidationError
            # POST
                # lines with quantity == 0 are cancelled (related sol product_uom_qty is consequently set to 0)
                # repair.product_id => repair.move_id
                # move_ids.state == (done || cancel)
                # state == done
                # move_ids with quantity (LOWER or HIGHER than) product_uom_qty MUST NOT be splitted
        # Any line with quantity < product_uom_qty => Warning
        repair.move_ids.picked = True
        end_action = repair.action_repair_end()
        self.assertEqual(end_action.get("res_model"), "repair.warn.uncomplete.move")
        warn_uncomplete_wizard = Form(
            self.env['repair.warn.uncomplete.move']
            .with_context(**end_action['context'])
            ).save()
        # LineB : no serial => ValidationError
        lot = lineB.move_line_ids.lot_id
        with self.assertRaises(UserError) as err:
            lineB.move_line_ids.lot_id = False
            warn_uncomplete_wizard.action_validate()

        # LineB with lots
        lineB.move_line_ids.lot_id = lot

        lineA.quantity = 2  # quantity = product_uom_qty
        lineC.quantity = 2  # quantity > product_uom_qty (No warning)
        lineD = self._create_simple_part_move(repair.id, 0.0)
        repair.move_ids |= lineD  # product_uom_qty = 0   : state is cancelled

        self.assertEqual(lineD.state, 'assigned')
        num_of_lines = len(repair.move_ids)
        self.assertFalse(repair.move_id)
        repair.action_repair_end()

        self.assertEqual(repair.state, "done")
        done_moves = repair.move_ids - lineD
        #line a,b,c are 'done', line d is 'cancel'
        self.assertTrue(all(m.state == 'done' for m in done_moves))
        self.assertEqual(lineD.state, 'cancel')
        self.assertEqual(len(repair.move_id), 1)
        self.assertEqual(len(repair.move_ids), num_of_lines)  # No split

        # (*) -> cancel (action_repair_cancel)
            # PRE
                # state != done !-> UserError
        with self.assertRaises(UserError) as err:
            repair.action_repair_cancel()

    def test_02_repair_sale_order_binding(self):
        # Binding from SO to RO(s)
        #   On SO Confirm
        #     - Create linked RO per line (only if item with "create_repair" checked)
        #   Create Repair SOL
        #     - sol qty updated to 0 -> RO canceled (Reciprocal is true too)
        #     - sol qty back to >0 -> RO Confirmed (Reciprocal is not true)
        #   RO Parts SOL
        #     - SOL qty change is NOT propagated to RO
        #     - However, these changes FROM RO are propagated to SO
        #----------------------------------------------------------------------------------
        #  Binding from RO to SO
        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.res_partner_1
        with so_form.order_line.new() as line:
            line.product_id = self.product_consu_order_repair
            line.product_uom_qty = 2.0
        sale_order = so_form.save()
        order_line = sale_order.order_line[0]
        self.assertEqual(len(sale_order.repair_order_ids), 0)
        sale_order.action_confirm()
        # Quantity set on the "create repair" product doesn't affect the number of RO created
        self.assertEqual(len(sale_order.repair_order_ids), 1)
        repair_order = sale_order.repair_order_ids[0]
        self.assertEqual(sale_order, repair_order.sale_order_id)
        self.assertEqual(repair_order.state, 'confirmed')
        order_line.product_uom_qty = 0
        self.assertEqual(repair_order.state, 'cancel')
        order_line.product_uom_qty = 1
        self.assertEqual(repair_order.state, 'confirmed')
        repair_order.action_repair_cancel()
        self.assertTrue(float_is_zero(order_line.product_uom_qty, 2))
        order_line.product_uom_qty = 3
        self.assertEqual(repair_order.state, 'confirmed')
        # Add RO line
        ro_form = Form(repair_order)
        with ro_form.move_ids.new() as ro_line_form:
            ro_line_form.repair_line_type = 'add'
            ro_line_form.product_id = self.product_product_11
            ro_line_form.product_uom_qty = 1
        ro_form.save()
        ro_line_0 = repair_order.move_ids[0]
        sol_part_0 = ro_line_0.sale_line_id
        self.assertEqual(float_compare(sol_part_0.product_uom_qty, ro_line_0.product_uom_qty, 2), 0)
        # chg qty in SO -> No effect on RO
        sol_part_0.product_uom_qty = 5
        self.assertNotEqual(float_compare(sol_part_0.product_uom_qty, ro_line_0.product_uom_qty, 2), 0)
        # chg qty in RO -> Update qty in SO
        ro_line_0.product_uom_qty = 3
        self.assertEqual(float_compare(sol_part_0.product_uom_qty, ro_line_0.product_uom_qty, 2), 0)
        # with/without warranty
        self.assertFalse(float_is_zero(sol_part_0.price_unit, 2))
        repair_order.under_warranty = True
        self.assertTrue(float_is_zero(sol_part_0.price_unit, 2))
        repair_order.under_warranty = False
        self.assertFalse(float_is_zero(sol_part_0.price_unit, 2))

        # stock_move transitions
        #   add -> remove -> add -> recycle -> add transitions
        ro_line_0.repair_line_type = 'remove'
        self.assertTrue(float_is_zero(sol_part_0.product_uom_qty, 2))
        ro_line_0.repair_line_type = 'add'
        self.assertEqual(float_compare(sol_part_0.product_uom_qty, ro_line_0.product_uom_qty, 2), 0)
        ro_line_0.repair_line_type = 'recycle'
        self.assertTrue(float_is_zero(sol_part_0.product_uom_qty, 2))
        ro_line_0.repair_line_type = 'add'
        self.assertEqual(float_compare(sol_part_0.product_uom_qty, ro_line_0.product_uom_qty, 2), 0)
        #   remove and recycle line : not added to SO.
        sol_count = len(sale_order.order_line)
        with ro_form.move_ids.new() as ro_line_form:
            ro_line_form.repair_line_type = 'remove'
            ro_line_form.product_id = self.product_product_12
            ro_line_form.product_uom_qty = 1
        with ro_form.move_ids.new() as ro_line_form:
            ro_line_form.repair_line_type = 'recycle'
            ro_line_form.product_id = self.product_product_13
            ro_line_form.product_uom_qty = 1
        ro_form.save()
        ro_line_1 = repair_order.move_ids[1]
        self.assertEqual(len(sale_order.order_line), sol_count)
        # remove to add -> added to SO
        ro_line_1.repair_line_type = 'add'
        sol_part_1 = ro_line_1.sale_line_id
        self.assertNotEqual(len(sale_order.order_line), sol_count)
        self.assertEqual(float_compare(sol_part_1.product_uom_qty, ro_line_1.product_uom_qty, 2), 0)
        # delete 'remove to add' line in RO -> SOL qty set to 0
        repair_order.move_ids = [(2, ro_line_1.id, 0)]
        self.assertTrue(float_is_zero(sol_part_1.product_uom_qty, 2))

        # repair_order.action_repair_end()
        #   -> order_line.qty_delivered == order_line.product_uom_qty
        #   -> "RO Lines"'s SOL.qty_delivered == move.quantity
        repair_order.action_repair_start()
        for line in repair_order.move_ids:
            line.quantity = line.product_uom_qty
        repair_order.action_repair_end()
        self.assertTrue(float_is_zero(order_line.qty_delivered, 2))
        self.assertEqual(float_compare(sol_part_0.product_uom_qty, ro_line_0.quantity, 2), 0)
        self.assertTrue(float_is_zero(sol_part_1.qty_delivered, 2))

    def test_03_sale_order_delivered_qty(self):
        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.res_partner_1
        with so_form.order_line.new() as line:
            line.product_id = self.product_consu_order_repair
            line.product_uom_qty = 1.0
        with so_form.order_line.new() as line:
            line.product_id = self.product_storable_order_repair
            line.product_uom_qty = 1.0
        with so_form.order_line.new() as line:
            line.product_id = self.product_service_order_repair
            line.product_uom_qty = 1.0
        sale_order = so_form.save()
        sale_order.action_confirm()

        repair_order_ids = sale_order.repair_order_ids
        repair_order_ids.action_repair_start()
        repair_order_ids.action_repair_end()

        for sol in sale_order.order_line:
            if sol.product_template_id.type == 'service':
                self.assertEqual(float_compare(sol.product_uom_qty, sol.qty_delivered, 2), 0)
            else:
                self.assertTrue(float_is_zero(sol.qty_delivered, 2))

    def test_repair_return(self):
        """Tests functionality of creating a repair directly from a return picking,
        i.e. repair can be made and defaults to appropriate return values. """
        # test return
        # Required for `location_dest_id` to be visible in the view
        self.env.user.groups_id += self.env.ref('stock.group_stock_multi_locations')
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.stock_warehouse.in_type_id
        picking_form.partner_id = self.res_partner_1
        picking_form.location_dest_id = self.stock_location_14
        return_picking = picking_form.save()

        # create repair
        res_dict = return_picking.action_repair_return()
        repair_form = Form(self.env[(res_dict.get('res_model'))].with_context(res_dict['context']))
        repair_form.product_id = self.product_product_3
        repair = repair_form.save()

        # test that the resulting repairs are correctly created
        self.assertEqual(len(return_picking.repair_ids), 1, "A repair order should have been created and linked to original return.")
        for repair in return_picking.repair_ids:
            self.assertEqual(repair.location_id, return_picking.location_dest_id, "Repair location should have defaulted to return destination location")
            self.assertEqual(repair.partner_id, return_picking.partner_id, "Repair customer should have defaulted to return customer")
            self.assertEqual(repair.picking_type_id, return_picking.picking_type_id.warehouse_id.repair_type_id)

    def test_repair_compute_product_uom(self):
        repair = self.env['repair.order'].create({
            'product_id': self.product_product_3.id,
            'picking_type_id': self.stock_warehouse.repair_type_id.id,
            'move_ids': [
                (0, 0, {
                    'repair_line_type': 'add',
                    'product_id': self.product_product_11.id,
                })
            ],
        })
        self.assertEqual(repair.product_uom, self.product_product_3.uom_id)
        self.assertEqual(repair.move_ids[0].product_uom, self.product_product_11.uom_id)

    def test_repair_compute_location(self):
        repair = self.env['repair.order'].create({
            'product_id': self.product_product_3.id,
            'picking_type_id': self.stock_warehouse.repair_type_id.id,
            'move_ids': [
                (0, 0, {
                    'repair_line_type': 'add',
                    'product_id': self.product_product_11.id,
                })
            ],
        })
        self.assertEqual(repair.location_id, self.stock_warehouse.lot_stock_id)
        self.assertEqual(repair.move_ids[0].location_id, self.stock_warehouse.lot_stock_id)
        location_dest_id = self.env['stock.location'].search([
            ('usage', '=', 'production'),
            ('company_id', '=', repair.company_id.id),
        ], limit=1)
        self.assertEqual(repair.move_ids[0].location_dest_id, location_dest_id)

    def test_purchase_price_so_create_from_repair(self):
        """
        Test that the purchase price is correctly set on the SO line,
        when creating a SO from a repair order.
        """
        if not self.env['ir.module.module'].search([('name', '=', 'sale_margin'), ('state', '=', 'installed')]):
            self.skipTest("sale_margin is not installed, so there is no purchase price to test")
        self.product_product_11.standard_price = 10
        repair = self.env['repair.order'].create({
            'partner_id': self.res_partner_1.id,
            'product_id': self.product_product_3.id,
            'picking_type_id': self.stock_warehouse.repair_type_id.id,
            'move_ids': [
                (0, 0, {
                    'repair_line_type': 'add',
                    'product_id': self.product_product_11.id,
                })
            ],
        })
        repair.action_create_sale_order()
        self.assertEqual(repair.sale_order_id.order_line.product_id, self.product_product_11)
        self.assertEqual(repair.sale_order_id.order_line.purchase_price, 10)

    def test_repair_from_return(self):
        """
        create a repair order from a return delivery and ensure that the stock.move
        resulting from the repair is not associated with the return picking.
        """

        product = self.env['product.product'].create({
            'name': 'Test Product',
            'type': 'product',
        })
        self.env['stock.quant']._update_available_quantity(product, self.stock_location_14, 1)
        picking_form = Form(self.env['stock.picking'])
        #create a delivery order
        picking_form.picking_type_id = self.stock_warehouse.out_type_id
        picking_form.partner_id = self.res_partner_1
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = product
            move.product_uom_qty = 1.0
        picking = picking_form.save()
        picking.action_confirm()
        picking.action_assign()
        picking.button_validate()

        self.assertEqual(picking.state, 'done')
        # Create a return
        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=picking.ids, active_id=picking.ids[0],
            active_model='stock.picking'))
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.quantity = 1.0
        stock_return_picking_action = stock_return_picking.create_returns()
        return_picking = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
        return_picking.move_ids.picked = True
        return_picking.button_validate()
        self.assertEqual(return_picking.state, 'done')

        res_dict = return_picking.action_repair_return()
        repair_form = Form(self.env[(res_dict.get('res_model'))].with_context(res_dict['context']))
        repair_form.product_id = product
        repair = repair_form.save()
        repair.action_repair_start()
        repair.action_repair_end()
        self.assertEqual(repair.state, 'done')
        self.assertEqual(len(return_picking.move_ids), 1)
