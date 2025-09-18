"""Unit tests for the custom AST-based lint checkers.

Tests SQL injection detection, gettext usage, and unlink override checking
using stdlib ``ast`` (no pylint/astroid dependency).
"""

import ast
from textwrap import dedent

from odoo.tests import BaseCase

from . import _checker_gettext, _checker_sql, _checker_unlink


class TestSqlLint(BaseCase):
    """Test the SQL injection checker."""

    def _check(self, snippet, filepath="dummy.py"):
        """Parse snippet and return violations."""
        source = dedent(snippet).strip()
        tree = ast.parse(source)
        _checker_sql.annotate_parents(tree)
        checker = _checker_sql.SqlInjectionChecker(filepath)
        return list(checker.check(tree))

    def test_printf(self):
        violations = self._check("""
        def do_the_thing(cr, name):
            cr.execute('select %s from thing' % name)
        """)
        self.assertTrue(violations, "should have noticed the injection")
        self.assertEqual(violations[0].lineno, 2)

        violations = self._check("""
        def do_the_thing(self):
            self.env.cr.execute("select thing from %s" % self._table)
        """)
        self.assertFalse(violations, "underscore-attributes are allowed")

        violations = self._check("""
        def do_the_thing(self):
            query = "select thing from %s"
            self.env.cr.execute(query % self._table)
        """)
        self.assertFalse(violations, "underscore-attributes are allowed")

    def test_fstring(self):
        violations = self._check("""
        def do_the_thing(cr, name):
            cr.execute(f'select {name} from thing')
        """)
        self.assertTrue(violations, "should have noticed the injection")
        self.assertEqual(violations[0].lineno, 2)

        violations = self._check("""
        def do_the_thing(cr, name):
            cr.execute(f'select name from thing')
        """)
        self.assertFalse(violations, "unnecessary fstring should be innocuous")

        violations = self._check("""
        def do_the_thing(self):
            self.env.cr.execute(f'select name from {self._table}')
        """)
        self.assertFalse(violations, "underscore-attributes are allowable")

    def test_const_concat(self):
        """Concatenation of constants is safe."""
        violations = self._check("""
        def test():
            arg = "test"
            arg = arg + arg
            self.env.cr.execute(arg)
        """)
        self.assertFalse(violations)

    def test_percent_with_param(self):
        """% formatting with parameter is injection."""
        violations = self._check("""
        def test_function9(self, arg):
            my_injection_variable = "aaa" % arg
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable)
        """)
        self.assertTrue(violations)

    def test_const_plus_const(self):
        violations = self._check("""
        def test_function10(self):
            my_injection_variable = "aaa" + "aaa"
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable)
        """)
        self.assertFalse(violations)

    def test_const_plus_arg(self):
        violations = self._check("""
        def test_function11(self, arg):
            my_injection_variable = "aaaaaaaa" + arg
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable)
        """)
        self.assertTrue(violations)

    def test_transitive_const_chain(self):
        violations = self._check("""
        def test_function12(self):
            arg1 = "a"
            arg2 = "b" + arg1
            arg3 = arg2 + arg1 + arg2
            arg4 = arg1 + "d"
            my_injection_variable = arg1 + arg2 + arg3 + arg4
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable)
        """)
        self.assertFalse(violations)

    def test_fstring_with_param(self):
        violations = self._check("""
        def test_function1(self, arg):
            my_injection_variable = f"aaaaa{arg}aaa"
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable)
        """)
        self.assertTrue(violations)

    def test_fstring_with_const_var(self):
        violations = self._check("""
        def test_function2(self):
            arg = 'bbb'
            my_injection_variable = f"aaaaa{arg}aaa"
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable)
        """)
        self.assertFalse(violations)

    def test_format_no_args(self):
        violations = self._check("""
        def test_function3(self, arg):
            my_injection_variable = "aaaaaaaa".format()
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable)
        """)
        self.assertFalse(violations)

    def test_format_keyword_const(self):
        violations = self._check("""
        def test_function4(self, arg):
            my_injection_variable = "aaaaaaaa {test}".format(test="aaa")
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable)
        """)
        self.assertFalse(violations)

    def test_format_keyword_const_var(self):
        violations = self._check("""
        def test_function5(self):
            arg = 'aaa'
            my_injection_variable = "aaaaaaaa {test}".format(test=arg)
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable)
        """)
        self.assertFalse(violations)

    def test_format_keyword_nonconst(self):
        violations = self._check("""
        def test_function6(self, arg):
            my_injection_variable = "aaaaaaaa {test}".format(test="aaa" + arg)
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable)
        """)
        self.assertTrue(violations)

    def test_format_keyword_const_chain(self):
        violations = self._check("""
        def test_function7(self):
            arg = "aaa"
            my_injection_variable = "aaaaaaaa {test}".format(test="aaa" + arg)
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable)
        """)
        self.assertFalse(violations)

    def test_format_global_var(self):
        """Global variables are not considered constant."""
        violations = self._check("""
        def test_function8(self):
            global arg
            my_injection_variable = "aaaaaaaa {test}".format(test="aaa" + arg)
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable)
        """)
        self.assertTrue(violations)

    def test_ternary_const_branches(self):
        violations = self._check("""
        def test_function10(self, arg):
            if_else_variable = "aaa" if arg else "bbb"
            self.env.cr.execute('select * from hello where id = %s' % if_else_variable)
        """)
        self.assertFalse(violations)

    def test_real_false_positive_private_function(self):
        """Private function with self._table and const ternary — not injection."""
        violations = self._check("""
        def _search_phone_mobile_search(self, operator, value):
            condition = 'IS NULL' if operator == '=' else 'IS NOT NULL'
            query = '''
                SELECT model.id
                FROM %s model
                WHERE model.phone %s
                AND model.mobile %s
            ''' % (self._table, condition, condition)
            self.env.cr.execute(query)
        """)
        self.assertFalse(violations)

    def test_tuple_assignment(self):
        violations = self._check("""
        def test1(self):
            operator = 'aaa'
            value = 'bbb'
            op1, val1 = (operator, value)
            self.env.cr.execute('query' + op1)
        """)
        self.assertFalse(violations)

    def test_augassign_const(self):
        violations = self._check("""
        def test2(self):
            operator = 'aaa'
            operator += 'bbb'
            self.env.cr.execute('query' + operator)
        """)
        self.assertFalse(violations)

    def test_fstring_self_table(self):
        violations = self._check("""
        def test3(self):
            self.env.cr.execute(f'{self._table}')
        """)
        self.assertFalse(violations)

    def test_private_function_fstring_with_param(self):
        """Private function with f-string and parameter is safe."""
        violations = self._check("""
        def _init_column(self, column_name):
            query = f'UPDATE "{self._table}" SET "{column_name}" = %s WHERE "{column_name}" IS NULL'
            self.env.cr.execute(query, (value,))
        """)
        self.assertFalse(violations)

    def test_dict_format_const(self):
        violations = self._check("""
        def _init_column1(self, column_name):
            query = 'SELECT %(var1)s FROM %(var2)s WHERE %(var3)s' % {'var1': 'field_name', 'var2': 'table_name', 'var3': 'where_clause'}
            self.env.cr.execute(query)
        """)
        self.assertFalse(violations)

    def test_complex_private_function(self):
        """Complex real-world case: private function with dict format."""
        violations = self._check("""
        def _graph_data(self, start_date, end_date):
            query = '''SELECT %(x_query)s as x_value, %(y_query)s as y_value
                        FROM %(table)s
                        WHERE team_id = %(team_id)s
                        AND DATE(%(date_column)s) >= %(start_date)s
                        AND DATE(%(date_column)s) <= %(end_date)s
                        %(extra_conditions)s
                        GROUP BY x_value;'''
            dashboard_graph_model = self._graph_get_model()
            GraphModel = self.env[dashboard_graph_model]
            graph_table = self._graph_get_table(GraphModel)
            extra_conditions = self._extra_sql_conditions()
            where_query = GraphModel._search([])
            from_clause, where_clause, where_clause_params = where_query.get_sql()
            if where_clause:
                extra_conditions += " AND " + where_clause
            query = query % {
                'x_query': self._graph_x_query(),
                'y_query': self._graph_y_query(),
                'table': graph_table,
                'team_id': "%s",
                'date_column': self._graph_date_column(),
                'start_date': "%s",
                'end_date': "%s",
                'extra_conditions': extra_conditions,
            }
            self.env.cr.execute(query, [self.id, start_date, end_date] + where_clause_params)
            return self.env.cr.dictfetchall()
        """)
        self.assertFalse(violations)

    def test_cross_function_const_return(self):
        """Function that returns a constant — safe to use in execute."""
        violations = self._check("""
        def first_fun():
            return 'a'

        def injectable():
            cr.execute(first_fun())
        """)
        self.assertFalse(violations)

    def test_cross_function_param_with_const_call(self):
        """Function returning parameter, called with constant arg — safe."""
        violations = self._check("""
        def second_fun(value):
            return value

        def injectable1():
            cr.execute(second_fun('aaaaa'))
        """)
        self.assertFalse(violations)

    def test_join_const_list(self):
        violations = self._check("""
        def injectable2(var):
            a = ['a', 'b']
            cr.execute('a'.join(a))
        """)
        self.assertFalse(violations)

    def test_cross_function_tuple_position(self):
        """Tuple return with position tracking — position 0 is constant."""
        violations = self._check("""
        def return_tuple(var):
            return 'a', var

        def injectable4(var):
            a, _ = return_tuple(var)
            cr.execute(a)
        """)
        self.assertFalse(violations)

    def test_starred_const_tuple(self):
        violations = self._check("""
        def not_injectable5(var):
            star = ('defined', 'constant', 'string')
            cr.execute(*star)
        """)
        self.assertFalse(violations)

    def test_starred_nonconst_tuple(self):
        violations = self._check("""
        def injectable6(var):
            star = ('defined', 'variable', 'string', var)
            cr.execute(*star)
        """)
        self.assertTrue(violations)

    def test_percent_d_format(self):
        """%d format is always safe (integer only)."""
        violations = self._check("""
        def formatNumber(var):
            cr.execute('LIMIT %d' % var)
        """)
        self.assertFalse(violations)

    def test_sql_call_with_variable(self):
        """SQL() with a variable argument should flag."""
        violations = self._check("""
        def wrapper1(var):
            query = SQL(var)
            return query
        """)
        self.assertTrue(violations)

    def test_tools_sql_call_with_variable(self):
        """tools.SQL() with a variable argument should flag."""
        violations = self._check("""
        def wrapper2(var):
            query = tools.SQL(var)
            return query
        """)
        self.assertTrue(violations)

    def test_skips_test_files(self):
        """Checker should skip files whose name starts with test_."""
        violations = self._check(
            """
        def do_the_thing(cr, name):
            cr.execute('select %s from thing' % name)
        """,
            filepath="test_something.py",
        )
        self.assertFalse(violations, "test files should be skipped")


