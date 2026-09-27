import ast
import json
import os
import tempfile
import unittest
from subprocess import run, PIPE
from textwrap import dedent

from odoo.tools.which import which

from .test_sql_injection import SQLInjectionLinter
from .common import LintCase

try:
    import pylint
    from pylint.lint import PyLinter
except ImportError:
    pylint = None
    PyLinter = object
try:
    pylint_bin = which('pylint')
except OSError:
    pylint_bin = None


class UnittestLinter(PyLinter):
    current_file = 'not_test_checkers.py'

    def __init__(self):
        self._messages = []
        self.stats = {}
        super().__init__()

    def add_message(self, msg_id, *args, **kwargs):
        self._messages.append(msg_id)

    @staticmethod
    def is_message_enabled(*_args, **kwargs):
        return True


HERE = os.path.dirname(os.path.realpath(__file__))


class TestPylintChecks(LintCase):
    def check(self, test_content, plugins, rules):
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as f:
            self.addCleanup(os.remove, f.name)
            f.write(dedent(test_content).strip())
        res = run(
            [
                pylint_bin,
                f"--rcfile={os.devnull}",
                f"--load-plugins={plugins}",
                "--disable=all",
                f"--enable={rules}",
                "--output-format=json",
                f.name,
            ],
            stdout=PIPE,
            encoding="utf-8",
            env={
                **os.environ,
                "PYTHONPATH": HERE + os.pathsep + os.environ.get("PYTHONPATH", ""),
            },
            check=False,
            shell=False,  # keep False to avoid shell injection
        )
        return res.returncode, json.loads(res.stdout)


@unittest.skipUnless(pylint and pylint_bin, "testing lints requires pylint")
class TestGetTextLint(TestPylintChecks):
    def check(self, testtext):
        return super().check(testtext, "_odoo_checker_gettext", "gettext-placeholders")

    def test_gettext_env(self):
        # check that _ and self.env._ are checked in the same way
        r, errs = self.check("""
        def method(self, vars):
            _("something %s %s", *vars)
        """)
        self.assertTrue(r, "_() should have raised for multiple placeholders")
        self.assertEqual(errs[0]['line'], 2, errs)

        r, errs = self.check("""
        def method(self, vars):
            self.env._("something %s %s", *vars)
        """)
        self.assertTrue(r, "self.env._() should have raised for multiple placeholders")
        self.assertEqual(errs[0]['line'], 2, errs)


