from unittest.mock import patch

from odoo import Command
from odoo.tests.common import TransactionCase, new_test_user

from odoo.addons.base.models.ir_ui_menu import IrUiMenu


class TestMenu(TransactionCase):
    def test_00_menu_deletion(self):
        Menu = self.env["ir.ui.menu"]
        root = Menu.create({"name": "Test root"})
        child1 = Menu.create({"name": "Test child 1", "parent_id": root.id})
        child2 = Menu.create({"name": "Test child 2", "parent_id": root.id})
        child21 = Menu.create({"name": "Test child 2-1", "parent_id": child2.id})
        all_ids = [root.id, child1.id, child2.id, child21.id]

        root.unlink()

        remaining = Menu.search([("id", "in", all_ids)], order="id")
        self.assertEqual([child1.id, child2.id, child21.id], remaining.ids)

        orphans = Menu.search(
            [("id", "in", all_ids), ("parent_id", "=", False)], order="id"
        )
        self.assertEqual([child1.id, child2.id], orphans.ids)

    def test_display_name_recomputed_on_ancestor_rename(self):
        Menu = self.env["ir.ui.menu"]
        root = Menu.create({"name": "Path root"})
        child = Menu.create({"name": "Child", "parent_id": root.id})
        grandchild = Menu.create({"name": "Leaf", "parent_id": child.id})
        self.assertEqual(grandchild.display_name, "Path root/Child/Leaf")

        root.name = "Renamed root"
        self.assertEqual(grandchild.display_name, "Renamed root/Child/Leaf")
        self.assertEqual(grandchild.complete_name, "Renamed root/Child/Leaf")


