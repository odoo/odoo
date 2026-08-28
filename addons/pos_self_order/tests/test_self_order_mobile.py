# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo import http

from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest
from odoo.addons.pos_self_order.controllers.orders import PosSelfOrderController
from unittest.mock import patch
from datetime import datetime, timedelta


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderMobile(SelfOrderCommonTest):
    def test_self_order_mobile(self):
        self.pos_config.write({
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'table',
        })

        floor = self.env["restaurant.floor"].create({
            "name": 'Main Floor',
            "table_ids": [(0, 0, {
                "table_number": 1,
            })],
        })

        # Only set one floor to the pos_config, otherwise it can have two table with the same name
        # which will cause the test to fail
        self.pos_config.write({
            "floor_ids": [(6, 0, [floor.id])],
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route(table_id=floor.table_ids[0].id)

        # Test selection of different presets
        order = self.process_self_order(
            [{'product': self.cola, 'qty': 1, 'price_unit': self.cola.lst_price}],
            preset=self.in_preset,
            table=floor.table_ids[0],
        )
        self.start_tour(self_route, "self_mobile_each_table_takeaway_out")
        orders = self.env['pos.order'].search([], order="id desc", limit=2)
        self.assertEqual(orders[0].preset_id, self.out_preset)
        self.assertEqual(orders[1].preset_id, self.in_preset)

        self.pos_config.write({
            'self_ordering_pay_after': 'meal',
            'self_ordering_service_mode': 'table',
        })

        # Mobile, meal, table
        order = self.process_self_order(
            [{'product': self.cola, 'qty': 1, 'price_unit': self.cola.lst_price}],
            preset=self.in_preset,
            table=floor.table_ids[0],
        )
        html = order.order_receipt_generate_html()
        self.assertTrue("Service at Table" in html)

        self.pos_config.write({
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'counter',
        })

        # Mobile, meal, counter
        order = self.process_self_order(
            [{'product': self.cola, 'qty': 1, 'price_unit': self.cola.lst_price}],
            preset=self.out_preset,
        )
        html = order.order_receipt_generate_html()
        self.assertTrue("Pickup At Counter" in html)

    def test_self_order_mobile_0_price_order(self):
        self.pos_config.write({
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'table',
        })

        floor = self.env["restaurant.floor"].create({
            "name": 'Main Floor',
            "table_ids": [(0, 0, {
                "table_number": 1,
            }), (0, 0, {
                "table_number": 2,
            }), (0, 0, {
                "table_number": 3,
            })],
        })

        # Only set one floor to the pos_config, otherwise it can have two table with the same name
        # which will cause the test to fail
        self.pos_config.write({
            "floor_ids": [(6, 0, [floor.id])],
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")

        # Zero priced order with a note
        order = self.process_self_order(
            [{'product': self.ketchup, 'qty': 1, 'price_unit': self.ketchup.lst_price}],
            general_customer_note='test',
            table=floor.table_ids[0],
        )

        self.assertEqual(order.general_customer_note, "test")

    def test_order_sequence_in_self(self):
        self.pos_config.write({
            'use_presets': False,
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'counter',
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, "test_order_sequence_in_self")

        current_year = str(datetime.now().year)[-2:]
        references = self.env['pos.order'].search([], limit=4, order="id desc").mapped('pos_reference')
        self.assertEqual(references, [f"{current_year}0-{self.pos_config.id}-00000{4 - i}" for i in range(4)])
        self.assertEqual(self.pos_config.order_backend_seq_id.number_next, 5)

    def test_mobile_self_order_preparation_changes(self):
        self.pos_config.write({
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'table',
            'use_presets': False,
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")

        # Create self-order from mobile directly
        table = self.pos_main_floor.table_ids[0]
        order = self.process_self_order(
            [
                {'product': self.cola, 'qty': 1, 'price_unit': self.cola.lst_price},
                {'product': self.fanta, 'qty': 1, 'price_unit': self.fanta.lst_price},
            ],
            table=table,
        )
        self.assertEqual(order.state, 'draft')
        self.assertEqual(len(order.lines), 2)

        # Check self-order in pos-terminal are not prompted for Send-for-Preparation
        expected_table = order.self_ordering_table_id
        self.start_tour('/pos/ui?config_id=%d' % self.pos_config.id, 'test_pos_self_order_preparation_changes', login='pos_user')
        self.assertEqual(order.self_ordering_table_id, expected_table, "self_ordering_table_id should be equal to the original table")

    def test_self_order_table_no_more_sharing(self):
        """
        - MEAL MODE: table is assigned to order via table_id field when scanning QR code
            all phones scanning the same table QR code share the same order
        - EACH MODE: table is assigned to order via floating_order_name field when scanning QR code
            each phone scanning the same table QR code has its own order
        """
        self.pos_config.write({
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'table',
            'use_presets': False,
        })

        floor = self.env["restaurant.floor"].create({
            "name": 'Main Floor',
            "table_ids": [(0, 0, {
                "table_number": 1,
            }), (0, 0, {
                "table_number": 2,
            }), (0, 0, {
                "table_number": 3,
            })],
        })
        self.pos_config.write({
            "floor_ids": [(6, 0, [floor.id])],
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        table = floor.table_ids[0]
        table_identifier = table.identifier
        self_route = self.pos_config._get_self_order_route(table_id=table.id)

        # Just needs to create an order; values do not matter
        self.process_self_order(
            [{'product': self.cola, 'qty': 1, 'price_unit': self.cola.lst_price}],
            floating_order_name=f'Self-Order {table_identifier}',
            table=table,
        )

        last_order = self.process_self_order(
            [
                {'product': self.cola, 'qty': 1, 'price_unit': self.cola.lst_price},
                {'product': self.fanta, 'qty': 1, 'price_unit': self.fanta.lst_price},
            ],
            table=table,
        )
        self.assertEqual(last_order.floating_order_name, f"Self-Order T {table.table_number}")
        self.assertFalse(last_order.table_id)

        self.pos_config.write({
            'self_ordering_pay_after': 'meal',
        })

        self.start_tour(self_route, "test_self_order_table_no_more_sharing-meal_mode")

    def test_delete_mobile_order_from_backend(self):
        self.pos_config.write({
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'counter',
            'use_presets': False,
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, '')
        self_route = self.pos_config._get_self_order_route()

        @http.route('/pos-self-order/test-delete-order-from-backend/', auth='public', type='jsonrpc', website=True)
        def delete_mobile_order_from_backend(self, order_ids):
            self.env['pos.order'].sudo().browse(order_ids).unlink()

        with patch.object(
            PosSelfOrderController,
            'delete_mobile_order_from_backend',
            delete_mobile_order_from_backend,
            create=True,
        ):
            self.start_tour(self_route, 'test_delete_mobile_order_from_backend')

    def test_self_order_pay_warns_on_stale_cart(self):
        self.pos_config.write({
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'meal',
            'self_ordering_service_mode': 'dynamic_qr',
            'use_presets': False,
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, '')

        order = self.env['pos.order'].create({
            'session_id': self.pos_config.current_session_id.id,
            'table_id': self.pos_table_1.id,
            'amount_total': 0.0,
            'amount_tax': 0.0,
            'amount_return': 0.0,
            'amount_paid': 0.0,
        })
        order._ensure_access_token()
        self_route = self.pos_config._get_self_order_route(order=order)

        @http.route('/pos-self-order/test-modify-line-qty-from-backend/', auth='public', type='jsonrpc', website=True)
        def modify_line_qty_from_backend(self, line_id, qty):
            self.env['pos.order.line'].sudo().browse(line_id).write({'qty': qty})

        with patch.object(PosSelfOrderController, 'modify_line_qty_from_backend', modify_line_qty_from_backend, create=True):
            self.start_tour(self_route, 'self_order_mobile_pay_warns_on_stale_cart')

    def test_self_order_snooze_service(self):
        """
        Verify that snoozing the self-order service from the order tracker
        dropdown creates a `pos.snooze` record for the requested duration.
        """

        self.pos_config.write({
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'counter',
            'use_presets': False,
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")

        self.start_tour('/pos/ui?config_id=%d' % self.pos_config.id, 'test_self_order_snooze_service', login='pos_user')

        snoozed_item = self.env['pos.snooze'].search([], limit=1)
        self.assertEqual(snoozed_item.type, "self-ordering")
        self.assertEqual(snoozed_item.end_time - snoozed_item.start_time, timedelta(hours=1))

    def test_pos_self_order_dynamic_qr(self):
        self.browser_size = '1366x768'
        self.pos_config.write({
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'meal',
            'self_ordering_service_mode': 'dynamic_qr',
            'floor_ids': [(6, 0, [self.pos_main_floor.id])],
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")

        # Without a QR-joined order, self-ordering is blocked with a staff-only message.
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, 'self_order_mobile_dynamic_qr_blocked')

        self.start_tour('/pos/ui?config_id=%d' % self.pos_config.id, 'test_pos_self_order_dynamic_qr', login='pos_user')

        order = self.pos_config.current_session_id.order_ids.filtered(lambda o: o.lines)
        self.assertEqual(len(order), 1, "Expected exactly one order with lines")
        self.assertTrue(order.access_token, "Clicking Dynamic QR should have generated an access_token for the order")

        self_route_order = self.pos_config._get_self_order_route(order=order)
        self.assertIn(f"order_identifier={order.access_token}", self_route_order)
        self.start_tour(self_route_order, "self_order_mobile_join_via_qr")

        order.invalidate_recordset()
        self.assertEqual(len(order.lines), 1)
        self.assertEqual(order.lines[0].qty, 2)

    def test_self_order_mobile_not_visible_in_other_config(self):
        """Self-orders from config A should not appear in config B's ticket screen."""
        self.pos_config.write({
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'counter',
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")

        order = self.env['pos.order'].create({
            'session_id': self.pos_config.current_session_id.id,
            'source': 'mobile',
            'amount_total': self.cola.lst_price,
            'amount_tax': 0,
            'amount_paid': 0,
            'amount_return': 0,
            'lines': [(0, 0, {
                'qty': 1,
                'product_id': self.cola.id,
                'price_unit': self.cola.lst_price,
                'price_subtotal': self.cola.lst_price,
                'price_subtotal_incl': self.cola.lst_price,
            })],
        })
        self.assertEqual(order.config_id, self.pos_config)

        other_pos = self.env['pos.config'].create({
            'name': 'OtherPOS',
            'module_pos_restaurant': True,
            'cash_control': False,
        })
        self.start_tour(f"/pos/ui/{other_pos.id}", 'test_self_order_mobile_not_visible_in_other_config', login="pos_admin")

    def test_self_order_availability_toggle(self):
        """Verify that toggling self_order_available is correctly reflected in the data loaded for the self-order interface."""
        self.pos_config.write({
            'self_ordering_mode': 'mobile',
        })
        desk_organizer = self.env['product.template'].search([('name', '=', 'Desk Organizer')], limit=1)
        desk_organizer.write({'self_order_available': False})

        self.pos_config.with_user(self.pos_user).open_ui()

        result = self.env['product.template'].load_product_from_pos(self.pos_config.id, [('id', '=', desk_organizer.id)])
        product_data = result['product.template'][0]
        self.assertEqual(product_data['self_order_available'], desk_organizer.self_order_available)
