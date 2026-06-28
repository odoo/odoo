import datetime
import re

from odoo.tests import common, tagged

from odoo.addons.base.tests.files import JPG_B64, JPG_RAW, PDF_RAW, PPTX_RAW


class TestExport(common.TransactionCase):
    _model = 'test_ir_qweb_fields'

    def setUp(self):
        super().setUp()
        self.Model = self.env[self._model]

    def get_converter(self, name, type=None, escape_white_space=True):
        field = self.Model._fields[name]

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

            if not escape_white_space:
                return model.with_context(context).record_to_html(record, name, options or {})

            # normalize non-newline spaces: some versions of babel use regular
            # spaces while others use non-break space when formatting time deltas
            # to the French locale
            return re.sub(
                r'[^\S\n\r]',  # no \p{Zs}
                ' ',
                model.with_context(context).record_to_html(record, name, options or {}),
            )
        return converter


@tagged('at_install', '-post_install')
class TestCharExport(TestExport):
    def test_char(self):
        converter = self.get_converter('char')

        self.assertEqual(converter('foo'), 'foo')
        self.assertEqual(converter('foo<bar>'), 'foo&lt;bar&gt;')


@tagged('at_install', '-post_install')
class TestIntegerExport(TestExport):
    def test_integer(self):
        converter = self.get_converter('integer')

        self.assertEqual(converter(42), "42")


@tagged('at_install', '-post_install')
class TestFloatExport(TestExport):
    def test_float(self):
        converter = self.get_converter('float')

        self.assertEqual(converter(42.0), '42.0')
        self.assertEqual(converter(-42.0), '-\N{ZERO WIDTH NO-BREAK SPACE}42.0')
        self.assertEqual(converter(42.0100), '42.01')
        self.assertEqual(converter(42.01234), '42.01234')
        self.assertEqual(converter(42.12345), '42.12345')
        self.assertEqual(converter(1234567.89), '1,234,567.89')

    def test_float_precision(self):
        converter = self.get_converter('float')

        self.assertEqual(converter(42.0, {'precision': 4}), '42.0000')
        self.assertEqual(converter(42.12345, {'precision': 4}), '42.1235')

    def test_float_decimal_precision(self):
        self.env['decimal.precision'].create({
            'name': '2 digits',
            'digits': 2,
        })
        self.env['decimal.precision'].create({
            'name': '6 digits',
            'digits': 6,
        })

        converter = self.get_converter('float')

        self.assertEqual(converter(42.0, {'decimal_precision': '2 digits'}), '42.00')
        self.assertEqual(converter(42.12345, {'decimal_precision': '2 digits'}), '42.12')

        self.assertEqual(converter(42.0, {'decimal_precision': '6 digits'}), '42.000000')
        self.assertEqual(converter(42.12345, {'decimal_precision': '6 digits'}), '42.123450')

    def test_numeric(self):
        converter = self.get_converter('numeric')

        self.assertEqual(converter(42.0), '42.00')
        self.assertEqual(converter(42.01234), '42.01')
        self.assertEqual(converter(42.12345), "42.12")


@tagged('at_install', '-post_install')
class TestCurrencyExport(TestExport):
    def test_currency_post(self):
        currency = self.env['res.currency'].create({'name': 'Test', 'symbol': 'test'})
        converter = self.get_converter('monetary', 'monetary', escape_white_space=False)

        self.assertEqual(
            converter(-0.12, {'widget': 'monetary', 'display_currency': currency}),
            f'<span class="oe_currency_value">-\N{ZERO WIDTH NO-BREAK SPACE}0.12</span>\N{NO-BREAK SPACE}{currency.symbol}'
        )

    def test_currency_pre(self):
        currency = self.env['res.currency'].create({'name': 'Test', 'symbol': 'test', 'position': 'before'})
        converter = self.get_converter('monetary', 'monetary', escape_white_space=False)

        self.assertEqual(
            converter(0.12, {'widget': 'monetary', 'display_currency': currency}),
            f'{currency.symbol}\N{NO-BREAK SPACE}<span class="oe_currency_value">0.12</span>'
        )

    def test_currency_precision(self):
        currency = self.env['res.currency'].create({'name': 'Test', 'symbol': 'test'})
        converter = self.get_converter('monetary', 'monetary', escape_white_space=False)

        # Should user the currency's precision, not the float field's.
        self.assertEqual(
            converter(0.1234567, {'widget': 'monetary', 'display_currency': currency}),
            f'<span class="oe_currency_value">0.12</span>\N{NO-BREAK SPACE}{currency.symbol}'
        )


