# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from copy import deepcopy
from datetime import timedelta
from uuid import uuid4

import odoo.tests
from odoo import Command
from odoo.tests import JsonRpcException
from odoo.tools import mute_logger

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
        data = {
            'order_data': {
                'name': 'Order/0001',
                'table_id': self.pos_table_1.id,
            },
            'line_data': [{
                'qty': 3,
                'price_unit': 1.0,
                'product_id': self.cola.id,
            }],
            'payment_data': [
                {'payment_method_id': self.bank_payment_method.id}
            ]
        }

        order1, _ = self.create_backend_pos_order(data)
        data['payment_data'] = []
        order2, _ = self.create_backend_pos_order(data)
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
        order2.action_pos_order_cancel()
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

        params = {
            'access_token': self.pos_config.access_token,
            'table_identifier': self.pos_table_1.identifier,
            'order': {
                'company_id': self.env.company.id,
                'uuid': '61f8181c-18e1-4b83-8a7b-21224750fe2f',
                'state': 'draft',
                'preset_id': self.in_preset.id,
                'session_id': self.pos_config.current_session_id.id,
                'amount_total': 0,
                'amount_paid': 0,
                'amount_tax': 0,
                'amount_return': 0,
                'lines': [[0, 0, {'uuid': str(uuid4()), 'product_id': self.cola.id, 'qty': 1,
                                  'price_unit': self.cola.lst_price,
                                  'price_subtotal': self.cola.lst_price,
                                  'tax_ids': [(6, 0, self.cola.taxes_id.ids)],
                                  'price_subtotal_incl': 0,
                                  }]]
            },
        }
        data = self.make_request_to_controller('/pos-self-order/process-order/mobile', params)
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

    def test_preparation_categories_are_loaded(self):
        """
        Preparation categories needs to be loaded in the self-ordering interface
        if there are printers linked to those categories, even if those
        categories are not available for the self-ordering interface.
        If a category is missing changes cannot be computed
        """
        moda_categ = self.env['pos.category'].create({'name': 'MODA'})
        stva_categ = self.env['pos.category'].create({'name': 'STVA'})
        adgu_categ = self.env['pos.category'].create({'name': 'ADGU'})
        manv_categ = self.env['pos.category'].create({'name': 'MANV'})
        ltra_categ = self.env['pos.category'].create({'name': 'LTRA'})
        lowe_categ = self.env['pos.category'].create({'name': 'LOWE'})
        mool_categ = self.env['pos.category'].create({'name': 'MOOL'})
        self.cola.pos_categ_ids = [moda_categ.id, stva_categ.id, lowe_categ.id, mool_categ.id, adgu_categ.id, manv_categ.id, ltra_categ.id]

        printer_1 = self.env['pos.printer'].create({
            'name': 'Preparation Printer',
            'epson_printer_ip': '127.0.0.1',
            'printer_type': 'epson_epos',
            'product_categories_ids': [moda_categ.id, stva_categ.id],
        })

        printer_2 = self.env['pos.printer'].create({
            'name': 'Preparation Printer',
            'epson_printer_ip': '127.0.0.1',
            'printer_type': 'epson_epos',
            'product_categories_ids': [adgu_categ.id, manv_categ.id, ltra_categ.id],
        })

        self.pos_config.write({
            'use_presets': False,
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'limit_categories': True,
            'iface_available_categ_ids': [mool_categ.id],
            'printer_ids': [printer_1.id, printer_2.id],
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()
        data = self.make_request_to_controller('/pos-self/data/' + str(self.pos_config.id), {
            'access_token': self.pos_config.access_token,
        })
        loaded_category_ids = [category['id'] for category in data['pos.category']]
        self.assertIn(mool_categ.id, loaded_category_ids, "The category linked to the printer should be loaded")
        self.assertIn(adgu_categ.id, loaded_category_ids, "The category linked to the printer should be loaded")
        self.assertIn(manv_categ.id, loaded_category_ids, "The category linked to the printer should be loaded")
        self.assertIn(ltra_categ.id, loaded_category_ids, "The category linked to the printer should be loaded")
        self.assertIn(moda_categ.id, loaded_category_ids, "The category linked to the printer should be loaded")
        self.assertIn(stva_categ.id, loaded_category_ids, "The category linked to the printer should be loaded")
        self.assertNotIn(lowe_categ.id, loaded_category_ids, "The category not linked to any printer should not be loaded")
        self.start_tour(self_route, "test_preparation_categories_are_loaded")

    def test_generate_return_values_includes_payment_method(self):
        self.pos_config.write({
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, '')

        payment_method = self.pos_config.payment_method_ids[0]
        order, _ = self.create_backend_pos_order({
            'line_data': [{'qty': 1, 'price_unit': 2.2, 'product_id': self.cola.id}],
            'payment_data': [{'payment_method_id': payment_method.id}],
        })

        params = {
            'access_token': self.pos_config.access_token,
            'order_access_tokens': [{
                'access_token': order.access_token,
            }],
        }
        data = self.make_request_to_controller('/pos-self-order/get-user-data', params)

        self.assertIn('pos.payment.method', data)
        returned_pm_ids = {pm['id'] for pm in data['pos.payment.method']}
        self.assertIn(payment_method.id, returned_pm_ids)

    def test_config_session_loaded_fields(self):
        self.pos_config.write({
            'use_presets': False,
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        data = self.make_request_to_controller('/pos-self/data/' + str(self.pos_config.id), {})

        self.assertEqual(len(data['pos.config']), 1)
        config_data = data['pos.config'][0]
        self.assertEqual(config_data['id'], self.pos_config.id)
        self.assertEqual(config_data['self_ordering_mode'], 'mobile')
        self.assertTrue(len(config_data['_self_ordering_image_home_ids']) > 1)
        self.assertFalse(config_data.get('access_token'))
        self.assertFalse(config_data.get('self_ordering_url'))

        self.assertEqual(len(data['pos.session']), 1)
        session_data = data['pos.session'][0]
        self.assertEqual(session_data['id'], self.pos_config.current_session_id.id)
        self.assertEqual(session_data['state'], 'opened')
        self.assertFalse(config_data.get('access_token'))

    def test_order_sanatization(self):
        self.pos_config.write({
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, '')
        params = {
            'company_id': self.env.company.id,
            'uuid': '61f8181c-18e1-4b83-8a7b-21224750fe2f',
            'state': 'draft',
            'preset_id': self.in_preset.id,
            'session_id': self.pos_config.current_session_id.id,
            'amount_total': 0,
            'amount_paid': 0,
            'account_move': 'test',  # This field should be removed by the _check_pos_order method
            'access_token': 'test',  # This field should be removed by the _check_pos_order method
            'amount_tax': 0,
            'amount_return': 0,
            'lines': [[0, 0, {
                    'uuid': str(uuid4()),
                    'product_id': self.cola.id, 'qty': 1,
                    'price_unit': self.cola.lst_price,
                    'price_subtotal': self.cola.lst_price,
                    'tax_ids': [(6, 0, self.cola.taxes_id.ids)],
                    'price_subtotal_incl': 0,
                }],
            ],
        }
        data = self.env['pos.order']._check_pos_order(self.pos_config, params, 'mobile')
        self.assertFalse('account_move' in data)  # Do not add it back, if needed contact the PoS team.
        self.assertFalse('access_token' in data)  # Do not add it back, if needed contact the PoS team.

    def test_foreign_line_update_is_dropped(self):
        self.pos_config.write({
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, '')

        victim_order, _ = self.create_backend_pos_order({
            'order_data': {'table_id': self.pos_table_1.id},
            'line_data': [{'qty': 1, 'price_unit': 1.0, 'product_id': self.cola.id}],
        })
        victim_line = victim_order.lines[0]

        params = {
            'uuid': '61f8181c-18e1-4b83-8a7b-21224750fe2f',  # attacker order, unrelated to victim_order
            'state': 'draft',
            'preset_id': self.in_preset.id,
            'session_id': self.pos_config.current_session_id.id,
            'lines': [[Command.UPDATE, victim_line.id, {
                'product_id': self.cola.id, 'qty': 10,
                'price_unit': self.cola.lst_price,
            }]],
        }
        data = self.env['pos.order']._check_pos_order(self.pos_config, params, 'mobile')

        # The update targets a line of another order: it must not reach sync_from_ui.
        self.assertFalse(data['lines'])
        self.assertEqual(victim_line.qty, 1)
        self.assertEqual(victim_line.order_id, victim_order)

    def _setup_relation_orders(self):
        self.pos_config.write({
            'self_ordering_mode': 'kiosk',
            'use_presets': False,
            'available_preset_ids': [Command.clear()],
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, '')
        self.other_config = self.pos_config.copy({
            'name': 'Other shop',
            'payment_method_ids': [Command.set(self.bank_payment_method.ids)],
        })
        self.combo = self.env['product.combo'].create({
            'name': 'Self-order combo',
            'combo_item_ids': [Command.create({'product_id': self.cola.id})],
        })
        self.combo_product = self.env['product.product'].create({
            'name': 'Self-order combo product',
            'type': 'combo',
            'available_in_pos': True,
            'list_price': 10,
            'combo_ids': [Command.set(self.combo.ids)],
            'taxes_id': False,
        })
        self.victim_order, _ = self.create_backend_pos_order({
            'line_data': [{'product_id': self.cola.id, 'qty': 1}],
        })
        self.victim_order._ensure_access_token()
        self.payment = self.env['pos.payment'].create({
            'pos_order_id': self.victim_order.id,
            'payment_method_id': self.bank_payment_method.id,
            'amount': 7,
        })
        self.order_payload = {
            'uuid': str(uuid4()),
            'state': 'draft',
            'preset_id': False,
            'session_id': self.pos_config.current_session_id.id,
            'amount_total': 0,
            'amount_tax': 0,
            'amount_paid': 0,
            'amount_return': 0,
            'lines': [[Command.CREATE, 0, {
                'uuid': str(uuid4()), 'product_id': self.cola.id, 'qty': 1, 'price_unit': 0,
            }]],
        }

    def _post(self, order, error=None):
        params = {
            'access_token': self.pos_config.access_token,
            'table_identifier': None,
            'order': order,
        }
        route = '/pos-self-order/process-order/kiosk/'
        records_to_check = [
            (self.victim_order, ['uuid', 'state', 'session_id', 'access_token', 'lines', 'payment_ids', 'amount_total']),
            (self.victim_order.lines, ['uuid', 'order_id', 'qty', 'combo_parent_id', 'combo_line_ids']),
            (self.payment, ['uuid', 'pos_order_id', 'amount', 'payment_method_id']),
            (self.pos_config | self.other_config, [
                'name', 'access_token', 'payment_method_ids', 'self_ordering_mode', 'trusted_config_ids',
            ]),
        ]
        before = [records.read(fields) for records, fields in records_to_check]
        res = None
        if error is None:
            res = self.make_jsonrpc_request(route, params)
            self.assertEqual({record['uuid'] for record in res['pos.order']}, {order['uuid']})
            self.assertFalse(res.get('pos.payment'))
            self.assertFalse(set(self.victim_order.lines.ids) & {record['id'] for record in res['pos.order.line']})
        else:
            # Rejected public requests must raise instead of returning order/payment data.
            with self.assertRaises(JsonRpcException) as rejected:
                self.make_jsonrpc_request(route, params)
            self.assertEqual(str(rejected.exception), error)
        self.env.invalidate_all()
        self.assertEqual([records.read(fields) for records, fields in records_to_check], before)
        if error and order['uuid'] != self.victim_order.uuid:
            self.assertFalse(self.env['pos.order'].search([('uuid', '=', order['uuid'])]))
        return res

    def test_public_relation_mapping_unsupported_models(self):
        self._setup_relation_orders()
        # Unsupported models are discarded; the legitimate order still syncs.
        for model_name in ('pos.payment', 'pos.config', 'pos.order'):
            with self.subTest(ignored_model=model_name):
                payload = deepcopy(self.order_payload)
                payload['uuid'] = str(uuid4())
                payload['lines'][0][2]['uuid'] = str(uuid4())
                ignored_mappings = {
                    'pos.payment': {self.payment.uuid: {'pos_order_id': payload['uuid']}},
                    'pos.config': {self.other_config.uuid: {'trusted_config_ids': [self.pos_config.uuid]}},
                    'pos.order': {payload['uuid']: {'payment_ids': [self.payment.uuid]}},
                }
                payload['relations_uuid_mapping'] = {model_name: ignored_mappings[model_name]}
                self._post(payload, error='werkzeug.exceptions.BadRequest')

    @mute_logger('odoo.http')
    def test_public_relation_mapping_validation(self):
        self._setup_relation_orders()
        self.assertEqual(self.other_config.payment_method_ids, self.bank_payment_method)
        for foreign_shop in (False, True):
            if foreign_shop:
                self.other_config.with_user(self.pos_user).open_ui()
                self.victim_order, _ = self.create_backend_pos_order({
                    'pos_config': self.other_config,
                    'line_data': [{'product_id': self.cola.id, 'qty': 1}],
                })
                self.payment = self.env['pos.payment'].create({
                    'pos_order_id': self.victim_order.id,
                    'payment_method_id': self.bank_payment_method.id,
                    'amount': 7,
                })

            # Reject foreign UUIDs, forbidden fields, and malformed UUID mappings.``
            order = deepcopy(self.order_payload)
            order['lines'][0][2]['product_id'] = self.combo_product.id
            local_line_uuid = order['lines'][0][2]['uuid']
            mappings = [
                {'pos.order.line': {self.victim_order.lines.uuid: {'order_id': order['uuid']}}},  # Forbidden ownership field.
                {'pos.order.line': {self.victim_order.lines.uuid: {'combo_parent_id': local_line_uuid}}},  # Foreign child owner.
                {'pos.order.line': {local_line_uuid: {'combo_parent_id': self.victim_order.lines.uuid}}},  # Foreign parent target.
                {'pos.order.line': {self.victim_order.lines.uuid: {'combo_line_ids': [local_line_uuid]}}},  # Foreign parent owner.
                {'pos.order.line': {local_line_uuid: {'combo_line_ids': [self.victim_order.lines.uuid]}}},  # Foreign child target.
                None, [], False, 0, 'uuid', {'pos.order.line': []},  # Invalid mapping structure/type.
                {'pos.order.line': {local_line_uuid: []}},  # Relation fields must be a dictionary.
                {'pos.order.line': {local_line_uuid: {'combo_parent_id': 123}}},  # Target must be a UUID string.
                {'pos.order.line': {local_line_uuid: {'combo_line_ids': 'uuid'}}},  # Targets must be a list.
                {'pos.order.line': {local_line_uuid: {'combo_line_ids': [False]}}},  # List entries must be UUID strings.
                {'pos.order.line': {local_line_uuid: {'course_id': str(uuid4())}}},  # Field is not allow-listed.
            ]
            for mapping in mappings:
                with self.subTest(foreign_shop=foreign_shop, mapping=mapping):
                    order['relations_uuid_mapping'] = mapping
                    self._post(order, error='werkzeug.exceptions.BadRequest')

            # Reject foreign IDs and malformed direct combo values.
            order['relations_uuid_mapping'] = {}
            for values in (
                {'combo_parent_id': self.victim_order.lines.id},
                {'combo_line_ids': self.victim_order.lines.ids},
                {'combo_parent_id': True},
                {'combo_line_ids': [[Command.LINK, self.victim_order.lines.id]]},
            ):
                with self.subTest(foreign_shop=foreign_shop, direct_relation=values):
                    payload = deepcopy(order)
                    payload['lines'][0][2].update(values)
                    self._post(payload, error='werkzeug.exceptions.BadRequest')

            # CREATE cannot claim a foreign UUID.
            claimed_line = deepcopy(self.order_payload['lines'][0])
            claimed_line[2]['uuid'] = self.victim_order.lines.uuid
            payload = deepcopy(order)
            payload['lines'].append(claimed_line)
            payload['relations_uuid_mapping'] = {'pos.order.line': {claimed_line[2]['uuid']: {'combo_parent_id': local_line_uuid}}}
            self._post(payload, error='werkzeug.exceptions.BadRequest')

            # UUIDs from updates dropped by the sanitizer are not valid endpoints either.
            dropped_update_uuid = str(uuid4())
            payload = deepcopy(order)
            payload['lines'].append([
                Command.UPDATE,
                self.victim_order.lines.id,
                {**deepcopy(self.order_payload['lines'][0][2]), 'uuid': dropped_update_uuid},
            ])
            payload['relations_uuid_mapping'] = {'pos.order.line': {dropped_update_uuid: {'combo_parent_id': local_line_uuid}}}
            self._post(payload, error='werkzeug.exceptions.BadRequest')

    @mute_logger('odoo.http')
    def test_existing_order_authorization(self):
        self._setup_relation_orders()
        payload = deepcopy(self.order_payload)
        payload.update(uuid=self.victim_order.uuid, lines=[])
        self._post({**payload, 'id': self.victim_order.id, 'access_token': 'wrong-token'}, error='werkzeug.exceptions.Unauthorized')

        # A newer table order must not authorize syncing a different order's UUID.
        table_order, _ = self.create_backend_pos_order({'order_data': {'table_id': self.pos_table_1.id}})
        table_order._ensure_access_token()
        self._post({**payload, 'table_id': self.pos_table_1.id, 'access_token': table_order.access_token}, error='werkzeug.exceptions.Unauthorized')

        # Different config's session.
        payload.update(id=self.victim_order.id, access_token=self.victim_order.access_token)
        self.other_config.with_user(self.pos_user).open_ui()
        other_session = self.other_config.current_session_id
        original_session = self.victim_order.session_id
        self.victim_order.session_id = other_session
        self._post(payload, error='werkzeug.exceptions.Unauthorized')

        # Same config, but a different session.
        other_session.write({'config_id': self.pos_config.id, 'state': 'closed'})
        self.assertNotEqual(self.victim_order.session_id, self.pos_config.current_session_id)
        self._post(payload, error='werkzeug.exceptions.Unauthorized')

        self.victim_order.session_id = original_session
        for state in ('cancel', 'paid', 'done'):
            self.victim_order.state = state
            self._post(payload, error='werkzeug.exceptions.Unauthorized')
