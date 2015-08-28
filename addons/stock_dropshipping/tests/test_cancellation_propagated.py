# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.stock_dropshipping.tests.common import TestStockDropshippingCommon


class TestCancellationPropagated(TestStockDropshippingCommon):
    def setUp(self):
        super(TestCancellationPropagated, self).setUp()
        # I create a new product in this warehouse
        self.product_mto = self.Product.create({
                'name': 'My Product', 'type': 'product',
                'uom_id': self.product_uom_unit_id,'uom_po_id': self.product_uom_unit_id,
                'seller_ids': [(0, 0, {'delay': 1, 'name': self.partner_sup_id, 'min_qty': 2.0, 'qty': 10.0})]
        })
        # Set routes on product to be MTO and Buy
        self.route_warehouse0_buy_id = self.warehouse0.buy_pull_id.route_id.id
        self.route_warehouse0_mto_id = self.warehouse0.mto_pull_id.route_id.id
        self.product_mto.write({'route_ids': [(6, 0, [self.route_warehouse0_mto_id, self.route_warehouse0_buy_id])]})
        # Create a sale order with a line of 5 Units "My Product"
        self.sale_order_product_mto = self.SaleOrder.create({
            'partner_id': self.partner_cus_a_id, 'pricelist_id': self.pricelist0,
             'note': 'Create Sales order', 'warehouse_id': self.wh_pps.id,
             'order_line': [(0, 0, {
                    'product_id': self.product_mto.id, 'name': 'product_mto',
                    'product_uom_qty': 5.0, 'product_uom': self.product_uom_unit_id})]
         })
        # Confirm the sale order
        self.sale_order_product_mto.action_confirm()
        # Create another sale order with 2 Dozen of the same product
        self.sale_order_product_mto2 = self.SaleOrder.create({
              'partner_id': self.partner_cus_a_id, 'note': 'Create Sales order',
              'warehouse_id': self.wh_pps.id,
              'order_line': [(0, 0, {
                 'product_id': self.product_mto.id, 'name': 'product_mto',
                 'product_uom_qty': 2.0, 'product_uom': self.product_uom_dozen_id})]
        })
        # Confirm second the sale order
        self.sale_order_product_mto2.action_confirm()


    def test_00_cancellation_propagated(self):
        """
          Check the propagation when we cancel the main procurement
            * Retrieve related procurements and check that there are all running
            * Check that a purchase order is well created
            * Cancel the main procurement
            * Check that all procurements related and the purchase order are well cancelled
        """
        # Run scheduler
        self.ProcurementOrder.run_scheduler()
        # Retrieve related procurement
        so = self.sale_order_product_mto
        procures = self.ProcurementOrder.search([('group_id.name', '=', so.name)])
        self.assertGreater(len(procures), 0, 'No procurement found for sale order %s (with id: %d)' % (so.name, so.id))
        # Check that all procurements are running
        for procure in procures:
            self.assertEqual(procure.state, u'running',
             'Procurement with id: %d should be running but is with state : %s!' % (procure.id, procure.state))
        # Check that one purchase order has been created
        purchase_ids = [procure.purchase_id for procure in procures if procure.purchase_line_id]
        self.assertEqual(len(purchase_ids), 1, 'Purchase order should be found !')
        # Check the two purchase order lines
        purchase_line = purchase_ids[0].order_line[0]
        self.assertEqual(purchase_line.product_qty, 5.0,
             'The product quantity of the first order line should be 5 and not %s' %
             (purchase_line.product_qty))
        self.assertEqual(purchase_line.product_uom.id, self.product_uom_unit_id,
             'The product UoM ID of the first order line should be %s and not %s' %
             (self.product_uom_unit_id, purchase_line.product_uom.id))
        purchase_line = purchase_ids[0].order_line[1]
        self.assertEqual(purchase_line.product_qty, 2.0,
             'The product quantity of the first order line should be 2 and not %s' %
             (purchase_line.product_qty))
        self.assertEqual(purchase_line.product_uom.id, self.product_uom_dozen_id,
             'The product UoM ID of the second order line should be %s and not %s' %
             (self.product_uom_dozen_id, purchase_line.product_uom.id))
        # Let us cancel the procurement related to the 2nd sale order first and check that the 2 Dozen(s) are subtracted correctly
        so2 = self.sale_order_product_mto2
        so2.order_line[0].procurement_ids[0].cancel()
        self.assertEqual(so2.order_line[0].procurement_ids[0].state, 'cancel', 'Main procurement should be cancelled !')
        # Cancel the main procurement from the sale order in units
        main_procure = self.ProcurementOrder.search([('origin', '=', so.name)])
        self.assertEqual(len(main_procure), 1, 'Main procurement not identified !')
        main_procure.cancel()
        self.assertEqual(main_procure.state, u'cancel', 'Main procurement should be cancelled !')
        #Check that all procurements related are cancelled
        for procure in procures:
            self.assertEqual(procure.state, u'cancel',
                 'Procurement %d should be cancelled but is with a state : %s!' % (procure.id, procure.state))
