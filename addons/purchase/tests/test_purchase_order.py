# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.addons.account.tests.account_test_classes import AccountingTestCase


class TestPurchaseOrder(AccountingTestCase):

    def setUp(self):
        super(TestPurchaseOrder, self).setUp()
        # Useful models
        self.PurchaseOrder = self.env['purchase.order']
        self.PurchaseOrderLine = self.env['purchase.order.line']
        self.AccountInvoice = self.env['account.invoice']
        self.AccountInvoiceLine = self.env['account.invoice.line']
        self.partner_id = self.env.ref('base.res_partner_1')
        self.product_id_1 = self.env.ref('product.product_product_8')
        self.product_id_2 = self.env.ref('product.product_product_11')

        (self.product_id_1 | self.product_id_2).write({'purchase_method': 'purchase'})
        self.po_vals = {
            'partner_id': self.partner_id.id,
            'order_line': [
                (0, 0, {
                    'name': self.product_id_1.name,
                    'product_id': self.product_id_1.id,
                    'product_qty': 5.0,
                    'product_uom': self.product_id_1.uom_po_id.id,
                    'price_unit': 500.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                }),
                (0, 0, {
                    'name': self.product_id_2.name,
                    'product_id': self.product_id_2.id,
                    'product_qty': 5.0,
                    'product_uom': self.product_id_2.uom_po_id.id,
                    'price_unit': 250.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                })],
        }


    def test_00_purchase_order_flow(self):

        # Ensure product_id_2 doesn't have res_partner_1 as supplier
        if self.partner_id in self.product_id_2.seller_ids.mapped('name'):
            id_to_remove = self.product_id_2.seller_ids.filtered(lambda r: r.name == self.partner_id).ids[0] if self.product_id_2.seller_ids.filtered(lambda r: r.name == self.partner_id) else False
            if id_to_remove:
                self.product_id_2.write({
                    'seller_ids': [(2, id_to_remove, False)],
                })
        self.assertFalse(self.product_id_2.seller_ids.filtered(lambda r: r.name == self.partner_id), 'Purchase: the partner should not be in the list of the product suppliers')

        self.po = self.PurchaseOrder.create(self.po_vals)
        self.assertTrue(self.po, 'Purchase: no purchase order created')
        self.assertEqual(self.po.invoice_status, 'no', 'Purchase: PO invoice_status should be "Not purchased"')
        self.assertEqual(self.po.order_line.mapped('qty_received'), [0.0, 0.0], 'Purchase: no product should be received"')
        self.assertEqual(self.po.order_line.mapped('qty_invoiced'), [0.0, 0.0], 'Purchase: no product should be invoiced"')

        self.po.button_confirm()
        self.assertEqual(self.po.state, 'purchase', 'Purchase: PO state should be "Purchase"')
        self.assertEqual(self.po.invoice_status, 'to invoice', 'Purchase: PO invoice_status should be "Waiting Invoices"')

        self.assertTrue(self.product_id_2.seller_ids.filtered(lambda r: r.name == self.partner_id), 'Purchase: the partner should be in the list of the product suppliers')

        seller = self.product_id_2._select_seller(partner_id=self.partner_id, quantity=2.0, date=self.po.date_planned, uom_id=self.product_id_2.uom_po_id)
        price_unit = seller.price if seller else 0.0
        if price_unit and seller and self.po.currency_id and seller.currency_id != self.po.currency_id:
            price_unit = seller.currency_id.compute(price_unit, self.po.currency_id)
        self.assertEqual(price_unit, 250.0, 'Purchase: the price of the product for the supplier should be 250.0.')

        self.assertEqual(self.po.picking_count, 1, 'Purchase: one picking should be created"')
        self.picking = self.po.picking_ids[0]
        self.picking.force_assign()
        self.picking.move_line_ids.write({'qty_done': 5.0})
        self.picking.button_validate()
        self.assertEqual(self.po.order_line.mapped('qty_received'), [5.0, 5.0], 'Purchase: all products should be received"')

        self.invoice = self.AccountInvoice.create({
            'partner_id': self.partner_id.id,
            'purchase_id': self.po.id,
            'account_id': self.partner_id.property_account_payable_id.id,
            'type': 'in_invoice',
        })
        self.invoice.purchase_order_change()
        self.assertEqual(self.po.order_line.mapped('qty_invoiced'), [5.0, 5.0], 'Purchase: all products should be invoiced"')

    def test_02_po_return(self):
        """
        Test a PO with a product on Incoming shipment. Validate the PO, then do a return
        of the picking with Refund.
        """
        # Draft purchase order created
        self.po = self.env['purchase.order'].create(self.po_vals)
        self.assertTrue(self.po, 'Purchase: no purchase order created')
        self.assertEqual(self.po.order_line.mapped('qty_received'), [0.0, 0.0], 'Purchase: no product should be received"')
        self.assertEqual(self.po.order_line.mapped('qty_invoiced'), [0.0, 0.0], 'Purchase: no product should be invoiced"')

        self.po.button_confirm()
        self.assertEqual(self.po.state, 'purchase', 'Purchase: PO state should be "Purchase"')
        self.assertEqual(self.po.invoice_status, 'to invoice', 'Purchase: PO invoice_status should be "Waiting Invoices"')

        # Confirm the purchase order
        self.po.button_confirm()
        self.assertEqual(self.po.state, 'purchase', 'Purchase: PO state should be "Purchase')
        self.assertEqual(self.po.picking_count, 1, 'Purchase: one picking should be created"')
        self.picking = self.po.picking_ids[0]
        self.picking.force_assign()
        self.picking.move_line_ids.write({'qty_done': 5.0})
        self.picking.button_validate()
        self.assertEqual(self.po.order_line.mapped('qty_received'), [5.0, 5.0], 'Purchase: all products should be received"')

        #After Receiving all products create vendor bill.
        self.invoice = self.AccountInvoice.create({
            'partner_id': self.partner_id.id,
            'purchase_id': self.po.id,
            'account_id': self.partner_id.property_account_payable_id.id,
            'type': 'in_invoice',
        })
        self.invoice.purchase_order_change()
        self.invoice.invoice_validate()
        self.assertEqual(self.po.order_line.mapped('qty_invoiced'), [5.0, 5.0], 'Purchase: all products should be invoiced"')

        # Check quantity received
        received_qty = sum(pol.qty_received for pol in self.po.order_line)
        self.assertEqual(received_qty, 10.0, 'Purchase: Received quantity should be 10.0 instead of %s after validating incoming shipment' % received_qty)

        # Create return picking
        StockReturnPicking = self.env['stock.return.picking']
        pick = self.po.picking_ids
        default_data = StockReturnPicking.with_context(active_ids=pick.ids, active_id=pick.ids[0]).default_get(['move_dest_exists', 'original_location_id', 'product_return_moves', 'parent_location_id', 'location_id'])
        return_wiz = StockReturnPicking.with_context(active_ids=pick.ids, active_id=pick.ids[0]).create(default_data)
        return_wiz.product_return_moves.write({'quantity': 2.0, 'to_refund': True}) # Return only 2
        res = return_wiz.create_returns()
        return_pick = self.env['stock.picking'].browse(res['res_id'])

        # Validate picking
        return_pick.force_assign()
        return_pick.move_line_ids.write({'qty_done': 2})
        
        return_pick.button_validate()

        # Check Received quantity
        self.assertEqual(self.po.order_line[0].qty_received, 3.0, 'Purchase: delivered quantity should be 3.0 instead of "%s" after picking return' % self.po.order_line[0].qty_received)
        #Create vendor bill for refund qty
        self.invoice = self.AccountInvoice.create({
            'partner_id': self.partner_id.id,
            'purchase_id': self.po.id,
            'account_id': self.partner_id.property_account_payable_id.id,
            'type': 'in_refund',
        })
        self.invoice.purchase_order_change()
        self.invoice.invoice_line_ids[0].quantity = 2.0
        self.invoice.invoice_line_ids[1].quantity = 2.0
        self.invoice.invoice_validate()
        self.assertEqual(self.po.order_line.mapped('qty_invoiced'), [3.0, 3.0], 'Purchase: Billed quantity should be 3.0')