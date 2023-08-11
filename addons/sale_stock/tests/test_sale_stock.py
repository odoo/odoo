# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, timedelta

from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCommon
from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.exceptions import UserError
from odoo.tests import Form, tagged


@tagged('post_install', '-at_install')
class TestSaleStock(TestSaleCommon, ValuationReconciliationTestCommon):

    def _get_new_sale_order(self, amount=10.0, product=False):
        """ Creates and returns a sale order with one default order line.

        :param float amount: quantity of product for the order line (10 by default)
        """
        product = product or self.company_data['product_delivery_no']
        sale_order_vals = {
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'order_line': [(0, 0, {
                'name': product.name,
                'product_id': product.id,
                'product_uom_qty': amount,
                'product_uom': product.uom_id.id,
                'price_unit': product.list_price})],
            'pricelist_id': self.company_data['default_pricelist'].id,
        }
        sale_order = self.env['sale.order'].create(sale_order_vals)
        return sale_order

    def test_00_sale_stock_invoice(self):
        """
        Test SO's changes when playing around with stock moves, quants, pack operations, pickings
        and whatever other model there is in stock with "invoice on delivery" products
        """
        self.so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': p.name,
                    'product_id': p.id,
                    'product_uom_qty': 2,
                    'product_uom': p.uom_id.id,
                    'price_unit': p.list_price,
                }) for p in (
                    self.company_data['product_order_no'],
                    self.company_data['product_service_delivery'],
                    self.company_data['product_service_order'],
                    self.company_data['product_delivery_no'],
                )],
            'pricelist_id': self.company_data['default_pricelist'].id,
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
        pick.move_ids.write({'quantity_done': 1})
        wiz_act = pick.button_validate()
        wiz = Form(self.env[wiz_act['res_model']].with_context(wiz_act['context'])).save()
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
        pick_2.move_ids.write({'quantity_done': 1})
        self.assertTrue(pick_2.button_validate(), 'Sale Stock: second picking should be final without need for a backorder')
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
        self.env.flush_all()
        self.env.invalidate_all()

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
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'order_line': [(0, 0, {
                'name': p.name,
                'product_id': p.id,
                'product_uom_qty': 2,
                'product_uom': p.uom_id.id,
                'price_unit': p.list_price,
                }) for p in (
                    self.company_data['product_order_no'],
                    self.company_data['product_service_delivery'],
                    self.company_data['product_service_order'],
                    self.company_data['product_delivery_no'],
                )],
            'pricelist_id': self.company_data['default_pricelist'].id,
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

        advance_product = self.env['product.product'].create({
            'name': 'Deposit',
            'type': 'service',
            'invoice_policy': 'order',
        })
        adv_wiz = self.env['sale.advance.payment.inv'].with_context(active_ids=[self.so.id]).create({
            'advance_payment_method': 'percentage',
            'amount': 5.0,
            'product_id': advance_product.id,
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
        pick.move_ids.write({'quantity_done': 2})
        self.assertTrue(pick.button_validate(), 'Sale Stock: complete delivery should not need a backorder')
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
        self.product = self.company_data['product_delivery_no']
        so_vals = {
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'order_line': [(0, 0, {
                'name': self.product.name,
                'product_id': self.product.id,
                'product_uom_qty': 5.0,
                'product_uom': self.product.uom_id.id,
                'price_unit': self.product.list_price})],
            'pricelist_id': self.company_data['default_pricelist'].id,
        }
        self.so = self.env['sale.order'].create(so_vals)

        # confirm our standard so, check the picking
        self.so.action_confirm()
        self.assertTrue(self.so.picking_ids, 'Sale Stock: no picking created for "invoice on delivery" storable products')

        # invoice in on delivery, nothing should be invoiced
        self.assertEqual(self.so.invoice_status, 'no', 'Sale Stock: so invoice_status should be "no" instead of "%s".' % self.so.invoice_status)

        # deliver completely
        pick = self.so.picking_ids
        pick.move_ids.write({'quantity_done': 5})
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
        self.inv_1.action_post()

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
        return_pick.move_ids.write({'quantity_done': 2})
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
        self.product = self.company_data['product_delivery_no']
        so_vals = {
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'order_line': [(0, 0, {
                'name': self.product.name,
                'product_id': self.product.id,
                'product_uom_qty': 5.0,
                'product_uom': self.product.uom_id.id,
                'price_unit': self.product.list_price})],
            'pricelist_id': self.company_data['default_pricelist'].id,
        }
        self.so = self.env['sale.order'].create(so_vals)

        # confirm our standard so, check the picking
        self.so.action_confirm()
        self.assertTrue(self.so.picking_ids, 'Sale Stock: no picking created for "invoice on delivery" storable products')

        # invoice in on delivery, nothing should be invoiced
        self.assertEqual(self.so.invoice_status, 'no', 'Sale Stock: so invoice_status should be "nothing to invoice"')

        # deliver partially
        pick = self.so.picking_ids
        pick.move_ids.write({'quantity_done': 4})
        res_dict = pick.button_validate()
        wizard = Form(self.env[(res_dict.get('res_model'))].with_context(res_dict['context'])).save()
        wizard.process_cancel_backorder()

        #Check Exception error is logged on SO
        activity = self.env['mail.activity'].search([('res_id', '=', self.so.id), ('res_model', '=', 'sale.order')])
        self.assertEqual(len(activity), 1, 'When no backorder is created for a partial delivery, a warning error should be logged in its origin SO')

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
        item1 = self.company_data['product_order_no']  # consumable
        item1.type = 'consu'
        item2 = self.company_data['product_delivery_no']    # storable
        item2.type = 'product'    # storable

        self.so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
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
        self.assertEqual(len(self.so.picking_ids), 1)
        res_dict = self.so.picking_ids.sorted()[0].button_validate()
        wizard = Form(self.env[(res_dict.get('res_model'))].with_context(res_dict['context'])).save()
        self.assertEqual(wizard._name, 'stock.immediate.transfer')
        res_dict = wizard.process()
        wizard = Form(self.env[(res_dict.get('res_model'))].with_context(res_dict['context'])).save()
        self.assertEqual(wizard._name, 'stock.backorder.confirmation')
        wizard.process()

        # Now, the original picking is done and there is a new one (the backorder).
        self.assertEqual(len(self.so.picking_ids), 2)
        for picking in self.so.picking_ids:
            move = picking.move_ids
            if picking.backorder_id:
                self.assertEqual(move.product_id.id, item2.id)
                self.assertEqual(move.state, 'confirmed')
            else:
                self.assertEqual(picking.move_ids.product_id.id, item1.id)
                self.assertEqual(move.state, 'done')

        # update the two original sale order lines
        self.so.write({
            'order_line': [
                (1, self.so.order_line.sorted()[0].id, {'product_uom_qty': 2}),
                (1, self.so.order_line.sorted()[1].id, {'product_uom_qty': 2}),
            ]
        })
        # a single picking should be created for the new delivery
        self.assertEqual(len(self.so.picking_ids), 2)
        backorder = self.so.picking_ids.filtered(lambda p: p.backorder_id)
        self.assertEqual(len(backorder.move_ids), 2)
        for backorder_move in backorder.move_ids:
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
        self.assertEqual(sum(backorder.move_ids.filtered(lambda m: m.product_id.id == item1.id).mapped('product_qty')), 2)

    def test_05_create_picking_update_saleorderline(self):
        """ Same test than test_04 but only with enough products in stock so that the reservation
        is successful.
        """
        # sell two products
        item1 = self.company_data['product_order_no']  # consumable
        item1.type = 'consu'  # consumable
        item2 = self.company_data['product_delivery_no']    # storable
        item2.type = 'product'    # storable

        self.env['stock.quant']._update_available_quantity(item2, self.company_data['default_warehouse'].lot_stock_id, 2)
        self.so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {'name': item1.name, 'product_id': item1.id, 'product_uom_qty': 1, 'product_uom': item1.uom_id.id, 'price_unit': item1.list_price}),
                (0, 0, {'name': item2.name, 'product_id': item2.id, 'product_uom_qty': 1, 'product_uom': item2.uom_id.id, 'price_unit': item2.list_price}),
            ],
        })
        self.so.action_confirm()

        # deliver them
        self.assertEqual(len(self.so.picking_ids), 1)
        res_dict = self.so.picking_ids.sorted()[0].button_validate()
        wizard = Form(self.env[(res_dict.get('res_model'))].with_context(res_dict['context'])).save()
        wizard.process()
        self.assertEqual(self.so.picking_ids.sorted()[0].state, "done")

        # update the two original sale order lines
        self.so.write({
            'order_line': [
                (1, self.so.order_line.sorted()[0].id, {'product_uom_qty': 2}),
                (1, self.so.order_line.sorted()[1].id, {'product_uom_qty': 2}),
            ]
        })
        # a single picking should be created for the new delivery
        self.assertEqual(len(self.so.picking_ids), 2)

    def test_05_confirm_cancel_confirm(self):
        """ Confirm a sale order, cancel it, set to quotation, change the
        partner, confirm it again: the second delivery order should have
        the new partner.
        """
        item1 = self.company_data['product_order_no']
        partner1 = self.partner_a.id
        partner2 = self.env['res.partner'].create({'name': 'Another Test Partner'})
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
        so1._action_cancel()
        so1.action_draft()
        so1.partner_id = partner2
        so1.partner_shipping_id = partner2  # set by an onchange
        so1.action_confirm()
        self.assertEqual(len(so1.picking_ids), 2)
        picking2 = so1.picking_ids.filtered(lambda p: p.state != 'cancel')
        self.assertEqual(picking2.partner_id.id, partner2.id)

    def test_06_uom(self):
        """ Sell a dozen of products stocked in units. Check that the quantities on the sale order
        lines as well as the delivered quantities are handled in dozen while the moves themselves
        are handled in units. Edit the ordered quantities, check that the quantities are correctly
        updated on the moves. Edit the ir.config_parameter to propagate the uom of the sale order
        lines to the moves and edit a last time the ordered quantities. Deliver, check the
        quantities.
        """
        uom_unit = self.env.ref('uom.product_uom_unit')
        uom_dozen = self.env.ref('uom.product_uom_dozen')
        item1 = self.company_data['product_order_no']

        self.assertEqual(item1.uom_id.id, uom_unit.id)

        # sell a dozen
        so1 = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
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
        move1 = so1.picking_ids.move_ids[0]
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
        move1 = so1.picking_ids.move_ids[0]
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
        move2 = so1.picking_ids.move_ids.filtered(lambda m: m.product_uom.id == uom_dozen.id)
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
        item1 = self.company_data['product_order_no']

        self.assertEqual(item1.uom_id.id, uom_unit.id)

        # sell a dozen
        so1 = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
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

        self.assertEqual(len(so1.picking_ids.move_ids), 3)
        so1.picking_ids.write({
            'move_line_ids': [
                (0, 0, {
                    'product_id': item1.id,
                    'reserved_uom_qty': 0,
                    'qty_done': 1,
                    'product_uom_id': uom_dozen.id,
                    'location_id': so1.picking_ids.location_id.id,
                    'location_dest_id': so1.picking_ids.location_dest_id.id,
                }),
                (0, 0, {
                    'product_id': item1.id,
                    'reserved_uom_qty': 0,
                    'qty_done': 1,
                    'product_uom_id': uom_dozen.id,
                    'location_id': so1.picking_ids.location_id.id,
                    'location_dest_id': so1.picking_ids.location_dest_id.id,
                }),
                (0, 0, {
                    'product_id': item1.id,
                    'reserved_uom_qty': 0,
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
        item1 = self.company_data['product_order_no']
        uom_unit = self.env.ref('uom.product_uom_unit')
        so1 = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
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
        wiz = Form(self.env[wiz_act['res_model']].with_context(wiz_act['context'])).save()
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
        wiz = Form(self.env[wiz_act['res_model']].with_context(wiz_act['context'])).save()
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
        self.assertEqual(so1.picking_ids.sorted('id')[-1].move_ids.product_qty, 10)

    def test_09_qty_available(self):
        """ create a sale order in warehouse1, change to warehouse2 and check the
        available quantities on sale order lines are well updated """
        # sell two products
        item1 = self.company_data['product_order_no']
        item1.type = 'product'

        warehouse1 = self.company_data['default_warehouse']
        self.env['stock.quant']._update_available_quantity(item1, warehouse1.lot_stock_id, 10)
        self.env['stock.quant']._update_reserved_quantity(item1, warehouse1.lot_stock_id, 3)

        warehouse2 = self.env['stock.warehouse'].create({
            'partner_id': self.partner_a.id,
            'name': 'Zizizatestwarehouse',
            'code': 'Test',
        })
        self.env['stock.quant']._update_available_quantity(item1, warehouse2.lot_stock_id, 5)
        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
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
        self.env.invalidate_all()
        self.assertEqual(line.virtual_available_at_date, 5)
        self.assertEqual(line.free_qty_today, 5)
        self.assertEqual(line.qty_available_today, 5)
        self.assertEqual(line.warehouse_id, warehouse2)
        self.assertEqual(line.qty_to_deliver, 1)

    def test_10_qty_available(self):
        """create a sale order containing three times the same product. The
        quantity available should be different for the 3 lines"""
        item1 = self.company_data['product_order_no']
        item1.type = 'product'
        self.env['stock.quant']._update_available_quantity(item1, self.company_data['default_warehouse'].lot_stock_id, 10)
        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
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
        picking.move_ids.write({'quantity_done': 10})
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
        return_picking.move_ids.write({'quantity_done': 10})
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
        picking.move_ids.write({'quantity_done': 10})
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
        return_picking.move_ids.write({'quantity_done': 10})
        return_picking.button_validate()
        # Checks the delivery amount (must still be 10).
        self.assertEqual(sale_order.order_line.qty_delivered, 10)

    def test_13_delivered_qty(self):
        """ Creates a sale order, valids it and adds a new move line in the delivery for a
        product with an invoicing policy on 'order', then checks a new SO line was created.
        After that, creates a second sale order and does the same thing but with a product
        with and invoicing policy on 'ordered'.
        """
        product_inv_on_delivered = self.company_data['product_delivery_no']
        # Configure a product with invoicing policy on order.
        product_inv_on_order = self.env['product.product'].create({
            'name': 'Shenaniffluffy',
            'type': 'consu',
            'invoice_policy': 'order',
            'list_price': 55.0,
        })
        # Creates a sale order for 3 products invoiced on qty. delivered.
        sale_order = self._get_new_sale_order(amount=3)
        # Confirms the sale order, then increases the delivered qty., adds a new
        # line and valids the delivery.
        sale_order.action_confirm()
        self.assertTrue(sale_order.picking_ids)
        self.assertEqual(len(sale_order.order_line), 1)
        self.assertEqual(sale_order.order_line.qty_delivered, 0)
        picking = sale_order.picking_ids
        initial_product = sale_order.order_line.product_id

        picking_form = Form(picking)
        with picking_form.move_line_ids_without_package.edit(0) as move:
            move.qty_done = 5
        with picking_form.move_line_ids_without_package.new() as new_move:
            new_move.product_id = product_inv_on_order
            new_move.qty_done = 5
        picking = picking_form.save()
        picking.button_validate()

        # Check a new sale order line was correctly created.
        self.assertEqual(len(sale_order.order_line), 2)
        so_line_1 = sale_order.order_line[0]
        so_line_2 = sale_order.order_line[1]
        self.assertEqual(so_line_1.product_id.id, product_inv_on_delivered.id)
        self.assertEqual(so_line_1.product_uom_qty, 3)
        self.assertEqual(so_line_1.qty_delivered, 5)
        self.assertEqual(so_line_1.price_unit, 70.0)
        self.assertEqual(so_line_2.product_id.id, product_inv_on_order.id)
        self.assertEqual(so_line_2.product_uom_qty, 0)
        self.assertEqual(so_line_2.qty_delivered, 5)
        self.assertEqual(
            so_line_2.price_unit, 0,
            "Shouldn't get the product price as the invoice policy is on qty. ordered")

        # Check the picking didn't change
        self.assertRecordValues(sale_order.picking_ids.move_ids, [
            {'product_id': initial_product.id, 'quantity_done': 5},
            {'product_id': product_inv_on_order.id, 'quantity_done': 5},
        ])

        # Creates a second sale order for 3 product invoiced on qty. ordered.
        sale_order = self._get_new_sale_order(product=product_inv_on_order, amount=3)
        # Confirms the sale order, then increases the delivered qty., adds a new
        # line and valids the delivery.
        sale_order.action_confirm()
        self.assertTrue(sale_order.picking_ids)
        self.assertEqual(len(sale_order.order_line), 1)
        self.assertEqual(sale_order.order_line.qty_delivered, 0)
        picking = sale_order.picking_ids

        picking_form = Form(picking)
        with picking_form.move_line_ids_without_package.edit(0) as move:
            move.qty_done = 5
        with picking_form.move_line_ids_without_package.new() as new_move:
            new_move.product_id = product_inv_on_delivered
            new_move.qty_done = 5
        picking = picking_form.save()
        picking.button_validate()

        # Check a new sale order line was correctly created.
        self.assertEqual(len(sale_order.order_line), 2)
        so_line_1 = sale_order.order_line[0]
        so_line_2 = sale_order.order_line[1]
        self.assertEqual(so_line_1.product_id.id, product_inv_on_order.id)
        self.assertEqual(so_line_1.product_uom_qty, 3)
        self.assertEqual(so_line_1.qty_delivered, 5)
        self.assertEqual(so_line_1.price_unit, 55.0)
        self.assertEqual(so_line_2.product_id.id, product_inv_on_delivered.id)
        self.assertEqual(so_line_2.product_uom_qty, 0)
        self.assertEqual(so_line_2.qty_delivered, 5)
        self.assertEqual(
            so_line_2.price_unit, 70.0,
            "Should get the product price as the invoice policy is on qty. delivered")

    def test_14_delivered_qty_in_multistep(self):
        """ Creates a sale order with delivery in two-step. Process the pick &
        ship and check we don't have extra SO line. Then, do the same but with
        adding a extra move and check only one extra SO line was created.
        """
        # Set the delivery in two steps.
        warehouse = self.company_data['default_warehouse']
        warehouse.delivery_steps = 'pick_ship'
        # Configure a product with invoicing policy on order.
        product_inv_on_order = self.env['product.product'].create({
            'name': 'Shenaniffluffy',
            'type': 'consu',
            'invoice_policy': 'order',
            'list_price': 55.0,
        })
        # Create a sale order.
        sale_order = self._get_new_sale_order()
        # Confirms the sale order, then valids pick and delivery.
        sale_order.action_confirm()
        self.assertTrue(sale_order.picking_ids)
        self.assertEqual(len(sale_order.order_line), 1)
        self.assertEqual(sale_order.order_line.qty_delivered, 0)
        pick = sale_order.picking_ids.filtered(lambda p: p.picking_type_code == 'internal')
        delivery = sale_order.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing')

        picking_form = Form(pick)
        with picking_form.move_line_ids_without_package.edit(0) as move:
            move.qty_done = 10
        pick = picking_form.save()
        pick.button_validate()

        picking_form = Form(delivery)
        with picking_form.move_line_ids_without_package.edit(0) as move:
            move.qty_done = 10
        delivery = picking_form.save()
        delivery.button_validate()

        # Check no new sale order line was created.
        self.assertEqual(len(sale_order.order_line), 1)
        self.assertEqual(sale_order.order_line.product_uom_qty, 10)
        self.assertEqual(sale_order.order_line.qty_delivered, 10)
        self.assertEqual(sale_order.order_line.price_unit, 70.0)

        # Creates a second sale order.
        sale_order = self._get_new_sale_order()
        # Confirms the sale order then add a new line for an another product in the pick/out.
        sale_order.action_confirm()
        self.assertTrue(sale_order.picking_ids)
        self.assertEqual(len(sale_order.order_line), 1)
        self.assertEqual(sale_order.order_line.qty_delivered, 0)
        pick = sale_order.picking_ids.filtered(lambda p: p.picking_type_code == 'internal')
        delivery = sale_order.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing')

        picking_form = Form(pick)
        with picking_form.move_line_ids_without_package.edit(0) as move:
            move.qty_done = 10
        with picking_form.move_line_ids_without_package.new() as new_move:
            new_move.product_id = product_inv_on_order
            new_move.qty_done = 10
        pick = picking_form.save()
        pick.button_validate()

        picking_form = Form(delivery)
        with picking_form.move_line_ids_without_package.edit(0) as move:
            move.qty_done = 10
        with picking_form.move_line_ids_without_package.new() as new_move:
            new_move.product_id = product_inv_on_order
            new_move.qty_done = 10
        delivery = picking_form.save()
        delivery.button_validate()

        # Check a new sale order line was correctly created.
        self.assertEqual(len(sale_order.order_line), 2)
        so_line_1 = sale_order.order_line[0]
        so_line_2 = sale_order.order_line[1]
        self.assertEqual(so_line_1.product_id.id, self.company_data['product_delivery_no'].id)
        self.assertEqual(so_line_1.product_uom_qty, 10)
        self.assertEqual(so_line_1.qty_delivered, 10)
        self.assertEqual(so_line_1.price_unit, 70.0)
        self.assertEqual(so_line_2.product_id.id, product_inv_on_order.id)
        self.assertEqual(so_line_2.product_uom_qty, 0)
        self.assertEqual(so_line_2.qty_delivered, 10)
        self.assertEqual(so_line_2.price_unit, 0)

    def test_08_sale_return_qty_and_cancel(self):
        """
        Test a SO with a product on delivery with a 5 quantity.
        Create two invoices: one for 3 quantity and one for 2 quantity
        Then cancel Sale order, it won't raise any warning, it should be cancelled.
        """
        partner = self.partner_a
        product = self.company_data['product_delivery_no']
        so_vals = {
            'partner_id': partner.id,
            'partner_invoice_id': partner.id,
            'partner_shipping_id': partner.id,
            'order_line': [(0, 0, {
                'name': product.name,
                'product_id': product.id,
                'product_uom_qty': 5.0,
                'product_uom': product.uom_id.id,
                'price_unit': product.list_price})],
            'pricelist_id': self.company_data['default_pricelist'].id,
        }
        so = self.env['sale.order'].create(so_vals)

        # confirm the so
        so.action_confirm()

        # deliver partially
        pick = so.picking_ids
        pick.move_ids.write({'quantity_done': 3})

        wiz_act = pick.button_validate()
        wiz = Form(self.env[wiz_act['res_model']].with_context(wiz_act['context'])).save()
        wiz.process()

        # create invoice for 3 quantity and post it
        inv_1 = so._create_invoices()
        inv_1.action_post()
        self.assertEqual(inv_1.state, 'posted', 'invoice should be in posted state')

        pick_2 = so.picking_ids.filtered('backorder_id')
        pick_2.move_ids.write({'quantity_done': 2})
        pick_2.button_validate()

        # create invoice for remaining 2 quantity
        inv_2 = so._create_invoices()
        self.assertEqual(inv_2.state, 'draft', 'invoice should be in draft state')

        # check the status of invoices after cancelling the order
        so._action_cancel()
        wizard = self.env['sale.order.cancel'].with_context({'order_id': so.id}).create({'order_id': so.id})
        wizard.action_cancel()
        self.assertEqual(inv_1.state, 'posted', 'A posted invoice state should remain posted')
        self.assertEqual(inv_2.state, 'cancel', 'A drafted invoice state should be cancelled')

    def test_reservation_method_w_sale(self):
        picking_type_out = self.company_data['default_warehouse'].out_type_id
        # make sure generated picking will auto-assign
        picking_type_out.reservation_method = 'at_confirm'
        product = self.company_data['product_delivery_no']
        product.type = 'product'
        self.env['stock.quant']._update_available_quantity(product, self.company_data['default_warehouse'].lot_stock_id, 20)

        sale_order1 = self._get_new_sale_order(amount=10.0)
        # Validate the sale order, picking should automatically assign stock
        sale_order1.action_confirm()
        picking1 = sale_order1.picking_ids
        self.assertTrue(picking1)
        self.assertEqual(picking1.state, 'assigned')
        picking1.unlink()

        # make sure generated picking will does not auto-assign
        picking_type_out.reservation_method = 'manual'
        sale_order2 = self._get_new_sale_order(amount=10.0)
        # Validate the sale order, picking should not automatically assign stock
        sale_order2.action_confirm()
        picking2 = sale_order2.picking_ids
        self.assertTrue(picking2)
        self.assertEqual(picking2.state, 'confirmed')
        picking2.unlink()

        # make sure generated picking auto-assigns according to (picking) scheduled date
        picking_type_out.reservation_method = 'by_date'
        picking_type_out.reservation_days_before = 2
        # too early for scheduled date => don't auto-assign
        sale_order3 = self._get_new_sale_order(amount=10.0)
        sale_order3.commitment_date = datetime.now() + timedelta(days=10)
        sale_order3.action_confirm()
        picking3 = sale_order3.picking_ids
        self.assertTrue(picking3)
        self.assertEqual(picking3.state, 'confirmed')
        picking3.unlink()
        # within scheduled date + reservation days before => auto-assign
        sale_order4 = self._get_new_sale_order(amount=10.0)
        sale_order4.commitment_date = datetime.now() + timedelta(days=1)
        sale_order4.action_confirm()
        self.assertTrue(sale_order4.picking_ids)
        self.assertEqual(sale_order4.picking_ids.state, 'assigned')

    def test_packaging_propagation(self):
        """Create a SO with lines using packaging, check the packaging propagate
        to its move.
        """
        warehouse = self.company_data['default_warehouse']
        warehouse.delivery_steps = 'pick_pack_ship'
        product = self.env['product.product'].create({
            'name': 'Product with packaging',
            'type': 'product',
        })

        packOf10 = self.env['product.packaging'].create({
            'name': 'PackOf10',
            'product_id': product.id,
            'qty': 10
        })

        packOf20 = self.env['product.packaging'].create({
            'name': 'PackOf20',
            'product_id': product.id,
            'qty': 20
        })

        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'product_id': product.id,
                    'product_uom_qty': 10.0,
                    'product_uom': product.uom_id.id,
                    'product_packaging_id': packOf10.id,
                })],
        })
        so.action_confirm()
        pick = so.order_line.move_ids
        pack = pick.move_orig_ids
        ship = pack.move_orig_ids
        self.assertEqual(pick.product_packaging_id, packOf10)
        self.assertEqual(pack.product_packaging_id, packOf10)
        self.assertEqual(ship.product_packaging_id, packOf10)

        so.order_line[0].write({
            'product_packaging_id': packOf20.id,
            'product_uom_qty': 20
        })
        self.assertEqual(so.order_line.move_ids.product_packaging_id, packOf20)
        self.assertEqual(pick.product_packaging_id, packOf20)
        self.assertEqual(pack.product_packaging_id, packOf20)
        self.assertEqual(ship.product_packaging_id, packOf20)

        so.order_line[0].write({'product_packaging_id': False})
        self.assertFalse(pick.product_packaging_id)
        self.assertFalse(pack.product_packaging_id)
        self.assertFalse(ship.product_packaging_id)

    def test_15_cancel_delivery(self):
        """ Suppose the option "Lock Confirmed Sales" enabled and a product with the invoicing
        policy set to "Delivered quantities". When cancelling the delivery of such a product, the
        invoice status of the associated SO should be 'Nothing to Invoice'
        """
        group_auto_done = self.env.ref('sale.group_auto_done_setting')
        self.env.user.groups_id = [(4, group_auto_done.id)]

        product = self.product_a
        product.invoice_policy = 'delivery'
        partner = self.partner_a
        so = self.env['sale.order'].create({
            'partner_id': partner.id,
            'partner_invoice_id': partner.id,
            'partner_shipping_id': partner.id,
            'order_line': [(0, 0, {
                'name': product.name,
                'product_id': product.id,
                'product_uom_qty': 2,
                'product_uom': product.uom_id.id,
                'price_unit': product.list_price
            })],
            'pricelist_id': self.env.ref('product.list0').id,
        })
        so.action_confirm()
        self.assertEqual(so.state, 'done')
        so.picking_ids.action_cancel()

        self.assertEqual(so.invoice_status, 'no')

    def test_16_multi_uom(self):
        yards_uom = self.env['uom.uom'].create({
            'category_id': self.env.ref('uom.uom_categ_length').id,
            'name': 'Yards',
            'factor_inv': 0.9144,
            'uom_type': 'bigger',
        })
        product = self.env.ref('product.product_product_11').copy({
            'uom_id': self.env.ref('uom.product_uom_meter').id,
            'uom_po_id': yards_uom.id,
        })
        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': product.name,
                    'product_id': product.id,
                    'product_uom_qty': 4.0,
                    'product_uom': yards_uom.id,
                    'price_unit': 1.0,
                })
            ],
        })
        so.action_confirm()
        picking = so.picking_ids[0]
        picking.move_ids.write({'quantity_done': 3.66})
        picking.button_validate()
        self.assertEqual(so.order_line.mapped('qty_delivered'), [4.0], 'Sale: no conversion error on delivery in different uom"')

    def test_17_qty_update_propagation(self):
        """ Creates a sale order, then modifies the sale order lines qty and verifies
        that quantity changes are correctly propagated to the picking and delivery picking.
        """
        # Set the delivery in two steps.
        warehouse = self.company_data['default_warehouse']
        warehouse.delivery_steps = 'pick_ship'
        # Sell a product.
        product = self.company_data['product_delivery_no']    # storable
        product.type = 'product'    # storable

        self.env['stock.quant']._update_available_quantity(product, self.company_data['default_warehouse'].lot_stock_id, 50)
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {'name': product.name, 'product_id': product.id, 'product_uom_qty': 50, 'product_uom': product.uom_id.id, 'price_unit': product.list_price}),
            ],
        })
        sale_order.action_confirm()

        # Check picking created
        self.assertEqual(len(sale_order.picking_ids), 2, 'A picking and a delivery picking should have been created.')
        customer_location = self.env.ref('stock.stock_location_customers')
        move_pick = sale_order.picking_ids.filtered(lambda p: p.location_dest_id.id != customer_location.id).move_ids
        move_out = sale_order.picking_ids.filtered(lambda p: p.location_dest_id.id == customer_location.id).move_ids
        self.assertEqual(len(move_out), 1, 'Only one move should be created for a single product.')
        self.assertEqual(move_out.product_uom_qty, 50, 'The move quantity should be the same as the quantity sold.')

        # Decrease the quantity in the sale order and check the move has been updated.
        sale_order.write({
            'order_line': [
                (1, sale_order.order_line.id, {'product_uom_qty': 30}),
            ]
        })
        self.assertEqual(move_pick.product_uom_qty, 30, 'The move quantity should have been decreased as the sale order line was.')
        self.assertEqual(move_out.product_uom_qty, 30, 'The move quantity should have been decreased as the sale order line and the pick line were.')
        self.assertEqual(len(sale_order.picking_ids), 2, 'No additionnal picking should have been created.')

        # Increase the quantity in the sale order and check the move has been updated.
        sale_order.write({
            'order_line': [
                (1, sale_order.order_line.id, {'product_uom_qty': 40})
            ]
        })
        self.assertEqual(move_pick.product_uom_qty, 40, 'The move quantity should have been increased as the sale order line was.')
        self.assertEqual(move_out.product_uom_qty, 40, 'The move quantity should have been increased as the sale order line and the pick line were.')

    def test_18_deliver_more_and_multi_uom(self):
        """
        Deliver an additional product with a UoM different than its default one
        This UoM should be the same on the generated SO line
        """
        uom_m_id = self.ref("uom.product_uom_meter")
        uom_km_id = self.ref("uom.product_uom_km")
        self.product_b.write({
            'uom_id': uom_m_id,
            'uom_po_id': uom_m_id,
        })

        so = self._get_new_sale_order(product=self.product_a)
        so.action_confirm()

        picking = so.picking_ids
        self.env['stock.move'].create({
            'picking_id': picking.id,
            'location_id': picking.location_id.id,
            'location_dest_id': picking.location_dest_id.id,
            'name': self.product_b.name,
            'product_id': self.product_b.id,
            'product_uom_qty': 1,
            'product_uom': uom_km_id,
        })
        action = picking.button_validate()
        wizard = Form(self.env[action['res_model']].with_context(action['context'])).save()
        wizard.process()

        self.assertEqual(so.order_line[1].product_id, self.product_b)
        self.assertEqual(so.order_line[1].qty_delivered, 1)
        self.assertEqual(so.order_line[1].product_uom.id, uom_km_id)

    def test_19_deliver_update_so_line_qty(self):
        """
        Creates a sale order, then validates the delivery
        modifying the sale order lines qty via import and ensures
        a new delivery is created.
        """
        self.product_a.type = 'product'
        self.env['stock.quant']._update_available_quantity(
            self.product_a, self.company_data['default_warehouse'].lot_stock_id, 10)

        # Create sale order
        sale_order = self._get_new_sale_order()
        sale_order.action_confirm()

        # Validate delivery
        picking = sale_order.picking_ids
        picking.move_ids.write({'quantity_done': 10})
        picking.button_validate()

        # Update the line and check a new delivery is created
        with Form(sale_order.with_context(import_file=True)) as so_form:
            with so_form.order_line.edit(0) as line:
                line.product_uom_qty = 777

        self.assertEqual(len(sale_order.picking_ids), 2)

    def test_multiple_returns(self):
        # Creates a sale order for 10 products.
        sale_order = self._get_new_sale_order()
        # Valids the sale order, then valids the delivery.
        sale_order.action_confirm()
        picking = sale_order.picking_ids
        picking.move_ids.write({'quantity_done': 10})
        picking.button_validate()

        # Creates a return from the delivery picking.
        return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=picking.ids, active_id=picking.id,
            active_model='stock.picking'))
        return_wizard = return_picking_form.save()
        # Check that the correct quantity is set on the retrun
        self.assertEqual(return_wizard.product_return_moves.quantity, 10)
        return_wizard.product_return_moves.quantity = 2
        # Valids the return picking.
        res = return_wizard.create_returns()
        return_picking = self.env['stock.picking'].browse(res['res_id'])
        return_picking.move_ids.write({'quantity_done': 2})
        return_picking.button_validate()

        # Creates a second return from the delivery picking.
        return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=picking.ids, active_id=picking.id,
            active_model='stock.picking'))
        return_wizard = return_picking_form.save()
        # Check that the remaining quantity is set on the retrun
        self.assertEqual(return_wizard.product_return_moves.quantity, 8)

    def test_return_with_mto_and_multisteps(self):
        """
        Suppose a product P and a 3-steps delivery.
        Sell 5 x P, process pick & pack pickings and then decrease the qty on
        the SO line:
        - the ship picking should be updated
        - there should be a return R1 for the pack picking
        - there should be a return R2 for the pick picking
        - it should be possible to reserve R1
        """
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        warehouse.delivery_steps = 'pick_pack_ship'
        stock_location = warehouse.lot_stock_id
        pack_location, out_location, custo_location = warehouse.delivery_route_id.rule_ids.location_dest_id

        product = self.env['product.product'].create({
            'name': 'SuperProduct',
            'type': 'product',
        })

        self.env['stock.quant']._update_available_quantity(product, stock_location, 5)

        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.partner_a
        with so_form.order_line.new() as line:
            line.product_id = product
            line.product_uom_qty = 5
        so = so_form.save()
        so.action_confirm()

        pick_picking, pack_picking, _ = so.picking_ids
        (pick_picking + pack_picking).move_ids.quantity_done = 5
        (pick_picking + pack_picking).button_validate()

        with Form(so) as so_form:
            with so_form.order_line.edit(0) as line:
                line.product_uom_qty = 3

        move_lines = so.picking_ids.move_ids.sorted('id')
        ship_sm, pack_sm, pick_sm, ret_pack_sm, ret_pick_sm = move_lines
        self.assertRecordValues(move_lines, [
            {'location_id': out_location.id, 'location_dest_id': custo_location.id, 'move_orig_ids': pack_sm.ids, 'move_dest_ids': []},
            {'location_id': pack_location.id, 'location_dest_id': out_location.id, 'move_orig_ids': pick_sm.ids, 'move_dest_ids': ship_sm.ids},
            {'location_id': stock_location.id, 'location_dest_id': pack_location.id, 'move_orig_ids': [], 'move_dest_ids': pack_sm.ids},
            {'location_id': out_location.id, 'location_dest_id': pack_location.id, 'move_orig_ids': [], 'move_dest_ids': ret_pick_sm.ids},
            {'location_id': pack_location.id, 'location_dest_id': stock_location.id, 'move_orig_ids': ret_pack_sm.ids, 'move_dest_ids': []},
        ])

        ret_pack_sm.picking_id.action_assign()
        self.assertEqual(ret_pack_sm.state, 'assigned')
        self.assertEqual(ret_pack_sm.move_line_ids.reserved_uom_qty, 2)

    def test_mtso_and_qty_decreasing(self):
        """
        First, confirm a SO that has a line with the MTO route (the product
        should already be available in stock). Then, decrease the qty on the SO
        line:
        - The delivery should be updated
        - There should not be any other picking
        """
        warehouse = self.company_data['default_warehouse']
        customer_location = self.env.ref('stock.stock_location_customers')
        mto_route = self.env.ref('stock.route_warehouse0_mto')
        mto_route.active = True

        self.product_a.type = 'product'
        self.env['stock.quant']._update_available_quantity(self.product_a, warehouse.lot_stock_id, 10)

        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'warehouse_id': warehouse.id,
            'order_line': [(0, 0, {
                'name': self.product_a.name,
                'product_id': self.product_a.id,
                'product_uom_qty': 10,
                'product_uom': self.product_a.uom_id.id,
                'price_unit': 1,
                'route_id': mto_route.id,
            })],
        })
        so.action_confirm()
        self.assertRecordValues(so.picking_ids, [{'location_id': warehouse.lot_stock_id.id, 'location_dest_id': customer_location.id}])

        so.order_line.product_uom_qty = 8
        self.assertRecordValues(so.picking_ids, [{'location_id': warehouse.lot_stock_id.id, 'location_dest_id': customer_location.id}])
        self.assertEqual(so.picking_ids.move_ids.product_uom_qty, 8)

    def test_packaging_and_qty_decrease(self):
        packaging = self.env['product.packaging'].create({
            'name': "Super Packaging",
            'product_id': self.product_a.id,
            'qty': 10.0,
        })

        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.partner_a
        with so_form.order_line.new() as line:
            line.product_id = self.product_a
            line.product_uom_qty = 10
        so = so_form.save()
        so.action_confirm()

        self.assertEqual(so.order_line.product_packaging_id, packaging)

        with Form(so) as so_form:
            with so_form.order_line.edit(0) as line:
                line.product_uom_qty = 8

        self.assertEqual(so.picking_ids.move_ids.product_uom_qty, 8)

    def test_backorder_and_decrease_sol_qty(self):
        """
        2 steps delivery
        SO with 10 x P
        Process pickings of 6 x P with backorders
        Update SO: 7 x P
        Backorder should be updated: 1 x P
        """
        warehouse = self.company_data['default_warehouse']
        warehouse.delivery_steps = 'pick_ship'
        stock_location = warehouse.lot_stock_id
        out_location = warehouse.wh_output_stock_loc_id
        customer_location = self.env.ref('stock.stock_location_customers')

        so = self._get_new_sale_order()
        so.action_confirm()
        pick01, ship01 = so.picking_ids

        pick01.move_line_ids.qty_done = 6
        pick01._action_done()
        pick02 = pick01.backorder_ids

        ship01.move_line_ids[0].qty_done = 6
        ship01._action_done()
        ship02 = ship01.backorder_ids

        so.order_line.product_uom_qty = 7

        self.assertRecordValues(so.picking_ids.move_ids.sorted('id'), [
            {'location_id': out_location.id, 'location_dest_id': customer_location.id, 'product_uom_qty': 6.0, 'quantity_done': 6.0, 'state': 'done'},
            {'location_id': stock_location.id, 'location_dest_id': out_location.id, 'product_uom_qty': 6.0, 'quantity_done': 6.0, 'state': 'done'},
            {'location_id': stock_location.id, 'location_dest_id': out_location.id, 'product_uom_qty': 1.0, 'quantity_done': 0.0, 'state': 'assigned'},
            {'location_id': out_location.id, 'location_dest_id': customer_location.id, 'product_uom_qty': 1.0, 'quantity_done': 0.0, 'state': 'waiting'},
        ])
        self.assertEqual(ship01.move_ids.move_orig_ids, (pick01 | pick02).move_ids)
        self.assertEqual(ship02.move_ids.move_orig_ids, (pick01 | pick02).move_ids)

    def test_incoterm_in_advance_payment(self):
        """When generating a advance payment invoice from a SO, this invoice incoterm should be the same as the SO"""

        incoterm = self.env['account.incoterms'].create({
            'name': 'Test Incoterm',
            'code': 'TEST',
        })

        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'incoterm': incoterm.id,
            'order_line': [(0, 0, {
                'name': self.product_a.name,
                'product_id': self.product_a.id,
                'product_uom_qty': 10,
                'product_uom': self.product_a.uom_id.id,
                'price_unit': 1,
            })],
        })
        so.action_confirm()

        advance_product = self.env['product.product'].create({
            'name': 'Deposit',
            'type': 'service',
            'invoice_policy': 'order',
        })

        adv_wiz = self.env['sale.advance.payment.inv'].with_context(active_ids=[so.id]).create({
            'advance_payment_method': 'percentage',
            'amount': 5.0,
            'product_id': advance_product.id,
        })

        act = adv_wiz.with_context(open_invoices=True).create_invoices()
        invoice = self.env['account.move'].browse(act['res_id'])

        self.assertEqual(invoice.invoice_incoterm_id.id, incoterm.id)

    def test_exception_delivery_partial_multi(self):
        """
        When a backorder is cancelled for a picking in multi-picking,
        the related SO should have an exception logged
        """
        #Create 2 sale orders
        so_1 = self._get_new_sale_order()
        so_1.action_confirm()
        picking_1 = so_1.picking_ids
        picking_1.move_ids.write({'quantity_done': 1})

        so_2 = self._get_new_sale_order()
        so_2.action_confirm()
        picking_2 = so_2.picking_ids
        picking_2.move_ids.write({'quantity_done': 2})

        #multi-picking validation
        pick = picking_1 | picking_2
        res_dict = pick.button_validate()
        wizard = Form(self.env[(res_dict.get('res_model'))].with_context(res_dict['context'])).save()
        wizard.backorder_confirmation_line_ids[1].write({'to_backorder': False})
        wizard.process()

        #Check Exception error is logged on so_2
        activity = self.env['mail.activity'].search([('res_id', '=', so_2.id), ('res_model', '=', 'sale.order')])
        self.assertEqual(len(activity), 1, 'When no backorder is created for a partial delivery, a warning error should be logged in its origin SO')

    def test_3_steps_and_unpack(self):
        """
        When removing the package of a stock.move.line mid-flow in a 3-steps delivery with backorders, make sure that
        the OUT picking does not get packages again on its stock.move.line.
        Steps:
        - create a SO of product A for 10 units
        - on PICK_1 picking: put 2 units in Done and put in a package, validate, create a backorder
        - on PACK_1 picking: remove the destination package for the 2 units, validate, create a backorder
        - on OUT picking: the stock.move.line should not have a package
        - on PICK_2 picking: put 2 units in Done and put in a package, validate, create a backorder
        - on OUT picking: the stock.move.line should still not have a package
        - on PACK_2: validate, create a backorder
        - on OUT picking: there should be 2 stock.move.lines, one with package and one without
        """
        warehouse = self.company_data.get('default_warehouse')
        self.env['res.config.settings'].write({
            'group_stock_tracking_lot': True,
            'group_stock_adv_location': True,
            'group_stock_multi_locations': True,
        })
        warehouse.delivery_steps = 'pick_pack_ship'
        self.env['stock.quant']._update_available_quantity(self.test_product_delivery, warehouse.lot_stock_id, 10)

        so_1 = self._get_new_sale_order(product=self.test_product_delivery)
        so_1.action_confirm()
        pick_picking = so_1.picking_ids.filtered(lambda p: p.picking_type_id == warehouse.pick_type_id)
        pack_picking = so_1.picking_ids.filtered(lambda p: p.picking_type_id == warehouse.pack_type_id)
        out_picking = so_1.picking_ids.filtered(lambda p: p.picking_type_id == warehouse.out_type_id)

        pick_picking.move_ids.quantity_done = 2
        pick_picking.action_put_in_pack()
        backorder_wizard_dict = pick_picking.button_validate()
        backorder_wizard = Form(self.env[backorder_wizard_dict['res_model']].with_context(backorder_wizard_dict['context'])).save()
        backorder_wizard.process()

        pack_picking.move_line_ids.result_package_id = False
        pack_picking.move_ids.quantity_done = 2
        backorder_wizard_dict = pack_picking.button_validate()
        backorder_wizard = Form(self.env[backorder_wizard_dict['res_model']].with_context(backorder_wizard_dict['context'])).save()
        backorder_wizard.process()

        self.assertEqual(out_picking.move_line_ids.package_id.id, False)
        self.assertEqual(out_picking.move_line_ids.result_package_id.id, False)

        pick_picking_2 = so_1.picking_ids.filtered(lambda x: x.picking_type_id == warehouse.pick_type_id and x.state != 'done')

        pick_picking_2.move_ids.quantity_done = 2
        package_2 = pick_picking_2.action_put_in_pack()
        backorder_wizard_dict = pick_picking_2.button_validate()
        backorder_wizard = Form(self.env[backorder_wizard_dict['res_model']].with_context(backorder_wizard_dict['context'])).save()
        backorder_wizard.process()

        self.assertEqual(out_picking.move_line_ids.package_id.id, False)
        self.assertEqual(out_picking.move_line_ids.result_package_id.id, False)

        pack_picking_2 = so_1.picking_ids.filtered(lambda p: p.picking_type_id == warehouse.pack_type_id and p.state != 'done')

        pack_picking_2.move_ids.quantity_done = 2
        backorder_wizard_dict = pack_picking_2.button_validate()
        backorder_wizard = Form(self.env[backorder_wizard_dict['res_model']].with_context(backorder_wizard_dict['context'])).save()
        backorder_wizard.process()

        self.assertRecordValues(out_picking.move_line_ids, [{'result_package_id': False}, {'result_package_id': package_2.id}])
