# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import datetime
import os

from odoo.tests import common
from odoo.tools import html_escape as e

directory = os.path.dirname(__file__)

class TestExport(common.TransactionCase):
    _model = None

    def setUp(self):
        super(TestExport, self).setUp()
        self.Model = self.env[self._model]

    def get_field(self, name):
        return self.Model._fields[name]

    def get_converter(self, name, type=None):
        field = self.get_field(name)

        for postfix in (type, field.type, ''):
            fs = ['ir', 'qweb', 'field']
            if postfix is None:
                continue
            if postfix:
                fs.append(postfix)
            try:
                model = self.env['.'.join(fs)]
                break
            except KeyError:
                pass

        def converter(value, options=None, context=None):
            context = context or {}
            record = self.Model.with_context(context).new({name: value})
            return model.with_context(context).record_to_html(record, name, options or {})
        return converter


class TestBasicExport(TestExport):
    _model = 'test_converter.test_model'


class TestCharExport(TestBasicExport):
    def test_char(self):
        converter = self.get_converter('char')

        value = converter('foo')
        self.assertEqual(value, 'foo')

        value = converter("foo<bar>")
        self.assertEqual(value, "foo&lt;bar&gt;")


class TestIntegerExport(TestBasicExport):
    def test_integer(self):
        converter = self.get_converter('integer')

        value = converter(42)
        self.assertEqual(value, "42")


class TestFloatExport(TestBasicExport):
    def setUp(self):
        super(TestFloatExport, self).setUp()
        self.env['res.lang'].browse(1).write({'grouping': '[3,0]'})

    def test_float(self):
        converter = self.get_converter('float')

        value = converter(-42.0)
        self.assertEqual(value, u"\u201142.0")

        value = converter(42.0100)
        self.assertEqual(value, "42.01")

        value = converter(42.01234)
        self.assertEqual(value, "42.01234")

        value = converter(1234567.89)
        self.assertEqual(value, '1,234,567.89')

    def test_numeric(self):
        converter = self.get_converter('numeric')

        value = converter(42.0)
        self.assertEqual(value, '42.00')

        value = converter(42.01234)
        self.assertEqual(value, '42.01')


class TestCurrencyExport(TestExport):
    _model = 'test_converter.monetary'

    def setUp(self):
        super(TestCurrencyExport, self).setUp()
        self.Currency = self.env['res.currency']
        self.base = self.create(self.Currency, name="Source", symbol=u'source')

    def create(self, model, **values):
        return model.create(values)

    def convert(self, obj, dest):
        converter = self.env['ir.qweb.field.monetary']
        options = {
            'widget': 'monetary',
            'display_currency': dest,
        }
        return converter.record_to_html(obj, 'value', options)

    def test_currency_post(self):
        currency = self.create(self.Currency, name="Test", symbol=u"test")
        obj = self.create(self.Model, value=-0.12)

        converted = self.convert(obj, dest=currency)

        self.assertEqual(
            converted, u'<span class="oe_currency_value">\u20110.12</span>'
                       u'\N{NO-BREAK SPACE}{symbol}'.format(
                obj=obj,
                symbol=currency.symbol
            ),)

    def test_currency_pre(self):
        currency = self.create(
            self.Currency, name="Test", symbol=u"test", position='before')
        obj = self.create(self.Model, value=0.12)

        converted = self.convert(obj, dest=currency)

        self.assertEqual(
            converted,
                      u'{symbol}\N{NO-BREAK SPACE}'
                      u'<span class="oe_currency_value">0.12</span>'.format(
                obj=obj,
                symbol=currency.symbol
            ),)

    def test_currency_precision(self):
        """ Precision should be the currency's, not the float field's
        """
        currency = self.create(self.Currency, name="Test", symbol=u"test",)
        obj = self.create(self.Model, value=0.1234567)

        converted = self.convert(obj, dest=currency)

        self.assertEqual(
            converted,
                      u'<span class="oe_currency_value">0.12</span>'
                      u'\N{NO-BREAK SPACE}{symbol}'.format(
                obj=obj,
                symbol=currency.symbol
            ),)


class TestTextExport(TestBasicExport):
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


class TestMany2OneExport(TestBasicExport):
    def test_many2one(self):
        Sub = self.env['test_converter.test_model.sub']
        converter = self.get_converter('many2one')

        value = converter(Sub.create({'name': "Foo"}).id)
        self.assertEqual(value, "Foo")

        value = converter(Sub.create({'name': "Fo<b>o</b>"}).id)
        self.assertEqual(value, "Fo&lt;b&gt;o&lt;/b&gt;")


