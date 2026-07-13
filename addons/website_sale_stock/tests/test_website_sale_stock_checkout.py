# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged

from odoo.addons.website_sale.controllers.main import WebsiteSale as CheckoutController
from odoo.addons.website_sale_stock.tests.common import WebsiteSaleStockCommon


@tagged("post_install", "-at_install")
class TestWebsiteSaleStockCheckout(WebsiteSaleStockCommon, HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product.write({"allow_out_of_stock_order": False, "is_storable": True})
        cls.stock_location = cls.warehouse.lot_stock_id
        cls.partner.write(cls.dummy_partner_address_values)
        cls.CheckoutController = CheckoutController()

    def test_checkout_possible_if_at_least_one_warehouse_can_fulfill_the_order(self):
        wh2 = self._create_warehouse()
        self._add_product_qty_to_wh(self.product.id, 0, self.stock_location.id)
        self._add_product_qty_to_wh(self.product.id, 10, wh2.lot_stock_id.id)

        with self.mock_request(path="/shop/checkout", sale_order_id=self.cart.id):
            response = self.CheckoutController.shop_checkout()

        self.assertEqual(response.status_code, 200)  # Success without redirection

    def test_pickup_address_excluded_from_delivery_address_list(self):
        """Pickup addresses must not appear in the selectable delivery address list."""
        pickup_address = self.env["res.partner"].create({
            "name": "DHL Locker",
            "type": "delivery",
            "parent_id": self.partner.id,
            "pickup_delivery_method_id": self.carrier.id,
        })
        with self.mock_request():
            address_data = CheckoutController()._prepare_address_data(self.partner)
        self.assertNotIn(pickup_address, address_data["delivery_addresses"])
