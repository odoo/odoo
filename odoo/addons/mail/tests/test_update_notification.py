# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestUpdateNotification(TransactionCase):
    def test_user_count(self):
        ping_msg = self.env['publisher_warranty.contract'].with_context(active_test=False)._get_message()
        user_count = self.env['res.users'].search_count([('active', '=', True)])
        self.assertEqual(ping_msg.get('nbr_users'), user_count, 'Update Notification: Users count is badly computed in ping message')
        share_user_count = self.env['res.users'].search_count([('active', '=', True), ('share', '=', True)])
        self.assertEqual(ping_msg.get('nbr_share_users'), share_user_count, 'Update Notification: Portal Users count is badly computed in ping message')
