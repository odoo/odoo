# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.website_sale.controllers.main import WebsiteSale as CheckoutController
from odoo.addons.website_sale_stock.tests.common import WebsiteSaleStockCommon


@tagged("post_install", "-at_install")
class TestWebsiteSaleStockCheckout(WebsiteSaleStockCommon):
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
