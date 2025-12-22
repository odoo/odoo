from datetime import datetime, timedelta

from odoo.addons.website_event.tests.common import OnlineEventCase
from odoo.tests.common import tagged, users


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestWebsiteEventTrackQuiz(OnlineEventCase):

    def _get_menus(self):
        return super()._get_menus() | {'Rooms'}

    @users('user_eventmanager')
    def test_menu_management(self):
        # Check that if no value is specified for community_menu, it is computed from website_menu.
        event = self.env['event.event'].create({
            'name': 'TestEvent',
            'date_begin': datetime.today() + timedelta(days=1),
            'date_end': datetime.today() + timedelta(days=15),
            'website_menu': False,
        })
        self.assertFalse(event.community_menu)
        event.write({'website_menu': True})
        self._assert_website_menus(event, ['Home', 'Practical', 'Rooms'])

        # Check that if a value is specified for community_menu, it is not computed from website_menu.
        event = self.env['event.event'].create({
            'name': 'TestEvent',
            'date_begin': datetime.today() + timedelta(days=1),
            'date_end': datetime.today() + timedelta(days=15),
            'website_menu': True,
            'community_menu': False,
        })
        self.assertFalse(event.community_menu)
        self._assert_website_menus(event, ['Home', 'Practical'], menus_out=['Rooms'])
        event.write({'community_menu': True})
        self._assert_website_menus(event, self._get_menus())
