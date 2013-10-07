# -*- coding: utf-8 -*-
from collections import namedtuple
from functools import partial
from xml.dom.minidom import getDOMImplementation

from lxml import html

from openerp.tests import common

impl = getDOMImplementation()
document = impl.createDocument(None, None, None)

Request = namedtuple('Request', 'cr uid registry')
class RegistryProxy(object):
    def __init__(self, func):
        self.func = func
    def __getitem__(self, name):
        return self.func(name)

class TestConvertBack(common.TransactionCase):
    def setUp(self):
        super(TestConvertBack, self).setUp()

        self.Converter = self.registry('ir.fields.converter')

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

        rendered = self.registry('ir.qweb').render_tag_field(
            e, {'field': field_value}, '', {
                'record': record,
            })
        element = html.fromstring(
            rendered, parser=html.HTMLParser(encoding='utf-8'))

        column = Model._all_columns[field].column

        from_html = self.Converter.to_field(
            self.cr, self.uid, model, column, 'html')

        value_back, warnings = from_html(element)
        self.assertEqual(warnings, [])

        if isinstance(expected, str):
            expected = expected.decode('utf-8')
        self.assertEqual(value_back, expected)

    def field_roundtrip(self, field, value):
        self.field_rountrip_result(field, value, value)

    def test_integer(self):
        self.field_roundtrip('integer', 42)

    def test_float(self):
        self.field_roundtrip('float', 42.567890)

    def test_numeric(self):
        self.field_roundtrip('numeric', 42.77)

    def test_char(self):
        self.field_roundtrip('char', "foo bar")

        self.field_roundtrip('char', "ⒸⓄⓇⒼⒺ")

    def test_m2o(self):
        Sub = self.registry('website.converter.test.sub')
        sub = partial(Sub.create, self.cr, self.uid)
        ids = [
            sub({'name': "Foo"}),
            sub({'name': "Bar"}),
            sub({'name': "Baz"}),
        ]

        self.field_rountrip_result(
            'many2one',
            ids[2],
            ids[2])

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
