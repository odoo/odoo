# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale.tests.test_sale_common import TestSale
from odoo.exceptions import UserError
from odoo.tests import Form, tagged


@tagged('post_install', '-at_install')
class TestSaleStock(TestSale):
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
        pick_2 = self.so.picking_ids[0]
        pick_2.move_lines.write({'quantity_done': 1})
        self.assertIsNone(pick_2.button_validate(), 'Sale Stock: second picking should be final without need for a backorder')
        self.assertEqual(self.so.invoice_status, 'to invoice', 'Sale Stock: so invoice_status should be "to invoice" after complete delivery')
        del_qties = [sol.qty_delivered for sol in self.so.order_line]
        del_qties_truth = [2.0 if sol.product_id.type in ['product', 'consu'] else 0.0 for sol in self.so.order_line]
        self.assertEqual(del_qties, del_qties_truth, 'Sale Stock: delivered quantities are wrong after complete delivery')
        # Without timesheet, we manually set the delivered qty for the product serv_del
        self.so.order_line[1]['qty_delivered'] = 2.0
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
        self.assertTrue(self.so.order_line[0].product_updatable)
        self.so.action_confirm()
        self.so.order_line._compute_product_updatable()
        self.assertFalse(self.so.order_line[0].product_updatable)
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
            .with_context(active_ids=pick.ids, active_id=pick.ids[0],
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
        self.assertAlmostEqual(self.so.order_line[0].qty_delivered, 3.0, msg='Sale Stock: delivered quantity should be 3.0 instead of "%s" after picking return' % self.so.order_line[0].qty_delivered)
        # let's do an invoice with refunds
        adv_wiz = self.env['sale.advance.payment.inv'].with_context(active_ids=[self.so.id]).create({
            'advance_payment_method': 'delivered',
        })
        adv_wiz.with_context(open_invoices=True).create_invoices()
        self.inv_2 = self.so.invoice_ids.filtered(lambda r: r.state == 'draft')
        self.assertAlmostEqual(self.inv_2.invoice_line_ids[0].quantity, 2.0, msg='Sale Stock: refund quantity on the invoice should be 2.0 instead of "%s".' % self.inv_2.invoice_line_ids[0].quantity)
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
        Test that updating multiple sale order lines after a succesful delivery creates a single picking containing
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
        res_dict = self.so.picking_ids[0].button_validate()
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
                (1, self.so.order_line[0].id, {'product_uom_qty': 2}),
                (1, self.so.order_line[1].id, {'product_uom_qty': 2}),
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
        res_dict = self.so.picking_ids[0].button_validate()
        wizard = self.env[(res_dict.get('res_model'))].browse(res_dict.get('res_id'))
        wizard.process()
        self.assertEquals(self.so.picking_ids[0].state, "done")

        # update the two original sale order lines
        self.so.write({
            'order_line': [
                (1, self.so.order_line[0].id, {'product_uom_qty': 2}),
                (1, self.so.order_line[1].id, {'product_uom_qty': 2}),
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