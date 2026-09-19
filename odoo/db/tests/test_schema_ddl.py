import re
import typing
import unittest
from collections import deque
from types import SimpleNamespace
from typing import Any

import psycopg

from odoo.db import BaseCursor, schema
from odoo.db.savepoint import Savepoint
from odoo.libs.sql import SQL


def _collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


class _Savepoint:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _RecordingCursor(BaseCursor):
    def __init__(self, rows: list[list[Any]] | None = None):
        super().__init__()
        self.statements: list[tuple[str, tuple[Any, ...]]] = []
        self.rows: deque[list[Any]] = deque(rows or [])
        self._current: list[Any] = []
        self._rowcount = 0
        self.raise_on: dict[int, Exception] = {}

    @property
    def rowcount(self) -> int:
        return self._rowcount

    def execute(self, query, params=None, log_exceptions=True, prepare=None):
        if isinstance(query, SQL):
            code, params = query.code, query.params
        else:
            code, params = query, params or ()
        self.statements.append((_collapse(code), tuple(params)))
        n = len(self.statements)
        if n in self.raise_on:
            raise self.raise_on[n]
        self._current = self.rows.popleft() if self.rows else []
        self._rowcount = len(self._current)

    def fetchone(self):
        return self._current[0] if self._current else None

    def fetchall(self):
        return list(self._current)

    def dictfetchone(self):
        return dict(self._current[0]) if self._current else None

    def dictfetchall(self):
        return [dict(row) for row in self._current]

    def savepoint(self, flush: bool = True) -> Savepoint:
        return typing.cast("Savepoint", _Savepoint())

    @property
    def codes(self) -> list[str]:
        return [code for code, _ in self.statements]

    @property
    def last(self) -> tuple[str, tuple[Any, ...]]:
        return self.statements[-1]


class TestTableDdl(unittest.TestCase):
    def test_create_model_table_is_one_statement_with_its_comments(self):
        cr = _RecordingCursor()
        schema.create_model_table(
            cr,
            "res_thing",
            comment="Things",
            columns=[("name", "varchar", "Name"), ("n", "int4", None)],
        )
        code, params = cr.last
        self.assertEqual(
            code,
            'CREATE TABLE "res_thing" (id SERIAL NOT NULL, "name" varchar, '
            '"n" int4, PRIMARY KEY(id)); COMMENT ON TABLE "res_thing" IS %s; '
            'COMMENT ON COLUMN "res_thing"."name" IS %s',
        )
        self.assertEqual(params, ("Things", "Name"))
        self.assertEqual(len(cr.statements), 1)

    def test_create_model_table_refuses_a_type_that_is_not_a_name(self):
        cr = _RecordingCursor()
        with self.assertRaises(ValueError):
            schema.create_model_table(
                cr, "t", columns=[("c", "int4; DROP TABLE x", None)]
            )
        self.assertEqual(cr.statements, [])

    def test_get_tables_existing_asks_for_every_admitted_relkind(self):
        cr = _RecordingCursor([[("a",)]])
        self.assertEqual(schema.get_tables_existing(cr, ["a", "b"]), ["a"])
        code, params = cr.last
        self.assertIn("c.relkind = ANY(%s)", code)
        self.assertEqual(params, (["a", "b"], list(schema._EXISTING_RELKINDS)))

    def test_get_table_kind_reads_persistence_for_a_regular_table(self):
        for row, kind in (
            (("r", "p"), schema.TableKind.Regular),
            (("r", "t"), schema.TableKind.Temporary),
            (("p", "p"), schema.TableKind.Partitioned),
            (("m", "p"), schema.TableKind.Materialized),
            (("x", "p"), schema.TableKind.Other),
        ):
            with self.subTest(row=row):
                cr = _RecordingCursor([[row]])
                self.assertIs(schema.get_table_kind(cr, "t"), kind)
        self.assertIsNone(schema.get_table_kind(_RecordingCursor([[]]), "t"))


