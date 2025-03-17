# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo.addons.mail.tests.common import MailCase
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestMail(MailCase):

    def test_website_publish_notification(self):
        """ Test that the published/unpublished notifications are sent when publishing/unpublishing an event"""
        published_subtype = self.env.ref('website_event.mt_event_published')
        unpublished_subtype = self.env.ref('website_event.mt_event_unpublished')
        event = self.env['event.event'].create({
            'name': 'Event',
            'date_begin': datetime.today() - timedelta(days=1),
            'date_end': datetime.today() + timedelta(days=1),
        })
        self.flush_tracking()

        follower = self.env.ref('base.user_admin').partner_id
        event.message_subscribe(partner_ids=follower.ids, subtype_ids=[published_subtype.id, unpublished_subtype.id])

        event.website_published = True
        self.flush_tracking()

        event.website_published = False
        self.flush_tracking()

        unpublished_message, published_message, creation_message = event.message_ids

        self.assertEqual(unpublished_message.subtype_id, unpublished_subtype)
        self.assertEqual(published_message.subtype_id, published_subtype)
        self.assertEqual(creation_message.subtype_id, self.env.ref('mail.mt_note'))
