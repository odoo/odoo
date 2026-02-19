from .common import PurchaseTestCommon


class TestPurchaseOrderStock(PurchaseTestCommon):
    def test_inventory_user_access_right(self):
        """ Test to check if Inventory/User is able to validate a
        transfer when the product has been invoiced already """

        purchase_order = self._create_purchase(self.product_avco, 1)

        purchase_order.action_create_invoice()
        self._create_bill(purchase_order=purchase_order, quantity=1.0)

        self.assertEqual(purchase_order.order_line[0].qty_invoiced, 1.0, 'QTY invoiced should have been set to 1 on the purchase order line')

        picking = purchase_order.picking_ids[0]
        # clear cash to ensure access rights verification
        self.env.invalidate_all()
        picking.with_user(self.inventory_user).button_validate()

        self.assertEqual(picking.state, 'done', 'Transfer should be in the DONE state')