@tagged('at_install', '-post_install')
class TestTextExport(TestExport):
    maxDiff = None

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
        fldkjsfhs &lt;i style=&#34;color: red&#34;&gt;&lt;a href=&#34;http://spamspam.com&#34;&gt;fldskjh&lt;/a&gt;&lt;/i&gt;<br>
        """)


@tagged('at_install', '-post_install')
class TestMany2OneExport(TestExport):
    def test_many2one(self):
        many2one = self.env['test_ir_qweb_fields.relations']
        converter = self.get_converter('many2one')

        self.assertEqual(converter(many2one.create({'name': "Foo"}).id), "Foo")
        self.assertEqual(converter(many2one.create({'name': "Fo<b>o</b>"}).id), "Fo&lt;b&gt;o&lt;/b&gt;")


@tagged('at_install', '-post_install')
class TestImageExport(TestExport):
    def test_image(self):
        converter = self.env['ir.qweb.field.image']

        self.assertEqual(converter.value_to_html(JPG_RAW, {}), f'<img src="data:image/jpg;base64,{JPG_B64}">')

        with self.assertRaises(ValueError):
            converter.value_to_html(PDF_RAW, {})

        with self.assertRaises(ValueError):
            converter.value_to_html(PPTX_RAW, {})


@tagged('at_install', '-post_install')
class TestSelectionExport(TestExport):
    def test_selection(self):
        converter = self.get_converter('selection')

        self.assertEqual(converter('C'), "Qu&#39;est-ce qu&#39;il fout ce maudit pancake, tabernacle ?")


@tagged('at_install', '-post_install')
class TestHTMLExport(TestExport):
    def test_html(self):
        converter = self.get_converter('html')

        self.assertEqual(converter('<span>span</span>'), '<span>span</span>')


@tagged('at_install', '-post_install')
class TestDateExport(TestExport):
    def test_date(self):
        converter = self.get_converter('date')

        # default lang/format is US
        self.assertEqual(converter('2011-05-03'), '05/03/2011')

    def test_date_format(self):
        converter = self.get_converter('date')

        # default lang/format is US
        self.assertEqual(converter('2001-03-02', {'format': 'MMMM d'}), 'March 2')


@tagged('at_install', '-post_install')
class TestDatetimeExport(TestExport):
    def test_datetime(self):
        self.env.user.write({'tz': 'Pacific/Niue'})  # Set user tz to known value.

        converter = self.get_converter('datetime')

        self.assertEqual(converter('2011-05-03 11:12:13'), '05/03/2011 12:12:13 AM')

    def test_datetime_format(self):
        self.env.user.write({'tz': 'Pacific/Niue'})  # Set user tz to known value.

        converter = self.get_converter('datetime')

        self.assertEqual(converter('2011-03-02 11:12:13', {'format': 'MMMM d'}), 'March 2')


@tagged('at_install', '-post_install')
class TestDurationExport(TestExport):
    def test_duration(self):
        converter = self.get_converter('float', 'duration')

        self.assertEqual(converter(4), '4 seconds')

    def test_negative_duration(self):
        converter = self.get_converter('float', 'duration')

        self.assertEqual(converter(-4), '- 4 seconds')

        # With round
        self.assertEqual(
            converter(-4.678, {'unit': 'year', 'round': 'hour'}),
            '- 4 years 8 months 1 week 11 hours'
        )

        # With digital
        self.assertEqual(
            converter(-90, {'unit': 'minute', 'round': 'minute', 'digital': True}),
            '-01:30'
        )

    def test_duration_unit(self):
        converter = self.get_converter('float', 'duration')

        self.assertEqual(converter(4, {'unit': 'hour'}), '4 hours')
        self.assertEqual(converter(1.5, {'unit': 'hour'}), "1 hour 30 minutes")
        self.assertEqual(converter(50, {'unit': 'second'}), '50 seconds')
        self.assertEqual(converter(72, {'unit': 'second'}), "1 minute 12 seconds")

    def test_duration_translation(self):
        self.env['res.lang']._activate_lang('fr_FR')

        converter = self.get_converter('float', 'duration')

        self.assertEqual(
            converter(-4.678, {'unit': 'year', 'round': 'hour'}, {'lang': 'fr_FR'}),
            '- 4 ans 8 mois 1 semaine 11 heures'
        )


@tagged('at_install', '-post_install')
class TestRelativeDatetime(TestExport):
    def test_relative_datetime(self):
        self.env['res.lang']._activate_lang('fr_FR')

        converter = self.get_converter('datetime', 'relative')
        time = datetime.datetime.now() - datetime.timedelta(hours=1)

        self.assertEqual(converter(time, context={'lang': 'fr_FR'}), "il y a 1 heure")
