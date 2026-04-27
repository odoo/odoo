# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo import Command

@odoo.tests.tagged('post_install', '-at_install')
class TestUi(TestPointOfSaleHttpCommon):

    def test_01_pos_iot_payment_terminal(self):
        env = self.env

        self.env['ir.config_parameter'].sudo().set_param('pos_iot.ingenico_payment_terminal', True)

        # Create IoT Box
        iotbox_id = env['iot.box'].sudo().create({
            'name': 'iotbox-test',
            'identifier': '01:01:01:01:01:01',
            'ip': '1.1.1.1',
        })

        # Create IoT device
        payment_terminal_device = env['iot.device'].sudo().create({
            'iot_id': iotbox_id.id,
            'name': 'Payment terminal',
            'identifier': 'test_payment_terminal',
            'type': 'payment',
            'connection': 'network',
        })

        cash_journal = self.env['account.journal'].create({
            'name': 'Cash',
            'type': 'cash',
            'company_id': self.company_data['company'].id,
            'code': 'AAA',
            'sequence': 10,
        })

        self.env['product.product'].create({
            'name': 'Test Product',
            'available_in_pos': True,
            'list_price': 10,
            'taxes_id': False,
        })

        # Select IoT Box, tick Payment terminal and set payment method in pos config
        self.main_pos_config.write({
            'payment_method_ids': [
                Command.clear(),
                Command.create({
                    'name': 'Terminal',
                    'use_payment_terminal': 'ingenico',
                    'iot_device_id': payment_terminal_device.id,
                    'journal_id': self.bank_journal.id,
                    'sequence': 0
                }),
                Command.create({
                    'name': 'Cash',
                    'journal_id': cash_journal.id,
                    'sequence': 1
                }),
            ],
        })

        self.start_tour("/odoo", 'payment_terminals_tour', login="pos_user")

        orders = env['pos.order'].search([])
        self.assertEqual(len(orders.ids), 1, "There should be 1 orders.")
        # First order at index 1 because orders are sorted in descending order.
        self.assertEqual(orders[0].state, 'paid', "The first order has payment of " + str(orders[0].amount_paid) + " and total of " + str(orders[0].amount_total))

    def test_02_pos_iot_scale(self):
        env = self.env

        # Create IoT Box
        iotbox_id = env['iot.box'].sudo().create({
            'name': 'iotbox-test',
            'identifier': '01:01:01:01:01:01',
            'ip': '1.1.1.1',
        })

        # Create IoT device
        iot_device_id = env['iot.device'].sudo().create({
            'iot_id': iotbox_id.id,
            'name': 'Scale',
            'identifier': 'test_scale',
            'type': 'scale',
            'connection': 'direct',
        })

        # Select IoT Box, tick electronic scale
        self.main_pos_config.write({
            'iface_scale_id': iot_device_id.id,
        })

        self.start_tour("/odoo", 'pos_iot_scale_tour', login="pos_user")
