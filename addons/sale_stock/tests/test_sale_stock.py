# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, timedelta

from odoo.addons.sale.tests.test_sale_common import TestSale
from odoo.exceptions import UserError
from odoo.tests import Form, tagged


@tagged('post_install', '-at_install')
class TestSaleStock(TestSale):
    def _get_new_sale_order(self, amount=10.0):
        """ Creates and returns a sale order with one default order line.

        :param float amount: quantity of product for the order line (10 by default)
        """
        partner = self.env.ref('base.res_partner_1')
        product = self.env.ref('product.product_delivery_01')
        sale_order_vals = {
            'partner_id': partner.id,
            'partner_invoice_id': partner.id,
            'partner_shipping_id': partner.id,
            'order_line': [(0, 0, {
                'name': product.name,
                'product_id': product.id,
                'product_uom_qty': amount,
                'product_uom': product.uom_id.id,
                'price_unit': product.list_price})],
            'pricelist_id': self.env.ref('product.list0').id,
        }
        sale_order = self.env['sale.order'].create(sale_order_vals)
        return sale_order

    def test_00_sale_stock_invoice(self):
        """
        Test SO's changes when playing around with stock moves, quants, pack operations, pickings
        and whatever other model there is in stock with "invoice on delivery" products
        """
        inv_obj = self.env['account.move']
        self.so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, {'name': p.name, 'product_id': p.id, 'product_uom_qty': 2, 'product_uom': p.uom_id.id, 'price_unit': p.list_price}) for p in self.products.values()],
            'pricelist_id': self.env.ref('product.list0').id,
            'picking_policy': 'direct',
        })

        # confirm our standard so, check the picking
        self.so.action_confirm()
        self.assertTrue(self.so.picking_ids, 'Sale Stock: no picking created for "invoice on delivery" storable products')
        # invoice on order
        self.so._create_invoices()

        # deliver partially, check the so's invoice_status and delivered quantities
        self.assertEqual(self.so.invoice_status, 'no', 'Sale Stock: so invoice_status should be "nothing to invoice" after invoicing')
        pick = self.so.picking_ids
        pick.move_lines.write({'quantity_done': 1})
        wiz_act = pick.button_validate()
        wiz = self.env[wiz_act['res_model']].browse(wiz_act['res_id'])
        wiz.process()
        self.assertEqual(self.so.invoice_status, 'to invoice', 'Sale Stock: so invoice_status should be "to invoice" after partial delivery')
        del_qties = [sol.qty_delivered for sol in self.so.order_line]
        del_qties_truth = [1.0 if sol.product_id.type in ['product', 'consu'] else 0.0 for sol in self.so.order_line]
        self.assertEqual(del_qties, del_qties_truth, 'Sale Stock: delivered quantities are wrong after partial delivery')
        # invoice on delivery: only storable products
        inv_1 = self.so._create_invoices()
        self.assertTrue(all([il.product_id.invoice_policy == 'delivery' for il in inv_1.invoice_line_ids]),
                        'Sale Stock: invoice should only contain "invoice on delivery" products')

        # complete the delivery and check invoice_status again
        self.assertEqual(self.so.invoice_status, 'no',
                         'Sale Stock: so invoice_status should be "nothing to invoice" after partial delivery and invoicing')
        self.assertEqual(len(self.so.picking_ids), 2, 'Sale Stock: number of pickings should be 2')
        pick_2 = self.so.picking_ids.filtered('backorder_id')
        pick_2.move_lines.write({'quantity_done': 1})
        self.assertIsNone(pick_2.button_validate(), 'Sale Stock: second picking should be final without need for a backorder')
        self.assertEqual(self.so.invoice_status, 'to invoice', 'Sale Stock: so invoice_status should be "to invoice" after complete delivery')
        del_qties = [sol.qty_delivered for sol in self.so.order_line]
        del_qties_truth = [2.0 if sol.product_id.type in ['product', 'consu'] else 0.0 for sol in self.so.order_line]
        self.assertEqual(del_qties, del_qties_truth, 'Sale Stock: delivered quantities are wrong after complete delivery')
        # Without timesheet, we manually set the delivered qty for the product serv_del
        self.so.order_line.sorted()[1]['qty_delivered'] = 2.0
        # There is a bug with `new` and `_origin`
        # If you create a first new from a record, then change a value on the origin record, than create another new,
        # this other new wont have the updated value of the origin record, but the one from the previous new
        # Here the problem lies in the use of `new` in `move = self_ctx.new(new_vals)`,
        # and the fact this method is called multiple times in the same transaction test case.
        # Here, we update `qty_delivered` on the origin record, but the `new` records which are in cache with this order line
        # as origin are not updated, nor the fields that depends on it.
        self.so.flush()
        for field in self.env['sale.order.line']._fields.values():
            for res_id in list(self.env.cache._data[field]):
                if not res_id:
                    self.env.cache._data[field].pop(res_id)
        inv_id = self.so._create_invoices()
        self.assertEqual(self.so.invoice_status, 'invoiced',
                         'Sale Stock: so invoice_status should be "fully invoiced" after complete delivery and invoicing')

    def test_01_sale_stock_order(self):
        """
        Test SO's changes when playing around with stock moves, quants, pack operations, pickings
        and whatever other model there is in stock with "invoice on order" products
        """
        # let's cheat and put all our products to "invoice on order"
        self.so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, {'name': p.name, 'product_id': p.id, 'product_uom_qty': 2, 'product_uom': p.uom_id.id, 'price_unit': p.list_price}) for p in self.products.values()],
            'pricelist_id': self.env.ref('product.list0').id,
            'picking_policy': 'direct',
        })
        for sol in self.so.order_line:
            sol.product_id.invoice_policy = 'order'
        # confirm our standard so, check the picking
        self.so.order_line._compute_product_updatable()
        self.assertTrue(self.so.order_line.sorted()[0].product_updatable)
        self.so.action_confirm()
        self.so.order_line._compute_product_updatable()
        self.assertFalse(self.so.order_line.sorted()[0].product_updatable)
        self.assertTrue(self.so.picking_ids, 'Sale Stock: no picking created for "invoice on order" storable products')
        # let's do an invoice for a deposit of 5%
        adv_wiz = self.env['sale.advance.payment.inv'].with_context(active_ids=[self.so.id]).create({
            'advance_payment_method': 'percentage',
            'amount': 5.0,
            'product_id': self.env.ref('sale.advance_product_0').id,
        })
        act = adv_wiz.with_context(open_invoices=True).create_invoices()
        inv = self.env['account.move'].browse(act['res_id'])
        self.assertEqual(inv.amount_untaxed, self.so.amount_untaxed * 5.0 / 100.0, 'Sale Stock: deposit invoice is wrong')
        self.assertEqual(self.so.invoice_status, 'to invoice', 'Sale Stock: so should be to invoice after invoicing deposit')
        # invoice on order: everything should be invoiced
        self.so._create_invoices(final=True)
        self.assertEqual(self.so.invoice_status, 'invoiced', 'Sale Stock: so should be fully invoiced after second invoice')

        # deliver, check the delivered quantities
        pick = self.so.picking_ids
        pick.move_lines.write({'quantity_done': 2})
        self.assertIsNone(pick.button_validate(), 'Sale Stock: complete delivery should not need a backorder')
        del_qties = [sol.qty_delivered for sol in self.so.order_line]
        del_qties_truth = [2.0 if sol.product_id.type in ['product', 'consu'] else 0.0 for sol in self.so.order_line]
        self.assertEqual(del_qties, del_qties_truth, 'Sale Stock: delivered quantities are wrong after partial delivery')
        # invoice on delivery: nothing to invoice
        with self.assertRaises(UserError):
            self.so._create_invoices()

    def test_02_sale_stock_return(self):
        """
        Test a SO with a product invoiced on delivery. Deliver and invoice the SO, then do a return
        of the picking. Check that a refund invoice is well generated.
        """
        # intial so
        self.partner = self.env.ref('base.res_partner_1')
        self.product = self.env.ref('product.product_delivery_01')
        so_vals = {
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, {
                'name': self.product.name,
                'product_id': self.product.id,
                'product_uom_qty': 5.0,
                'product_uom': self.product.uom_id.id,
                'price_unit': self.product.list_price})],
            'pricelist_id': self.env.ref('product.list0').id,
        }
        self.so = self.env['sale.order'].create(so_vals)

        # confirm our standard so, check the picking
        self.so.action_confirm()
        self.assertTrue(self.so.picking_ids, 'Sale Stock: no picking created for "invoice on delivery" storable products')

        # invoice in on delivery, nothing should be invoiced
        self.assertEqual(self.so.invoice_status, 'no', 'Sale Stock: so invoice_status should be "no" instead of "%s".' % self.so.invoice_status)

        # deliver completely
        pick = self.so.picking_ids
        pick.move_lines.write({'quantity_done': 5})
        pick.button_validate()

        # Check quantity delivered
        del_qty = sum(sol.qty_delivered for sol in self.so.order_line)
        self.assertEqual(del_qty, 5.0, 'Sale Stock: delivered quantity should be 5.0 instead of %s after complete delivery' % del_qty)

        # Check invoice
        self.assertEqual(self.so.invoice_status, 'to invoice', 'Sale Stock: so invoice_status should be "to invoice" instead of "%s" before invoicing' % self.so.invoice_status)
        self.inv_1 = self.so._create_invoices()
        self.assertEqual(self.so.invoice_status, 'invoiced', 'Sale Stock: so invoice_status should be "invoiced" instead of "%s" after invoicing' % self.so.invoice_status)
        self.assertEqual(len(self.inv_1), 1, 'Sale Stock: only one invoice instead of "%s" should be created' % len(self.inv_1))
        self.assertEqual(self.inv_1.amount_untaxed, self.inv_1.amount_untaxed, 'Sale Stock: amount in SO and invoice should be the same')
        self.inv_1.post()

        # Create return picking
        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=pick.ids, active_id=pick.sorted().ids[0],
            active_model='stock.picking'))
        return_wiz = stock_return_picking_form.save()
        return_wiz.product_return_moves.quantity = 2.0 # Return only 2
        return_wiz.product_return_moves.to_refund = True # Refund these 2
        res = return_wiz.create_returns()
        return_pick = self.env['stock.picking'].browse(res['res_id'])

        # Validate picking
        return_pick.move_lines.write({'quantity_done': 2})
        return_pick.button_validate()

        # Check invoice
        self.assertEqual(self.so.invoice_status, 'to invoice', 'Sale Stock: so invoice_status should be "to invoice" instead of "%s" after picking return' % self.so.invoice_status)
        self.assertAlmostEqual(self.so.order_line.sorted()[0].qty_delivered, 3.0, msg='Sale Stock: delivered quantity should be 3.0 instead of "%s" after picking return' % self.so.order_line.sorted()[0].qty_delivered)
        # let's do an invoice with refunds
        adv_wiz = self.env['sale.advance.payment.inv'].with_context(active_ids=[self.so.id]).create({
            'advance_payment_method': 'delivered',
        })
        adv_wiz.with_context(open_invoices=True).create_invoices()
        self.inv_2 = self.so.invoice_ids.filtered(lambda r: r.state == 'draft')
        self.assertAlmostEqual(self.inv_2.invoice_line_ids.sorted()[0].quantity, 2.0, msg='Sale Stock: refund quantity on the invoice should be 2.0 instead of "%s".' % self.inv_2.invoice_line_ids.sorted()[0].quantity)
        self.assertEqual(self.so.invoice_status, 'no', 'Sale Stock: so invoice_status should be "no" instead of "%s" after invoicing the return' % self.so.invoice_status)

    def test_03_sale_stock_delivery_partial(self):
        """
        Test a SO with a product invoiced on delivery. Deliver partially and invoice the SO, when
        the SO is set on 'done', the SO should be fully invoiced.
        """
        # intial so
        self.partner = self.env.ref('base.res_partner_1')
        self.product = self.env.ref('product.product_delivery_01')
        so_vals = {
            'partner_id': self.partner.id,
            'partner_invoice_id': self.partner.id,
            'partner_shipping_id': self.partner.id,
            'order_line': [(0, 0, {
                'name': self.product.name,
                'product_id': self.product.id,
                'product_uom_qty': 5.0,
                'product_uom': self.product.uom_id.id,
                'price_unit': self.product.list_price})],
            'pricelist_id': self.env.ref('product.list0').id,
        }
        self.so = self.env['sale.order'].create(so_vals)

        # confirm our standard so, check the picking
        self.so.action_confirm()
        self.assertTrue(self.so.picking_ids, 'Sale Stock: no picking created for "invoice on delivery" storable products')

        # invoice in on delivery, nothing should be invoiced
        self.assertEqual(self.so.invoice_status, 'no', 'Sale Stock: so invoice_status should be "nothing to invoice"')

        # deliver partially
        pick = self.so.picking_ids
        pick.move_lines.write({'quantity_done': 4})
        res_dict = pick.button_validate()
        wizard = self.env[(res_dict.get('res_model'))].browse(res_dict.get('res_id'))
        wizard.process_cancel_backorder()

        # Check quantity delivered
        del_qty = sum(sol.qty_delivered for sol in self.so.order_line)
        self.assertEqual(del_qty, 4.0, 'Sale Stock: delivered quantity should be 4.0 after partial delivery')

        # Check invoice
        self.assertEqual(self.so.invoice_status, 'to invoice', 'Sale Stock: so invoice_status should be "to invoice" before invoicing')
        self.inv_1 = self.so._create_invoices()
        self.assertEqual(self.so.invoice_status, 'no', 'Sale Stock: so invoice_status should be "no" after invoicing')
        self.assertEqual(len(self.inv_1), 1, 'Sale Stock: only one invoice should be created')
        self.assertEqual(self.inv_1.amount_untaxed, self.inv_1.amount_untaxed, 'Sale Stock: amount in SO and invoice should be the same')

        self.so.action_done()
        self.assertEqual(self.so.invoice_status, 'invoiced', 'Sale Stock: so invoice_status should be "invoiced" when set to done')

    def test_04_create_picking_update_saleorderline(self):
        """
        Test that updating multiple sale order lines after a successful delivery creates a single picking containing
        the new move lines.
        """
        # sell two products
        item1 = self.products['prod_order']  # consumable
        item1.type = 'consu'
        item2 = self.products['prod_del']    # storable

        self.so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                (0, 0, {'name': item1.name, 'product_id': item1.id, 'product_uom_qty': 1, 'product_uom': item1.uom_id.id, 'price_unit': item1.list_price}),
                (0, 0, {'name': item2.name, 'product_id': item2.id, 'product_uom_qty': 1, 'product_uom': item2.uom_id.id, 'price_unit': item2.list_price}),
            ],
        })
        self.so.action_confirm()

        # deliver them
        # One of the move is for a consumable product, thus is assigned. The second one is for a
        # storable product, thus is unavailable. Hitting `button_validate` will first ask to
        # process all the reserved quantities and, if the user chose to process, a second wizard
        # will ask to create a backorder for the unavailable product.
        self.assertEquals(len(self.so.picking_ids), 1)
        res_dict = self.so.picking_ids.sorted()[0].button_validate()
        wizard = self.env[(res_dict.get('res_model'))].browse(res_dict.get('res_id'))
        self.assertEqual(wizard._name, 'stock.immediate.transfer')
        res_dict = wizard.process()
        wizard = self.env[(res_dict.get('res_model'))].browse(res_dict.get('res_id'))
        self.assertEqual(wizard._name, 'stock.backorder.confirmation')
        wizard.process()

        # Now, the original picking is done and there is a new one (the backorder).
        self.assertEquals(len(self.so.picking_ids), 2)
        for picking in self.so.picking_ids:
            move = picking.move_lines
            if picking.backorder_id:
                self.assertEqual(move.product_id.id, item2.id)
                self.assertEqual(move.state, 'confirmed')
            else:
                self.assertEqual(picking.move_lines.product_id.id, item1.id)
                self.assertEqual(move.state, 'done')

        # update the two original sale order lines
        self.so.write({
            'order_line': [
                (1, self.so.order_line.sorted()[0].id, {'product_uom_qty': 2}),
                (1, self.so.order_line.sorted()[1].id, {'product_uom_qty': 2}),
            ]
        })
        # a single picking should be created for the new delivery
        self.assertEquals(len(self.so.picking_ids), 2)
        backorder = self.so.picking_ids.filtered(lambda p: p.backorder_id)
        self.assertEqual(len(backorder.move_lines), 2)
        for backorder_move in backorder.move_lines:
            if backorder_move.product_id.id == item1.id:
                self.assertEqual(backorder_move.product_qty, 1)
            elif backorder_move.product_id.id == item2.id:
                self.assertEqual(backorder_move.product_qty, 2)

        # add a new sale order lines
        self.so.write({
            'order_line': [
                (0, 0, {'name': item1.name, 'product_id': item1.id, 'product_uom_qty': 1, 'product_uom': item1.uom_id.id, 'price_unit': item1.list_price}),
            ]
        })
        self.assertEqual(sum(backorder.move_lines.filtered(lambda m: m.product_id.id == item1.id).mapped('product_qty')), 2)

    def test_05_create_picking_update_saleorderline(self):
        """ Same test than test_04 but only with enough products in stock so that the reservation
        is successful.
        """
        # sell two products
        item1 = self.products['prod_order']  # consumable
        item2 = self.products['prod_del']    # storable

        self.env['stock.quant']._update_available_quantity(item2, self.env.ref('stock.stock_location_stock'), 2)
        self.so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                (0, 0, {'name': item1.name, 'product_id': item1.id, 'product_uom_qty': 1, 'product_uom': item1.uom_id.id, 'price_unit': item1.list_price}),
                (0, 0, {'name': item2.name, 'product_id': item2.id, 'product_uom_qty': 1, 'product_uom': item2.uom_id.id, 'price_unit': item2.list_price}),
            ],
        })
        self.so.action_confirm()

        # deliver them
        self.assertEquals(len(self.so.picking_ids), 1)
        res_dict = self.so.picking_ids.sorted()[0].button_validate()
        wizard = self.env[(res_dict.get('res_model'))].browse(res_dict.get('res_id'))
        wizard.process()
        self.assertEquals(self.so.picking_ids.sorted()[0].state, "done")

        # update the two original sale order lines
        self.so.write({
            'order_line': [
                (1, self.so.order_line.sorted()[0].id, {'product_uom_qty': 2}),
                (1, self.so.order_line.sorted()[1].id, {'product_uom_qty': 2}),
            ]
        })
        # a single picking should be created for the new delivery
        self.assertEquals(len(self.so.picking_ids), 2)

    def test_05_confirm_cancel_confirm(self):
        """ Confirm a sale order, cancel it, set to quotation, change the
        partner, confirm it again: the second delivery order should have
        the new partner.
        """
        item1 = self.products['prod_order']
        partner1 = self.partner.id
        partner2 = self.env.ref('base.res_partner_2').id
        so1 = self.env['sale.order'].create({
            'partner_id': partner1,
            'order_line': [(0, 0, {
                'name': item1.name,
                'product_id': item1.id,
                'product_uom_qty': 1,
                'product_uom': item1.uom_id.id,
                'price_unit': item1.list_price,
            })],
        })
        so1.action_confirm()
        self.assertEqual(len(so1.picking_ids), 1)
        self.assertEqual(so1.picking_ids.partner_id.id, partner1)
        so1.action_cancel()
        so1.action_draft()
        so1.partner_id = partner2
        so1.partner_shipping_id = partner2  # set by an onchange
        so1.action_confirm()
        self.assertEqual(len(so1.picking_ids), 2)
        picking2 = so1.picking_ids.filtered(lambda p: p.state != 'cancel')
        self.assertEqual(picking2.partner_id.id, partner2)

    def test_06_uom(self):
        """ Sell a dozen of products stocked in units. Check that the quantities on the sale order
        lines as well as the delivered quantities are handled in dozen while the moves themselves
        are handled in units. Edit the ordered quantities, check that the quantites are correctly
        updated on the moves. Edit the ir.config_parameter to propagate the uom of the sale order
        lines to the moves and edit a last time the ordered quantities. Deliver, check the
        quantities.
        """
        uom_unit = self.env.ref('uom.product_uom_unit')
        uom_dozen = self.env.ref('uom.product_uom_dozen')
        item1 = self.products['prod_order']

        self.assertEqual(item1.uom_id.id, uom_unit.id)

        # sell a dozen
        so1 = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'name': item1.name,
                'product_id': item1.id,
                'product_uom_qty': 1,
                'product_uom': uom_dozen.id,
                'price_unit': item1.list_price,
            })],
        })
        so1.action_confirm()

        # the move should be 12 units
        # note: move.product_qty = computed field, always in the uom of the quant
        #       move.product_uom_qty = stored field representing the initial demand in move.product_uom
        move1 = so1.picking_ids.move_lines[0]
        self.assertEqual(move1.product_uom_qty, 12)
        self.assertEqual(move1.product_uom.id, uom_unit.id)
        self.assertEqual(move1.product_qty, 12)

        # edit the so line, sell 2 dozen, the move should now be 24 units
        so1.write({
            'order_line': [
                (1, so1.order_line.id, {'product_uom_qty': 2}),
            ]
        })
        # The above will create a second move, and then the two moves will be merged in _merge_moves`
        # The picking moves are not well sorted because the new move has just been created, and this influences the resulting move,
        # in which move the twos are merged.
        # But, this doesn't seem really important which is the resulting move, but in this test we have to ensure
        # we use the resulting move to compare the qty.
        # ```
        # for moves in moves_to_merge:
        #     # link all move lines to record 0 (the one we will keep).
        #     moves.mapped('move_line_ids').write({'move_id': moves[0].id})
        #     # merge move data
        #     moves[0].write(moves._merge_moves_fields())
        #     # update merged moves dicts
        #     moves_to_unlink |= moves[1:]
        # ```
        move1 = so1.picking_ids.move_lines[0]
        self.assertEqual(move1.product_uom_qty, 24)
        self.assertEqual(move1.product_uom.id, uom_unit.id)
        self.assertEqual(move1.product_qty, 24)

        # force the propagation of the uom, sell 3 dozen
        self.env['ir.config_parameter'].sudo().set_param('stock.propagate_uom', '1')
        so1.write({
            'order_line': [
                (1, so1.order_line.id, {'product_uom_qty': 3}),
            ]
        })
        move2 = so1.picking_ids.move_lines.filtered(lambda m: m.product_uom.id == uom_dozen.id)
        self.assertEqual(move2.product_uom_qty, 1)
        self.assertEqual(move2.product_uom.id, uom_dozen.id)
        self.assertEqual(move2.product_qty, 12)

        # deliver everything
        move1.quantity_done = 24
        move2.quantity_done = 1
        so1.picking_ids.button_validate()

        # check the delivered quantity
        self.assertEqual(so1.order_line.qty_delivered, 3.0)

    def test_07_forced_qties(self):
        """ Make multiple sale order lines of the same product which isn't available in stock. On
        the picking, create new move lines (through the detailed operations view). See that the move
        lines are correctly dispatched through the moves.
        """
        uom_unit = self.env.ref('uom.product_uom_unit')
        uom_dozen = self.env.ref('uom.product_uom_dozen')
        item1 = self.products['prod_order']

        self.assertEqual(item1.uom_id.id, uom_unit.id)

        # sell a dozen
        so1 = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                (0, 0, {
                    'name': item1.name,
                    'product_id': item1.id,
                    'product_uom_qty': 1,
                    'product_uom': uom_dozen.id,
                    'price_unit': item1.list_price,
                }),
                (0, 0, {
                    'name': item1.name,
                    'product_id': item1.id,
                    'product_uom_qty': 1,
                    'product_uom': uom_dozen.id,
                    'price_unit': item1.list_price,
                }),
                (0, 0, {
                    'name': item1.name,
                    'product_id': item1.id,
                    'product_uom_qty': 1,
                    'product_uom': uom_dozen.id,
                    'price_unit': item1.list_price,
                }),
            ],
        })
        so1.action_confirm()

        self.assertEqual(len(so1.picking_ids.move_lines), 3)
        so1.picking_ids.write({
            'move_line_ids': [
                (0, 0, {
                    'product_id': item1.id,
                    'product_uom_qty': 0,
                    'qty_done': 1,
                    'product_uom_id': uom_dozen.id,
                    'location_id': so1.picking_ids.location_id.id,
                    'location_dest_id': so1.picking_ids.location_dest_id.id,
                }),
                (0, 0, {
                    'product_id': item1.id,
                    'product_uom_qty': 0,
                    'qty_done': 1,
                    'product_uom_id': uom_dozen.id,
                    'location_id': so1.picking_ids.location_id.id,
                    'location_dest_id': so1.picking_ids.location_dest_id.id,
                }),
                (0, 0, {
                    'product_id': item1.id,
                    'product_uom_qty': 0,
                    'qty_done': 1,
                    'product_uom_id': uom_dozen.id,
                    'location_id': so1.picking_ids.location_id.id,
                    'location_dest_id': so1.picking_ids.location_dest_id.id,
                }),
            ],
        })
        so1.picking_ids.button_validate()
        self.assertEqual(so1.picking_ids.state, 'done')
        self.assertEqual(so1.order_line.mapped('qty_delivered'), [1, 1, 1])

    def test_08_quantities(self):
        """Change the picking code of the receipts to internal. Make a SO for 10 units, go to the
        picking and return 5, edit the SO line to 15 units.

        The purpose of the test is to check the consistencies across the delivered quantities and the
        procurement quantities.
        """
        # Change the code of the picking type receipt
        self.env['stock.picking.type'].search([('code', '=', 'incoming')]).write({'code': 'internal'})

        # Sell and deliver 10 units
        item1 = self.products['prod_order']
        uom_unit = self.env.ref('uom.product_uom_unit')
        so1 = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                (0, 0, {
                    'name': item1.name,
                    'product_id': item1.id,
                    'product_uom_qty': 10,
                    'product_uom': uom_unit.id,
                    'price_unit': item1.list_price,
                }),
            ],
        })
        so1.action_confirm()

        picking = so1.picking_ids
        wiz_act = picking.button_validate()
        wiz = self.env[wiz_act['res_model']].browse(wiz_act['res_id'])
        wiz.process()

        # Return 5 units
        stock_return_picking_form = Form(self.env['stock.return.picking'].with_context(
            active_ids=picking.ids,
            active_id=picking.sorted().ids[0],
            active_model='stock.picking'
        ))
        return_wiz = stock_return_picking_form.save()
        for return_move in return_wiz.product_return_moves:
            return_move.write({
                'quantity': 5,
                'to_refund': True
            })
        res = return_wiz.create_returns()
        return_pick = self.env['stock.picking'].browse(res['res_id'])
        wiz_act = return_pick.button_validate()
        wiz = self.env[wiz_act['res_model']].browse(wiz_act['res_id'])
        wiz.process()

        self.assertEqual(so1.order_line.qty_delivered, 5)

        # Deliver 15 instead of 10.
        so1.write({
            'order_line': [
                (1, so1.order_line.sorted()[0].id, {'product_uom_qty': 15}),
            ]
        })

        # A new move of 10 unit (15 - 5 units)
        self.assertEqual(so1.order_line.qty_delivered, 5)
        self.assertEqual(so1.picking_ids[-1].move_lines.product_qty, 10)

    def test_09_qty_available(self):
        """ create a sale order in warehouse1, change to warehouse2 and check the
        available quantities on sale order lines are well updated """
        # sell two products
        item1 = self.products['prod_order']
        item1.type = 'product'
        warehouse1 = self.env.ref('stock.warehouse0')
        self.env['stock.quant']._update_available_quantity(item1, warehouse1.lot_stock_id, 10)
        self.env['stock.quant']._update_reserved_quantity(item1, warehouse1.lot_stock_id, 3)
        warehouse2 = self.env['stock.warehouse'].create({
            'partner_id': self.env.ref('base.main_partner').id,
            'code': 'Test',
        })
        self.env['stock.quant']._update_available_quantity(item1, warehouse2.lot_stock_id, 5)
        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                (0, 0, {'name': item1.name, 'product_id': item1.id, 'product_uom_qty': 1, 'product_uom': item1.uom_id.id, 'price_unit': item1.list_price}),
            ],
        })
        line = so.order_line[0]
        self.assertAlmostEqual(line.scheduled_date, datetime.now(), delta=timedelta(seconds=10))
        self.assertEqual(line.virtual_available_at_date, 10)
        self.assertEqual(line.free_qty_today, 7)
        self.assertEqual(line.qty_available_today, 10)
        self.assertEqual(line.warehouse_id, warehouse1)
        self.assertEqual(line.qty_to_deliver, 1)
        so.warehouse_id = warehouse2
        # invalidate product cache to ensure qty_available is recomputed
        # bc warehouse isn't in the depends_context of qty_available
        line.product_id.invalidate_cache()
        self.assertEqual(line.virtual_available_at_date, 5)
        self.assertEqual(line.free_qty_today, 5)
        self.assertEqual(line.qty_available_today, 5)
        self.assertEqual(line.warehouse_id, warehouse2)
        self.assertEqual(line.qty_to_deliver, 1)

    def test_10_qty_available(self):
        """create a sale order containing three times the same product. The
        quantity available should be different for the 3 lines"""
        item1 = self.products['prod_order']
        item1.type = 'product'
        self.env['stock.quant']._update_available_quantity(item1, self.env.ref('stock.stock_location_stock'), 10)
        so = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                (0, 0, {'name': item1.name, 'product_id': item1.id, 'product_uom_qty': 5, 'product_uom': item1.uom_id.id, 'price_unit': item1.list_price}),
                (0, 0, {'name': item1.name, 'product_id': item1.id, 'product_uom_qty': 5, 'product_uom': item1.uom_id.id, 'price_unit': item1.list_price}),
                (0, 0, {'name': item1.name, 'product_id': item1.id, 'product_uom_qty': 5, 'product_uom': item1.uom_id.id, 'price_unit': item1.list_price}),
            ],
        })
        self.assertEqual(so.order_line.mapped('free_qty_today'), [10, 5, 0])

    def test_11_return_with_refund(self):
        """ Creates a sale order, valids it and its delivery, then creates a
        return. The return must refund by default and the sale order delivered
        quantity must be updated.
        """
        # Creates a sale order for 10 products.
        sale_order = self._get_new_sale_order()
        # Valids the sale order, then valids the delivery.
        sale_order.action_confirm()
        self.assertTrue(sale_order.picking_ids)
        self.assertEqual(sale_order.order_line.qty_delivered, 0)
        picking = sale_order.picking_ids
        picking.move_lines.write({'quantity_done': 10})
        picking.button_validate()

        # Checks the delivery amount (must be 10).
        self.assertEqual(sale_order.order_line.qty_delivered, 10)
        # Creates a return from the delivery picking.
        return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=picking.ids, active_id=picking.id,
            active_model='stock.picking'))
        return_wizard = return_picking_form.save()
        # Checks the field `to_refund` is checked (must be checked by default).
        self.assertEqual(return_wizard.product_return_moves.to_refund, True)
        self.assertEqual(return_wizard.product_return_moves.quantity, 10)

        # Valids the return picking.
        res = return_wizard.create_returns()
        return_picking = self.env['stock.picking'].browse(res['res_id'])
        return_picking.move_lines.write({'quantity_done': 10})
        return_picking.button_validate()
        # Checks the delivery amount (must be 0).
        self.assertEqual(sale_order.order_line.qty_delivered, 0)

    def test_12_return_without_refund(self):
        """ Do the exact thing than in `test_11_return_with_refund` except we
        set on False the refund and checks the sale order delivered quantity
        isn't changed.
        """
        # Creates a sale order for 10 products.
        sale_order = self._get_new_sale_order()
        # Valids the sale order, then valids the delivery.
        sale_order.action_confirm()
        self.assertTrue(sale_order.picking_ids)
        self.assertEqual(sale_order.order_line.qty_delivered, 0)
        picking = sale_order.picking_ids
        picking.move_lines.write({'quantity_done': 10})
        picking.button_validate()

        # Checks the delivery amount (must be 10).
        self.assertEqual(sale_order.order_line.qty_delivered, 10)
        # Creates a return from the delivery picking.
        return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=picking.ids, active_id=picking.id,
            active_model='stock.picking'))
        return_wizard = return_picking_form.save()
        # Checks the field `to_refund` is checked, then unchecks it.
        self.assertEqual(return_wizard.product_return_moves.to_refund, True)
        self.assertEqual(return_wizard.product_return_moves.quantity, 10)
        return_wizard.product_return_moves.to_refund = False
        # Valids the return picking.
        res = return_wizard.create_returns()
        return_picking = self.env['stock.picking'].browse(res['res_id'])
        return_picking.move_lines.write({'quantity_done': 10})
        return_picking.button_validate()
        # Checks the delivery amount (must still be 10).
        self.assertEqual(sale_order.order_line.qty_delivered, 10)
