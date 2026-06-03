# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.exceptions import AccessError
from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.website_sale.tests.common import WebsiteSaleCommon
from odoo.addons.website_sale_stock.controllers.location_selector import LocationSelector
from odoo.addons.website_sale_stock.models.delivery_carrier import DeliveryCarrier


@tagged("post_install", "-at_install")
class TestLocationSelectorController(WebsiteSaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.LocationSelectorController = LocationSelector()
        cls.backend_dm = cls._prepare_carrier(
            cls._prepare_carrier_product(list_price=0.0), name="Backend Delivery"
        )
        cls.salesman = cls.env["res.users"].create({
            "name": "Test Salesman",
            "login": "test_salesman_pickup_locations",
            "group_ids": [Command.link(cls.quick_ref("sales_team.group_sale_salesman").id)],
        })

    def test_passed_delivery_method_takes_priority_over_session_cart(self):
        self.cart.carrier_id = self.free_delivery
        with self.mock_request(user=self.salesman, sale_order_id=self.cart.id), patch.object(
            DeliveryCarrier,
            "_get_pickup_locations",
            autospec=True,
            return_value={"pickup_locations": []},
        ) as mock_get_pickup_locations:
            self.LocationSelectorController.website_sale_get_pickup_locations(
                delivery_method_id=self.backend_dm.id, country_id=self.country_us.id
            )
        self.assertEqual(mock_get_pickup_locations.call_args.args[0], self.backend_dm)

    def test_delivery_method_read_access(self):
        with self.mock_request(), self.assertRaises(AccessError):
            self.LocationSelectorController.website_sale_get_pickup_locations(
                delivery_method_id=self.backend_dm.id, country_id=self.country_us.id
            )

    def test_pickup_locations_read_from_cart_without_delivery_method_id(self):
        self.cart.carrier_id = self.backend_dm
        with self.mock_request(sale_order_id=self.cart.id), patch.object(
            DeliveryCarrier,
            "_get_pickup_locations",
            autospec=True,
            return_value={"pickup_locations": []},
        ) as mock_get_pickup_locations:
            self.LocationSelectorController.website_sale_get_pickup_locations()
        self.assertEqual(mock_get_pickup_locations.call_args.args[0], self.backend_dm)

    def test_no_cart_and_no_delivery_method_returns_empty(self):
        with self.mock_request():
            response = self.LocationSelectorController.website_sale_get_pickup_locations()
        self.assertEqual(response, {})
