import json
import os
import tempfile
import unittest

from contextlib import contextmanager
from subprocess import run, PIPE
from textwrap import dedent

from odoo import tools
from odoo.tests.common import TransactionCase

from . import _odoo_checker_sql_injection

try:
    import pylint
    from pylint.lint import PyLinter
except ImportError:
    pylint = None
    PyLinter = object
try:
    pylint_bin = tools.which('pylint')
except IOError:
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
@unittest.skipUnless(pylint and pylint_bin, "testing lints requires pylint")
class TestSqlLint(TransactionCase):
    def check(self, testtext):
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False) as f:
            self.addCleanup(os.remove, f.name)
            f.write(dedent(testtext).strip())

        result = run(
            [pylint_bin,
             f'--rcfile={os.devnull}',
             '--load-plugins=_odoo_checker_sql_injection',
             '--disable=all',
             '--enable=sql-injection',
             '--output-format=json',
             f.name,
            ],
            stdout=PIPE, encoding='utf-8',
            env={
                **os.environ,
                'PYTHONPATH': HERE+os.pathsep+os.environ.get('PYTHONPATH', ''),
            }
        )
        return result.returncode, json.loads(result.stdout)

    def test_printf(self):
        r, [err] = self.check("""
        def do_the_thing(cr, name):
            cr.execute('select %s from thing' % name)
        """)
        self.assertTrue(r, "should have noticed the injection")
        self.assertEqual(err['line'], 2, err)

        r, errs = self.check("""
        def do_the_thing(self):
            self.env.cr.execute("select thing from %s" % self._table)
        """)
        self.assertFalse(r, f"underscore-attributes are allowed\n{errs}")

        r, errs = self.check("""
        def do_the_thing(self):
            query = "select thing from %s"
            self.env.cr.execute(query % self._table)
        """)
        self.assertFalse(r, f"underscore-attributes are allowed\n{errs}")

    def test_fstring(self):
        r, [err] = self.check("""
        def do_the_thing(cr, name):
            cr.execute(f'select {name} from thing')
        """)
        self.assertTrue(r, "should have noticed the injection")
        self.assertEqual(err['line'], 2, err)

        r, errs = self.check("""
        def do_the_thing(cr, name):
            cr.execute(f'select name from thing')
        """)
        self.assertFalse(r, f"unnecessary fstring should be innocuous\n{errs}")

        #r, errs = self.check("""
        #def do_the_thing(cr, name, value):
        #    cr.execute(f'select {name} from thing where field = %s', [value])
        #""")
        #self.assertFalse(r, f"probably has a good reason for the extra arg\n{errs}")

        r, errs = self.check("""
        def do_the_thing(self):
            self.env.cr.execute(f'select name from {self._table}')
        """)
        self.assertFalse(r, f'underscore-attributes are allowable\n{errs}')


    @contextmanager
    def assertMessages(self, *messages):
        self.linter._messages = []
        yield
        self.assertEqual(self.linter._messages, list(messages))

    @contextmanager
    def assertNoMessages(self):
        self.linter._messages = []
        yield
        self.assertEqual(self.linter._messages, [])

    def test_sql_injection_detection(self):
        self.linter = UnittestLinter()
        self.linter.current_file = 'dummy.py' # should not be prefixed by test
        checker = _odoo_checker_sql_injection.OdooBaseChecker(self.linter)

        node = _odoo_checker_sql_injection.astroid.extract_node("""
        def test(): 
            arg = "test"
            arg = arg + arg
            self.env.cr.execute(arg) #@
        """)

        with self.assertNoMessages():
            checker.visit_call(node)

        node = _odoo_checker_sql_injection.astroid.extract_node("""
        def test_function9(self,arg):
            my_injection_variable= "aaa" % arg #Uninferable
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable) #@
        """)

        with self.assertMessages("sql-injection"):
            checker.visit_call(node)

        node = _odoo_checker_sql_injection.astroid.extract_node("""
        def test_function10(self):
            my_injection_variable= "aaa" + "aaa" #Const
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable) #@
        """)
        with self.assertNoMessages():
            checker.visit_call(node)

        node = _odoo_checker_sql_injection.astroid.extract_node("""
        def test_function11(self, arg):
            my_injection_variable= "aaaaaaaa" + arg #Uninferable
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable) #@
        """)

        with self.assertMessages("sql-injection"):
            checker.visit_call(node)

        node = _odoo_checker_sql_injection.astroid.extract_node("""
        def test_function12(self):
            arg1 = "a"
            arg2 = "b" + arg1
            arg3 = arg2 + arg1 + arg2
            arg4 = arg1 + "d"
            my_injection_variable= arg1 + arg2 + arg3 + arg4
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable) #@
        """)

        with self.assertNoMessages():
            checker.visit_call(node)

        node = _odoo_checker_sql_injection.astroid.extract_node("""
        def test_function1(self, arg):
            my_injection_variable= f"aaaaa{arg}aaa" #Uninferable
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable) #@
        """)
        with self.assertMessages("sql-injection"):
            checker.visit_call(node)

        node = _odoo_checker_sql_injection.astroid.extract_node("""
        def test_function2(self):
            arg = 'bbb'
            my_injection_variable= f"aaaaa{arg}aaa" #Uninferable
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable) #@
        """)
        with self.assertNoMessages():
            checker.visit_call(node)

        node = _odoo_checker_sql_injection.astroid.extract_node("""
        def test_function3(self, arg):
            my_injection_variable= "aaaaaaaa".format() # Const
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable) #@
        """)
        with self.assertNoMessages():
            checker.visit_call(node)

        node = _odoo_checker_sql_injection.astroid.extract_node("""
        def test_function4(self, arg):
            my_injection_variable= "aaaaaaaa {test}".format(test="aaa") 
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable) #@
        """)
        with self.assertNoMessages():
            checker.visit_call(node)

        node = _odoo_checker_sql_injection.astroid.extract_node("""
        def test_function5(self):
            arg = 'aaa'
            my_injection_variable= "aaaaaaaa {test}".format(test=arg) #Uninferable
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable) #@
        """)
        with self.assertNoMessages():
            checker.visit_call(node)

        node = _odoo_checker_sql_injection.astroid.extract_node("""
        def test_function6(self,arg):
            my_injection_variable= "aaaaaaaa {test}".format(test="aaa" + arg) #Uninferable
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable) #@
        """)
        with self.assertMessages("sql-injection"):
            checker.visit_call(node)

        node = _odoo_checker_sql_injection.astroid.extract_node("""
        def test_function7(self):
            arg = "aaa"
            my_injection_variable= "aaaaaaaa {test}".format(test="aaa" + arg) #Const
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable)#@
        """)
        with self.assertNoMessages():
            checker.visit_call(node)

        node = _odoo_checker_sql_injection.astroid.extract_node("""
        def test_function8(self):
            global arg
            my_injection_variable= "aaaaaaaa {test}".format(test="aaa" + arg) #Uninferable
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable) #@
        """)
        with self.assertMessages("sql-injection"):
            checker.visit_call(node)

        #TODO
        #node = _odoo_checker_sql_injection.astroid.extract_node("""
        #def test_function(self):
        #    def test():
        #        return "hello world"
        #    my_injection_variable= "aaaaaaaa {test}".format(test=test()) #Const
        #    self.env.cr.execute('select * from hello where id = %s' % my_injection_variable) #@
        #""")
        #with self.assertNoMessages():
        #    checker.visit_call(node)

        node = _odoo_checker_sql_injection.astroid.extract_node("""
        def test_function9(self,arg):
            my_injection_variable= "aaa" % arg
            self.env.cr.execute('select * from hello where id = %s' % my_injection_variable) #@
        """)

        with self.assertMessages("sql-injection"):
            checker.visit_call(node)

        node = _odoo_checker_sql_injection.astroid.extract_node("""
        def test_function10(self,arg):
            if_else_variable = "aaa" if arg else "bbb" # the two choice of a condition are constant, this is not injectable
            self.env.cr.execute('select * from hello where id = %s' % if_else_variable) #@
        """)

        with self.assertMessages():
            checker.visit_call(node)

        node = _odoo_checker_sql_injection.astroid.extract_node("""
        def _search_phone_mobile_search(self, operator, value):
  
            condition = 'IS NULL' if operator == '=' else 'IS NOT NULL'
            query = '''
                SELECT model.id
                FROM %s model
                WHERE model.phone %s
                AND model.mobile %s
            ''' % (self._table, condition, condition)
            self.env.cr.execute(query) #@
        """) #Real false positive example from the code
        with self.assertMessages():
            checker.visit_call(node)

        node = _odoo_checker_sql_injection.astroid.extract_node("""
        def test1(self):
            operator = 'aaa' 
            value = 'bbb'
            op1 , val1 = (operator,value)
            self.env.cr.execute('query' + op1) #@
        """) #Test tuple assignement
        with self.assertMessages():
            checker.visit_call(node)

        node = _odoo_checker_sql_injection.astroid.extract_node("""
        def test2(self):
            operator = 'aaa' 
            operator += 'bbb'
            self.env.cr.execute('query' + operator) #@
        """)
        with self.assertMessages():
            checker.visit_call(node)

        node = _odoo_checker_sql_injection.astroid.extract_node("""
        def test3(self):
            self.env.cr.execute(f'{self._table}') #@
        """)
        with self.assertMessages():
            checker.visit_call(node)

        node = _odoo_checker_sql_injection.astroid.extract_node("""
        def _init_column(self, column_name):
            query = f'UPDATE "{self._table}" SET "{column_name}" = %s WHERE "{column_name}" IS NULL'
            self._cr.execute(query, (value,)) #@
        """) #Test private function arg should not flag
        with self.assertMessages():
            checker.visit_call(node)

        node = _odoo_checker_sql_injection.astroid.extract_node("""
        def _init_column1(self, column_name):
            query = 'SELECT %(var1)s FROM %(var2)s WHERE %(var3)s' % {'var1': 'field_name','var2': 'table_name','var3': 'where_clause'}
            self._cr.execute(query) #@
        """)
        with self.assertMessages():
            checker.visit_call(node)

        node = _odoo_checker_sql_injection.astroid.extract_node("""
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
            where_query = GraphModel._where_calc([])  
            GraphModel._apply_ir_rules(where_query, 'read')
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

            self._cr.execute(query, [self.id, start_date, end_date] + where_clause_params) #@
            return self.env.cr.dictfetchall()
        """)
        with self.assertMessages():
            checker.visit_call(node)

        node = _odoo_checker_sql_injection.astroid.extract_node("""
        def first_fun():
            anycall() #@
            return 'a'
        """)
        with self.assertMessages():
            checker.visit_call(node)
        node = _odoo_checker_sql_injection.astroid.extract_node("""
        def second_fun(value):
            anycall() #@
            return value
        """)
        with self.assertMessages():
            checker.visit_call(node)
        node = _odoo_checker_sql_injection.astroid.extract_node("""
        def injectable():
            cr.execute(first_fun())#@
        """)
        with self.assertMessages():
            checker.visit_call(node)
        node = _odoo_checker_sql_injection.astroid.extract_node("""
        def injectable1():
            cr.execute(second_fun('aaaaa'))#@
        """)
        with self.assertMessages():
            checker.visit_call(node)

        node = _odoo_checker_sql_injection.astroid.extract_node("""
        def injectable2(var):
            a = ['a','b']
            cr.execute('a'.join(a))#@
        """)
        with self.assertMessages():
            checker.visit_call(node)

        node = _odoo_checker_sql_injection.astroid.extract_node("""
        def return_tuple(var):
            return 'a',var
        """)
        with self.assertMessages():
            checker.visit_call(node)

        node = _odoo_checker_sql_injection.astroid.extract_node("""
        def injectable4(var):
            a, _ =  return_tuple(var)
            cr.execute(a)#@
        """)
        with self.assertMessages():
            checker.visit_call(node)
        node = _odoo_checker_sql_injection.astroid.extract_node("""
        def not_injectable5(var):
            star = ('defined','constant','string')
            cr.execute(*star)#@
        """)
        with self.assertMessages():
            checker.visit_call(node)

        node = _odoo_checker_sql_injection.astroid.extract_node("""
        def injectable6(var):
            star = ('defined','variable','string',var)
            cr.execute(*star)#@
        """)
        with self.assertMessages("sql-injection"):
            checker.visit_call(node)

        node = _odoo_checker_sql_injection.astroid.extract_node("""
        def formatNumber(var):
            cr.execute('LIMIT %d'  % var)#@
        """)
        with self.assertMessages():
            checker.visit_call(node)
