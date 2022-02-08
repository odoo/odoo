# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.tests import HttpCase

@odoo.tests.tagged('-at_install', 'post_install')
class TestMailGuestPages(HttpCase):
    def test_mail_channel_as_guest(self):
        """Checks that the invite page redirects to the channel and that all
        modules load correctly on the welcome and channel page"""
        channel = self.env['mail.channel'].create({
            'name': 'Test channel',
        })
        self.start_tour(f"/chat/{channel.id}/{channel.uuid}", "mail/static/tests/tours/mail_channel_as_guest_tour.js")
