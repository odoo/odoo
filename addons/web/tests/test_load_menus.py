import json
import re

from odoo import Command, api, tools
from odoo.tests.common import HttpCase, tagged


@tagged("web_http", "web_menu")
class LoadMenusTests(HttpCase):
    maxDiff = None

    def setUp(self):
        super().setUp()
        self.menu = self.env["ir.ui.menu"].create(
            {
                "name": "root menu (test)",
                "parent_id": False,
            }
        )
        self.action = self.env["ir.actions.act_window"].create(
            {
                "name": "action (test)",
                "res_model": "res.users",
                "view_ids": [Command.create({"view_mode": "form"})],
            }
        )
        self.menu_child = self.env["ir.ui.menu"].create(
            {
                "name": "child menu (test)",
                "parent_id": self.menu.id,
                "action": f"{self.action._name},{self.action.id}",
            }
        )

        menus = self.menu + self.menu_child

        origin_search_fetch = self.env.registry["ir.ui.menu"].search_fetch

        @api.model
        def search_fetch(self, domain, *args, **kwargs):
            return origin_search_fetch(
                self, domain + [("id", "in", menus.ids)], *args, **kwargs
            )

        self.patch(self.env.registry["ir.ui.menu"], "search_fetch", search_fetch)
        self.authenticate("admin", "admin")

    def test_load_menus(self):
        menu_loaded = self.url_open("/web/webclient/load_menus")
        expected = {
            str(self.menu.id): {
                "actionID": self.action.id,
                "actionModel": "ir.actions.act_window",
                "actionPath": False,
                "actionResModel": "res.users",
                "appID": self.menu.id,
                "children": [self.menu_child.id],
                "id": self.menu.id,
                "name": "root menu (test)",
                "webCategory": False,
                "webCategorySequence": 0,
                "webIcon": False,
                "webKeywords": False,
                "webIconData": "/web/static/img/default_icon_app.png",
                "webIconDataMimetype": False,
                "xmlid": "",
            },
            str(self.menu_child.id): {
                "actionID": self.action.id,
                "actionModel": "ir.actions.act_window",
                "actionPath": False,
                "actionResModel": "res.users",
                "appID": self.menu.id,
                "children": [],
                "id": self.menu_child.id,
                "name": "child menu (test)",
                "webCategory": False,
                "webCategorySequence": 0,
                "webIcon": False,
                "webKeywords": False,
                "webIconData": False,
                "webIconDataMimetype": False,
                "xmlid": "",
            },
            "root": {
                "actionID": False,
                "actionModel": False,
                "actionPath": False,
                "actionResModel": False,
                "appID": False,
                "children": [self.menu.id],
                "id": "root",
                "name": "root",
                "webCategory": None,
                "webCategorySequence": None,
                "webIcon": None,
                "webKeywords": None,
                "webIconData": None,
                "webIconDataMimetype": None,
                "xmlid": "",
            },
        }

        loaded = menu_loaded.json()
        self.assertEqual(loaded.keys(), expected.keys())
        self.assertDictEqual(
            {
                menu_id: {key: menu[key] for key in expected[menu_id]}
                for menu_id, menu in loaded.items()
            },
            expected,
            "load_menus didn't return the expected value on the keys web owns "
            "(an installed addon may add its own — web_studio's backgroundImage)",
        )

    def test_load_menus_web_icon_data(self):
        self.menu.web_icon = False
        self.menu.web_icon_data = b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+BCQAHBQICJmhD1AAAAABJRU5ErkJggg=="
        menu_loaded = self.url_open("/web/webclient/load_menus").json()
        root = menu_loaded[str(self.menu.id)]
        self.assertEqual(
            root["webIconData"],
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+BCQAHBQICJmhD1AAAAABJRU5ErkJggg==",
        )
        self.assertEqual(root["webIconDataMimetype"], "image/png")
        self.assertFalse(root["webIcon"])
        child = menu_loaded[str(self.menu_child.id)]
        self.assertFalse(child["webIconData"])
        self.assertFalse(child["webIconDataMimetype"])

    def test_load_menus_conditional(self):
        res = self.url_open("/web/webclient/load_menus")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("Cache-Control"), "no-store")
        current_hash = res.headers.get("X-Menus-Hash")
        self.assertTrue(current_hash, "200 response must expose X-Menus-Hash")
        full_payload = res.json()
        self.assertIn("root", full_payload)

        res_cached = self.url_open(f"/web/webclient/load_menus?hash={current_hash}")
        self.assertEqual(res_cached.status_code, 304)
        self.assertFalse(
            res_cached.content,
            "304 response must have an empty body",
        )

        res_stale = self.url_open("/web/webclient/load_menus?hash=0deadbeef0")
        self.assertEqual(res_stale.status_code, 200)
        self.assertEqual(res_stale.headers.get("X-Menus-Hash"), current_hash)
        self.assertEqual(
            res_stale.json(),
            full_payload,
            "stale hash must return the full menus payload",
        )

    def test_preload_gate_reads_the_key_menu_storage_writes(self):
        self.authenticate("admin", "admin")
        page = self.url_open("/odoo").text

        gate = re.search(
            r'localStorage\.getItem\("webclient_menus_version"\)\s*===\s*([\w.]+)',
            page,
        )
        self.assertTrue(gate, "the preload's cache-validity check is gone")
        self.assertEqual(
            gate.group(1),
            "menus_cache_version",
            "the preload must compare against the server-composed key; "
            "recomposing it here is what drifted last time",
        )

        storage = tools.file_open(
            "web/static/src/webclient/menus/menu_storage.js",
        ).read()
        self.assertRegex(
            storage,
            r"function cacheVersion\(\) \{\s*return session\.menus_cache_version;",
            "menu_storage.js must read the same server-composed key",
        )

        session_info = json.loads(
            re.search(r"odoo\.__session_info__ = (\{.*?\});", page, re.DOTALL).group(1),
        )
        self.assertIn(
            "menus_cache_version",
            session_info,
            "session_info must carry the key both consumers read",
        )


