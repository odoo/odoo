# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import fields
from odoo.addons.website_event.tests.common import OnlineEventCase
from odoo.tests.common import users


class TestEventMenus(OnlineEventCase):

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

    def test_submenu_url_uniqueness(self):
        """Ensure that the last part of the menus URL (used to retrieve the right view)
        are unique when creating two events with same name."""
        event_1, event_2 = self.env["event.event"].create(
            [
                {
                    "name": "Test Event",
                    "date_begin": fields.Datetime.to_string(
                        datetime.today() + timedelta(days=1)
                    ),
                    "date_end": fields.Datetime.to_string(
                        datetime.today() + timedelta(days=15)
                    ),
                    "website_menu": True,
                    "community_menu": False,
                }
                for _ in range(2)
            ]
        )

        # Skip the register and community menus since they already have a unique URL
        event_1_menus = event_1.menu_id.child_id.filtered(
            lambda menu: menu.name in ["Introduction", "Location"]
        )
        event_2_menus = event_2.menu_id.child_id.filtered(
            lambda menu: menu.name in ["Introduction", "Location"]
        )
        for event_1_menu, event_2_menu in zip(event_1_menus, event_2_menus):
            end_url_1 = event_1_menu.url.split("/")[-1]
            end_url_2 = event_2_menu.url.split("/")[-1]
            self.assertNotEqual(end_url_1, end_url_2)
            IrUiView = self.env["ir.ui.view"]
            self.assertEqual(
                IrUiView.search_count([("key", "=", "website_event.%s" % end_url_1)]),
                1,
            )
            self.assertEqual(
                IrUiView.search_count([("key", "=", "website_event.%s" % end_url_2)]),
                1,
            )
