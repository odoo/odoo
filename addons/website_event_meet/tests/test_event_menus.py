from datetime import datetime, timedelta

from odoo import fields
from odoo.addons.website_event.tests.common import OnlineEventCase
from odoo.tests.common import users


class TestEventWebsiteMeet(OnlineEventCase):

    def _get_menus(self):
        return super()._get_menus() | {'Community'}

    @users('user_eventmanager')
    def test_create_menu(self):
        event = self.env['event.event'].create({
            'name': 'TestEvent',
            'date_begin': fields.Datetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': fields.Datetime.to_string(datetime.today() + timedelta(days=15)),
            'website_menu': True,
            'community_menu': True,
        })
        self._assert_website_menus(event)

        event.write({
            'community_menu': False,
        })
        self._assert_website_menus(event, ['Introduction', 'Location', 'Info'], menus_out=['Community'])

    @users('user_event_web_manager')
    def test_menu_management_frontend(self):
        event = self.env['event.event'].create({
            'name': 'TestEvent',
            'date_begin': fields.Datetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': fields.Datetime.to_string(datetime.today() + timedelta(days=15)),
            'website_menu': True,
            'community_menu': True,
        })
        self.assertTrue(event.community_menu)
        self._assert_website_menus(event, self._get_menus())

        menu = event.menu_id.child_id.filtered(lambda menu: menu.name == 'Community')
        menu.unlink()
        self.assertFalse(event.community_menu)

        self._assert_website_menus(event, ['Introduction', 'Location', 'Info'], menus_out=['Community'])

        event.write({'community_menu': True})
        self.assertTrue(event.community_menu)
        self._assert_website_menus(event, self._get_menus())