class TestSqlLint(LintCase):
    def setUp(self):
        super().setUp()
        self.errors = []
        self.linter = SQLInjectionLinter()
        self.linter.add_error = self.errors.append

    def check_error(self, text, *, message=None):
        tree = ast.parse(dedent(text))
        self.errors.clear()
        self.linter.visit(tree)
        self.assertEqual(len(self.errors), 1, message or "expecting error")

    def check_no_error(self, text, *, message=None):
        tree = ast.parse(dedent(text))
        self.errors.clear()
        self.linter.visit(tree)
        if self.errors:
            self.fail(message or ';'.join(ast.unparse(e) for e in self.errors))

    def test_printf(self):
        self.check_error("""
        def do_the_thing(cr, name):
            cr.execute('select %s from thing' % name)
        """)

        self.check_no_error("""
        def do_the_thing(self):
            self.env.cr.execute("select thing from %s" % self._table)
        """, message="underscore-attributes are allowed")

        self.check_no_error("""
        def do_the_thing(self):
            query = "select thing from %s"
            self.env.cr.execute(query % self._table)
        """, message="underscore-attributes are allowed")

    def test_fstring(self):
        self.check_error("""
        def do_the_thing(cr, name):
            cr.execute(f'select {name} from thing')
        """)

        self.check_no_error("""
        def do_the_thing(cr, name):
            cr.execute(f'select name from thing')
        """, message="unnecessary fstring should be innocuous")

        self.check_error("""
        def do_the_thing(cr, name, value):
            cr.execute(f'select {name} from thing where field = %s', [value])
        """, message="probably has a good reason for the extra arg")

        self.check_no_error("""
        def do_the_thing(self):
            self.env.cr.execute(f'select name from {self._table}')
        """, message='underscore-attributes are allowable')

    def test_sql_injection_detection(self):

        self.check_error("""
        def test():
            arg = "test"
            arg = arg + arg  # lazy
            self.env.cr.execute(arg) #@
        """)

        self.check_error("""
        def test_function9(self,arg):
            my_injection_variable= "aaa" % arg #Uninferable
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable) #@
        """)

        self.check_error("""
        def test_function10(self):
            my_injection_variable= "aaa" + "aaa" #Const - lazy
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable) #@
        """)

        self.check_error("""
        def test_function11(self, arg):
            my_injection_variable= "aaaaaaaa" + arg #Uninferable
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable) #@
        """)

        self.check_error("""
        def test_function12(self):
            # don't concat unknown stuff
            arg1 = "a"
            arg2 = "b" + arg1
            arg3 = arg2 + arg1 + arg2
            arg4 = arg1 + "d"
            my_injection_variable= arg1 + arg2 + arg3 + arg4
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable) #@
        """)

        self.check_error("""
        def test_function1(self, arg):
            my_injection_variable= f"aaaaa{arg}aaa" #Uninferable
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable) #@
        """)

        self.check_no_error("""
        def test_function2(self):
            arg = 'bbb'
            my_injection_variable= f"aaaaa{arg}aaa" #Uninferable
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable) #@
        """)

        # .format() is not supported

        self.check_error("""
        def test_function3(self, arg):
            my_injection_variable= "aaaaaaaa".format() # Const
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable) #@
        """)

        self.check_error("""
        def test_function4(self, arg):
            my_injection_variable= "aaaaaaaa {test}".format(test="aaa")
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable) #@
        """)

        self.check_error("""
        def test_function5(self):
            arg = 'aaa'
            my_injection_variable= "aaaaaaaa {test}".format(test=arg) #Uninferable
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable) #@
        """)

        self.check_error("""
        def test_function6(self,arg):
            my_injection_variable= "aaaaaaaa {test}".format(test="aaa" + arg) #Uninferable
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable) #@
        """)

        self.check_error("""
        def test_function7(self):
            arg = "aaa"
            my_injection_variable= "aaaaaaaa {test}".format(test="aaa" + arg) #Const
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable)#@
        """)

        self.check_error("""
        def test_function8(self):
            global arg
            my_injection_variable= "aaaaaaaa {test}".format(test="aaa" + arg) #Uninferable
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable) #@
        """)

        self.check_error("""
        def test_function9(self,arg):
            my_injection_variable= "aaa" % arg
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable) #@
        """)

        self.check_no_error("""
        def test_function10(self,arg):
            if_else_variable = "aaa" if arg else "bbb" # the two choice of a condition are constant, this is not injectable
            self.env.cr.execute('select * from hello where id = %s' % if_else_variable) #@
        """)

        self.check_no_error("""
        def test_function11(self, arg):
            self.env.cr.execute(SQL('SELECT %d', arg))
        """)

        self.check_no_error("""
        def test_function12(self, arg):
            self.env.cr.execute(SQL('VACUUM FULL %s', SQL.identifier(arg)))
        """)

        self.check_no_error("""
        def test_function13(self, args):
            self.env.cr.execute(SQL('SELECT %s', SQL(',').join(args)))
            self.env.cr.execute(SQL('SELECT %s', SQL(',').join(SQL("%s AS a%s", d, d) for d in range(3))))
        """)

        self.check_no_error("""
        def _search_phone_mobile_search(self, operator, value):
            condition = 'IS NULL' if operator == '=' else 'IS NOT NULL'
            query = '''
                SELECT model.id
                FROM %s model
                WHERE model.phone %s
                AND model.mobile %s
            ''' % (self._table, condition, condition)
            self.env.cr.execute(query) #@
        """)

        self.check_error("""
        def test1(self):
            operator = 'aaa'
            value = 'bbb'
            op1 , val1 = (operator,value)
            self.env.cr.execute('query' + op1) #@
        """)  # Test tuple assignement

        self.check_error("""
        def test2(self):
            operator = 'aaa'
            operator += 'bbb'
            self.env.cr.execute('query' + operator) #@
        """)

        self.check_no_error("""
        def test3(self):
            self.env.cr.execute(f'{self._table}') #@
        """)

        self.check_error("""
        def _init_column(self, column_name):
            query = f'UPDATE "{self._table}" SET "{column_name}" = %s WHERE "{column_name}" IS NULL'
            self.env.cr.execute(query, (value,)) #@
        """)

        self.check_error("""
        def _init_column1(self, column_name):
            query = 'SELECT %(var1)s FROM %(var2)s WHERE %(var3)s' % {'var1': 'field_name','var2': 'table_name','var3': 'where_clause'}
            self.env.cr.execute(query) #@
        """)

        self.check_error("""
        def _graph_data(self, start_date, end_date):

            query = '''SELECT %(x_query)s as x_value, %(y_query)s as y_value
                        FROM %(table)s
                        WHERE team_id = %(team_id)s
                        AND DATE(%(date_column)s) >= %(start_date)s
                        AND DATE(%(date_column)s) <= %(end_date)s
                        %(extra_conditions)s
                        GROUP BY x_value;'''

            # apply rules
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
                'extra_conditions': extra_conditions
            }

            self.env.cr.execute(query, [self.id, start_date, end_date] + where_clause_params) #@
            return self.env.cr.dictfetchall()
        """)

        self.check_error("""
        def first_fun():
            anycall()
            return 'a'
        def injectable():
            cr.execute(first_fun())  #@
        """)
        self.check_error("""
        def second_fun(value):
            anycall() #@
            return value
        def injectable1():
            cr.execute(second_fun('aaaaa'))#@
        """)

        self.check_error("""
        def injectable2(var):
            a = ['a','b']
            cr.execute('a'.join(a))#@
        """)

        self.check_error("""
        def return_tuple(var):
            return 'a',var
        def injectable4(var):
            a, _ =  return_tuple(var)
            cr.execute(a) #@
        """)  # not implemented

        self.check_error("""
        def not_injectable5(var):
            star = ('defined','constant','string')
            cr.execute(*star)#@
        """)  # not implemented

        self.check_error("""
        def injectable6(var):
            star = ('defined','variable','string',var)
            cr.execute(*star)#@
        """)  # not implemented

        self.check_error("""
        def formatNumber(var):
            cr.execute('LIMIT %d'  % var)#@
        """)  # formatter not implemented

        self.check_error("""
        def wrapper1(var):
            query = SQL(var) #@
            return query
        """)

        self.check_error("""
        def wrapper2(var):
            query = tools.SQL(var) #@
            return query
        """)


