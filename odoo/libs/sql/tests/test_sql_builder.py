import unittest
from typing import Any

from odoo.libs.sql.builder import SQL


class TestSqlTupleExpansion(unittest.TestCase):
    def test_empty_tuple_renders_null(self):
        sql = SQL("x IN %s", ())
        self.assertEqual(sql.code, "x IN (NULL)")
        self.assertEqual(tuple(sql.params), ())

    def test_non_empty_tuple_expands_placeholders(self):
        sql = SQL("x IN %s", (1, 2, 3))
        self.assertEqual(sql.code, "x IN (%s, %s, %s)")
        self.assertEqual(tuple(sql.params), (1, 2, 3))

    def test_sql_element_in_tuple_is_spliced_not_leaked(self):
        sql = SQL("x IN %s", (SQL("SELECT 1"), 2))
        self.assertEqual(sql.code, "x IN (SELECT 1, %s)")
        self.assertEqual(tuple(sql.params), (2,))
        self.assertFalse(any(isinstance(p, SQL) for p in sql.params))

    def test_sql_element_in_tuple_carries_params_and_flush(self):
        field = object()
        inner = SQL("col = %s", 7, to_flush=field)  # type: ignore[arg-type]
        sql = SQL("(%s)", (inner, 8))
        self.assertEqual(sql.code, "((col = %s, %s))")
        self.assertEqual(tuple(sql.params), (7, 8))
        self.assertEqual(tuple(sql.to_flush), (field,))

    def test_single_element_tuple(self):
        sql = SQL("x IN %s", (7,))
        self.assertEqual(sql.code, "x IN (%s)")
        self.assertEqual(tuple(sql.params), (7,))


class TestSqlIdentifierValidation(unittest.TestCase):
    def test_identifier_rejects_trailing_newline(self):
        with self.assertRaises(ValueError):
            SQL.identifier("col\n")

    def test_identifier_accepts_plain_name(self):
        self.assertEqual(SQL.identifier("col").code, '"col"')


class TestSqlInlined(unittest.TestCase):
    class _Cursor:
        connection = None

    def test_preserves_to_flush(self):
        field = object()
        sql = SQL('"t"."name"->>%s', "fr_FR", to_flush=field)  # type: ignore[arg-type]
        inlined = sql.inlined(self._Cursor())  # type: ignore[arg-type]
        self.assertEqual(inlined.code, '"t"."name"->>\'fr_FR\'')
        self.assertEqual(inlined.params, ())
        self.assertEqual(tuple(inlined.to_flush), (field,))

    def test_percent_escape_survives(self):
        sql = SQL("x LIKE 'a%%' AND y = %s", 5)
        inlined = sql.inlined(self._Cursor())  # type: ignore[arg-type]
        self.assertEqual(inlined.code, "x LIKE 'a%%' AND y = 5")
        self.assertEqual(inlined.params, ())

    def test_literal_containing_percent_is_reescaped(self):
        sql = SQL("y = %s", "50% 'off'")
        inlined = sql.inlined(self._Cursor())  # type: ignore[arg-type]
        self.assertEqual(inlined.code, "y = '50%% ''off'''")
        self.assertEqual(inlined.params, ())

    def test_no_params_returns_self(self):
        sql = SQL("x LIKE 'a%%'")
        self.assertIs(sql.inlined(self._Cursor()), sql)  # type: ignore[arg-type]

    def test_composes_as_sql(self):
        inner = SQL("a = %s", 1).inlined(self._Cursor())  # type: ignore[arg-type]
        outer = SQL("%s AND b = %s", inner, 2)
        self.assertEqual(outer.code, "a = 1 AND b = %s")
        self.assertEqual(outer.params, (2,))


if __name__ == "__main__":
    unittest.main()


class TestSqlNoArgConstructionStillValidatesPercent(unittest.TestCase):
    def test_a_stray_percent_is_still_rejected(self):
        with self.assertRaises(TypeError):
            SQL("x LIKE 'a%b'")

    def test_a_doubled_percent_is_still_accepted_and_preserved(self):
        self.assertEqual(SQL("x LIKE 'a%%'").code, "x LIKE 'a%%'")

    def test_percent_free_code_is_unchanged(self):
        self.assertEqual(
            SQL('SELECT id FROM "res_partner"').code, 'SELECT id FROM "res_partner"'
        )
        self.assertEqual(SQL("").code, "")

    def test_identifier_still_builds(self):
        self.assertEqual(
            SQL.identifier("res_partner", "name").code, '"res_partner"."name"'
        )


class TestPgVarcharRejectsNonsense(unittest.TestCase):
    def test_a_negative_size_is_not_silently_unbounded(self):
        from odoo.libs.sql.utils import pg_varchar

        with self.assertRaises(ValueError):
            pg_varchar(-5)

    def test_a_non_int_is_rejected_even_when_falsy(self):
        from odoo.libs.sql.utils import pg_varchar

        bad_values: tuple[Any, ...] = (0.0, 2.5, "10")
        for bad in bad_values:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                pg_varchar(bad)

    def test_none_is_chars_own_spelling_of_unbounded(self):
        from odoo.libs.sql.utils import pg_varchar

        self.assertEqual(pg_varchar(None), "VARCHAR")

    def test_a_bool_is_not_a_size(self):
        from odoo.libs.sql.utils import pg_varchar

        with self.assertRaises(ValueError):
            pg_varchar(True)

    def test_ordinary_sizes_are_unchanged(self):
        from odoo.libs.sql.utils import pg_varchar

        self.assertEqual(pg_varchar(), "VARCHAR")
        self.assertEqual(pg_varchar(0), "VARCHAR")
        self.assertEqual(pg_varchar(64), "VARCHAR(64)")
