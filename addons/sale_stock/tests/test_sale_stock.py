# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, timedelta

from odoo import Command
from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCommon
from odoo.addons.sale_stock.tests.common import TestSaleStockCommon
from odoo.exceptions import RedirectWarning, UserError
from odoo.tests import Form, tagged
from odoo.tests.common import new_test_user


@tagged('post_install', '-at_install')
class TestSaleStock(TestSaleStockCommon, ValuationReconciliationTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.new_product = cls.env['product.product'].create({
            'name': 'new_product',
            'type': 'consu',
            'is_storable': True,
        })

    def _get_new_sale_order(self, amount=10.0, product=False, sol_vals=False):
        """ Creates and returns a sale order with one default order line.

        :param float amount: quantity of product for the order line (10 by default)
        """
        sol_vals = sol_vals or {}
        product = product or self.company_data['product_delivery_no']
        sale_order_vals = {
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'order_line': [Command.create({
                'product_id': product.id,
                'product_uom_qty': amount,
                'price_unit': product.list_price,
                **sol_vals
            })]
        }
        return self.env['sale.order'].create(sale_order_vals)

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
                    'price_unit': p.list_price,
                }) for p in (
                    self.company_data['product_order_no'],
                    self.company_data['product_service_delivery'],
                    self.company_data['product_service_order'],
                    self.company_data['product_delivery_no'],
                )],
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
        pick.move_ids.write({'quantity': 1, 'picked': True})
        Form.from_action(self.env, pick.button_validate()).save().process()
        self.assertEqual(self.so.invoice_status, 'to invoice', 'Sale Stock: so invoice_status should be "to invoice" after partial delivery')
        del_qties = [sol.qty_delivered for sol in self.so.order_line]
        del_qties_truth = [1.0 if sol.product_id.type == 'consu' else 0.0 for sol in self.so.order_line]
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
        pick_2.move_ids.write({'quantity': 1, 'picked': True})
        self.assertTrue(pick_2.button_validate(), 'Sale Stock: second picking should be final without need for a backorder')
        self.assertEqual(self.so.invoice_status, 'to invoice', 'Sale Stock: so invoice_status should be "to invoice" after complete delivery')
        del_qties = [sol.qty_delivered for sol in self.so.order_line]
        del_qties_truth = [2.0 if sol.product_id.type == 'consu' else 0.0 for sol in self.so.order_line]
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
        product_list = (
                    self.company_data['product_order_no'],
                    self.company_data['product_service_delivery'],
                    self.company_data['product_service_order'],
                    self.company_data['product_delivery_no'],
                )

        for product in product_list:
            product.invoice_policy = 'order'

        self.so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'order_line': [(0, 0, {
                'name': p.name,
                'product_id': p.id,
                'product_uom_qty': 2,
                'price_unit': p.list_price,
                }) for p in product_list],
            'picking_policy': 'direct',
        })
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
        })
        act = adv_wiz.create_invoices()
        inv = self.env['account.move'].browse(act['res_id'])
        self.assertEqual(inv.amount_untaxed, self.so.amount_untaxed * 5.0 / 100.0, 'Sale Stock: deposit invoice is wrong')
        self.assertEqual(self.so.invoice_status, 'to invoice', 'Sale Stock: so should be to invoice after invoicing deposit')
        # invoice on order: everything should be invoiced
        self.so._create_invoices(final=True)
        self.assertEqual(self.so.invoice_status, 'invoiced', 'Sale Stock: so should be fully invoiced after second invoice')

        # deliver, check the delivered quantities
        pick = self.so.picking_ids
        pick.move_ids.write({'quantity': 2, 'picked': True})
        self.assertTrue(pick.button_validate(), 'Sale Stock: complete delivery should not need a backorder')
        del_qties = [sol.qty_delivered for sol in self.so.order_line]
        del_qties_truth = [2.0 if sol.product_id.type == 'consu' else 0.0 for sol in self.so.order_line]
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
                'price_unit': self.product.list_price})],
        }
        self.so = self.env['sale.order'].create(so_vals)

        # confirm our standard so, check the picking
        self.so.action_confirm()
        self.assertTrue(self.so.picking_ids, 'Sale Stock: no picking created for "invoice on delivery" storable products')

        # invoice in on delivery, nothing should be invoiced
        self.assertEqual(self.so.invoice_status, 'no', 'Sale Stock: so invoice_status should be "no" instead of "%s".' % self.so.invoice_status)

        # deliver completely
        pick = self.so.picking_ids
        pick.move_ids.write({'quantity': 5, 'picked': True})
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
        res = return_wiz.action_create_returns()
        return_pick = self.env['stock.picking'].browse(res['res_id'])

        # Validate picking
        return_pick.move_ids.write({'quantity': 2, 'picked': True})
        return_pick.button_validate()

        # Check invoice
        self.assertEqual(self.so.invoice_status, 'to invoice', 'Sale Stock: so invoice_status should be "to invoice" instead of "%s" after picking return' % self.so.invoice_status)
        self.assertAlmostEqual(self.so.order_line.sorted()[0].qty_delivered, 3.0, msg='Sale Stock: delivered quantity should be 3.0 instead of "%s" after picking return' % self.so.order_line.sorted()[0].qty_delivered)
        # let's do an invoice with refunds
        adv_wiz = self.env['sale.advance.payment.inv'].with_context(active_ids=[self.so.id]).create({
            'advance_payment_method': 'delivered',
        })
        adv_wiz.create_invoices()
        self.inv_2 = self.so.invoice_ids.filtered(lambda r: r.state == 'draft')
        self.assertAlmostEqual(self.inv_2.invoice_line_ids.sorted()[0].quantity, 2.0, msg='Sale Stock: refund quantity on the invoice should be 2.0 instead of "%s".' % self.inv_2.invoice_line_ids.sorted()[0].quantity)
        self.assertEqual(self.so.invoice_status, 'invoiced', 'Sale Stock: so invoice_status should be "invoiced" instead of "%s" after invoicing the return' % self.so.invoice_status)

    def test_03_sale_stock_delivery_partial(self):
        """
        Test a SO with a product invoiced on delivery. Deliver partially and invoice the SO, when
        the SO is set on 'done', the SO should be fully invoiced.
        """
        self.product = self.company_data['product_delivery_no']
        so_vals = {
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'order_line': [(0, 0, {
                'name': self.product.name,
                'product_id': self.product.id,
                'product_uom_qty': 5.0,
                'product_uom_id': self.product.uom_id.id,
                'price_unit': self.product.list_price,
            })],
        }
        self.so = self.env['sale.order'].create(so_vals)

        # confirm our standard so, check the picking
        self.so.action_confirm()
        self.assertTrue(self.so.picking_ids, 'Sale Stock: no picking created for "invoice on delivery" storable products')

        # invoice in on delivery, nothing should be invoiced
        self.assertEqual(self.so.invoice_status, 'no', 'Sale Stock: so invoice_status should be "nothing to invoice"')

        # deliver partially
        pick = self.so.picking_ids
        pick.move_ids.write({'quantity': 4})
        res_dict = pick.button_validate()
        wizard = Form(self.env[(res_dict.get('res_model'))].with_context(res_dict['context'])).save()
        wizard.process_cancel_backorder()

        # Check Exception error is logged on SO
        activity = self.env['mail.activity'].search([('res_id', '=', self.so.id), ('res_model', '=', 'sale.order')])
        self.assertEqual(len(activity), 1, 'When no backorder is created for a partial delivery, a warning error should be logged in its origin SO')

        # Check quantity delivered
        del_qty = sum(sol.qty_delivered for sol in self.so.order_line)
        self.assertEqual(del_qty, 4.0, 'Sale Stock: delivered quantity should be 4.0 after partial delivery')

        # Check invoice
        self.assertEqual(self.so.invoice_status, 'to invoice', 'Sale Stock: so invoice_status should be "to invoice" before invoicing')
        self.inv_1 = self.so._create_invoices()
        self.assertEqual(len(self.inv_1), 1, 'Sale Stock: only one invoice should be created')
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
        item2.is_storable = True    # storable

        self.so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {'name': item1.name, 'product_id': item1.id, 'product_uom_qty': 1, 'price_unit': item1.list_price}),
                (0, 0, {'name': item2.name, 'product_id': item2.id, 'product_uom_qty': 1, 'price_unit': item2.list_price}),
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
        wizard = Form.from_action(self.env, res_dict).save()
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
                (0, 0, {'name': item1.name, 'product_id': item1.id, 'product_uom_qty': 1, 'price_unit': item1.list_price}),
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
        item2.is_storable = True    # storable

        self.env['stock.quant']._update_available_quantity(item2, self.company_data['default_warehouse'].lot_stock_id, 2)
        self.so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {'name': item1.name, 'product_id': item1.id, 'product_uom_qty': 1, 'price_unit': item1.list_price}),
                (0, 0, {'name': item2.name, 'product_id': item2.id, 'product_uom_qty': 1, 'price_unit': item2.list_price}),
            ],
        })
        self.so.action_confirm()

        # deliver them
        self.assertEqual(len(self.so.picking_ids), 1)
        self.so.picking_ids.sorted()[0].button_validate()
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
        self.env.ref('uom.decimal_product_uom').digits = 0
        uom_unit = self.env.ref('uom.product_uom_unit')
        uom_dozen = self.env.ref('uom.product_uom_dozen')
        item1 = self.company_data['product_order_no']

        self.assertEqual(item1.uom_id.id, uom_unit.id)

        # sell a dozen
        so1 = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({'name': "UoM Test", 'display_type': 'line_note'}),
                Command.create({'product_id': item1.id, 'product_uom_id': uom_dozen.id}),
                Command.create({'name': "Downpayment", 'is_downpayment': True}),
            ],
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
        product_line = so1.order_line.filtered('product_id')
        so1.write({
            'order_line': [
                Command.update(product_line.id, {'product_uom_qty': 2}),
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
                Command.update(product_line.id, {'product_uom_qty': 3}),
            ]
        })
        move2 = so1.picking_ids.move_ids.filtered(lambda m: m.product_uom.id == uom_dozen.id)
        self.assertEqual(move2.product_uom_qty, 1)
        self.assertEqual(move2.product_uom.id, uom_dozen.id)
        self.assertEqual(move2.product_qty, 12)

        # deliver everything
        move1.write({'quantity': 24, 'picked': True})
        move2.write({'quantity': 1, 'picked': True})
        so1.picking_ids.button_validate()

        # check the delivered quantity
        self.assertEqual(product_line.qty_delivered, 3.0)

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
                    'product_uom_id': uom_dozen.id,
                    'price_unit': item1.list_price,
                }),
                (0, 0, {
                    'name': item1.name,
                    'product_id': item1.id,
                    'product_uom_qty': 1,
                    'product_uom_id': uom_dozen.id,
                    'price_unit': item1.list_price,
                }),
                (0, 0, {
                    'name': item1.name,
                    'product_id': item1.id,
                    'product_uom_qty': 1,
                    'product_uom_id': uom_dozen.id,
                    'price_unit': item1.list_price,
                }),
            ],
        })
        so1.action_confirm()

        self.assertEqual(len(so1.picking_ids.move_ids), 3)
        self.assertEqual(len(so1.picking_ids.move_line_ids), 3)
        so1.picking_ids.move_ids.picked = True
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
                    'product_uom_id': uom_unit.id,
                    'price_unit': item1.list_price,
                }),
            ],
        })
        so1.action_confirm()

        picking = so1.picking_ids
        picking.button_validate()

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
        res = return_wiz.action_create_returns()
        return_pick = self.env['stock.picking'].browse(res['res_id'])
        return_pick.button_validate()

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
        item1.is_storable = True

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
                (0, 0, {'name': item1.name, 'product_id': item1.id, 'product_uom_qty': 1, 'price_unit': item1.list_price}),
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
        item1.is_storable = True
        self.env['stock.quant']._update_available_quantity(item1, self.company_data['default_warehouse'].lot_stock_id, 10)
        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {'name': item1.name, 'product_id': item1.id, 'product_uom_qty': 5, 'price_unit': item1.list_price}),
                (0, 0, {'name': item1.name, 'product_id': item1.id, 'product_uom_qty': 5, 'price_unit': item1.list_price}),
                (0, 0, {'name': item1.name, 'product_id': item1.id, 'product_uom_qty': 5, 'price_unit': item1.list_price}),
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
        picking.move_ids.write({'quantity': 10, 'picked': True})
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
        self.assertEqual(return_wizard.product_return_moves.quantity, 0)

        # Valids the return picking.
        return_wizard.product_return_moves.quantity = 10
        res = return_wizard.action_create_returns()
        return_picking = self.env['stock.picking'].browse(res['res_id'])
        return_picking.move_ids.write({'quantity': 10, 'picked': True})
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
        picking.move_ids.write({'quantity': 10, 'picked': True})
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
        self.assertEqual(return_wizard.product_return_moves.quantity, 0)
        return_wizard.product_return_moves.to_refund = False
        return_wizard.product_return_moves.quantity = 10
        # Valids the return picking.
        res = return_wizard.action_create_returns()
        return_picking = self.env['stock.picking'].browse(res['res_id'])
        return_picking.move_ids.write({'quantity': 10, 'picked': True})
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
        picking.picking_type_id.show_operations = True  # Could be false without demo data, as the lot group is disabled
        picking_form = Form(picking)
        with picking_form.move_ids.edit(0) as move:
            move.quantity = 5
        with picking_form.move_ids.new() as new_move:
            new_move.product_id = product_inv_on_order
            new_move.quantity = 5
        picking = picking_form.save()
        picking.move_ids.picked = True
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
            {'product_id': initial_product.id, 'quantity': 5},
            {'product_id': product_inv_on_order.id, 'quantity': 5},
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
        with picking_form.move_ids.edit(0) as move:
            move.quantity = 5
        with picking_form.move_ids.new() as new_move:
            new_move.product_id = product_inv_on_delivered
            new_move.quantity = 5
        picking = picking_form.save()
        picking.move_ids.picked = True
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
        pick.picking_type_id.show_operations = True  # Could be false without demo data, as the lot group is disabled
        picking_form = Form(pick)
        with picking_form.move_ids.edit(0) as move:
            move.quantity = 10
        pick = picking_form.save()
        pick.move_ids.picked = True
        pick.button_validate()

        delivery = sale_order.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing')
        delivery.picking_type_id.show_operations = True  # Could be false without demo data, as the lot group is disabled
        picking_form = Form(delivery)
        with picking_form.move_ids.edit(0) as move:
            move.quantity = 10
        delivery = picking_form.save()
        delivery.move_ids.picked = True
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

        picking_form = Form(pick)
        with picking_form.move_ids.edit(0) as move:
            move.quantity = 10
        with picking_form.move_ids.new() as new_move:
            new_move.product_id = product_inv_on_order
            new_move.quantity = 10
        pick = picking_form.save()
        pick.move_ids.picked = True
        pick.button_validate()

        delivery = sale_order.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing')
        picking_form = Form(delivery)
        with picking_form.move_ids.edit(0) as move:
            move.quantity = 10
        with picking_form.move_ids.edit(1) as new_move:
            new_move.quantity = 10
        delivery = picking_form.save()
        delivery.move_ids.picked = True
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
                'price_unit': product.list_price})],
        }
        so = self.env['sale.order'].create(so_vals)

        # confirm the so
        so.action_confirm()

        # deliver partially
        pick = so.picking_ids
        pick.move_ids.write({'quantity': 3, 'picked': True})

        Form.from_action(self.env, pick.button_validate()).save().process()

        # create invoice for 3 quantity and post it
        inv_1 = so._create_invoices()
        inv_1.action_post()
        self.assertEqual(inv_1.state, 'posted', 'invoice should be in posted state')

        pick_2 = so.picking_ids.filtered('backorder_id')
        pick_2.move_ids.write({'quantity': 2, 'picked': True})
        pick_2.button_validate()

        # create invoice for remaining 2 quantity
        inv_2 = so._create_invoices()
        self.assertEqual(inv_2.state, 'draft', 'invoice should be in draft state')

        # check the status of invoices after cancelling the order
        so.action_cancel()
        self.assertEqual(inv_1.state, 'posted', 'A posted invoice state should remain posted')
        self.assertEqual(inv_2.state, 'cancel', 'A drafted invoice state should be cancelled')

    def test_reservation_method_w_sale(self):
        picking_type_out = self.company_data['default_warehouse'].out_type_id
        # make sure generated picking will auto-assign
        picking_type_out.reservation_method = 'at_confirm'
        product = self.company_data['product_delivery_no']
        product.is_storable = True
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

    def test_15_cancel_delivery(self):
        """ Suppose the option "Lock Confirmed Sales" enabled and a product with the invoicing
        policy set to "Delivered quantities". When cancelling the delivery of such a product, the
        invoice status of the associated SO should be 'Nothing to Invoice'
        """
        group_auto_done = self.env.ref('sale.group_auto_done_setting')
        self.group_user.implied_ids = [Command.link(group_auto_done.id)]

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
                'price_unit': product.list_price
            })],
        })
        so.action_confirm()
        self.assertEqual(so.state, 'sale')
        self.assertTrue(so.locked)
        so.picking_ids.action_cancel()

        self.assertEqual(so.invoice_status, 'no')

    def test_16_multi_uom(self):
        yards_uom = self.env['uom.uom'].create({
            'name': 'Yards',
            'relative_factor': 0.9144,
            'relative_uom_id': self.env.ref('uom.product_uom_meter').id,
        })
        product = self.env['product.product'].create({
            'name': 'Test Product',
            'uom_id': self.env.ref('uom.product_uom_meter').id,
        })
        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': product.name,
                    'product_id': product.id,
                    'product_uom_qty': 4.0,
                    'product_uom_id': yards_uom.id,
                    'price_unit': 1.0,
                })
            ],
        })
        so.action_confirm()
        picking = so.picking_ids[0]
        picking.move_ids.write({'quantity': 3.66, 'picked': True})
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
        product.is_storable = True    # storable

        self.env['stock.quant']._update_available_quantity(product, self.company_data['default_warehouse'].lot_stock_id, 50)
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {'name': product.name, 'product_id': product.id, 'product_uom_qty': 50, 'price_unit': product.list_price}),
            ],
        })
        sale_order.action_confirm()

        # Check picking created
        self.assertEqual(len(sale_order.picking_ids), 1, 'Only the "Pick" picking should have been created.')
        customer_location = self.env.ref('stock.stock_location_customers')
        move_pick = sale_order.picking_ids.filtered(lambda p: p.location_dest_id.id != customer_location.id).move_ids
        self.assertEqual(len(move_pick), 1, 'Only one move should be created for a single product.')
        self.assertEqual(move_pick.product_uom_qty, 50, 'The move quantity should be the same as the quantity sold.')

        # Decrease the quantity in the sale order and check the move has been updated.
        sale_order.order_line.write({'product_uom_qty': 30})
        self.assertEqual(move_pick.product_uom_qty, 30, 'The move quantity should have been decreased as the sale order line was.')
        self.assertEqual(len(sale_order.picking_ids), 1, 'No additionnal picking should have been created.')

        # Increase the quantity in the sale order and check the move has been updated.
        sale_order.order_line.write({'product_uom_qty': 40})
        self.assertEqual(move_pick.product_uom_qty, 40, 'The move quantity should have been increased as the sale order line was.')
        move_pick.write({'quantity': 40, 'picked': True})
        move_pick._action_done()

        self.assertEqual(len(sale_order.picking_ids), 2, 'The delivery picking should have been created as well.')
        move_out = sale_order.picking_ids.filtered(lambda p: p.location_dest_id.id == customer_location.id).move_ids
        self.assertEqual(move_out.product_uom_qty, 40, 'The move quantity should have been increased as the sale order line and the pick line were.')

        # Increase the quantity in the sale order and check new 'Pick' has been created for the missing quantity.
        sale_order.order_line.write({'product_uom_qty': 50})
        self.assertEqual(len(sale_order.picking_ids), 3, 'A new "Pick" picking should have been created for the missing quantity.')
        move_pick_2 = sale_order.picking_ids.filtered(lambda p: p.location_dest_id.id != customer_location.id and p.state != 'done').move_ids
        self.assertEqual(move_pick_2.product_uom_qty, 10, 'The move quantity should be the missing quantity.')

    def test_18_deliver_more_and_multi_uom(self):
        """
        Deliver an additional product with a UoM different than its default one
        This UoM should be the same on the generated SO line
        """
        uom_m_id = self.ref("uom.product_uom_meter")
        uom_km_id = self.ref("uom.product_uom_km")
        self.product_b.write({
            'uom_id': uom_m_id,
        })

        so = self._get_new_sale_order(product=self.product_a)
        so.action_confirm()

        picking = so.picking_ids
        self.env['stock.move'].create({
            'picking_id': picking.id,
            'location_id': picking.location_id.id,
            'location_dest_id': picking.location_dest_id.id,
            'product_id': self.product_b.id,
            'product_uom_qty': 1,
            'product_uom': uom_km_id,
            'quantity': 1,
        })
        picking.button_validate()

        self.assertEqual(so.order_line[1].product_id, self.product_b)
        self.assertEqual(so.order_line[1].qty_delivered, 1)
        self.assertEqual(so.order_line[1].product_uom_id.id, uom_km_id)

    def test_19_deliver_update_so_line_qty(self):
        """
        Creates a sale order, then validates the delivery
        modifying the sale order lines qty via import and ensures
        a new delivery is created.
        """
        self.product_a.is_storable = True
        self.env['stock.quant']._update_available_quantity(
            self.product_a, self.company_data['default_warehouse'].lot_stock_id, 10)

        # Create sale order
        sale_order = self._get_new_sale_order()
        sale_order.action_confirm()

        # Validate delivery
        picking = sale_order.picking_ids
        picking.move_ids.write({'quantity': 10, 'picked': True})
        picking.button_validate()

        # Update the line and check a new delivery is created
        with Form(sale_order.with_context(import_file=True)) as so_form:
            with so_form.order_line.edit(0) as line:
                line.product_uom_qty = 777

        self.assertEqual(len(sale_order.picking_ids), 2)

    def test_update_so_line_qty_with_package(self):
        """
        Creates a sale order, then validates the delivery
        modifying the sale order lines qty to 0
        move line should be deleted.
        """
        self.product_a.is_storable = True
        self.env['stock.quant']._update_available_quantity(
            self.product_a, self.company_data['default_warehouse'].lot_stock_id, 10,
            package_id=self.env['stock.package'].create({'name': 'PacMan'}))

        # Create sale order
        sale_order = self._get_new_sale_order(product=self.product_a)
        sale_order.action_confirm()

        # Update the SO line
        with Form(sale_order.with_context(import_file=True)) as so_form:
            with so_form.order_line.edit(0) as line:
                line.product_uom_qty = 0

        self.assertFalse(sale_order.picking_ids.move_line_ids)

    def test_multiple_returns(self):
        # Creates a sale order for 10 products.
        sale_order = self._get_new_sale_order()
        # Valids the sale order, then valids the delivery.
        sale_order.action_confirm()
        picking = sale_order.picking_ids
        picking.move_ids.write({'quantity': 10, 'picked': True})
        picking.button_validate()

        # Creates a return from the delivery picking.
        return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=picking.ids, active_id=picking.id,
            active_model='stock.picking'))
        return_wizard = return_picking_form.save()
        # Check that the correct quantity is set on the retrun
        self.assertEqual(return_wizard.product_return_moves.quantity, 0)
        return_wizard.product_return_moves.quantity = 2
        # Valids the return picking.
        res = return_wizard.action_create_returns()
        return_picking = self.env['stock.picking'].browse(res['res_id'])
        return_picking.move_ids.write({'quantity': 2, 'picked': True})
        return_picking.button_validate()

    def test_return_for_exchange_negativ(self):
        """test product added into the return wizard are excluded in case of return for exchange"""
        sale_order = self._get_new_sale_order()
        sale_order.action_confirm()
        picking = sale_order.picking_ids
        picking.move_ids.write({'quantity': 10, 'picked': True})
        picking.button_validate()

        return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_id=picking.id, active_model='stock.picking'))
        with return_picking_form.product_return_moves.new() as line:
            line.product_id = self.new_product
            line.quantity = 2
        return_wizard = return_picking_form.save()
        return_wizard.product_return_moves[0].quantity = 2

        res = return_wizard.action_create_exchanges()
        return_picking = self.env['stock.picking'].browse(res['res_id'])
        self.assertTrue(return_picking)
        self.assertEqual(len(return_picking.move_ids), 2)
        new_product_moves = self.env['stock.move'].search([('product_id', '=', self.new_product.id)])
        self.assertEqual(len(new_product_moves), 1, 'The new product should not create extra procurement')
        sol = self.env['sale.order.line'].search([('product_id', '=', self.new_product.id)])
        self.assertFalse(sol)
        return_picking.button_validate()
        sol = self.env['sale.order.line'].search([('product_id', '=', self.new_product.id)])
        self.assertTrue(sol)
        self.assertEqual(sol.product_uom_qty, 0)
        self.assertEqual(sol.qty_delivered, -2)
        self.assertEqual(sol.order_id, sale_order)

    def test_return_for_exchange_and_cancel_sol_qty(self):
        """
        SO, deliver, generate the return for exchange
        Process the return
        Then, SOL qty to 0
        The new delivery should be canceled
        """
        warehouse = self.company_data['default_warehouse']
        stock_location = warehouse.lot_stock_id
        customer_location = self.env.ref('stock.stock_location_customers')

        so = self._get_new_sale_order()
        so.action_confirm()

        delivery = so.picking_ids
        delivery.move_ids.write({'quantity': 10, 'picked': True})
        delivery.button_validate()

        return_picking_form = Form(self.env['stock.return.picking'].with_context(active_id=delivery.id, active_model='stock.picking'))
        with return_picking_form.product_return_moves.edit(0) as line:
            line.quantity = 10
        return_wizard = return_picking_form.save()
        res = return_wizard.action_create_exchanges()

        return_picking = self.env['stock.picking'].browse(res['res_id'])
        return_picking.move_ids.write({'quantity': 10, 'picked': True})
        return_picking.button_validate()

        so.order_line.product_uom_qty = 0
        self.assertRecordValues(so.picking_ids.move_ids.sorted(key='id'), [
            {'location_id': stock_location.id, 'location_dest_id': customer_location.id, 'state': 'done'},
            {'location_id': customer_location.id, 'location_dest_id': stock_location.id, 'state': 'done'},
            {'location_id': stock_location.id, 'location_dest_id': customer_location.id, 'state': 'cancel'},
        ])

    def test_return_multisteps_receipt(self):
        """test extra product returned are added to the sale order only once in 3 steps receipt"""

        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        warehouse.reception_steps = 'three_steps'
        sale_order = self._get_new_sale_order()
        sale_order.action_confirm()
        picking = sale_order.picking_ids
        picking.move_ids.write({'quantity': 10, 'picked': True})
        picking.button_validate()

        return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_id=picking.id, active_model='stock.picking'))
        with return_picking_form.product_return_moves.new() as line:
            line.product_id = self.new_product
            line.quantity = 2
        return_wizard = return_picking_form.save()
        res = return_wizard.action_create_returns()
        return_picking = self.env['stock.picking'].browse(res['res_id'])
        self.assertEqual(return_picking.location_id, picking.location_dest_id)
        self.assertEqual(return_picking.location_dest_id, warehouse.in_type_id.default_location_dest_id)
        return_picking.button_validate()
        next_pick = return_picking.move_ids.move_dest_ids.picking_id
        next_pick.button_validate()
        next_pick = next_pick.move_ids.move_dest_ids.picking_id
        next_pick.button_validate()
        sol = self.env['sale.order.line'].search([('product_id', '=', self.new_product.id)])
        self.assertEqual(len(sol), 1)
        self.assertEqual(sol.qty_delivered, -2)

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
        pack_location, out_location, custo_location = warehouse.delivery_route_id.rule_ids.picking_type_id.default_location_dest_id

        product = self.env['product.product'].create({
            'name': 'SuperProduct',
            'is_storable': True,
        })

        self.env['stock.quant']._update_available_quantity(product, stock_location, 5)

        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.partner_a
        with so_form.order_line.new() as line:
            line.product_id = product
            line.product_uom_qty = 5
        so = so_form.save()
        so.action_confirm()

        pick_picking = so.picking_ids
        pick_picking.move_ids.write({'quantity': 5, 'picked': True})
        pick_picking.button_validate()
        pack_picking = so.picking_ids - pick_picking
        pack_picking.move_ids.write({'quantity': 5, 'picked': True})
        pack_picking.button_validate()

        with Form(so) as so_form:
            with so_form.order_line.edit(0) as line:
                line.product_uom_qty = 3
            so_form.save()

        moves = so.picking_ids.move_ids.sorted('id')
        pick_sm, pack_sm, ship_sm, ret_pick_sm, ret_pack_sm = moves
        self.assertRecordValues(moves, [
            {'product_uom_qty': 5, 'location_id': stock_location.id, 'location_dest_id': pack_location.id, 'move_orig_ids': [], 'move_dest_ids': pack_sm.ids},
            {'product_uom_qty': 5, 'location_id': pack_location.id, 'location_dest_id': out_location.id, 'move_orig_ids': pick_sm.ids, 'move_dest_ids': ship_sm.ids},
            {'product_uom_qty': 3, 'location_id': out_location.id, 'location_dest_id': custo_location.id, 'move_orig_ids': pack_sm.ids, 'move_dest_ids': []},
            {'product_uom_qty': 2, 'location_id': pack_location.id, 'location_dest_id': stock_location.id, 'move_orig_ids': ret_pack_sm.ids, 'move_dest_ids': []},
            {'product_uom_qty': 2, 'location_id': out_location.id, 'location_dest_id': pack_location.id, 'move_orig_ids': [], 'move_dest_ids': ret_pick_sm.ids},
        ])

        # Make sure the total outgoing qty per step is correct
        for picking_type in warehouse.delivery_route_id.rule_ids.picking_type_id:
            step_moves = moves.filtered(lambda m: m.picking_type_id == picking_type)
            total_qty = sum(m.product_uom_qty if m.location_id == picking_type.default_location_src_id else -m.product_uom_qty for m in step_moves)
            self.assertEqual(total_qty, 3)

        ret_pack_sm.picking_id.action_assign()
        self.assertEqual(ret_pack_sm.state, 'assigned')
        self.assertEqual(ret_pack_sm.move_line_ids.quantity, 2)

        # Now add the set the quantity back to what it was. A new PICK should be created that will end up merging with the OUT once it reaches the OUT
        with Form(so) as so_form:
            with so_form.order_line.edit(0) as line:
                line.product_uom_qty = 5

        moves = so.picking_ids.move_ids.sorted('id')
        self.assertRecordValues(moves, [
            {'product_uom_qty': 5, 'location_id': stock_location.id, 'location_dest_id': pack_location.id, 'move_orig_ids': [], 'move_dest_ids': pack_sm.ids},
            {'product_uom_qty': 5, 'location_id': pack_location.id, 'location_dest_id': out_location.id, 'move_orig_ids': pick_sm.ids, 'move_dest_ids': ship_sm.ids},
            {'product_uom_qty': 3, 'location_id': out_location.id, 'location_dest_id': custo_location.id, 'move_orig_ids': pack_sm.ids, 'move_dest_ids': []},
            {'product_uom_qty': 2, 'location_id': pack_location.id, 'location_dest_id': stock_location.id, 'move_orig_ids': ret_pack_sm.ids, 'move_dest_ids': []},
            {'product_uom_qty': 2, 'location_id': out_location.id, 'location_dest_id': pack_location.id, 'move_orig_ids': [], 'move_dest_ids': ret_pick_sm.ids},
            {'product_uom_qty': 2, 'location_id': stock_location.id, 'location_dest_id': pack_location.id, 'move_orig_ids': [], 'move_dest_ids': []},
        ])

        # Make sure the total outgoing qty in pick is correct
        step_moves = moves.filtered(lambda m: m.picking_type_id == warehouse.pick_type_id)
        total_pick_qty = sum(m.product_uom_qty if m.location_id == warehouse.pick_type_id.default_location_src_id else -m.product_uom_qty for m in step_moves)
        self.assertEqual(total_pick_qty, 5)

    def test_return_with_mto_and_multisteps_old_pull(self):
        """
        Suppose a product P and a 3-steps delivery.
        Sell 5 x P, process pick & pack pickings and then decrease the qty on
        the SO line:
        - the ship picking should be updated
        - there should be a return R1 for the pack picking
        - there should be a return R2 for the pick picking
        - it should be possible to reserve R1
        """
        stock_location = self.warehouse_3_steps_pull.lot_stock_id
        pack_location, out_location, custo_location = self.warehouse_3_steps_pull.delivery_route_id.rule_ids.location_dest_id

        product = self.env['product.product'].create({
            'name': 'SuperProduct',
            'is_storable': True,
        })

        self.env['stock.quant']._update_available_quantity(product, stock_location, 5)

        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.partner_a
        so_form.warehouse_id = self.warehouse_3_steps_pull
        with so_form.order_line.new() as line:
            line.product_id = product
            line.product_uom_qty = 5
        so = so_form.save()
        so.action_confirm()

        _, pack_picking, pick_picking = so.picking_ids
        (pick_picking + pack_picking).move_ids.write({'quantity': 5, 'picked': True})
        (pick_picking + pack_picking).button_validate()
        with Form(so) as so_form:
            with so_form.order_line.edit(0) as line:
                line.product_uom_qty = 3

        moves = so.picking_ids.move_ids.sorted('id')
        ship_sm, pack_sm, pick_sm, ret_pack_sm, ret_pick_sm = moves
        self.assertRecordValues(moves, [
            {'product_uom_qty': 3, 'location_id': out_location.id, 'location_dest_id': custo_location.id, 'move_orig_ids': pack_sm.ids, 'move_dest_ids': []},
            {'product_uom_qty': 5, 'location_id': pack_location.id, 'location_dest_id': out_location.id, 'move_orig_ids': pick_sm.ids, 'move_dest_ids': ship_sm.ids},
            {'product_uom_qty': 5, 'location_id': stock_location.id, 'location_dest_id': pack_location.id, 'move_orig_ids': [], 'move_dest_ids': pack_sm.ids},
            {'product_uom_qty': 2, 'location_id': out_location.id, 'location_dest_id': pack_location.id, 'move_orig_ids': [], 'move_dest_ids': ret_pick_sm.ids},
            {'product_uom_qty': 2, 'location_id': pack_location.id, 'location_dest_id': stock_location.id, 'move_orig_ids': ret_pack_sm.ids, 'move_dest_ids': []},
        ])

        # Make sure the total outgoing qty per step is correct
        for picking_type in self.warehouse_3_steps_pull.delivery_route_id.rule_ids.picking_type_id:
            step_moves = moves.filtered(lambda m: m.picking_type_id == picking_type)
            total_qty = sum(m.product_uom_qty if m.location_id == picking_type.default_location_src_id else -m.product_uom_qty for m in step_moves)
            self.assertEqual(total_qty, 3)

        ret_pack_sm.picking_id.action_assign()
        self.assertEqual(ret_pack_sm.state, 'assigned')
        self.assertEqual(ret_pack_sm.move_line_ids.quantity, 2)

        # Now add the set the quantity back to what it was. A new PICK line should be created up to OUT
        with Form(so) as so_form:
            with so_form.order_line.edit(0) as line:
                line.product_uom_qty = 5

        moves = so.picking_ids.move_ids.sorted('id')
        ship_sm, pack_sm, pick_sm, ret_pack_sm, ret_pick_sm, new_pack_sm, new_pick_sm = moves
        self.assertRecordValues(moves, [
            {'product_uom_qty': 5, 'location_id': out_location.id, 'location_dest_id': custo_location.id, 'move_orig_ids': (pack_sm | new_pack_sm).ids, 'move_dest_ids': []},
            {'product_uom_qty': 5, 'location_id': pack_location.id, 'location_dest_id': out_location.id, 'move_orig_ids': pick_sm.ids, 'move_dest_ids': ship_sm.ids},
            {'product_uom_qty': 5, 'location_id': stock_location.id, 'location_dest_id': pack_location.id, 'move_orig_ids': [], 'move_dest_ids': pack_sm.ids},
            {'product_uom_qty': 2, 'location_id': out_location.id, 'location_dest_id': pack_location.id, 'move_orig_ids': [], 'move_dest_ids': ret_pick_sm.ids},
            {'product_uom_qty': 2, 'location_id': pack_location.id, 'location_dest_id': stock_location.id, 'move_orig_ids': ret_pack_sm.ids, 'move_dest_ids': []},
            {'product_uom_qty': 2, 'location_id': pack_location.id, 'location_dest_id': out_location.id, 'move_orig_ids': new_pick_sm.ids, 'move_dest_ids': ship_sm.ids},
            {'product_uom_qty': 2, 'location_id': stock_location.id, 'location_dest_id': pack_location.id, 'move_orig_ids': [], 'move_dest_ids': new_pack_sm.ids},
        ])

        # Make sure the total outgoing qty per step is correct
        for picking_type in self.warehouse_3_steps_pull.delivery_route_id.rule_ids.picking_type_id:
            step_moves = moves.filtered(lambda m: m.picking_type_id == picking_type)
            total_qty = sum(m.product_uom_qty if m.location_id == picking_type.default_location_src_id else -m.product_uom_qty for m in step_moves)
            self.assertEqual(total_qty, 5)

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
        pick01 = so.picking_ids

        pick01.move_line_ids.write({'quantity': 6})
        pick01.move_ids.picked = True
        pick01._action_done()

        ship = so.picking_ids.filtered(lambda p: p.picking_type_id == warehouse.out_type_id)
        ship.move_ids.write({'quantity': 6, 'picked': True})
        ship._action_done()

        so.order_line.product_uom_qty = 7

        self.assertRecordValues(so.picking_ids.move_ids.sorted('id'), [
            {'location_id': stock_location.id, 'location_dest_id': out_location.id, 'product_uom_qty': 6.0, 'quantity': 6.0, 'state': 'done'},
            {'location_id': stock_location.id, 'location_dest_id': out_location.id, 'product_uom_qty': 1.0, 'quantity': 1.0, 'state': 'assigned'},
            {'location_id': out_location.id, 'location_dest_id': customer_location.id, 'product_uom_qty': 6.0, 'quantity': 6.0, 'state': 'done'},
        ])

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
                'price_unit': 1,
            })],
        })
        so.action_confirm()

        adv_wiz = self.env['sale.advance.payment.inv'].with_context(active_ids=[so.id]).create({
            'advance_payment_method': 'percentage',
            'amount': 5.0,
        })

        act = adv_wiz.create_invoices()
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
        picking_1.move_ids.write({'quantity': 1, 'picked': True})

        so_2 = self._get_new_sale_order()
        so_2.action_confirm()
        picking_2 = so_2.picking_ids
        picking_2.move_ids.write({'quantity': 2, 'picked': True})

        #multi-picking validation
        pick = picking_1 | picking_2
        wizard = Form.from_action(self.env, pick.button_validate()).save()
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
        - on PACK_1 picking: remove the destination package for the 2 units, validate
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

        pick_picking.move_ids.write({'quantity': 2, 'picked': True})
        pick_picking.action_put_in_pack()
        Form.from_action(self.env, pick_picking.button_validate()).save().process()

        pack_picking = so_1.picking_ids.filtered(lambda p: p.picking_type_id == warehouse.pack_type_id)
        pack_picking.move_line_ids.result_package_id = False
        pack_picking.move_ids.write({'quantity': 2, 'picked': True})
        pack_picking.button_validate()

        out_picking = so_1.picking_ids.filtered(lambda p: p.picking_type_id == warehouse.out_type_id)
        self.assertEqual(out_picking.move_line_ids.package_id.id, False)
        self.assertEqual(out_picking.move_line_ids.result_package_id.id, False)

        pick_picking_2 = so_1.picking_ids.filtered(lambda x: x.picking_type_id == warehouse.pick_type_id and x.state != 'done')

        pick_picking_2.move_ids.write({'quantity': 2, 'picked': True})
        package_2 = pick_picking_2.action_put_in_pack()
        Form.from_action(self.env, pick_picking_2.button_validate()).save().process()

        self.assertEqual(out_picking.move_line_ids.package_id.id, False)
        self.assertEqual(out_picking.move_line_ids.result_package_id.id, False)

        pack_picking_2 = so_1.picking_ids.filtered(lambda p: p.picking_type_id == warehouse.pack_type_id and p.state != 'done')

        pack_picking_2.move_ids.write({'quantity': 2, 'picked': True})
        pack_picking_2.button_validate()

        self.assertRecordValues(out_picking.move_line_ids, [{'result_package_id': False}, {'result_package_id': package_2.id}])

    def test_inventory_admin_no_backorder_not_own_sale_order(self):
        sale_order = self._get_new_sale_order()
        sale_order.action_confirm()
        pick = sale_order.picking_ids
        inventory_admin_user = self.env['res.users'].create({
            'name': "documents test basic user",
            'login': "dtbu",
            'email': "dtbu@yourcompany.com",
            'group_ids': [(6, 0, [
                self.ref('base.group_user'),
                self.ref('stock.group_stock_manager'),
                self.ref('sales_team.group_sale_salesman')])]
        })
        pick.with_user(inventory_admin_user).move_ids.write(
            {'quantity': 1, 'picked': True})
        Form.from_action(self.env(user=inventory_admin_user), pick.button_validate())\
            .save().process_cancel_backorder()

    def test_reduce_qty_ordered_no_backorder(self):
        """
        When validating a reduced picking, declining a backorder then reducing the quantity ordered on the SO line
        to match the quantity delivered, make sure that no additional picking is created.
        """

        so_1 = self._get_new_sale_order(amount=3, product=self.test_product_delivery)
        so_1.action_confirm()
        self.assertEqual(so_1.order_line.product_uom_qty, 3)
        self.assertEqual(len(so_1.picking_ids), 1)

        delivery_picking = so_1.picking_ids
        delivery_picking.move_ids.quantity = 2
        Form.from_action(self.env, delivery_picking.button_validate()).save().process_cancel_backorder()
        self.assertEqual(so_1.order_line.product_uom_qty, 3)
        self.assertEqual(so_1.order_line.qty_delivered, 2)

        so_1.write({'order_line': [(1, so_1.order_line.id, {'product_uom_qty': so_1.order_line.qty_delivered})]})
        self.assertEqual(len(so_1.picking_ids), 1)

    def test_decrease_sol_qty_to_zero(self):
        """
        2 steps delivery.
        SO with two products.
        Set the done quantity on the first picking.
        On the SO, cancel the qty of the first product:
        On the first picking, since the done quantity is already defined, it
        should only set the demand to zero.
        """
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        warehouse.delivery_steps = 'pick_ship'

        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [(0, 0, {
                'name': p.name,
                'product_id': p.id,
                'product_uom_qty': 1,
                'price_unit': p.list_price,
            }) for p in (
                self.product_a,
                self.product_b,
            )],
        })
        so.action_confirm()

        pick_picking = so.picking_ids
        pick_picking.move_ids.picked = True

        so.order_line[0].product_uom_qty = 0

        self.assertRecordValues(pick_picking.move_ids, [
            {'product_id': self.product_a.id, 'product_uom_qty': 0, 'quantity': 1, 'state': 'assigned'},
            {'product_id': self.product_b.id, 'product_uom_qty': 1, 'quantity': 1, 'state': 'assigned'},
        ])

    def test_create_so_return_with_tracked_product(self):
        """
        Creates a sale order with a tracked product, validates it and its delivery, then creates a
        return validates it and finally creates a second return.
        """
        self.product_a.tracking = 'serial'
        self.product_a.is_storable = True
        sn1 = self.env['stock.lot'].create({
            'name': 'SN0001',
            'product_id': self.product_a.id,
            'company_id': self.env.company.id,
        })
        self.env['stock.quant']._update_available_quantity(self.product_a, self.company_data['default_warehouse'].lot_stock_id, 1, lot_id=sn1)
        # Creates a sale order for 1 tracked product.
        sale_order = self._get_new_sale_order(amount=1, product=self.product_a)
        # validates the sale order, then validates the delivery.
        sale_order.action_confirm()
        self.assertTrue(sale_order.picking_ids)
        picking = sale_order.picking_ids
        picking.button_validate()

        # Checks the delivery amount (must be 1).
        self.assertEqual(sale_order.order_line.qty_delivered, 1)
        # Creates a return from the delivery picking.
        return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=picking.ids, active_id=picking.id,
            active_model='stock.picking'))
        return_wizard = return_picking_form.save()
        self.assertEqual(return_wizard.product_return_moves.quantity, 0)
        return_wizard.product_return_moves.quantity = 1

        # validates the return picking.
        res = return_wizard.action_create_returns()
        return_picking = self.env['stock.picking'].browse(res['res_id'])
        return_picking.button_validate()
        # Checks the delivery amount (must be 0).
        self.assertEqual(sale_order.order_line.qty_delivered, 0)
        return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=return_picking.ids, active_id=return_picking.id,
            active_model='stock.picking'))
        return_wizard = return_picking_form.save()
        self.assertEqual(return_wizard.product_return_moves.quantity, 0)
        return_wizard.product_return_moves.quantity = 1

        # validates the return picking.
        res = return_wizard.action_create_returns()
        return_picking_2 = self.env['stock.picking'].browse(res['res_id'])
        return_picking_2.button_validate()

    def test_2_steps_pull_and_decrease_sol_qty_to_zero(self):
        """
        2 steps delivery, special rules:
        - Pull
        - 'Cancel next move' enabled
        SO with one product
        On the SO, cancel the qty of the product
        On each picking, the SM should be canceled
        """
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        customer_location = self.env.ref('stock.stock_location_customers')

        warehouse.delivery_steps = 'pick_ship'
        warehouse.delivery_route_id.rule_ids = [
            (5, 0, 0),
            (0, 0, {
                'name': 'Pull out->custo',
                'action': 'pull',
                'location_src_id': warehouse.wh_output_stock_loc_id.id,
                'location_dest_id': customer_location.id,
                'picking_type_id': warehouse.out_type_id.id,
                'propagate_cancel': True,
                'procure_method': 'make_to_order',
            }),
            (0, 0, {
                'name': 'Pull stock->out',
                'action': 'pull',
                'location_src_id': warehouse.lot_stock_id.id,
                'location_dest_id': warehouse.wh_output_stock_loc_id.id,
                'picking_type_id': warehouse.pick_type_id.id,
                'propagate_cancel': True,
                'procure_method': 'make_to_stock',
            }),
        ]

        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [(0, 0, {
                'name': self.product_a.name,
                'product_id': self.product_a.id,
                'product_uom_qty': 1,
                'price_unit': self.product_a.list_price,
            })],
        })
        so.action_confirm()

        so.order_line.product_uom_qty = 0

        self.assertEqual(so.picking_ids.move_ids.mapped('state'), ['cancel', 'cancel'])

    def test_delivery_on_negative_delivered_qty(self):
        """
            Tests that returns created from SO lines with negative quantities update the delivered
            quantities negatively so that they appear on the corresponding invoice.
        """
        product = self.env['product.product'].create({
            'name': 'Super product',
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'lst_price': 100.0,
            'is_storable': True,
            'invoice_policy': 'delivery',
        })
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'state': 'draft',
            'order_line': [Command.create({
                'product_id': product.id,
                'product_uom_qty': -1,
            })],
        })
        sale_order.action_confirm()
        self.assertEqual(sale_order.order_line.qty_delivered, 0.0)
        self.assertEqual(sale_order.order_line.qty_to_invoice, 0.0)
        picking = self.env['stock.move'].browse(self.env['stock.move'].search([('sale_line_id', '=', sale_order.order_line.id)]).id).picking_id
        picking.action_confirm()
        picking.button_validate()
        self.assertEqual(sale_order.order_line.qty_delivered, -1.0)
        self.assertEqual(sale_order.order_line.qty_to_invoice, -1.0)

    def test_reduce_qty_on_partially_moved(self):
        """ In a three-steps delivery, with the first step (PICK) partially done with a backorder and the PACK step pending,
            ensure that reducing the SOL quantity will:
            - Decrease the backorder PICK first
            - Create a return PICK for the leftover quantity
            - Decrease the PACK for the same leftover quantity
            - Not create any OUT/IN move.
        """
        warehouse = self.company_data['default_warehouse']
        warehouse.delivery_steps = 'pick_pack_ship'
        product = self.env['product.product'].create({
            'name': 'To be delivered',
            'is_storable': True,
        })
        self.env['stock.quant']._update_available_quantity(product, warehouse.lot_stock_id, 10)
        with Form(self.env['sale.order']) as so_form:
            so_form.partner_id = self.partner_a
            with so_form.order_line.new() as line:
                line.product_id = product
                line.product_uom_qty = 10
            sale_order = so_form.save()
        sale_order.action_confirm()
        self.assertEqual(len(sale_order.picking_ids), 1)

        pick = sale_order.picking_ids
        self.assertEqual(pick.picking_type_id, warehouse.pick_type_id)
        pick.move_ids.write({'quantity': 6, 'picked': True})
        # Create backorder for missing qty
        pick._action_done()
        pick_backorder = pick.backorder_ids
        self.assertEqual(pick_backorder.move_ids.product_uom_qty, 4)

        pack = sale_order.picking_ids - (pick | pick_backorder)
        self.assertEqual(pack.picking_type_id, warehouse.pack_type_id)
        self.assertEqual(pack.move_ids.product_uom_qty, 6)

        # Reduce the intial SO demand to 5
        with Form(sale_order) as so_form:
            with so_form.order_line.edit(0) as line:
                line.product_uom_qty = 5
            sale_order = so_form.save()

        self.assertEqual(len(sale_order.picking_ids), 4, "PICK + PICK backorder + PACK + (new) PICK return")
        self.assertEqual(pick_backorder.state, 'cancel')
        self.assertEqual(pack.move_ids.product_uom_qty, 5)
        self.assertEqual(pack.state, 'assigned')
        pick_return = sale_order.picking_ids - (pick | pick_backorder | pack)
        self.assertEqual(pick_return.picking_type_id, warehouse.pick_type_id)
        self.assertEqual(pick_return.move_ids.product_uom_qty, 1)
        self.assertEqual(pick_return.location_dest_id, warehouse.lot_stock_id)
        self.assertEqual(pick_return.state, 'assigned')

    def test_return_partial_delivery(self):
        """
        Test that the qty_delivered is correctly computed when a return of backorder delivery is validated:
        - Set the delivery process to three steps.
        - Update the quantity of the product to 10.
        - Create a sales order to deliver 3 units.
        - Validate a pick for 1 unit and create a backorder.
        - Validate the pack for 1 unit.
        - Validate the backorder for 2 units.
        - Create and validate a return.
        Check that the qty_delivered is 0.
        """
        warehouse = self.company_data['default_warehouse']
        warehouse.delivery_steps = 'pick_pack_ship'
        product = self.env['product.product'].create({
            'name': 'To be delivered',
            'is_storable': True,
        })
        self.env['stock.quant']._update_available_quantity(product, warehouse.lot_stock_id, 10)
        with Form(self.env['sale.order']) as so_form:
            so_form.partner_id = self.partner_a
            with so_form.order_line.new() as line:
                line.product_id = product
                line.product_uom_qty = 3
            sale_order = so_form.save()
        sale_order.action_confirm()
        self.assertEqual(len(sale_order.picking_ids), 1)
        pick = sale_order.picking_ids
        self.assertEqual(pick.picking_type_id, warehouse.pick_type_id)
        pick.move_ids.write({'quantity': 1, 'picked': True})
        # Create backorder for missing qty
        pick._action_done()
        pick_backorder = pick.backorder_ids
        self.assertEqual(pick_backorder.move_ids.product_uom_qty, 2)
        # validate the pack for one unit
        pack_1 = sale_order.picking_ids - pick
        pack_1.move_ids.write({'quantity': 1, 'picked': True})
        pack_1._action_done()
        # validate the pick_backorder and then create the return
        pick_backorder.move_ids.write({'quantity': 2, 'picked': True})
        pick_backorder._action_done()
        self.assertEqual(pick_backorder.state, 'done')
        # Create return picking
        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=pick_backorder.ids, active_id=pick_backorder.sorted().ids[0],
            active_model='stock.picking'))
        return_wiz = stock_return_picking_form.save()
        return_wiz.product_return_moves.quantity = 2.0
        return_wiz.product_return_moves.to_refund = True
        res = return_wiz.action_create_returns()
        return_pick = self.env['stock.picking'].browse(res['res_id'])
        # Validate the return
        return_pick.move_ids.write({'quantity': 2, 'picked': True})
        return_pick.button_validate()
        # check the qty delivered in the SOL
        self.assertEqual(sale_order.order_line.qty_delivered, 0)

    def test_sale_order_cancel_with_cyclic_returns(self):
        """ Test Sale Order cancellation after recursive return creation causes cyclic stock moves. """
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                Command.create({
                    'product_id': self.product.id,
                })],
        })

        sale_order.action_confirm()
        self.assertEqual(sale_order.state, 'sale')

        picking = sale_order.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
        self.assertTrue(picking, "Delivery picking should exist.")

        return_wizard = self.env['stock.return.picking'].with_context(active_id=picking.id, active_model='stock.picking')
        return_wiz_1 = return_wizard.create({})
        return_res_1 = return_wiz_1.action_create_returns_all()
        return_picking_1 = self.env['stock.picking'].browse(return_res_1['res_id'])

        return_wizard2 = self.env['stock.return.picking'].with_context(active_id=return_picking_1.id, active_model='stock.picking')
        return_wiz_2 = return_wizard2.create({})
        return_wiz_2.action_create_returns_all()

        sale_order._action_cancel()
        self.assertEqual(sale_order.state, 'cancel')

    def test_sol_reserved_qty_wizard_3_steps_delivery(self):
        """
        Check that the reserved qty wizard related to a sol is computed from
        the pick move in 2+ step deliveries.
        """
        admin = self.env.ref('base.user_admin')
        admin.write({
            'email': 'mitchell.admin@example.com',
        })
        warehouse = self.env.ref('stock.warehouse0').with_user(admin)
        warehouse.delivery_steps = 'pick_pack_ship'
        product = self.product_a
        product.is_storable = True
        self.env['stock.quant']._update_available_quantity(product, warehouse.lot_stock_id, 10.0)
        sale_order = self.env['sale.order'].with_user(admin).create({
            'company_id': warehouse.company_id.id,
            'warehouse_id': warehouse.id,
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                'product_id': product.id,
                'product_uom_qty': 7.0,
                }),
            ],
        })
        sale_order.action_confirm()
        pick = sale_order.picking_ids.filtered(lambda p: p.location_id == warehouse.lot_stock_id)
        self.assertEqual(pick.move_line_ids.quantity, 7.0)
        self.assertEqual(sale_order.order_line.qty_available_today, 7.0)
        pick.move_ids.quantity = 7.0
        pick.move_ids.picked = True
        pick.button_validate()
        pack = sale_order.picking_ids - pick
        self.assertEqual(sale_order.order_line.qty_available_today, 7.0)
        pack.move_ids.quantity = 2.0
        pack.move_ids.picked = True
        Form.from_action(self.env(user=admin), pack.button_validate()).save().process()
        backorder = pack.backorder_ids
        ship = sale_order.picking_ids.filtered(lambda p: p.location_dest_id == self.env.ref('stock.stock_location_customers'))
        self.assertEqual(sum(backorder.move_line_ids.mapped('quantity')), 5.0)
        self.assertEqual(sum(ship.move_line_ids.mapped('quantity')), 2.0)
        self.assertEqual(sale_order.order_line.qty_available_today, 7.0)
        self.assertEqual(sale_order.order_line.qty_delivered, 0.0)
        backorder.move_ids.quantity = 5.0
        backorder.move_ids.picked = True
        backorder.button_validate()
        self.assertEqual(sum(ship.move_line_ids.mapped('quantity')), 7.0)
        self.assertEqual(sale_order.order_line.qty_available_today, 7.0)
        self.assertEqual(sale_order.order_line.qty_delivered, 0.0)
        ship.move_ids.quantity = 7.0
        ship.move_ids.picked = True
        ship.button_validate()
        self.assertEqual(sale_order.order_line.qty_available_today, 0.0)
        self.assertEqual(sale_order.order_line.qty_delivered, 7.0)

    def test_delivery_status(self):
        """
            Tests the delivery status of a sales order.
            If nothing was done: pending
            If some pickings were completed but nothing was actually delivery to the customer yet: started
            If not everything was delivered: partial
            If everything was delivered: full
        """
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        warehouse.delivery_steps = 'pick_ship'

        so = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'My Partner'}).id,
            'order_line': [
                Command.create({
                    'name': 'sol_p1',
                    'product_id': self.env['product.product'].create({'name': 'p1'}).id,
                    'product_uom_qty': 10,
                }),
            ],
        })
        so.action_confirm()
        self.assertEqual(so.delivery_status, 'pending')

        pick01 = so.picking_ids
        pick01.move_ids.write({'quantity': 10, 'picked': True})
        pick01.button_validate()
        self.assertEqual(so.delivery_status, 'started')

        ship01 = so.picking_ids.filtered(lambda p: p.picking_type_id == warehouse.out_type_id)
        ship01.move_ids.write({'quantity': 3, 'picked': True})
        Form.from_action(self.env, ship01.button_validate()).save().process()
        self.assertEqual(so.delivery_status, 'partial')

        ship02 = ship01.backorder_ids[0]
        ship02.move_ids.write({'quantity': 7, 'picked': True})
        ship02.button_validate()
        self.assertEqual(so.delivery_status, 'full')

    def test_so_delivery_ignores_shipping_policy_from_picking_type(self):
        picking_type_out = self.company_data['default_warehouse'].out_type_id
        picking_type_out.move_type = "direct"

        so = self._get_new_sale_order()
        # Ignore picking_type_out, use the value from SO
        so.picking_policy = "one"
        so.action_confirm()

        self.assertEqual(so.picking_ids[0].picking_type_id, picking_type_out)
        self.assertEqual(so.picking_ids[0].move_type, "one")

    def test_double_return_on_so(self):
        """
        Check that the return of a return of a delivery linked to an SO
        is seen as an outgoing move for the related procurements.
        """
        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'name': 'sol_p1',
                    'product_id': self.env['product.product'].create({'name': 'p1'}).id,
                    'product_uom_qty': 5,
                }),
            ],
        })
        so.action_confirm()
        delivery = so.picking_ids
        delivery.button_validate()
        self.assertEqual(so.order_line.qty_delivered, 5.0)
        # create and validate a return
        return_form = Form(self.env['stock.return.picking']
            .with_context(active_id=delivery.id,
            active_model='stock.picking'))
        return_wiz = return_form.save()
        return_wiz.product_return_moves.write({'quantity': 5.0})
        res = return_wiz.action_create_returns()
        do_return = self.env['stock.picking'].browse(res['res_id'])
        do_return.button_validate()
        self.assertEqual(so.order_line.qty_delivered, 0.0)
        # create and validate the return of the return
        return_form = Form(self.env['stock.return.picking']
            .with_context(active_id=do_return.id,
            active_model='stock.picking'))
        return_wiz = return_form.save()
        return_wiz.product_return_moves.write({'quantity': 5.0})
        res = return_wiz.action_create_returns()
        do_return_return = self.env['stock.picking'].browse(res['res_id'])
        do_return_return.button_validate()
        self.assertEqual(so.order_line.qty_delivered, 5.0)
        with Form(so) as so_form:
            with so_form.order_line.edit(0) as line_form:
                line_form.product_uom_qty = 8.0
        delivery_2 = so.picking_ids - delivery - do_return - do_return_return
        self.assertTrue(delivery_2)
        self.assertEqual(delivery_2.move_ids.product_uom_qty, 3.0)
        self.assertEqual(so.order_line.qty_delivered, 5.0)

    def test_warehouse_redirect_warnings(self):
        """
        Check that the correct warnings are raised when you try to confirm
        a SO for a storable product without warehouse.
        """
        new_company = self.env['res.company'].create({'name': 'Company 2'})
        # Warhouses are created for new companies in test mode but not IRL
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', new_company.id)], limit=1)
        warehouse.active = False
        storable_product = self.env['product.product'].create({
            'name': 'Lovely Product',
            'is_storable': True,
        })
        so = self.env['sale.order'].with_company(new_company).create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'name': storable_product.name,
                    'product_id': storable_product.id,
                    'product_uom_qty': 1,
                }),
            ],
        })
        # Since you dont have any warehouse for your company  you should raise a RedirectWarning
        error_message = "Please create a warehouse for company Company 2."
        with self.assertRaisesRegex(RedirectWarning, error_message), self.env.cr.savepoint():
            so.with_company(new_company).action_confirm()
        warehouse.active = True
        # Since you have a warehouse which is not linked to the SO you should raise a UserError
        error_message = "You must set a warehouse on your sale order to proceed."
        with self.assertRaisesRegex(UserError, error_message), self.env.cr.savepoint():
            so.with_company(new_company).action_confirm()
        # check the flow with 2 available warehouses for that company
        self.env['stock.warehouse'].create({'name': 'Warehouse 2', 'code': 'WH2', 'company_id': new_company.id})
        # Since you have a warehouse which is not linked to the SO you should raise a UserError
        error_message = "You must set a warehouse on your sale order to proceed."
        with self.assertRaisesRegex(UserError, error_message), self.env.cr.savepoint():
            so.with_company(new_company).action_confirm()

    def test_custom_delivery_route_new_sale_line(self):
        """
        Create a custom delivery route Stock -> Transit -> Customer that uses pull rules.
        Ensure that the validating the move from Stock to Transit does NOT create a new SaleOrderLine.
        """
        warehouse = self.company_data['default_warehouse']
        stock_location = warehouse.lot_stock_id
        customer_location = self.env.ref('stock.stock_location_customers')
        transit_location = self.env['stock.location'].create({
            'name': 'Transit',
            'usage': 'transit',
            'location_id': warehouse.view_location_id.id,
        })
        warehouse.pick_type_id.default_location_dest_id = transit_location

        warehouse.delivery_route_id = self.env['stock.route'].create({
            'name': '2 Steps Pull Delivery Route',
            'warehouse_selectable': True,
            'warehouse_ids': [(4, warehouse.id)],
            'rule_ids': [
                Command.create({
                    'name': 'Stock to Output',
                    'action': 'pull',
                    'location_src_id': stock_location.id,
                    'location_dest_id': transit_location.id,
                    'picking_type_id': warehouse.pick_type_id.id,
                    'procure_method': 'make_to_stock',
                }),
                Command.create({
                    'name': 'Output to Customer',
                    'action': 'pull',
                    'location_src_id': transit_location.id,
                    'location_dest_id': customer_location.id,
                    'picking_type_id': warehouse.out_type_id.id,
                    'procure_method': 'make_to_order',
                })
            ]
        })

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'name': 'Test Product',
                'product_id': self.product_a.id,
                'product_uom_qty': 1.0,
                'price_unit': 1.0,
            })],
        })
        sale_order.action_confirm()

        # Ensure the created pickings follow the expected route
        pickings = sale_order.picking_ids
        self.assertEqual(len(pickings), 2, "Expected two pickings: Stock->Output and Output->Customer")
        self.assertEqual(pickings[0].location_id, stock_location)
        self.assertEqual(pickings[0].location_dest_id, transit_location)
        self.assertEqual(pickings[1].location_id, transit_location)
        self.assertEqual(pickings[1].location_dest_id, customer_location)

        pickings[0].move_ids.picked = True
        pickings[0].button_validate()

        self.assertEqual(pickings[0].state, 'done')
        self.assertEqual(len(sale_order.order_line), 1)

    def test_multi_step_product_forecast_availability(self):
        """
        Test that forecast availability(icon) widget info on the Sales Order correctly appears green
        when enough stock is available in a 2-step/3-step delivery.
        """
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        warehouse.delivery_steps = 'pick_ship'

        # Make quantity available for the product.
        self.env['stock.quant']._update_available_quantity(self.new_product, warehouse.lot_stock_id, 1)

        so = self._get_new_sale_order(product=self.new_product, amount=1)
        so.action_confirm()

        self.assertEqual(
            so.picking_ids.move_ids.forecast_availability, 1.0,
            "Forecast availability should be 1.0 because 1.0 quantity is available."
            "So forecast availability icon should appear green."
        )
        self.assertEqual(
            so.order_line.free_qty_today, 1.0,
            "Free quantity today should be 1.0, indicating the quantity is usable for this SO."
        )

    def test_extra_return_product_so_sequence(self):
        """
        Ensure returned products are added to the bottom of the SO
        """
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {'product_id': self.product_a.id, 'product_uom_qty': 2, 'sequence': 42}),
                (0, 0, {'product_id': self.product_b.id, 'product_uom_qty': 3, 'sequence': 43}),
            ],
        })
        sale_order.action_confirm()
        picking = sale_order.picking_ids
        picking.button_validate()
        return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_id=picking.id, active_model='stock.picking'))
        with return_picking_form.product_return_moves.new() as line:
            line.product_id = self.new_product
            line.quantity = 4
        return_wiz = return_picking_form.save()
        res = return_wiz.action_create_returns()
        return_pick = self.env['stock.picking'].browse(res['res_id'])
        return_pick.button_validate()
        self.assertEqual(sale_order.order_line.mapped('sequence'), [42, 43, 44])

    def test_move_description(self):
        """
        Test that the move description is correctly propagated to the move description
        """
        # product with all description items: delivery description, attribute variant value, attribute no variant value
        product_with_description = self.env['product.template'].create({
            'name': 'Product with description',
            'description_pickingout': 'Deliver with care',
            'description_sale': 'Sale description',
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': self.color_attribute.id,
                    'value_ids': [Command.set(self.color_attribute.value_ids.ids)],
                }),
                Command.create({
                    'attribute_id': self.no_variant_attribute.id,
                    'value_ids': [Command.set(self.no_variant_attribute.value_ids.ids)],
                })
            ]
        })
        so = self._get_new_sale_order(
            product=product_with_description.product_variant_ids.filtered(lambda p: p.product_template_attribute_value_ids.name == 'red'),
            amount=1,
            sol_vals={
                'product_no_variant_attribute_value_ids': [Command.set(product_with_description.attribute_line_ids[1].product_template_value_ids[0].ids)],
            }
        )
        self.assertEqual(so.order_line.name, 'Product with description (red)\nSale description\nNo variant: extra')
        so.order_line.name += '\nRandom sale notes'
        so.action_confirm()
        self.assertEqual(so.picking_ids.move_ids.description_picking, 'No variant: extra\nDeliver with care')

    def test_move_description_uses_custom_attribute_values(self):
        """
        Check that the move description of prodcut variants uses
        the custom attribute values as expected.
        """
        self.env['res.lang']._activate_lang('fr_FR')
        product = self.new_product
        product.with_context(lang='fr_FR').name = "French Sofa"
        self.partner_b.lang = 'fr_FR'
        attribute_line = self.env['product.template.attribute.line'].create({
            'product_tmpl_id': self.product_template_sofa.id,
            'attribute_id': self.no_variant_attribute.id,
            'value_ids': [
                Command.set([self.no_variant_attribute.value_ids[0].id])
            ],
        })
        order_line_vals = {
            'product_id': product.id,
            'product_custom_attribute_value_ids': [
                Command.create({
                    'custom_product_template_attribute_value_id':
                        attribute_line.product_template_value_ids.id,
                    'custom_value': 'Best',
                })
            ]
        }
        sale_orders = self.env['sale.order'].create([
            {
                'partner_id': partner.id,
                'order_line': [Command.create(order_line_vals)],
            } for partner in [self.partner_a, self.partner_b]
        ])
        sale_orders.action_confirm()
        self.assertEqual(
            sale_orders.picking_ids.move_ids.mapped('description_picking'),
            ['No variant: extra: Best', 'No variant: extra: Best\nFrench Sofa']
        )

    def test_multicompany_transit_with_one_company_for_user(self):
        """ Check that the inter-company transit location is created when
        user has only one allowed company. """
        company_a = self.env['res.company'].create({'name': 'Company A'})
        company_b = self.env['res.company'].create({'name': 'Company B'})
        user_a = self.env['res.users'].create({
            'name': 'user only in company a',
            'login': 'user a',
            'company_id': company_a.id,
            'company_ids': [Command.link(company_a.id)],
            'group_ids': [Command.link(self.env.ref('sales_team.group_sale_salesman').id)],
        })
        product = self.new_product
        so = self.env['sale.order'].with_user(user_a).create({
            'partner_id': company_b.partner_id.id,
            'order_line': [
                Command.create({
                    'product_id': product.id,
                }),
            ],
        })
        so.action_confirm()
        intercom_location = self.env.ref('stock.stock_location_inter_company')
        self.assertEqual(so.picking_ids.location_dest_id, intercom_location)
        self.assertEqual(so.picking_ids.move_ids.location_dest_id, intercom_location)

    def test_sale_order_line_quantity_forecast_widget_display(self):
        """
        Ensure the availability widget is visible when the sale order line is linked to a move, and hidden if the related moves are all cancelled or done.
        """
        self.product_a.is_storable = True
        self.env['stock.quant']._update_available_quantity(self.product_a, self.company_data['default_warehouse'].lot_stock_id, 15)

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({'product_id': self.product_a.id, 'product_uom_qty': 5}),
            ],
        })
        sale_order.action_confirm()
        self.assertTrue(sale_order.order_line.display_qty_widget)
        picking = sale_order.picking_ids
        picking.move_ids[0].quantity = 2
        backorder_wizard_dict = picking.button_validate()
        backorder_wizard_form = Form.from_action(self.env, backorder_wizard_dict)
        backorder_wizard_form.save().process_cancel_backorder()
        self.assertFalse(sale_order.order_line.display_qty_widget)

    def test_create_route_update_so_quantity(self):
        """
        Check that moves created from user-created push rules does not interfere with updating the
        quantity of pickings when the quanityt of the SO is updated
        """
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        warehouse.delivery_steps = 'pick_pack_ship'
        stock_location = warehouse.lot_stock_id
        pack_location, out_location, _ = warehouse.delivery_route_id.rule_ids.picking_type_id.default_location_dest_id

        self.product_a.is_storable = True
        self.env['stock.quant']._update_available_quantity(self.product_a, stock_location, 5)
        loc_perso = self.env['stock.location'].create({
                'name': 'Locperso',
                'location_id': stock_location.id,
        })
        warehouse.delivery_route_id.rule_ids = [
            Command.create({
                'name': 'Push stock->Locperso',
                'action': 'push',
                'location_src_id': loc_perso.id,
                'location_dest_id': out_location.id,
                'picking_type_id': warehouse.int_type_id.id,
                'propagate_cancel': False,
                'procure_method': 'make_to_stock',
            }),
        ]
        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'name': self.product_a.name,
                'product_id': self.product_a.id,
                'product_uom_qty': 1,
                'price_unit': self.product_a.list_price,
            })],
        })
        so.action_confirm()
        picking_1 = so.picking_ids
        self.assertRecordValues(picking_1, [
            {'location_id': stock_location.id, 'location_dest_id': pack_location.id},
        ])
        picking_1.location_dest_id = loc_perso
        picking_1.button_validate()
        so.order_line.product_uom_qty = 2

        self.assertRecordValues(so.picking_ids.move_ids.sorted("id"), [
            {'location_id': stock_location.id, 'location_dest_id': loc_perso.id, 'quantity': 1},
            {'location_id': loc_perso.id, 'location_dest_id': out_location.id, 'quantity': 1},
            {'location_id': stock_location.id, 'location_dest_id': pack_location.id, 'quantity': 1},
        ])

    def test_update_picking_sale_order(self):
        """ Checks that updating the SO directly on the picking form properly updates the move as well.
        """
        self.new_product.is_storable = False
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_a.id,
                    'product_uom_qty': 1,
                })
            ]
        })
        sale_order.action_confirm()
        so_delivery = sale_order.picking_ids
        self.assertEqual(so_delivery.move_ids.sale_line_id, sale_order.order_line)

        new_delivery = self.env['stock.picking'].create({
            'picking_type_id': so_delivery.picking_type_id.id,
            'location_id': so_delivery.location_id.id,
            'location_dest_id': so_delivery.location_dest_id.id,
            'move_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'product_uom_qty': 2,
                    'location_id': so_delivery.location_id.id,
                    'location_dest_id': so_delivery.location_dest_id.id,
                }),
                Command.create({
                    'product_id': self.new_product.id,
                    'product_uom_qty': 3,
                    'location_id': so_delivery.location_id.id,
                    'location_dest_id': so_delivery.location_dest_id.id,
                }),
            ],
        })
        new_delivery.action_confirm()
        self.assertFalse(new_delivery.sale_id)
        self.assertRecordValues(new_delivery.move_ids, [
            {'product_id': self.product_a.id, 'sale_line_id': False},
            {'product_id': self.new_product.id, 'sale_line_id': False},
        ])

        new_delivery.sale_id = sale_order
        # Only corresponding lines should be set, but missing SO line will be created at picking's validation.
        self.assertRecordValues(new_delivery.move_ids, [
            {'product_id': self.product_a.id, 'sale_line_id': sale_order.order_line.id},
            {'product_id': self.new_product.id, 'sale_line_id': False},
        ])

        new_delivery.button_validate()
        self.assertRecordValues(new_delivery.move_ids, [
            {'product_id': self.product_a.id, 'sale_line_id': sale_order.order_line[0].id},
            {'product_id': self.new_product.id, 'sale_line_id': sale_order.order_line[1].id},
        ])
        self.assertRecordValues(sale_order.order_line, [
            {'product_id': self.product_a.id, 'product_uom_qty': 1, 'qty_delivered': 2},
            {'product_id': self.new_product.id, 'product_uom_qty': 0, 'qty_delivered': 3},
        ])

        # Remove sale order from the original delivery. Its validation should no longer impact the sale order.
        so_delivery.sale_id = False
        self.assertRecordValues(so_delivery.move_ids, [
            {'product_id': self.product_a.id, 'sale_line_id': False},
        ])
        so_delivery.button_validate()
        self.assertRecordValues(sale_order.order_line, [
            {'product_id': self.product_a.id, 'product_uom_qty': 1, 'qty_delivered': 2},
            {'product_id': self.new_product.id, 'product_uom_qty': 0, 'qty_delivered': 3},
        ])

    def test_sale_line_route_overrides_product_routes(self):
        """
        Test that a route defined on the sale order line takes precedence over
        product-level routes when selecting the procurement rule.
        """
        warehouse = self.company_data['default_warehouse']
        customer_location = self.env.ref('stock.stock_location_customers')
        transit_location = self.env['stock.location'].create({
            'name': 'Transit',
            'usage': 'transit',
            'location_id': warehouse.view_location_id.id,
        })

        route_product, route_so = self.env['stock.route'].create([
            {
                'name': 'Route set in the product',
                'warehouse_ids': [Command.link(warehouse.id)],
                'rule_ids': [
                    Command.create({
                        'name': 'Stock to transit',
                        'action': 'pull',
                        'location_src_id': warehouse.lot_stock_id.id,
                        'location_dest_id': transit_location.id,
                        'picking_type_id': warehouse.int_type_id.id,
                        'procure_method': 'make_to_stock',
                    }),
                    Command.create({
                        'name': 'Transit to Customer',
                        'action': 'pull',
                        'location_src_id': transit_location.id,
                        'location_dest_id': customer_location.id,
                        'picking_type_id': warehouse.out_type_id.id,
                        'procure_method': 'make_to_order',
                    }),
                ],
            },
            {
                'name': 'Route set in the SOL',
                'warehouse_ids': [Command.link(warehouse.id)],
                'sale_selectable': True,
                'rule_ids': [
                    Command.create({
                        'name': 'Stock to transit',
                        'action': 'pull',
                        'location_src_id': warehouse.lot_stock_id.id,
                        'location_dest_id': transit_location.id,
                        'picking_type_id': warehouse.int_type_id.id,
                        'procure_method': 'make_to_stock',
                    }),
                    Command.create({
                        'name': 'Transit to Customer',
                        'action': 'pull',
                        'location_src_id': transit_location.id,
                        'location_dest_id': customer_location.id,
                        'picking_type_id': warehouse.out_type_id.id,
                        'procure_method': 'make_to_order',
                    }),
                ],
            },
        ])

        product = self.env['product.product'].create({
            'name': 'SuperProduct',
            'is_storable': True,
            'route_ids': [route_product.id],
        })

        so = self.env['sale.order'].create([
            {
                'partner_id': self.partner_a.id,
                'order_line': [Command.create(
                    {
                        'name': product.name,
                        'product_id': product.id,
                        'product_uom_qty': 8.0,
                        'price_unit': product.list_price,
                        'route_ids': [route_so.id],
                    }),
                ],
            },
        ])
        so.action_confirm()

        self.assertRecordValues(so.picking_ids.move_ids.rule_id, [{'route_id': route_so.id}] * 2)

    def test_set_sale_reference_on_delivery(self):
        """
        Check that linking a delivery to a sale order sets its reference accordingly
        """
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        delivery = self.env['stock.picking'].create({
            'picking_type_id': warehouse.out_type_id.id,
            'location_id': warehouse.lot_stock_id.id,
            'location_dest_id': self.ref('stock.stock_location_customers'),
            'move_ids': [Command.create({
                'product_id': self.product.id,
                'product_uom_qty': 2,
                'product_uom': self.product.uom_id.id,
                'location_id': warehouse.lot_stock_id.id,
                'location_dest_id': self.ref('stock.stock_location_customers'),
            })],
        })
        self.assertFalse(delivery.reference_ids | delivery.move_ids.reference_ids)
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
        })
        delivery.sale_id = sale_order
        self.assertEqual(delivery.reference_ids.sale_ids, sale_order)
        self.assertEqual(delivery.move_ids.reference_ids, delivery.reference_ids)

    def test_sale_partner_propagation_3_step_pull(self):
        """
        Check that the customer of an SO is propageted to all moves of the
        pull chain in multi-step deliveries.
        """
        # delivery_route = self.warehouse_3_steps_pull.delivery_route_id
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'warehouse_id':  self.warehouse_3_steps_pull.id,
            'order_line': [Command.create({
                'product_id': self.product_a.id,
                'product_uom_qty': 1,
            })]
        })
        sale_order.action_confirm()
        self.assertRecordValues(sale_order.picking_ids.sorted(lambda p: p.picking_type_id.name)[::-1], [
            {'partner_id': self.partner_a.id, 'picking_type_id': self.warehouse_3_steps_pull.pick_type_id.id},
            {'partner_id': self.partner_a.id, 'picking_type_id': self.warehouse_3_steps_pull.pack_type_id.id},
            {'partner_id': self.partner_a.id, 'picking_type_id': self.warehouse_3_steps_pull.out_type_id.id},
        ])

    def test_compute_sale_order_count_with_stock_user(self):
        """Test that `sale_order_count` only counts sale orders
        accessible to the current stock user.

        A stock user can compute `sale_order_count` for a serial number,
        but the result only includes sale orders that the user has
        read access to (i.e. their own sale orders in this scenario).
        """
        user = new_test_user(self.env, login='fgh',
                             groups='base.group_user,stock.group_stock_user, sales_team.group_sale_salesman')
        self.new_product.tracking = 'lot'
        lot = self.env['stock.lot'].create({
            'name': 'SN001',
            'product_id': self.new_product.id,
        })
        self.env['stock.quant']._update_available_quantity(self.new_product, self.company_data['default_warehouse'].lot_stock_id, 2, lot_id=lot)
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'product_id': self.new_product.id,
                'product_uom_qty': 1.0,
            })],
        })
        sale_order.action_confirm()
        sale_order.picking_ids.button_validate()
        self.assertEqual(sale_order.picking_ids.state, 'done')
        self.assertEqual(lot.with_user(user).sale_order_count, 0)
        sale_order_2 = self.env['sale.order'].with_user(user).create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'product_id': self.new_product.id,
                'product_uom_qty': 1.0,
            })],
        })
        sale_order_2.action_confirm()
        sale_order_2.picking_ids.button_validate()
        self.assertEqual(sale_order_2.picking_ids.state, 'done')
        lot.invalidate_recordset()
        self.assertEqual(lot.with_user(user).sale_order_count, 1)
        self.assertEqual(lot.with_user(user).sale_order_ids, sale_order_2)

    def test_invoice_zero_quantity_after_delivery_fifo(self):
        """
        Posting an invoice with quantity = 0 after delivery
        """
        self.env.company.write({
            'cost_method': 'fifo',
            'inventory_valuation': 'real_time',
        })

        sale = self._get_new_sale_order(product=self.new_product, amount=1)
        sale.action_confirm()

        picking = sale.picking_ids
        self.assertEqual(len(picking), 1)

        picking.move_ids.quantity = 1
        picking.button_validate()

        invoice = sale._create_invoices()
        invoice.invoice_line_ids.quantity = 0
        invoice.action_post()

        self.assertEqual(invoice.state, 'posted')
