from .common import TestPurchase


class TestPurchaseOrderProcess(TestPurchase):

    def test_00_cancel_purchase_order_flow(self):
        """ Test cancel purchase order with group user."""

        purchase_order = self.env.ref('purchase.purchase_order_5')
        # In order to test the cancel flow,start it from canceling confirmed purchase order.
        po_edit_with_user = purchase_order.sudo(self.res_users_purchase_user.id)
        # Confirm the purchase order.
        po_edit_with_user.button_confirm()

        # Check the "Approved" status  after confirmed RFQ.
        self.assertEqual(po_edit_with_user.state, 'purchase', 'Purchase: PO state should be "Purchase')

        # First cancel receptions related to this order if order shipped.
        po_edit_with_user.picking_ids.action_cancel()
        # Able to cancel purchase order.
        po_edit_with_user.button_cancel()

        # Check that order is cancelled.
        self.assertEqual(po_edit_with_user.state, 'cancel', 'Purchase: PO state should be "Cancel')

    def test_01_run_schedular_flow(self):
        """ Test procurement run schedular."""

        # In order to test the scheduler to generate RFQ, create a new product.
        scheduler_product = self.env['product.product'].create({
            'name': "Scheduler Product",
            'route_ids': [(6, 0, [self.ref("purchase.route_warehouse0_buy")])],
            'seller_ids': [(0, 0, {
                    'delay': 1,
                    'name': self.ref('base.res_partner_2'),
                    'min_qty': 5.0
                })]
        })
        # Create a procurement order.
        procurement = self.Procurement.create({
            'location_id': self.ref('stock.stock_location_stock'),
            'name': 'Test scheduler for RFQ',
            'product_id': scheduler_product.id,
            'product_qty': 15,
            'product_uom': self.ref('product.product_uom_unit'),
            })
        # Run the scheduler.
        procurement.run_scheduler()

        # Check Generated RFQ.
        self.assertTrue(procurement.purchase_line_id, 'RFQ should be generated!')

        # Delete the line from the purchase order and check that the move and the procurement are cancelled
        procurement.purchase_line_id.unlink()

        self.assertEqual(procurement.state, 'exception', 'Procurement should be in exception')
