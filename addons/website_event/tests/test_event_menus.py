# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import fields
from odoo.addons.website_event.tests.common import OnlineEventCase
from odoo.tests.common import HttpCase, users


class TestEventMenus(OnlineEventCase, HttpCase):

    @users('admin')
    def test_menu_copy(self):
        """ Test that the content of the introduction(Home) menu is
        correctly copied when duplicating an event """

        event = self.env['event.event'].create({
            'name': 'TestEvent',
            'date_begin': fields.Datetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': fields.Datetime.to_string(datetime.today() + timedelta(days=15)),
            'website_menu': True,
        })
        self.assertTrue(event.website_menu)
        self.assertTrue(event.introduction_menu)
        self.env['ir.ui.view'].create({
            'arch_db': '<xpath expr="//div[@id=\'oe_structure_website_event_intro_2\']" position="replace"><p>This is an intro</p></xpath>',
            'inherit_id': event.introduction_menu_ids.view_id.id,
            'key': 'website_event.intro-test-child',
        })
        event_copy = event.copy()
        self.assertTrue(event_copy.website_menu)
        self.assertTrue(event_copy.introduction_menu)

        # The menu used should be different
        self.assertNotEqual(event.introduction_menu_ids, event_copy.introduction_menu_ids)

        # The child in the view should be different
        self.assertNotEqual(
            event.introduction_menu_ids.view_id.inherit_children_ids,
            event_copy.introduction_menu_ids.view_id.inherit_children_ids,
        )

        # The content of the views should be the same
        self.assertEqual(
            event.introduction_menu_ids.view_id.arch_db,
            event_copy.introduction_menu_ids.view_id.arch_db,
        )
        self.assertEqual(
            event.introduction_menu_ids.view_id.inherit_children_ids[0].arch_db,
            event_copy.introduction_menu_ids.view_id.inherit_children_ids[0].arch_db,
        )
        self.assertIn("This is an intro", event_copy.introduction_menu_ids.view_id.inherit_children_ids[0].arch_db)

    @users('admin')
    def test_menu_deletion(self):
        """ Testing the complex case of this module's override of 'website.menu#unlink'.

        When deleting a website.menu, we want to delete its matching website.event.menu.
        When deleting a website.event.menu, we want to delete its associated views.

        *However*, when deleting views, it can cascade delete website.menu.
        (website.page has a cascade on 'view_id', website.menu has a cascade on 'page_id')

        Meaning we need to identify which website.menus are going to be cascade-deleted when calling
        'unlink' on the matching website.event.menu and avoid calling the super unlink of
        website.menu on them (it causes a 'Missing Record' cache error). """

        event = self.env['event.event'].create({
            'name': 'TestEvent',
            'date_begin': fields.Datetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': fields.Datetime.to_string(datetime.today() + timedelta(days=15)),
            'website_menu': True,
        })

        new_page_url = f'{event.website_url}/newpage'

        # create a custom menu entry and its associated website.page / website.event.menu
        website_menu = self.env['website.menu'].create({
            'name': 'New Menu',
            'url': new_page_url,
            'parent_id': event.introduction_menu_ids[0].menu_id.parent_id.id,
        })

        self.env['website.event.menu'].create({
            'event_id': event.id,
            'menu_id': website_menu.id,
            'menu_type': 'community',
        })

        new_page = self.env['website'].new_page(new_page_url.lstrip('/'))
        website_menu.page_id = new_page['page_id']

        website_menu_id = website_menu.id
        website_menu.unlink()
        self.assertFalse(bool(self.env['website.menu'].search([('id', '=', website_menu_id)])))

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
        self.assertTrue(event.register_menu)
        self.assertFalse(event.community_menu)
        self._assert_website_menus(event, ['Home', 'Practical'], menus_out=['Rooms'])

        event.community_menu = True
        self._assert_website_menus(event, ['Home', 'Rooms', 'Practical'])

        # test create without any requested menus
        event = self.env['event.event'].create({
            'name': 'TestEvent',
            'date_begin': fields.Datetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': fields.Datetime.to_string(datetime.today() + timedelta(days=15)),
            'website_menu': False,
        })
        self.assertFalse(event.website_menu)
        self.assertFalse(event.introduction_menu)
        self.assertFalse(event.register_menu)
        self.assertFalse(event.community_menu)
        self.assertFalse(event.menu_id)

        # test update of website_menu triggering 3 sub menus
        event.write({'website_menu': True})
        self._assert_website_menus(event, ['Home', 'Practical'], menus_out=['Rooms'])

    @users('user_event_web_manager')
    def test_menu_management_frontend(self):
        event = self.env['event.event'].create({
            'name': 'TestEvent',
            'date_begin': fields.Datetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': fields.Datetime.to_string(datetime.today() + timedelta(days=15)),
            'website_menu': True,
            'community_menu': False,
        })
        self._assert_website_menus(event, ['Home', 'Practical'], menus_out=['Rooms'])

        # simulate menu removal from frontend: aka unlinking a menu
        event.menu_id.child_id.filtered(lambda menu: menu.name == 'Home').unlink()

        self.assertTrue(event.website_menu)
        self._assert_website_menus(event, ['Practical'], menus_out=['Home', 'Rooms'])

        # re-created from backend
        event.introduction_menu = True
        self._assert_website_menus(event, ['Home', 'Practical'], menus_out=['Rooms'])

    def test_submenu_url(self):
        """ Test that the different URL of a submenu page of an event are accessible """
        old_event_1, old_event_2, event_1, event_2, event_3 = self.env["event.event"].create(
            [
                {
                    "community_menu": False,
                    "date_begin": fields.Datetime.to_string(
                        datetime.today() + timedelta(days=1)
                    ),
                    "date_end": fields.Datetime.to_string(
                        datetime.today() + timedelta(days=15)
                    ),
                    "is_published": True,
                    "name": "Test Event",
                    "website_menu": True,
                }
                for _ in range(5)
            ]
        )

        # Use previous URL for submenu page
        old_event_1.introduction_menu_ids.menu_id.url = f"/event/test-event-{old_event_1.id}/page/home-test-event"
        old_event_2.introduction_menu_ids.menu_id.url = f"/event/test-event-{old_event_2.id}/page/home-test-event"
        old_event_menus = (old_event_1 + old_event_2).introduction_menu_ids
        self.assertEqual(len(old_event_menus.view_id), 2, "Each menu should have a view")

        # Menu with unique page
        new_event_menus = (event_1 + event_2).introduction_menu_ids
        self.assertEqual(len(new_event_menus.view_id), 2, "Each menu should have a view")

        # Menu without views
        menu_without_view = event_3._create_menu(1, 'custom', f"/event/test-event-{event_3.id}/page/home-test-event", 'website_event.template_intro', 'introduction')
        self.assertEqual(
            len(self.env['website.event.menu'].search([('menu_id', 'in', menu_without_view.ids)]).view_id), 0,
            "The menu should not have a view assigned because an URL has been given manually"
        )

        all_menus = old_event_menus.menu_id + new_event_menus.menu_id + menu_without_view
        for menu in all_menus:
            res = self.url_open(menu.url)
            self.assertEqual(res.status_code, 200)

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
        event_1_home_menu = event_1.menu_id.child_id.filtered(
            lambda menu: menu.name == "Home"
        )
        event_2_home_menu = event_2.menu_id.child_id.filtered(
            lambda menu: menu.name == "Home"
        )

        for event_1_menu, event_2_menu in zip(event_1_home_menu, event_2_home_menu):
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
