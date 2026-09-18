from psycopg.errors import CheckViolation

from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestTypeNamesTheTable(TransactionCase):
    def test_every_leaf_table_pins_its_type(self):
        Actions = self.env["ir.actions.actions"]
        for model_name in sorted(Actions._get_model_names_in_tree() - {Actions._name}):
            table = self.env[model_name]._table
            with self.subTest(table=table):
                self.env.cr.execute(
                    "SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c"
                    " JOIN pg_class t ON t.oid = c.conrelid"
                    " WHERE t.relname = %s AND c.conname = %s",
                    [table, f"{table}_type_names_model"],
                )
                [definition] = self.env.cr.fetchone() or [""]
                self.assertIn(f"'{model_name}'", definition)

    def test_a_row_cannot_name_another_model(self):
        action = self.env["ir.actions.act_window"].search([], limit=1)
        with (
            self.assertRaises(CheckViolation),
            mute_logger("odoo.db.cursor"),
            self.env.cr.savepoint(),
        ):
            self.env.cr.execute(
                "UPDATE ir_act_window SET type = 'ir.actions.client' WHERE id = %s",
                [action.id],
            )
