# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from unittest.mock import patch
from urllib.parse import urlencode

from odoo.tests import HttpCase, tagged

from odoo.addons.sale_shopee import utils as shopee_utils
from odoo.addons.sale_shopee.const import API_OPERATIONS_MAPPING
from odoo.addons.sale_shopee.tests import common as common_sale_shopee


@tagged("post_install", "-at_install")
class TestShopeeOnboarding(HttpCase, common_sale_shopee.TestShopeeCommon):
    """Tests the Shopee onboarding controller."""

    def call_return_from_authorization(self, query):
        self.authenticate("admin", "admin")
        timestamp = int(datetime.now().timestamp())
        sign = shopee_utils.get_public_sign(
            self.account, API_OPERATIONS_MAPPING["auth_partner"]["url_path"], timestamp
        )

        path_params = (self.account.id, self.env.company.id, timestamp, sign)
        url = (
            "/shopee/return_from_authorization"
            f"/{'/'.join(map(str, path_params))}"
            f"?{urlencode(query)}"
        )
        return self.url_open(url)

    def test_shopee_return_from_authorization_with_main_account(self):
        """
        When `main_account_id` is provided, the controller should retrieve all the
        `shop_identifiers` from the main account, and update/create all the specific shops.
        """
        captured_shop_context = {}

        def get_shopee_api_response_mock(shop_, operation_, *_args, **_kwargs):
            if operation_ == "get_token":
                captured_shop_context["authorization_code"] = shop_.env.context.get(
                    "authorization_code"
                )
                return {
                    **common_sale_shopee.OPERATIONS_RESPONSES_MAP[operation_],
                    "shop_id_list": [1, 2],  # Add one new shop to be created
                }
            return common_sale_shopee.OPERATIONS_RESPONSES_MAP[operation_]

        with patch(
            "odoo.addons.sale_shopee.utils.make_shopee_api_request",
            new=get_shopee_api_response_mock,
        ):
            query = {"code": "test_authorization_code", "shop_id": "1", "main_account_id": "main_1"}
            self.call_return_from_authorization(query)

            self.assertEqual(
                captured_shop_context.get("authorization_code"),
                "test_authorization_code",
                msg="The authorization_code should be in the shop's context when calling"
                " request_access_token. ",
            )
            shops = self.env["shopee.shop"].search([("account_id", "=", self.account.id)])
            self.assertEqual(len(shops), 2, "Two shops should have been created")
            for shop in shops:
                self.assertEqual(shop.access_token, "dummy_oauth_token")
                self.assertEqual(shop.refresh_token, "dummy_refresh_token")

    def test_shopee_return_from_authorization_without_main_account(self):
        """
        When `main_account_id` is not provided, the controller should only update
        the specific shop identified by `shop_id`.
        """

        def get_shopee_api_response_mock(_shop, operation_, *_args, **_kwargs):
            return common_sale_shopee.OPERATIONS_RESPONSES_MAP[operation_]

        with patch(
            "odoo.addons.sale_shopee.utils.make_shopee_api_request",
            new=get_shopee_api_response_mock,
        ):
            query = {"code": "test_authorization_code", "shop_id": "1"}
            self.call_return_from_authorization(query)

            shops = self.env["shopee.shop"].search([("account_id", "=", self.account.id)])
            self.assertEqual(len(shops), 1)
            self.assertEqual(shops.shop_identifier, 1)
            self.assertEqual(shops.access_token, "dummy_oauth_token")
            self.assertEqual(shops.refresh_token, "dummy_refresh_token")
