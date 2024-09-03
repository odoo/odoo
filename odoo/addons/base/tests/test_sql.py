# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import BaseCase
from odoo.tools import SQL


class TestSQL(BaseCase):

    def test_sql_empty(self):
        sql = SQL()
        self.assertEqual(sql.code, "")
        self.assertEqual(sql.params, [])

    def test_sql_bool(self):
        self.assertFalse(SQL())
        self.assertFalse(SQL(""))
        self.assertTrue(SQL("anything"))
        self.assertTrue(SQL("%s", 42))

    def test_sql_with_no_parameter(self):
        sql = SQL("SELECT id FROM table WHERE foo=bar")
        self.assertEqual(sql.code, "SELECT id FROM table WHERE foo=bar")
        self.assertEqual(sql.params, [])

    def test_sql_with_literal_parameters(self):
        sql = SQL("SELECT id FROM table WHERE foo=%s AND bar=%s", 42, 'baz')
        self.assertEqual(sql.code, "SELECT id FROM table WHERE foo=%s AND bar=%s")
        self.assertEqual(sql.params, [42, 'baz'])

    def test_sql_with_wrong_pattern(self):
        with self.assertRaises(TypeError):
            SQL("SELECT id FROM table WHERE foo=%s AND bar=%s", 42)

        with self.assertRaises(TypeError):
            SQL("SELECT id FROM table WHERE foo=%s AND bar=%s", 1, 2, 3)

        with self.assertRaises(TypeError):
            SQL("SELECT id FROM table WHERE foo=%s AND bar=%(two)s", 1, two=2)

        with self.assertRaises(KeyError):
            SQL("SELECT id FROM table WHERE foo=%(one)s AND bar=%(two)s", one=1, to=2)

    def test_sql_equality(self):
        sql1 = SQL("SELECT id FROM table WHERE foo=%s", 42)
        sql2 = SQL("SELECT id FROM table WHERE foo=%s", 42)
        self.assertEqual(sql1, sql2)

        sql1 = SQL("SELECT id FROM table WHERE foo=%s", 42)
        sql2 = SQL("SELECT id FROM table WHERE bar=%s", 42)
        self.assertNotEqual(sql1, sql2)

        sql1 = SQL("SELECT id FROM table WHERE foo=%s", 42)
        sql2 = SQL("SELECT id FROM table WHERE foo=%s", 421)
        self.assertNotEqual(sql1, sql2)

    def test_sql_idempotence(self):
        sql1 = SQL("SELECT id FROM table WHERE foo=%s AND bar=%s", 42, 'baz')
        sql2 = SQL(sql1)
        self.assertIs(sql1, sql2)

    def test_sql_unpacking(self):
        sql = SQL("SELECT id FROM table WHERE foo=%s AND bar=%s", 42, 'baz')
        string, params = sql
        self.assertEqual(string, "SELECT id FROM table WHERE foo=%s AND bar=%s")
        self.assertEqual(params, [42, 'baz'])

    def test_sql_join(self):
        sql = SQL(" AND ").join([])
        self.assertEqual(sql.code, "")
        self.assertEqual(sql.params, [])
        self.assertEqual(sql, SQL(""))

        sql = SQL(" AND ").join([SQL("foo=%s", 1)])
        self.assertEqual(sql.code, "foo=%s")
        self.assertEqual(sql.params, [1])

        sql = SQL(" AND ").join([
            SQL("foo=%s", 1),
            SQL("bar=%s", 2),
            SQL("baz=%s", 3),
        ])
        self.assertEqual(sql.code, "foo=%s AND bar=%s AND baz=%s")
        self.assertEqual(sql.params, [1, 2, 3])

        sql = SQL(", ").join([1, 2, 3])
        self.assertEqual(sql.code, "%s, %s, %s")
        self.assertEqual(sql.params, [1, 2, 3])

    def test_sql_identifier(self):
        sql = SQL.identifier('foo')
        self.assertEqual(sql.code, '"foo"')
        self.assertEqual(sql.params, [])

        sql = SQL.identifier('année')
        self.assertEqual(sql.code, '"année"')
        self.assertEqual(sql.params, [])

        sql = SQL.identifier('foo', 'bar')
        self.assertEqual(sql.code, '"foo"."bar"')
        self.assertEqual(sql.params, [])

        with self.assertRaises(AssertionError):
            sql = SQL.identifier('foo"')

        with self.assertRaises(AssertionError):
            sql = SQL.identifier('(SELECT 42)')

        with self.assertRaises(AssertionError):
            sql = SQL.identifier('foo', 'ba"r')

    def test_sql_with_sql_parameters(self):
        sql = SQL("SELECT id FROM table WHERE foo=%s AND %s", 1, SQL("bar=%s", 2))
        self.assertEqual(sql.code, "SELECT id FROM table WHERE foo=%s AND bar=%s")
        self.assertEqual(sql.params, [1, 2])
        self.assertEqual(sql, SQL("SELECT id FROM table WHERE foo=%s AND bar=%s", 1, 2))

        sql = SQL("SELECT id FROM table WHERE %s AND bar=%s", SQL("foo=%s", 1), 2)
        self.assertEqual(sql.code, "SELECT id FROM table WHERE foo=%s AND bar=%s")
        self.assertEqual(sql.params, [1, 2])
        self.assertEqual(sql, SQL("SELECT id FROM table WHERE foo=%s AND bar=%s", 1, 2))

        sql = SQL("SELECT id FROM table WHERE %s AND %s", SQL("foo=%s", 1), SQL("bar=%s", 2))
        self.assertEqual(sql.code, "SELECT id FROM table WHERE foo=%s AND bar=%s")
        self.assertEqual(sql.params, [1, 2])
        self.assertEqual(sql, SQL("SELECT id FROM table WHERE foo=%s AND bar=%s", 1, 2))

    def test_sql_with_named_parameters(self):
        sql = SQL("SELECT id FROM table WHERE %(one)s AND bar=%(two)s", one=SQL("foo=%s", 1), two=2)
        self.assertEqual(sql.code, "SELECT id FROM table WHERE foo=%s AND bar=%s")
        self.assertEqual(sql.params, [1, 2])
        self.assertEqual(sql, SQL("SELECT id FROM table WHERE foo=%s AND bar=%s", 1, 2))

        # the parameters are bound locally
        sql = SQL(
            "%s AND %s",
            SQL("foo=%(value)s", value=1),
            SQL("bar=%(value)s", value=2),
        )
        self.assertEqual(sql.code, "foo=%s AND bar=%s")
        self.assertEqual(sql.params, [1, 2])
        self.assertEqual(sql, SQL("foo=%s AND bar=%s", 1, 2))

    def test_complex_sql(self):
        sql = SQL(
            "SELECT %s FROM %s WHERE %s",
            SQL.identifier('id'),
            SQL.identifier('table'),
            SQL(" AND ").join([
                SQL("%s=%s", SQL.identifier('table', 'foo'), 1),
                SQL("%s=%s", SQL.identifier('table', 'bar'), 2),
            ]),
        )
        self.assertEqual(sql.code, 'SELECT "id" FROM "table" WHERE "table"."foo"=%s AND "table"."bar"=%s')
        self.assertEqual(sql.params, [1, 2])
        self.assertEqual(sql, SQL('SELECT "id" FROM "table" WHERE "table"."foo"=%s AND "table"."bar"=%s', 1, 2))
        self.assertEqual(
            repr(sql),
            """SQL('SELECT "id" FROM "table" WHERE "table"."foo"=%s AND "table"."bar"=%s', 1, 2)"""
        )