class TestColumnDdl(unittest.TestCase):
    def test_create_column_defaults_a_boolean_to_false(self):
        cr = _RecordingCursor()
        schema.create_column(cr, "t", "flag", "boolean")
        self.assertEqual(
            cr.last, ('ALTER TABLE "t" ADD COLUMN "flag" boolean DEFAULT false', ())
        )

    def test_create_column_renders_no_trailing_space_without_a_default(self):
        cr = _RecordingCursor()
        schema.create_column(cr, "t", "n", "int4", comment="Count")
        self.assertEqual(
            cr.last,
            (
                'ALTER TABLE "t" ADD COLUMN "n" int4; COMMENT ON COLUMN "t"."n" IS %s',
                ("Count",),
            ),
        )

    def test_create_column_refuses_a_type_that_is_not_a_name(self):
        for bad in ("int4; DROP", "varchar(", ""):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                schema.create_column(_RecordingCursor(), "t", "c", bad)

    def test_convert_column_casts_through_the_type(self):
        cr = _RecordingCursor()
        schema.convert_column(cr, "t", "c", "numeric")
        self.assertEqual(
            cr.codes,
            [
                (
                    'ALTER TABLE "t" ALTER COLUMN "c" DROP DEFAULT, '
                    'ALTER COLUMN "c" TYPE numeric USING "c"::numeric'
                )
            ],
        )

    def test_convert_column_guards_the_type_before_building_any_sql(self):
        cr = _RecordingCursor()
        with self.assertRaises(ValueError):
            schema.convert_column(cr, "t", "c", "numeric; DROP")
        self.assertEqual(cr.statements, [])

    def test_a_conversion_a_view_blocks_drops_the_views_and_retries(self):
        cr = _RecordingCursor([[("v_thing", "v"), ("mv_thing", "m")]])
        cr.raise_on[1] = psycopg.errors.FeatureNotSupported("used by a view")
        schema.convert_column(cr, "t", "c", "text")
        self.assertEqual(
            [c[:40] for c in cr.codes],
            [
                'ALTER TABLE "t" ALTER COLUMN "c" DROP DE',
                "SELECT distinct dependee.relname, depend",
                'DROP VIEW IF EXISTS "v_thing" CASCADE',
                'DROP MATERIALIZED VIEW IF EXISTS "mv_thi',
                'ALTER TABLE "t" ALTER COLUMN "c" DROP DE',
            ],
        )

    def test_translatable_conversion_wraps_and_unwraps_en_us(self):
        cr = _RecordingCursor()
        schema.convert_column_translatable(cr, "t", "c", "jsonb")
        self.assertEqual(cr.codes[0], 'DROP INDEX IF EXISTS "t__c_index"')
        self.assertIn(
            "USING CASE WHEN \"c\" IS NOT NULL THEN jsonb_build_object('en_US', "
            '"c"::varchar) END',
            cr.codes[1],
        )
        cr = _RecordingCursor()
        schema.convert_column_translatable(cr, "t", "c", "varchar")
        self.assertIn("USING \"c\"->>'en_US'", cr.codes[1])

    def test_rename_column_renames_the_not_null_constraint_named_after_it(self):
        cr = _RecordingCursor([[], [(1,)], []])
        schema.rename_column(cr, "t", "old", "new")
        self.assertEqual(cr.codes[0], 'ALTER TABLE "t" RENAME COLUMN "old" TO "new"')
        code, params = cr.statements[1]
        self.assertIn("t.relnamespace = current_schema::regnamespace", code)
        self.assertEqual(params, ("t", "t_old_not_null"))
        self.assertEqual(
            cr.codes[2],
            'ALTER TABLE "t" RENAME CONSTRAINT "t_old_not_null" TO "t_new_not_null"',
        )

    def test_rename_column_leaves_a_constraint_that_is_not_there_alone(self):
        cr = _RecordingCursor([[], []])
        schema.rename_column(cr, "t", "old", "new")
        self.assertEqual(len(cr.statements), 2)

    def test_drop_columns_is_one_cascading_alter_for_the_columns_that_exist(self):
        existing = [{"column_name": "a"}, {"column_name": "b"}]
        cr = _RecordingCursor([existing, [], [], []])
        self.assertEqual(schema.drop_columns(cr, "t", ["a", "gone", "b"]), ["a", "b"])
        self.assertEqual(
            cr.codes[-1],
            'ALTER TABLE "t" DROP COLUMN "a" CASCADE, DROP COLUMN "b" CASCADE',
        )
        self.assertEqual(sum("DROP COLUMN" in code for code in cr.codes), 1)

    def test_drop_columns_names_the_views_it_takes_down(self):
        cr = _RecordingCursor([[{"column_name": "a"}], [("report_v", "v")], []])
        with self.assertLogs("odoo.schema", level="INFO") as logs:
            schema.drop_columns(cr, "t", ["a"])
        self.assertIn("report_v", logs.output[0])

    def test_drop_columns_leaves_a_table_without_them_alone(self):
        cr = _RecordingCursor([[{"column_name": "kept"}]])
        self.assertEqual(schema.drop_columns(cr, "t", ["gone"]), [])
        self.assertEqual(len(cr.statements), 1)

    def test_not_null_and_default(self):
        cr = _RecordingCursor()
        schema.set_not_null(cr, "t", "c")
        schema.drop_not_null(cr, "t", "c")
        schema.set_default(cr, "t", "c", 0)
        self.assertEqual(
            cr.statements,
            [
                ('ALTER TABLE "t" ALTER COLUMN "c" SET NOT NULL', ()),
                ('ALTER TABLE "t" ALTER COLUMN "c" DROP NOT NULL', ()),
                ('ALTER TABLE "t" ALTER COLUMN "c" SET DEFAULT %s', (0,)),
            ],
        )

    def test_column_exists_reads_rowcount(self):
        cr = _RecordingCursor([[(1,)]])
        self.assertIs(schema.column_exists(cr, "t", "c"), True)
        self.assertEqual(cr.last[1], ("t", "c"))
        self.assertIs(schema.column_exists(_RecordingCursor([[]]), "t", "c"), False)


