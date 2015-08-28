# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.stock_dropshipping.tests.common import TestStockDropshippingCommon


class TestDropship(TestStockDropshippingCommon):
    def setUp(self):
        super(TestDropship, self).setUp()
        # Create a vendor.
        self.supplier_dropship = self.ResPartner.create({'name': 'Vendor of Dropshipping test'})
        # Create new product without any routes
        self.drop_shop_product = self.Product.create({
              'name': 'Pen drive', 'type': 'product',
              'categ_id': self.product_category1_id, 'list_price': 100.0,'standard_price': 0.0,
              'seller_ids': [(0, 0, {'delay': 1, 'name': self.supplier_dropship.id, 'min_qty': 2.0, 'qty': 5.0})],
              'uom_id': self.product_uom_unit_id, 'uom_po_id': self.product_uom_unit_id})
        # Create a sale order with a line of 200 PCE incoming shipment, with route_id drop shipping.
        self.sale_order_crossdock_shipping = self.SaleOrder.create({
            'partner_id': self.partner_sup_id, 'note': 'Create sale order for drop shipping',
            'payment_term_id': self.account_payment_term_id,
            'order_line': [(0, 0, {
               'product_id': self.drop_shop_product.id, 'name': 'drop_shop_product',
               'product_uom_qty': 200.0, 'product_uom': self.product_uom_unit_id,
               'price_unit': 1.00, 'route_id': self.route_drop_shipping_id})]
        })

    def test_00_dropshipping(self):
        # Confirm sale order.
        self.sale_order_crossdock_shipping.action_confirm()
        procurement_order = self.sale_order_crossdock_shipping.procurement_group_id.procurement_ids[0]
        # Check the sale order created a procurement group which has a procurement of 200 pieces.
        self.assertEqual(procurement_order.product_qty, 200.00, 'Procurement should have contain 200 product Qty.')
        # Check a quotation was created to a certain vendor and confirm so it becomes a confirmed purchase order.
        purchase_order = procurement_order.purchase_id
        purchase_order.button_confirm()
        self.assertEqual(purchase_order.state, 'purchase', 'Purchase order should be in the purchase state')
        #  Use 'Receive Products' button to immediately view this picking, it should have created a picking with 200 pieces
        po = self.PurchaseOrder.search([('partner_id', '=', self.supplier_dropship.id)])
        self.assertEqual(len(po), 1, 'There should be one picking')
        # Send the 200 pieces.
        po[0].picking_ids.do_transfer()
        # Check one Quant was created in Customers location with 200 pieces and one move in the history_ids.
        quants = self.StockQuant.search([('location_id', '=', self.stock_location_customer_id), ('product_id', '=', self.drop_shop_product.id)])
        self.assertTrue(quants, 'No Quant found')
        self.assertEqual(len(quants), 1, 'There should be exactly one Quant')
        self.assertEqual(len(quants[0].history_ids), 1, 'The Quant should have exactly 1 move in its history')
