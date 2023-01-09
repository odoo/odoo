from .common import PurchaseTestCommon


class TestPurchaseOrderProcess(PurchaseTestCommon):

    def test_00_cancel_purchase_order_flow(self):
        """ Test cancel purchase order with group user."""

        # In order to test the cancel flow,start it from canceling confirmed purchase order.
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'My Partner'}).id,
            'state': 'draft',
        })
        po_edit_with_user = purchase_order.with_user(self.res_users_purchase_user)

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

    def test_01_packaging_propagation(self):
        """Create a PO with lines using packaging, check the packaging propagate
        to its move.
        """
        product = self.env['product.product'].create({
            'name': 'Product with packaging',
            'type': 'product',
        })

        packaging = self.env['product.packaging'].create({
            'name': 'box',
            'product_id': product.id,
        })

        po = self.env['purchase.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'My Partner'}).id,
            'order_line': [
                (0, 0, {
                    'product_id': product.id,
                    'product_qty': 1.0,
                    'product_uom': product.uom_id.id,
                    'product_packaging_id': packaging.id,
                })],
        })
        po.button_confirm()
        self.assertEqual(po.order_line.move_ids.product_packaging_id, packaging)