class TestConstraintDdl(unittest.TestCase):
    def test_add_constraint_escapes_the_definition_and_comments_it_verbatim(self):
        cr = _RecordingCursor()
        schema.add_constraint(cr, "t", "t_pct", "CHECK (name NOT LIKE '%x')")
        self.assertEqual(
            cr.statements,
            [
                (
                    'ALTER TABLE "t" ADD CONSTRAINT "t_pct" CHECK (name NOT LIKE \'%%x\')',
                    (),
                ),
                (
                    'COMMENT ON CONSTRAINT "t_pct" ON "t" IS %s',
                    ("CHECK (name NOT LIKE '%x')",),
                ),
            ],
        )

    def test_drop_constraint(self):
        cr = _RecordingCursor()
        schema.drop_constraint(cr, "t", "c1")
        self.assertEqual(cr.last, ('ALTER TABLE "t" DROP CONSTRAINT "c1"', ()))

    def test_get_constraint_definition_prefers_the_stored_comment(self):
        cr = _RecordingCursor([[("stored",)]])
        self.assertEqual(schema.get_constraint_definition(cr, "t", "c1"), "stored")
        self.assertIn(
            "COALESCE(d.description, pg_get_constraintdef(c.oid))", cr.last[0]
        )
        self.assertIsNone(
            schema.get_constraint_definition(_RecordingCursor([[]]), "t", "c1")
        )

    def test_add_foreign_key_validates_the_on_delete_policy(self):
        cr = _RecordingCursor()
        schema.add_foreign_key(cr, "child", "parent_id", "parent", "id", "set null")
        self.assertEqual(
            cr.last,
            (
                (
                    'ALTER TABLE "child" ADD FOREIGN KEY ("parent_id") REFERENCES '
                    '"parent"("id") ON DELETE set null'
                ),
                (),
            ),
        )
        with self.assertRaises(ValueError):
            schema.add_foreign_key(cr, "child", "parent_id", "parent", "id", "explode")
        self.assertEqual(len(cr.statements), 1)

    def test_fk_constraint_names_match_target_and_policy(self):
        rows = [
            ("fk_a", "parent", "id", "n"),
            ("fk_b", "parent", "id", "c"),
            ("fk_c", "other", "id", "n"),
        ]
        cr = _RecordingCursor([rows])
        self.assertEqual(
            schema.get_fk_constraint_names(
                cr, "child", "pid", "parent", "id", "SET NULL"
            ),
            ["fk_a"],
        )
        self.assertEqual(cr.last[1], ("child", "pid"))

    def test_fk_constraints_batch_asks_once_for_every_table(self):
        cr = _RecordingCursor([[("fk", "a", "x", "b", "id", "a")]])
        rows = schema.get_fk_constraints_batch(cr, ["a", "b"])
        self.assertEqual(rows, [("fk", "a", "x", "b", "id", "a")])
        self.assertEqual(cr.last[1], (["a", "b"],))
        self.assertIn("array_length(fk.conkey, 1) = 1", cr.last[0])

    def test_column_names_in_constraint_uses_the_diagnostic_first(self):
        diag = SimpleNamespace(column_name="c", constraint_name="k", table_name="t")
        cr = _RecordingCursor()
        self.assertEqual(schema.get_column_names_in_constraint(cr, diag), ["c"])  # type: ignore[arg-type]
        self.assertEqual(cr.statements, [])
        diag = SimpleNamespace(column_name=None, constraint_name="k", table_name="t")
        self.assertEqual(schema.get_column_names_in_constraint(cr, diag), [])  # type: ignore[arg-type]
        self.assertEqual(cr.statements, [])
        cr = _RecordingCursor([[(["a", "b"],)]])
        self.assertEqual(
            schema.get_column_names_in_constraint(cr, diag, check_catalog=True),  # type: ignore[arg-type]
            ["a", "b"],
        )
        self.assertEqual(cr.last[1], ("k", "t"))


