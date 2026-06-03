# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.website_sale_collect.controllers.delivery import InStoreDelivery
from odoo.addons.website_sale_collect.tests.common import ClickAndCollectCommon
from odoo.addons.website_sale_stock.models.delivery_carrier import DeliveryCarrier


@tagged("post_install", "-at_install")
class TestInStoreDeliveryController(PaymentHttpCommon, ClickAndCollectCommon):
    _test_user_groups = None  # FIXME list needed groups

    def setUp(self):
        super().setUp()
        self.InStoreController = InStoreDelivery()

    def test_order_not_created_on_fetching_pickup_location_with_empty_cart(self):
        count_so_before = self.env["sale.order"].search_count([])
        url = self._build_url("/website_sale_stock/get_pickup_locations")
        with patch("odoo.addons.website_sale_collect.controllers.delivery", return_value={}):
            self.make_jsonrpc_request(url, {"product_id": 1})
        count_so_after = self.env["sale.order"].search_count([])
        self.assertEqual(count_so_after, count_so_before)

    def test_product_page_pickup_locations_without_cart(self):
        """Without a cart, the website's in-store delivery method is used."""
        with self.mock_request(), patch.object(
            DeliveryCarrier,
            "_get_pickup_locations",
            autospec=True,
            return_value={"pickup_locations": []},
        ) as mock_get_pickup_locations:
            self.InStoreController.website_sale_get_pickup_locations(
                product_id=self.storable_product.id
            )
        self.assertEqual(mock_get_pickup_locations.call_args.args[0], self.in_store_dm)

    def test_product_page_pickup_locations_with_cart_set_in_store_dm(self):
        self.cart.carrier_id = self.free_delivery
        with self.mock_request(sale_order_id=self.cart.id), patch.object(
            DeliveryCarrier,
            "_get_pickup_locations",
            autospec=True,
            return_value={"pickup_locations": []},
        ):
            self.InStoreController.website_sale_get_pickup_locations(
                product_id=self.storable_product.id
            )
        self.assertEqual(self.cart.carrier_id, self.in_store_dm)
