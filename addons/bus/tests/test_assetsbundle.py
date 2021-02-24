# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo.tests
from odoo.osv import expression


@odoo.tests.tagged('post_install', '-at_install', 'assets_bundle')
class BusWebTests(odoo.tests.HttpCase):

    def test_bundle_sends_bus(self):
        """
        Tests two things:
        - Messages are posted to the bus when assets change
          i.e. their hash has been recomputed and differ from the attachment's
        - The interface deals with those bus messages by displaying one notification
        """
        bundle_names = ['web.assets_common', 'web.assets_backend']

        domain = []
        for bundle in bundle_names:
            domain = expression.OR([
                domain,
                [('name', 'ilike', bundle + '%')]
            ])
        # start from a clean slate
        self.env['ir.attachment'].search(domain).unlink()
        self.env.registry._clear_cache()

        sent_notifications = []

        def patched__send_notifications(self, channel, message):
            """ Control API and number of messages posted to the bus linked to
            bundle_changed events """
            if channel[1] == 'bundle_changed':
                sent_notifications.append((channel, message))

        self.patch(type(self.env['bus.bus']), '_send_notifications', patched__send_notifications)

        self.start_tour('/web', "bundle_changed_notification", login='admin', timeout=180)

        # One sent_notifications for each asset bundle and for each CSS / JS
        self.assertEqual(len(sent_notifications), 4)
        for notifications in sent_notifications:
            self.assertEqual(len(notifications), 1)
            notification = notifications[0]
            self.assertTrue(notification['type'], 'base.bundle_changed')
            self.assertEqual(notification['target'], self.env['res.partner'])
            self.assertTrue(notification['payload']['name'] in bundle_names)
            self.assertTrue(isinstance(notification['payload']['version'], str))