class TestMenuVisibility(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Menu = cls.env["ir.ui.menu"]
        cls.Action = cls.env["ir.actions.act_window"]
        cls.employee = new_test_user(
            cls.env, login="menu_employee", groups="base.group_user"
        )

    def _act_window(self, res_model):
        return self.Action.create(
            {
                "name": f"action {res_model}",
                "res_model": res_model,
                "view_ids": [Command.create({"view_mode": "form"})],
            }
        )

    def test_visible_menu_ids_action_acl_gate(self):
        readable = self._act_window("res.partner")
        restricted = self._act_window("ir.config_parameter")
        root = self.Menu.create({"name": "ACL root"})
        menu_readable = self.Menu.create(
            {
                "name": "Readable",
                "parent_id": root.id,
                "action": f"{readable._name},{readable.id}",
            }
        )
        menu_restricted = self.Menu.create(
            {
                "name": "Restricted",
                "parent_id": root.id,
                "action": f"{restricted._name},{restricted.id}",
            }
        )

        admin_visible = self.Menu._get_visible_menu_ids()
        self.assertIn(menu_readable.id, admin_visible)
        self.assertIn(menu_restricted.id, admin_visible)
        self.assertIn(root.id, admin_visible)

        emp_visible = self.Menu.with_user(self.employee)._get_visible_menu_ids()
        self.assertIn(menu_readable.id, emp_visible)
        self.assertNotIn(menu_restricted.id, emp_visible)
        self.assertIn(root.id, emp_visible)

    def test_visible_menu_ids_client_action_without_a_model(self):
        action = self.env["ir.actions.client"].create(
            {"name": "modelless client action", "tag": "test_tag"}
        )
        self.assertFalse(action.res_model, "the case under test")
        root = self.Menu.create({"name": "Client root"})
        menu = self.Menu.create(
            {
                "name": "Client",
                "parent_id": root.id,
                "action": f"{action._name},{action.id}",
            }
        )

        visible = self.Menu.with_user(self.employee)._get_visible_menu_ids()
        self.assertIn(menu.id, visible, "no model named means no model-level gate")
        self.assertIn(root.id, visible)

    def test_visible_menu_ids_client_action_with_a_model_is_still_gated(self):
        action = self.env["ir.actions.client"].create(
            {
                "name": "restricted client action",
                "tag": "test_tag",
                "res_model": "ir.config_parameter",
            }
        )
        root = self.Menu.create({"name": "Gated client root"})
        menu = self.Menu.create(
            {
                "name": "Gated client",
                "parent_id": root.id,
                "action": f"{action._name},{action.id}",
            }
        )

        self.assertIn(menu.id, self.Menu._get_visible_menu_ids())
        self.assertNotIn(
            menu.id, self.Menu.with_user(self.employee)._get_visible_menu_ids()
        )

    def test_visible_menu_ids_deleted_action_hidden(self):
        action = self._act_window("res.partner")
        root = self.Menu.create({"name": "Dangling root"})
        menu = self.Menu.create(
            {
                "name": "Dangling",
                "parent_id": root.id,
                "action": f"{action._name},{action.id}",
            }
        )
        self.assertIn(menu.id, self.Menu._get_visible_menu_ids())

        action.unlink()
        visible = self.Menu._get_visible_menu_ids()
        self.assertNotIn(menu.id, visible)
        self.assertNotIn(root.id, visible)

    def test_visible_menu_ids_group_gate(self):
        group = self.env["res.groups"].create({"name": "Menu test group"})
        action = self._act_window("res.partner")
        parent = self.Menu.create(
            {"name": "Gated parent", "group_ids": [Command.set(group.ids)]}
        )
        child = self.Menu.create(
            {
                "name": "Child",
                "parent_id": parent.id,
                "action": f"{action._name},{action.id}",
            }
        )

        emp_visible = self.Menu.with_user(self.employee)._get_visible_menu_ids()
        self.assertIn(child.id, emp_visible)
        self.assertNotIn(parent.id, emp_visible)

        self.employee.write({"group_ids": [Command.link(group.id)]})
        emp_visible = self.Menu.with_user(self.employee)._get_visible_menu_ids()
        self.assertIn(child.id, emp_visible)
        self.assertIn(parent.id, emp_visible)

    def test_visible_menu_ids_cache_keyed_by_group_set(self):
        action = self._act_window("ir.config_parameter")
        root = self.Menu.create({"name": "Cache root"})
        menu = self.Menu.create(
            {
                "name": "Needs system",
                "parent_id": root.id,
                "action": f"{action._name},{action.id}",
            }
        )

        self.assertNotIn(
            menu.id, self.Menu.with_user(self.employee)._get_visible_menu_ids()
        )

        self.employee.write(
            {"group_ids": [Command.link(self.env.ref("base.group_system").id)]}
        )
        self.assertIn(
            menu.id, self.Menu.with_user(self.employee)._get_visible_menu_ids()
        )

    def test_visible_menu_ids_keyed_on_debug(self):
        action = self._act_window("res.partner")
        debug_root = self.Menu.create(
            {
                "name": "Debug only root",
                "group_ids": [Command.set(self.env.ref("base.group_no_one").ids)],
                "action": f"{action._name},{action.id}",
            }
        )

        self.assertNotIn(debug_root.id, self.Menu._get_visible_menu_ids(False))
        self.assertIn(debug_root.id, self.Menu._get_visible_menu_ids(True))

    def test_load_menus_root_keyed_on_debug(self):
        self.assertIn(
            "self._get_session_debug()", IrUiMenu.load_menus_root.__cache__.args
        )

        action = self._act_window("res.partner")
        debug_root = self.Menu.create(
            {
                "name": "Debug only root",
                "group_ids": [Command.set(self.env.ref("base.group_no_one").ids)],
                "action": f"{action._name},{action.id}",
            }
        )
        self.assertFalse(self.Menu._get_session_debug())

        roots_no_debug = self.Menu.load_menus_root()
        self.assertNotIn(debug_root.id, roots_no_debug["all_menu_ids"])

        with self.debug_mode():
            self.assertEqual(self.Menu._get_session_debug(), "1")
            roots_debug = self.Menu.load_menus_root()
            self.assertIn(debug_root.id, roots_debug["all_menu_ids"])

        roots_again = self.Menu.load_menus_root()
        self.assertNotIn(debug_root.id, roots_again["all_menu_ids"])

    def test_load_menus_answers_the_debug_flag_it_is_keyed_on(self):
        action = self._act_window("res.partner")
        debug_root = self.Menu.create(
            {
                "name": "Debug only root",
                "group_ids": [Command.set(self.env.ref("base.group_no_one").ids)],
                "action": f"{action._name},{action.id}",
            }
        )
        self.assertFalse(self.Menu._get_session_debug())

        self.assertIn(
            debug_root.id,
            self.Menu.load_menus(True),
            "load_menus(True) outside a debug session is cached under the debug "
            "key, so it must be the debug answer",
        )
        self.assertNotIn(debug_root.id, self.Menu.load_menus(False))
        with self.debug_mode():
            self.assertNotIn(
                debug_root.id,
                self.Menu.load_menus(False),
                "load_menus(False) inside a debug session must not leak the "
                "debug-only menus into the non-debug cache entry",
            )
            self.assertIn(debug_root.id, self.Menu.load_menus(True))


class TestMenuMisc(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Menu = self.env["ir.ui.menu"]

    def test_copy_suffixes_name(self):
        menu = self.Menu.create({"name": "Original"})
        copy1 = menu.copy()
        self.assertEqual(copy1.name, "Original (1)")

        copy2 = copy1.copy()
        self.assertEqual(copy2.name, "Original (2)")

    def test_copy_ignores_mid_name_number(self):
        menu = self.Menu.create({"name": "Budget (2025) Plan"})
        copy1 = menu.copy()
        self.assertEqual(copy1.name, "Budget (2025) Plan (1)")

        copy2 = copy1.copy()
        self.assertEqual(copy2.name, "Budget (2025) Plan (2)")

    def _count_cache_clears(self):
        registry_class = type(self.env.registry)
        calls = []
        original = registry_class.clear_cache

        def counting(reg, *cache_names):
            calls.append(cache_names)
            return original(reg, *cache_names)

        return patch.object(registry_class, "clear_cache", counting), calls

    def test_multi_copy_names_and_single_invalidation(self):
        menus = self.Menu.create([{"name": f"Multi {i}"} for i in range(3)])
        patcher, calls = self._count_cache_clears()
        with patcher:
            copies = menus.copy()
        self.assertEqual(
            copies.mapped("name"), ["Multi 0 (1)", "Multi 1 (1)", "Multi 2 (1)"]
        )
        self.assertEqual(
            len(calls),
            1,
            "copying N menus must invalidate the cache once (the batched "
            "create), not once per copied menu",
        )

    def test_copy_suffixes_explicit_default_name(self):
        menu = self.Menu.create({"name": "Original"})
        copy = menu.copy({"name": "Custom"})
        self.assertEqual(copy.name, "Custom (1)")

    def test_empty_operations_do_not_invalidate_cache(self):
        patcher, calls = self._count_cache_clears()
        with patcher:
            self.assertFalse(self.Menu.create([]))
            self.assertTrue(self.Menu.browse().write({"name": "x"}))
            self.assertTrue(self.Menu.browse().unlink())
        self.assertEqual(calls, [])

    def test_web_icon_data_built_icon(self):
        menu3 = self.Menu.create(
            {"name": "Built 3", "web_icon": "fa fa-cog,#000000,#ffffff"}
        )
        self.assertFalse(menu3.web_icon_data)

        menu2 = self.Menu.create({"name": "Built 2", "web_icon": "fa fa-cog,#000000"})
        self.assertFalse(menu2.web_icon_data)

    def test_web_icon_data_image_icon(self):
        menu = self.Menu.create(
            {"name": "Image icon", "web_icon": "base,static/img/main_partner-image.png"}
        )
        self.assertTrue(menu.web_icon_data)

    def test_read_image_malformed_path(self):
        self.assertFalse(self.Menu._read_image(""))
        self.assertFalse(self.Menu._read_image("only_one_part"))
        self.assertFalse(self.Menu._read_image("a,b,c"))