class TestGetTextLint(BaseCase):
    """Test the gettext checker."""

    def _check(self, snippet, filepath="not_test.py"):
        """Parse snippet and return violations."""
        source = dedent(snippet).strip()
        tree = ast.parse(source)
        return list(_checker_gettext.check(tree, filepath))

    def test_gettext_env(self):
        """Check that _ and self.env._ are checked the same way."""
        violations = self._check("""
        def method(self, vars):
            _("something %s %s", *vars)
        """)
        placeholders = [v for v in violations if v.rule == "gettext-placeholders"]
        self.assertTrue(placeholders, "_() should flag multiple placeholders")

        violations = self._check("""
        def method(self, vars):
            self.env._("something %s %s", *vars)
        """)
        placeholders = [v for v in violations if v.rule == "gettext-placeholders"]
        self.assertTrue(placeholders, "self.env._() should flag multiple placeholders")

    def test_gettext_variable(self):
        violations = self._check("""
        some_variable = "Roblox Mini Golf! [ACTUALLY FIXED]"
        _(some_variable)
        _lt(513)
        _lt("string but" + "not static")
        _(f"formatted string")
        """)
        variable_violations = [v for v in violations if v.rule == "gettext-variable"]
        self.assertEqual(len(variable_violations), 4)

    def test_gettext_placeholders(self):
        violations = self._check("""
        _("shouldn't match escaped %%s %%s")
        """)
        placeholders = [v for v in violations if v.rule == "gettext-placeholders"]
        self.assertFalse(placeholders)

        violations = self._check("""
        _("more than one unnamed placeholder: %s %s")
        _lt("with fancy placeholders: %03.14d %-xL")
        """)
        placeholders = [v for v in violations if v.rule == "gettext-placeholders"]
        self.assertEqual(len(placeholders), 2)

    def test_gettext_repr(self):
        violations = self._check("""
        _("%r shouldn't be part of translated strings")
        _lt("%(with_placeholders_in_between)r")
        """)
        repr_violations = [v for v in violations if v.rule == "gettext-repr"]
        self.assertEqual(len(repr_violations), 2)

    def test_missing_gettext_no_errors(self):
        violations = self._check("""
        raise UserError(_('This is translated'))
        some_var = 'This is not translated'
        raise UserError(some_var)
        raise UserError(some_var + _('This is translated'))
        raise UserError(_('This is translated') and some_var)
        raise UserError(_('This is translated') + "this is not translated")
        raise UserError(_('This is translated') if true else some_var)
        def some_call():
            return _("nothing")
        some_arr = ["random_string", _("another_random_string")]
        raise UserError(some_arr[0])
        """)
        missing = [v for v in violations if v.rule == "missing-gettext"]
        self.assertEqual(len(missing), 0)

    def test_missing_gettext_catching_errors(self):
        violations = self._check("""
        UserError('This is not translated')
        exceptions.UserError('This is also not translated')
        UserError(f'This is an f-string')
        raise UserError('This is not translated' + 'This is also not translated')
        some_var = 'random_string'
        raise UserError('This is not translated' and some_var)
        raise UserError('This is not translated' if true else _('This is translated'))
        """)
        missing = [v for v in violations if v.rule == "missing-gettext"]
        self.assertEqual(len(missing), 6)

    def test_skips_test_files(self):
        """Checker should skip test files."""
        violations = self._check(
            """
        UserError('This is not translated')
        """,
            filepath="/some/path/tests/test_something.py",
        )
        self.assertFalse(violations, "test files should be skipped")


