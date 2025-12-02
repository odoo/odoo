# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import datetime
import os.path

import pytz

from odoo.tests.common import BaseCase, TransactionCase
from odoo.tools import config, misc, urls
from odoo.tools.mail import validate_url
from odoo.tools.misc import file_open, file_path, merge_sequences, remove_accents


class TestMergeSequences(BaseCase):
    def test_merge_sequences(self):
        # base case
        seq = merge_sequences(['A', 'B', 'C'])
        self.assertEqual(seq, ['A', 'B', 'C'])

        # 'Z' can be anywhere
        seq = merge_sequences(['A', 'B', 'C'], ['Z'])
        self.assertEqual(seq, ['A', 'B', 'C', 'Z'])

        # 'Y' must precede 'C';
        seq = merge_sequences(['A', 'B', 'C'], ['Y', 'C'])
        self.assertEqual(seq, ['A', 'B', 'Y', 'C'])

        # 'X' must follow 'A' and precede 'C'
        seq = merge_sequences(['A', 'B', 'C'], ['A', 'X', 'C'])
        self.assertEqual(seq, ['A', 'B', 'X', 'C'])

        # all cases combined
        seq = merge_sequences(
            ['A', 'B', 'C'],
            ['Z'],                  # 'Z' can be anywhere
            ['Y', 'C'],             # 'Y' must precede 'C';
            ['A', 'X', 'Y'],        # 'X' must follow 'A' and precede 'Y'
        )
        self.assertEqual(seq, ['A', 'B', 'X', 'Y', 'C', 'Z'])


