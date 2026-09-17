import json
import logging
from unittest.mock import patch

import werkzeug.exceptions
from lxml import html

from odoo.fields import Command
from odoo.http import root
from odoo.tests import HttpCase, common, freeze_time, tagged
from odoo.tools import mute_logger

from odoo.addons.http_routing.tests.common import MockRequest
from odoo.addons.website.controllers.main import Website

_logger = logging.getLogger(__name__)


@tagged("-at_install", "post_install")
class TestPage(common.TransactionCase):
    @freeze_time("2026-09-13 12:00:00")
    def test_scheduled_page_is_not_a_public_fuzzy_candidate_but_is_editable(self):
        website = self.env.ref("website.default_website")
        self.page_1.write(
            {
                "name": "zebratopic",
                "is_published": True,
                "website_indexed": True,
                "date_publish": "2026-09-14 12:00:00",
            }
        )
        public = website.with_user(website.user_id).with_context(website_id=website.id)
        with MockRequest(public.env, website=public):
            count, _results, fuzzy = public._search_with_fuzzy(
                "pages",
                "zebratopci",
                10,
                "id",
                {"displayDescription": True, "allowFuzzy": True},
            )
        _logger.debug("Scheduled fuzzy candidate: count=%s correction=%s", count, fuzzy)
        self.assertEqual(count, 0)
        self.assertFalse(fuzzy)
        with MockRequest(self.env, website=website):
            count, results, _fuzzy = website._search_with_fuzzy(
                "pages",
                "zebratopic",
                10,
                "id",
                {"displayDescription": True, "allowFuzzy": False},
            )
        self.assertEqual(count, 1)
        self.assertEqual(results[0]["results"].ids, self.page_1.ids)

    def test_visibility_cache_is_separate_for_each_website(self):
        website = self.env.ref("website.default_website")
        other = self.env["website"].create({"name": "Visibility challenge"})
        self.page_1.write({"website_id": website.id, "is_published": True})
        on_site = self.page_1.with_context(website_id=website.id)
        off_site = self.page_1.with_context(website_id=other.id)
        self.assertTrue(on_site.is_visible)
        self.assertFalse(off_site.is_visible)
        self.assertTrue(on_site.is_visible)
        self.page_1.is_published = False
        self.assertFalse(on_site.is_visible)

    @freeze_time("2026-09-13 12:00:00")
    def test_visibility_recomputes_after_publication_changes(self):
        page = self.page_1
        self.assertFalse(page.is_visible)
        page.is_published = True
        _logger.debug("Published page %s has is_visible=%s", page.id, page.is_visible)
        self.assertTrue(page.is_visible)
        page.date_publish = "2026-09-14 12:00:00"
        self.assertFalse(page.is_visible)
        page.date_publish = "2026-09-13 12:00:00"
        self.assertTrue(page.is_visible)

    @freeze_time("2026-09-13 12:00:00")
    def test_public_search_excludes_scheduled_pages(self):
        website = self.env.ref("website.default_website")
        self.page_1.write(
            {
                "is_published": True,
                "website_indexed": True,
                "date_publish": "2026-09-14 12:00:00",
            }
        )
        public_website = website.with_user(website.user_id).with_context(
            website_id=website.id
        )
        with MockRequest(public_website.env, website=public_website):
            count, results, _fuzzy = public_website._search_with_fuzzy(
                "pages",
                "page_1",
                10,
                "id",
                {"displayDescription": True, "allowFuzzy": False},
            )
        _logger.debug(
            "Scheduled page %s search count=%s results=%s",
            self.page_1.id,
            count,
            [detail["results"].ids for detail in results],
        )
        self.assertEqual(count, 0)
        self.page_1.date_publish = "2026-09-13 12:00:00"
        with MockRequest(public_website.env, website=public_website):
            count, results, _fuzzy = public_website._search_with_fuzzy(
                "pages",
                "page_1",
                10,
                "id",
                {"displayDescription": True, "allowFuzzy": False},
            )
        self.assertEqual(count, 1)
        self.assertEqual(results[0]["results"].ids, self.page_1.ids)

    def setUp(self):
        super().setUp()
        View = self.env["ir.ui.view"]
        Page = self.env["website.page"]
        Menu = self.env["website.menu"]

        self.base_view = View.create(
            {
                "name": "Base",
                "type": "qweb",
                "arch": "<div>content</div>",
                "key": "test.base_view",
            }
        )

        self.extension_view = View.create(
            {
                "name": "Extension",
                "mode": "extension",
                "inherit_id": self.base_view.id,
                "arch": '<div position="inside">, extended content</div>',
                "key": "test.extension_view",
            }
        )

        self.page_1 = Page.create(
            {
                "view_id": self.base_view.id,
                "url": "/page_1",
            }
        )

        self.page_1_menu = Menu.create(
            {
                "name": "Page 1 menu",
                "page_id": self.page_1.id,
                "website_id": 1,
            }
        )

    def test_homepage_url_sync_is_per_website(self):
        Website = self.env["website"]
        website_1 = Website.browse(1)
        website_2 = Website.create({"name": "Second Website"})

        page = (
            self.env["website.page"]
            .with_context(website_id=website_2.id)
            .create(
                {
                    "name": "MW Home",
                    "type": "qweb",
                    "arch": "<div>MW Home</div>",
                    "key": "test.mw_home",
                    "url": "/mw-home",
                    "is_published": True,
                    "website_id": website_2.id,
                }
            )
        )
        website_2.homepage_url = page.url
        self.assertEqual(website_2.homepage_url, "/mw-home")
        self.assertFalse(website_1.homepage_url)

        with MockRequest(self.env, website=website_1):
            page.url = "/mw-home-renamed"

        self.assertEqual(website_2.homepage_url, page.url)
        self.assertEqual(website_2.homepage_url, "/mw-home-renamed")
        self.assertFalse(website_1.homepage_url)

    def test_inverse_is_homepage_keeps_other_page(self):
        website = self.env["website"].browse(1)
        website.homepage_url = "/page_1"

        props = self.env["website.page.properties"].new(
            {
                "website_id": website.id,
                "url": "/some_other_page",
                "is_homepage": False,
            }
        )
        props._inverse_is_homepage()
        self.assertEqual(
            website.homepage_url,
            "/page_1",
            "Editing a non-homepage page must not wipe the real homepage.",
        )

        props_home = self.env["website.page.properties"].new(
            {
                "website_id": website.id,
                "url": "/page_1",
                "is_homepage": False,
            }
        )
        props_home._inverse_is_homepage()
        self.assertFalse(website.homepage_url)

    def test_controller_page_write_preserves_custom_menu_label(self):
        view = self.env["ir.ui.view"].create(
            {
                "name": "Listing",
                "type": "qweb",
                "arch": "<div/>",
                "key": "test.listing_ctrl_view",
            }
        )
        page = self.env["website.controller.page"].create(
            {
                "name": "Widgets",
                "view_id": view.id,
                "model_id": self.env["ir.model"]._get_id("res.partner"),
            }
        )
        menu = self.env["website.menu"].create(
            {
                "name": "Custom Label",
                "controller_page_id": page.id,
                "url": "/model/widgets",
                "website_id": 1,
            }
        )
        menu.name = "MY CUSTOM MENU LABEL"

        page.write({"is_published": not page.is_published})
        self.assertEqual(
            menu.name,
            "MY CUSTOM MENU LABEL",
            "Unrelated page write must not clobber the custom menu label.",
        )

        page.write({"name": "Gadgets"})
        self.assertEqual(menu.name, "Gadgets")
        self.assertEqual(menu.url, f"/model/{page.name_slugified}")

    def test_copy_page(self):
        View = self.env["ir.ui.view"]
        Page = self.env["website.page"]
        Menu = self.env["website.menu"]
        self.specific_view = View.create(
            {
                "name": "Base",
                "type": "qweb",
                "arch": "<div>Specific View</div>",
                "key": "test.specific_view",
            }
        )
        self.page_specific = Page.create(
            {
                "view_id": self.specific_view.id,
                "url": "/page_specific",
                "website_id": 1,
            }
        )
        self.page_specific_menu = Menu.create(
            {
                "name": "Page Specific menu",
                "page_id": self.page_specific.id,
                "website_id": 1,
            }
        )
        total_pages = Page.search_count([])
        total_menus = Menu.search_count([])
        Page.clone_page(self.page_specific.id, clone_menu=True)
        cloned_page = Page.search([("url", "=", "/page_specific-1")])
        cloned_menu = Menu.search([("url", "=", "/page_specific-1")])
        self.assertEqual(
            len(cloned_page),
            1,
            "A page with an URL /page_specific-1 should've been created",
        )
        self.assertEqual(
            Page.search_count([]), total_pages + 1, "Should have cloned the page"
        )
        self.assertEqual(
            len(cloned_menu),
            1,
            "A specific page (with a menu) being cloned should have it's menu also cloned",
        )
        self.assertEqual(
            cloned_menu.page_id,
            cloned_page,
            "The new cloned menu and the new cloned page should be linked (m2o)",
        )
        self.assertEqual(
            Menu.search_count([]), total_menus + 1, "Should have cloned the page menu"
        )
        Page.clone_page(self.page_specific.id, page_name="about-us", clone_menu=True)
        cloned_page_about_us = Page.search([("url", "=", "/about-us")])
        cloned_menu_about_us = Menu.search([("url", "=", "/about-us")])
        self.assertEqual(
            len(cloned_page_about_us),
            1,
            "A page with an URL /about-us should've been created",
        )
        self.assertEqual(
            len(cloned_menu_about_us),
            1,
            "A specific page (with a menu) being cloned should have it's menu also cloned",
        )
        self.assertEqual(
            cloned_menu_about_us.page_id,
            cloned_page_about_us,
            "The new cloned menu and the new cloned page should be linked (m2o)",
        )
        self.assertEqual(
            Menu.search_count([]), total_menus + 2, "Should have cloned the page menu"
        )

        total_pages = Page.search_count([])
        total_menus = Menu.search_count([])

        Page.clone_page(self.page_1.id, clone_menu=True)
        cloned_generic_page = Page.search(
            [
                ("url", "=", "/page_1"),
                ("id", "!=", self.page_1.id),
                ("website_id", "!=", False),
            ]
        )
        self.assertEqual(
            len(cloned_generic_page),
            1,
            "A generic page being cloned should create a specific one for the current website",
        )
        self.assertEqual(
            cloned_generic_page.url,
            self.page_1.url,
            "The URL of the cloned specific page should be the same as the generic page it has been cloned from",
        )
        self.assertEqual(
            Page.search_count([]),
            total_pages + 1,
            "Should have cloned the generic page as a specific page for this website",
        )
        self.assertEqual(
            Menu.search_count([]),
            total_menus,
            "It should not create a new menu as the generic page's menu belong to another website",
        )
        Page.clone_page(self.page_1.id, clone_menu=True)
        cloned_generic_page_2 = Page.search(
            [("url", "=", "/page_1-1"), ("id", "!=", self.page_1.id)]
        )
        self.assertEqual(
            len(cloned_generic_page_2),
            1,
            "A generic page being cloned should create a specific page with a new URL if there is already a specific page with that URL",
        )

    def test_cow_page(self):
        Menu = self.env["website.menu"]
        Page = self.env["website.page"]
        View = self.env["ir.ui.view"]

        total_pages = Page.search_count([])
        total_menus = Menu.search_count([])
        total_views = View.search_count([])
        self.page_1.write({"arch": "<div>modified base content</div>"})
        self.assertEqual(total_pages, Page.search_count([]))
        self.assertEqual(total_menus, Menu.search_count([]))
        self.assertEqual(total_views, View.search_count([]))

        self.page_1.with_context(website_id=1).write(
            {"arch": "<div>website 1 content</div>"}
        )

        self.assertEqual(total_pages + 1, Page.search_count([]))
        self.assertEqual(total_menus, Menu.search_count([]))
        self.assertEqual(total_views + 2, View.search_count([]))

        self.assertEqual(self.page_1.arch, "<div>modified base content</div>")
        self.assertEqual(bool(self.page_1.website_id), False)

        new_page = Page.search([("url", "=", "/page_1"), ("id", "!=", self.page_1.id)])
        self.assertEqual(new_page.website_id.id, 1)
        self.assertEqual(new_page.view_id.inherit_children_ids[0].website_id.id, 1)
        self.assertEqual(new_page.arch, "<div>website 1 content</div>")

    def test_cow_extension_view(self):
        Menu = self.env["website.menu"]
        Page = self.env["website.page"]
        View = self.env["ir.ui.view"]

        total_pages = Page.search_count([])
        total_menus = Menu.search_count([])
        total_views = View.search_count([])
        self.extension_view.write({"arch": "<div>modified extension content</div>"})
        self.assertEqual(
            self.extension_view.arch, "<div>modified extension content</div>"
        )
        self.assertEqual(total_pages, Page.search_count([]))
        self.assertEqual(total_menus, Menu.search_count([]))
        self.assertEqual(total_views, View.search_count([]))

        self.extension_view.with_context(website_id=1).write(
            {"arch": "<div>website 1 content</div>"}
        )
        self.assertEqual(total_pages, Page.search_count([]))
        self.assertEqual(total_menus, Menu.search_count([]))
        self.assertEqual(total_views + 1, View.search_count([]))

        self.assertEqual(
            self.extension_view.arch, "<div>modified extension content</div>"
        )
        self.assertEqual(bool(self.page_1.website_id), False)

        new_view = View.search([("name", "=", "Extension"), ("website_id", "=", 1)])
        self.assertEqual(new_view.arch, "<div>website 1 content</div>")
        self.assertEqual(new_view.website_id.id, 1)

    def test_cow_generic_parent_preserves_specific_child_page(self):
        Page = self.env["website.page"]
        View = self.env["ir.ui.view"]

        self.extension_view.with_context(website_id=1).write(
            {"arch": "<div>website 1 extension content</div>"}
        )
        specific_extension_view = View.search(
            [("name", "=", "Extension"), ("website_id", "=", 1)]
        )
        self.assertTrue(specific_extension_view)

        Page.create(
            {
                "name": "Child page on specific extension view",
                "view_id": specific_extension_view.id,
                "website_id": 1,
                "url": "/child_page_on_extension",
            }
        )

        self.base_view.with_context(website_id=1).write(
            {"arch": "<div>website 1 base content</div>"}
        )

        self.assertFalse(
            specific_extension_view.exists(),
            "the original specific extension view is expected to be replaced",
        )
        surviving_page = Page.search(
            [("name", "=", "Child page on specific extension view")]
        )
        self.assertTrue(surviving_page, "the page must not be lost")
        self.assertTrue(
            surviving_page.view_id.exists(),
            "the surviving page's view_id must be a real, valid view",
        )
        self.assertEqual(surviving_page.view_id.website_id.id, 1)

    def test_cou_page_backend(self):
        Page = self.env["website.page"]
        View = self.env["ir.ui.view"]

        self.extension_view.unlink()

        self.page_1.unlink()
        self.assertEqual(Page.search_count([("url", "=", "/page_1")]), 0)
        self.assertEqual(View.search_count([("name", "in", ("Base", "Extension"))]), 0)

    def test_cou_page_frontend(self):
        Page = self.env["website.page"]
        View = self.env["ir.ui.view"]
        Website = self.env["website"]

        self.env["website"].create(
            {
                "name": "My Second Website",
            }
        )

        self.extension_view.unlink()

        website_id = 1
        self.page_1.with_context(website_id=website_id).unlink()

        self.assertEqual(bool(self.base_view.exists()), False)
        self.assertEqual(bool(self.page_1.exists()), False)
        self.assertEqual(bool(self.page_1_menu.exists()), False)

        pages = Page.search([("url", "=", "/page_1")])
        self.assertEqual(
            len(pages),
            Website.search_count([]) - 1,
            "A specific page for every website should have been created, except for the one from where we deleted the generic one.",
        )
        self.assertTrue(
            website_id not in pages.mapped("website_id").ids,
            "The website from which we deleted the generic page should not have a specific one.",
        )
        self.assertTrue(
            website_id
            not in View.search([("name", "in", ("Base", "Extension"))])
            .mapped("website_id")
            .ids,
            "Same for views",
        )


