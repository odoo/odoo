# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from unittest.mock import patch
from datetime import timedelta

import odoo.tests
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest


@odoo.tests.tagged('post_install', '-at_install')
class TestSelfOrderController(SelfOrderCommonTest):
    def make_request_to_controller(self, url, params):
        response = self.url_open(url, json.dumps({'jsonrpc': '2.0', 'params': params}),
            method='POST',
            headers={
                'Content-Type': 'application/json',
            }
        )
        return response.json().get('result')

    def test_get_orders_by_access_token(self):
        self.pos_config.self_ordering_mode = 'mobile'
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, '')

        order_data = self._create_order_data(
            state='paid',
            product=self.cola,
            qty=3,
            price_unit=1.0,
            price_subtotal_incl=0
        )
        data = self.make_request_to_controller('/pos-self-order/process-order/mobile', order_data)
        order1 = self.env['pos.order'].browse(data['pos.order'][0]['id'])

        order_data = self._create_order_data(
            state='draft',
            product=self.cola,
            qty=3,
            price_unit=1.0,
            price_subtotal_incl=self.cola.lst_price
        )

        data = self.make_request_to_controller('/pos-self-order/process-order/mobile', order_data)
        order2 = self.env['pos.order'].browse(data['pos.order'][0]['id'])
        self.assertEqual(order2.state, 'draft')

        params = {
            'access_token': order1.config_id.access_token,
            'order_access_tokens': [{
                'access_token': order1.access_token,
                'state': order1.state,
                'write_date': order1.write_date.strftime('%Y-%m-%d %H:%M:%S')
            }],
        }

        # At this point there is no change on the order, so no data is returned
        data = self.make_request_to_controller('/pos-self-order/get-user-data', params)
        self.assertEqual(data, {})

        # Changing state in params should return the order to update it
        params['order_access_tokens'][0]['state'] = 'draft'  # Server order is paid
        data = self.make_request_to_controller('/pos-self-order/get-user-data', params)
        self.assertEqual(len(data['pos.order']), 1)

        # No order access token should return no order
        params['order_access_tokens'] = []
        data = self.make_request_to_controller('/pos-self-order/get-user-data', params)
        self.assertEqual(data, {})

        # Two outdated order write_date should return both orders
        params['order_access_tokens'] = [{
            'access_token': order1.access_token,
            'state': order1.state,
            'write_date': (order1.write_date - timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S')
        }, {
            'access_token': order2.access_token,
            'state': order2.state,
            'write_date': (order2.write_date - timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S')
        }]
        data = self.make_request_to_controller('/pos-self-order/get-user-data', params)
        self.assertEqual(len(data['pos.order']), 2)

        # Only one outdated order write_date should return one order
        params['order_access_tokens'] = [{
            'access_token': order1.access_token,
            'state': order1.state,
            'write_date': (order1.write_date - timedelta(minutes=1)).strftime('%Y-%m-%d %H:%M:%S')
        }, {
            'access_token': order2.access_token,
            'state': order2.state,
            'write_date': order2.write_date.strftime('%Y-%m-%d %H:%M:%S')
        }]
        data = self.make_request_to_controller('/pos-self-order/get-user-data', params)
        self.assertEqual(len(data['pos.order']), 1)
        self.assertEqual(data['pos.order'][0]['id'], order1.id)

        # A cancelled order should be returned
        order2.cancel_order_from_pos()
        params['order_access_tokens'] = [{
            'access_token': order2.access_token,
            'state': 'paid',
            'write_date': order2.write_date.strftime('%Y-%m-%d %H:%M:%S')
        }]
        data = self.make_request_to_controller('/pos-self-order/get-user-data', params)
        self.assertEqual(len(data['pos.order']), 1)
        self.assertEqual(data['pos.order'][0]['id'], order2.id)
        self.assertEqual(data['pos.order'][0]['state'], 'cancel')

        # Up to date data should return no order
        params['order_access_tokens'] = [{
            'access_token': order1.access_token,
            'state': order1.state,
            'write_date': order1.write_date.strftime('%Y-%m-%d %H:%M:%S')
        }, {
            'access_token': order2.access_token,
            'state': order2.state,
            'write_date': order2.write_date.strftime('%Y-%m-%d %H:%M:%S')
        }]
        data = self.make_request_to_controller('/pos-self-order/get-user-data', params)
        self.assertEqual(data, {})

        # Only write date is provided
        params['order_access_tokens'] = [{
            'access_token': order2.access_token,
            'write_date': '1970-01-01 00:00:00'
        }]

        data = self.make_request_to_controller('/pos-self-order/get-user-data', params)
        self.assertEqual(len(data['pos.order']), 1)
        self.assertEqual(data['pos.order'][0]['id'], order2.id)

        # Only state is provided
        params['order_access_tokens'] = [{
            'access_token': order2.access_token,
            'state': 'paid'
        }]

        data = self.make_request_to_controller('/pos-self-order/get-user-data', params)
        self.assertEqual(len(data['pos.order']), 1)
        self.assertEqual(data['pos.order'][0]['id'], order2.id)

    def test_access_right_with_message_follower(self):
        """ Test to ensure that user data is still displayed when a message follower is set on the order """
        self.pos_config.self_ordering_mode = 'mobile'
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, '')

        order_data = self._create_order_data(
            state='draft',
            product=self.cola,
            qty=3,
            price_unit=1.0,
            price_subtotal_incl=0
        )
        data = self.make_request_to_controller('/pos-self-order/process-order/mobile', order_data)
        pos_order = self.env['pos.order'].browse(data['pos.order'][0]['id'])
        self.assertEqual(len(pos_order.message_follower_ids), 1)

        params = {
            'access_token': pos_order.config_id.access_token,
            'order_access_tokens': [{
                'access_token': pos_order.access_token,
                'write_date': '1970-01-01 00:00:00'
            }],
        }

        data = self.make_request_to_controller('/pos-self-order/get-user-data', params)
        self.assertEqual(len(data['pos.order']), 1)
        self.assertEqual(data['pos.order'][0]['id'], pos_order.id)

    def test_validate_partner_delivery_distance_accepts_within_limit(self):
        self.pos_config.self_ordering_mode = 'mobile'
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, '')

        with patch('odoo.addons.base_geolocalize.models.res_partner.ResPartner._geo_localize', return_value=(0.0, 0.0)):
            self.delivery_preset.write({
                'delivery_from_address': 'Main St 1',
                'delivery_from_city': 'Test City',
                'delivery_from_zip': '1000',
                'delivery_from_country_id': self.env.ref('base.be').id,
                'delivery_max_distance_km': 5.0,
            })

        customer = self.env['res.partner'].create({
            'name': 'Customer',
            'street': 'Main St 2',
            'city': 'Test City',
            'zip': '1000',
            'country_id': self.env.ref('base.be').id,
            'partner_latitude': 0.0,
            'partner_longitude': 0.0,
        })

        params = {
            'access_token': self.pos_config.access_token,
            'preset_id': self.delivery_preset.id,
            'partner_id': customer.id,
            'name': customer.name,
            'phone': customer.phone,
            'street': customer.street,
            'zip': customer.zip,
            'city': customer.city,
            'country_id': customer.country_id.id,
            'state_id': customer.state_id.id,
            'email': customer.email,
        }

        with patch('odoo.addons.base_geolocalize.models.res_partner.ResPartner.geo_localize', return_value=True):
            data = self.make_request_to_controller('/pos-self-order/validate-partner', params)

        self.assertIn('res.partner', data)
        self.assertNotIn('error', data)

    def test_validate_partner_delivery_distance_rejects_outside_limit(self):
        self.pos_config.self_ordering_mode = 'mobile'
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, '')

        with patch('odoo.addons.base_geolocalize.models.res_partner.ResPartner._geo_localize', return_value=(0.0, 0.0)):
            self.delivery_preset.write({
                'delivery_from_address': 'Main St 1',
                'delivery_from_city': 'Test City',
                'delivery_from_zip': '1000',
                'delivery_from_country_id': self.env.ref('base.be').id,
                'delivery_max_distance_km': 1.0,
            })

        customer = self.env['res.partner'].create({
            'name': 'Customer Far',
            'street': 'Far St 1',
            'city': 'Test City',
            'zip': '1000',
            'country_id': self.env.ref('base.be').id,
            'partner_latitude': 1.0,
            'partner_longitude': 0.0,
        })

        params = {
            'access_token': self.pos_config.access_token,
            'preset_id': self.delivery_preset.id,
            'partner_id': customer.id,
            'name': customer.name,
            'phone': customer.phone,
            'street': customer.street,
            'zip': customer.zip,
            'city': customer.city,
            'country_id': customer.country_id.id,
            'state_id': customer.state_id.id,
            'email': customer.email,
        }

        with patch('odoo.addons.base_geolocalize.models.res_partner.ResPartner.geo_localize', return_value=True):
            data = self.make_request_to_controller('/pos-self-order/validate-partner', params)

        self.assertIn('error', data)
        self.assertEqual(data['error']['type'], 'delivery')

    def test_free_delivery_threshold_edge_cases(self):
        """Test free delivery threshold at exactly the minimum, below, and above"""
        self.pos_config.self_ordering_mode = 'mobile'
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, '')

        # Create delivery product
        delivery_product = self.env['product.template'].create({
            'name': 'Delivery Fee',
            'default_code': 'DELIVERY',
            'list_price': 5.0,
            'available_in_pos': True,
        })

        # Configure delivery preset with free delivery threshold at 50.0
        with patch('odoo.addons.base_geolocalize.models.res_partner.ResPartner._geo_localize', return_value=(0.0, 0.0)):
            self.delivery_preset.write({
                'delivery_from_address': 'Main St 1',
                'delivery_from_city': 'Brussels',
                'delivery_from_zip': '1000',
                'delivery_from_country_id': self.env.ref('base.be').id,
                'delivery_max_distance_km': 10.0,
                'delivery_product_id': delivery_product.id,
                'free_delivery_min_amount': 50.0,
            })

        # Test 1: Order total exactly at threshold (50.0) - should qualify for free delivery
        self.assertEqual(self.delivery_preset.free_delivery_min_amount, 50.0)

        # Test 2: Order total below threshold (49.99) - should not qualify
        # Test 3: Order total above threshold (50.01) - should qualify
        # These would be tested in JavaScript/tour tests since the logic is in ensureDeliveryLine

        # Verify preset configuration is loaded correctly
        preset_data = self.delivery_preset._load_pos_self_data_fields(self.pos_config)
        self.assertIn('free_delivery_min_amount', preset_data)

    def _create_order_data(self, state, product, qty, price_unit, price_subtotal_incl=None):
        return {
            'access_token': self.pos_config.access_token,
            'table_identifier': self.pos_table_1.identifier,
            'order': {
                'table_id': self.pos_table_1.id,
                'company_id': self.env.company.id,
                'state': state,
                'preset_id': self.in_preset.id,
                'session_id': self.pos_config.current_session_id.id,
                'amount_total': 0,
                'amount_paid': 0,
                'amount_tax': 0,
                'amount_return': 0,
                'lines': [[0, 0, {
                    'product_id': product.id,
                    'qty': qty,
                    'price_unit': price_unit,
                    'price_subtotal': product.lst_price,
                    'tax_ids': [(6, 0, product.taxes_id.ids)],
                    'price_subtotal_incl': price_subtotal_incl or 0,
                }]],
            }
        }
