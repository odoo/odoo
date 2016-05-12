# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mrp.tests.common import TestMrpCommon


class TestMrpOrder(TestMrpCommon):

    def test_access_rights_manager(self):
        production = self.production_1.sudo(self.user_mrp_manager)
        production.action_compute()
        production.signal_workflow('button_confirm')
        production.action_cancel()
        self.assertEqual(production.state, 'cancel')
        production.unlink()

    def test_access_rights_user(self):
        production = self.production_1.sudo(self.user_mrp_user)
        production.action_compute()
        production.signal_workflow('button_confirm')
        production.action_cancel()
        self.assertEqual(production.state, 'cancel')
        production.unlink()

    def test_flow(self):
        production = self.production_1.sudo(self.user_mrp_user)
        production.action_compute()
