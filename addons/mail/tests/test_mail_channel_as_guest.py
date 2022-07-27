# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.tests import HttpCase


@odoo.tests.tagged('-at_install', 'post_install')
class TestMailPublicPage(HttpCase):
    """Checks that the invite page redirects to the channel and that all
    modules load correctly on the welcome and channel page when authenticated as various users"""

    def setUp(self):
        super().setUp()
        self.channel = self.env['mail.channel'].create({
            'name': 'Test channel',
            'public': 'public',
        })
        self.route = f"/chat/{self.channel.id}/{self.channel.uuid}"
        self.tour = "mail/static/tests/tours/discuss_public_tour.js"

    def _open_channel_page_as_user(self, login):
        self.start_tour(self.route, self.tour, login=login)
        # Second run of the tour as the first call has side effects, like creating user settings or adding members to
        # the channel, so we need to run it again to test different parts of the code.
        self.start_tour(self.route, self.tour, login=login)

    def test_mail_channel_public_page_as_admin(self):
        self._open_channel_page_as_user('admin')

    def test_mail_channel_public_page_as_guest(self):
        self.start_tour(self.route, "mail/static/tests/tours/mail_channel_as_guest_tour.js")
        guest = self.env['mail.guest'].search([('channel_ids', 'in', self.channel.id)], limit=1, order='id desc')
        self.start_tour(self.route, self.tour, cookies={guest._cookie_name: f"{guest.id}{guest._cookie_separator}{guest.access_token}"})

    def test_mail_channel_public_page_as_internal(self):
        self._open_channel_page_as_user('demo')

    def test_mail_channel_public_page_as_portal(self):
        self._open_channel_page_as_user('portal')