@tagged("-at_install", "post_install")
class WithContext(HttpCase):
    def test_scheduled_page_becomes_visible_without_a_write(self):
        with freeze_time("2026-09-13 12:00:00") as clock:
            self.page.date_publish = "2026-09-14 12:00:00"
            self.assertEqual(self.url_open(self.page.url).status_code, 404)
            clock.move_to("2026-09-14 12:00:00")
            response = self.url_open(self.page.url)
            _logger.debug(
                "Scheduled page after clock advance without a write: status=%s",
                response.status_code,
            )
            self.assertEqual(response.status_code, 200)

    @freeze_time("2026-09-13 12:00:00")
    def test_scheduled_page_is_hidden_from_http_and_autocomplete(self):
        self.page.write(
            {"date_publish": "2026-09-14 12:00:00", "website_indexed": True}
        )
        response = self.url_open(self.page.url)
        _logger.debug("Scheduled page HTTP challenge: status=%s", response.status_code)
        self.assertEqual(response.status_code, 404)
        response = self.url_open(
            "/website/snippet/autocomplete",
            data=json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "call",
                    "id": 1,
                    "params": {
                        "search_type": "pages",
                        "term": "page_1",
                        "options": {"displayDescription": True, "allowFuzzy": False},
                    },
                }
            ),
            headers={"Content-Type": "application/json"},
        )
        result = response.json()["result"]
        _logger.debug("Scheduled page autocomplete HTTP challenge: %s", result)
        self.assertEqual(result["results_count"], 0)
        self.page.date_publish = "2026-09-13 12:00:00"
        self.assertEqual(self.url_open(self.page.url).status_code, 200)

    def setUp(self):
        super().setUp()
        Page = self.env["website.page"]
        View = self.env["ir.ui.view"]
        self.base_view = View.create(
            {
                "name": "Base",
                "type": "qweb",
                "arch": """<t name="Homepage" t-name="test.base_view">
                        <t t-call="website.layout">
                            I am a generic page
                        </t>
                    </t>""",
                "key": "test.base_view",
            }
        )
        self.page = Page.create(
            {
                "view_id": self.base_view.id,
                "url": "/page_1",
                "is_published": True,
            }
        )

    def test_unpublished_page(self):
        specific_page = self.page.copy(
            {"website_id": self.env["website"].get_current_website().id}
        )
        specific_page.write(
            {
                "is_published": False,
                "arch": self.page.arch.replace(
                    "I am a generic page", "I am a specific page"
                ),
            }
        )

        self.authenticate(None, None)
        r = self.url_open(specific_page.url)
        self.assertEqual(
            r.status_code,
            404,
            "Restricted users should see a 404 and not the generic one as we unpublished the specific one",
        )

        self.authenticate("admin", "admin")
        r = self.url_open(specific_page.url)
        self.assertEqual(
            r.status_code, 200, "Admin should see the specific unpublished page"
        )
        self.assertEqual(
            "I am a specific page" in r.text,
            True,
            "Admin should see the specific unpublished page",
        )

    @mute_logger("odoo.addons.rpc.controllers.xmlrpc")
    def test_search(self):
        dbname = common.get_db_name()
        admin_uid = self.env.ref("base.user_admin").id
        website = self.env["website"].get_current_website()

        robot = self.xmlrpc_object.execute(
            dbname, admin_uid, "admin", "website", "search_pages", [website.id], "info"
        )
        self.assertIn({"loc": "/website/info"}, robot)

        pages = self.xmlrpc_object.execute(
            dbname, admin_uid, "admin", "website", "search_pages", [website.id], "page"
        )
        self.assertIn(
            "/page_1",
            [p["loc"] for p in pages],
        )

    @mute_logger("odoo.http")
    def test_03_error_page_debug(self):
        with MockRequest(self.env, website=self.env["website"].browse(1)):
            self.base_view.arch = self.base_view.arch.replace(
                "I am a generic page", '<t t-out="15/0"/>'
            )

            r = self.url_open(self.page.url)
            self.assertEqual(r.status_code, 500, "15/0 raise a 500 error page")
            self.assertNotIn(
                "ZeroDivisionError: division by zero",
                r.text,
                "Error should not be shown when not in debug.",
            )

            r = self.url_open(self.page.url + "?debug=1")
            self.assertEqual(r.status_code, 500, "15/0 raise a 500 error page (2)")
            self.assertIn(
                "ZeroDivisionError: division by zero",
                r.text,
                "Error should be shown in debug.",
            )

            r = self.url_open(self.page.url)
            self.assertEqual(r.status_code, 500, "15/0 raise a 500 error page (2)")
            self.assertIn(
                "ZeroDivisionError: division by zero",
                r.text,
                "Error should be shown in debug.",
            )

    def test_04_visitor_no_session(self):
        store = root.session_store
        with (
            patch.object(store, "save", wraps=store.save) as session_save,
            MockRequest(self.env, website=self.env["website"].browse(1)),
        ):
            self.url_open(self.page.url).raise_for_status()
            self.assertLessEqual(
                session_save.call_count,
                1,
                "a page view must persist at most one (CSRF) session",
            )
            for call in session_save.call_args_list:
                self.assertFalse(
                    call.args[0].uid,
                    "an anonymous page view must not authenticate the session",
                )

            session_save.reset_mock()
            self.url_open(self.page.url).raise_for_status()
            session_save.assert_not_called()

    def test_05_homepage_not_slash_url(self):
        website = self.env["website"].browse([1])
        website.write(
            {
                "homepage_url": self.page.url,
                "domain": self.base_url(),
            }
        )
        assert self.page.url != "/"

        r = self.url_open("/")
        r.raise_for_status()
        self.assertEqual(
            r.status_code,
            200,
            "There should be no crash when a public user is accessing `/` which is rerouting to another page with a different URL.",
        )
        root_html = html.fromstring(r.content)
        canonical_url = root_html.xpath('//link[@rel="canonical"]')[0].attrib["href"]
        self.assertIn(canonical_url, [f"{website.domain}/", f"{website.domain}/page_1"])

    def test_opengraph_image_with_absolute_url(self):
        base_url = self.base_url()
        with MockRequest(self.env, website=self.env["website"].browse(1)):
            self.page.website_meta_og_img = "http://wrong.example.com/favicon.ico"
            r = self.url_open(self.page.url)
            self.assertEqual(r.status_code, 200)
            self.assertIn(f'"og:image" content="{base_url}/favicon.ico"', r.text)
            self.assertIn(f'"twitter:image" content="{base_url}/favicon.ico"', r.text)

            self.page.website_meta_og_img = "/logo"
            r = self.url_open(self.page.url)
            self.assertEqual(r.status_code, 200)
            self.assertIn(f'"og:image" content="{base_url}/logo"', r.text)
            self.assertIn(f'"twitter:image" content="{base_url}/logo"', r.text)

    def test_website_homepage_url_change(self):
        website = self.env["website"].browse([1])
        self.assertFalse(website.homepage_url)

        test_page = (
            self.env["website.page"]
            .with_context(website_id=website.id)
            .create(
                {
                    "name": "HomepageUrlTest",
                    "type": "qweb",
                    "arch": "<div>HomepageUrlTest</div>",
                    "key": "test.homepage_url_test",
                    "url": "/homepage_url_test",
                    "is_published": True,
                    "website_id": website.id,
                }
            )
        )
        self.assertURLEqual(test_page.url, "/homepage_url_test")

        website.write(
            {
                "name": "Test Website",
                "domain": self.base_url(),
                "homepage_url": test_page.url,
            }
        )
        home_url_full = website.domain + "/"
        r = self.url_open("/")
        self.assertEqual(r.status_code, 200)
        self.assertURLEqual(r.url, home_url_full)
        self.assertIn(b"HomepageUrlTest", r.content)

        with MockRequest(self.env, website=website):
            test_page.url = "/url-changed"

        self.assertEqual(website.homepage_url, "/url-changed")
        r = self.url_open("/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.url,
            home_url_full,
            """URL should still be '/', note that if this
            `assert` fail, the loaded URL will probably be the first available
            menu different from '/', see homepage controller.""",
        )
        self.assertIn(b"HomepageUrlTest", r.content)

        with MockRequest(self.env, website=website):
            test_page.url = "/url-changed_two"
        self.assertEqual(website.homepage_url, "/url-changed-two")
        r = self.url_open("/")
        self.assertEqual(r.status_code, 200)
        self.assertURLEqual(r.url, home_url_full)
        self.assertIn(b"HomepageUrlTest", r.content)

    def test_06_homepage_url(self):
        website = self.env["website"].browse([1])
        website.write(
            {
                "name": "Test Website",
                "domain": self.base_url(),
                "homepage_url": False,
            }
        )
        contactus_url = "/contactus"
        contactus_url_full = website.domain + contactus_url
        contactus_content = b'content="Contact Us | Test Website"'
        contactus_menu = self.env["website.menu"].search(
            [
                ("website_id", "=", website.id),
                ("url", "=", contactus_url),
            ],
            limit=1,
        )
        home_url = "/"
        home_url_full = website.domain + home_url
        home_content = b'content="Home | Test Website"'
        home_menu = self.env["website.menu"].search(
            [
                ("website_id", "=", website.id),
                ("url", "=", home_url),
            ],
            limit=1,
        )

        r = self.url_open(home_url)
        self.assertEqual(r.status_code, 200)
        self.assertURLEqual(r.url, home_url_full)
        self.assertIn(home_content, r.content)

        website.homepage_url = contactus_url
        r = self.url_open(home_url)
        self.assertEqual(r.status_code, 200)
        self.assertURLEqual(r.url, home_url_full)
        self.assertIn(contactus_content, r.content)

        contactus_menu.sequence = 2
        website.homepage_url = False
        r = self.url_open(home_url)
        self.assertEqual(r.status_code, 200)
        self.assertURLEqual(r.url, home_url_full)
        self.assertIn(home_content, r.content)

        website.homepage_url = "/unexisting"
        home_menu.sequence = 1
        self.assertEqual(website.menu_id.child_id[0], home_menu)
        self.assertEqual(website.menu_id.child_id[1], contactus_menu)
        r = self.url_open(website.homepage_url)
        self.assertEqual(r.status_code, 404, "The website homepage_url should be a 404")
        r = self.url_open(home_url)
        self.assertEqual(r.status_code, 200)
        self.assertURLEqual(
            r.url,
            contactus_url_full,
            "Menu fallback should be a redirect, not a reroute",
        )
        self.assertIn(contactus_content, r.content)

        self.env["website.page"].search([("url", "=", home_url)]).unlink()
        website.homepage_url = False
        r = self.url_open(home_url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.history[0].status_code, 303)
        self.assertURLEqual(r.url, contactus_url_full)
        self.assertIn(contactus_content, r.content)

        website.homepage_url = "/website/info"
        r = self.url_open(home_url)
        self.assertEqual(r.status_code, 200)
        self.assertURLEqual(r.url, home_url_full)
        self.assertIn(b"o_website_info", r.content)

        website.homepage_url = "/my"
        r = self.url_open(home_url)
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(b"<title>My Portal", r.content)
        self.assertIn(b"<title>Contact Us", r.content)
        self.assertURLEqual(r.url, contactus_url_full)
        self.assertEqual(r.history[0].status_code, 303)
        self.env["website.menu"].create(
            {
                "name": "/my first menu",
                "website_id": website.id,
                "parent_id": website.menu_id.id,
                "url": "/my",
                "sequence": 1,
            }
        )
        r = self.url_open(home_url)
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(b"<title>My Portal", r.content)
        self.assertIn(b"<title>Login", r.content)
        self.assertIn("/web/login?redirect", r.url)
        self.assertEqual(r.history[0].status_code, 303)

    def test_07_alternatives(self):
        website = self.env.ref("website.default_website")
        lang_fr = self.env["res.lang"]._activate_lang("fr_FR")
        lang_fr.write({"url_code": "fr"})
        website.language_ids = self.env.ref("base.lang_en") + lang_fr
        website.default_lang_id = self.env.ref("base.lang_en")

        with self.subTest(url="/page_1"):
            res = self.url_open("/page_1")
            res.raise_for_status()

            root_html = html.fromstring(res.content)
            canonical_url = root_html.xpath('//link[@rel="canonical"]')[0].attrib[
                "href"
            ]
            alternate_en_url = root_html.xpath(
                '//link[@rel="alternate"][@hreflang="en"]'
            )[0].attrib["href"]
            alternate_fr_url = root_html.xpath(
                '//link[@rel="alternate"][@hreflang="fr"]'
            )[0].attrib["href"]

            self.assertEqual(canonical_url, f"{self.base_url()}/page_1")
            self.assertEqual(alternate_en_url, f"{self.base_url()}/page_1")
            self.assertEqual(alternate_fr_url, f"{self.base_url()}/fr/page_1")

        with self.subTest(url="/fr/page_1"):
            res = self.url_open("/fr/page_1")
            res.raise_for_status()

            root_html = html.fromstring(res.content)
            canonical_url = root_html.xpath('//link[@rel="canonical"]')[0].attrib[
                "href"
            ]
            alternate_en_url = root_html.xpath(
                '//link[@rel="alternate"][@hreflang="en"]'
            )[0].attrib["href"]
            alternate_fr_url = root_html.xpath(
                '//link[@rel="alternate"][@hreflang="fr"]'
            )[0].attrib["href"]

            self.assertEqual(canonical_url, f"{self.base_url()}/fr/page_1")
            self.assertEqual(alternate_en_url, f"{self.base_url()}/page_1")
            self.assertEqual(alternate_fr_url, f"{self.base_url()}/fr/page_1")

    def test_alternate_hreflang(self):
        website = self.env["website"].get_current_website() or self.env[
            "website"
        ].browse(1)
        lang_en = self.env.ref("base.lang_en")
        ResLang = self.env["res.lang"].with_context(website_id=website.id)
        lang_fr = ResLang._activate_lang("fr_FR")
        with MockRequest(self.env, website=website):
            website.language_ids = [Command.set((lang_en + lang_fr).ids)]
            langs = ResLang._get_frontend()
            self.assertEqual(langs["en_US"]["hreflang"], "en")
            self.assertEqual(langs["fr_FR"]["hreflang"], "fr")
            lang_be = ResLang._activate_lang("fr_BE")
            lang_ca = ResLang._activate_lang("fr_CA")
            website.language_ids = [
                Command.set((lang_en + lang_fr + lang_be + lang_ca).ids)
            ]
            langs = ResLang._get_frontend()
            self.assertEqual(langs["en_US"]["hreflang"], "en")
            self.assertEqual(langs["fr_FR"]["hreflang"], "fr-fr")
            self.assertEqual(langs["fr_BE"]["hreflang"], "fr")
            self.assertEqual(langs["fr_CA"]["hreflang"], "fr-ca")
            lang_es = ResLang._activate_lang("es_ES")
            lang_419 = ResLang._activate_lang("es_419")
            website.language_ids = [Command.set((lang_en + lang_es + lang_419).ids)]
            langs = ResLang._get_frontend()
            self.assertEqual(langs["en_US"]["hreflang"], "en")
            self.assertEqual(langs["es_ES"]["hreflang"], "es-es")
            self.assertEqual(langs["es_419"]["hreflang"], "es")

    def test_07_not_authorized(self):
        specific_page = self.page.copy(
            {"website_id": self.env["website"].get_current_website().id}
        )
        specific_page.write(
            {
                "arch": self.page.arch.replace(
                    "I am a generic page",
                    "I am a specific page not available for visitors",
                ),
                "is_published": True,
                "visibility": "restricted_group",
                "group_ids": [Command.link(self.ref("website.group_website_designer"))],
            }
        )
        self.authenticate(None, None)
        r = self.url_open("/page_1")
        self.assertEqual(403, r.status_code, "Must fail with 403")
        self.assertTrue('id="wrap"' in r.text, "Must be rendered as a website page")

    def test_page_url_case_insensitive_match(self):
        r = self.url_open("/page_1")
        self.assertEqual(r.status_code, 200, "Reaching page URL, common case")
        r2 = self.url_open("/Page_1", allow_redirects=False)
        self.assertEqual(
            r2.status_code,
            303,
            "URL exists only in different casing, should redirect to it",
        )
        self.assertURLEqual(
            r2.headers.get("Location"), "/page_1", "Should redirect /Page_1 to /page_1"
        )

    def test_page_generic_diverged_url(self):
        Page = self.env["website.page"]
        specific_arch = "<div>website 1 content</div>"
        generic_page = self.page
        generic_page.arch = "<div>content</div>"

        specific_page = Page.search(
            [("url", "=", self.page.url), ("website_id", "=", 1)]
        )
        self.assertFalse(
            specific_page, "For this test, the specific page should not exist yet"
        )

        generic_page.view_id.with_context(website_id=1).save(
            specific_arch, xpath="/div"
        )
        specific_page = Page.search(
            [("url", "=", self.page.url), ("website_id", "=", 1)]
        )
        self.assertEqual(specific_page.arch.replace("\n", ""), specific_arch)
        self.assertEqual(generic_page.arch, "<div>content</div>")
        specific_page.url = "/page_1_specific"
        r = self.url_open(specific_page.url)
        self.assertEqual(r.status_code, 200, "Specific should be reachable")
        r = self.url_open(generic_page.url)
        self.assertEqual(r.status_code, 404, "Generic should not be reachable")


