# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestPushToken(common.TransactionCase):

    def test_push_token_unique(self):
        """ Ensure the 'push_token' field is unique.
        When trying to insert an identical push_token, the existing one has to be unlinked first. """

        common_push_token = 'ABC123'

        visitor_1 = self.env['website.visitor'].create({'access_token': 'f9d2b3e247685b628b8e96f5788cf40a'})
        push_token_1 = visitor_1._register_push_subscription(common_push_token)

        self.assertEqual(visitor_1.push_subscription_ids[0], push_token_1)
        self.assertTrue(visitor_1.has_push_notifications)

        visitor_2 = self.env['website.visitor'].create({'access_token': 'f9d28377d61080c17076c35d9a1bccb5'})
        push_token_2 = visitor_2._register_push_subscription(common_push_token)

        self.assertFalse(bool(visitor_1.push_subscription_ids))
        self.assertFalse(visitor_1.has_push_notifications)
        self.assertEqual(visitor_2.push_subscription_ids[0], push_token_2)
        self.assertTrue(visitor_2.has_push_notifications)

    def test_sync_has_push_notification(self):
        visitor_1 = self.env['website.visitor'].create({'access_token': 'f9d20bd006c3bf46b875451defb5991d'})
        push_token_1 = visitor_1._register_push_subscription('ABC123')

        self.assertTrue(visitor_1.has_push_notifications)

        push_token_2 = visitor_1._register_push_subscription('ABC456')
        self.assertTrue(visitor_1.has_push_notifications)

        push_token_1.unlink()
        self.assertTrue(visitor_1.has_push_notifications)

        push_token_2.unlink()
        # when removing the last push notification, the flag has to be set to False
        self.assertFalse(visitor_1.has_push_notifications)
