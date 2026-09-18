from odoo.tests.common import TransactionCase, tagged

from odoo.addons.base.models.ir_model_common import MODULE_UNINSTALL_FLAG


@tagged("post_install", "-at_install")
class TestCascadeIntoActionTree(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.model = cls.env["ir.model"].create(
            {
                "name": "Cascade Probe",
                "model": "x_tab_cascade",
                "field_id": [
                    (
                        0,
                        0,
                        {"name": "x_name", "ttype": "char", "field_description": "N"},
                    )
                ],
            }
        )
        cls.window = cls.env["ir.actions.act_window"].create(
            {
                "name": "tab-cascade window",
                "res_model": "x_tab_cascade",
                "path": "tab-cascade-window",
                "binding_model_id": cls.model.id,
            }
        )
        cls.server = cls.env["ir.actions.server"].create(
            {
                "name": "tab-cascade server",
                "model_id": cls.model.id,
                "state": "code",
                "code": "pass",
                "path": "tab-cascade-server",
            }
        )
        cls.menu = cls.env["ir.ui.menu"].create(
            {
                "name": "tab-cascade menu",
                "action": f"ir.actions.server,{cls.server.id}",
            }
        )
        cls.holder = cls.env["tab.action.holder"].create({"action_id": cls.window.id})
        cls.user = cls.env["res.users"].create(
            {"name": "tab-cascade", "login": "tab-cascade", "action_id": cls.window.id}
        )
        cls.env.flush_all()

    def _count(self, query, *params):
        self.env.cr.execute(query, list(params))
        return self.env.cr.fetchone()[0]

    def test_registry_knows_the_cascades_into_the_tree(self):
        cascades = self.env.registry.cascades_into_inheritance_trees
        self.assertIn(("ir.actions.actions", "binding_model_id"), cascades["ir.model"])
        self.assertIn(("ir.actions.server", "model_id"), cascades["ir.model"])
        self.assertNotIn(
            ("ir.actions.act_window", "binding_model_id"), cascades["ir.model"]
        )
        self.assertIn(("ir.actions.server", "parent_id"), cascades["ir.actions.server"])

    def test_registry_follows_a_cascade_through_a_plain_model(self):
        cascades = self.env.registry.cascades_into_inheritance_trees
        self.assertIn(
            ("ir.actions.server", "update_field_id"), cascades["ir.model.fields"]
        )
        self.assertIn(
            ("ir.actions.server", "update_field_id.model_id"), cascades["ir.model"]
        )
        self.assertIn(
            ("ir.actions.server", "selection_value.field_id.model_id"),
            cascades["ir.model"],
        )
        for pairs in cascades.values():
            for __, path in pairs:
                self.assertLessEqual(path.count("."), 3, path)

    def test_deleting_the_model_unlinks_its_actions_through_the_orm(self):
        action_ids = [self.window.id, self.server.id]
        holder_id, menu_id, user_id = self.holder.id, self.menu.id, self.user.id

        self.model.unlink()
        self.env.flush_all()

        self.assertEqual(
            self._count(
                "SELECT count(*) FROM ir_actions WHERE id = ANY(%s)", action_ids
            ),
            0,
        )
        self.assertEqual(
            self._count(
                "SELECT count(*) FROM ir_actions_path WHERE action_id = ANY(%s)",
                action_ids,
            ),
            0,
        )
        self.assertEqual(
            self._count(
                "SELECT count(*) FROM tab_action_holder WHERE id = %s", holder_id
            ),
            0,
        )
        self.assertEqual(
            self._count(
                "SELECT count(*) FROM ir_ui_menu WHERE id = %s AND action IS NOT NULL",
                menu_id,
            ),
            0,
        )
        self.assertEqual(
            self._count(
                "SELECT count(*) FROM res_users WHERE id = %s AND action_id IS NOT NULL",
                user_id,
            ),
            0,
        )
        self.env["ir.actions.act_url"].create(
            {"name": "reuse", "url": "/x", "path": "tab-cascade-window"}
        )

    def test_deleting_a_parent_server_action_unlinks_its_children_through_the_orm(self):
        parent = self.env["ir.actions.server"].create(
            {
                "name": "tab-cascade parent",
                "model_id": self.env["ir.model"]._get("res.partner").id,
                "state": "multi",
            }
        )
        child = self.env["ir.actions.server"].create(
            {
                "name": "tab-cascade child",
                "model_id": parent.model_id.id,
                "state": "code",
                "code": "pass",
                "parent_id": parent.id,
                "path": "tab-cascade-child",
            }
        )
        self.env.flush_all()
        child_id = child.id

        parent.unlink()
        self.env.flush_all()

        self.assertEqual(
            self._count(
                "SELECT count(*) FROM ir_actions_path WHERE action_id = %s", child_id
            ),
            0,
        )

    def test_init_releases_a_path_that_outlived_its_action(self):
        self.env.flush_all()
        self.env.cr.execute("DELETE FROM ir_act_window WHERE id = %s", [self.window.id])
        self.env["ir.actions.path"].init()
        self.assertEqual(
            self._count(
                "SELECT count(*) FROM ir_actions_path WHERE path = %s",
                "tab-cascade-window",
            ),
            0,
        )

    def test_deleting_a_referrer_model_with_the_bound_one_still_unlinks(self):
        referrer = self.env["ir.model"].create(
            {
                "name": "Cascade Referrer",
                "model": "x_tab_referrer",
                "field_id": [
                    (
                        0,
                        0,
                        {
                            "name": "x_action_id",
                            "ttype": "many2one",
                            "relation": "ir.actions.actions",
                            "on_delete": "cascade",
                            "field_description": "A",
                        },
                    )
                ],
            }
        )
        self.env["x_tab_referrer"].create({"x_action_id": self.window.id})
        self.env.flush_all()
        action_ids = [self.window.id, self.server.id]

        (self.model + referrer).unlink()
        self.env.flush_all()

        self.assertEqual(
            self._count(
                "SELECT count(*) FROM ir_actions WHERE id = ANY(%s)", action_ids
            ),
            0,
        )

    def test_a_cascade_through_a_deleted_models_field_unlinks_the_action(self):
        holder = self.env["ir.model"].create(
            {
                "name": "Cascade Holder",
                "model": "x_tab_holder",
                "field_id": [
                    (
                        0,
                        0,
                        {
                            "name": "x_probe_id",
                            "ttype": "many2one",
                            "relation": "x_tab_cascade",
                            "field_description": "P",
                        },
                    )
                ],
            }
        )
        action = self.env["ir.actions.server"].create(
            {
                "name": "tab-cascade two steps",
                "model_id": holder.id,
                "state": "object_write",
                "update_path": "x_probe_id.x_name",
                "value": "x",
                "path": "tab-cascade-two-steps",
            }
        )
        self.assertEqual(action.update_field_id.model, "x_tab_cascade")
        self.env.flush_all()
        action_id = action.id

        self.model.unlink()
        self.env.flush_all()

        self.assertEqual(
            self._count("SELECT count(*) FROM ir_actions WHERE id = %s", action_id), 0
        )
        self.assertEqual(
            self._count(
                "SELECT count(*) FROM ir_actions_path WHERE action_id = %s", action_id
            ),
            0,
        )

    def test_a_referrer_column_dropped_by_an_uninstall_does_not_stop_the_unlink(self):
        referrer = self.env["ir.model"].create(
            {
                "name": "Cascade Referrer",
                "model": "x_tab_dropped",
                "field_id": [
                    (
                        0,
                        0,
                        {
                            "name": "x_action_id",
                            "ttype": "many2one",
                            "relation": "ir.actions.actions",
                            "on_delete": "cascade",
                            "field_description": "A",
                        },
                    )
                ],
            }
        )
        self.env.flush_all()
        uninstalling = self.env(context={MODULE_UNINSTALL_FLAG: True})
        self.env.cr.execute('ALTER TABLE "x_tab_dropped" DROP COLUMN "x_action_id"')
        self.assertIn("x_action_id", self.env["x_tab_dropped"]._fields)
        window_id = self.window.id

        self.window.with_env(uninstalling).unlink()
        self.env.flush_all()

        self.assertEqual(
            self._count("SELECT count(*) FROM ir_actions WHERE id = %s", window_id), 0
        )
        self.assertTrue(referrer.exists())
