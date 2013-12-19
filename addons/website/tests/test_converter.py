# -*- coding: utf-8 -*-
from functools import partial
from xml.dom.minidom import getDOMImplementation

from lxml import html

from openerp.tests import common
from openerp.addons.base.ir import ir_qweb

impl = getDOMImplementation()
document = impl.createDocument(None, None, None)

class TestConvertBack(common.TransactionCase):
    def setUp(self):
        super(TestConvertBack, self).setUp()

    def field_rountrip_result(self, field, value, expected):
        model = 'website.converter.test'
        Model = self.registry(model)
        id = Model.create(
            self.cr, self.uid, {
                field: value
            })
        [record] = Model.browse(self.cr, self.uid, [id])

        e = document.createElement('span')
        field_value = 'record.%s' % field
        e.setAttribute('t-field', field_value)

        rendered = self.registry('website.qweb').render_tag_field(
            e, {'field': field_value}, '', ir_qweb.QWebContext(self.cr, self.uid, {
                'record': record,
            }))
        element = html.fromstring(
            rendered, parser=html.HTMLParser(encoding='utf-8'))

        column = Model._all_columns[field].column
        converter = self.registry('website.qweb').get_converter_for(
            element.get('data-oe-type'))

        value_back = converter.from_html(
            self.cr, self.uid, model, column, element)

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
        self.field_roundtrip('text', """
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
            You never know until you go
        """)

    def test_m2o(self):
        """ the M2O field conversion (from html) is markedly different from
        others as it directly writes into the m2o and returns nothing at all.
        """
        model = 'website.converter.test'
        field = 'many2one'

        Sub = self.registry('website.converter.test.sub')
        sub_id = Sub.create(self.cr, self.uid, {'name': "Foo"})

        Model = self.registry(model)
        id = Model.create(self.cr, self.uid, {field: sub_id})
        [record] = Model.browse(self.cr, self.uid, [id])

        e = document.createElement('span')
        field_value = 'record.%s' % field
        e.setAttribute('t-field', field_value)

        rendered = self.registry('website.qweb').render_tag_field(
            e, {'field': field_value}, '', ir_qweb.QWebContext(self.cr, self.uid, {
                'record': record,
            }))

        element = html.fromstring(rendered, parser=html.HTMLParser(encoding='utf-8'))
        # emulate edition
        element.text = "New content"

        column = Model._all_columns[field].column
        converter = self.registry('website.qweb').get_converter_for(
            element.get('data-oe-type'))

        value_back = converter.from_html(
            self.cr, self.uid, model, column, element)

        self.assertIsNone(
            value_back, "the m2o converter should return None to avoid spurious"
                        " or useless writes on the parent record")

        self.assertEqual(
            Sub.browse(self.cr, self.uid, sub_id).name,
            "New content",
            "element edition should have been written directly to the m2o record"
        )
