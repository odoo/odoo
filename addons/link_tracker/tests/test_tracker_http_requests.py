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

        # Check that no click is registered for a WhatsApp preview agent
        self.url_open(link, headers={'User-Agent': 'WhatsApp/2.22.20.72 A'}, allow_redirects=False)
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

        # Check that in-app browsers of social apps do register the click
        for user_agent in (
            (
                'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/21E219 '
                'Instagram 320.0.2.29.98 (iPhone14,3; iOS 17_4; en_US; en; scale=3.00; 1284x2778; 569998124)'
            ),
            (
                'Mozilla/5.0 (Linux; Android 12; NCO-LX1 Build/HUAWEINCO-LX1; wv) AppleWebKit/537.36 (KHTML, like Gecko) '
                'Version/4.0 Chrome/99.0.4844.88 Mobile Safari/537.36 [Pinterest/Android]'
            ),
        ):
            self.url_open(link, headers={'User-Agent': user_agent}, allow_redirects=False)
        self.assertEqual(len(link_tracker.link_click_ids), 3)
