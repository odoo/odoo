from odoo.tests import TransactionCase
from odoo.tools import SQL
from odoo.tools.populate import (
    PopulateContext,
    infer_many2many_model,
    populate_models,
)


class TestPopulate(TransactionCase):
    def _count(self, model):
        return self.env[model].search_count([])

    def test_populate_inherits_model_does_not_raise(self):
        users_before = self._count("res.users")
        partners_before = self._count("res.partner")

        populate_models({self.env["res.users"]: 2}, ord("_"))
        self.env.invalidate_all()

        self.assertEqual(self._count("res.users"), users_before * 3)
        self.assertGreater(self._count("res.partner"), partners_before)

    def test_populate_plain_model(self):
        partners_before = self._count("res.partner")
        populate_models({self.env["res.partner"]: 2}, ord("_"))
        self.env.invalidate_all()
        self.assertEqual(self._count("res.partner"), partners_before * 3)

    def _count_catalogue_probes(self, model_factors):
        cursor_class = type(self.env.cr)
        original = cursor_class.execute
        seen = {"catalogue": 0, "total": 0}

        def counting(cursor, query, *args, **kwargs):
            seen["total"] += 1
            code = getattr(query, "code", None) or (
                query if isinstance(query, str) else ""
            )
            if "pg_index" in code:
                seen["catalogue"] += 1
            return original(cursor, query, *args, **kwargs)

        cursor_class.execute = counting
        try:
            populate_models(model_factors, ord("_"))
        finally:
            cursor_class.execute = original
        return seen

    def test_the_unique_column_lookup_does_not_scale_with_the_columns(self):
        partner = self.env["res.partner"]
        columns = sum(1 for field in partner._fields.values() if field.is_column)
        self.assertGreater(columns, 20, "res.partner should be wide enough to matter")

        seen = self._count_catalogue_probes({partner: 2})

        self.assertLess(
            seen["catalogue"],
            columns // 4,
            f"{seen['catalogue']} pg_index lookups for {columns} columns — the "
            f"per-column probe is back",
        )
        self.assertLess(
            seen["catalogue"],
            seen["total"] // 2,
            "catalogue probing should not dominate a bulk-insert run",
        )


class TestPopulateTableInheritance(TransactionCase):
    def _tables(self):
        return [
            table
            for (table,) in self.env.execute_query(
                SQL(
                    """
                    SELECT c.relname
                      FROM pg_inherits i
                      JOIN pg_class c ON c.oid = i.inhrelid
                     WHERE i.inhparent = 'ir_actions'::regclass
                    """
                )
            )
        ]

    def _own_counts(self):
        return {
            table: self.env.execute_query(
                SQL("SELECT count(*) FROM ONLY %s", SQL.identifier(table))
            )[0][0]
            for table in ["ir_actions", *self._tables()]
        }

    def _duplicate_ids(self):
        return self.env.execute_query(
            SQL("SELECT id FROM ir_actions GROUP BY id HAVING count(*) > 1")
        )

    def _assert_sequence_past_the_tree(self):
        last_value, max_id = self.env.execute_query(
            SQL(
                "SELECT (SELECT last_value FROM ir_actions_id_seq), "
                "(SELECT max(id) FROM ir_actions)"
            )
        )[0]
        self.assertGreaterEqual(last_value, max_id)

    def test_a_member_is_copied_into_its_own_table_past_the_whole_tree(self):
        before = self._own_counts()
        self.assertTrue(before["ir_act_url"])

        populate_models({self.env["ir.actions.act_url"]: 2}, ord("_"))

        after = self._own_counts()
        self.assertEqual(after["ir_act_url"], before["ir_act_url"] * 3)
        self.assertEqual(
            {t: n for t, n in after.items() if t != "ir_act_url"},
            {t: n for t, n in before.items() if t != "ir_act_url"},
        )
        self.assertFalse(self._duplicate_ids())
        self._assert_sequence_past_the_tree()

    def test_the_root_copies_every_table_into_itself(self):
        before = self._own_counts()

        populate_models({self.env["ir.actions.actions"]: 1}, ord("_"))

        after = self._own_counts()
        self.assertEqual(after, {t: n * 2 for t, n in before.items()})
        self.assertFalse(self._duplicate_ids())
        self._assert_sequence_past_the_tree()


class TestPopulateFactors(TransactionCase):
    def _relation_rows(self):
        [(rows,)] = self.env.execute_query(
            SQL("SELECT count(*) FROM res_groups_users_rel")
        )
        return rows

    def test_a_requested_factor_is_not_overwritten_by_a_parent(self):
        self.env.flush_all()
        rows_before = self._relation_rows()
        self.assertTrue(rows_before)
        relation = infer_many2many_model(
            self.env, self.env["res.users"]._fields["group_ids"]
        )
        factors = {self.env["res.users"]: 2, relation: 1}

        populate_models(factors, ord("_"))

        self.assertEqual(factors[relation], 1)
        self.assertEqual(self._relation_rows(), rows_before * 2)


class TestPopulateIndexRestore(TransactionCase):
    def _indexes(self):
        return {
            name
            for (name,) in self.env.execute_query(
                SQL("SELECT indexname FROM pg_indexes WHERE tablename = 'res_partner'")
            )
        }

    def test_one_failed_restore_does_not_abort_the_others(self):
        cr = self.env.cr
        cr.execute(
            SQL("CREATE INDEX res_partner_0_populate_probe ON res_partner (comment)")
        )
        before = self._indexes()
        self.assertGreater(len(before), 3)

        with (
            self.assertLogs("odoo.tools.populate", "ERROR") as logs,
            PopulateContext().ignore_indexes(self.env["res.partner"]),
        ):
            cr.execute(SQL("CREATE TABLE res_partner_0_populate_probe (x int)"))

        self.assertEqual(len(logs.records), 1)
        self.assertEqual(self._indexes(), before - {"res_partner_0_populate_probe"})