class TestFormatLangDate(TransactionCase):
    def test_00_accepted_types(self):
        self.env.user.tz = 'Europe/Brussels'
        datetime_str = '2017-01-31 12:00:00'
        date_datetime = datetime.datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
        date_date = date_datetime.date()
        date_str = '2017-01-31'
        time_part = datetime.time(16, 30, 22)
        t_medium = 'h:mm:ss a'
        medium = f'MMM d, YYYY, {t_medium}'

        self.assertEqual(misc.format_date(self.env, date_datetime), '01/31/2017')
        self.assertEqual(misc.format_date(self.env, date_date), '01/31/2017')
        self.assertEqual(misc.format_date(self.env, date_str), '01/31/2017')
        self.assertEqual(misc.format_date(self.env, ''), '')
        self.assertEqual(misc.format_date(self.env, False), '')
        self.assertEqual(misc.format_date(self.env, None), '')

        self.assertEqual(misc.format_datetime(self.env, date_datetime, dt_format=medium), 'Jan 31, 2017, 1:00:00 PM')
        self.assertEqual(misc.format_datetime(self.env, datetime_str, dt_format=medium), 'Jan 31, 2017, 1:00:00 PM')
        self.assertEqual(misc.format_datetime(self.env, '', dt_format=medium), '')
        self.assertEqual(misc.format_datetime(self.env, False, dt_format=medium), '')
        self.assertEqual(misc.format_datetime(self.env, None, dt_format=medium), '')

        self.assertEqual(misc.format_time(self.env, time_part, time_format=t_medium), '4:30:22 PM')
        self.assertEqual(misc.format_time(self.env, '', time_format=t_medium), '')
        self.assertEqual(misc.format_time(self.env, False, time_format=t_medium), '')
        self.assertEqual(misc.format_time(self.env, None, time_format=t_medium), '')

    def test_01_code_and_format(self):
        date_str = '2017-01-31'
        lang = self.env['res.lang']

        # Activate French and Simplified Chinese (test with non-ASCII characters)
        lang._activate_lang('fr_FR')
        lang._activate_lang('zh_CN')

        # -- test `date`
        # Change a single parameter
        self.assertEqual(misc.format_date(lang.with_context(lang='fr_FR').env, date_str), '31/01/2017')
        self.assertEqual(misc.format_date(lang.env, date_str, lang_code='fr_FR'), '31/01/2017')
        self.assertEqual(misc.format_date(lang.env, date_str, date_format='MMM d, y'), 'Jan 31, 2017')

        # Change 2 parameters
        self.assertEqual(misc.format_date(lang.with_context(lang='zh_CN').env, date_str, lang_code='fr_FR'), '31/01/2017')
        self.assertEqual(misc.format_date(lang.with_context(lang='zh_CN').env, date_str, date_format='MMM d, y'), u'1\u6708 31, 2017')
        self.assertEqual(misc.format_date(lang.env, date_str, lang_code='fr_FR', date_format='MMM d, y'), 'janv. 31, 2017')

        # Change 3 parameters
        self.assertEqual(misc.format_date(lang.with_context(lang='zh_CN').env, date_str, lang_code='en_US', date_format='MMM d, y'), 'Jan 31, 2017')

        # -- test `datetime`
        datetime_str = '2017-01-31 10:33:00'
        # Change languages and timezones
        datetime_us_str = misc.format_datetime(lang.with_context(lang='en_US').env, datetime_str, tz='Europe/Brussels')
        self.assertNotEqual(misc.format_datetime(lang.with_context(lang='fr_FR').env, datetime_str, tz='Europe/Brussels'), datetime_us_str)
        self.assertNotEqual(misc.format_datetime(lang.with_context(lang='zh_CN').env, datetime_str, tz='America/New_York'), datetime_us_str)

        # Change language, timezone and format
        self.assertEqual(misc.format_datetime(lang.with_context(lang='fr_FR').env, datetime_str, tz='America/New_York', dt_format='dd/MM/YYYY HH:mm'), '31/01/2017 05:33')
        self.assertEqual(misc.format_datetime(lang.with_context(lang='en_US').env, datetime_str, tz='Europe/Brussels', dt_format='MMM d, y'), 'Jan 31, 2017')

        # Check given `lang_code` overwites context lang
        fmt_fr = 'dd MMMM YYYY à HH:mm:ss Z'
        fmt_us = "MMMM dd, YYYY 'at' hh:mm:ss a Z"
        self.assertEqual(misc.format_datetime(lang.env, datetime_str, tz='Europe/Brussels', dt_format=fmt_fr, lang_code='fr_FR'), '31 janvier 2017 à 11:33:00 +0100')
        self.assertEqual(misc.format_datetime(lang.with_context(lang='zh_CN').env, datetime_str, tz='Europe/Brussels', dt_format=fmt_us, lang_code='en_US'), 'January 31, 2017 at 11:33:00 AM +0100')

        # -- test `time`
        time_part = datetime.time(16, 30, 22)
        time_part_tz = datetime.time(16, 30, 22, tzinfo=pytz.timezone('America/New_York'))  # 4:30 PM timezoned

        self.assertEqual(misc.format_time(lang.with_context(lang='fr_FR').env, time_part, time_format='HH:mm:ss'), '16:30:22')
        self.assertEqual(misc.format_time(lang.with_context(lang='zh_CN').env, time_part, time_format="ah:m:ss"), '\u4e0b\u53484:30:22')

        # Check format in different languages
        self.assertEqual(misc.format_time(lang.with_context(lang='fr_FR').env, time_part, time_format='HH:mm'), '16:30')
        self.assertEqual(misc.format_time(lang.with_context(lang='zh_CN').env, time_part, time_format='ah:mm'), '\u4e0b\u53484:30')

        # Check timezoned time part
        self.assertEqual(misc.format_time(lang.with_context(lang='fr_FR').env, time_part_tz, time_format='HH:mm:ss Z'), '16:30:22 -0504')
        self.assertEqual(misc.format_time(lang.with_context(lang='zh_CN').env, time_part_tz, time_format='zzzz ah:mm:ss'), '\u5317\u7f8e\u4e1c\u90e8\u6807\u51c6\u65f6\u95f4\u0020\u4e0b\u53484:30:22')

        #Check timezone conversion in format_time
        self.assertEqual(misc.format_time(lang.with_context(lang='fr_FR').env, datetime_str, 'Europe/Brussels', time_format='HH:mm:ss Z'), '11:33:00 +0100')
        self.assertEqual(misc.format_time(lang.with_context(lang='fr_FR').env, datetime_str, 'America/New_York', time_format='HH:mm:ss Z'), '05:33:00 -0500')

        # Check given `lang_code` overwites context lang
        self.assertEqual(misc.format_time(lang.with_context(lang='fr_FR').env, time_part, time_format='ah:mm', lang_code='zh_CN'), '\u4e0b\u53484:30')
        self.assertEqual(misc.format_time(lang.with_context(lang='zh_CN').env, time_part, time_format='ah:mm', lang_code='fr_FR'), 'PM4:30')

    def test_02_tz(self):
        self.env.user.tz = 'Europe/Brussels'
        datetime_str = '2016-12-31 23:55:00'
        date_datetime = datetime.datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")

        # While London is still in 2016, Brussels is already in 2017
        self.assertEqual(misc.format_date(self.env, date_datetime), '01/01/2017')

        # Force London timezone
        date_datetime = date_datetime.replace(tzinfo=pytz.UTC)
        self.assertEqual(misc.format_date(self.env, date_datetime), '12/31/2016', "User's tz must be ignored when tz is specifed in datetime object")


