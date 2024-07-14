# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.pos_restaurant.tests.test_frontend import TestFrontend
from odoo import Command
import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
class TestUi(TestFrontend):
    def test_01_preparation_display_resto(self):
        self.env['pos_preparation_display.display'].create({
            'name': 'Preparation Display',
            'pos_config_ids': [(4, self.pos_config.id)],
        })

        # open a session, the /pos/ui controller will redirect to it
        self.pos_config.printer_ids.unlink()
        self.pos_config.with_user(self.user_demo).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.pos_config.id, 'PreparationDisplayTourResto', login="demo")

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

    def test_preparation_display_with_internal_note(self):
        self.env['pos_preparation_display.display'].create({
            'name': 'Preparation Display',
            'pos_config_ids': [(4, self.pos_config.id)],
        })
        self.pos_config.printer_ids.unlink()
        self.pos_config.with_user(self.user_demo).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.pos_config.id, 'PreparationDisplayTourInternalNotes', login="demo")
        # Order 1 should have 2 preparation orderlines (Coca-Cola and Water)
        order1 = self.env['pos.order'].search([('pos_reference', 'ilike', '%-0001')], limit=1)
        pdis_order1 = self.env['pos_preparation_display.order'].search([('pos_order_id', '=', order1.id)])
        self.assertEqual(len(pdis_order1.preparation_display_order_line_ids), 2, "Should have 2 preparation orderlines")
        self.assertEqual(pdis_order1.preparation_display_order_line_ids[0].product_quantity, 1)
        self.assertEqual(pdis_order1.preparation_display_order_line_ids[0].internal_note, "Test Internal Notes")
        self.assertEqual(pdis_order1.preparation_display_order_line_ids[1].product_quantity, 1)
        self.assertEqual(pdis_order1.preparation_display_order_line_ids[1].internal_note, "Test Internal Notes")

    def test_bill_preparation_display(self):
        pos_config = self.env['pos.config'].create({
            'name': 'Restaurant',
            'module_pos_restaurant': True,
            'iface_printbill': True,
        })

        pdis = self.env['pos_preparation_display.display'].create({
            'name': 'Preparation Display',
            'pos_config_ids': [Command.link(pos_config.id)],
        })

        order_count = pdis.order_count

        pos_config.with_user(self.user_demo).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % pos_config.id, 'MakeBillTour', login="demo")

        self.assertEqual(order_count, pdis.order_count)
