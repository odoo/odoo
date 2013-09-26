# -*- encoding: utf-8 -*-
import base64
import os

from openerp.tests import common

directory = os.path.dirname(__file__)

class TestHTMLExport(common.TransactionCase):
    def setUp(self):
        super(TestHTMLExport, self).setUp()
        self.Converter = self.registry('ir.fields.converter')
        self.Model = self.registry('test_converter.test_model')

    def get_column(self, name):
        return self.Model._all_columns[name].column

    def get_converter(self, name):
        return self.Converter.from_field(
            self.cr, self.uid, self.Model, self.get_column(name),
            totype="html")

    def test_char(self):
        converter = self.get_converter('char')

        value, warnings = converter('foo')
        self.assertEqual(value, 'foo')
        self.assertEqual(warnings, [])

        value, warnings = converter("foo<bar>")
        self.assertEqual(value, "foo&lt;bar&gt;")
        self.assertEqual(warnings, [])

    def test_integer(self):
        converter = self.get_converter('integer')

        value, warnings = converter(42)
        self.assertEqual(value, "42")
        self.assertEqual(warnings, [])

    def test_float(self):
        converter = self.get_converter('float')

        value, warnings = converter(42.0)
        self.assertEqual(value, "42.0")
        self.assertEqual(warnings, [])

    def test_text(self):
        converter = self.get_converter('text')

        value, warnings = converter("This is my text-kai")
        self.assertEqual(value, "This is my text-kai")
        self.assertEqual(warnings, [])

        value, warnings = converter("""
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
        self.assertEqual(warnings, [])

        value, warnings = converter("""
        fgdkls;hjas;lj <b>fdslkj</b> d;lasjfa lkdja <a href=http://spam.com>lfks</a>
        fldkjsfhs <i style="color: red"><a href="http://spamspam.com">fldskjh</a></i>
        """)
        self.assertEqual(value, """<br>
        fgdkls;hjas;lj &lt;b&gt;fdslkj&lt;/b&gt; d;lasjfa lkdja &lt;a href=http://spam.com&gt;lfks&lt;/a&gt;<br>
        fldkjsfhs &lt;i style=&quot;color: red&quot;&gt;&lt;a href=&quot;http://spamspam.com&quot;&gt;fldskjh&lt;/a&gt;&lt;/i&gt;<br>
        """)
        self.assertEqual(warnings, [])

    def test_many2one(self):
        converter = self.get_converter('many2one')
        Sub = self.registry('test_converter.test_model.sub')

        id0 = Sub.create(self.cr, self.uid, {'name': "Foo"})
        value, warnings = converter(Sub.browse(self.cr, self.uid, id0))
        self.assertEqual(value, "Foo")
        self.assertEqual(warnings, [])

        id1 = Sub.create(self.cr, self.uid, {'name': "Fo<b>o</b>"})
        value, warnings = converter(Sub.browse(self.cr, self.uid, id1))
        self.assertEqual(value, "Fo&lt;b&gt;o&lt;/b&gt;")
        self.assertEqual(warnings, [])

    def test_binary(self):
        converter = self.get_converter('binary')
        with open(os.path.join(directory, 'test_vectors', 'image'), 'rb') as f:
            content = f.read()

            value, warnings = converter(content.encode('base64'))
            self.assertEqual(
                value, '<img src="data:image/jpeg;base64,%s">' % (
                    content.encode('base64')
                ))
            self.assertEqual(warnings, [])

        with open(os.path.join(directory, 'test_vectors', 'pdf'), 'rb') as f:
            content = f.read()

            with self.assertRaises(ValueError):
                converter(content.encode('base64'))

        with open(os.path.join(directory, 'test_vectors', 'pptx'), 'rb') as f:
            content = f.read()

            with self.assertRaises(ValueError):
                converter(content.encode('base64'))

    def test_selection(self):
        converter = self.get_converter('selection')

        value, warnings = converter(2)
        self.assertEqual(value, "réponse B")
        self.assertEqual(warnings, [])

        converter = self.get_converter('selection_str')

        value, warnings = converter('C')
        self.assertEqual(value, "Qu'est-ce qu'il fout ce maudit pancake, tabernacle ?")
        self.assertEqual(warnings, [])

    def test_html(self):
        converter = self.get_converter('html')

        input = '<span>span</span>'
        value, warnings = converter(input)
        self.assertEqual(value, input)
        self.assertEqual(warnings, [])
    # o2m, m2m?
    # reference?
