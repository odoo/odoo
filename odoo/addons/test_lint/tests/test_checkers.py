import json
import os
import tempfile
import unittest
from subprocess import run, PIPE
from textwrap import dedent

from odoo import tools
from odoo.tests.common import TransactionCase

try:
    import pylint
except ImportError:
    pylint = None
try:
    pylint_bin = tools.which('pylint')
except IOError:
    pylint_bin = None

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
            check=False,
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

        r, errs = self.check("""
        def do_the_thing(cr, name, value):
            cr.execute(f'select {name} from thing where field = %s', [value])
        """)
        self.assertFalse(r, f"probably has a good reason for the extra arg\n{errs}")

        r, errs = self.check("""
        def do_the_thing(self):
            self.env.cr.execute(f'select name from {self._table}')
        """)
        self.assertFalse(r, f'underscore-attributes are allowable\n{errs}')
