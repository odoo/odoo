# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import collections
import unittest

from lxml import etree as ET
from lxml.builder import E

import odoo
from odoo.tests import common
from odoo.tools.convert import xml_import, _eval_xml, _process_raw_csv

Field = E.field
Value = E.value

class TestEvalXML(common.TransactionCase):
    def eval_xml(self, node, obj=None):
        return _eval_xml(obj, node, self.env)

    def test_function_eval(self):
        def id_get(): pass
        Obj = collections.namedtuple('Obj', ['module', 'idref', 'id_get'])
        obj = Obj('test_convert', {}, id_get)

        try:
            test_datetime = ET.XML("<function name='action_test_date' model='test_convert.test_model' eval='[datetime.now().strftime(\"%Y-%m-%d %H:%M:%S\")]'/>")
            self.eval_xml(node=test_datetime, obj=obj)
            test_time = ET.XML("<function name='action_test_time' model='test_convert.test_model' eval='[time.strftime(\"%Y-%m-%d %H:%M:%S\")]'/>")
            self.eval_xml(node=test_time, obj=obj)
            test_timedelta = ET.XML("<function name='action_test_date' model='test_convert.test_model' eval='[(datetime.today()-timedelta(days=365)).strftime(\"%Y-%m-%d %H:%M:%S\")]'/>")
            self.eval_xml(node=test_timedelta, obj=obj)
            test_relativedelta = ET.XML("<function name='action_test_date' model='test_convert.test_model' eval='[(datetime.today()+relativedelta(months=3)).strftime(\"%Y-%m-%d %H:%M:%S\")]'/>")
            self.eval_xml(node=test_relativedelta, obj=obj)
            test_timezone = ET.XML("<function name='action_test_timezone' model='test_convert.test_model' eval='[pytz.timezone(\"Asia/Calcutta\")]'/>")
            self.eval_xml(node=test_timezone, obj=obj)
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
        Obj = collections.namedtuple('Obj', ['module', 'idref'])
        obj = Obj('test_convert', None)
        self.assertEqual(
            self.eval_xml(Field('test_file.txt', type='file'), obj),
            'test_convert,test_file.txt')

        with self.assertRaises(IOError):
            self.eval_xml(Field('test_nofile.txt', type='file'), obj)

    def test_function(self):
        obj = xml_import(self.cr, 'test_convert', None, 'init')

        # pass args in eval
        xml = E.function(
            model="test_convert.usered",
            name="model_method",
            eval="[1, 2]",
        )
        rec, args, kwargs = self.eval_xml(xml, obj)
        self.assertEqual(rec.env.context, self.env.context)
        self.assertEqual(rec.ids, [])
        self.assertEqual(args, (1, 2))
        self.assertEqual(kwargs, {})

        xml = E.function(
            model="test_convert.usered",
            name="method",
            eval="[1, 2]",
        )
        rec, args, kwargs = self.eval_xml(xml, obj)
        self.assertEqual(rec.env.context, self.env.context)
        self.assertEqual(rec.ids, [1])
        self.assertEqual(args, (2,))
        self.assertEqual(kwargs, {})

        # pass args in child elements
        xml = E.function(
            E.value(eval="1"), E.value(eval="2"),
            model="test_convert.usered",
            name="model_method",
        )
        rec, args, kwargs = self.eval_xml(xml, obj)
        self.assertEqual(rec.env.context, self.env.context)
        self.assertEqual(rec.ids, [])
        self.assertEqual(args, (1, 2))
        self.assertEqual(kwargs, {})

        xml = E.function(
            E.value(eval="1"), E.value(eval="2"),
            model="test_convert.usered",
            name="method",
        )
        rec, args, kwargs = self.eval_xml(xml, obj)
        self.assertEqual(rec.env.context, self.env.context)
        self.assertEqual(rec.ids, [1])
        self.assertEqual(args, (2,))
        self.assertEqual(kwargs, {})

    def test_function_kwargs(self):
        obj = xml_import(self.cr, 'test_convert', None, 'init')

        # pass args and kwargs in child elements
        xml = E.function(
            E.value(eval="1"), E.value(name="foo", eval="2"),
            model="test_convert.usered",
            name="model_method",
        )
        rec, args, kwargs = self.eval_xml(xml, obj)
        self.assertEqual(rec.env.context, self.env.context)
        self.assertEqual(rec.ids, [])
        self.assertEqual(args, (1,))
        self.assertEqual(kwargs, {'foo': 2})

        xml = E.function(
            E.value(eval="1"), E.value(name="foo", eval="2"),
            model="test_convert.usered",
            name="method",
        )
        rec, args, kwargs = self.eval_xml(xml, obj)
        self.assertEqual(rec.env.context, self.env.context)
        self.assertEqual(rec.ids, [1])
        self.assertEqual(args, ())
        self.assertEqual(kwargs, {'foo': 2})

        # pass args and context in kwargs
        xml = E.function(
            E.value(eval="1"), E.value(name="context", eval="{'foo': 2}"),
            model="test_convert.usered",
            name="model_method",
        )
        rec, args, kwargs = self.eval_xml(xml, obj)
        self.assertEqual(rec.env.context, {'foo': 2})
        self.assertEqual(rec.ids, [])
        self.assertEqual(args, (1,))
        self.assertEqual(kwargs, {})

        xml = E.function(
            E.value(eval="1"), E.value(name="context", eval="{'foo': 2}"),
            model="test_convert.usered",
            name="method",
        )
        rec, args, kwargs = self.eval_xml(xml, obj)
        self.assertEqual(rec.env.context, {'foo': 2})
        self.assertEqual(rec.ids, [1])
        self.assertEqual(args, ())
        self.assertEqual(kwargs, {})

    def test_function_function(self):
        obj = xml_import(self.cr, 'test_convert', None, 'init')

        xml = E.function(
            E.function(model="test_convert.usered", name="search", eval="[[]]"),
            model="test_convert.usered",
            name="method",
        )
        rec, args, kwargs = self.eval_xml(xml, obj)
        self.assertEqual(rec.env.context, {})
        self.assertEqual(rec.ids, [])
        self.assertEqual(args, ())
        self.assertEqual(kwargs, {})

    @unittest.skip("not tested")
    def test_xml(self):
        pass

    @unittest.skip("not tested")
    def test_html(self):
        pass


