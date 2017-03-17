# -*- encoding: utf-8 -*-
import json
import os
import datetime

from lxml import etree

from openerp.tests import common
from openerp.tools import html_escape as e
from openerp.addons.base.ir import ir_qweb

directory = os.path.dirname(__file__)

class TestExport(common.TransactionCase):
    _model = None

    def setUp(self):
        super(TestExport, self).setUp()
        self.Model = self.registry(self._model)

    def get_field(self, name):
        return self.Model._fields[name]

    def get_converter(self, name, type=None):
        field = self.get_field(name)

        for postfix in type, field.type, '':
            fs = ['ir', 'qweb', 'field']
            if postfix is None: continue
            if postfix: fs.append(postfix)

            try:
                model = self.registry('.'.join(fs))
                break
            except KeyError: pass

        return lambda value, options=None, context=None: e(model.value_to_html(
            self.cr, self.uid, value, field, options=options, context=context))

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
        self.registry('res.lang').write(self.cr, self.uid, [1], {
            'grouping': '[3,0]'
        })

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
        self.Currency = self.registry('res.currency')
        self.base = self.create(self.Currency, name="Source", symbol=u'source')

    def create(self, model, context=None, **values):
        return model.browse(
            self.cr, self.uid,
            model.create(self.cr, self.uid, values, context=context),
            context=context)

    def convert(self, obj, dest):
        converter = self.registry('ir.qweb.field.monetary')
        options = {
            'widget': 'monetary',
            'display_currency': 'c2'
        }
        context = dict(inherit_branding=True)
        converted = converter.to_html(
            self.cr, self.uid, 'value', obj, options,
            etree.Element('span'),
            {'field': 'obj.value', 'field-options': json.dumps(options)},
            '', ir_qweb.QWebContext(self.cr, self.uid, {'obj': obj, 'c2': dest, }),
            context=context,
        )
        return converted

    def test_currency_post(self):
        currency = self.create(self.Currency, name="Test", symbol=u"test")
        obj = self.create(self.Model, value=-0.12)

        converted = self.convert(obj, dest=currency)

        self.assertEqual(
            converted,
            '<span data-oe-model="{obj._model._name}" data-oe-id="{obj.id}" '
                  'data-oe-field="value" data-oe-type="monetary" '
                  'data-oe-expression="obj.value">'
                      u'<span class="oe_currency_value">\u20110.12</span>'
                      u'\N{NO-BREAK SPACE}{symbol}</span>'.format(
                obj=obj,
                symbol=currency.symbol.encode('utf-8')
            ).encode('utf-8'),)

    def test_currency_pre(self):
        currency = self.create(
            self.Currency, name="Test", symbol=u"test", position='before')
        obj = self.create(self.Model, value=0.12)

        converted = self.convert(obj, dest=currency)

        self.assertEqual(
            converted,
            '<span data-oe-model="{obj._model._name}" data-oe-id="{obj.id}" '
                  'data-oe-field="value" data-oe-type="monetary" '
                  'data-oe-expression="obj.value">'
                      u'{symbol}\N{NO-BREAK SPACE}'
                      '<span class="oe_currency_value">0.12</span>'
                      '</span>'.format(
                obj=obj,
                symbol=currency.symbol.encode('utf-8')
            ).encode('utf-8'),)

    def test_currency_precision(self):
        """ Precision should be the currency's, not the float field's
        """
        currency = self.create(self.Currency, name="Test", symbol=u"test",)
        obj = self.create(self.Model, value=0.1234567)

        converted = self.convert(obj, dest=currency)

        self.assertEqual(
            converted,
            '<span data-oe-model="{obj._model._name}" data-oe-id="{obj.id}" '
                  'data-oe-field="value" data-oe-type="monetary" '
                  'data-oe-expression="obj.value">'
                      '<span class="oe_currency_value">0.12</span>'
                      u'\N{NO-BREAK SPACE}{symbol}</span>'.format(
                obj=obj,
                symbol=currency.symbol.encode('utf-8')
            ).encode('utf-8'),)

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
        Sub = self.registry('test_converter.test_model.sub')


        id0 = self.Model.create(self.cr, self.uid, {
            'many2one': Sub.create(self.cr, self.uid, {'name': "Foo"})
        })
        id1 = self.Model.create(self.cr, self.uid, {
            'many2one': Sub.create(self.cr, self.uid, {'name': "Fo<b>o</b>"})
        })

        def converter(record):
            model = self.registry('ir.qweb.field.many2one')
            return e(model.record_to_html(self.cr, self.uid, 'many2one', record))

        value = converter(self.Model.browse(self.cr, self.uid, id0))
        self.assertEqual(value, "Foo")

        value = converter(self.Model.browse(self.cr, self.uid, id1))
        self.assertEqual(value, "Fo&lt;b&gt;o&lt;/b&gt;")

class TestBinaryExport(TestBasicExport):
    def test_image(self):
        field = self.get_field('binary')
        converter = self.registry('ir.qweb.field.image')

        with open(os.path.join(directory, 'test_vectors', 'image'), 'rb') as f:
            content = f.read()

        encoded_content = content.encode('base64')
        value = e(converter.value_to_html(
            self.cr, self.uid, encoded_content, field))
        self.assertEqual(
            value, '<img src="data:image/jpeg;base64,%s">' % (
                encoded_content
            ))

        with open(os.path.join(directory, 'test_vectors', 'pdf'), 'rb') as f:
            content = f.read()

        with self.assertRaises(ValueError):
            e(converter.value_to_html(
                self.cr, self.uid, 'binary', content.encode('base64'), field))

        with open(os.path.join(directory, 'test_vectors', 'pptx'), 'rb') as f:
            content = f.read()

        with self.assertRaises(ValueError):
            e(converter.value_to_html(
                self.cr, self.uid, 'binary', content.encode('base64'), field))

class TestSelectionExport(TestBasicExport):
    def test_selection(self):
        [record] = self.Model.browse(self.cr, self.uid, [self.Model.create(self.cr, self.uid, {
            'selection': 2,
            'selection_str': 'C',
        })])

        converter = self.registry('ir.qweb.field.selection')

        field_name = 'selection'
        value = converter.record_to_html(self.cr, self.uid, field_name, record)
        self.assertEqual(value, "réponse B")

        field_name = 'selection_str'
        value = converter.record_to_html(self.cr, self.uid, field_name, record)
        self.assertEqual(value, "Qu'est-ce qu'il fout ce maudit pancake, tabernacle ?")

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
        Users = self.registry('res.users')
        Users.write(self.cr, self.uid, self.uid, {
            'tz': 'Pacific/Niue'
        }, context=None)

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
        self.registry('res.lang').load_lang(self.cr, self.uid, 'fr_FR')

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
        self.registry('res.lang').load_lang(self.cr, self.uid, 'fr_FR')

    def test_basic(self):
        converter = self.get_converter('datetime', 'relative')
        t = datetime.datetime.utcnow() - datetime.timedelta(hours=1)

        result = converter(t, context={'lang': 'fr_FR'})
        self.assertEqual(result, u"il y a 1 heure")