class TestBinaryExport(TestBasicExport):
    def test_image(self):
        converter = self.env['ir.qweb.field.image']

        with open(os.path.join(directory, 'test_vectors', 'image'), 'rb') as f:
            content = f.read()

        encoded_content = base64.b64encode(content)
        value = converter.value_to_html(encoded_content, {})

        self.assertEqual(
            value, u'<img src="data:image/jpeg;base64,%s">' % encoded_content.decode('ascii'))

        with open(os.path.join(directory, 'test_vectors', 'pdf'), 'rb') as f:
            content = f.read()

        with self.assertRaises(ValueError):
            converter.value_to_html(base64.b64encode(content), {})

        with open(os.path.join(directory, 'test_vectors', 'pptx'), 'rb') as f:
            content = f.read()

        with self.assertRaises(ValueError):
            converter.value_to_html(base64.b64encode(content), {})


class TestSelectionExport(TestBasicExport):
    def test_selection(self):
        converter = self.get_converter('selection')
        value = converter(4)
        self.assertEqual(value, e(u"réponse <D>"))

        converter = self.get_converter('selection_str')
        value = converter('C')
        self.assertEqual(value, u"Qu'est-ce qu'il fout ce maudit pancake, tabernacle ?")


class TestHTMLExport(TestBasicExport):
    def test_html(self):
        converter = self.get_converter('html')

        input = '<span>span</span>'
        value = converter(input)
        self.assertEqual(value, input)


class TestDatetimeExport(TestBasicExport):
    def setUp(self):
        super(TestDatetimeExport, self).setUp()
        # set user tz to known value
        self.env.user.write({'tz': 'Pacific/Niue'})

    def test_date(self):
        converter = self.get_converter('date')

        value = converter('2011-05-03')

        # default lang/format is US
        self.assertEqual(value, '05/03/2011')

    def test_datetime(self):
        converter = self.get_converter('datetime')

        value = converter('2011-05-03 11:12:13')

        # default lang/format is US
        self.assertEqual(value, '05/03/2011 00:12:13')

    def test_custom_format(self):
        converter = self.get_converter('datetime')
        converter2 = self.get_converter('date')
        opts = {'format': 'MMMM d'}

        value = converter('2011-03-02 11:12:13', options=opts)
        value2 = converter2('2001-03-02', options=opts)
        self.assertEqual(
            value,
            'March 2'
        )
        self.assertEqual(
            value2,
            'March 2'
        )


class TestDurationExport(TestBasicExport):
    def setUp(self):
        super(TestDurationExport, self).setUp()
        # needs to have lang installed otherwise falls back on en_US
        self.env['res.lang'].load_lang('fr_FR')

    def test_negative(self):
        converter = self.get_converter('float', 'duration')

        with self.assertRaises(ValueError):
            converter(-4)

    def test_missing_unit(self):
        converter = self.get_converter('float', 'duration')

        with self.assertRaises(ValueError):
            converter(4)

    def test_basic(self):
        converter = self.get_converter('float', 'duration')

        result = converter(4, {'unit': 'hour'}, {'lang': 'fr_FR'})
        self.assertEqual(result, u'4 heures')

        result = converter(50, {'unit': 'second'}, {'lang': 'fr_FR'})
        self.assertEqual(result, u'50 secondes')

    def test_multiple(self):
        converter = self.get_converter('float', 'duration')

        result = converter(1.5, {'unit': 'hour'}, {'lang': 'fr_FR'})
        self.assertEqual(result, u"1 heure 30 minutes")

        result = converter(72, {'unit': 'second'}, {'lang': 'fr_FR'})
        self.assertEqual(result, u"1 minute 12 secondes")


class TestRelativeDatetime(TestBasicExport):
    # not sure how a test based on "current time" should be tested. Even less
    # so as it would mostly be a test of babel...

    def setUp(self):
        super(TestRelativeDatetime, self).setUp()
        # needs to have lang installed otherwise falls back on en_US
        self.env['res.lang'].load_lang('fr_FR')

    def test_basic(self):
        converter = self.get_converter('datetime', 'relative')
        t = datetime.datetime.utcnow() - datetime.timedelta(hours=1)

        result = converter(t, context={'lang': 'fr_FR'})
        self.assertEqual(result, u"il y a 1 heure")
