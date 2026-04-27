# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.pos_restaurant.tests import test_frontend
from unittest.mock import patch
import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
class TestUi(test_frontend.TestFrontendCommon):
    def test_01_preparation_display_resto(self):
        self.env['pos_preparation_display.display'].create({
            'name': 'Preparation Display (Food only)',
            'pos_config_ids': [(4, self.pos_config.id)],
            'category_ids': [(0, 0, {
                'name': 'Food',
            })],
        })

        self.env['pos_preparation_display.display'].create({
            'name': 'Preparation Display',
            'pos_config_ids': [(4, self.pos_config.id)],
        })

        # open a session, the /pos/ui controller will redirect to it
        self.pos_config.printer_ids.unlink()
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('PreparationDisplayTourResto')

        # Order 1 should have 2 preparation orderlines (Coca-Cola and Water)
        order1 = self.env['pos.order'].search([('pos_reference', 'ilike', '%-0001')], limit=1)
        pdis_order1 = self.env['pos_preparation_display.order'].search([('pos_order_id', '=', order1.id)], limit=1)
        self.assertEqual(len(pdis_order1.preparation_display_order_line_ids), 2, "Should have 2 preparation orderlines")

        # Order 2 should have 1 preparation orderline (Coca-Cola)
        order2 = self.env['pos.order'].search([('pos_reference', 'ilike', '%-0002')], limit=1)
        pdis_order2 = self.env['pos_preparation_display.order'].search([('pos_order_id', '=', order2.id)], limit=1)
        self.assertEqual(len(pdis_order2.preparation_display_order_line_ids), 1, "Should have 1 preparation orderline")
        self.assertEqual(pdis_order2.preparation_display_order_line_ids.product_quantity, 1, "Should have 1 quantity of Coca-Cola")

        # Order 3 should have 3 preparation orderlines (Coca-Cola, Water and Minute Maid)
        # with one cancelled Minute Maid
        order3 = self.env['pos.order'].search([('pos_reference', 'ilike', '%-0003')], limit=1)
        pdis_order3 = self.env['pos_preparation_display.order'].search([('pos_order_id', '=', order3.id)], limit=1)
        cancelled_orderline = pdis_order3.preparation_display_order_line_ids.filtered(lambda x: x.product_id.name == 'Minute Maid')
        self.assertEqual(cancelled_orderline.product_cancelled, 1, "Should have 1 cancelled Minute Maid orderline")
        self.assertEqual(cancelled_orderline.product_id.name, 'Minute Maid', "Cancelled orderline should be Minute Maid")

    def test_02_preparation_display_resto(self):
        self.env['pos_preparation_display.display'].create({
            'name': 'Preparation Display (Food only)',
            'pos_config_ids': [(4, self.pos_config.id)],
            'category_ids': [(0, 0, {
                'name': 'Food',
            })],
        })

        self.env['pos_preparation_display.display'].create({
            'name': 'Preparation Display',
            'pos_config_ids': [(4, self.pos_config.id)],
        })

        # open a session, the /pos/ui controller will redirect to it
        self.pos_config.printer_ids.unlink()
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('PreparationDisplayTourResto2')

        # Order 1 should have 1 preparation orderlines (Coca-Cola) with quantity 2
        order1 = self.env['pos.order'].search([('pos_reference', 'ilike', '%-0001')], limit=1)
        prep_line = self.env['pos_preparation_display.orderline'].search([
            ('preparation_display_order_id.pos_order_id', '=', order1.id),
        ])
        self.assertEqual(len(prep_line), 2)
        self.assertEqual(sum(prep_line.mapped('product_quantity')), 2)

    def test_preparation_display_with_internal_note(self):
        self.env['pos_preparation_display.display'].create({
            'name': 'Preparation Display',
            'pos_config_ids': [(4, self.pos_config.id)],
        })
        self.pos_config.printer_ids.unlink()
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('PreparationDisplayTourInternalNotes')
        # Order 1 should have 2 preparation orderlines (Coca-Cola and Water)
        order1 = self.env['pos.order'].search([('pos_reference', 'ilike', '%-0001')], limit=1)
        pdis_order1 = self.env['pos_preparation_display.order'].search([('pos_order_id', '=', order1.id)])
        self.assertEqual(len(pdis_order1.preparation_display_order_line_ids), 2, "Should have 2 preparation orderlines")
        self.assertEqual(pdis_order1.preparation_display_order_line_ids[1].product_quantity, 1)
        self.assertEqual(pdis_order1.preparation_display_order_line_ids[1].internal_note, "")
        self.assertEqual(pdis_order1.preparation_display_order_line_ids[0].product_quantity, 1)
        self.assertEqual(pdis_order1.preparation_display_order_line_ids[0].internal_note, "Test Internal Notes")

    def test_03_preparation_display_skip_change(self):
        self.env['pos_preparation_display.display'].create({
            'name': 'Preparation Display',
            'pos_config_ids': [(4, self.pos_config.id)],
        })
        self.pos_config.printer_ids.unlink()
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('PreparationDisplayTourSkipChange')
        order1 = self.env['pos.order'].search([('pos_reference', 'ilike', '%-0001')], limit=1)
        pdis_order1 = self.env['pos_preparation_display.order'].search([('pos_order_id', '=', order1.id)])
        # We only have 3 lines because one of the 4 lines in the order has the skip change option
        self.assertEqual(len(pdis_order1.preparation_display_order_line_ids), 3, "Should have 3 preparation orderlines")

    def test_cancel_order_notifies_display(self):
        category = self.env['pos.category'].create({'name': 'Food'})
        self.env['product.product'].create({
            'name': 'Test Food',
            'list_price': 10,
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': category,
        })

        pdis = self.env['pos_preparation_display.display'].create({
            'name': 'Preparation Display (Food only)',
            'pos_config_ids': [(4, self.pos_config.id)],
            'category_ids': category,
        })

        notifications = []

        def _send_load_orders_message(self, sound):
            notifications.append(self.id)

        # open a session, the /pos/ui controller will redirect to it
        with patch('odoo.addons.pos_preparation_display.models.preparation_display.PosPreparationDisplay._send_load_orders_message', new=_send_load_orders_message):
            self.pos_config.printer_ids.unlink()
            self.pos_config.with_user(self.pos_user).open_ui()
            self.start_pos_tour('PreparationDisplayCancelOrderTour')

        # Should receive 2 notifications, 1 placing the order, 1 cancelling it
        self.assertEqual(notifications.count(pdis.id), 2)

    def test_payment_does_not_cancel_display_orders(self):
        self.env['pos_preparation_display.display'].create({
            'name': 'Preparation Display (Food only)',
            'pos_config_ids': [(4, self.pos_config.id)],
        })
        self.pos_config.printer_ids.unlink()
        self.pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PreparationDisplayPaymentNotCancelDisplayTour', login="pos_user")
        pos_order = self.env['pos.order'].search([], limit=1)
        pdis_order = self.env['pos_preparation_display.order'].search(
            [('pos_order_id', '=', pos_order.id)]
        )
        pdis_lines = pdis_order.preparation_display_order_line_ids
        self.assertEqual(len(pdis_lines), 2)
        self.assertEqual(pdis_lines[0].product_quantity, 2.0)
        self.assertEqual(pdis_lines[0].product_cancelled, 0.0)
        self.assertEqual(pdis_lines[1].product_quantity, 2.0)
        self.assertEqual(pdis_lines[1].product_cancelled, 1.0)

    def test_update_internal_note_of_order(self):
        category = self.env['pos.category'].create({'name': 'Test-cat'})
        product_1, product_2 = self.env['product.product'].create([{
            'name': 'Test Food',
            'list_price': 10,
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': category,
        }, {
            'name': 'Demo Food',
            'list_price': 10,
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': category,
        }])

        self.env['pos_preparation_display.display'].create({
            'name': 'Preparation Display (Food only)',
            'pos_config_ids': [(4, self.pos_config.id)],
            'category_ids': category,
        })

        self.pos_config.with_user(self.pos_admin).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.pos_config.id, 'test_update_internal_note_of_order', login='pos_admin')

        pos_order = self.env['pos.order'].search([('session_id', 'in', self.pos_config.session_ids.ids)], limit=1)
        order_lines = self.env['pos_preparation_display.order'].search([
            ('pos_order_id', '=', pos_order.id),
            ('pos_config_id', '=', self.pos_config.id)
        ]).preparation_display_order_line_ids

        self.assertEqual(len(order_lines), 2)
        self.assertEqual(pos_order.state, 'paid')
        self.assertEqual(pos_order.amount_paid, product_2.list_price)

        self.assertEqual(order_lines[0]['product_id'].id, product_2.id)
        self.assertEqual(order_lines[0]['product_quantity'], 1)
        self.assertEqual(order_lines[0]['product_cancelled'], 0)

        self.assertEqual(order_lines[1]['product_id'].id, product_1.id)
        self.assertEqual(order_lines[1]['internal_note'], '')
        self.assertEqual(order_lines[1]['product_quantity'], 1)
        self.assertEqual(order_lines[1]['product_cancelled'], 1)
