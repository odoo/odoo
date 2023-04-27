# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests import HttpCase, tagged
from odoo.tools import mute_logger


@tagged('post_install', '-at_install')
class TestWebsiteEventAccess(HttpCase):
    def setUp(self):
        super(TestWebsiteEventAccess, self).setUp()

        self.events = self.env['event.event'].create([{
            'name': 'Event 0 - Sitemap test',
            'website_published': True,
            'date_begin': datetime.today() - timedelta(days=1),
            'date_end': datetime.today() + timedelta(days=1),
        }, {
            'name': 'Event 1 - Sitemap test',
            'website_published': True,
            'date_begin': datetime.today() - timedelta(days=1),
            'date_end': datetime.today() + timedelta(days=1),
        }, {
            'name': 'Event 2 - Sitemap test',
            'date_begin': datetime.today() - timedelta(days=1),
            'date_end': datetime.today() + timedelta(days=1),
        }])

        self.event_manager = mail_new_test_user(
            self.env, name='Gandalf le blanc', login='event_manager', password='event_manager', email='event.manager@example.com',
            groups='event.group_event_manager,base.group_user'
        )

        self.event_user = mail_new_test_user(
            self.env, name='Frodon Sacquet', login='event_user', password='event_user', email='event.user@example.com',
            groups='event.group_event_user,base.group_user'
        )

        self.portal_user = mail_new_test_user(
            self.env, name='Smeagol', login='user_portal', password='user_portal', email='portal@example.com',
            groups='base.group_portal'
        )

    def test_sitemap(self):
        resp = self.url_open('/sitemap.xml')
        self.assertTrue('/event/event-0' in resp.text, 'Published events must be present in the sitemap')
        self.assertTrue('/event/event-1' in resp.text, 'Published events must be present in the sitemap')
        self.assertFalse('/event/event-2' in resp.text, 'Unpublished events must not be present in the sitemap')

    def test_events_access_1(self):
        """Access to a published event with public user."""
        published_events = self.events.filtered(lambda event: event.website_published)
        resp = self.url_open('/event/%i' % published_events[0].id)
        self.assertEqual(resp.status_code, 200, 'We must have access to published event')

    def test_events_access_2(self):
        """Access to an unpublished event with public user."""
        with mute_logger('odoo.addons.http_routing.models.ir_http'):
            unpublished_events = self.events.filtered(lambda event: not event.website_published)
            resp = self.url_open('/event/%i' % unpublished_events[0].id)
            self.assertEqual(resp.status_code, 403, 'We must not have access to unpublished event')

    def test_events_access_3(self):
        """Access to an published event with admin user."""
        self.authenticate('event_manager', 'event_manager')
        published_events = self.events.filtered(lambda event: event.website_published)
        resp = self.url_open('/event/%i' % published_events[0].id)
        self.assertEqual(resp.status_code, 200, 'Admin must have access to published event.')

    def test_events_access_4(self):
        """Access to an unpublished event with admin user."""
        self.authenticate('event_manager', 'event_manager')
        unpublished_events = self.events.filtered(lambda event: not event.website_published)
        resp = self.url_open('/event/%i' % unpublished_events[0].id)
        self.assertEqual(resp.status_code, 200, 'Admin must have access to unpublished event.')

    def test_events_access_5(self):
        """Access to an published event with event user."""
        self.authenticate('event_user', 'event_user')
        published_events = self.events.filtered(lambda event: event.website_published)
        resp = self.url_open('/event/%i' % published_events[0].id)
        self.assertEqual(resp.status_code, 200, 'Event user must have access to published event.')

    def test_events_access_6(self):
        """Access to an unpublished event with event user."""
        self.authenticate('event_user', 'event_user')
        unpublished_events = self.events.filtered(lambda event: not event.website_published)
        resp = self.url_open('/event/%i' % unpublished_events[0].id)
        self.assertEqual(resp.status_code, 200, 'Event user must have access to unpublished event.')

    def test_events_access_7(self):
        """Access to an published event with portal user."""
        self.authenticate('user_portal', 'user_portal')
        published_events = self.events.filtered(lambda event: event.website_published)
        resp = self.url_open('/event/%i' % published_events[0].id)
        self.assertEqual(resp.status_code, 200, 'Portal user must have access to published event.')

    def test_events_access_8(self):
        """Access to an unpublished event with portal user."""
        with mute_logger('odoo.addons.http_routing.models.ir_http'):
            self.authenticate('user_portal', 'user_portal')
            unpublished_events = self.events.filtered(lambda event: not event.website_published)
            resp = self.url_open('/event/%i' % unpublished_events[0].id)
            self.assertEqual(resp.status_code, 403, 'Portal user must not have access to unpublished event.')

    def test_events_home_page_1(self):
        """Portal can only view the published events."""
        self.authenticate('user_portal', 'user_portal')
        published_event = self.events.filtered(lambda event: event.website_published)[0]
        unpublished_event = self.events.filtered(lambda event: not event.website_published)[0]
        resp = self.url_open('/event')
        self.assertTrue(unpublished_event.name not in resp.text, 'Portal should not see the unpublished events.')
        self.assertTrue(published_event.name in resp.text, 'Portal must see the published events.')

    def test_events_home_page_2(self):
        """Admin can see all the events."""
        self.authenticate('event_manager', 'event_manager')
        published_event = self.events.filtered(lambda event: event.website_published)[0]
        unpublished_event = self.events.filtered(lambda event: not event.website_published)[0]
        resp = self.url_open('/event')
        self.assertTrue(unpublished_event.name in resp.text, 'Admin must see the unpublished events.')
        self.assertTrue(published_event.name in resp.text, 'Admin must see the published events.')
