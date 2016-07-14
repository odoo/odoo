# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp.addons.sale.tests.test_sale_common import TestSale


class TestSaleStock(TestSale):
    def test_00_sale_stock_return(self):
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

        # confirm our standard so
        self.so.action_confirm()

        # deliver completely
        pick = self.so.picking_ids
        pick.force_assign()
        pick.pack_operation_product_ids.write({'qty_done': 5})
        pick.do_new_transfer()

        # Create invoice
        inv_1_id = self.so.action_invoice_create()
        self.inv_1 = self.env['account.invoice'].browse(inv_1_id)
        self.inv_1.signal_workflow('invoice_open')

        # Create return picking
        stockreturnpicking = self.env['stock.return.picking']
        default_data = stockreturnpicking.with_context(active_ids=pick.ids, active_id=pick.ids[0]).default_get(['move_dest_exists', 'original_location_id', 'product_return_moves', 'parent_location_id', 'location_id'])
        return_wiz = stockreturnpicking.with_context(active_ids=pick.ids, active_id=pick.ids[0]).create(default_data)
        return_wiz.product_return_moves.quantity = 2.0 # Return only 2
        return_wiz.product_return_moves.to_refund_so = True # Refund these 2
        res = return_wiz.create_returns()
        return_pick = self.env['stock.picking'].browse(res['res_id'])

        # Validate picking
        return_pick.force_assign()
        return_pick.pack_operation_product_ids.write({'qty_done': 2})
        return_pick.do_new_transfer()

        # Check invoice
        self.assertEqual(self.so.invoice_status, 'to invoice', 'Sale Stock: so invoice_status should be "to invoice" instead of "%s" after picking return' % self.so.invoice_status)
        self.assertEqual(self.so.order_line[0].qty_delivered, 3.0, 'Sale Stock: delivered quantity should be 3.0 instead of "%s" after picking return' % self.so.order_line[0].qty_delivered)
        # let's do an invoice with refunds
        adv_wiz = self.env['sale.advance.payment.inv'].with_context(active_ids=[self.so.id]).create({
            'advance_payment_method': 'all',
        })
        adv_wiz.with_context(open_invoices=True).create_invoices()
        self.inv_2 = self.so.invoice_ids.filtered(lambda r: r.state == 'draft')
        self.assertEqual(self.inv_2.invoice_line_ids[0].quantity, 2.0, 'Sale Stock: refund quantity on the invoice should be 2.0 instead of "%s".' % self.inv_2.invoice_line_ids[0].quantity)
        self.assertEqual(self.so.invoice_status, 'no', 'Sale Stock: so invoice_status should be "no" instead of "%s" after invoicing the return' % self.so.invoice_status)
