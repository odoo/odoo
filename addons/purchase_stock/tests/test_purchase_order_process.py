from .common import TestPurchase


class TestPurchaseOrderProcess(TestPurchase):

    def test_00_cancel_purchase_order_flow(self):
        """ Test cancel purchase order with group user."""

        # In order to test the cancel flow,start it from canceling confirmed purchase order.
        po_edit_with_user = self.env.ref('purchase.purchase_order_5').with_user(self.res_users_purchase_user)

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