@tagged("-at_install", "post_install")
class TestNewPage(common.TransactionCase):
    def test_new_page_used_key(self):
        website = self.env.ref("website.default_website")
        controller = Website()
        with MockRequest(self.env, website=website):
            controller.pagenew(path="snippets")
        pages = self.env["website.page"].search([("url", "=", "/snippets")])
        self.assertEqual(len(pages), 1, "Exactly one page should be at /snippets.")
        self.assertNotEqual(
            pages.key, "website.snippets", "Page's key cannot be website.snippets."
        )


@tagged("-at_install", "post_install")
class TestErrorPageFallback(HttpCase):
    EP = "/website/translations"

    def test_designer_gets_the_same_fallback_as_a_visitor(self):
        page = self.env["website.page"].create(
            {
                "name": "Fallback probe",
                "url": self.EP,
                "is_published": True,
                "type": "qweb",
                "key": "website.test_error_page_fallback",
                "arch": '<t t-name="website.test_error_page_fallback">'
                '<t t-call="website.layout">FALLBACKBODY</t></t>',
            }
        )
        self.addCleanup(page.unlink)
        self.env.flush_all()
        self.env.registry.clear_cache()

        def _dispatch(endpoint):
            raise werkzeug.exceptions.NotFound

        self.patch(self.registry["ir.http"], "_dispatch", _dispatch)

        anonymous = self.url_open(self.EP, allow_redirects=False)
        self.assertEqual(anonymous.status_code, 200)
        self.assertIn("FALLBACKBODY", anonymous.text)

        self.authenticate("admin", "admin")
        self.assertTrue(
            self.env.ref("base.user_admin").has_group("website.group_website_designer"),
            "the premise: admin is a website designer",
        )
        designer = self.url_open(self.EP, allow_redirects=False)
        self.assertEqual(designer.status_code, 200)
        self.assertIn("FALLBACKBODY", designer.text)

    def test_password_protected_page_still_gates(self):
        page = self.env["website.page"].create(
            {
                "name": "Secret",
                "url": "/test-protected-page",
                "is_published": True,
                "type": "qweb",
                "key": "website.test_protected_page",
                "arch": '<t t-name="website.test_protected_page">'
                '<t t-call="website.layout">TOPSECRETBODY</t></t>',
            }
        )
        self.addCleanup(page.unlink)
        page.view_id.write({"visibility": "password", "visibility_password": "hunter2"})
        self.env.flush_all()
        self.env.registry.clear_cache()

        response = self.url_open("/test-protected-page", allow_redirects=False)
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("TOPSECRETBODY", response.text)
        self.assertIn("visibility_password", response.text)


