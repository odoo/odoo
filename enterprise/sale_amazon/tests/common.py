# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import TransactionCase

ORDER_BUYER_INFO_MOCK = {
    'BuyerEmail': 'iliketurtles@marketplace.amazon.com',
    'BuyerName': 'Gederic Frilson',
}

ORDER_ADDRESS_MOCK = {
    'AddressLine1': '123 RainBowMan Street',
    'Phone': '+1 234-567-8910 ext. 12345',
    'PostalCode': '12345-1234',
    'City': 'New Duck City DC',
    'StateOrRegion': 'CA',
    'CountryCode': 'US',
    'Name': 'Gederic Frilson',
    'AddressType': 'Commercial',
}

ORDER_MOCK = {
    'BuyerInfo': ORDER_BUYER_INFO_MOCK,
    'AmazonOrderId': '123456789',
    'PurchaseDate': '1378-04-08T00:00:00Z',
    'LastUpdateDate': '2017-01-20T00:00:00Z',
    'OrderStatus': 'Unshipped',
    'FulfillmentChannel': 'MFN',
    'ShipServiceLevel': 'SHIPPING-CODE',
    'OrderTotal': {'CurrencyCode': 'USD', 'Amount': '120.00'},
    'MarketplaceId': 'ATVPDKIKX0DER',
    'ShippingAddress': ORDER_ADDRESS_MOCK,
}

GET_ORDERS_RESPONSE_MOCK = {
    'payload': {
        'LastUpdatedBefore': '2020-01-01T00:00:00Z',
        'Orders': [ORDER_MOCK],
    },
}

GET_ORDER_ITEMS_MOCK = {
    'payload': {
        'AmazonOrderId': '123456789',
        'OrderItems': [
            {
                'BuyerInfo': {
                    'OrderItemId': '987654321',
                    'GiftMessageText': 'Wrapped Hello',
                    'GiftWrapLevel': 'WRAP-CODE',
                    'GiftWrapTax': {'CurrencyCode': 'USD', 'Amount': '1.33'},
                    'GiftWrapPrice': {'CurrencyCode': 'USD', 'Amount': '3.33'},
                },
                'ItemTax': {'CurrencyCode': 'USD', 'Amount': '20.00'},
                'ItemPrice': {'CurrencyCode': 'USD', 'Amount': '100.00'},
                'ShippingTax': {'CurrencyCode': 'USD', 'Amount': '2.50'},
                'ShippingPrice': {'CurrencyCode': 'USD', 'Amount': '12.50'},
                'ShippingDiscountTax': {'CurrencyCode': 'USD', 'Amount': '0.50'},
                'ShippingDiscount': {'CurrencyCode': 'USD', 'Amount': '2.50'},
                'PromotionDiscountTax': {'CurrencyCode': 'USD', 'Amount': '1.00'},
                'PromotionDiscount': {'CurrencyCode': 'USD', 'Amount': '5.00'},
                'SellerSKU': 'TEST',
                'Title': 'Run Test, Run!',
                'IsGift': 'true',
                'ConditionNote': 'DO NOT BUY THIS',
                'ConditionId': 'Used',
                'ConditionSubtypeId': 'Acceptable',
                'QuantityOrdered': 2,
                'OrderItemId': '987654321',
            },
        ],
    },
}

OPERATIONS_RESPONSES_MAP = {
    'getOrder': {'payload': ORDER_MOCK},
    'getOrders': GET_ORDERS_RESPONSE_MOCK,
    'getOrderItems': GET_ORDER_ITEMS_MOCK,
    'createFeedDocument': {'feedDocumentId': '123123', 'url': 'my_amazing_feed_url.test'},
    'createFeed': None,
}


class TestAmazonCommon(TransactionCase):

    def setUp(self):
        super().setUp()
        self.marketplace = self.env['amazon.marketplace'].search(
            [('api_ref', '=', ORDER_MOCK['MarketplaceId'])]
        )
        self.account = self.env['amazon.account'].create({
            'name': 'TestAccountName',
            'seller_key': 'Random Seller Key',
            'refresh_token': 'A refresh token',
            'base_marketplace_id': self.marketplace.id,
            'available_marketplace_ids': [self.marketplace.id],
            'active_marketplace_ids': [self.marketplace.id],
            'company_id': self.env.company.id,
        })

        # Create an offer linked to the product
        self.product = self.env['product.product'].create(
            {'name': "This is a storable product", 'is_storable': True}
        )
        self.offer = self.env['amazon.offer'].create({
            'account_id': self.account.id,
            'marketplace_id': self.marketplace.id,
            'product_id': self.product.id,
            'sku': 'TESTING_SKU',
            'amazon_feed_ref': '{"productType":"PRODUCT","is_fbm":true}',
        })

        # Create a delivery carrier
        self.carrier = self.env['delivery.carrier'].create(
            {'name': "My Truck", 'product_id': self.product.id}  # delivery_type == 'fixed'
        )
        self.tracking_ref = "dummy tracking ref"
