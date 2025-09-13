# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.exceptions import AccessError, UserError
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
        end_action = repair.action_repair_end()
        self.assertEqual(end_action.get("res_model"), "repair.warn.uncomplete.move")
        warn_uncomplete_wizard = Form(
            self.env['repair.warn.uncomplete.move']
            .with_context(**end_action['context'])
            ).save()
        warn_uncomplete_wizard.action_validate()
        self.assertFalse((repair.move_id | repair.move_ids).picking_id, "No picking for repair moves")
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
        with so_form.order_line.new() as line:
            line.display_type = 'line_section'
            line.name = 'Dummy Section'
        sale_order = so_form.save()
        order_line = sale_order.order_line[0]
        line_section = sale_order.order_line[1]
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
        line_section.name = 'updated section'
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

    def test_no_recompute_location_when_change_user_after_confirm(self):
        user1 = self.env['res.users'].create({
            'name': 'A User',
            'login': 'a_user',
            'email': 'a@user.com',
        })
        repair_order = self._create_simple_repair_order()
        repair_order.location_id = self.stock_location_14
        repair_order.recycle_location_id = self.stock_location_14
        repair_order.action_validate()
        repair_order.user_id = user1
        self.assertEqual(repair_order.location_id, self.stock_location_14)
        self.assertEqual(repair_order.recycle_location_id, self.stock_location_14)
        repair_order.action_repair_start()
        repair_order.action_repair_end()
        with Form(repair_order) as ro_form:
            ro_form.user_id = user1
        self.assertEqual(repair_order.location_id, self.stock_location_14)
        self.assertEqual(repair_order.recycle_location_id, self.stock_location_14)

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
        repair_form = Form(self.env[(res_dict.get('res_model'))].with_context(res_dict['context']), view=res_dict['view_id'])
        repair_form.product_id = product
        # The repair needs to be saved to ensure the context is correctly set.
        repair = repair_form.save()
        repair_form = Form(repair)
        with repair_form.move_ids.new() as move:
            move.product_id = self.product_product_5
            move.product_uom_qty = 1.0
            move.quantity = 1.0
            move.repair_line_type = 'add'
        repair = repair_form.save()
        repair.action_repair_start()
        repair.action_repair_end()
        self.assertEqual(repair.state, 'done')
        self.assertEqual(len(return_picking.move_ids), 1, "Parts added to the repair order shoudln't be added to the return picking")
        self.assertEqual(repair.location_id, return_picking.location_dest_id, "Repair location should have defaulted to return destination location")
        self.assertEqual(repair.partner_id, return_picking.partner_id, "Repair customer should have defaulted to return customer")
        self.assertEqual(repair.picking_type_id, return_picking.picking_type_id.warehouse_id.repair_type_id)

    def test_repair_with_product_in_package(self):
        """
        Test That a repair order can be validated when the repaired product is tracked and in a package
        """
        self.product_product_3.tracking = 'serial'
        self.product_product_3.type = 'product'
        # Create two serial numbers
        sn_1 = self.env['stock.lot'].create({'name': 'sn_1', 'product_id': self.product_product_3.id})
        sn_2 = self.env['stock.lot'].create({'name': 'sn_2', 'product_id': self.product_product_3.id})

        # Create two packages
        package_1 = self.env['stock.quant.package'].create({'name': 'Package-test-1'})
        package_2 = self.env['stock.quant.package'].create({'name': 'Package-test-2'})

        # update the quantity of the product in the stock
        self.env['stock.quant']._update_available_quantity(self.product_product_3, self.stock_warehouse.lot_stock_id, 1, lot_id=sn_1, package_id=package_1)
        self.env['stock.quant']._update_available_quantity(self.product_product_3, self.stock_warehouse.lot_stock_id, 1, lot_id=sn_2, package_id=package_2)
        self.assertEqual(self.product_product_3.qty_available, 2)
        # create a repair order
        repair_order = self.env['repair.order'].create({
            'product_id': self.product_product_3.id,
            'product_uom': self.product_product_3.uom_id.id,
            # 'guarantee_limit': '2019-01-01',
            'location_id': self.stock_warehouse.lot_stock_id.id,
            'lot_id': sn_1.id,
            'picking_type_id': self.stock_warehouse.repair_type_id.id,
            'move_ids': [
                (0, 0, {
                    'product_id': self.product_product_5.id,
                    'product_uom_qty': 1.0,
                    'state': 'draft',
                    'repair_line_type': 'add',
                })
            ],
        })
        # Validate and complete the repair order
        repair_order.action_validate()
        self.assertEqual(repair_order.state, 'confirmed')
        repair_order.action_repair_start()
        self.assertEqual(repair_order.state, 'under_repair')
        repair_order.move_ids.quantity = 1
        repair_order.action_repair_end()
        self.assertEqual(repair_order.state, 'done')

    def test_sn_with_no_tracked_product(self):
        """
        Check that the lot_id field is cleared after updating the product in the repair order.
        """
        self.env.ref('base.group_user').implied_ids += (
            self.env.ref('stock.group_production_lot')
        )
        sn_1 = self.env['stock.lot'].create({'name': 'sn_1', 'product_id': self.product_storable_serial.id})
        ro_form = Form(self.env['repair.order'])
        ro_form.product_id = self.product_storable_serial
        ro_form.lot_id = sn_1
        repair_order = ro_form.save()
        ro_form = Form(repair_order)
        ro_form.product_id = self.product_storable_no
        repair_order = ro_form.save()
        self.assertFalse(repair_order.lot_id)

    def test_repair_multi_unit_order_with_serial_tracking(self):
        """
        Test that a sale order with a single order line with quantity > 1 for a product that creates a repair order and
        is tracked via serial number creates multiple repair orders rather than grouping the line into a single RO
        """
        product_a = self.env['product.product'].create({
            'name': 'productA',
            'detailed_type': 'product',
            'tracking': 'serial',
            'create_repair': True,
        })

        sale_order = self.env['sale.order'].create({
            'partner_id': self.res_partner_1.id,
            'order_line': [Command.create({
                'product_id': product_a.id,
                'product_uom_qty': 3.0,
            })]
        })
        sale_order.action_confirm()

        repair_orders = sale_order.repair_order_ids
        self.assertRecordValues(repair_orders, [
            {'product_id': product_a.id, 'product_qty': 1.0},
            {'product_id': product_a.id, 'product_qty': 1.0},
            {'product_id': product_a.id, 'product_qty': 1.0},
        ])

    def test_onchange_picking_type_id_and_name(self):
        """
        Test that when changing the picking_type_id, the name of the repair order should be changed too
        """
        repair_order = self.env['repair.order'].create({
            'product_id': self.product_product_3.id,
            'picking_type_id': self.stock_warehouse.repair_type_id.id,
        })
        picking_type_1 = self.env['stock.picking.type'].create({
            'name': 'new_picking_type_1',
            'code': 'repair_operation',
            'sequence_code': 'PT1/',
        })
        picking_type_2 = self.env['stock.picking.type'].create({
            'name': 'new_picking_type_2',
            'code': 'repair_operation',
            'sequence_code': 'PT2/',
        })
        repair_order.picking_type_id = picking_type_1
        self.assertEqual(repair_order.name, "PT1/00001")
        repair_order.picking_type_id = picking_type_2
        self.assertEqual(repair_order.name, "PT2/00001")
        repair_order.picking_type_id = picking_type_1
        self.assertEqual(repair_order.name, "PT1/00002")
        repair_order.picking_type_id = picking_type_1
        self.assertEqual(repair_order.name, "PT1/00002")

    def test_repair_components_lots_show_in_invoice(self):
        """
        Test that the lots of the components of a repair order are shown in the invoice
        """
        quant = self.create_quant(self.product_storable_serial, 1)
        quant.action_apply_inventory()
        repair_order = self.env['repair.order'].create({
            'product_id': self.product_product_3.id,
            'product_uom': self.product_product_3.uom_id.id,
            'partner_id': self.res_partner_12.id,
            'move_ids': [
                Command.create({
                    'product_id': self.product_storable_serial.id,
                    'product_uom_qty': 1.0,
                    'state': 'draft',
                    'repair_line_type': 'add',
                })
            ],
        })
        repair_order.action_validate()
        repair_order.action_repair_start()
        repair_order.action_repair_end()
        repair_order.action_create_sale_order()
        sale_order = repair_order.sale_order_id
        sale_order.action_confirm()
        invoice = sale_order._create_invoices()
        invoice.action_post()
        res = invoice._get_invoiced_lot_values()
        self.assertEqual(len(res), 1, "The invoice should have one line")
        self.assertEqual(res[0]['product_name'], self.product_storable_serial.display_name, "The product name should be the same")
        self.assertEqual(res[0]['lot_name'], quant.lot_id.name, "The lot name should be the same")

    def test_trigger_orderpoint_from_repair(self):
        """
        Test that the order point triggered by the repair order creates a move linked to a picking.
        """
        self.assertFalse(self.env['stock.move'].search([('product_id', '=', self.product_storable_no.id)]))
        route = self.env['stock.route'].create({
            'name': 'new route',
            'rule_ids': [(0, False, {
                'name': 'rule_test',
                'location_src_id': self.stock_warehouse.lot_stock_id.id,
                'location_dest_id': self.stock_location_14.id,
                'company_id': self.env.company.id,
                'action': 'pull',
                'picking_type_id': self.env.ref('stock.picking_type_in').id,
                'procure_method': 'make_to_stock'
            })],
        })
        self.env['stock.warehouse.orderpoint'].create({
            'name': 'Cake RR',
            'product_id': self.product_storable_no,
            'route_id': route.id,
            'location_id': self.stock_location_14.id,
            'product_id': self.product_storable_no.id,
            'product_min_qty': 0,
            'product_max_qty': 1,
            'trigger': 'auto'
        })
        # The product to be repaired should be storable and out of stock
        # to trigger the wizard indicating that the product has an insufficient quantity.
        self.product_product_3.type = 'product'
        repair_order = self.env['repair.order'].create({
            'product_id': self.product_product_3.id,
            'product_uom': self.product_product_3.uom_id.id,
            'partner_id': self.res_partner_12.id,
            'location_id': self.stock_location_14.id,
            'move_ids': [
                Command.create({
                    'product_id': self.product_storable_no.id,
                    'product_uom_qty': 1.0,
                    'state': 'draft',
                    'repair_line_type': 'add',
                })
            ],
        })
        validate_action = repair_order.action_validate()
        self.assertEqual(validate_action.get("res_model"), "stock.warn.insufficient.qty.repair")
        warn_qty_wizard = Form(
            self.env['stock.warn.insufficient.qty.repair']
            .with_context(**validate_action['context'])
            ).save()
        warn_qty_wizard.action_done()
        self.assertEqual(repair_order.state, "confirmed", 'Repair order should be in "Confirmed" state.')
        move = self.env['stock.move'].search([
            ('product_id', '=', self.product_storable_no.id),
            ('location_dest_id', '=', self.stock_location_14.id,)
        ])
        self.assertTrue(move.picking_id)
        self.assertFalse(move.repair_id)
        self.assertEqual(move.location_id, self.stock_warehouse.lot_stock_id)
        self.assertEqual(move.location_dest_id, self.stock_location_14)

    def test_open_and_create_repair_from_lot(self):
        """
        Test that the repair order can be opened from the lot and that it is created correctly.
        """
        sn_1 = self.env['stock.lot'].create({'name': 'sn_1', 'product_id': self.product_storable_serial.id})
        action = sn_1.action_lot_open_repairs()
        context = action.get('context')
        tracked_product_repair_line = self.env['product.product'].create({
            'name': 'Test Product',
            'type': 'product',
            'tracking': 'serial',
        })
        tracked_product_sn = self.env['stock.lot'].create({'name': 'tracked_product_sn1', 'product_id': tracked_product_repair_line.id})
        repair_order = self.env['repair.order'].with_context(context).create({
            'product_id': self.product_storable_serial.id,
            'product_uom': self.product_storable_serial.uom_id.id,
            'location_id': self.stock_warehouse.lot_stock_id.id,
            'lot_id': sn_1.id,
            'picking_type_id': self.stock_warehouse.repair_type_id.id,
        })
        repair_order.with_context(context).move_ids = [Command.create({
            'product_id': tracked_product_repair_line.id,
            'product_uom_qty': 1.0,
            'repair_line_type': 'add',
            'lot_ids': [(4, tracked_product_sn.id)],
            'quantity': 1.0,
        })]
        self.assertEqual(repair_order.lot_id, sn_1)

    def test_copy_repair_product_with_different_groups(self):
        """
            This test checks if the product can be copied with users that don't have access on the Inventory app
        """
        product_templ = self.env['product.template'].create({
            'name': "Repair Consumable",
            'type': 'consu',
            'create_repair': True,
        })
        mitchell_user = self.env['res.users'].create({
            'name': "Mitchell not Admin",
            'login': "m_user",
            'email': "m@user.com",
            'groups_id': [Command.set(self.env.ref('sales_team.group_sale_manager').ids)],
        })
        product_templ.invalidate_recordset(['create_repair'])
        with self.assertRaises(AccessError):
            product_templ.with_user(mitchell_user).create_repair
        copied_without_access = product_templ.with_user(mitchell_user).copy()
        mitchell_user.write({
            'groups_id': [Command.link(self.env.ref('stock.group_stock_user').id)]
        })
        self.assertFalse(copied_without_access.create_repair)
        copied_with_access = product_templ.copy().with_user(mitchell_user)
        self.assertTrue(copied_with_access.create_repair)

    def test_delivered_qty_of_generated_so(self):
        """
        Test that checks that `qty_delivered` of the generated SOL is correctly set when the repair is done.
        """
        repair_order = self.env['repair.order'].create({
            'product_id': self.product_storable_order_repair.id,
            'product_uom': self.product_storable_order_repair.uom_id.id,
            'partner_id': self.res_partner_1.id,
            'move_ids': [
                Command.create({
                    'product_id': self.product_consu_order_repair.id,
                    'product_uom_qty': 1.0,
                    'state': 'draft',
                    'repair_line_type': 'add',
                })
            ],
        })
        repair_order.action_validate()
        repair_order.action_repair_start()
        repair_order.action_repair_end()
        self.assertEqual(repair_order.state, 'done')
        self.assertEqual(repair_order.move_ids.quantity, 1.0)
        repair_order.action_create_sale_order()
        sale_order = repair_order.sale_order_id
        sale_order.action_confirm()
        self.assertEqual(sale_order.order_line.qty_delivered, 1.0)
