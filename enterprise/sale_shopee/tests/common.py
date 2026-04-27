# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo.tests import TransactionCase

ORDER_SN_MOCK = 'O123456789'

BUYER_ADDRESS_MOCK = {
    'name': 'Gederic Frilson',
    'phone': '9876543210',
    'full_address': '123 RainBowMan Street, Xã Phong Thạnh Tây B, New Duck City DC, Tây Ninh',
    'city': 'New Duck City DC',
    'district': 'Xã Phong Thạnh Tây B',
    'state': 'Tây Ninh',
    'town': '',
    'region': 'VN',
    'zipcode': '',
}

ORDER_ITEM_MOCK = {
    'add_on_deal': False,
    'add_on_deal_id': 0,
    'item_id': 111111,
    'item_name': 'test product',
    'item_sku': '',
    'model_discounted_price': 40,
    'model_id': 222222,
    'model_original_price': 100,
    'model_quantity_purchased': 4,
    'model_sku': 'TEST_SKU',
    'order_item_id': 111111,
    'promotion_group_id': 0,
    'promotion_id': 333333,
    'promotion_type': 'flash_sale',
}

PACKAGE_ITEM_MOCK = {
    'item_list': [
        {
            'item_id': 111111,
            'model_id': 222222,
            'model_quantity': 1,
            'order_item_id': 111111,
            'promotion_group_id': 0,
        }
    ],
    'package_number': 'A123456789',
    'shipping_carrier': 'Fake Ship',
}

# Mock data for an order
ORDER_MOCK = {
    'actual_shipping_fee_confirmed': True,
    'buyer_user_id': 444444,
    'buyer_username': 'Gederic Frilson',
    'update_time': 1579050000,  # 2020-1-15
    'create_time': 1579050000,  # 2020-1-15
    'currency': 'VND',
    'actual_shipping_fee': 10,
    'estimated_shipping_fee': 10,
    'fulfillment_flag': 'fulfilled_by_local_seller',
    'item_list': [ORDER_ITEM_MOCK],
    'order_sn': ORDER_SN_MOCK,
    'order_status': 'READY_TO_SHIP',
    'package_list': [PACKAGE_ITEM_MOCK],
    'recipient_address': BUYER_ADDRESS_MOCK,
    'region': 'VN',
    'shipping_carrier': 'Fake Ship',
    'total_amount': 170,
}

# Mock data for the response of the getOrders API
GET_ACCESS_TOKEN_RESPONSE_MOCK = {
    'error': '',
    'message': '',
    'request_id': '123456',
    'response': {},
    'refresh_token': 'dummy_refresh_token',
    "access_token": "dummy_oauth_token",
    'expire_in': 1000000,
}

REFRESH_TOKEN_RESPONSE_MOCK = {
    **GET_ACCESS_TOKEN_RESPONSE_MOCK,
    'partner_id': 100,
}

GET_ORDER_DETAILS_RESPONSE_MOCK = {'order_list': [ORDER_MOCK]}

GET_ORDER_LIST_RESPONSE_MOCK = {
    'order_list': [{'order_sn': ORDER_SN_MOCK}],
    'more': False,
    'next_cursor': None,
}

GET_SHIPMENT_RESPONSE_MOCK = {
    'result_list': [{
        'status': 'READY',
        'order_sn': ORDER_SN_MOCK,
        'package_number': '2537708677189632625',
    }]
}

GET_SHOP_INFO_RESPONSE_MOCK = {
    'shop_name': 'mock_shopee_shop',
    'region': 'VN',
    'status': 'NORMAL',
    'expire_time': 1682179199,
}

# Map of API operations to their corresponding response data
OPERATIONS_RESPONSES_MAP = {
    'refresh_token': REFRESH_TOKEN_RESPONSE_MOCK,
    'get_token': GET_ACCESS_TOKEN_RESPONSE_MOCK,
    'get_shop_info': GET_SHOP_INFO_RESPONSE_MOCK,
    'get_order_list': GET_ORDER_LIST_RESPONSE_MOCK,
    'get_order_detail': {'order_list': [ORDER_MOCK]},
    'get_tracking_number': {'tracking_number': 'MY200448706479IT'},
    'create_shipping_document': {'result_list': [{'order_sn': ORDER_SN_MOCK}]},
    'get_shipping_document_result': GET_SHIPMENT_RESPONSE_MOCK,
    'download_shipping_document': b'%PDF-1.4\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF',
    'update_stock': None,
}


# Test class for common Shopee-related functionality
class TestShopeeCommon(TransactionCase):

    def setUp(self):
        super().setUp()
        # Create a Shopee account
        self.initial_sync_date = datetime(2020, 1, 1)
        self.account = self.env['shopee.account'].create({
            'name': "mock_shopee_account",
            'api_endpoint': 'test',
            'partner_identifier': 1,
            'partner_key': 'A partner token',
            'company_ids': [self.env.company.id],
        })

        # Create a shop
        self.shop = self.env['shopee.shop'].create({
            'name': GET_SHOP_INFO_RESPONSE_MOCK['shop_name'],
            'shop_identifier': 1,
            'account_id': self.account.id,
            'status': 'active',
            'authorization_expiration_date': datetime.now() + timedelta(days=365),
            'last_orders_sync_date': self.initial_sync_date,
        })

        # Create a product
        self.product = self.env['product.product'].create({
            'name': "This is a storable product",
            'type': 'consu',
            'default_code': ORDER_ITEM_MOCK['model_sku'],
            'list_price': 0.0,
            'is_storable': True,
        })

        # Create a Shopee item linked to the product
        self.item = self.env['shopee.item'].create({
            'product_id': self.product.id,
            'shop_id': self.shop.id,
            'shopee_item_identifier': ORDER_ITEM_MOCK['item_id'],
            'shopee_model_identifier': ORDER_ITEM_MOCK['model_id'],
            'last_inventory_sync_date': self.initial_sync_date,
            'sync_to_shopee': True,
        })