class TestCallbacks(BaseCase):
    def test_callback(self):
        log = []
        callbacks = misc.Callbacks()

        # add foo
        def foo():
            log.append("foo")

        callbacks.add(foo)

        # add bar
        @callbacks.add
        def bar():
            log.append("bar")

        # add foo again
        callbacks.add(foo)

        # this should call foo(), bar(), foo()
        callbacks.run()
        self.assertEqual(log, ["foo", "bar", "foo"])

        # this should do nothing
        callbacks.run()
        self.assertEqual(log, ["foo", "bar", "foo"])

    def test_aggregate(self):
        log = []
        callbacks = misc.Callbacks()

        # register foo once
        @callbacks.add
        def foo():
            log.append(callbacks.data["foo"])

        # aggregate data
        callbacks.data.setdefault("foo", []).append(1)
        callbacks.data.setdefault("foo", []).append(2)
        callbacks.data.setdefault("foo", []).append(3)

        # foo() is called once
        callbacks.run()
        self.assertEqual(log, [[1, 2, 3]])
        self.assertFalse(callbacks.data)

        callbacks.run()
        self.assertEqual(log, [[1, 2, 3]])

    def test_reentrant(self):
        log = []
        callbacks = misc.Callbacks()

        # register foo that runs callbacks
        @callbacks.add
        def foo():
            log.append("foo1")
            callbacks.run()
            log.append("foo2")

        @callbacks.add
        def bar():
            log.append("bar")

        # both foo() and bar() are called once
        callbacks.run()
        self.assertEqual(log, ["foo1", "bar", "foo2"])

        callbacks.run()
        self.assertEqual(log, ["foo1", "bar", "foo2"])


class TestRemoveAccents(BaseCase):
    def test_empty_string(self):
        self.assertEqual(remove_accents(False), False)
        self.assertEqual(remove_accents(''), '')
        self.assertEqual(remove_accents(None), None)

    def test_latin(self):
        self.assertEqual(remove_accents('Niño Hernández'), 'Nino Hernandez')
        self.assertEqual(remove_accents('Anaïs Clémence'), 'Anais Clemence')

    def test_non_latin(self):
        self.assertEqual(remove_accents('العربية'), 'العربية')
        self.assertEqual(remove_accents('русский алфавит'), 'русскии алфавит')


