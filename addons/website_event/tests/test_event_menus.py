from datetime import datetime, timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests.common import HttpCase, users

from odoo.addons.website_event.tests.common import OnlineEventCase


class TestEventMenus(OnlineEventCase, HttpCase):
    @users("admin")
    def test_menu_copy(self):

        event = self.env["event.event"].create(
            {
                "name": "TestEvent",
                "date_begin": fields.Datetime.to_string(
                    datetime.today() + timedelta(days=1)
                ),
                "date_end": fields.Datetime.to_string(
                    datetime.today() + timedelta(days=15)
                ),
                "website_menu": True,
            }
        )
        self.assertTrue(event.website_menu)
        self.assertTrue(event.introduction_menu)
        self.env["ir.ui.view"].create(
            {
                "arch_db": '<xpath expr="//div[@id=\'oe_structure_website_event_intro_2\']" position="replace"><p>This is an intro</p></xpath>',
                "inherit_id": event.introduction_menu_ids.view_id.id,
                "key": "website_event.intro-test-child",
            }
        )
        event_copy = event.copy()
        self.assertTrue(event_copy.website_menu)
        self.assertTrue(event_copy.introduction_menu)

        self.assertNotEqual(
            event.introduction_menu_ids, event_copy.introduction_menu_ids
        )

        self.assertNotEqual(
            event.introduction_menu_ids.view_id.inherit_children_ids,
            event_copy.introduction_menu_ids.view_id.inherit_children_ids,
        )

        self.assertEqual(
            event.introduction_menu_ids.view_id.arch_db,
            event_copy.introduction_menu_ids.view_id.arch_db,
        )
        self.assertEqual(
            event.introduction_menu_ids.view_id.inherit_children_ids[0].arch_db,
            event_copy.introduction_menu_ids.view_id.inherit_children_ids[0].arch_db,
        )
        self.assertIn(
            "This is an intro",
            event_copy.introduction_menu_ids.view_id.inherit_children_ids[0].arch_db,
        )

    @users("admin")
    def test_menu_deletion(self):

        event = self.env["event.event"].create(
            {
                "name": "TestEvent",
                "date_begin": fields.Datetime.to_string(
                    datetime.today() + timedelta(days=1)
                ),
                "date_end": fields.Datetime.to_string(
                    datetime.today() + timedelta(days=15)
                ),
                "website_menu": True,
            }
        )

        new_page_url = f"{event.website_url}/newpage"

        website_menu = self.env["website.menu"].create(
            {
                "name": "New Menu",
                "url": new_page_url,
                "parent_id": event.introduction_menu_ids[0].menu_id.parent_id.id,
            }
        )

        self.env["website.event.menu"].create(
            {
                "event_id": event.id,
                "menu_id": website_menu.id,
                "menu_type": "community",
            }
        )

        new_page = self.env["website"].new_page(new_page_url.lstrip("/"))
        website_menu.page_id = new_page["page_id"]

        website_menu_id = website_menu.id
        website_menu.unlink()
        self.assertFalse(
            bool(self.env["website.menu"].search([("id", "=", website_menu_id)]))
        )

    @users("admin")
    def test_new_page_section_outside_wrap(self):
        """new_page() must not crash when the event's base layout template
        contains a <section> outside the #wrap container (WEM-02): the
        section-relocation logic must only look at sections that are direct
        children of #wrap, not any <section> anywhere in the document."""
        event = self.env["event.event"].create(
            {
                "name": "TestEvent",
                "date_begin": fields.Datetime.to_string(
                    datetime.today() + timedelta(days=1)
                ),
                "date_end": fields.Datetime.to_string(
                    datetime.today() + timedelta(days=15)
                ),
                "website_menu": True,
            }
        )
        new_page_url = f"{event.website_url}/newpage-section"
        website_menu = self.env["website.menu"].create(
            {
                "name": "New Menu With Section",
                "url": new_page_url,
                "parent_id": event.introduction_menu_ids[0].menu_id.parent_id.id,
            }
        )
        self.env["website.event.menu"].create(
            {
                "event_id": event.id,
                "menu_id": website_menu.id,
                "menu_type": "community",
            }
        )

        layout_view = self.env.ref("website_event.layout")
        layout_view.arch = layout_view.arch.replace(
            "</t>", '<section id="o_outside_wrap_section"/></t>', 1
        )

        new_page = self.env["website"].new_page(
            new_page_url.lstrip("/"), sections_arch="<section>Injected</section>"
        )
        self.assertTrue(new_page.get("view_id"))

    @users("admin")
    def test_create_menu_skip_when_nothing_changed(self):
        """Round-1 fix WEM-05: when a website.menu parent group has no
        new (string-id) menu among its children, WebsiteMenu.save() must
        skip straight to the next group instead of still querying
        website.event.menu for it - materializing new_menus to a list so
        the `if not new_menus` check actually short-circuits (a `filter`
        object is always truthy and never would)."""
        event = self.env["event.event"].create(
            {
                "name": "TestEvent",
                "date_begin": fields.Datetime.to_string(
                    datetime.today() + timedelta(days=1)
                ),
                "date_end": fields.Datetime.to_string(
                    datetime.today() + timedelta(days=15)
                ),
                "website_menu": True,
            }
        )
        home_menu = event.introduction_menu_ids.menu_id
        data = {
            "data": [
                {
                    "id": home_menu.id,
                    "name": home_menu.name,
                    "url": home_menu.url,
                    "new_window": False,
                    "sequence": home_menu.sequence,
                    "parent_id": home_menu.parent_id.id,
                },
                # An unrelated, genuinely new top-level menu so save()'s
                # outer has_new_menus gate is True - home_menu's own group
                # (the one under test) has no new menu of its own.
                {
                    "id": "new-1",
                    "name": "Unrelated New Menu",
                    "url": "/unrelated-new-menu",
                    "new_window": False,
                    "sequence": 100,
                    "parent_id": self.env.ref("website.main_menu").id,
                },
            ],
        }

        WebsiteEventMenu = type(self.env["website.event.menu"])
        original_search = WebsiteEventMenu.search
        search_domains = []

        def counting_search(self_, domain, *args, **kwargs):
            search_domains.append(domain)
            return original_search(self_, domain, *args, **kwargs)

        with patch.object(WebsiteEventMenu, "search", counting_search):
            self.env["website.menu"].save(
                self.env.ref("website.default_website").id, data
            )

        home_menu_parent_searches = [
            domain
            for domain in search_domains
            if domain == [("menu_id.parent_id", "=", home_menu.parent_id.id)]
        ]
        self.assertFalse(
            home_menu_parent_searches,
            "A group with no new menu must never trigger a "
            "website.event.menu search for it.",
        )

    @users("user_eventmanager")
    def test_menu_management(self):
        event = self.env["event.event"].create(
            {
                "name": "TestEvent",
                "date_begin": fields.Datetime.to_string(
                    datetime.today() + timedelta(days=1)
                ),
                "date_end": fields.Datetime.to_string(
                    datetime.today() + timedelta(days=15)
                ),
                "website_menu": True,
                "community_menu": False,
            }
        )
        self.assertTrue(event.website_menu)
        self.assertTrue(event.introduction_menu)
        self.assertTrue(event.register_menu)
        self.assertFalse(event.community_menu)
        self._assert_website_menus(event, ["Home", "Practical"], menus_out=["Rooms"])

        event.community_menu = True
        self._assert_website_menus(event, ["Home", "Rooms", "Practical"])

        event = self.env["event.event"].create(
            {
                "name": "TestEvent",
                "date_begin": fields.Datetime.to_string(
                    datetime.today() + timedelta(days=1)
                ),
                "date_end": fields.Datetime.to_string(
                    datetime.today() + timedelta(days=15)
                ),
                "website_menu": False,
            }
        )
        self.assertFalse(event.website_menu)
        self.assertFalse(event.introduction_menu)
        self.assertFalse(event.register_menu)
        self.assertFalse(event.community_menu)
        self.assertFalse(event.menu_id)

        event.write({"website_menu": True})
        self._assert_website_menus(event, ["Home", "Practical"], menus_out=["Rooms"])

    @users("user_event_web_manager")
    def test_menu_management_frontend(self):
        event = self.env["event.event"].create(
            {
                "name": "TestEvent",
                "date_begin": fields.Datetime.to_string(
                    datetime.today() + timedelta(days=1)
                ),
                "date_end": fields.Datetime.to_string(
                    datetime.today() + timedelta(days=15)
                ),
                "website_menu": True,
                "community_menu": False,
            }
        )
        self._assert_website_menus(event, ["Home", "Practical"], menus_out=["Rooms"])

        event.menu_id.child_id.filtered(lambda menu: menu.name == "Home").unlink()

        self.assertTrue(event.website_menu)
        self._assert_website_menus(event, ["Practical"], menus_out=["Home", "Rooms"])

        event.introduction_menu = True
        self._assert_website_menus(event, ["Home", "Practical"], menus_out=["Rooms"])

    def test_submenu_url(self):
        old_event_1, old_event_2, event_1, event_2, event_3 = self.env[
            "event.event"
        ].create(
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

        old_event_1.introduction_menu_ids.menu_id.url = (
            f"/event/test-event-{old_event_1.id}/page/home-test-event"
        )
        old_event_2.introduction_menu_ids.menu_id.url = (
            f"/event/test-event-{old_event_2.id}/page/home-test-event"
        )
        old_event_menus = (old_event_1 + old_event_2).introduction_menu_ids
        self.assertEqual(
            len(old_event_menus.view_id), 2, "Each menu should have a view"
        )

        new_event_menus = (event_1 + event_2).introduction_menu_ids
        self.assertEqual(
            len(new_event_menus.view_id), 2, "Each menu should have a view"
        )

        menu_without_view = event_3._create_menu(
            1,
            "custom",
            f"/event/test-event-{event_3.id}/page/home-test-event",
            "website_event.template_intro",
            "introduction",
        )
        self.assertEqual(
            len(
                self.env["website.event.menu"]
                .search([("menu_id", "in", menu_without_view.ids)])
                .view_id
            ),
            0,
            "The menu should not have a view assigned because an URL has been given manually",
        )

        all_menus = (
            old_event_menus.menu_id + new_event_menus.menu_id + menu_without_view
        )
        for menu in all_menus:
            res = self.url_open(menu.url)
            self.assertEqual(res.status_code, 200)

    def test_submenu_url_uniqueness(self):
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

        event_1_home_menu = event_1.menu_id.child_id.filtered(
            lambda menu: menu.name == "Home"
        )
        event_2_home_menu = event_2.menu_id.child_id.filtered(
            lambda menu: menu.name == "Home"
        )

        for event_1_menu, event_2_menu in zip(
            event_1_home_menu, event_2_home_menu, strict=True
        ):
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
