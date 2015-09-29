# -*- coding: utf-8 -*-
import textwrap
import unittest

from lxml import etree, html
from lxml.builder import E

from openerp.tests import common
from openerp.addons.base.ir import ir_qweb
from openerp.addons.web_editor.models.ir_qweb import html_to_text


class TestHTMLToText(unittest.TestCase):
    def test_rawstring(self):
        self.assertEqual(
            "foobar",
            html_to_text(E.div("foobar")))

    def test_br(self):
        self.assertEqual(
            "foo\nbar",
            html_to_text(E.div("foo", E.br(), "bar")))

        self.assertEqual(
            "foo\n\nbar\nbaz",
            html_to_text(E.div(
                "foo", E.br(), E.br(),
                "bar", E.br(),
                "baz")))

    def test_p(self):
        self.assertEqual(
            "foo\n\nbar\n\nbaz",
            html_to_text(E.div(
                "foo",
                E.p("bar"),
                "baz")))

        self.assertEqual(
            "foo",
            html_to_text(E.div(E.p("foo"))))

        self.assertEqual(
            "foo\n\nbar",
            html_to_text(E.div("foo", E.p("bar"))))
        self.assertEqual(
            "foo\n\nbar",
            html_to_text(E.div(E.p("foo"), "bar")))

        self.assertEqual(
            "foo\n\nbar\n\nbaz",
            html_to_text(E.div(
                E.p("foo"),
                E.p("bar"),
                E.p("baz"),
            )))

    def test_div(self):
        self.assertEqual(
            "foo\nbar\nbaz",
            html_to_text(E.div(
                "foo",
                E.div("bar"),
                "baz"
            )))

        self.assertEqual(
            "foo",
            html_to_text(E.div(E.div("foo"))))

        self.assertEqual(
            "foo\nbar",
            html_to_text(E.div("foo", E.div("bar"))))
        self.assertEqual(
            "foo\nbar",
            html_to_text(E.div(E.div("foo"), "bar")))

        self.assertEqual(
            "foo\nbar\nbaz",
            html_to_text(E.div(
                "foo",
                E.div("bar"),
                E.div("baz")
            )))

    def test_other_block(self):
        self.assertEqual(
            "foo\nbar\nbaz",
            html_to_text(E.div(
                "foo",
                E.section("bar"),
                "baz"
            )))

    def test_inline(self):
        self.assertEqual(
            "foobarbaz",
            html_to_text(E.div("foo", E.span("bar"), "baz")))

    def test_whitespace(self):
        self.assertEqual(
            "foo bar\nbaz",
            html_to_text(E.div(
                "foo\nbar",
                E.br(),
                "baz")
            ))

        self.assertEqual(
            "foo bar\nbaz",
            html_to_text(E.div(
                E.div(E.span("foo"), " bar"),
                "baz")))


class TestConvertBack(common.TransactionCase):
    def setUp(self):
        super(TestConvertBack, self).setUp()

    def field_rountrip_result(self, field, value, expected):
        model = 'web_editor.converter.test'
        Model = self.registry(model)
        id = Model.create(
            self.cr, self.uid, {
                field: value
            })
        [record] = Model.browse(self.cr, self.uid, [id])

        e = etree.Element('span')
        field_value = 'record.%s' % field
        e.set('t-field', field_value)

        rendered = self.registry('ir.qweb').render_tag_field(
            e, {'field': field_value}, '', ir_qweb.QWebContext(self.cr, self.uid, {
                'record': record,
            }, context={'inherit_branding': True}))
        element = html.fromstring(
            rendered, parser=html.HTMLParser(encoding='utf-8'))

        converter = self.registry('ir.qweb').get_converter_for(
            element.get('data-oe-type'))

        value_back = converter.from_html(
            self.cr, self.uid, model, Model._fields[field], element)

        if isinstance(expected, str):
            expected = expected.decode('utf-8')
        self.assertEqual(value_back, expected)

    def field_roundtrip(self, field, value):
        self.field_rountrip_result(field, value, value)

    def test_integer(self):
        self.field_roundtrip('integer', 42)

    def test_float(self):
        self.field_roundtrip('float', 42.567890)
        self.field_roundtrip('float', 324542.567890)

    def test_numeric(self):
        self.field_roundtrip('numeric', 42.77)

    def test_char(self):
        self.field_roundtrip('char', "foo bar")

        self.field_roundtrip('char', "ⒸⓄⓇⒼⒺ")

    def test_selection(self):
        self.field_roundtrip('selection', 3)

    def test_selection_str(self):
        self.field_roundtrip('selection_str', 'B')

    def test_text(self):
        self.field_roundtrip('text', textwrap.dedent("""\
            You must obey the dance commander
            Givin' out the order for fun
            You must obey the dance commander
            You know that he's the only one
            Who gives the orders here,
            Alright
            Who gives the orders here,
            Alright

            It would be awesome
            If we could dance-a
            It would be awesome, yeah
            Let's take the chance-a
            It would be awesome, yeah
            Let's start the show
            Because you never know
            You never know
            You never know until you go"""))

    def test_m2o(self):
        """ the M2O field conversion (from html) is markedly different from
        others as it directly writes into the m2o and returns nothing at all.
        """
        model = 'web_editor.converter.test'
        field = 'many2one'

        Sub = self.registry('web_editor.converter.test.sub')
        sub_id = Sub.create(self.cr, self.uid, {'name': "Foo"})
        sub2_id = Sub.create(self.cr, self.uid, {'name': "Bar"})

        Model = self.registry(model)
        id = Model.create(self.cr, self.uid, {field: sub_id})
        [record] = Model.browse(self.cr, self.uid, [id])

        e = etree.Element('span')
        field_value = 'record.%s' % field
        e.set('t-field', field_value)

        rendered = self.registry('ir.qweb').render_tag_field(
            e, {'field': field_value}, '', ir_qweb.QWebContext(self.cr, self.uid, {
                'record': record,
            }, context={'inherit_branding': True}))

        element = html.fromstring(rendered, parser=html.HTMLParser(encoding='utf-8'))
        # emulate edition
        element.set('data-oe-many2one-id', str(sub2_id))
        element.text = "New content"

        converter = self.registry('ir.qweb').get_converter_for(
            element.get('data-oe-type'))

        value_back = converter.from_html(
            self.cr, self.uid, model, Model._fields[field], element)

        self.assertIsNone(
            value_back, "the m2o converter should return None to avoid spurious"
                        " or useless writes on the parent record")

        self.assertEqual(
            Sub.browse(self.cr, self.uid, sub_id).name,
            "Foo",
            "element edition can't change directly the m2o record"
        )
        self.assertEqual(
            Model.browse(self.cr, self.uid, id).many2one.name,
            "Bar",
            "element edition should have been change the m2o id"
        )
