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
        db_name = self.env.registry.db_name
        bundle_xml_ids = ('web.assets_common', 'web.assets_backend')

        domain = []
        for bundle in bundle_xml_ids:
            domain = expression.OR([
                domain,
                [('name', 'ilike', bundle + '%')]
            ])
        # start from a clean slate
        self.env['ir.attachment'].search(domain).unlink()
        self.env.registry._clear_cache()

        sendones = []
        def patched_sendone(self, channel, message):
            """
            Control API and number of messages posted to the bus
            """
            sendones.append((channel, message))

        self.patch(type(self.env['bus.bus']), 'sendone', patched_sendone)

        self.start_tour('/web', "bundle_changed_notification", login='admin', timeout=180)

        # One sendone for each asset bundle and for each CSS / JS
        self.assertEqual(len(sendones), 4)
        for sent in sendones:
            channel = sent[0]
            message = sent[1]
            self.assertEqual(channel, (db_name, 'bundle_changed'))
            self.assertEqual(len(message), 2)
            self.assertTrue(message[0] in bundle_xml_ids)
            self.assertTrue(isinstance(message[1], str))