class TestAddonsFileAccess(BaseCase):

    def assertCannotAccess(self, path, ExceptionType=OSError, filter_ext=None, check_exists=True):
        with self.assertRaises(ExceptionType):
            file_path(path, filter_ext=filter_ext, check_exists=check_exists)

    def assertCanRead(self, path, needle='', mode='r', filter_ext=None):
        with file_open(path, mode, filter_ext) as f:
            self.assertIn(needle, f.read())

    def assertCannotRead(self, path, ExceptionType=OSError, filter_ext=None):
        with self.assertRaises(ExceptionType):
            file_open(path, filter_ext=filter_ext).close()

    def test_file_path(self):
        # absolute path
        self.assertEqual(__file__, file_path(__file__))
        self.assertEqual(__file__, file_path(__file__, filter_ext=None)) # means "no filter" too
        self.assertEqual(__file__, file_path(__file__, filter_ext=('.py',)))

        # directory target is ok
        self.assertEqual(os.path.dirname(__file__), file_path(os.path.join(__file__, '..')))

        # relative path
        relpath = os.path.join(*(__file__.split(os.sep)[-3:])) # 'base/tests/test_misc.py'
        self.assertEqual(__file__, file_path(relpath))
        self.assertEqual(__file__, file_path(relpath, filter_ext=('.py',)))

        # leading 'addons/' is ignored if present
        self.assertTrue(file_path("addons/web/__init__.py"))
        relpath = os.path.join('addons', relpath) # 'addons/base/tests/test_misc.py'
        self.assertEqual(__file__, file_path(relpath))

        # files in root_path are allowed
        self.assertTrue(file_path('tools/misc.py'))

        # absolute or relative inexisting files are ok
        self.assertTrue(file_path(config.root_path + '/__inexisting', check_exists=False))
        self.assertTrue(file_path('base/__inexisting_file', check_exists=False))

        # errors when outside addons_paths
        self.assertCannotAccess('/doesnt/exist')
        self.assertCannotAccess('/tmp')
        self.assertCannotAccess('../../../../../../../../../tmp')
        self.assertCannotAccess(os.path.join(__file__, '../../../../../'))

        # data_dir is forbidden
        self.assertCannotAccess(config['data_dir'])

        # errors for illegal extensions
        self.assertCannotAccess(__file__, ValueError, filter_ext=('.png',))
        # file doesnt exist but has wrong extension
        self.assertCannotAccess(__file__.replace('.py', '.foo'), ValueError, filter_ext=('.png',))

    def test_file_open(self):
        # The needle includes UTF8 so we test reading non-ASCII files at the same time.
        # This depends on the system locale and is harder to unit test, but if you manage to run the
        # test with a non-UTF8 locale (`LC_ALL=fr_FR.iso8859-1 python3...`) it should not crash ;-)
        test_needle = "A needle with non-ascii bytes: ♥"

        # absolute path
        self.assertCanRead(__file__, test_needle)
        self.assertCanRead(__file__, test_needle.encode(), mode='rb')
        self.assertCanRead(__file__, test_needle.encode(), mode='rb', filter_ext=('.py',))

        # directory target *is* an error
        with self.assertRaises(IsADirectoryError):
            file_open(os.path.join(__file__, '..'))

        # relative path
        relpath = os.path.join(*(__file__.split(os.sep)[-3:])) # 'base/tests/test_misc.py'
        self.assertCanRead(relpath, test_needle)
        self.assertCanRead(relpath, test_needle.encode(), mode='rb')
        self.assertCanRead(relpath, test_needle.encode(), mode='rb', filter_ext=('.py',))

        # leading 'addons/' is ignored if present
        self.assertCanRead("addons/web/__init__.py", "import")
        relpath = os.path.join('addons', relpath) # 'addons/base/tests/test_misc.py'
        self.assertCanRead(relpath, test_needle)

        # files in root_path are allowed
        self.assertCanRead('tools/misc.py')

        # absolute or relative inexisting files are ok
        self.assertCannotRead(config.root_path + '/__inexisting')
        self.assertCannotRead('base/__inexisting_file')

        # errors when outside addons_paths
        self.assertCannotRead('/doesnt/exist')
        self.assertCannotRead('')
        self.assertCannotRead('/tmp')
        self.assertCannotRead('../../../../../../../../../tmp')
        self.assertCannotRead(os.path.join(__file__, '../../../../../'))

        # data_dir is forbidden
        self.assertCannotRead(config['data_dir'])

        # errors for illegal extensions
        self.assertCannotRead(__file__, ValueError, filter_ext=('.png',))
        # file doesnt exist but has wrong extension
        self.assertCannotRead(__file__.replace('.py', '.foo'), ValueError, filter_ext=('.png',))


class TestDictTools(BaseCase):
    def test_readonly_dict(self):
        d = misc.ReadonlyDict({'foo': 'bar'})
        with self.assertRaises(TypeError):
            d['baz'] = 'xyz'
        with self.assertRaises(AttributeError):
            d.update({'baz': 'xyz'})
        with self.assertRaises(TypeError):
            dict.update(d, {'baz': 'xyz'})


