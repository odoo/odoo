# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

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
        event_date_begin = datetime.now()
        self.event = self.env['event.event'].create([{
            'name': 'Test event',
            'date_begin': event_date_begin,
            'date_end': event_date_begin + timedelta(weeks=1),
            'is_published': True
        }])
        self.env['event.track'].create([{
            'name': 'Introduction class',
            'date': event_date_begin + timedelta(hours=1),
            'date_end': event_date_begin + timedelta(hours=2),
            'event_id': self.event.id,
            'is_published': True
        }])
        self.email_reminder_tour_url = f'{self.event.website_url}/agenda'

    def test_visitor_email_reminder_tour(self):
        self.start_tour(self.email_reminder_tour_url, 'visitor_email_reminder_tour')
        session = http.root.session_store.get(self.session.sid)
        last_email = self.env['mail.mail'].search([], limit=1, order="id DESC")
        self.assertEqual(session.get('website_event_track.email_reminder'), last_email.email_to)

    def test_logged_user_email_reminder_tour(self):
        user = self.env['res.users'].search([('login', '=', 'admin')])
        self.start_tour(self.email_reminder_tour_url, "logged_user_email_reminder_tour",
                        login=user.login)
        last_email = self.env['mail.mail'].search([], limit=1, order="id DESC")
        self.assertEqual(user.email, last_email.email_to)