@unittest.skipUnless(pylint and pylint_bin, "testing lints requires pylint")
class TestI18nChecks(TestPylintChecks):
    def check(self, test_content):
        return super().check(
            test_content, "_odoo_checker_gettext", "missing-gettext,gettext-variable,gettext-placeholders,gettext-repr"
        )

    def test_gettext_variable(self):
        exit_code, errors = self.check(
            """
            some_variable = "Roblox Mini Golf! [ACTUALLY FIXED]"
            _(some_variable)
            _lt(513)
            _lt("string but" + "not static")
            _(f"formatted string")
            """
        )
        self.assertNotEqual(exit_code, os.EX_OK)
        self.assertEqual(len(errors), 4)
        for error in errors:
            self.assertEqual(error["symbol"], "gettext-variable")

    def test_gettext_placeholders(self):
        exit_code, errors = self.check(
            """
            _("shouldn't match escaped %%s %%s")
            """
        )
        self.assertEqual(exit_code, os.EX_OK)
        self.assertFalse(errors)
        exit_code, errors = self.check(
            """
            _("more than one unnamed placeholder: %s %s")
            _lt("with fancy placeholders: %03.14d %-xL")
            """
        )
        self.assertNotEqual(exit_code, os.EX_OK)
        self.assertEqual(len(errors), 2)
        for error in errors:
            self.assertEqual(error["symbol"], "gettext-placeholders")

    def test_gettext_repr(self):
        exit_code, errors = self.check(
            """
            _("%r shouldn't be part of translated strings")
            _lt("%(with_placeholders_in_between)r")
            """
        )
        self.assertNotEqual(exit_code, os.EX_OK)
        self.assertEqual(len(errors), 2)
        for error in errors:
            self.assertEqual(error["symbol"], "gettext-repr")

    def test_missing_gettext_no_errors(self):
        node = """
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
            """

        exit_code, errors = self.check(node)
        self.assertEqual(exit_code, os.EX_OK)
        self.assertEqual(len(errors), 0)

    def test_missing_gettext_catching_errors(self):
        node = """
            UserError('This is not translated')
            exceptions.UserError('This is also not translated')
            UserError(f'This is an f-string')
            raise UserError('This is not translated' + 'This is also not translated')
            some_var = 'random_string'
            raise UserError('This is not translated' and some_var)
            raise UserError('This is not translated' if true else _('This is translated'))
            """

        exit_code, errors = self.check(node)
        self.assertNotEqual(exit_code, os.EX_OK)
        self.assertEqual(len(errors), 6)
        for error in errors:
            self.assertEqual(error["symbol"], "missing-gettext")