class TestFormatLang(TransactionCase):
    def test_value_and_digits(self):
        self.assertEqual(misc.formatLang(self.env, 100.23, digits=1), '100.2')
        self.assertEqual(misc.formatLang(self.env, 100.23, digits=3), '100.230')

        self.assertEqual(misc.formatLang(self.env, ''), '', 'If value is an empty string, it should return an empty string (not 0)')

        self.assertEqual(misc.formatLang(self.env, 100), '100.00', 'If digits is None (default value), it should default to 2')

        # Default rounding is 'HALF_EVEN'
        self.assertEqual(misc.formatLang(self.env, 100.205), '100.20')
        self.assertEqual(misc.formatLang(self.env, 100.215), '100.22')

    def test_grouping(self):
        self.env["res.lang"].create({
            "name": "formatLang Lang",
            "code": "fLT",
            "grouping": "[3,0]",
            "decimal_point": "!",
            "thousands_sep": "?",
        })

        self.env['res.lang']._activate_lang('fLT')

        self.assertEqual(misc.formatLang(self.env['res.lang'].with_context(lang='fLT').env, 1000000000, grouping=True), '1?000?000?000!00')
        self.assertEqual(misc.formatLang(self.env['res.lang'].with_context(lang='fLT').env, 1000000000, grouping=False), '1000000000!00')

    def test_decimal_precision(self):
        decimal_precision = self.env['decimal.precision'].create({
            'name': 'formatLang Decimal Precision',
            'digits': 3,  # We want .001 decimals to make sure the decimal precision parameter 'dp' is chosen.
        })

        self.assertEqual(misc.formatLang(self.env, 100, dp=decimal_precision.name), '100.000')

    def test_currency_object(self):
        currency_object = self.env['res.currency'].create({
            'name': 'formatLang Currency',
            'symbol': 'fL',
            'rounding': 0.1,  # We want .1 decimals to make sure 'currency_obj' is chosen.
            'position': 'after',
        })

        self.assertEqual(misc.formatLang(self.env, 100, currency_obj=currency_object), '100.0%sfL' % u'\N{NO-BREAK SPACE}')

        currency_object.write({'position': 'before'})

        self.assertEqual(misc.formatLang(self.env, 100, currency_obj=currency_object), 'fL%s100.0' % u'\N{NO-BREAK SPACE}')

    def test_decimal_precision_and_currency_object(self):
        decimal_precision = self.env['decimal.precision'].create({
            'name': 'formatLang Decimal Precision',
            'digits': 3,
        })

        currency_object = self.env['res.currency'].create({
            'name': 'formatLang Currency',
            'symbol': 'fL',
            'rounding': 0.1,
            'position': 'after',
        })

        # If we have a 'dp' and 'currency_obj', we use the decimal precision of 'dp' and the format of 'currency_obj'.
        self.assertEqual(misc.formatLang(self.env, 100, dp=decimal_precision.name, currency_obj=currency_object), '100.000%sfL' % u'\N{NO-BREAK SPACE}')

    def test_rounding_method(self):
        self.assertEqual(misc.formatLang(self.env, 100.205), '100.20')  # Default is 'HALF-EVEN'
        self.assertEqual(misc.formatLang(self.env, 100.215), '100.22')  # Default is 'HALF-EVEN'

        self.assertEqual(misc.formatLang(self.env, 100.205, rounding_method='HALF-UP'), '100.21')
        self.assertEqual(misc.formatLang(self.env, 100.215, rounding_method='HALF-UP'), '100.22')

        self.assertEqual(misc.formatLang(self.env, 100.205, rounding_method='HALF-DOWN'), '100.20')
        self.assertEqual(misc.formatLang(self.env, 100.215, rounding_method='HALF-DOWN'), '100.21')

    def test_rounding_unit(self):
        self.assertEqual(misc.formatLang(self.env, 1000000.00), '1,000,000.00')
        self.assertEqual(misc.formatLang(self.env, 1000000.00, rounding_unit='units'), '1,000,000')
        self.assertEqual(misc.formatLang(self.env, 1000000.00, rounding_unit='thousands'), '1,000')
        self.assertEqual(misc.formatLang(self.env, 1000000.00, rounding_unit='lakhs'), '10')
        self.assertEqual(misc.formatLang(self.env, 1000000.00, rounding_unit="millions"), '1')

    def test_rounding_method_and_rounding_unit(self):
        self.assertEqual(misc.formatLang(self.env, 1822060000, rounding_method='HALF-UP', rounding_unit='lakhs'), '18,221')
        self.assertEqual(misc.formatLang(self.env, 1822050000, rounding_method='HALF-UP', rounding_unit='lakhs'), '18,221')
        self.assertEqual(misc.formatLang(self.env, 1822049900, rounding_method='HALF-UP', rounding_unit='lakhs'), '18,220')

    def test_format_decimal_point_without_grouping(self):
        lang = self.env['res.lang'].browse(misc.get_lang(self.env).id)
        self.assertEqual(lang.format(f'%.{1}f', 1200.50, grouping=True), '1,200.5')
        self.assertEqual(lang.format(f'%.{1}f', 1200.50, grouping=False), '1200.5')

        comma_lang = self.env['res.lang'].create({
            'name': 'Comma (CM)',
            'code': 'co_MA',
            'iso_code': 'co_MA',
            'thousands_sep': ' ',
            'decimal_point': ',',
            'grouping': '[3,0]',
            'active': True,
        })

        self.assertEqual(comma_lang.format(f'%.{1}f', 1200.50, grouping=True), '1 200,5')
        self.assertEqual(comma_lang.format(f'%.{1}f', 1200.50, grouping=False), '1200,5')


