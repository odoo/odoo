# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-

from odoo import http
from odoo.tests import tagged
from odoo.tests.common import HttpCase, TransactionCase


@tagged('post_install', '-at_install')
class TestWebsiteTour(HttpCase, TransactionCase):

    def setUp(self):
        super().setUp()
        self.env['res.config.settings'].write({
            'module_website_event_track_live': True,
        })

    def test_visitor_email_reminder_tour(self):
        self.start_tour("/event/design-fair-los-angeles-1/agenda", "visitor_email_reminder_tour")
        session = http.root.session_store.get(self.session.sid)
        last_email = self.env['mail.mail'].search([], limit=1, order="id DESC")
        self.assertEqual(session.get('event_track_email_reminder'), last_email.email_to)

    def test_logged_user_email_reminder_tour(self):
        user = self.env['res.users'].search([('login', '=', 'admin')])
        self.start_tour("/event/design-fair-los-angeles-1/agenda", "logged_user_email_reminder_tour",
                        login=user.login)
        last_email = self.env['mail.mail'].search([], limit=1, order="id DESC")
        self.assertEqual(user.email, last_email.email_to)
