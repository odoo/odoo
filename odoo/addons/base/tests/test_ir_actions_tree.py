from psycopg.errors import CheckViolation

from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestIrActionsTree(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Actions = cls.env["ir.actions.actions"]
        cls.window = cls.env["ir.actions.act_window"].create(
            {"name": "Tree probe", "res_model": "res.partner", "path": "tree-probe"}
        )

    def _children_in_database(self):
        self.env.cr.execute(
            """
            SELECT c.relname
              FROM pg_inherits i
              JOIN pg_class c ON c.oid = i.inhrelid
              JOIN pg_class p ON p.oid = i.inhparent
             WHERE p.relname = %s
            """,
            [self.Actions._table],
        )
        return {row[0] for row in self.env.cr.fetchall()}

    def test_every_subtype_table_inherits_the_root_in_the_database(self):
        declared = {
            self.env[name]._table
            for name in self.Actions._get_model_names_in_tree()
            if self.env[name]._table != self.Actions._table
        }
        self.assertEqual(self._children_in_database(), declared)

    def test_a_subtype_whose_table_does_not_inherit_is_refused_at_init(self):
        Window = self.env["ir.actions.act_window"]
        with self.env.cr.savepoint():
            self.env.cr.execute("ALTER TABLE ir_act_window NO INHERIT ir_actions")
            with self.assertRaises(ValueError) as caught:
                Window._check_table_inheritance()
            self.assertIn("ir_act_window", str(caught.exception))
            self.env.cr.execute("ALTER TABLE ir_act_window INHERIT ir_actions")

    def test_the_root_table_itself_holds_no_rows(self):
        self.env.cr.execute("SELECT count(*) FROM ONLY ir_actions")
        self.assertEqual(self.env.cr.fetchone()[0], 0)
        with self.assertRaises(CheckViolation), self.env.cr.savepoint():
            self.env.cr.execute(
                "INSERT INTO ir_actions (name, type, binding_type)"
                " VALUES ('{}'::jsonb, 'ir.actions.act_window', 'action')"
            )

    def test_load_resolves_the_concrete_model_from_the_table_not_the_column(self):
        # a database upgraded with such rows keeps them: the constraint that
        # forbids them is only added once none is left
        self.env.cr.execute(
            "ALTER TABLE ir_act_window DROP CONSTRAINT ir_act_window_type_names_model"
        )
        self.env.cr.execute(
            "UPDATE ir_act_window SET type = 'ir.actions.client' WHERE id = %s",
            [self.window.id],
        )
        self.Actions.invalidate_model()
        self.env["ir.actions.act_window"].invalidate_model()

        by_id = self.Actions.browse(self.window.id)._get_concrete()
        by_path = self.Actions._get_action_by_path("tree-probe")
        self.assertEqual(by_id._name, "ir.actions.act_window")
        self.assertEqual(by_path._name, "ir.actions.act_window")
        self.assertEqual(by_id._get_action_dict()["type"], "ir.actions.act_window")

    def test_a_type_that_names_another_model_is_refused_by_the_orm(self):
        with self.assertRaises(ValidationError):
            self.env["ir.actions.act_window"].create(
                {"name": "x", "res_model": "res.partner", "type": "ir.actions.client"}
            )

    @mute_logger("odoo.addons.base.models.ir_actions_actions")
    def test_a_domain_with_a_missing_name_reads_it_as_false(self):
        self.assertEqual(
            self.Actions._eval_action_domain("[('id', '=', active_id)]"),
            [("id", "=", False)],
        )
        self.assertEqual(
            self.Actions._eval_action_domain("[('id', '=', active_id)]", active_id=7),
            [("id", "=", 7)],
        )

    @mute_logger("odoo.addons.base.models.ir_actions_actions")
    def test_a_domain_that_is_not_a_list_falls_back_to_empty(self):
        self.assertEqual(self.Actions._eval_action_domain("{'a': 1}"), [])
        self.assertEqual(self.Actions._eval_action_domain("1 +"), [])


@tagged("post_install", "-at_install")
class TestIrActionsLoadAudit(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.env["res.users"].create(
            {
                "name": "load audit",
                "login": "load_audit",
                "group_ids": [(6, 0, [cls.env.ref("base.group_user").id])],
            }
        )
        cls.system = cls.env.ref("base.group_system")
        Window = cls.env["ir.actions.act_window"]
        cls.open = Window.create({"name": "open", "res_model": "res.partner"})
        cls.restricted = Window.create(
            {
                "name": "restricted",
                "res_model": "res.partner",
                "group_ids": [(6, 0, [cls.system.id])],
            }
        )
        cls.closed_model = Window.create(
            {"name": "closed", "res_model": "ir.config_parameter"}
        )

    def test_the_rule_is_the_one_bindings_apply(self):
        as_user = lambda action: action.with_user(self.user)  # noqa: E731  reads as the sentence the assertions below are made of
        self.assertEqual(as_user(self.open)._get_load_refusal_of_record(), "")
        self.assertEqual(
            as_user(self.restricted)._get_load_refusal_of_record(), "groups"
        )
        self.assertEqual(
            as_user(self.closed_model)._get_load_refusal_of_record(), "model"
        )
        self.assertEqual(self.restricted._get_load_refusal_of_record(), "")

    def test_a_type_without_groups_or_target_is_always_loadable(self):
        url = self.env["ir.actions.act_url"].create({"name": "u", "url": "/x"})
        self.assertEqual(url.with_user(self.user)._get_load_refusal_of_record(), "")

    def test_bindings_and_load_agree(self):
        model_id = self.env["ir.model"]._get("res.partner").id
        (self.open + self.restricted).write({"binding_model_id": model_id})
        bound = {
            b["id"]
            for b in self.env["ir.actions.actions"]
            .with_user(self.user)
            .get_bindings("res.partner")
            .get("action", [])
        }
        for action in (self.open, self.restricted):
            loadable = not action.with_user(self.user)._get_load_refusal_of_record()
            self.assertEqual(action.id in bound, loadable, action.name)

    def test_a_refused_load_raises_and_is_logged(self):
        logger = "odoo.addons.base.models.ir_actions_actions"
        with (
            self.assertLogs(logger, level="INFO") as captured,
            self.assertRaises(AccessError),
        ):
            self.restricted.with_user(self.user)._check_access_to_load()
        self.assertIn("refused", captured.output[0])
        self.assertIn(str(self.restricted.id), captured.output[0])
        with self.assertNoLogs(logger, level="INFO"):
            self.open.with_user(self.user)._check_access_to_load()
        self.restricted._check_access_to_load()

    def test_a_closed_target_model_refuses_the_load(self):
        with self.assertRaises(AccessError):
            self.closed_model.with_user(self.user)._check_access_to_load()

    def test_load_by_xml_id_refuses_a_non_member(self):
        self.env["ir.model.data"].create(
            {
                "module": "base",
                "name": "load_audit_restricted",
                "model": "ir.actions.act_window",
                "res_id": self.restricted.id,
            }
        )
        Actions = self.env["ir.actions.actions"]
        with self.assertRaises(AccessError):
            Actions.with_user(self.user)._get_action_dict_by_xml_id(
                "base.load_audit_restricted"
            )
        result = Actions._get_action_dict_by_xml_id("base.load_audit_restricted")
        self.assertEqual(result["id"], self.restricted.id)


@tagged("post_install", "-at_install")
class TestIrActionsConcreteCache(TransactionCase):
    def _queries(self, fn):
        before = self.env.cr.sql_statement_count
        result = fn()
        return result, self.env.cr.sql_statement_count - before

    def test_a_second_resolution_of_the_same_id_costs_no_query(self):
        window = self.env["ir.actions.act_window"].create(
            {"name": "cache probe", "res_model": "res.partner"}
        )
        Actions = self.env["ir.actions.actions"]
        self.env.flush_all()
        self.env.registry.clear_cache("default")
        first, cost_first = self._queries(
            lambda: Actions.browse(window.id)._get_model_names_concrete()
        )
        second, cost_second = self._queries(
            lambda: Actions.browse(window.id)._get_model_names_concrete()
        )
        self.assertEqual(first, {window.id: "ir.actions.act_window"})
        self.assertEqual(second, first)
        self.assertGreaterEqual(cost_first, 1)
        self.assertEqual(cost_second, 0)

    def test_a_batch_queries_only_the_ids_it_has_not_seen(self):
        Window = self.env["ir.actions.act_window"]
        seen = Window.create({"name": "seen", "res_model": "res.partner"})
        unseen = Window.create({"name": "unseen", "res_model": "res.partner"})
        Actions = self.env["ir.actions.actions"]
        self.env.flush_all()
        self.env.registry.clear_cache("default")
        Actions.browse(seen.id)._get_model_names_concrete()
        result, cost = self._queries(
            lambda: Actions.browse([seen.id, unseen.id])._get_model_names_concrete()
        )
        self.assertEqual(
            result,
            {seen.id: "ir.actions.act_window", unseen.id: "ir.actions.act_window"},
        )
        self.assertGreaterEqual(cost, 1)

    def test_a_missing_id_is_the_root_and_is_not_cached(self):
        Actions = self.env["ir.actions.actions"]
        missing = 10**8
        self.env.registry.clear_cache("default")
        self.assertEqual(
            Actions.browse(missing)._get_model_names_concrete(),
            {missing: "ir.actions.actions"},
        )
        _result, cost = self._queries(
            lambda: Actions.browse(missing)._get_model_names_concrete()
        )
        self.assertGreaterEqual(cost, 1, "a miss is asked again, never memoised")