class TestUrlValidate(BaseCase):
    def test_url_validate(self):
        for case, truth in [
            # full URLs should be preserved
            ('http://example.com', 'http://example.com'),
            ('http://example.com/index.html', 'http://example.com/index.html'),
            ('http://example.com?debug=1', 'http://example.com?debug=1'),
            ('http://example.com#h3', 'http://example.com#h3'),

            # URLs with a domain should get a http scheme
            ('example.com', 'http://example.com'),
            ('example.com/index.html', 'http://example.com/index.html'),
            ('example.com?debug=1', 'http://example.com?debug=1'),
            ('example.com#h3', 'http://example.com#h3'),
        ]:
            with self.subTest(case=case):
                self.assertEqual(validate_url(case), truth)

        # broken cases, do we really want that?
        self.assertEqual(validate_url('/index.html'), 'http:///index.html')
        self.assertEqual(validate_url('?debug=1'), 'http://?debug=1')
        self.assertEqual(validate_url('#model=project.task&id=3603607'), 'http://#model=project.task&id=3603607')


class TestUrlJoin(BaseCase):
    # simple path joins
    def test_basic_relative_path(self):
        self.assertEqual(urls.urljoin('http://example.com/', 'c'), 'http://example.com/c')
        self.assertEqual(urls.urljoin('http://example.com/b/', 'c'), 'http://example.com/b/c')

    def test_path_normalization(self):
        self.assertEqual(urls.urljoin('http://example.com/b/', '/c'), 'http://example.com/b/c')  # leading / normalized
        self.assertEqual(urls.urljoin('http://example.com/b///', '///c'), 'http://example.com/b/c')
        self.assertEqual(urls.urljoin('http://example.com/b/', 'c/'), 'http://example.com/b/c/')  # trailing / must be kept

    def test_base_has_no_path(self):
        self.assertEqual(urls.urljoin('http://example.com', 'c.com'), 'http://example.com/c.com')
        self.assertEqual(urls.urljoin('http://example.com', '/c'), 'http://example.com/c')

    def test_extra_trailing_slash(self):
        self.assertEqual(urls.urljoin('http://example.com/b', ''), 'http://example.com/b')
        self.assertEqual(urls.urljoin('http://example.com/b', ' '), 'http://example.com/b')
        self.assertEqual(urls.urljoin('http://example.com/b', '/'), 'http://example.com/b/')

    # Scheme/Netloc
    def test_leading_and_trailing_slashes(self):
        self.assertEqual(urls.urljoin('http://example.com/b//c/d/e/////f/g/', '/h/i/j/'), 'http://example.com/b/c/d/e/f/g/h/i/j/')
        self.assertEqual(urls.urljoin('http://example.com/b//c/d/e/////f/g', '/h/i/j/'), 'http://example.com/b/c/d/e/f/g/h/i/j/')
        self.assertEqual(urls.urljoin('http://example.com/b//c/d/e/////f/g', 'h/i/j/'), 'http://example.com/b/c/d/e/f/g/h/i/j/')
        self.assertEqual(urls.urljoin('http://example.com/b//c/d/e/////f/g//', '/h/i/j'), 'http://example.com/b/c/d/e/f/g/h/i/j')
        self.assertEqual(urls.urljoin('http://example.com//', '/b/c'), 'http://example.com/b/c')
        self.assertEqual(urls.urljoin('/', '\\/example.com'), '/example.com')
        self.assertEqual(urls.urljoin('/', '\\\x07/example.com'), '/example.com')
        self.assertEqual(urls.urljoin('/', '\r\n\t\x00\\\r\n\t/example.com'), '/example.com')

    def test_absolute_url_raises(self):
        to_fail = [
            ('http://example.com/b#f1', 'http://example.com/c#f2'),
            ('http://test.example.com', 'https://test2.example.com'),
            ('https://test.example.com', 'http://test.example.com'),
            ('https://example.com/p?example=test', 'https://example.com/q?example=example'),
        ]
        for base, extra in to_fail:
            with self.subTest(base=base, extra=extra):
                with self.assertRaises(ValueError):
                    urls.urljoin(base, extra)

    def test_dot_segments_not_allowed(self):
        urls_with_dot = [
            ('http://example.com/b/', 'c/./d'),
            ('http://example.com/b/', 'c/../d'),
            ('http://example.com/b/', 'c/d/%2E%2E/e'),
            ('http://example.com/b/', 'c/%2E/d'),
            ('http://example.com/b/', 'c%2F%2E./d'),
            ('http://example.com/b/', 'c%2F%2E%2Fd'),
            ('http://example.com/./b/', 'c/d'),
            ('http://example.com/b/../', 'c/d'),
            ('http://example.com/%2E/b/', 'c/d'),
            ('http://example.com/b%2F%2E%2E/d', 'c/d'),
        ]
        for base, extra in urls_with_dot:
            with self.subTest(base=base, extra=extra):
                with self.assertRaises(ValueError):
                    urls.urljoin(base, extra)

    # Query Handling
    def test_query_keeps_base_by_default(self):
        self.assertEqual(urls.urljoin('http://example.com/b?q1=1', 'c?q2=2'), 'http://example.com/b/c?q2=2')
        self.assertEqual(urls.urljoin('http://example.com/b', 'c?q2=2'), 'http://example.com/b/c?q2=2')
        self.assertEqual(urls.urljoin('http://example.com/b?q1=1', 'c'), 'http://example.com/b/c')

    def test_allow_query_override(self):
        self.assertEqual(urls.urljoin('http://example.com/b', 'c?q2=2'), 'http://example.com/b/c?q2=2')
        self.assertEqual(urls.urljoin('http://example.com/b?q1=1', 'c'), 'http://example.com/b/c')
        self.assertEqual(urls.urljoin('http://example.com/b?q1=1', 'c?q2=2'), 'http://example.com/b/c?q2=2')
        self.assertEqual(urls.urljoin('http://example.com/b#c?q1=2&q2=3', 'c?q1=1&q2=2'), 'http://example.com/b/c?q1=1&q2=2')

    # Fragment Handling
    def test_only_extra_fragments(self):
        self.assertEqual(urls.urljoin('http://example.com/b#f1', 'c#f2'), 'http://example.com/b/c#f2')
        self.assertEqual(urls.urljoin('http://example.com/b', 'c#f2'), 'http://example.com/b/c#f2')
        self.assertEqual(urls.urljoin('http://example.com/b#f1', 'c'), 'http://example.com/b/c')

    # Input Validation
    def test_not_string_fails(self):
        with self.assertRaises(AssertionError):
            urls.urljoin(None, 'c')
        with self.assertRaises(AssertionError):
            urls.urljoin('http://a', 123)

    # Edge Cases
    def test_whitespaces(self):
        self.assertEqual(urls.urljoin('http://example.com/b', ' \ta '), 'http://example.com/b/a ')
        self.assertEqual(urls.urljoin('http://example.com/b', '\t \x0a\x0b\n\r\t a\t \t'), 'http://example.com/b/a ')
        self.assertEqual(urls.urljoin('http://example.com/b', ' a \n\t'), 'http://example.com/b/a ')

    def test_empty_base_string(self):
        self.assertEqual(urls.urljoin('', 'example.com'), '/example.com')
        self.assertEqual(urls.urljoin('', '/c?q=1#f'), '/c?q=1#f')

    def test_percent_encoding(self):
        self.assertEqual(
            urls.urljoin('http://host/space%20here/', 'x%2Fy'),
            'http://host/space%20here/x%2Fy',
        )
        self.assertEqual(
            urls.urljoin('http://host/a/', '%2Fhidden'),
            'http://host/a/%2Fhidden',
        )


