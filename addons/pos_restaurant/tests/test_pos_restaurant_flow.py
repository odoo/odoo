# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.addons.pos_restaurant.tests.test_frontend import TestFrontendCommon

@tagged('post_install', '-at_install')
class TestPosRestaurantFlow(TestFrontendCommon):

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
                'pack_lot_ids': [],
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
