# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from unittest.mock import Mock, patch

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests.common import tagged
from odoo.tools import mute_logger

from odoo.addons.sale_amazon import utils as amazon_utils
from odoo.addons.sale_amazon.tests import common


@tagged('post_install', '-at_install')
class TestAmazon(common.TestAmazonCommon):

    @mute_logger('odoo.addons.sale_amazon.models.amazon_account')
    def test_update_marketplaces_no_change(self):
        """ Test the available marketplaces synchronization with no change. """
        marketplaces = self.env['amazon.marketplace'].search([])
        with patch(
            'odoo.addons.sale_amazon.models.amazon_account.AmazonAccount'
            '._get_available_marketplaces',
            return_value=marketplaces,
        ):
            self.account.write({
                'available_marketplace_ids': [(6, 0, marketplaces.ids)],
                'active_marketplace_ids': [(6, 0, marketplaces.ids)],
            })
            self.account.action_update_available_marketplaces()
            self.assertEqual(self.account.available_marketplace_ids.ids, marketplaces.ids)
            self.assertEqual(self.account.active_marketplace_ids.ids, marketplaces.ids)

    @mute_logger('odoo.addons.sale_amazon.models.amazon_account')
    def test_update_marketplaces_remove(self):
        """ Test the available marketplaces synchronization with a marketplace removal. """
        marketplaces = self.env['amazon.marketplace'].search([], limit=2)
        with patch(
            'odoo.addons.sale_amazon.models.amazon_account.AmazonAccount'
            '._get_available_marketplaces',
            return_value=marketplaces[:1],
        ):
            self.account.write({
                'available_marketplace_ids': [(6, 0, marketplaces.ids)],
                'active_marketplace_ids': [(6, 0, marketplaces.ids)],
            })
            self.account.action_update_available_marketplaces()
            self.assertEqual(self.account.available_marketplace_ids.ids, marketplaces.ids[:1])
            self.assertEqual(
                self.account.active_marketplace_ids.ids,
                marketplaces.ids[:1],
                msg="Unavailable marketplaces should be removed from the list of active "
                    "marketplaces.",
            )

    @mute_logger('odoo.addons.sale_amazon.models.amazon_account')
    def test_update_marketplaces_add(self):
        """ Test the available marketplaces synchronization with a new marketplace. """
        marketplaces = self.env['amazon.marketplace'].search([], limit=2)
        with patch(
            'odoo.addons.sale_amazon.models.amazon_account.AmazonAccount'
            '._get_available_marketplaces',
            return_value=marketplaces,
        ):
            self.account.write({
                'available_marketplace_ids': [(6, 0, marketplaces.ids[:1])],
                'active_marketplace_ids': [(6, 0, marketplaces.ids[:1])],
            })
            self.account.action_update_available_marketplaces()
            self.assertEqual(self.account.available_marketplace_ids.ids, marketplaces.ids)
            self.assertEqual(
                self.account.active_marketplace_ids.ids,
                marketplaces.ids,
                msg="New available marketplaces should be added to the list of active marketplaces"
            )

    @mute_logger('odoo.addons.sale_amazon.models.amazon_account')
    def test_sync_orders_full(self):
        """ Test the orders synchronization with on-the-fly creation of all required records. """

        def find_matching_product_mock(
            _self, product_code_, _default_xmlid, default_name_, default_type_
        ):
            """ Return a product created on-the-fly with the product code as internal reference. """
            product_ = self.env['product.product'].create({
                'name': default_name_,
                'type': default_type_,
                'list_price': 0.0,
                'sale_ok': False,
                'purchase_ok': False,
                'default_code': product_code_,
            })
            product_.product_tmpl_id.taxes_id = [Command.clear()]
            return product_

        # Create a warehouse that is prioritized when creating a normal order
        view_location = self.env['stock.location'].create({
            'name': "some location", 'usage': 'view', 'company_id': self.env.company.id
        })
        stock_location = self.env['stock.location'].create({
            'name': "some location", 'usage': 'internal', 'company_id': self.env.company.id
        })
        other_warehouse = self.env['stock.warehouse'].create({
            'name': "Other warehouse",
            'code': "OW",
            'view_location_id': view_location.id,
            'lot_stock_id': stock_location.id,
            'sequence': 1,
        })

        self.assertNotEqual(self.account.location_id.warehouse_id, other_warehouse)

        with patch(
            'odoo.addons.sale_amazon.utils.make_sp_api_request',
            new=lambda _account, operation, **kwargs: common.OPERATIONS_RESPONSES_MAP[operation],
        ), patch(
            'odoo.addons.sale_amazon.models.amazon_account.AmazonAccount._recompute_subtotal',
            new=lambda self_, subtotal_, *args_, **kwargs_: subtotal_,
        ), patch(
            'odoo.addons.sale_amazon.models.amazon_account.AmazonAccount._find_matching_product',
            new=find_matching_product_mock,
        ):
            self.account._sync_orders(auto_commit=False)
            self.assertEqual(
                self.account.last_orders_sync,
                datetime(2020, 1, 1),
                msg="The last_order_sync should be equal to the date returned by get_orders_data "
                    "when the synchronization is completed."
            )
            order = self.env['sale.order'].search([('amazon_order_ref', '=', '123456789')])
            self.assertEqual(len(order), 1, msg="There should have been exactly one order created.")
            self.assertEqual(order.origin, 'Amazon Order 123456789')
            self.assertEqual(order.date_order, datetime(1378, 4, 8))
            self.assertEqual(order.company_id.id, self.account.company_id.id)
            self.assertEqual(order.user_id.id, self.account.user_id.id)
            self.assertEqual(order.team_id.id, self.account.team_id.id)
            self.assertNotEqual(order.warehouse_id.id, self.account.location_id.warehouse_id.id)
            self.assertEqual(order.amazon_channel, 'fbm')
            self.assertEqual(order.currency_id.name, 'USD')

            order_lines = self.env['sale.order.line'].search([('order_id', '=', order.id)])
            self.assertEqual(
                len(order_lines),
                4,
                msg="There should have been four order lines created: one for the product, one for "
                    "the gift wrapping charges, one (note) for the gift message and one for the "
                    "shipping."
            )
            product_line = order_lines.filtered(lambda l: l.product_id.default_code == 'TEST')
            self.assertEqual(
                product_line.price_unit,
                50.0,
                msg="The unitary price should be the quotient of the item price (tax excluded) "
                    "divided by the quantity.",
            )
            self.assertEqual(product_line.discount, 5)  # 5% discount.
            self.assertEqual(product_line.product_uom_qty, 2.0)
            self.assertEqual(product_line.amazon_item_ref, '987654321')
            self.assertTrue(product_line.amazon_offer_id)

            shipping_line = order_lines.filtered(
                lambda l: l.product_id.default_code == 'SHIPPING-CODE'
            )
            self.assertEqual(shipping_line.price_unit, 12.5)
            self.assertEqual(shipping_line.discount, 20)  # 2.5/12.5*100
            self.assertEqual(shipping_line.product_uom_qty, 1.0)
            self.assertFalse(shipping_line.amazon_item_ref)
            self.assertFalse(shipping_line.amazon_offer_id)

            gift_wrapping_line = order_lines.filtered(
                lambda l: l.product_id.default_code == 'WRAP-CODE'
            )
            self.assertEqual(gift_wrapping_line.price_unit, 3.33)
            self.assertEqual(gift_wrapping_line.product_uom_qty, 1.0)
            self.assertFalse(gift_wrapping_line.amazon_item_ref)
            self.assertFalse(gift_wrapping_line.amazon_offer_id)

    @mute_logger('odoo.addons.sale_amazon.models.amazon_account')
    def test_sync_orders_partial(self):
        """ Test the orders synchronization interruption with API throttling. """

        def get_sp_api_response_mock(_account, operation_, **_kwargs):
            """ Return a mocked response without making an actual call to the SP-API. """
            base_response_ = common.OPERATIONS_RESPONSES_MAP[operation_]
            if operation_ == 'getOrders':
                response_ = dict(base_response_, payload={
                    'LastUpdatedBefore': '2020-01-01T00:00:00Z',
                    'Orders': [common.ORDER_MOCK, dict(
                        common.ORDER_MOCK,
                        AmazonOrderId={'value': '987654321'},
                        LastUpdateDate='2019-01-20T00:00:00Z',
                    )],
                })
            elif operation_ == 'getOrderItems':
                response_ = base_response_
                self.get_order_items_count += 1
                if self.get_order_items_count == 2:
                    raise amazon_utils.AmazonRateLimitError(operation_)
            else:
                response_ = base_response_
            return response_

        with patch(
            'odoo.addons.sale_amazon.utils.make_sp_api_request', new=get_sp_api_response_mock
        ):
            self.get_order_items_count = 0
            self.account._sync_orders(auto_commit=False)
            self.assertEqual(
                self.account.last_orders_sync,
                datetime(2017, 1, 20),
                msg="The last_order_sync should be equal to the LastUpdateDate of the last fully "
                    "synchronized order if no all orders could be synchronized.",
            )

    @mute_logger('odoo.addons.sale_amazon.models.amazon_account')
    def test_sync_orders_fail(self):
        """ Test the orders synchronization cancellation with API throttling. """

        def get_sp_api_response_mock(_account, operation_, **_kwargs):
            """ Return a mocked response or raise an AmazonRateLimitError without making an actual
            call to the SP-API. """
            if operation_ != 'getOrderItems':
                return common.OPERATIONS_RESPONSES_MAP[operation_]
            else:
                raise amazon_utils.AmazonRateLimitError(operation_)

        with patch(
            'odoo.addons.sale_amazon.utils.make_sp_api_request', new=get_sp_api_response_mock
        ):
            last_order_sync_copy = self.account.last_orders_sync
            self.account._sync_orders(auto_commit=False)
            self.assertEqual(
                self.account.last_orders_sync,
                last_order_sync_copy,
                msg="The last_order_sync field should not have been modified if the rate limit of "
                    "one operation was reached when synchronizing an order.",
            )

    @mute_logger('odoo.addons.sale_amazon.models.amazon_account')
    def test_sync_orders_abort(self):
        """ Test the orders synchronization cancellation with no active marketplace. """
        last_order_sync_copy = self.account.last_orders_sync
        self.account.active_marketplace_ids = False
        with self.assertRaises(UserError):
            self.account._sync_orders(auto_commit=False)
        self.assertEqual(
            self.account.last_orders_sync,
            last_order_sync_copy,
            msg="The last_order_sync field should not have been modified if there is no active "
                "marketplace selected for the account.",
        )

    @mute_logger('odoo.addons.sale_amazon.models.amazon_account')
    def test_sync_orders_fba(self):
        """ Test the orders synchronization with Fulfillment By Amazon. """

        def get_sp_api_response_mock(_account, operation_, **_kwargs):
            """ Return a mocked response without making an actual call to the SP-API. """
            base_response_ = common.OPERATIONS_RESPONSES_MAP[operation_]
            if operation_ == 'getOrders':
                return dict(base_response_, payload={
                    'LastUpdatedBefore': base_response_['payload']['LastUpdatedBefore'],
                    'Orders': [
                        dict(common.ORDER_MOCK, OrderStatus='Shipped', FulfillmentChannel='AFN')
                    ],
                })
            else:
                return base_response_

        def find_matching_product_mock(
            _self, product_code_, _default_xmlid, default_name_, default_type_
        ):
            """ Return a product created on-the-fly with the product code as internal reference. """
            product_ = self.env['product.product'].create({
                'name': default_name_,
                'type': default_type_,
                'list_price': 0.0,
                'sale_ok': False,
                'purchase_ok': False,
                'default_code': product_code_,
            })
            product_.product_tmpl_id.taxes_id = [Command.clear()]
            return product_

        # Create a warehouse that is prioritized when creating a normal order
        view_location = self.env['stock.location'].create({
            'name': "some location", 'usage': 'view', 'company_id': self.env.company.id
        })
        stock_location = self.env['stock.location'].create({
            'name': "some location", 'usage': 'internal', 'company_id': self.env.company.id
        })
        other_warehouse = self.env['stock.warehouse'].create({
            'name': "Other warehouse",
            'code': "OW",
            'view_location_id': view_location.id,
            'lot_stock_id': stock_location.id,
            'sequence': 1,
        })

        self.assertNotEqual(self.account.location_id.warehouse_id, other_warehouse)

        with patch(
            'odoo.addons.sale_amazon.utils.make_sp_api_request', new=get_sp_api_response_mock
        ), patch(
            'odoo.addons.sale_amazon.models.amazon_account.AmazonAccount._find_matching_product',
            new=find_matching_product_mock,
        ):
            self.account._sync_orders(auto_commit=False)
            order = self.env['sale.order'].search([('amazon_order_ref', '=', '123456789')])
            self.assertEqual(order.amazon_channel, 'fba')
            self.assertEqual(order.warehouse_id.id, self.account.location_id.warehouse_id.id)
            picking = self.env['stock.picking'].search([('sale_id', '=', order.id)])
            self.assertEqual(len(picking), 0, msg="FBA orders should generate no picking.")
            products = order.order_line.mapped('product_id').filtered(lambda p: p.type != 'service')
            moves = self.env['stock.move'].search([('product_id', 'in', products.ids)])
            self.assertEqual(
                len(moves),
                len(products),
                msg="FBA orders should generate one stock move per product that is not a service.",
            )

    @mute_logger('odoo.addons.sale_amazon.models.amazon_account')
    def test_sync_orders_europe(self):
        """ Test the orders synchronization with a European marketplace. """

        def get_sp_api_response_mock(_account, operation_, **_kwargs):
            """ Return a mocked response without making an actual call to the SP-API. """
            base_response_ = common.OPERATIONS_RESPONSES_MAP[operation_]
            if operation_ == 'getOrders':
                response_ = dict(base_response_, payload={
                    'LastUpdatedBefore': base_response_['payload']['LastUpdatedBefore'],
                    'Orders': [dict(common.ORDER_MOCK, MarketplaceId='A13V1IB3VIYZZH')]
                })
            else:
                response_ = base_response_
            return response_

        def find_matching_product_mock(
            _self, product_code_, _default_xmlid, default_name_, default_type_
        ):
            """ Return a product created on-the-fly with the product code as internal reference. """
            product_ = self.env['product.product'].create({
                'name': default_name_,
                'type': default_type_,
                'list_price': 0.0,
                'sale_ok': False,
                'purchase_ok': False,
                'default_code': product_code_,
            })
            product_.product_tmpl_id.taxes_id = [Command.clear()]
            return product_

        with patch(
            'odoo.addons.sale_amazon.utils.make_sp_api_request', new=get_sp_api_response_mock
        ), patch(
            'odoo.addons.sale_amazon.models.amazon_account.AmazonAccount._recompute_subtotal',
            new=lambda self_, subtotal_, *args_, **kwargs_: subtotal_,
        ), patch(
            'odoo.addons.sale_amazon.models.amazon_account.AmazonAccount._find_matching_product',
            new=find_matching_product_mock,
        ):
            europe_mp = self.env['amazon.marketplace'].search([('api_ref', '=', 'A13V1IB3VIYZZH')])
            self.account.base_marketplace_id = europe_mp.id
            self.account.available_marketplace_ids = [europe_mp.id]
            self.account.active_marketplace_ids = [europe_mp.id]

            self.account._sync_orders(auto_commit=False)
            order_lines = self.env['sale.order.line'].search(
                [('order_id.amazon_order_ref', '=', '123456789')]
            )
            product_line = order_lines.filtered(lambda l: l.product_id.default_code == 'TEST')
            shipping_line = order_lines.filtered(
                lambda l: l.product_id.default_code == 'SHIPPING-CODE'
            )
            gift_wrapping_line = order_lines.filtered(
                lambda l: l.product_id.default_code == 'WRAP-CODE'
            )
            self.assertEqual(
                product_line.price_unit,
                40,  # (100 - 20)/2
                msg="Tax amounts should be deducted from the item price for European marketplaces.",
            )
            self.assertEqual(
                shipping_line.price_unit,
                10,  # 12.50 - 2.50
                msg="Tax amounts should be deducted from the shipping price for European "
                    "marketplaces.",
            )
            self.assertEqual(
                gift_wrapping_line.price_unit,
                2,  # 3.33 - 1.33
                msg="Tax amounts should be deducted from the gift wrap price for European "
                    "marketplaces.",
            )

    @mute_logger('odoo.addons.sale_amazon.models.amazon_account')
    def test_sync_orders_cancel(self):
        """ Test the orders synchronization with cancellation from Amazon. """

        def get_sp_api_response_mock(_account, operation_, **_kwargs):
            """ Return a mocked response without making an actual call to the SP-API. """
            base_response_ = common.OPERATIONS_RESPONSES_MAP[operation_]
            order_status_ = 'Unshipped' if not order_created else 'Canceled'
            if operation_ == 'getOrders':
                return dict(base_response_, payload={
                    'LastUpdatedBefore': base_response_['payload']['LastUpdatedBefore'],
                    'Orders': [dict(common.ORDER_MOCK, OrderStatus=order_status_)],
                })
            else:
                return base_response_

        with patch(
            'odoo.addons.sale_amazon.utils.make_sp_api_request', new=get_sp_api_response_mock
        ):
            # Sync an order created on Amazon.
            order_created = False
            self.account._sync_orders(auto_commit=False)

            # Sync an order canceled from Amazon.
            order_created = True
            self.account._sync_orders(auto_commit=False)
            order = self.env['sale.order'].search([('amazon_order_ref', '=', '123456789')])
            self.assertEqual(
                order.state,
                'cancel',
                msg="The cancellation of orders should be synchronized from Amazon.",
            )

    @mute_logger('odoo.addons.sale_amazon.models.amazon_account')
    @mute_logger('odoo.addons.sale_amazon.models.stock_picking')
    def test_sync_orders_cancel_abort(self):
        """ Test the pickings that were confirmed at odoo and then order is canceled at Amazon. """

        def get_sp_api_response_mock(_account, operation_, **_kwargs):
            """ Return a mock response without making an actual call to the Selling Partner API. """
            base_response_ = common.OPERATIONS_RESPONSES_MAP[operation_]
            order_status_ = 'Unshipped' if not self.order_canceled else 'Canceled'
            if operation_ == 'getOrders':
                response_ = dict(base_response_, payload={
                    'LastUpdatedBefore': base_response_['payload']['LastUpdatedBefore'],
                    'Orders': [dict(common.ORDER_MOCK, OrderStatus=order_status_)]
                })
            else:
                response_ = base_response_
            return response_

        with patch(
            'odoo.addons.sale_amazon.utils.make_sp_api_request', new=get_sp_api_response_mock
        ):
            # Sync an order created on Amazon.
            self.order_canceled = False
            self.account._sync_orders(auto_commit=False)

            # Check the order state and validate the picking.
            order = self.env['sale.order'].search([('amazon_order_ref', '=', '123456789')])
            self.assertNotEqual(order.state, 'cancel')
            picking = self.env['stock.picking'].search([('sale_id', '=', order.id)])
            picking.move_ids.picked = True
            picking.carrier_id, picking.carrier_tracking_ref = self.carrier, self.tracking_ref
            picking._action_done()
            self.assertEqual(picking.state, 'done')

            # Sync an order canceled from Amazon.
            self.order_canceled = True
            self.account._sync_orders(auto_commit=False)

    def test_sync_orders_replacement(self):
        """ Test handling of Amazon replacement orders without currency. """

        def get_sp_api_response_mock(_account, operation_, **_kwargs):
            """ Return a mocked response without making an actual call to the SP-API. """
            base_response_ = common.OPERATIONS_RESPONSES_MAP[operation_]
            if operation_ == 'getOrders':
                response_ = dict(base_response_, payload={
                    'LastUpdatedBefore': base_response_['payload']['LastUpdatedBefore'],
                    'Orders': [dict(
                        common.ORDER_MOCK,
                        IsReplacementOrder='true',
                        ReplacedOrderId='replaced_order',
                        OrderTotal=dict(Amount='0'),
                    )],
                })
            elif operation_ == 'getOrderItems':
                response_ = dict(base_response_, payload={
                    'AmazonOrderId': base_response_['payload']['AmazonOrderId'],
                    'OrderItems': [dict(
                        ItemPrice=dict(Amount='0'),
                        ShippingPrice=dict(Amount='0'),
                        SellerSKU='TEST',
                        Title='Run Test, Run!',
                        QuantityOrdered=2,
                        OrderItemId='987654321',
                    )],
                })
            else:
                response_ = base_response_
            return response_

        def find_matching_product_mock(
            _self, product_code_, _default_xmlid, default_name_, default_type_
        ):
            """ Return a product created on-the-fly with the product code as internal reference. """
            product_ = self.env['product.product'].create({
                'name': default_name_,
                'type': default_type_,
                'list_price': 10.0,
                'sale_ok': False,
                'purchase_ok': False,
                'default_code': product_code_,
            })
            product_.product_tmpl_id.taxes_id = False
            return product_

        with patch(
            'odoo.addons.sale_amazon.utils.make_sp_api_request', new=get_sp_api_response_mock
        ), patch(
            'odoo.addons.sale_amazon.models.amazon_account.AmazonAccount._recompute_subtotal',
            new=lambda self_, subtotal_, *args_, **kwargs_: subtotal_,
        ), patch(
            'odoo.addons.sale_amazon.models.amazon_account.AmazonAccount._find_matching_product',
            new=find_matching_product_mock,
        ):
            partner = self.env['res.partner'].create({'name': 'Gederic Frilson'})
            currency = self.env['res.currency'].create({'name': 'QUA', 'symbol': 'Q'})
            pricelist = self.env['product.pricelist'].create({
                'name': 'QUA pricelist', 'currency_id': currency.id,
            })
            self.env['sale.order'].create({
                'partner_id': partner.id,
                'pricelist_id': pricelist.id,
                'amazon_order_ref': 'replaced_order',
            })

            self.account._sync_orders(auto_commit=False)

            order = self.env['sale.order'].search([('amazon_order_ref', '=', '123456789')])
            self.assertEqual(order.currency_id.name, 'QUA')
            self.assertEqual(order.amount_total, 0)

    def test_inventory_sync_is_skipped_when_disabled(self):
        """ Test that the inventory synchronization is skipped when the account has disabled it. """
        self.account.synchronize_inventory = False
        with patch(
            'odoo.addons.sale_amazon.utils.submit_feed', return_value='An_amazing_id'
        ) as mock:
            self.assertEqual(self.account.offer_ids, self.offer)
            self.assertEqual(self.offer.amazon_sync_status, False)
            self.account._sync_inventory()
            self.assertEqual(
                mock.call_count,
                0,
                msg="The stock synchronization is deactivated, no call should have been made.",
            )
            self.assertEqual(self.offer.amazon_sync_status, False)

    @mute_logger('odoo.addons.sale_amazon.models.amazon_account')
    @mute_logger('odoo.addons.sale_amazon.models.amazon_offer')
    def test_sync_inventory(self):
        """ Test the inventory availability confirmation synchronization. """
        self.account.synchronize_inventory = True
        with patch(
            'odoo.addons.sale_amazon.utils.submit_feed', return_value='An_amazing_id'
        ) as mock:
            self.assertEqual(self.account.offer_ids, self.offer)
            self.assertEqual(self.offer.amazon_sync_status, False)
            self.account._sync_inventory()
            self.assertEqual(self.offer.amazon_sync_status, 'processing')
            self.assertEqual(
                mock.call_count,
                1,
                msg="An inventory availability feed should be sent to Amazon for all the offers.",
            )

    @mute_logger('odoo.addons.sale_amazon.models.amazon_offer')
    def test_inventory_sync_is_skipped_if_loading_feed_data_fails(self):
        self.offer.amazon_feed_ref = 'incorrect json'  # force fetch of feed data
        self.offer.amazon_sync_status = False

        with (
            patch(
                'odoo.addons.sale_amazon.utils.submit_feed', return_value='An_amazing_id'
            ) as submit_feed_mock,
            patch(
                'odoo.addons.sale_amazon.utils.make_sp_api_request',
                side_effect=amazon_utils.AmazonRateLimitError(''),
            ) as make_sp_api_request_mock,
        ):
            self.account._sync_inventory()

        make_sp_api_request_mock.assert_called_once()
        self.assertEqual(self.offer.amazon_sync_status, 'error')

    def test_offer_get_feed_data(self):
        self.offer.amazon_feed_ref = 'incorrect json'  # force fetch of feed data

        with patch(
            'odoo.addons.sale_amazon.utils.make_sp_api_request',
            return_value={
                'items': [{
                    'sku': self.offer.sku,
                    'productTypes': [{'productType': 'PRODUCT'}],
                    'attributes': {'merchant_shipping_group': {}},
                }],
            },
        ):
            feed_info = self.offer._get_feed_data()

        self.assertIn(self.offer, feed_info)
        self.assertEqual(self.offer.amazon_feed_ref, '{"productType":"PRODUCT","is_fbm":true}')

    def test_offer_get_feed_data_fallback_when_missing_data(self):
        self.offer.amazon_feed_ref = 'incorrect json'  # force fetch of feed data

        with patch('odoo.addons.sale_amazon.utils.make_sp_api_request', return_value={'items': []}):
            feed_info = self.offer._get_feed_data()

        self.assertIn(self.offer, feed_info)
        self.assertEqual(self.offer.amazon_feed_ref, '{"productType":false,"is_fbm":false}')

    @mute_logger('odoo.addons.sale_amazon.models.amazon_offer')
    def test_offer_get_feed_data_fails_gracefully(self):
        self.offer.amazon_feed_ref = 'incorrect json'  # force fetch of feed data

        with patch(
            'odoo.addons.sale_amazon.utils.make_sp_api_request',
            side_effect=amazon_utils.AmazonRateLimitError(''),
        ):
            feed_info = self.offer._get_feed_data()

        self.assertNotIn(self.offer, feed_info)
        self.assertEqual(self.offer.amazon_sync_status, 'error')

    def test_offer_get_feed_info_calls_sp_api_only_if_needed(self):
        # Every necessary feed data is already stored
        self.offer.amazon_feed_ref = '{"productType":"PRODUCT","is_fbm":true}'

        with patch('odoo.addons.sale_amazon.utils.make_sp_api_request') as make_sp_api_request_mock:
            feed_info = self.offer._get_feed_data()

        make_sp_api_request_mock.assert_not_called()  # does not need to be called anymore
        self.assertIn(self.offer, feed_info)

    @mute_logger('odoo.addons.sale_amazon.models.amazon_account')
    @mute_logger('odoo.addons.sale_amazon.models.stock_picking')
    def test_sync_pickings(self):
        """ Test the pickings confirmation synchronization. """
        with patch(
            'odoo.addons.sale_amazon.utils.make_sp_api_request',
            new=lambda account_, operation_, **_kwargs: common.OPERATIONS_RESPONSES_MAP[operation_],
        ), patch(
            'odoo.addons.sale_amazon.utils.submit_feed', new=Mock(return_value='An_amazing_id'),
        ) as mock:
            self.account._sync_orders(auto_commit=False)
            order = self.env['sale.order'].search([('amazon_order_ref', '=', '123456789')])
            picking = self.env['stock.picking'].search([('sale_id', '=', order.id)])
            self.assertEqual(len(picking), 1, msg="FBM orders should generate exactly one picking.")
            picking.carrier_id, picking.carrier_tracking_ref = self.carrier, self.tracking_ref
            picking._action_done()
            self.assertEqual(picking.amazon_sync_status, 'pending')
            self.account.company_id.write({"street": "street1"})  # needed in no-demo
            picking._sync_pickings(account_ids=(self.account.id,))
            self.assertEqual(
                mock.call_count,
                1,
                msg="An order fulfillment feed should be sent to Amazon for each confirmed "
                    "picking.",
            )
            self.assertEqual(picking.amazon_sync_status, 'processing')

    def test_find_matching_product_search(self):
        """ Test the product search based on the internal reference. """
        self.env['product.product'].create({
            'name': "Test Name",
            'type': 'consu',
            'default_code': 'TEST_CODE',
        })
        self.assertTrue(self.account._find_matching_product('TEST_CODE', None, None, None))

    def test_find_matching_product_use_fallback(self):
        """ Test the product search failure with use of the fallback. """
        default_product = self.env['product.product'].create({
            'name': "Default Name", 'type': 'consu'
        })
        self.env['ir.model.data'].create({
            'module': 'sale_amazon',
            'name': 'test_xmlid',
            'model': 'product.product',
            'res_id': default_product.id,
        })
        self.assertTrue(
            self.account._find_matching_product('INCORRECT_CODE', 'test_xmlid', None, None)
        )

    def test_find_matching_product_regen_fallback(self):
        """ Test the product search failure with regeneration of the fallback. """
        default_product = self.env['product.product'].create({
            'name': "Default Name", 'type': 'consu',
        })
        self.env['ir.model.data'].create({
            'module': 'sale_amazon',
            'name': 'test_xmlid',
            'model': 'product.product',
            'res_id': default_product.id,
        })
        default_product.unlink()  # Simulate deletion of the default product added with data
        product = self.account._find_matching_product(
            'INCORRECT_CODE', 'test_xmlid', 'Default Name', 'consu'
        )
        self.assertEqual(product.name, 'Default Name')
        self.assertEqual(product.type, 'consu')
        self.assertEqual(product.list_price, 0.)
        self.assertFalse(product.sale_ok)
        self.assertFalse(product.purchase_ok)

    def test_find_matching_product_no_fallback(self):
        """ Test the product search failure without regeneration of the fallback. """
        self.assertFalse(self.account._find_matching_product(
            'INCORRECT_CODE', 'test_xmlid', 'Default Name', 'consu', fallback=False
        ))
        self.assertFalse(self.env.ref('sale_amazon.test_xmlid', raise_if_not_found=False))

    def test_get_pricelist_search(self):
        """ Test the pricelist search. """
        currency = self.env['res.currency'].create({'name': 'TEST', 'symbol': 'T'})
        self.env['product.pricelist'].create({
            'name': 'Amazon Pricelist %s' % currency.name,
            'active': False,
            'currency_id': currency.id,
        })
        pricelist = self.env['product.pricelist']
        pricelists_count = pricelist.with_context(active_test=False).search_count([])
        self.assertTrue(self.account._find_or_create_pricelist(currency))
        self.assertEqual(self.env['product.pricelist'].with_context(
            active_test=False).search_count([]), pricelists_count)

    def test_get_pricelist_creation(self):
        """ Test the pricelist creation. """
        currency = self.env['res.currency'].create({'name': 'TEST', 'symbol': 'T'})
        pricelist = self.env['product.pricelist']
        pricelists_count = pricelist.with_context(active_test=False).search_count([])
        pricelist = self.account._find_or_create_pricelist(currency)
        self.assertEqual(self.env['product.pricelist'].with_context(
            active_test=False).search_count([]), pricelists_count + 1)
        self.assertFalse(pricelist.active)
        self.assertEqual(pricelist.currency_id.id, currency.id)

    def test_get_partners_no_creation_same_partners(self):
        """ Test the partners search with contact as delivery. """
        with patch(
            'odoo.addons.sale_amazon.utils.make_sp_api_request',
            new=lambda account_, operation_, **kwargs: common.OPERATIONS_RESPONSES_MAP[operation_],
        ):
            country_id = self.env['res.country'].search([('code', '=', 'US')], limit=1).id
            self.env['res.partner'].create({
                'name': 'Gederic Frilson',
                'is_company': True,
                'street': '123 RainBowMan Street',
                'zip': '12345-1234',
                'city': 'New Duck City DC',
                'country_id': country_id,
                'state_id': self.env['res.country.state'].search(
                    [('country_id', '=', country_id), ('code', '=', 'CA')], limit=1
                ).id,
                'phone': '+1 234-567-8910 ext. 12345',
                'customer_rank': 1,
                'company_id': self.account.company_id.id,
                'amazon_email': 'iliketurtles@marketplace.amazon.com',
            })
            contacts_count = self.env['res.partner'].search_count([])
            order_data = common.OPERATIONS_RESPONSES_MAP['getOrders']['payload']['Orders'][0]
            contact, delivery = self.account._find_or_create_partners_from_data(order_data)
            self.assertEqual(self.env['res.partner'].search_count([]), contacts_count)
            self.assertEqual(contact.id, delivery.id)
            self.assertEqual(contact.type, 'contact')
            self.assertEqual(contact.amazon_email, 'iliketurtles@marketplace.amazon.com')

    def test_get_partners_no_creation_different_partners(self):
        """ Test the partners search with different partners for contact and delivery. """
        country_id = self.env['res.country'].search([('code', '=', 'US')], limit=1).id
        new_partner_vals = {
            'is_company': True,
            'street': '123 RainBowMan Street',
            'zip': '12345-1234',
            'city': 'New Duck City DC',
            'country_id': country_id,
            'state_id': self.env['res.country.state'].search(
                [('country_id', '=', country_id), ('code', '=', 'CA')], limit=1
            ).id,
            'phone': '+1 234-567-8910 ext. 12345',
            'customer_rank': 1,
            'company_id': self.account.company_id.id,
            'amazon_email': 'iliketurtles@marketplace.amazon.com',
        }
        contact = self.env['res.partner'].create(dict(new_partner_vals, name='Gederic Frilson'))
        self.env['res.partner'].create(dict(
            new_partner_vals,
            name='Gederic Frilson Delivery',
            type='delivery',
            parent_id=contact.id,
        ))
        partners_count = self.env['res.partner'].search_count([])
        order_data = dict(common.ORDER_MOCK, ShippingAddress=dict(
            common.ORDER_ADDRESS_MOCK, Name='Gederic Frilson Delivery'
        ))
        contact, delivery = self.account._find_or_create_partners_from_data(order_data)
        self.assertEqual(self.env['res.partner'].search_count([]), partners_count)
        self.assertNotEqual(contact.id, delivery.id)
        self.assertEqual(delivery.type, 'delivery')
        self.assertEqual(delivery.parent_id.id, contact.id)
        self.assertEqual(contact.amazon_email, delivery.amazon_email)

    def test_get_partners_creation_delivery(self):
        """ Test the partners search with creation of the delivery. """

        def get_sp_api_response_mock(_account, operation_, **_kwargs):
            """ Return a mocked response without making an actual call to the SP-API. """
            base_response_ = common.OPERATIONS_RESPONSES_MAP[operation_]
            if operation_ == 'getOrderAddress':
                return dict(base_response_, payload={
                    'ShippingAddress': {
                        'AddressLine1': '123 RainBowMan Street',
                        'Phone': '+1 234-567-8910 ext. 12345',
                        'PostalCode': '12345-1234',
                        'City': 'New Duck City DC',
                        'StateOrRegion': 'CA',
                        'CountryCode': 'US',
                        'Name': 'Gederic Frilson Delivery',
                        'AddressType': 'Commercial',
                    }
                })
            else:
                return base_response_

        with patch(
            'odoo.addons.sale_amazon.utils.make_sp_api_request', new=get_sp_api_response_mock
        ):
            self.env['res.partner'].create({
                'name': 'Gederic Frilson',
                'company_id': self.account.company_id.id,
                'amazon_email': 'iliketurtles@marketplace.amazon.com',
            })
            partners_count = self.env['res.partner'].search_count([])
            order_data = common.OPERATIONS_RESPONSES_MAP['getOrders']['payload']['Orders'][0]
            contact, delivery = self.account._find_or_create_partners_from_data(order_data)
            self.assertEqual(
                self.env['res.partner'].search_count([]),
                partners_count + 1,
                msg="A delivery partner should be created when a field of the address is different "
                    "from that of the contact.",
            )
            self.assertNotEqual(contact.id, delivery.id)
            self.assertEqual(delivery.type, 'delivery')
            self.assertEqual(delivery.parent_id.id, contact.id)
            self.assertEqual(delivery.company_id.id, self.account.company_id.id)
            self.assertEqual(contact.amazon_email, delivery.amazon_email)

    def test_get_partners_creation_contact(self):
        """ Test the partners search with creation of the contact. """
        with patch(
            'odoo.addons.sale_amazon.utils.make_sp_api_request',
            new=lambda account_, operation_, **kwargs: common.OPERATIONS_RESPONSES_MAP[operation_],
        ):
            partners_count = self.env['res.partner'].search_count([])
            order_data = common.OPERATIONS_RESPONSES_MAP['getOrders']['payload']['Orders'][0]
            contact, delivery = self.account._find_or_create_partners_from_data(order_data)
            self.assertEqual(
                self.env['res.partner'].search_count([]),
                partners_count + 1,
                "No delivery partner should be created when the contact is not found and the name "
                "on the order is the same as that of the address.",
            )
            self.assertEqual(contact.id, delivery.id)
            self.assertEqual(contact.name, 'Gederic Frilson')
            self.assertEqual(contact.type, 'contact')
            self.assertTrue(contact.is_company)
            self.assertEqual(contact.street, '123 RainBowMan Street')
            self.assertFalse(contact.street2)
            self.assertEqual(contact.zip, '12345-1234')
            self.assertEqual(contact.city, 'New Duck City DC')
            self.assertEqual(contact.country_id.code, 'US')
            self.assertEqual(contact.state_id.code, 'CA')
            self.assertEqual(contact.phone, '+1 234-567-8910 ext. 12345')
            self.assertEqual(contact.customer_rank, 1)
            self.assertEqual(contact.company_id.id, self.account.company_id.id)
            self.assertEqual(contact.amazon_email, 'iliketurtles@marketplace.amazon.com')

    def test_get_partners_creation_contact_delivery(self):
        """ Test the partners search with creation of the contact and delivery. """
        partners_count = self.env['res.partner'].search_count([])
        order_data = dict(common.ORDER_MOCK, BuyerInfo=dict(
            common.ORDER_BUYER_INFO_MOCK, BuyerName='Not Gederic Frilson'
        ))
        contact, delivery = self.account._find_or_create_partners_from_data(order_data)
        self.assertEqual(
            self.env['res.partner'].search_count([]),
            partners_count + 2,
            msg="A contact partner and a delivery partner should be created when the contact "
                "is not found and the name on the order is different from that of the address.",
        )
        self.assertNotEqual(contact.id, delivery.id)
        self.assertEqual(contact.type, 'contact')
        self.assertEqual(delivery.type, 'delivery')
        self.assertEqual(delivery.parent_id.id, contact.id)
        self.assertEqual(contact.company_id.id, delivery.company_id.id)
        self.assertEqual(contact.amazon_email, delivery.amazon_email)

    def test_get_partners_missing_buyer_name(self):
        """ Test the partners search with missing buyer name. """
        self.env['res.partner'].create({
            'name': 'Gederic Frilson',
            'company_id': self.account.company_id.id,
            'amazon_email': 'iliketurtles@marketplace.amazon.com',
        })
        partners_count = self.env['res.partner'].search_count([])
        order_data = dict(common.ORDER_MOCK, BuyerInfo=dict(
            common.ORDER_BUYER_INFO_MOCK, BuyerName=None
        ))
        contact, delivery = self.account._find_or_create_partners_from_data(order_data)
        self.assertEqual(
            self.env['res.partner'].search_count([]),
            partners_count + 2,
            msg="A contact partner should be created when the buyer name is missing, "
                "regardless of whether the same customer already had a partner, and a delivery "
                "partner should also be created if the address name is different.",
        )
        self.assertNotEqual(contact.id, delivery.id)
        self.assertEqual(contact.type, 'contact')
        self.assertEqual(delivery.type, 'delivery')
        self.assertEqual(delivery.parent_id.id, contact.id)
        self.assertEqual(contact.amazon_email, 'iliketurtles@marketplace.amazon.com')
        self.assertEqual(
            contact.street,
            '123 RainBowMan Street',
            msg="Partners synchronized with partial personal information should still hold all "
                "the available personal information.",
        )

    def test_get_partners_missing_amazon_email(self):
        """ Test the partners search with missing amazon email. """
        self.env['res.partner'].create({
            'name': 'Gederic Frilson',
            'company_id': self.account.company_id.id,
            'amazon_email': 'iliketurtles@marketplace.amazon.com',
        })
        partners_count = self.env['res.partner'].search_count([])
        order_data = dict(common.ORDER_MOCK, BuyerInfo=dict(
            common.ORDER_BUYER_INFO_MOCK, BuyerEmail=None
        ))
        contact, _delivery = self.account._find_or_create_partners_from_data(order_data)
        self.assertEqual(
            self.env['res.partner'].search_count([]),
            partners_count + 1,
            msg="A contact partner should always be created when the amazon email is missing.",
        )
        self.assertFalse(contact.amazon_email)

    def test_get_partners_arbitrary_fields(self):
        """ Test the partners search with all PII filled but in arbitrary fields. """
        order_data = dict(common.ORDER_MOCK, ShippingAddress=dict(
            common.ORDER_ADDRESS_MOCK, AddressLine1=None, AddressLine2='123 test Street',
        ))
        contact, _delivery = self.account._find_or_create_partners_from_data(order_data)
        self.assertFalse(contact.street)
        self.assertTrue(contact.street2)
        self.assertTrue(contact.phone)
        self.assertTrue(contact.customer_rank)
        self.assertTrue(contact.amazon_email)

    def _get_activity_count(self, contact):
        """" Return activity count of given the contact. """
        activity_id = self.env.ref('mail.mail_activity_data_todo').id
        return self.env['mail.activity'].search_count([
            ('activity_type_id', '=', activity_id),
            ('res_model_id', '=', 'res.partner'),
            ('res_id', '=', contact.id),
        ])

    def test_activity_on_partners_for_no_matching_state(self):
        """ Test activity created for the salesman if the state received in the Amazon data
        didn't match any existing state when creating a partner.
        """
        order_data = dict(common.ORDER_MOCK, ShippingAddress=dict(
            common.ORDER_ADDRESS_MOCK, StateOrRegion="dummy_state"
        ))
        contact, delivery = self.account._find_or_create_partners_from_data(order_data)
        self.assertEqual(self._get_activity_count(contact), 1)
        self.assertEqual(self._get_activity_count(delivery), 1)

    def test_no_activity_on_partners_for_no_state_in_amazon_data(self):
        """ Test no activity created for the salesman if there is no state received in the Amazon
        data.
        """
        order_data = dict(common.ORDER_MOCK, ShippingAddress=dict(
            common.ORDER_ADDRESS_MOCK, StateOrRegion=None,
        ))
        contact, delivery = self.account._find_or_create_partners_from_data(order_data)
        self.assertFalse(self._get_activity_count(contact))
        self.assertFalse(self._get_activity_count(delivery))

    def test_get_amazon_offer_search(self):
        """ Test the offer search. """
        marketplace = self.env['amazon.marketplace'].search([('api_ref', '=', 'ATVPDKIKX0DER')])
        self.env['amazon.offer'].create({
            'account_id': self.account.id,
            'marketplace_id': marketplace.id,
            'product_id': self.account._find_matching_product(
                None, 'default_product', None, None
            ).id,
            'sku': 'TEST',
        })
        offers_count = self.env['amazon.offer'].search_count([])
        self.assertTrue(self.account._find_or_create_offer('TEST', marketplace))
        self.assertEqual(self.env['amazon.offer'].search_count([]), offers_count)

    def test_get_amazon_offer_creation(self):
        """ Test the offer creation. """
        marketplace = self.env['amazon.marketplace'].search([('api_ref', '=', 'ATVPDKIKX0DER')])
        offers_count = self.env['amazon.offer'].search_count([])
        offer = self.account._find_or_create_offer('TEST', marketplace)
        self.assertEqual(self.env['amazon.offer'].search_count([]), offers_count + 1)
        self.assertEqual(offer.account_id.id, self.account.id)
        self.assertEqual(offer.company_id.id, self.account.company_id.id)
        self.assertEqual(offer.marketplace_id.api_ref, 'ATVPDKIKX0DER')
        self.assertEqual(offer.sku, 'TEST')