class TestMiscToken(TransactionCase):

    def test_expired_token(self):
        payload = {'test': True, 'value': 123456, 'some_string': 'hello', 'some_dict': {'name': 'New Dict'}}
        expiration = datetime.datetime.now() - datetime.timedelta(days=1)
        token = misc.hash_sign(self.env, 'test', payload, expiration=expiration)
        self.assertIsNone(misc.verify_hash_signed(self.env, 'test', token))

    def test_long_payload(self):
        payload = {'test': True, 'value':123456, 'some_string': 'hello', 'some_dict': {'name': 'New Dict'}}
        token = misc.hash_sign(self.env, 'test', payload, expiration_hours=24)
        self.assertEqual(misc.verify_hash_signed(self.env, 'test', token), payload)

    def test_None_payload(self):
        with self.assertRaises(Exception):
            misc.hash_sign(self.env, 'test', None, expiration_hours=24)

    def test_list_payload(self):
        payload = ["str1", "str2", "str3", 4, 5]
        token = misc.hash_sign(self.env, 'test', payload, expiration_hours=24)
        self.assertEqual(misc.verify_hash_signed(self.env, 'test', token), payload)

    def test_modified_payload(self):
        payload = ["str1", "str2", "str3", 4, 5]
        token = base64.urlsafe_b64decode(misc.hash_sign(self.env, 'test', payload, expiration_hours=24) + '===')
        new_timestamp = datetime.datetime.now() + datetime.timedelta(days=7)
        new_timestamp = int(new_timestamp.timestamp())
        new_timestamp = new_timestamp.to_bytes(8, byteorder='little')
        token = base64.urlsafe_b64encode(token[:1] + new_timestamp + token[9:]).decode()
        self.assertIsNone(misc.verify_hash_signed(self.env, 'test', token))


