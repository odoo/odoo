# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.addons.mrp.tests.test_order_demo import TestOrderDemo


class TestCancelOrder(TestOrderDemo):

    def test_00_cancel_order(self):

    # I first confirm order for PC Assemble SC349.
        self.mrp_production_test1.signal_workflow('button_confirm')

    # Now I cancel the production order.
        self.mrp_production_test1.action_cancel()

    # Now I check that the production order is cancelled.
        self.assertEqual(self.mrp_production_test1.state, 'cancel')

    # I remove cancelled production order.
        self.mrp_production_test1.unlink()
