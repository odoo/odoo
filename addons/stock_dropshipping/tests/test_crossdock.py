# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.stock_dropshipping.tests.common import TestStockDropshippingCommon


class TestCrossDock(TestStockDropshippingCommon):
    def setUp(self):
        super(TestCrossDock, self).setUp()
        # Create a supplier
        self.supplier_crossdock = self.ResPartner.create({'name': 'Crossdocking supplier'})
        # Create new product without any routes.
        cross_shop_product = self.Product.create({
              'name': 'PCE', 'type': 'product', 'categ_id': self.product_category1_id,
              'list_price': 100.0, 'standard_price': 70.0,
              'seller_ids': [(0, 0, {'delay': 1, 'name': self.supplier_crossdock.id, 'min_qty': 2.0, 'qty': 5.0})],
              'uom_id': self.product_uom_unit_id, 'uom_po_id': self.product_uom_unit_id})
        # Create a sale order with a line of 100 PCE incoming shipment, with route_id crossdock shipping
        self.sale_order_crossdock_shipping = self.SaleOrder.create({
                'partner_id': self.partner_cus_b_id, 'note': 'Create Sales order',
                'warehouse_id': self.wh_pps.id,
                'order_line': [(0, 0, {
                       'product_id': cross_shop_product.id, 'name': 'cross_shop_product',
                       'product_uom_qty': 100.0, 'product_uom': self.product_uom_unit_id
                 })]
        })

    def test_00_crossdock(self):
        # Use the warehouse created.
        self.assertTrue(self.wh_pps.crossdock_route_id.active, 'Crossdock route is not active')
        self.sale_order_crossdock_shipping.order_line.write({'route_id': self.wh_pps.crossdock_route_id.id})
        # Confirm sale order.
        self.sale_order_crossdock_shipping.action_confirm()
        # Run scheduler
        self.ProcurementOrder.run_scheduler()
        # Check a quotation was created for the created supplier and confirm it.
        self.PurchaseOrder.search([
           ('partner_id', '=', self.supplier_crossdock.id), ('state', '=', 'draft')
        ]).button_confirm()
