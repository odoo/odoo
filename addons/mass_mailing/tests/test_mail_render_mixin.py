from lxml import html

from odoo.addons.mass_mailing.tests.common import MassMailCommon
from odoo.tests import tagged


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestMailRenderMixin(MassMailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMailRenderMixin, cls).setUpClass()

        cls.mailing_1 = cls.env['mailing.mailing'].create({
            'subject': 'First Mailing',
        })
        cls.env['mailing.mailing'].create({
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
            'mass_mailing_id': self.mailing_1.id,
            'utm_reference': f'mailing.mailing,{self.mailing_1.id}',
            'source_id': self.env.ref('utm.utm_source_mailing').id,
            'medium_id': self.env.ref('utm.utm_medium_email').id,
        }

        # Execute
        result_html_tracked = self.env["mail.render.mixin"]._shorten_links(html_links_tracked, link_tracker_vals)
        result_html_untracked = self.env["mail.render.mixin"]._shorten_links(html_links_not_tracked, link_tracker_vals)

        root_tracked = html.fromstring(result_html_tracked)
        root_untracked = html.fromstring(result_html_untracked)
        tracked_links = root_tracked.xpath("//a")
        untracked_links = root_untracked.xpath("//a")

        # Assert
        self._assert_all_link_tracking(tracked_links, untracked_links)

    def _assert_all_link_tracking(self, tracked_links, untracked_links):
        untracked_link_1_href = untracked_links[0].get("href")
        untracked_link_2_href = untracked_links[1].get("href")
        self.assertNotIn('/r/', untracked_link_1_href)
        self.assertNotIn('/r/', untracked_link_2_href)
        self.assertEqual('https://example.com/page1', untracked_link_1_href)
        self.assertEqual('https://example.com/page2', untracked_link_2_href)
        for link in tracked_links:
            self.assertIn('/r/', link.get("href"))
