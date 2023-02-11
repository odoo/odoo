# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import fields
from odoo.addons.website_event.tests.common import TestWebsiteEventCommon
from odoo.tests.common import users


class TestEventMenus(TestWebsiteEventCommon):

    @users('user_eventmanager')
    def test_menu_management(self):
        event = self.env['event.event'].create({
            'name': 'TestEvent',
            'date_begin': fields.Datetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': fields.Datetime.to_string(datetime.today() + timedelta(days=15)),
            'website_menu': True,
            'community_menu': False,
        })
        self.assertTrue(event.website_menu)
        self.assertTrue(event.introduction_menu)
        self.assertTrue(event.location_menu)
        self.assertTrue(event.register_menu)
        self.assertFalse(event.community_menu)
        self._assert_website_menus(event, ['Introduction', 'Location', 'Register'], menus_out=['Community'])

        event.community_menu = True
        self._assert_website_menus(event, ['Introduction', 'Location', 'Register', 'Community'])

        # test create without any requested menus
        event = self.env['event.event'].create({
            'name': 'TestEvent',
            'date_begin': fields.Datetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': fields.Datetime.to_string(datetime.today() + timedelta(days=15)),
            'website_menu': False,
        })
        self.assertFalse(event.website_menu)
        self.assertFalse(event.introduction_menu)
        self.assertFalse(event.location_menu)
        self.assertFalse(event.register_menu)
        self.assertFalse(event.community_menu)
        self.assertFalse(event.menu_id)

        # test update of website_menu triggering 3 sub menus
        event.write({'website_menu': True})
        self._assert_website_menus(event, ['Introduction', 'Location', 'Register'], menus_out=['Community'])

    @users('user_event_web_manager')
    def test_menu_management_frontend(self):
        event = self.env['event.event'].create({
            'name': 'TestEvent',
            'date_begin': fields.Datetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': fields.Datetime.to_string(datetime.today() + timedelta(days=15)),
            'website_menu': True,
            'community_menu': False,
        })
        self._assert_website_menus(event, ['Introduction', 'Location', 'Register'], menus_out=['Community'])

        # simulate menu removal from frontend: aka unlinking a menu
        event.menu_id.child_id.filtered(lambda menu: menu.name == 'Introduction').unlink()

        self.assertTrue(event.website_menu)
        self._assert_website_menus(event, ['Location', 'Register'], menus_out=['Introduction', 'Community'])

        # re-created from backend
        event.introduction_menu = True
        self._assert_website_menus(event, ['Introduction', 'Location', 'Register'], menus_out=['Community'])