@tagged("-at_install", "post_install")
class TestMostSpecificPagesScan(common.TransactionCase):
    """`_get_most_specific_pages` counts keys, and only the keys it will read.

    It sits behind site search, the sitemap, `is_page_existing` and the backend
    page list, where the candidate set is a handful of rows and the table is the
    whole site. Counting every page's key there made each of those O(site).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env.ref("website.default_website")
        template = cls.env.ref("website.default_page")
        pages = []
        for index in range(12):
            view = template.copy(
                {"website_id": cls.website.id, "key": f"website.scan_probe_{index}"}
            )
            pages.append(
                {
                    # Distinct names on purpose: a fixture whose rows sort the
                    # same ascending and descending cannot witness an order bug.
                    "name": f"Scan probe {index:02d}",
                    "url": f"/scan-probe-{index}",
                    "view_id": view.id,
                    "website_id": cls.website.id,
                    "is_published": True,
                }
            )
        cls.pages = cls.env["website.page"].create(pages)
        cls.env.flush_all()

    def _fetched_keys(self, records):
        """How many rows the key-count query brings back for `records`."""
        seen = []
        original = type(self.env["website.page"]).search_fetch

        def counting_search_fetch(model, domain, field_names, *args, **kwargs):
            result = original(model, domain, field_names, *args, **kwargs)
            if field_names == ["key"]:
                seen.append(len(result))
            return result

        with patch.object(
            type(self.env["website.page"]), "search_fetch", counting_search_fetch
        ):
            kept = records._get_most_specific_pages()
        return kept, seen

    def test_the_key_count_is_bounded_by_the_candidate_set(self):
        one = self.pages[:1].with_context(website_id=self.website.id)
        kept, fetched = self._fetched_keys(one)
        self.assertEqual(kept, one)
        self.assertEqual(
            fetched,
            [1],
            "a one-page candidate set must not read every key on the site",
        )

    def test_a_generic_page_shadowed_by_a_specific_one_is_still_dropped(self):
        generic_view = self.env["ir.ui.view"].create(
            {
                "name": "Shadowed",
                "type": "qweb",
                "key": "website.shadowed_page",
                "arch": '<t t-name="website.shadowed_page">'
                '<t t-call="website.layout">SHADOWED</t></t>',
            }
        )
        generic = self.env["website.page"].create(
            {"url": "/shadowed", "view_id": generic_view.id, "is_published": True}
        )
        specific = self.env["website.page"].create(
            {
                "url": "/shadowed",
                "view_id": generic_view.copy(
                    {"website_id": self.website.id, "key": "website.shadowed_page"}
                ).id,
                "website_id": self.website.id,
                "is_published": True,
            }
        )
        self.env.flush_all()
        candidates = (generic | specific).with_context(website_id=self.website.id)
        self.assertEqual(candidates._get_most_specific_pages(), specific)

    def test_an_unshadowed_generic_page_is_kept(self):
        generic_view = self.env["ir.ui.view"].create(
            {
                "name": "Lonely",
                "type": "qweb",
                "key": "website.lonely_page",
                "arch": '<t t-name="website.lonely_page">'
                '<t t-call="website.layout">LONELY</t></t>',
            }
        )
        generic = self.env["website.page"].create(
            {"url": "/lonely", "view_id": generic_view.id, "is_published": True}
        )
        self.env.flush_all()
        candidates = generic.with_context(website_id=self.website.id)
        self.assertEqual(candidates._get_most_specific_pages(), generic)

    def test_an_empty_candidate_set_reads_nothing(self):
        empty = self.env["website.page"].with_context(website_id=self.website.id)
        kept, _fetched = self._fetched_keys(empty)
        self.assertFalse(kept)

    def test_the_caller_s_order_survives_the_dedup(self):
        """The url sort inside the dedup decides which page wins, not the output
        order. Returning `browse(ids)` handed every caller its pages in url
        order instead, so site search ignored the requested sort."""
        candidates = self.pages.with_context(website_id=self.website.id)
        for order in ("name asc", "name desc"):
            with self.subTest(order=order):
                asked = (
                    self.env["website.page"]
                    .sudo()
                    .search([("id", "in", self.pages.ids)], order=order)
                )
                kept = asked.with_context(
                    website_id=self.website.id
                )._get_most_specific_pages()
                self.assertEqual(
                    kept.ids,
                    [i for i in asked.ids if i in set(kept.ids)],
                    "the dedup must filter, not re-sort",
                )
        self.assertNotEqual(
            self.env["website.page"]
            .sudo()
            .search([("id", "in", self.pages.ids)], order="name asc")
            .ids,
            self.env["website.page"]
            .sudo()
            .search([("id", "in", self.pages.ids)], order="name desc")
            .ids,
            "the fixture must be able to tell the two orders apart",
        )
        self.assertTrue(candidates)


@tagged("-at_install", "post_install")
class TestShadowedPageIsReachable(common.TransactionCase):
    """A url carrying both a generic page and this website's override must not
    lose both to a SQL limit applied before the dedup."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env.ref("website.default_website")
        key = "website.shadowed_reachable"
        generic_view = cls.env["ir.ui.view"].create(
            {
                "name": "Shadowed reachable",
                "type": "qweb",
                "key": key,
                "arch": '<t t-name="%s"><t t-call="website.layout">GHOST</t></t>' % key,
            }
        )
        cls.generic = cls.env["website.page"].create(
            {"url": "/ghost-page", "view_id": generic_view.id, "is_published": True}
        )
        cls.specific = cls.env["website.page"].create(
            {
                "url": "/ghost-page",
                "website_id": cls.website.id,
                "view_id": generic_view.copy(
                    {"website_id": cls.website.id, "key": key}
                ).id,
                "is_published": True,
            }
        )
        cls.env.flush_all()

    def _lookup(self, limit=None):
        return self.env["website"]._get_website_pages(
            domain=[("url", "=", "/ghost-page"), ("view_id", "!=", False)], limit=limit
        )

    def test_a_limit_of_one_still_finds_the_override(self):
        self.assertEqual(self._lookup(limit=1), self.specific)

    def test_the_limit_agrees_with_no_limit(self):
        self.assertEqual(self._lookup(limit=1), self._lookup())

    def test_a_limit_still_truncates(self):
        self.assertEqual(len(self.env["website"]._get_website_pages(limit=2)), 2)

    def test_the_page_is_reported_as_existing(self):
        with MockRequest(self.env, website=self.website):
            self.assertTrue(self.env["website"].is_page_existing("/ghost-page"))


