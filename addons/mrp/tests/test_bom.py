# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mrp.tests.common import TestMrpCommon


class TestBoM(TestMrpCommon):

    def test_basic(self):
        # make the production order
        production = self.production_1

        # compute production order data
        production.action_compute()

        # confirm production
        production.signal_workflow('button_confirm')
        self.assertEqual(production.state, 'confirmed')

        # reserve product
        production.force_production()

        # produce product
        produce_wizard = self.env['mrp.product.produce'].with_context({
            'active_id': production.id,
            'active_ids': [production.id],
        }).create({
            'mode': 'consume_produce',
            'product_qty': 1.0,
        })
        produce_wizard.on_change_qty()
        produce_wizard.do_produce()

        # check production
        self.assertEqual(production.state, 'done')
