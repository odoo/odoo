# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.website.tests.test_base_url import TestUrlCommon
from odoo.addons.website_event.tests.common import TestWebsiteEventCommon
from odoo.tests import tagged
from odoo.tools import mute_logger


@tagged('post_install', '-at_install')
class TestUi(HttpCaseWithUserDemo):

    def test_website_event_tour_admin(self):
        self.start_tour("/", 'website_event_tour', login='admin', step_delay=100)


@tagged('-at_install', 'post_install')
class TestURLs(TestUrlCommon):

    def test_canonical_url(self):
        self._assertCanonical('/event?date=all', self.domain + '/event')
        self._assertCanonical('/event?date=old', self.domain + '/event?date=old')


@tagged('post_install', '-at_install')
class TestWebsiteAccess(HttpCaseWithUserDemo, TestWebsiteEventCommon):

    def setUp(self):
        super(TestWebsiteAccess, self).setUp()

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

        self.portal_user = mail_new_test_user(
            self.env, name='Smeagol', login='user_portal', password='user_portal', email='portal@example.com',
            groups='base.group_portal'
        )

    def test_website_access_event_manager(self):
        """ Event managers are allowed to access both published and unpublished events """
        self.authenticate('user_eventmanager', 'user_eventmanager')
        published_events = self.events.filtered(lambda event: event.website_published)
        resp = self.url_open('/event/%i' % published_events[0].id)
        self.assertEqual(resp.status_code, 200, 'Managers must have access to published event.')

        unpublished_events = self.events.filtered(lambda event: not event.website_published)
        resp = self.url_open('/event/%i' % unpublished_events[0].id)
        self.assertEqual(resp.status_code, 200, 'Managers must have access to unpublished event.')

        resp = self.url_open('/event')
        self.assertTrue(published_events[0].name in resp.text, 'Managers must see the unpublished events.')
        self.assertTrue(unpublished_events[0].name in resp.text, 'Managers must see the published events.')

    def test_website_access_event_uer(self):
        """ Event users are allowed to access both published and unpublished events """
        self.authenticate('user_eventuser', 'user_eventuser')
        published_events = self.events.filtered(lambda event: event.website_published)
        resp = self.url_open('/event/%i' % published_events[0].id)
        self.assertEqual(resp.status_code, 200, 'Event user must have access to published event.')

        unpublished_events = self.events.filtered(lambda event: not event.website_published)
        resp = self.url_open('/event/%i' % unpublished_events[0].id)
        self.assertEqual(resp.status_code, 200, 'Event user must have access to unpublished event.')

        resp = self.url_open('/event')
        self.assertTrue(published_events[0].name in resp.text, 'Event user must see the unpublished events.')
        self.assertTrue(unpublished_events[0].name in resp.text, 'Event user must see the published events.')

    @mute_logger('odoo.addons.http_routing.models.ir_http')
    def test_website_access_portal(self):
        """ Portal users access only published events """
        self.authenticate('user_portal', 'user_portal')
        published_events = self.events.filtered(lambda event: event.website_published)
        resp = self.url_open('/event/%i' % published_events[0].id)
        self.assertEqual(resp.status_code, 200, 'Portal user must have access to published event.')

        unpublished_events = self.events.filtered(lambda event: not event.website_published)
        resp = self.url_open('/event/%i' % unpublished_events[0].id)
        self.assertEqual(resp.status_code, 403, 'Portal user must not have access to unpublished event.')

        resp = self.url_open('/event')
        self.assertTrue(published_events[0].name in resp.text, 'Portal must see the published events.')
        self.assertFalse(unpublished_events[0].name in resp.text, 'Portal should not see the unpublished events.')

    @mute_logger('odoo.addons.http_routing.models.ir_http')
    def test_website_access_public(self):
        """ Public users access only published events """
        published_events = self.events.filtered(lambda event: event.website_published)
        resp = self.url_open('/event/%i' % published_events[0].id)
        self.assertEqual(resp.status_code, 200, 'Public must have access to published event')

        unpublished_events = self.events.filtered(lambda event: not event.website_published)
        resp = self.url_open('/event/%i' % unpublished_events[0].id)
        self.assertEqual(resp.status_code, 403, 'Public must not have access to unpublished event')

        resp = self.url_open('/event')
        self.assertTrue(published_events[0].name in resp.text, 'Public must see the published events.')
        self.assertFalse(unpublished_events[0].name in resp.text, 'Public should not see the unpublished events.')

    def test_sitemap(self):
        resp = self.url_open('/sitemap.xml')
        self.assertTrue('/event/event-0' in resp.text, 'Published events must be present in the sitemap')
        self.assertTrue('/event/event-1' in resp.text, 'Published events must be present in the sitemap')
        self.assertFalse('/event/event-2' in resp.text, 'Unpublished events must not be present in the sitemap')