class TestUnlinkLint(BaseCase):
    """Test the unlink override checker."""

    def _check(self, snippet):
        """Parse snippet and return violations."""
        source = dedent(snippet).strip()
        tree = ast.parse(source)
        return list(_checker_unlink.check(tree))

    def test_raise_in_unlink(self):
        violations = self._check("""
        class MyModel(models.Model):
            def unlink(self):
                if self.state == 'posted':
                    raise UserError("Cannot delete posted record")
                return super().unlink()
        """)
        self.assertTrue(violations, "raise inside unlink should be flagged")

    def test_no_raise_in_unlink(self):
        violations = self._check("""
        class MyModel(models.Model):
            def unlink(self):
                self._check_delete()
                return super().unlink()
        """)
        self.assertFalse(violations, "no raise means no violation")

    def test_non_model_class(self):
        violations = self._check("""
        class NotAModel:
            def unlink(self):
                raise ValueError("this is fine")
        """)
        self.assertFalse(violations, "non-model classes should not be flagged")

    def test_model_variants(self):
        """All model base classes should be detected."""
        for base in (
            "models.Model",
            "models.TransientModel",
            "models.AbstractModel",
        ):
            with self.subTest(base=base):
                violations = self._check(f"""
                class MyModel({base}):
                    def unlink(self):
                        raise UserError("nope")
                        return super().unlink()
                """)
                self.assertTrue(violations, f"{base} should be detected as model class")