@tagged("web_http", "web_menu")
class LoadMenusSearchTests(HttpCase):
    def setUp(self):
        super().setUp()
        self.authenticate("admin", "admin")

    def test_keywords_reach_the_client(self):
        menu = self.env.ref("base.menu_administration")
        menu.web_keywords = "preferences, configuration"
        self.env.registry.clear_all_caches()
        loaded = self.url_open("/web/webclient/load_menus").json()
        self.assertEqual(
            loaded[str(menu.id)]["webKeywords"],
            "preferences, configuration",
            "the launcher matches an app on words its name does not contain",
        )

    def test_keywords_are_translated(self):
        menu = self.env.ref("base.menu_administration")
        menu.web_keywords = "settings"
        self.assertTrue(
            self.env["ir.ui.menu"]._fields["web_keywords"].translate,
            "the vocabulary a user types is the vocabulary of their language",
        )

    def test_category_is_the_root_of_the_module_tree(self):
        base_menu = self.env.ref("base.menu_administration")
        category = self.env.ref("base.module_base").category_id
        while category.parent_id:
            category = category.parent_id
        menus = self.env["ir.ui.menu"].load_menus(False)
        self.assertEqual(
            menus[base_menu.id]["web_category"],
            category.name,
            "an app root carries the top of its module's category tree",
        )
        child_id = menus[base_menu.id]["children"][0]
        self.assertFalse(
            menus[child_id]["web_category"],
            "a heading belongs to an app, not to every menu under it",
        )

    def test_category_survives_a_menu_no_module_declares(self):
        action = self.env["ir.actions.act_window"].create(
            {
                "name": "orphan action",
                "res_model": "res.users",
                "view_ids": [Command.create({"view_mode": "form"})],
            }
        )
        menu = self.env["ir.ui.menu"].create(
            {
                "name": "orphan",
                "parent_id": False,
                "action": f"{action._name},{action.id}",
            }
        )
        self.env.registry.clear_all_caches()
        menus = self.env["ir.ui.menu"].load_menus(False)
        self.assertIn(menu.id, menus)
        self.assertFalse(
            menus[menu.id]["web_category"],
            "a menu with no xmlid has no heading, and asks for none",
        )

    def test_category_carries_the_order_its_group_sits_in(self):
        base_menu = self.env.ref("base.menu_administration")
        category = self.env.ref("base.module_base").category_id
        while category.parent_id:
            category = category.parent_id
        menus = self.env["ir.ui.menu"].load_menus(False)
        self.assertEqual(
            menus[base_menu.id]["web_category_sequence"],
            category.sequence,
            "the client has no other way to order the groups: menus are ordered "
            "by their own sequence, so grouping alone puts the headings in the "
            "order the first app of each happens to appear",
        )

    def test_a_leaf_category_does_not_head_a_group_of_its_own(self):
        # base declared five categories whose xml id path names a parent that
        # exists and which carried no parent_id, so each read as a top-level
        # application. On a database that loads the data file before any
        # manifest asks for the path -- which is any database where the module
        # arrives later -- the launcher heads its apps with the leaf, and
        # Invoicing sits beside Accounting as a separate group.
        # module_category_vocabulary.py is the gate; this pins the five.
        for leaf, parent in (
            ("accounting_accounting", "accounting"),
            ("services_helpdesk", "services"),
            ("human_resources_appraisals", "human_resources"),
            ("human_resources_referrals", "human_resources"),
            ("sales_sign", "sales"),
        ):
            self.assertEqual(
                self.env.ref(f"base.module_category_{leaf}").parent_id,
                self.env.ref(f"base.module_category_{parent}"),
                f"module_category_{leaf} heads a launcher group of its own "
                f"unless it declares module_category_{parent} as its parent",
            )
