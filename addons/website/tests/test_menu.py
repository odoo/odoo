import json
from hashlib import sha256
from unittest.mock import Mock, patch
from urllib.parse import urlsplit

from lxml import html

from odoo.exceptions import AccessError, UserError
from odoo.tests import common

from odoo.addons.http_routing.tests.common import MockRequest


class TestMenu(common.TransactionCase):
    def setUp(self):
        super().setUp()
        self.nb_website = self.env["website"].search_count([])

    def test_01_menu_got_duplicated(self):
        Menu = self.env["website.menu"]
        total_menu_items = Menu.search_count([])

        self.menu_root = Menu.create(
            {
                "name": "Root",
            }
        )

        self.menu_child = Menu.create(
            {
                "name": "Child",
                "parent_id": self.menu_root.id,
            }
        )

        self.assertEqual(
            total_menu_items + self.nb_website * 2,
            Menu.search_count([]),
            "Creating a menu without a website_id should create this menu for every website_id",
        )

    def test_02_menu_count(self):
        Menu = self.env["website.menu"]
        total_menu_items = Menu.search_count([])

        top_menu = self.env["website"].get_current_website().menu_id
        data = [
            {
                "id": "new-1",
                "parent_id": top_menu.id,
                "name": "New Menu Specific 1",
                "url": "/new-specific-1",
                "is_mega_menu": False,
            },
            {
                "id": "new-2",
                "parent_id": top_menu.id,
                "name": "New Menu Specific 2",
                "url": "/new-specific-2",
                "is_mega_menu": False,
            },
        ]
        Menu.save(1, {"data": data, "to_delete": []})

        self.assertEqual(
            total_menu_items + 2,
            Menu.search_count([]),
            "Creating 2 new menus should create only 2 menus records",
        )

    def test_03_default_menu_for_new_website(self):
        Website = self.env["website"]
        Menu = self.env["website.menu"]
        total_menu_items = Menu.search_count([])

        default_menu = self.env.ref("website.main_menu")
        Menu.create(
            {
                "name": "Sub Default Menu",
                "parent_id": default_menu.id,
            }
        )
        self.assertEqual(
            total_menu_items + 1 + self.nb_website,
            Menu.search_count([]),
            "Creating a default child menu should create it as such and copy it on every website",
        )

        total_menus = Menu.search_count([])
        default_tree = Menu.search_count([("id", "child_of", default_menu.id)])
        self.assertGreaterEqual(default_tree, 4)
        Website.create({"name": "new website"})
        self.assertEqual(
            total_menus + default_tree,
            Menu.search_count([]),
            "New website's bootstraping should have duplicate default menu tree (Top/Home/Contactus/Sub Default Menu)",
        )

    def test_04_specific_menu_translation(self):
        IrModuleModule = self.env["ir.module.module"]
        if self.env["website"].search_count([]) == 1:
            self.env["website"].create(
                {
                    "name": "My Website 2",
                    "domain": "",
                    "sequence": 20,
                }
            )

        Menu = self.env["website.menu"]
        existing_menus = Menu.search([])

        default_menu = self.env.ref("website.main_menu")
        template_menu = Menu.create(
            {
                "parent_id": default_menu.id,
                "name": "Menu in english",
                "url": "turlututu",
            }
        )
        new_menus = Menu.search([]) - existing_menus
        specific1, specific2 = new_menus.with_context(lang="fr_FR") - template_menu

        self.env.ref("base.lang_fr").active = True
        template_menu.with_context(lang="fr_FR").name = "Menu en français"
        self.assertEqual(
            specific1.name,
            "Menu in english",
            "Translating template menu does not translate specific menu",
        )

        specific1.name = "Menu in french"

        IrModuleModule._load_module_terms(["website"], ["fr_FR"])
        Menu.invalidate_model(["name"])
        self.assertEqual(
            specific1.name,
            "Menu in french",
            "Load translation without overwriting keep existing translation",
        )
        self.assertEqual(
            specific2.name,
            "Menu en français",
            "Load translation add missing translation from template menu",
        )

        IrModuleModule._load_module_terms(["website"], ["fr_FR"], overwrite=True)
        Menu.invalidate_model(["name"])
        self.assertEqual(
            specific1.name,
            "Menu en français",
            "Load translation with overwriting update existing menu from template",
        )

    def test_05_default_menu_unlink(self):
        Menu = self.env["website.menu"]
        total_menu_items = Menu.search_count([])

        default_menu = self.env.ref("website.main_menu")
        default_menu.child_id[0].unlink()
        self.assertEqual(
            total_menu_items - 1 - self.nb_website,
            Menu.search_count([]),
            "Deleting a default menu item should delete its 'copies' (same URL) from website's menu trees. In this case, the default child menu and its copies on website 1 and website 2",
        )

    def test_06_menu_active(self):
        Menu = self.env["website.menu"]
        website_1 = self.env["website"].browse(1)
        menu = Menu.create(
            {
                "name": "Page Specific menu",
                "url": "/contactus",
                "website_id": website_1.id,
            }
        )

        def urlsplit_mock(s):
            if isinstance(s, Mock):
                return urlsplit(self.request_url_mock)
            return urlsplit(s)

        def test_full_case(a_menu):
            url = a_menu.url
            self.request_url_mock = "http://localhost:8069" + url
            with (
                MockRequest(self.env, website=website_1),
                patch(
                    "odoo.addons.website.models.website_menu.urlsplit",
                    new=urlsplit_mock,
                ),
            ):
                self.assertTrue(
                    a_menu._is_active(), "Same path, no domain, no qs, should match"
                )
                a_menu.url = f"{url}#anchor"
                self.assertTrue(
                    a_menu._is_active(),
                    "Same path, no domain, no qs, should match (anchor should be ignored)",
                )
                a_menu.url = f"{url}?qs=1"
                self.assertFalse(
                    a_menu._is_active(),
                    "Same path, no domain, qs mismatch, should not match",
                )
                self.request_url_mock = f"http://localhost:8069{url}?qs=2"
                self.assertFalse(
                    a_menu._is_active(),
                    "Same path, no domain, qs mismatch (not the same val), should not match",
                )
                self.request_url_mock = f"http://localhost:8069{url}?qs=1"
                self.assertTrue(
                    a_menu._is_active(), "Same path, no domain, qs match, should match"
                )
                self.request_url_mock = f"http://localhost:8069{url}?qs=1&qs_extra=1"
                self.assertTrue(
                    a_menu._is_active(),
                    "Same path, no domain, qs subset match, should match",
                )
                a_menu.url = f"http://localhost.com:8069{url}"
                self.request_url_mock = f"http://example.com:8069{url}"
                self.assertFalse(
                    a_menu._is_active(), "Same path, domain mismatch, should not match"
                )
                self.request_url_mock = f"http://localhost.com:8069{url}"
                self.assertTrue(
                    a_menu._is_active(), "Same path, same domain, should match"
                )

        test_full_case(menu)

        menu.url = "/"
        menu2 = menu.copy()
        menu3 = menu.copy({"url": "#"})
        menu4 = menu3.copy()
        submenu = Menu.create(
            {
                "name": "Page Specific menu",
                "url": "/contactus",
                "website_id": website_1.id,
                "parent_id": menu.id,
            }
        )
        submenu2 = submenu.copy({"parent_id": menu3.id})

        self.request_url_mock = "http://localhost:8069/"
        with (
            MockRequest(self.env, website=website_1),
            patch(
                "odoo.addons.website.models.website_menu.urlsplit", new=urlsplit_mock
            ),
        ):
            self.assertFalse(
                menu._is_active(),
                "Same path but it's a container menu, its URL shouldn't be considered",
            )
            self.assertTrue(
                menu2._is_active(), "Same path and no child -> Should be active"
            )
            self.assertFalse(menu3._is_active(), "Not same path + children")
            self.assertTrue(menu4._is_active(), "Should match, see comment in code")
            self.assertFalse(submenu._is_active(), "Not same path (2)")
            self.assertFalse(submenu2._is_active(), "Not same path (3)")

            self.request_url_mock = "http://localhost:8069/contactus"
            self.assertTrue(menu._is_active(), "A child is active (submenu)")
            self.assertFalse(menu2._is_active(), "Not same path (4)")
            self.assertTrue(menu3._is_active(), "A child is active (submenu2)")
            self.assertFalse(menu4._is_active(), "Not same path (5)")
            self.assertTrue(submenu._is_active(), "Same path")
            self.assertTrue(submenu2._is_active(), "Same path (2)")

        test_full_case(submenu)
        submenu.url = "/sub/slug-3"
        test_full_case(submenu)

        result = website_1.new_page(
            name="/sub/page-3",
            add_menu=True,
        )
        menu = Menu.browse(result["menu_id"])
        page = self.env["website.page"].browse(result["page_id"])
        self.assertEqual(
            menu.url, page.url, "Menu url should be the same than the page url"
        )

        test_full_case(menu.copy())

        with (
            MockRequest(self.env, website=website_1),
            patch(
                "odoo.addons.website.models.website_menu.urlsplit", new=urlsplit_mock
            ),
        ):
            self.request_url_mock = "http://localhost:8069/sub/slug-3"
            self.assertFalse(
                menu._is_active(), "Page linked, same unslug, should not match"
            )

    def test_menu_group_ids(self):
        Menu = self.env["website.menu"]
        menu = Menu.create(
            {
                "name": "Test",
            }
        )
        self.assertEqual(menu.group_ids, self.env["res.groups"])
        menu.group_ids = self.env.ref("base.group_user")
        self.assertEqual(
            menu.group_ids,
            self.env.ref("base.group_user")
            + self.env.ref("website.group_website_designer"),
        )

    def test_07_menu_hierarchy_validation(self):
        Menu = self.env["website.menu"]

        self.main_menu = Menu.create(
            {
                "name": "Main",
            }
        )
        self.child_menu_1 = Menu.create(
            {
                "name": "Child1",
            }
        )
        self.child_menu_1.parent_id = self.main_menu.id

        self.child_menu_2 = Menu.create(
            {
                "name": "Child2",
            }
        )
        with self.assertRaises(UserError):
            self.child_menu_2.parent_id = self.child_menu_1.id

        self.mega_menu = Menu.create(
            {
                "name": "Mega menu",
                "is_mega_menu": True,
            }
        )
        self.another_menu = Menu.create(
            {
                "name": "Sample_menu",
            }
        )

        with self.assertRaises(UserError):
            self.mega_menu.parent_id = self.another_menu.id

        with self.assertRaises(UserError):
            self.another_menu.parent_id = self.mega_menu.id

        with self.assertRaises(UserError):
            self.main_menu.parent_id = self.another_menu.id

    def test_08_menu_save_is_gated_and_field_whitelisted(self):
        Menu = self.env["website.menu"]
        website = self.env["website"].search([], limit=1)
        other_website = self.env["website"].create({"name": "W2"})
        menu = Menu.create(
            {"name": "Editable", "url": "/editable", "website_id": website.id}
        )

        public = self.env.ref("base.public_user")
        with self.assertRaises(AccessError):
            Menu.with_user(public).save(website.id, {"data": [], "to_delete": []})

        payload = {
            "data": [
                {
                    "id": menu.id,
                    "name": "Renamed",
                    "url": "/editable",
                    "parent_id": website.menu_id.id,
                    "sequence": 3,
                    "website_id": other_website.id,
                    "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
                }
            ],
            "to_delete": [],
        }
        with MockRequest(self.env, website=website):
            Menu.save(website.id, payload)
        menu.invalidate_recordset()
        self.assertEqual(menu.name, "Renamed", "whitelisted field must be written")
        self.assertEqual(
            menu.website_id, website, "website_id injection must be ignored"
        )
        self.assertFalse(menu.group_ids, "group_ids injection must be ignored")

    def test_09_default_sequence_scoped_to_website(self):
        Menu = self.env["website.menu"]
        website_a = self.env["website"].search([], limit=1)
        website_b = self.env["website"].create({"name": "Seq Site B"})
        Menu.create({"name": "HighA", "website_id": website_a.id, "sequence": 5000})
        default_b = Menu.with_context(website_id=website_b.id)._default_sequence()
        self.assertLess(
            default_b,
            5000,
            "site B's default sequence must not inherit site A's high sequence",
        )


