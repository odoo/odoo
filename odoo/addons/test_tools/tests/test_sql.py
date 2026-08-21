# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2.errors import CheckViolation

from odoo.tests.common import tagged, BaseCase, TransactionCase
from odoo.tools import SQL, mute_logger, sql


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestSQL(BaseCase):

    def test_sql_empty(self):
        sql = SQL()
        code, params, _flush = sql._sql_tuple
        self.assertEqual(code, "")
        self.assertEqual(params, ())

    def test_sql_bool(self):
        self.assertFalse(SQL())
        self.assertFalse(SQL(""))
        self.assertTrue(SQL("anything"))
        self.assertTrue(SQL("%s", 42))

    def test_sql_with_no_parameter(self):
        sql = SQL("SELECT id FROM table WHERE foo=bar")
        code, params, _flush = sql._sql_tuple
        self.assertEqual(code, "SELECT id FROM table WHERE foo=bar")
        self.assertEqual(params, ())

    def test_sql_with_literal_parameters(self):
        sql = SQL("SELECT id FROM table WHERE foo=%s AND bar=%s", 42, 'baz')
        code, params, _flush = sql._sql_tuple
        self.assertEqual(code, "SELECT id FROM table WHERE foo=%s AND bar=%s")
        self.assertEqual(params, (42, 'baz'))

    def test_sql_with_wrong_pattern(self):
        with self.assertRaises(TypeError):
            SQL("SELECT id FROM table WHERE foo=%s AND bar=%s", 42)

        with self.assertRaises(TypeError):
            SQL("SELECT id FROM table WHERE foo=%s AND bar=%s", 1, 2, 3)

        with self.assertRaises(TypeError):
            SQL("SELECT id FROM table WHERE foo=%s AND bar=%(two)s", 1, two=2)

        with self.assertRaises(KeyError):
            SQL("SELECT id FROM table WHERE foo=%(one)s AND bar=%(two)s", one=1, to=2)

    def test_escape_percent(self):
        def sql_code(*a, **kw):
            return SQL(*a, **kw)._sql_tuple[0]
        self.assertEqual(sql_code("'%%' || %s", 'a'), "'%%' || %s")
        with self.assertRaises(TypeError):
            SQL("'%'")  # not enough arguments
        with self.assertRaises(ValueError):
            SQL("'%' || %s", 'a')  # unescaped percent
        with self.assertRaises(TypeError):
            SQL("'%%' || %s")  # not enough arguments

        self.assertEqual(sql_code("'foo%%'"), "'foo%%'")
        self.assertEqual(sql_code("'foo%%' || %s", 'bar'), "'foo%%' || %s")
        self.assertEqual(sql_code("'foo%%' || %(bar)s", bar='bar'), "'foo%%' || %s")

        self.assertEqual(sql_code("%(foo)s AND bar='baz%%'", foo=SQL("qrux='%%'")), "qrux='%%' AND bar='baz%%'")
        self.assertEqual(sql_code("%(foo)s AND bar='baz%%'", foo=SQL("%s='%%s'", "qrux")), "%s='%%s' AND bar='baz%%'")

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

    def test_sql_hash(self):
        hash(SQL("SELECT id FROM table WHERE x=%s", 5))

    def test_sql_idempotence(self):
        sql1 = SQL("SELECT id FROM table WHERE foo=%s AND bar=%s", 42, 'baz')
        sql2 = SQL(sql1)
        self.assertEqual(sql1, sql2)

    def test_sql_join(self):
        sql = SQL(" AND ").join([])
        code, params, _flush = sql._sql_tuple
        self.assertEqual(code, "")
        self.assertEqual(params, ())
        self.assertEqual(sql, SQL(""))

        sql = SQL(" AND ").join([SQL("foo=%s", 1)])
        code, params, _flush = sql._sql_tuple
        self.assertEqual(code, "foo=%s")
        self.assertEqual(params, (1,))

        sql = SQL(" AND ").join([
            SQL("foo=%s", 1),
            SQL("bar=%s", 2),
            SQL("baz=%s", 3),
        ])
        code, params, _flush = sql._sql_tuple
        self.assertEqual(code, "foo=%s AND bar=%s AND baz=%s")
        self.assertEqual(params, (1, 2, 3))

        sql = SQL(", ").join([1, 2, 3])
        code, params, _flush = sql._sql_tuple
        self.assertEqual(code, "%s, %s, %s")
        self.assertEqual(params, (1, 2, 3))

    def test_sql_identifier(self):
        sql = SQL.identifier('foo')
        code, params, _flush = sql._sql_tuple
        self.assertEqual(code, '"foo"')
        self.assertEqual(params, ())

        sql = SQL.identifier('année')
        code, params, _flush = sql._sql_tuple
        self.assertEqual(code, '"année"')
        self.assertEqual(params, ())

        sql = SQL.identifier('foo', 'bar')
        code, params, _flush = sql._sql_tuple
        self.assertEqual(code, '"foo"."bar"')
        self.assertEqual(params, ())

        with self.assertRaises(AssertionError):
            sql = SQL.identifier('foo"')

        with self.assertRaises(AssertionError):
            sql = SQL.identifier('(SELECT 42)')

        with self.assertRaises(AssertionError):
            sql = SQL.identifier('foo', 'ba"r')

    def test_sql_with_sql_parameters(self):
        sql = SQL("SELECT id FROM table WHERE foo=%s AND %s", 1, SQL("bar=%s", 2))
        code, params, _flush = sql._sql_tuple
        self.assertEqual(code, "SELECT id FROM table WHERE foo=%s AND bar=%s")
        self.assertEqual(params, (1, 2))
        self.assertEqual(sql, SQL("SELECT id FROM table WHERE foo=%s AND bar=%s", 1, 2))

        sql = SQL("SELECT id FROM table WHERE %s AND bar=%s", SQL("foo=%s", 1), 2)
        code, params, _flush = sql._sql_tuple
        self.assertEqual(code, "SELECT id FROM table WHERE foo=%s AND bar=%s")
        self.assertEqual(params, (1, 2))
        self.assertEqual(sql, SQL("SELECT id FROM table WHERE foo=%s AND bar=%s", 1, 2))

        sql = SQL("SELECT id FROM table WHERE %s AND %s", SQL("foo=%s", 1), SQL("bar=%s", 2))
        code, params, _flush = sql._sql_tuple
        self.assertEqual(code, "SELECT id FROM table WHERE foo=%s AND bar=%s")
        self.assertEqual(params, (1, 2))
        self.assertEqual(sql, SQL("SELECT id FROM table WHERE foo=%s AND bar=%s", 1, 2))

    def test_sql_with_named_parameters(self):
        sql = SQL("SELECT id FROM table WHERE %(one)s AND bar=%(two)s", one=SQL("foo=%s", 1), two=2)
        code, params, _flush = sql._sql_tuple
        self.assertEqual(code, "SELECT id FROM table WHERE foo=%s AND bar=%s")
        self.assertEqual(params, (1, 2))
        self.assertEqual(sql, SQL("SELECT id FROM table WHERE foo=%s AND bar=%s", 1, 2))

        # the parameters are bound locally
        sql = SQL(
            "%s AND %s",
            SQL("foo=%(value)s", value=1),
            SQL("bar=%(value)s", value=2),
        )
        code, params, _flush = sql._sql_tuple
        self.assertEqual(code, "foo=%s AND bar=%s")
        self.assertEqual(params, (1, 2))
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
        code, params, _flush = sql._sql_tuple
        self.assertEqual(code, 'SELECT "id" FROM "table" WHERE "table"."foo"=%s AND "table"."bar"=%s')
        self.assertEqual(params, (1, 2))
        self.assertEqual(sql, SQL('SELECT "id" FROM "table" WHERE "table"."foo"=%s AND "table"."bar"=%s', 1, 2))
        self.assertEqual(
            repr(sql),
            """SQL('SELECT "id" FROM "table" WHERE "table"."foo"=%s AND "table"."bar"=%s', 1, 2)"""
        )


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestSqlTools(TransactionCase):

    def test_add_constraint(self):
        definition = "CHECK (name !~ '%')"
        sql.add_constraint(self.env.cr, 'test_tools_partner', 'test_constraint_dummy', definition)

        # ensure the constraint with % works and it's in the DB
        with self.assertRaises(CheckViolation), mute_logger('odoo.sql_db'):
            self.env['test_tools.partner'].create({'name': r'10% partner'})

        # ensure the definitions match
        db_definition = sql.constraint_definition(self.env.cr, 'test_tools_partner', 'test_constraint_dummy')
        self.assertEqual(db_definition, definition)

    def test_add_index(self):
        definition = "(name, id)"
        sql.add_index(self.env.cr, 'test_tools_partner_test_name', 'test_tools_partner', definition, unique=False)

        # check the definition
        db_definition, db_comment = sql.index_definition(self.env.cr, 'test_tools_partner_test_name')
        self.assertIn(definition, db_definition)
        self.assertIs(db_comment, None)

    def test_add_index_escape(self):
        definition = "(id) WHERE name ~ '%'"
        comment = r'some%comment'
        sql.add_index(self.env.cr, 'test_tools_partner_test_percent_escape', 'test_tools_partner', definition, unique=False, comment=comment)

        # ensure the definitions match (definition is the comment if it is set)
        db_definition, db_comment = sql.index_definition(self.env.cr, 'test_tools_partner_test_percent_escape')
        self.assertIn('WHERE', db_definition)  # the definition is rewritten by postgres
        self.assertEqual(db_comment, comment)