class TestIndexDdl(unittest.TestCase):
    def test_create_index_skips_when_it_exists(self):
        cr = _RecordingCursor([[(1,)]])
        schema.create_index(cr, "i", "t", ["a"])
        self.assertEqual(len(cr.statements), 1)
        self.assertIn("c.relkind IN ('i', 'I')", cr.last[0])

    def test_create_index_builds_the_full_definition(self):
        cr = _RecordingCursor([[]])
        schema.create_index(
            cr, "i", "t", ["a", "lower(b)"], "gin", "a > 0", comment="why", unique=True
        )
        self.assertEqual(
            cr.codes[1:],
            [
                'CREATE UNIQUE INDEX "i" ON "t" USING gin (a, lower(b)) WHERE a > 0',
                'COMMENT ON INDEX "i" IS %s',
            ],
        )
        self.assertEqual(cr.statements[2][1], ("why",))

    def test_create_index_refuses_an_empty_expression_list_and_a_bad_method(self):
        with self.assertRaises(ValueError):
            schema.create_index(_RecordingCursor(), "i", "t", [])
        with self.assertRaises(ValueError):
            schema.create_index(_RecordingCursor(), "i", "t", ["a"], "btree; DROP")

    def test_add_index_with_a_string_definition_escapes_percent(self):
        cr = _RecordingCursor()
        schema.add_index(
            cr, "i", "t", "USING btree (a) WHERE a LIKE 'x%'", unique=False
        )
        self.assertEqual(
            cr.last,
            ('CREATE INDEX "i" ON "t" USING btree (a) WHERE a LIKE \'x%%\'', ()),
        )

    def test_drop_index(self):
        cr = _RecordingCursor()
        schema.drop_index(cr, "i", "t")
        self.assertEqual(cr.last, ('DROP INDEX IF EXISTS "i"', ()))

    def test_index_definition_and_constraint(self):
        cr = _RecordingCursor([[("CREATE INDEX ...", "why")]])
        self.assertEqual(
            schema.get_index_definition(cr, "i"), ("CREATE INDEX ...", "why")
        )
        self.assertEqual(
            schema.get_index_definition(_RecordingCursor([[]]), "i"), (None, None)
        )
        cr = _RecordingCursor([[("t_pkey",)]])
        self.assertEqual(schema.get_index_constraint(cr, "t_pkey"), "t_pkey")
        self.assertIsNone(schema.get_index_constraint(_RecordingCursor([[]]), "i"))


class TestViewDdl(unittest.TestCase):
    def test_drop_view_if_exists_matches_the_kind_it_finds(self):
        for row, expected in (
            (("v", "p"), 'DROP VIEW "v1" CASCADE'),
            (("m", "p"), 'DROP MATERIALIZED VIEW "v1" CASCADE'),
        ):
            with self.subTest(kind=row[0]):
                cr = _RecordingCursor([[row]])
                schema.drop_view_if_exists(cr, "v1")
                self.assertEqual(cr.last[0], expected)
        cr = _RecordingCursor([[]])
        schema.drop_view_if_exists(cr, "v1")
        self.assertEqual(len(cr.statements), 1, "nothing to drop, nothing dropped")
        cr = _RecordingCursor([[("r", "p")]])
        schema.drop_view_if_exists(cr, "v1")
        self.assertEqual(len(cr.statements), 1, "a table is not a view")


class TestCatalogProbes(unittest.TestCase):
    def test_unaccent_status(self):
        for row, status in (
            ([], schema.FunctionStatus.MISSING),
            ([("i",)], schema.FunctionStatus.INDEXABLE),
            ([("s",)], schema.FunctionStatus.PRESENT),
        ):
            with self.subTest(row=row):
                self.assertIs(
                    schema.get_unaccent_status(_RecordingCursor([row])), status
                )

    def test_has_trigram(self):
        self.assertTrue(schema.has_trigram(_RecordingCursor([[(1,)]])))
        self.assertFalse(schema.has_trigram(_RecordingCursor([[]])))

    def test_get_table_columns_keys_by_column_name(self):
        row = {
            "column_name": "a",
            "udt_name": "varchar",
            "character_maximum_length": 8,
            "is_nullable": "NO",
        }
        cr = _RecordingCursor([[row]])  # type: ignore[list-item]
        self.assertEqual(schema.get_table_columns(cr, "t"), {"a": row})
        self.assertEqual(cr.last[1], ("t",))


if __name__ == "__main__":
    unittest.main()
