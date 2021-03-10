# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import fields
from odoo.addons.website_event.tests.common import TestWebsiteEventCommon
from odoo.tests.common import users


class TestEventWebsite(TestWebsiteEventCommon):

    @users('user_eventmanager')
    def test_menu_create(self):
        event = self.env['event.event'].create({
            'name': 'TestEvent',
            'date_begin': fields.Datetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': fields.Datetime.to_string(datetime.today() + timedelta(days=15)),
            'website_menu': True,
            'community_menu': False,
        })
        self.assertTrue(event.website_menu)
        self.assertFalse(event.community_menu)
        self._assert_website_menus(event, ['Introduction', 'Location', 'Register'], menus_out=['Community'])

        event.community_menu = True
        self._assert_website_menus(event, ['Introduction', 'Location', 'Register', 'Community'])

        event = self.env['event.event'].create({
            'name': 'TestEvent',
            'date_begin': fields.Datetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': fields.Datetime.to_string(datetime.today() + timedelta(days=15)),
            'website_menu': False,
        })
        self.assertFalse(event.website_menu)
        self.assertFalse(event.community_menu)
        self.assertFalse(event.menu_id)


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

        introduction_menu = event.menu_id.child_id.filtered(lambda menu: menu.name == 'Introduction')
        introduction_menu.unlink()

        self.assertTrue(event.website_menu)
        self._assert_website_menus(event, ['Location', 'Register'], menus_out=['Introduction', 'Community'])