@tagged("-at_install", "post_install")
class TestSearchFetchScalesWithMatches(common.TransactionCase):
    """A public search must cost what it matches, not what the site contains.

    `_search_fetch` used to fetch every page the base domain admits and filter
    it with `filtered_domain`, which reads `arch_db` -- the whole stored html of
    every page -- for a search matching a handful. This pins the property rather
    than a timing: the candidate set the dedup is handed must not grow with the
    table.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env.ref("website.default_website")
        template = cls.env.ref("website.default_page")
        cls.needle = "zqneedle"
        pages = []
        for index in range(40):
            view = template.copy(
                {"website_id": cls.website.id, "key": f"website.scale_probe_{index}"}
            )
            marker = cls.needle if index < 3 else "filler"
            view.with_context(no_cow=True).write(
                {
                    "arch": '<t t-name="website.scale_probe_%d">'
                    '<t t-call="website.layout"><div id="wrap">'
                    "<p>%s body %d</p></div></t></t>" % (index, marker, index),
                }
            )
            pages.append(
                {
                    "name": f"Scale probe {index:02d}",
                    "url": f"/scale-probe-{index}",
                    "view_id": view.id,
                    "website_id": cls.website.id,
                    "is_published": True,
                }
            )
        cls.pages = cls.env["website.page"].create(pages)
        cls.env.flush_all()

    def _candidates_handed_to_the_dedup(self, term):
        sizes = []
        original = type(self.env["website.page"])._get_most_specific_pages

        def counting(records):
            sizes.append(len(records))
            return original(records)

        with patch.object(
            type(self.env["website.page"]), "_get_most_specific_pages", counting
        ):
            options = {
                "displayDescription": True,
                "displayDetail": False,
                "displayExtraDetail": False,
                "displayExtraLink": False,
                "displayImage": False,
                "allowFuzzy": False,
            }
            detail = self.env["website.page"]._search_get_detail(
                self.website, "name asc", options
            )
            results, count = self.env["website.page"]._search_fetch(
                detail, term, 5, "name asc"
            )
        return results, count, sizes

    def test_the_candidate_set_is_bounded_by_the_matches(self):
        total = self.env["website.page"].sudo().search_count([])
        _results, count, sizes = self._candidates_handed_to_the_dedup(self.needle)
        self.assertEqual(count, 3, "the fixture must match exactly three pages")
        self.assertTrue(sizes, "the dedup must still run")
        self.assertLess(
            max(sizes),
            total,
            "the dedup must not be handed the whole page table for a 3-page match",
        )
        self.assertLessEqual(
            max(sizes),
            10,
            "the candidate set must be the matching url groups, not the site",
        )

    def test_a_search_matching_nothing_hands_over_nothing(self):
        _results, count, sizes = self._candidates_handed_to_the_dedup("zqabsentterm")
        self.assertEqual(count, 0)
        self.assertEqual(max(sizes, default=0), 0)


@tagged("-at_install", "post_install")
class TestPageRenameRedirects(common.TransactionCase):
    """A page that moves leaves a redirect behind. Moving it back left that
    redirect active, pointing away from where the page now lives -- which made
    the reverse redirect a cycle and the rename impossible to undo."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env.ref("website.default_website")
        cls.page = cls.env["website.page"].create(
            {
                "name": "rename probe",
                "url": "/rename-probe-a",
                "website_id": cls.website.id,
                "view_id": cls.env["ir.ui.view"]
                .create(
                    {
                        "name": "rename probe view",
                        "type": "qweb",
                        "key": "website.rename_probe_view",
                        "arch": '<t t-name="website.rename_probe_view"><div>x</div></t>',
                    }
                )
                .id,
            }
        )

    def _props(self):
        return self.env["website.page.properties"].create(
            {"target_model_id": self.page.id, "website_id": self.website.id}
        )

    def _rewrites(self, url_from):
        return (
            self.env["website.rewrite"]
            .with_context(active_test=False)
            .search([("url_from", "=", url_from)])
        )

    def _move(self, props, url):
        props.write(
            {
                "url": url,
                "redirect_old_url": True,
                "name": "probe redirect",
                "redirect_type": "301",
            }
        )

    def test_a_page_can_be_renamed_back_to_its_previous_url(self):
        props = self._props()
        self._move(props, "/rename-probe-b")
        self._move(props, "/rename-probe-a")
        self.assertEqual(props.url, "/rename-probe-a")

    def test_the_redirect_off_the_new_url_is_archived_not_deleted(self):
        props = self._props()
        self._move(props, "/rename-probe-b")
        stale = self._rewrites("/rename-probe-a")
        self.assertTrue(stale.filtered("active"), "the A -> B redirect starts active")
        self._move(props, "/rename-probe-a")
        self.assertTrue(stale, "the row is kept as history")
        self.assertFalse(
            stale.filtered("active"),
            "a redirect away from where the page now lives must not stay active",
        )

    def test_the_reverse_redirect_is_created(self):
        props = self._props()
        self._move(props, "/rename-probe-b")
        self._move(props, "/rename-probe-a")
        reverse = self._rewrites("/rename-probe-b").filtered("active")
        self.assertEqual(reverse.url_to, "/rename-probe-a")

    def test_an_unrelated_redirect_is_left_alone(self):
        other = self.env["website.rewrite"].create(
            {
                "name": "unrelated",
                "redirect_type": "301",
                "url_from": "/somewhere-else",
                "url_to": "/rename-probe-b",
                "website_id": self.website.id,
            }
        )
        props = self._props()
        self._move(props, "/rename-probe-b")
        self.assertTrue(other.active, "only redirects off the new url are retired")

    def test_a_generic_redirect_is_not_retired_by_one_website(self):
        """Deliberately scoped: a generic rewrite serves every website."""
        generic = self.env["website.rewrite"].create(
            {
                "name": "generic",
                "redirect_type": "301",
                "url_from": "/rename-probe-b",
                "url_to": "/elsewhere",
                "website_id": False,
            }
        )
        props = self._props()
        self._move(props, "/rename-probe-b")
        self.assertTrue(
            generic.active,
            "one website's page moving must not retire another website's redirect",
        )
