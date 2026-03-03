import lxml.html

from odoo.addons.mass_mailing.tests.common import MassMailCommon
from odoo.tests import tagged


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestMailRenderMixin(MassMailCommon):

    def setUp(self):
        super().setUp()
        self.env['mailing.mailing'].create({
            'subject': 'First Mailing',
        })
        self.env['mailing.mailing'].create({
            'subject': 'Second Mailing',
        })

    def test_shorten_links(self):
        # Prepare
        html_links_tracked = """
            <div>
                <a href="https://example.com/page1">Link 1</a>
                <a href="https://example.com/page2">Link 2</a>
            </div>
        """
        html_links_not_tracked = """
            <div>
                <a href="https://example.com/page1" data-no-tracking='1'>Link 1</a>
                <a href="https://example.com/page2" data-no-tracking='1'>Link 2</a>
            </div>
        """
        link_tracker_vals = {
            'mass_mailing_id': 1,
            'utm_reference': 'mailing.mailing,1',
            'source_id': 2,
            'medium_id': 4,
        }

        # Execute
        result_html_tracked = self.env["mailing.mailing"]._shorten_links(html_links_tracked, link_tracker_vals)
        result_html_untracked = self.env["mailing.mailing"]._shorten_links(html_links_not_tracked, link_tracker_vals)

        root_tracked = lxml.html.fromstring(result_html_tracked)
        root_untracked = lxml.html.fromstring(result_html_untracked)
        tracked_links = root_tracked.xpath("//a")
        untracked_links = root_untracked.xpath("//a")

        # Assert
        self._assert_all_tracked(tracked_links)
        self._assert_all_untracked(untracked_links)

    def _assert_all_tracked(self, links):
        for link in links:
            self.assertIn('/r/', link.get("href"))

    def _assert_all_untracked(self, links):
        link_1_href = links[0].get("href")
        link_2_href = links[1].get("href")
        self.assertNotIn('/r/', link_1_href)
        self.assertNotIn('/r/', link_2_href)
        self.assertEqual('https://example.com/page1', link_1_href)
        self.assertEqual('https://example.com/page2', link_2_href)