class TestFormatAmountFunction(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.currency_object_format_amount = cls.env["res.currency"].create({
            "name": "format_amount Currency",
            "symbol": "fA",
            "rounding": 0.01,  # Makes 12.345 as 12.34
            "position": "before",
        })
        # A language where decimal separator and thousands separator is same to check effectiveness of
        # regular expression used in format_amount
        cls.kiliki_language = cls.env["res.lang"].create({
            "name": "Kili kili",
            "code": "GFL",
            "grouping": "[3,0]",
            "decimal_point": "#",
            "thousands_sep": "#",
        })

        cls.kiliki_language.install_lang()
        cls.kiliki_language.active = True

    def assert_format_amount(self, amount, expected, trailing_zeroes=True, lang_code=None):
        result = misc.format_amount(
            self.env,
            amount,
            self.currency_object_format_amount,
            trailing_zeroes=trailing_zeroes,
            lang_code=lang_code,
        )
        self.assertEqual(result, expected)

    def test_trailing_true_on_number_having_no_trailing_zeroes(self):
        # Has no effect on number not having trailing zeroes
        self.assert_format_amount(1.234, "fA%s1.23" % "\N{NO-BREAK SPACE}")

        # Has no effect on number not having trailing zeroes - currency position after
        self.currency_object_format_amount.position = "after"
        self.assert_format_amount(1.234, "1.23%sfA" % "\N{NO-BREAK SPACE}")

    def test_trailing_false_on_number_having_no_trailing_zeroes(self):
        # Has no effect on number not having trailing zeroes even if trailing zeroes set as False
        self.assert_format_amount(1.234, "fA%s1.23" % "\N{NO-BREAK SPACE}")

        # Has no effect on number not having trailing zeroes - currency position after
        self.currency_object_format_amount.position = "after"
        self.assert_format_amount(1.234, "1.23%sfA" % "\N{NO-BREAK SPACE}")

    def test_trailing_zeroes_true_on_number_having_trailing_zeroes(self):
        # Has no effect on number having trailing zeroes if trailing zeroes set as True (True by default)
        self.assert_format_amount(1.0000, "fA%s1.00" % "\N{NO-BREAK SPACE}")

        # Has no effect on number having trailing zeroes - currency position after
        self.currency_object_format_amount.position = "after"
        self.assert_format_amount(1.0000, "1.00%sfA" % "\N{NO-BREAK SPACE}")

    def test_trailing_false_on_number_having_trailing_zeroes(self):
        # Has effect (removes trailing zeroes) on number having trailing zeroes if trailing zeroes set as False
        self.assert_format_amount(1.0000, "fA%s1" % "\N{NO-BREAK SPACE}", False)

        # Has effect on number having trailing zeroes - currency position after
        self.currency_object_format_amount.position = "after"
        self.assert_format_amount(1.0000, "1%sfA" % "\N{NO-BREAK SPACE}", False)

    def test_trailing_false_on_number_having_trailing_zeroes_with_kilikili_language(self):
        # Here the amount is first will be given decimal separator and thousandth separator as
        # follows 10#000#00 in which second # is decimal so, the RE targets the decimal separator
        # at the last position.
        self.assert_format_amount(10000, "fA%s10#000" % "\N{NO-BREAK SPACE}", False, "GFL")

        # Has no effect on number having same decimal and thousandth seperator - currency position after
        self.currency_object_format_amount.position = "after"
        self.assert_format_amount(10000, "10#000%sfA" % "\N{NO-BREAK SPACE}", False, "GFL")