class TestFormatQuery(BaseCase):

    def test_empty(self):
        self.assertEqual(sql.format_query(''), ';')

    def test_simple_select(self):
        query = "SELECT id, name FROM res_partner WHERE active = true AND company_id = 1 ORDER BY name"
        self.assertEqual(sql.format_query(query), (
            "SELECT id, name\n"
            "FROM res_partner\n"
            "WHERE active = true\n"
            "    AND company_id = 1\n"
            "ORDER BY name;"
        ))

    def test_or_and_multiple_where_conditions(self):
        query = "SELECT id FROM res_partner WHERE a = 1 AND b = 2 OR c = 3"
        self.assertEqual(sql.format_query(query), (
            "SELECT id\n"
            "FROM res_partner\n"
            "WHERE a = 1\n"
            "    AND b = 2\n"
            "    OR c = 3;"
        ))

    def test_joins(self):
        query = (
            "SELECT f.id FROM foo f "
            "LEFT JOIN bar b ON b.foo_id = f.id "
            "INNER JOIN baz z ON z.foo_id = f.id "
            "WHERE f.active"
        )
        self.assertEqual(sql.format_query(query), (
            "SELECT f.id\n"
            "FROM foo f\n"
            "LEFT JOIN bar b ON b.foo_id = f.id\n"
            "INNER JOIN baz z ON z.foo_id = f.id\n"
            "WHERE f.active;"
        ))

    def test_subquery_indentation(self):
        query = "SELECT id FROM (SELECT id FROM res_partner WHERE active) sub"
        self.assertEqual(sql.format_query(query), (
            "SELECT id\n"
            "FROM (\n"
            "    SELECT id\n"
            "    FROM res_partner\n"
            "    WHERE active) sub;"
        ))

    def test_exists_subquery_indentation(self):
        query = "SELECT id FROM res_partner WHERE EXISTS (SELECT id FROM res_partner WHERE active)"
        self.assertEqual(sql.format_query(query), (
            "SELECT id\n"
            "FROM res_partner\n"
            "WHERE\n"
            "EXISTS (\n"
            "    SELECT id\n"
            "    FROM res_partner\n"
            "    WHERE active);"
        ))

    def test_insert(self):
        query = "INSERT INTO res_partner (name, active) VALUES (%s, %s)"
        self.assertEqual(sql.format_query(query), (
            "INSERT INTO res_partner (name, active)\n"
            "VALUES (%s, %s);"
        ))

    def test_update(self):
        query = "UPDATE res_partner SET name = %s, active = %s WHERE id = %s"
        self.assertEqual(sql.format_query(query), (
            "UPDATE res_partner\n"
            "SET name = %s, active = %s\n"
            "WHERE id = %s;"
        ))

    def test_union(self):
        query = "SELECT id FROM foo UNION ALL SELECT id FROM bar"
        self.assertEqual(sql.format_query(query), (
            "SELECT id\n"
            "FROM foo\n"
            "UNION ALL\n"
            "SELECT id\n"
            "FROM bar;"
        ))

    def test_does_not_break_keywords_inside_string_literals(self):
        query = "SELECT id FROM res_partner WHERE name = 'select from where and or'"
        self.assertEqual(sql.format_query(query), (
            "SELECT id\n"
            "FROM res_partner\n"
            "WHERE name = 'select from where and or';"
        ))

    def test_does_not_break_keywords_inside_quoted_identifiers(self):
        query = 'SELECT "select", "from" FROM "where" WHERE "and" = 1'
        self.assertEqual(sql.format_query(query), (
            'SELECT "select", "from"\n'
            'FROM "where"\n'
            'WHERE "and" = 1;'
        ))

    def test_keyword_substrings_and_dot_notation(self):
        query = "SELECT selection FROM my_table.select WHERE sand = true AND band = false"
        self.assertEqual(sql.format_query(query), (
            "SELECT selection\n"
            "FROM my_table.select\n"
            "WHERE sand = true\n"
            "    AND band = false;"
        ))

    def test_with_cte_and_returning(self):
        query = "WITH x AS (SELECT id FROM foo) UPDATE bar SET active = false WHERE id IN (SELECT id FROM x) RETURNING id"
        self.assertEqual(sql.format_query(query), (
            "WITH x AS (\n"
            "    SELECT id\n"
            "    FROM foo)\n"
            "UPDATE bar\n"
            "SET active = false\n"
            "WHERE id IN (\n"
            "    SELECT id\n"
            "    FROM x)\n"
            "RETURNING id;"
        ))

    def test_deeply_nested_parentheses(self):
        query = "SELECT id FROM (SELECT id FROM (SELECT id FROM foo WHERE active AND id > 0) t1) t2"
        self.assertEqual(sql.format_query(query), (
            "SELECT id\n"
            "FROM (\n"
            "    SELECT id\n"
            "    FROM (\n"
            "        SELECT id\n"
            "        FROM foo\n"
            "        WHERE active\n"
            "            AND id > 0) t1) t2;"
        ))

    def test_preserves_weird_syntax_and_custom_operators(self):
        query = "SELECT payload->>'name' AS user, tags @> ARRAY['vip']::text[] FROM users WHERE email ~* '.*@admin.com' AND score >= 100"

        self.assertEqual(sql.format_query(query), (
            "SELECT payload->>'name' AS user, tags @> ARRAY['vip']::text[]\n"
            "FROM users\n"
            "WHERE email ~* '.*@admin.com'\n"
            "    AND score >= 100;"
        ))

    def test_does_not_break_line_comments(self):
        """Splitting a comment would turn the rest of it into executable SQL."""
        query = "SELECT id FROM res_partner -- the active and recent ones\nWHERE active"
        self.assertEqual(sql.format_query(query), (
            "SELECT id\n"
            "FROM res_partner -- the active and recent ones\n"
            "WHERE active;"
        ))

    def test_comment_marker_inside_a_string_literal(self):
        query = "SELECT id FROM res_partner WHERE name = 'a -- and b' AND c = 1"
        self.assertEqual(sql.format_query(query), (
            "SELECT id\n"
            "FROM res_partner\n"
            "WHERE name = 'a -- and b'\n"
            "    AND c = 1;"
        ))

    def test_multiple_statements(self):
        query = "SELECT id FROM foo; SELECT id FROM bar"
        self.assertEqual(sql.format_query(query), (
            "SELECT id\n"
            "FROM foo;\n"
            "SELECT id\n"
            "FROM bar;"
        ))
