import psycopg.errors

from odoo.libs.sql import SQL
from odoo.tests.common import TransactionCase


def build(model, **registries):
    """Assemble ``model``'s query with some registry hooks replaced.

    Values are returned verbatim by the patched hook.  Patching the registry
    class is restored in ``finally``; every caller goes through here so no test
    can leak a hook into the ones that follow it.
    """
    cls = type(model)
    original = {name: cls.__dict__.get(name, _ABSENT) for name in registries}
    try:
        for name, value in registries.items():
            setattr(cls, name, lambda self, _v=value: _v)
        return model._query()
    finally:
        for name, method in original.items():
            if method is _ABSENT:
                delattr(cls, name)
            else:
                setattr(cls, name, method)


_ABSENT = object()


class TestRegistryComposition(TransactionCase):
    """Core registry-assembly behaviour, on a real report model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.report = cls.env["mixin.report.sql.test.plain"]

    def test_select_and_from_assemble(self):
        sql = self.report._query()
        self.assertIn("SELECT", sql.code)
        self.assertIn('s.grain AS "grain"', sql.code)
        self.assertIn("FROM", sql.code)
        self.assertIn("mixin_report_sql_test_source s", sql.code)

    def test_the_assembled_query_runs(self):
        self.env["mixin.report.sql.test.source"].create({"grain": "a", "value": 2.0})
        self.env.flush_all()
        self.env.cr.execute(self.report._query())
        rows = {row[1]: row[2] for row in self.env.cr.fetchall()}
        self.assertEqual(rows["a"], 2.0)

    def test_the_orm_reads_the_report(self):
        Source = self.env["mixin.report.sql.test.source"]
        Source.create({"grain": "a", "value": 2.0})
        Source.create({"grain": "a", "value": 3.0})
        Source.create({"grain": "b", "value": 7.0})
        self.env.flush_all()
        by_grain = {r.grain: (r.total, r.rows) for r in self.report.search([])}
        self.assertEqual(by_grain, {"a": (5.0, 2), "b": (7.0, 1)})

    def test_with_cte_preserved(self):
        sql = build(
            self.report,
            _with_cte=SQL("my_cte AS (SELECT 1 AS id)"),
            _get_from_tables=[("my_cte", "c", None, None)],
            _get_fields_select={"id": "c.id"},
            _get_fields_group_by=[],
        )
        self.assertTrue(sql.code.startswith("WITH my_cte AS (SELECT 1 AS id)"))
        self.env.cr.execute(sql)

    def test_where_joins_with_AND(self):
        sql = build(
            self.report,
            _get_where_conditions=["s.value > 0", "s.grain IS NOT NULL"],
        )
        self.assertIn("WHERE\n    s.value > 0\n    AND s.grain IS NOT NULL", sql.code)
        self.env.cr.execute(sql)

    def test_where_accepts_SQL_objects_for_params(self):
        sql = build(self.report, _get_where_conditions=[SQL("s.grain = %s", "a")])
        self.assertEqual(sql.params, ("a",))
        self.env.cr.execute(sql)

    def test_having_has_a_named_home(self):
        """Aggregate filters land in HAVING, after GROUP BY and before ORDER BY."""
        Source = self.env["mixin.report.sql.test.source"]
        Source.create({"grain": "a", "value": 1.0})
        Source.create({"grain": "b", "value": 1.0})
        Source.create({"grain": "b", "value": 1.0})
        self.env.flush_all()
        sql = build(self.report, _get_having_conditions=["COUNT(*) > 1"])
        self.assertLess(sql.code.index("GROUP BY"), sql.code.index("HAVING"))
        self.env.cr.execute(sql)
        self.assertEqual([row[1] for row in self.env.cr.fetchall()], ["b"])

    def test_having_accepts_SQL_objects_for_params(self):
        sql = build(self.report, _get_having_conditions=[SQL("SUM(s.value) > %s", 5)])
        self.assertEqual(sql.params, (5,))
        self.env.cr.execute(sql)

    def test_clause_order(self):
        sql = build(
            self.report,
            _with_cte=SQL("c AS (SELECT 1)"),
            _get_where_conditions=["s.value > 0"],
            _get_having_conditions=["COUNT(*) > 0"],
            _get_fields_order_by=["s.grain"],
        )
        positions = [
            sql.code.index(kw)
            for kw in (
                "WITH",
                "SELECT",
                "FROM",
                "WHERE",
                "GROUP BY",
                "HAVING",
                "ORDER BY",
            )
        ]
        self.assertEqual(positions, sorted(positions))
        self.env.cr.execute(sql)

    def test_empty_select_raises(self):
        with self.assertRaises(NotImplementedError) as cm:
            build(self.report, _get_fields_select={})
        self.assertIn("_get_fields_select", str(cm.exception))

    def test_empty_from_raises(self):
        with self.assertRaises(NotImplementedError) as cm:
            build(self.report, _get_from_tables=[])
        self.assertIn("_get_from_tables", str(cm.exception))


class TestFromEntryShapes(TransactionCase):
    """``_prepare_from_entry`` renders each entry kind, and refuses the broken one."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.report = cls.env["mixin.report.sql.test.plain"]

    def test_base_table(self):
        entry = self.report._prepare_from_entry("t", "a", None, None)
        self.assertEqual(entry.code, "t a")

    def test_base_table_without_alias(self):
        entry = self.report._prepare_from_entry("t", None, None, None)
        self.assertEqual(entry.code, "t")

    def test_join_with_alias_and_condition(self):
        entry = self.report._prepare_from_entry("t", "a", "LEFT JOIN", "a.id = b.id")
        self.assertEqual(entry.code, "LEFT JOIN t a ON a.id = b.id")

    def test_join_without_alias_has_no_stray_space(self):
        entry = self.report._prepare_from_entry("t", None, "LEFT JOIN", "t.id = b.id")
        self.assertEqual(entry.code, "LEFT JOIN t ON t.id = b.id")

    def test_sql_table_carries_its_own_alias(self):
        entry = self.report._prepare_from_entry(SQL("(SELECT 1) x"), None, None, None)
        self.assertEqual(entry.code, "(SELECT 1) x")

    def test_a_sql_table_never_renders_the_alias_argument(self):
        """It binds its own name; rendering both is a syntax error.

        The base entry used to render it and the JOIN entry used to drop it, so
        the same registry value was valid in one slot and not the other.
        """
        entry = self.report._prepare_from_entry(SQL("(SELECT 1) x"), "x", None, None)
        self.assertEqual(entry.code, "(SELECT 1) x")
        entry = self.report._prepare_from_entry(
            SQL("(SELECT 1) x"), "x", "LEFT JOIN", "x.c = 1"
        )
        self.assertEqual(entry.code, "LEFT JOIN (SELECT 1) x ON x.c = 1")

        # what rendering both would have produced, and why it is not rendered
        with self.assertRaises(psycopg.errors.SyntaxError):
            with self.env.cr.savepoint():
                self.env.cr.execute(
                    SQL("SELECT * FROM (SELECT 1 AS c) x a"), log_exceptions=False
                )

    def test_both_currency_table_shapes_assemble(self):
        """The live reason the alias must be dropped rather than rendered.

        `res.currency._get_simple_currency_table` returns an aliased VALUES list
        or a bare relation name depending on the companies' currencies, and
        sale.report / purchase.report pass the same alias for both.
        """
        aliased = SQL("(VALUES (1, 1.0)) AS account_currency_table(company_id, rate)")
        bare = SQL("account_currency_table")
        for table in (aliased, bare):
            entry = self.report._prepare_from_entry(
                table, "account_currency_table", "LEFT JOIN", "o.company_id = 1"
            )
            self.assertNotIn(
                "account_currency_table account_currency_table", entry.code
            )
        self.env.cr.execute(
            SQL(
                "SELECT rate FROM %s",
                self.report._prepare_from_entry(
                    aliased, "account_currency_table", None, None
                ),
            )
        )
        self.assertEqual(self.env.cr.fetchone()[0], 1.0)


