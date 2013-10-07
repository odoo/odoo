# -*- encoding: utf-8 -*-
import base64
import functools
import os

from openerp.tests import common

directory = os.path.dirname(__file__)

class TestHTMLExport(common.TransactionCase):
    def setUp(self):
        super(TestHTMLExport, self).setUp()
        self.Model = self.registry('test_converter.test_model')
        self.columns = self.Model._all_columns

    def get_column(self, name):
        return self.Model._all_columns[name].column

    def get_converter(self, name):
        column = self.get_column(name)
        try:
            model = self.registry('ir.qweb.field.' + column._type)
        except KeyError:
            model = self.registry('ir.qweb.field')

        return lambda value: model.value_to_html(
            self.cr, self.uid, value, column)

    def test_char(self):
        converter = self.get_converter('char')

        value = converter('foo')
        self.assertEqual(value, 'foo')

        value = converter("foo<bar>")
        self.assertEqual(value, "foo&lt;bar&gt;")

    def test_integer(self):
        converter = self.get_converter('integer')

        value = converter(42)
        self.assertEqual(value, "42")

    def test_float(self):
        converter = self.get_converter('float')

        value = converter(42.0)
        self.assertEqual(value, "42.0")

        value = converter(42.0100)
        self.assertEqual(value, "42.01")

        value = converter(42.01234)
        self.assertEqual(value, "42.01234")

    def test_numeric(self):
        converter = self.get_converter('numeric')

        value = converter(42.0)
        self.assertEqual(value, '42.00')

        value = converter(42.01234)
        self.assertEqual(value, '42.01')

    def test_text(self):
        converter = self.get_converter('text')

        value = converter("This is my text-kai")
        self.assertEqual(value, "This is my text-kai")

        value = converter("""
            .  The current line (address) in the buffer.
            $  The last line in the buffer.
            n  The nth, line in the buffer where n is a number in the range [0,$].
            $  The last line in the buffer.
            -  The previous line. This is equivalent to -1 and may be repeated with cumulative effect.
            -n The nth previous line, where n is a non-negative number.
            +  The next line. This is equivalent to +1 and may be repeated with cumulative effect.
        """)
        self.assertEqual(value, """<br>
            .  The current line (address) in the buffer.<br>
            $  The last line in the buffer.<br>
            n  The nth, line in the buffer where n is a number in the range [0,$].<br>
            $  The last line in the buffer.<br>
            -  The previous line. This is equivalent to -1 and may be repeated with cumulative effect.<br>
            -n The nth previous line, where n is a non-negative number.<br>
            +  The next line. This is equivalent to +1 and may be repeated with cumulative effect.<br>
        """)

        value = converter("""
        fgdkls;hjas;lj <b>fdslkj</b> d;lasjfa lkdja <a href=http://spam.com>lfks</a>
        fldkjsfhs <i style="color: red"><a href="http://spamspam.com">fldskjh</a></i>
        """)
        self.assertEqual(value, """<br>
        fgdkls;hjas;lj &lt;b&gt;fdslkj&lt;/b&gt; d;lasjfa lkdja &lt;a href=http://spam.com&gt;lfks&lt;/a&gt;<br>
        fldkjsfhs &lt;i style=&quot;color: red&quot;&gt;&lt;a href=&quot;http://spamspam.com&quot;&gt;fldskjh&lt;/a&gt;&lt;/i&gt;<br>
        """)

    def test_many2one(self):
        converter = self.get_converter('many2one')
        Sub = self.registry('test_converter.test_model.sub')

        id0 = Sub.create(self.cr, self.uid, {'name': "Foo"})
        value = converter(Sub.browse(self.cr, self.uid, id0))
        self.assertEqual(value, "Foo")

        id1 = Sub.create(self.cr, self.uid, {'name': "Fo<b>o</b>"})
        value = converter(Sub.browse(self.cr, self.uid, id1))
        self.assertEqual(value, "Fo&lt;b&gt;o&lt;/b&gt;")

    def test_binary(self):
        converter = self.get_converter('binary')
        with open(os.path.join(directory, 'test_vectors', 'image'), 'rb') as f:
            content = f.read()

            value = converter(content.encode('base64'))
            self.assertEqual(
                value, '<img src="data:image/jpeg;base64,%s">' % (
                    content.encode('base64')
                ))

        with open(os.path.join(directory, 'test_vectors', 'pdf'), 'rb') as f:
            content = f.read()

            with self.assertRaises(ValueError):
                converter(content.encode('base64'))

        with open(os.path.join(directory, 'test_vectors', 'pptx'), 'rb') as f:
            content = f.read()

            with self.assertRaises(ValueError):
                converter(content.encode('base64'))

    def test_selection(self):
        [record] = self.Model.browse(self.cr, self.uid, [self.Model.create(self.cr, self.uid, {
            'selection': 2,
            'selection_str': 'C',
        })])

        column_name = 'selection'
        column = self.get_column(column_name)
        converter = self.registry('ir.qweb.field.selection')

        value = converter.record_to_html(
            self.cr, self.uid, column_name, record, column)
        self.assertEqual(value, "réponse B")

        column_name = 'selection_str'
        column = self.get_column(column_name)
        value = converter.record_to_html(
            self.cr, self.uid, column_name, record, column)
        self.assertEqual(value, "Qu'est-ce qu'il fout ce maudit pancake, tabernacle ?")

    def test_html(self):
        converter = self.get_converter('html')

        input = '<span>span</span>'
        value = converter(input)
        self.assertEqual(value, input)
    # o2m, m2m?
    # reference?
