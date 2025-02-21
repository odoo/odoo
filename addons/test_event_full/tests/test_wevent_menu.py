from odoo.addons.test_event_full.tests.common import TestWEventCommon
from odoo.tests import tagged
from odoo.tests.common import users


@tagged('event_online', 'post_install', '-at_install')
class TestWEventMenu(TestWEventCommon):

    @users('admin')
    def test_seo_data(self):
        """Test SEO data for submenus on event website page"""

        self.assertFalse(self.event.website_meta_title, 'Event should initially have no meta title')
        self.event.write({
            'website_meta_title': 'info',
        })
        self.assertTrue(self.event.website_meta_title, 'Event should have a meta title after writing')

        menus = [
            ('booth_menu_ids', 'Get a Booth'),
            ('exhibitor_menu_ids', 'Exhibitor'),
            ('community_menu_ids', 'Leaderboard'),
            ('track_menu_ids', 'Talks'),
            ('track_menu_ids', 'Agenda'),
            ('track_proposal_menu_ids', 'Talk Proposal'),
        ]

        for menu_field, menu_name in menus:
            menu = self.event[menu_field]

            if menu_field == 'track_menu_ids':
                menu_url = '/track' if menu_name == 'Talks' else '/agenda'
                menu = self.event[menu_field].filtered(lambda menu: menu.menu_id.url.endswith(menu_url))

            self.assertFalse(menu.website_meta_title, f"{menu_name} page should initially have no meta title")
            menu.write({'website_meta_title': menu_name})

            web_page = self.url_open(menu.menu_id.url)

            self.assertTrue(menu.website_meta_title, f"{menu_name} page should have a meta title after writing")
            self.assertIn(f"<title>{menu.website_meta_title}</title>", web_page.text)