class TestPercentEscaping(TransactionCase):
    """Registry strings must escape ``%`` as ``%%``; enforce with a clear error."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.report = cls.env["mixin.report.sql.test.plain"]

    def test_unescaped_percent_in_select_raises_value_error(self):
        with self.assertRaises(ValueError) as cm:
            build(
                self.report,
                _get_fields_select={
                    "id": "MIN(s.id)",
                    "grain": "CASE WHEN s.grain LIKE 'a%' THEN 'x' ELSE 'y' END",
                },
            )
        self.assertIn("%%", str(cm.exception))
        self.assertIn("grain", str(cm.exception))

    def test_escaped_percent_pair_round_trips_through_psycopg(self):
        sql = build(
            self.report,
            _get_fields_select={
                "id": "MIN(s.id)",
                "grain": "MAX(CASE WHEN s.grain LIKE 'a%%' THEN 'hit' ELSE 'miss' END)",
            },
        )
        self.assertIn("a%%", sql.code)
        self.env["mixin.report.sql.test.source"].create({"grain": "abc", "value": 1.0})
        self.env.flush_all()
        self.env.cr.execute(sql)
        # Odoo's cursor passes params=() rather than None, so psycopg still
        # collapses '%%' to '%': the doubled pattern must match 'abc'.
        self.assertEqual(self.env.cr.fetchone()[1], "hit")

    def test_unescaped_percent_in_where_raises(self):
        with self.assertRaises(ValueError):
            build(self.report, _get_where_conditions=["s.grain LIKE 'x%'"])

    def test_unescaped_percent_in_having_raises(self):
        with self.assertRaises(ValueError):
            build(self.report, _get_having_conditions=["MAX(s.grain) LIKE 'x%'"])


class TestMaterializedMarkerInteraction(TransactionCase):
    """The ``_materialized`` marker decides what the ORM reads.

    Regression fence: without it, models inheriting both mixins have a physical
    relation the ORM never reads.
    """

    def test_non_materialized_model_is_inlined(self):
        report = self.env["mixin.report.sql.test.plain"]
        self.assertIsInstance(report._table_query, SQL)
        self.assertTrue(report._table_sql.code.startswith("(SELECT"))

    def test_materialized_model_reads_the_relation(self):
        report = self.env["mixin.report.sql.test.mv"]
        self.assertIsNone(report._table_query)
        self.assertEqual(report._table_sql.code, '"mixin_report_sql_test_mv"')
