# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.pos_restaurant.tests.test_frontend import TestFrontendCommon
from odoo import Command

@odoo.tests.tagged('post_install', '-at_install')
class TestTransferTable(TestFrontendCommon):
    def setUp(self):
        super().setUp()
        self.env['pos.printer'].create({
            'name': 'Printer',
            'printer_type': 'epson_epos',
            'epson_printer_ip': '0.0.0.0',
            'product_categories_ids': [Command.set(self.env['pos.category'].search([]).ids)],
        })

        self.main_pos_config.write({
            'is_order_printer' : True,
            'printer_ids': [Command.set(self.env['pos.printer'].search([]).ids)],
        })

        self.product_test = self.env['product.product'].create({
            'name': 'Product Test',
            'available_in_pos': True,
            'list_price': 10,
            'pos_categ_ids': [(6, 0, [self.env['pos.category'].search([], limit=1).id])],
            'taxes_id': False,
        })

    def test_transfer_table_last_preparation_change_1(self):
        """This test will check if the last preparation change is correctly transferred when transfering sent product on table with same product sent"""
        #TEST OK
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(f"/pos/ui?config_id={self.main_pos_config.id}", 'TableTransferPreparationChange1', login="pos_user")

    def test_transfer_table_last_preparation_change_2(self):
        """This test will check if the last preparation change is correctly transferred when transfering sent product on table with same product not sent"""
        #TEST OK

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(f"/pos/ui?config_id={self.main_pos_config.id}", 'TableTransferPreparationChange2', login="pos_user")

    def test_transfer_table_last_preparation_change_3(self):
        """This test will check if the last preparation change is correctly transferred when transfering sent product on table without the same product"""
        #TEST OK

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(f"/pos/ui?config_id={self.main_pos_config.id}", 'TableTransferPreparationChange3', login="pos_user")

    def test_transfer_table_last_preparation_change_4(self):
        """This test will check if the last preparation change is correctly transferred when transfering not sent product on table with same product not sent"""
        #TEST NOK
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(f"/pos/ui?config_id={self.main_pos_config.id}", 'TableTransferPreparationChange4', login="pos_user")

    def test_transfer_table_last_preparation_change_5(self):
        """This test will check if the last preparation change is correctly transferred when transfering not sent product on table with same product sent"""
        #TEST NOK
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(f"/pos/ui?config_id={self.main_pos_config.id}", 'TableTransferPreparationChange5', login="pos_user")

    def test_transfer_table_last_preparation_change_6(self):
        """This test will check if the last preparation change is correctly transferred when transfering not sent product on table without the same product"""
        #TEST NOK
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(f"/pos/ui?config_id={self.main_pos_config.id}", 'TableTransferPreparationChange6', login="pos_user")
