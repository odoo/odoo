# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import collections
import unittest

from lxml import etree as ET
from lxml.builder import E

import odoo
from odoo.tests import common
from odoo.tools.convert import xml_import, _eval_xml

Field = E.field
Value = E.value

class TestEvalXML(common.TransactionCase):
    def eval_xml(self, node, obj=None):
        return _eval_xml(obj, node, self.env)

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

    def test_o2m_sub_records(self):
        # patch the model's class with a proxy that copies the argument
        Model = self.registry['test_convert.test_model']
        call_args = []

        def _load_records(self, data_list, update=False):
            call_args.append(data_list)
            # pylint: disable=bad-super-call
            return super(Model, self)._load_records(data_list, update=update)

        self.patch(Model, '_load_records', _load_records)

        # import a record with a subrecord
        xml = ET.fromstring("""
            <record id="test_convert.test_o2m_record" model="test_convert.test_model">
                <field name="usered_ids">
                    <record id="test_convert.test_o2m_subrecord" model="test_convert.usered">
                        <field name="name">subrecord</field>
                    </record>
                </field>
            </record>
        """.strip())
        obj = xml_import(self.cr, 'test_convert', None, 'init')
        obj._tag_record(xml)

        # check that field 'usered_ids' is not passed
        self.assertEqual(len(call_args), 1)
        for data in call_args[0]:
            self.assertNotIn('usered_ids', data['values'],
                             "Unexpected value in O2M When loading XML with sub records")

    def test_o2m_sub_records_noupdate(self):
        xml = ET.fromstring("""
            <data noupdate="1">
              <record id="test_convert.test_o2m_record_noup" model="test_convert.test_model">
                <field name="usered_ids">
                    <record id="test_convert.test_o2m_subrecord_noup" model="test_convert.usered">
                        <field name="name">subrecord</field>
                    </record>
                </field>
              </record>
            </data>
        """.strip())

        xmlids = {"test_convert.test_o2m_record_noup", "test_convert.test_o2m_subrecord_noup"}

        # create records
        xml_import(self.cr, 'test_convert', None, 'init').parse(xml)

        # clear loaded xmlids
        self.registry.loaded_xmlids.difference_update(xmlids)

        # reload the xml in update mode
        idref = {}
        xml_import(self.cr, 'test_convert', idref, 'update').parse(xml)

        self.assertEqual(set(idref.keys()), xmlids)
        self.assertTrue(self.registry.loaded_xmlids.issuperset(xmlids))

    @unittest.skip("not tested")
    def test_xml(self):
        pass

    def test_html(self):
        self.assertEqual(
            self.eval_xml(Field(ET.fromstring(
            """<parent>
                <t t-if="True">
                    <t t-out="'text'"/>
                </t>
                <t t-else="">
                    <t t-out="'text2'"></t>
                </t>
            </parent>"""), type="html")),
            """<parent>
                <t t-if="True">
                    <t t-out="'text'"></t>
                </t>
                <t t-else="">
                    <t t-out="'text2'"></t>
                </t>
            </parent>""",
            "Evaluating an HTML field should give empty nodes instead of self-closing tags"
        )
