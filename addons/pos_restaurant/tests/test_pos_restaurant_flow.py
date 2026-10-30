# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.addons.pos_restaurant.tests.test_frontend import TestFrontendCommon

@tagged('post_install', '-at_install')
class TestPosRestaurantFlow(TestFrontendCommon):

    def test_table_parent_circular_relation_is_rejected(self):
        table_a, table_b = self.env['restaurant.table'].create([
            {
                'table_number': 91,
                'parent_id': False,
                'parent_side': False,
                'floor_id': self.main_floor.id,
                'seats': 4,
                'active': True,
                'floor_plan_layout': {
                    'width': 10,
                    'height': 10,
                    'left': 10,
                    'top': 10,
                    'shape': "square",
                    'color': "rgb(53,211,116)",
                },
            },
            {
                'table_number': 92,
                'parent_id': False,
                'parent_side': False,
                'floor_id': self.main_floor.id,
                'seats': 4,
                'active': True,
                'floor_plan_layout': {
                    'width': 10,
                    'height': 10,
                    'left': 30,
                    'top': 30,
                    'shape': "square",
                    'color': "rgb(53,211,116)",
                },
            },
        ])

        table_b.set_parent_id(table_a.id, "top", self.pos_config.id)
        table_b.flush_recordset(['parent_id'])
        self.assertEqual(table_b.parent_id, table_a, "Table B should be attached to table A")

        table_a.set_parent_id(table_b.id, "bottom", self.pos_config.id)
        table_a.flush_recordset(['parent_id'])
        table_b.flush_recordset(['parent_id'])

        self.assertFalse(table_a.parent_id, "Table A should not get table B as parent because this creates a loop")
        self.assertEqual(table_b.parent_id, table_a, "Table B should keep its valid parent")
        self.assertFalse((table_a + table_b)._has_cycle('parent_id'), "Table hierarchy should remain acyclic")

    def test_offline_order_merged_into_table_order_then_paid(self):
        """An order created offline on a table is merged into the open order created meanwhile
        by another device on the same table. Paying only the amount known by the offline device
        keeps the payment but leaves the order draft since the other device's line is not paid."""
        self.pos_config.open_ui()
        session = self.pos_config.current_session_id
        cash_payment_method = session.payment_method_ids.filtered('is_cash_count')[:1]
        price = self.coca_cola_test.lst_price

        def order_data(uuid, state, line_uuids, payments):
            return {
                'amount_paid': sum(payments),
                'amount_return': 0,
                'amount_tax': 0,
                'amount_total': price,
                'date_order': fields.Datetime.to_string(fields.Datetime.now()),
                'fiscal_position_id': False,
                'pricelist_id': session.config_id.pricelist_id.id,
                'name': f'Order {uuid}',
                'last_order_preparation_change': '{}',
                'lines': [(0, 0, {
                    'price_unit': price,
                    'product_id': self.coca_cola_test.id,
                    'price_subtotal': price,
                    'price_subtotal_incl': price,
                    'qty': 1,
                    'tax_ids': [],
                    'uuid': line_uuid,
                }) for line_uuid in line_uuids],
                'partner_id': False,
                'session_id': session.id,
                'payment_ids': [(0, 0, {
                    'amount': amount,
                    'name': fields.Datetime.to_string(fields.Datetime.now()),
                    'payment_method_id': cash_payment_method.id,
                    'uuid': f'{uuid}-payment',
                }) for amount in payments],
                'uuid': uuid,
                'user_id': self.env.uid,
                'to_invoice': False,
                'state': state,
                'table_id': self.main_floor_table_5.id,
            }

        # Online device creates an order on the table
        self.env['pos.order'].sync_from_ui([order_data('online-order', 'draft', ['online-line'], [])])
        # Offline device created its own order on the same table, it is synced afterwards
        self.env['pos.order'].sync_from_ui([order_data('offline-order', 'draft', ['offline-line'], [])])

        table_order = self.env['pos.order'].search([('table_id', '=', self.main_floor_table_5.id)])
        self.assertEqual(len(table_order), 1, "The offline order should be merged in the open order of the table")
        self.assertEqual(table_order.uuid, 'online-order')
        self.assertEqual(len(table_order.lines), 2)

        # The offline device pays the merged order with the amount it knew
        self.env['pos.order'].sync_from_ui([order_data('online-order', 'paid', [], [price])])
        self.assertEqual(table_order.state, 'draft', "The line of the online device is not paid")
        self.assertEqual(table_order.payment_ids.mapped('amount'), [price])

    def test_floor_plans_archive(self):
        floors = self.main_floor + self.second_floor
        floors.action_archive()
        # All floors should be archived successfully
        self.assertTrue(all(floor.active is False for floor in floors), "All floors should be archived")

    def test_archive_product_with_open_restaurant_order(self):
        """
        1. Open a POS session (restaurant).
        2. Place a draft order on a table with.
        3. Check that no paid/validated order exists for this product in the backend.
        4. Trying to archive the product must raise a UserError (session is still open).
        """
        self.pos_config.open_ui()
        session = self.pos_config.current_session_id

        product_variant = self.coca_cola_test
        product = product_variant.product_tmpl_id

        order_data = {
            'amount_paid': 0,
            'amount_return': 0,
            'amount_tax': 0,
            'amount_total': product_variant.lst_price,
            'date_order': '2024-01-01 10:00:00',
            'fiscal_position_id': False,
            'pricelist_id': session.config_id.pricelist_id.id,
            'name': 'Order 00001-001-0001',
            'last_order_preparation_change': '{}',
            'lines': [(0, 0, {
                'id': 1,
                'price_unit': product_variant.lst_price,
                'product_id': product_variant.id,
                'price_subtotal': product_variant.lst_price,
                'price_subtotal_incl': product_variant.lst_price,
                'qty': 1,
                'tax_ids': [],
            })],
            'partner_id': False,
            'session_id': session.id,
            'payment_ids': [],
            'uuid': 'test-archive-0001',
            'user_id': self.env.uid,
            'to_invoice': False,
            'state': 'draft',
            'table_id': self.main_floor_table_5.id,
        }
        self.env['pos.order'].sync_from_ui([order_data])

        draft_order = self.env['pos.order'].search([
            ('session_id', '=', session.id),
            ('table_id', '=', self.main_floor_table_5.id),
        ])
        self.assertTrue(draft_order, "A draft order should exist for the table")
        self.assertEqual(draft_order.state, 'draft', "The order should be in draft state, not yet paid")

        with self.assertRaises(UserError):
            product.action_archive()
