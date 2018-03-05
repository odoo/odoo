import collections
import unittest
from lxml import etree as ET
from lxml.builder import E

import openerp
from openerp.tests import common

from openerp.tools.convert import _eval_xml

Field = E.field
Value = E.value
class TestEvalXML(common.TransactionCase):
    def eval_xml(self, node, obj=None, pool=None, idref=None):
        return _eval_xml(obj, node, pool=pool, cr=self.cr, uid=self.uid,
                         idref=idref, context=None)

    def test_function_eval(self):
        pool = openerp.registry(self.cr.dbname)
        Obj = collections.namedtuple('Obj', ['module', 'pool'])
        obj = Obj('test_convert', pool)

        try:
            test_datetime = ET.XML("<function name='action_test_date' model='test_convert.test_model' eval='[datetime.now().strftime(\"%Y-%m-%d %H:%M:%S\")]'/>")
            self.eval_xml(node=test_datetime, idref={}, pool=obj.pool, obj=obj)
            test_time = ET.XML("<function name='action_test_time' model='test_convert.test_model' eval='[time.strftime(\"%Y-%m-%d %H:%M:%S\")]'/>")
            self.eval_xml(node=test_time, idref={}, pool=obj.pool, obj=obj)
            test_timedelta = ET.XML("<function name='action_test_date' model='test_convert.test_model' eval='[(datetime.today()-timedelta(days=365)).strftime(\"%Y-%m-%d %H:%M:%S\")]'/>")
            self.eval_xml(node=test_timedelta, idref={}, pool=obj.pool, obj=obj)
            test_relativedelta = ET.XML("<function name='action_test_date' model='test_convert.test_model' eval='[(datetime.today()+relativedelta(months=3)).strftime(\"%Y-%m-%d %H:%M:%S\")]'/>")
            self.eval_xml(node=test_relativedelta, idref={}, pool=obj.pool, obj=obj)
            test_timezone = ET.XML("<function name='action_test_timezone' model='test_convert.test_model' eval='[pytz.timezone(\"Asia/Calcutta\")]'/>")
            self.eval_xml(node=test_timezone, idref={}, pool=obj.pool, obj=obj)
        except ValueError as e:
            self.fail(e.message)

    def test_char(self):
        self.assertEqual(
            self.eval_xml(Field("foo")),
            "foo")
        self.assertEqual(
            self.eval_xml(Field("None")),
            "None")

    def test_int(self):
        self.assertIsNone(
            self.eval_xml(Field("None", type='int')),
            "what the fuck?")
        self.assertEqual(
            self.eval_xml(Field(" 42  ", type="int")),
            42)

        with self.assertRaises(ValueError):
            self.eval_xml(Field("4.82", type="int"))

        with self.assertRaises(ValueError):
            self.eval_xml(Field("Whelp", type="int"))

    def test_float(self):
        self.assertEqual(
            self.eval_xml(Field("4.78", type="float")),
            4.78)

        with self.assertRaises(ValueError):
            self.eval_xml(Field("None", type="float"))

        with self.assertRaises(ValueError):
            self.eval_xml(Field("Foo", type="float"))

    def test_list(self):
        self.assertEqual(
            self.eval_xml(Field(type="list")),
            [])

        self.assertEqual(
            self.eval_xml(Field(
                Value("foo"),
                Value("5", type="int"),
                Value("4.76", type="float"),
                Value("None", type="int"),
                type="list"
            )),
            ["foo", 5, 4.76, None])

    def test_file(self):
        Obj = collections.namedtuple('Obj', 'module')
        obj = Obj('test_convert')
        self.assertEqual(
            self.eval_xml(Field('test_file.txt', type='file'), obj),
            'test_convert,test_file.txt')

        with self.assertRaises(IOError):
            self.eval_xml(Field('test_nofile.txt', type='file'), obj)

    @unittest.skip("not tested")
    def test_xml(self):
        pass

    @unittest.skip("not tested")
    def test_html(self):
        pass
