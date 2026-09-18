from psycopg.errors import CheckViolation

from odoo.exceptions import ValidationError
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
