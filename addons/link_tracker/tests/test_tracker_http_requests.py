from odoo.addons.link_tracker.tests.common import MockLinkTracker
from odoo.tests import common, tagged
from odoo.tools import mute_logger


@tagged('post_install', '-at_install')
class TestTrackerHttpRequests(MockLinkTracker, common.HttpCase):

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