@common.tagged('csv_comments')
class TestCSVProcessing(common.TransactionCase):

    def setUp(self):
        super().setUp()
        self.csv = b"""field1,field2,field3\n"""

    def test_invalid_00(self):
        self.csv += b""""#this",should,be,invalid"""
        with self.assertRaises(ValueError):
            _process_raw_csv(self.csv, 'test_invalid_00.csv')

    def test_valid_00(self):
        self.csv += b"""" # this is valid though",no,problem"""
        _, datas = _process_raw_csv(self.csv, 'test_valid_00.csv')
        self.assertEqual(len(datas), 1)
        self.assertEqual(len(datas[0]), 3)
        self.assertEqual(datas[0][0], " # this is valid though")

    def test_valid_10(self):
        self.csv += b"""# this is a very valid comment"""
        _, datas = _process_raw_csv(self.csv, 'test_valid_10.csv')
        self.assertFalse(any(datas))

    def test_valid_20(self):
        self.csv += b"""what,about,"this"\n# this should still be a valid comment"""
        _, datas = _process_raw_csv(self.csv, 'test_valid_20.csv')
        self.assertEqual(len(datas), 1)
        self.assertEqual(datas[0], ["what", "about", "this"])

    def test_valid_30(self):
        self.csv += b"""# this comment has lots of , and, also, ","," and #,#,#"""
        _, datas = _process_raw_csv(self.csv, 'test_valid_30.csv')
        self.assertFalse(any(datas))

    def test_valid_40(self):
        self.csv += b"""#this\n#is\n#a\n#valid\n#multi-line\n#comment"""
        _, datas = _process_raw_csv(self.csv, 'test_valid_40.csv')
        self.assertFalse(any(datas))

    def test_valid_50(self):
        self.csv += b"""these,are,multiple\n#comments\nscattered,accross,"multiple"\n#different\nlines,ok,boomer"""
        _, datas = _process_raw_csv(self.csv, 'test_valid_50.csv')
        self.assertEqual(len(datas), 3)
        self.assertEqual(datas[0], ['these', 'are', 'multiple'])
        self.assertEqual(' '.join(datas[-1][1:]), "ok boomer")

    def test_valid_60(self):
        self.csv += b""""\n#this should",be,valid"""
        _, datas = _process_raw_csv(self.csv, 'test_valid_60')
        self.assertEqual(len(datas), 1)
        self.assertEqual(datas[0][0], "\n#this should")

    def test_valid_70(self):
        self.csv += b""""\n\n\n\n#this should also",be,valid"""
        _, datas = _process_raw_csv(self.csv, 'test_valid_70.csv')
        self.assertEqual(len(datas), 1)
        self.assertEqual(datas[0][0], "\n\n\n\n#this should also")