class TestMenuHttp(common.HttpCase):
    def setUp(self):
        super().setUp()
        self.page_url = "/page_specific"
        self.page = self.env["website.page"].create(
            {
                "url": self.page_url,
                "website_id": 1,
                "name": "Base",
                "type": "qweb",
                "arch": "<div>Specific View</div>",
                "key": "test.specific_view",
            }
        )
        self.menu = self.env["website.menu"].create(
            {
                "name": "Page Specific menu",
                "page_id": self.page.id,
                "url": self.page_url,
                "website_id": 1,
            }
        )
        self.headers = {"Content-Type": "application/json"}

    def simulate_rpc_save_menu(self, data, to_delete=None):
        self.authenticate("admin", "admin")
        self.url_open(
            "/web/dataset/call_kw",
            data=json.dumps(
                {
                    "params": {
                        "model": "website.menu",
                        "method": "save",
                        "args": [1, {"data": [data], "to_delete": to_delete or []}],
                        "kwargs": {},
                    },
                }
            ),
            headers={
                "Content-Type": "application/json",
                "Referer": self.page.get_base_url() + self.page_url,
            },
        )

    def test_01_menu_page_m2o(self):
        self.assertTrue(self.menu.page_id, "M2o should have been set by the setup")
        data = {
            "id": self.menu.id,
            "parent_id": self.menu.parent_id.id,
            "name": self.menu.name,
            "url": "/website/info",
        }
        self.simulate_rpc_save_menu(data)

        self.assertFalse(
            self.menu.page_id, "M2o should have been unset as this is a reserved URL."
        )
        self.assertEqual(
            self.menu.url, "/website/info", "Menu URL should have changed."
        )
        self.assertEqual(
            self.page.url, self.page_url, "Page's URL shouldn't have changed."
        )

        data["url"] = self.page_url
        self.env["website.menu"].save(1, {"data": [data], "to_delete": []})
        self.assertEqual(
            self.menu.page_id,
            self.page,
            "M2o should have been set back, as there was a page found with the new URL set on the menu.",
        )
        self.assertTrue(self.page.url == self.menu.url == self.page_url)

    def test_02_menu_anchors(self):
        self.assertTrue(self.menu.page_id, "M2o should have been set by the setup")
        data = {
            "id": self.menu.id,
            "parent_id": self.menu.parent_id.id,
            "name": self.menu.name,
            "url": "#anchor",
        }
        self.simulate_rpc_save_menu(data)
        self.assertFalse(
            self.menu.page_id, "M2o should have been unset as this is an anchor URL."
        )
        self.assertEqual(
            self.menu.url,
            self.page_url + "#anchor",
            "Page URL should have been properly prefixed with the referer url",
        )
        self.assertEqual(
            self.page.url, self.page_url, "Page URL should not have changed"
        )

    def test_03_mega_menu_translate(self):
        self.authenticate("admin", "admin")
        fr = self.env["res.lang"]._activate_lang("fr_FR")
        Menu = self.env["website.menu"]
        website = self.env["website"].browse(1)
        website.language_ids += fr
        menu = Menu.create(
            {
                "name": "Test Mega Menu Content Translation Edit Mode",
                "mega_menu_content": "<p>something</p>",
                "parent_id": website.menu_id.id,
                "website_id": website.id,
            }
        )
        self.env["ir.module.module"]._load_module_terms(["website"], [fr.code])

        self.url_open("/%s" % fr.url_code)
        self.url_open("/%s?edit_translations=1" % fr.url_code)

        root = html.fromstring(menu.mega_menu_content)
        to_translate = root.text_content()
        sha = sha256(to_translate.encode()).hexdigest()
        payload = self.prepare_rpc_payload(
            {
                "model": menu._name,
                "record_id": menu.id,
                "field_name": "mega_menu_content",
                "translations": {fr.code: {sha: "french_mega_menu_content"}},
            }
        )
        self.url_open(
            "/website/field/translation/update",
            data=json.dumps(payload),
            headers=self.headers,
        )
        self.assertIn(
            "french_mega_menu_content",
            menu.with_context(lang=fr.code, website_id=website.id).mega_menu_content,
        )

        page = self.url_open("/%s" % fr.url_code)
        self.assertIn(b"french_mega_menu_content", page.content)
        page = self.url_open("/%s?edit_translations=1" % fr.url_code)
        self.assertIn(b"french_mega_menu_content", page.content)
