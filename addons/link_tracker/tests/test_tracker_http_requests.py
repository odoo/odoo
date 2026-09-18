from odoo.addons.link_tracker.tests.common import MockLinkTracker
from odoo.tests import common, tagged
from werkzeug.urls import url_parse
from odoo.tools import mute_logger


@tagged('post_install', '-at_install')
class TestTrackerHttpRequests(MockLinkTracker, common.HttpCase):

    def test_preserve_incoming_query_params(self):
        """Ensure incoming query parameters survive the tracked redirect."""
        link_tracker = self.env['link.tracker'].create({
            'url': '/landing-page?utm_source=stored&existing=destination',
            'title': 'Odoo',
        })

        response = self.url_open(
            '/r/' + link_tracker.code + '?gclid=TEST123&foo=BAR&existing=incoming',
            allow_redirects=False,
        )
        redirect_url = url_parse(response.headers['Location'])
        redirect_params = redirect_url.decode_query().to_dict(flat=True)

        self.assertEqual(redirect_params['gclid'], 'TEST123')
        self.assertEqual(redirect_params['foo'], 'BAR')
        self.assertEqual(redirect_params['existing'], 'destination')
        self.assertEqual(redirect_params['utm_source'], 'stored')

    @mute_logger("odoo.addons.http_routing.models.ir_http", "odoo.http")
    def test_no_preview_tracking(self):
        """Ensure that requests with a user agent matching known preview user agents will not be registered as a click"""
        link_tracker = self.env['link.tracker'].create({
                'url': '/',
                'title': 'Odoo',
            })
        self.assertEqual(len(link_tracker.link_click_ids), 0)
        link = '/r/' + link_tracker.code

        # Check that no click is registrered for a MicrosoftPreview agent
        self.url_open(
            link,
            headers={
                'User-Agent': 'Mozilla/5.0 MicrosoftPreview/2.0 +https://aka.ms/MicrosoftPreview',
            },
            allow_redirects=False,
        )
        self.assertEqual(len(link_tracker.link_click_ids), 0)

        # Check that no click is registered for a Google Messages preview agent
        self.url_open(
            link,
            headers={
                'User-Agent': 'Mozilla/5.0 Google-PageRenderer Google (+https://developers.google.com/+/web/snippet/)'
            },
            allow_redirects=False,
        )
        self.assertEqual(len(link_tracker.link_click_ids), 0)

        # Check (sanity) that a request from a regular UA does still register the click
        self.url_open(
            link,
            headers={
                'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0'
            },
            allow_redirects=False,
        )
        self.assertEqual(len(link_tracker.link_click_ids), 1)
