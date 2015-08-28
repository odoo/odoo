# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.stock_dropshipping.tests.common import TestStockDropshippingCommon


class TestProcurementException(TestStockDropshippingCommon):
    def setUp(self):
        super(TestProcurementException, self).setUp()

        res_partner_address_3_id = self.ref('base.res_partner_address_3')
        # Create a product with no supplier define for it.
        self.product_with_no_seller = self.Product.create({
           'name': 'product with no seller', 'list_price': 20.00,
           'standard_price': 15.00, 'categ_id': self.product_category1_id
        })
        # Create a sale order with this product with route dropship.
        self.sale_order_route_dropship01 = self.SaleOrder.create({
          'partner_id': self.partner_sup_id, 'partner_invoice_id': res_partner_address_3_id,
          'partner_shipping_id': res_partner_address_3_id, 'note': 'crossdock route',
          'payment_term_id': self.account_payment_term_id,
          'order_line': [(0, 0, {
                 'product_id': self.product_with_no_seller.id, 'name': 'product_with_no_seller',
                 'product_uom_qty': 1, 'product_uom': self.product_uom_unit_id,
                 'route_id': self.route_drop_shipping_id})]
          })

    def test_00_procurement_exception(self):
        # Confirm the sale order.
        self.sale_order_route_dropship01.action_confirm()
        # Check there is a procurement in exception that has the procurement group of the sale order created before.
        self.ProcurementOrder.run_scheduler()
        procure = self.ProcurementOrder.search([('group_id.name', '=', self.sale_order_route_dropship01.name), ('state', '=', 'exception')])
        self.assertTrue(procure, 'Sale Order should have a Procurement!')
        # Set the at least one supplier on the product.
        self.product_with_no_seller.write({'seller_ids': [(0, 0, {'delay': 1, 'name': self.partner_sup_id, 'min_qty': 2.0})]})
        # Run the Procurement.
        procure = self.ProcurementOrder.search([('group_id.name', '=', self.sale_order_route_dropship01.name), ('state', '=', 'exception')])
        procure.run()
        # Check the status changed there is no procurement order in exception any more from that procurement group
        procure = self.ProcurementOrder.search([('group_id.name', '=', self.sale_order_route_dropship01.name), ('state', '=', 'exception')])
        self.assertFalse(procure, 'Procurement should be in running state')
        # Check a purchase quotation was created.
        procures = self.ProcurementOrder.search([('group_id.name', '=', self.sale_order_route_dropship01.name)])
        purchase = procures.mapped('purchase_line_id').order_id
        self.assertTrue(purchase, 'No Purchase Quotation is created')
