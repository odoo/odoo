# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from contextlib import suppress

import odoo.tests
from odoo.tools.misc import file_open
from werkzeug.urls import url_quote_plus

RE_FORBIDDEN_STATEMENTS = re.compile(r'test.*\.(only|debug)\(')
RE_ONLY = re.compile(r'QUnit\.(only|debug)\(')


def unit_test_error_checker(message):
    return '[HOOT]' not in message


def qunit_error_checker(message):
    # ! DEPRECATED
    # We don't want to stop qunit if a qunit is breaking.

    # '%s/%s test failed.' case: end message when all tests are finished
    if  'tests failed.' in message:
        return True

    # "QUnit test failed" case: one qunit failed. don't stop in this case
    if "QUnit test failed:" in message:
        return False

    return True  # in other cases, always stop (missing dependency, ...)


def _get_filters(test_params):
    filters = []
    for sign, param in test_params:
        parts = param.split(',')
        for part in parts:
            part = part.strip()
            if not part:
                continue
            part_sign = sign
            if part.startswith('-'):
                part = part[1:]
                part_sign = '-' if sign == '+' else '+'
            filters.append((part_sign, part))
    return sorted(filters)

@odoo.tests.tagged('post_install', '-at_install')
class QunitCommon(odoo.tests.HttpCase):

    def setUp(self):
        super().setUp()
        self.qunit_filters = self.get_qunit_filters()

    def get_qunit_regex(self, test_params):
        filters = _get_filters(test_params)
        positive = [f'({re.escape(f)}.*)' for sign, f in filters if sign == '+']
        negative = [f'({re.escape(f)}.*)' for sign, f in filters if sign == '-']
        filter = ''
        if filters:
            positive_re = '|'.join(positive) or '.*'
            negative_re = '|'.join(negative)
            negative_re = f'(?!{negative_re})' if negative_re else ''
            filter = f'^({negative_re})({positive_re})$'
        return filter

    def get_qunit_filters(self):
        filter_param = ''
        filter = self.get_qunit_regex(self._test_params)
        if filter:
            url_filter = url_quote_plus(filter)
            filter_param = f'&filter=/{url_filter}/'
        return filter_param

    def test_get_qunit_regex(self):
        f = self.get_qunit_regex([('+', 'utils,mail,-utils > bl1,-utils > bl2')])
        f2 = self.get_qunit_regex([('+', 'utils'), ('-', 'utils > bl1,utils > bl2'), ('+', 'mail')])
        self.assertEqual(f, f2)
        self.assertRegex('utils', f)
        self.assertRegex('mail', f)
        self.assertRegex('utils > something', f)

        self.assertNotRegex('utils > bl1', f)
        self.assertNotRegex('utils > bl2', f)
        self.assertNotRegex('web', f)

        f2 = self.get_qunit_regex([('+', '-utils > bl1,-utils > bl2')])
        f3 = self.get_qunit_regex([('-', 'utils > bl1,utils > bl2')])
        for f in (f2, f3):
            self.assertRegex('utils', f)
            self.assertRegex('mail', f)
            self.assertRegex('utils > something', f)
            self.assertRegex('web', f)

            self.assertNotRegex('utils > bl1', f)
            self.assertNotRegex('utils > bl2', f)

@odoo.tests.tagged('post_install', '-at_install')
class HOOTCommon(odoo.tests.HttpCase):

    def setUp(self):
        super().setUp()
        self.hoot_filters = self.get_hoot_filters()

    def _generate_hash(self, test_string):
        hash = 0
        for char in test_string:
            hash = (hash << 5) - hash + ord(char)
            hash = hash & 0xFFFFFFFF
        return f'{hash:08x}'

    def get_hoot_filters(self):
        filters = _get_filters(self._test_params)
        filter = ''
        for sign, f in filters:
            h = self._generate_hash(f)
            if sign == '-':
                h = f'-{h}'
            # Since we don't know if the descriptor we have is a test or a suite, we need to provide the hash both for test and suite
            filter += f'&test={h}&suite={h}'
        return filter

    def test_generate_hoot_hash(self):
        self.assertEqual(self._generate_hash('@web/core'), 'e39ce9ba')
        self.assertEqual(self._generate_hash('@web/core/autocomplete'), '69a6561d') # suite
        self.assertEqual(self._generate_hash('@web/core/autocomplete/open dropdown on input'), 'ee565d54') # test

    def test_get_hoot_filter(self):
        self._test_params = []
        self.assertEqual(self.get_hoot_filters(), '')
        expected = '&test=e39ce9ba&suite=e39ce9ba&test=-69a6561d&suite=-69a6561d'
        self._test_params = [('+', '@web/core,-@web/core/autocomplete')]
        self.assertEqual(self.get_hoot_filters(), expected)
        self._test_params = [('+', '@web/core'), ('-', '@web/core/autocomplete')]
        self.assertEqual(self.get_hoot_filters(), expected)
        self._test_params = [('+', '-@web/core/autocomplete,-@web/core/autocomplete2')]
        self.assertEqual(self.get_hoot_filters(), '&test=-69a6561d&suite=-69a6561d&test=-cb246db5&suite=-cb246db5')
        self._test_params = [('-', '-@web/core/autocomplete,-@web/core/autocomplete2')]
        self.assertEqual(self.get_hoot_filters(), '&test=69a6561d&suite=69a6561d&test=cb246db5&suite=cb246db5')

@odoo.tests.tagged('post_install', '-at_install')
class WebSuite(QunitCommon, HOOTCommon):

    @odoo.tests.no_retry
    def test_unit_desktop(self):
        # Unit tests suite (desktop)
        self.browser_js(f'/web/tests?headless&loglevel=2&preset=desktop&timeout=15000{self.hoot_filters}', "", "", login='admin', timeout=1800, success_signal="[HOOT] test suite succeeded", error_checker=unit_test_error_checker)

    @odoo.tests.no_retry
    def test_hoot(self):
        # HOOT tests suite
        self.browser_js(f'/web/static/lib/hoot/tests/index.html?headless&loglevel=2{self.hoot_filters}', "", "", login='admin', timeout=1800, success_signal="[HOOT] test suite succeeded", error_checker=unit_test_error_checker)

    @odoo.tests.no_retry
    def test_qunit_desktop(self):
        # ! DEPRECATED
        self.browser_js(f'/web/tests/legacy?mod=web{self.qunit_filters}', "", "", login='admin', timeout=1800, success_signal="QUnit test suite done.", error_checker=qunit_error_checker)

    def test_check_suite(self):
        self._check_forbidden_statements('web.assets_unit_tests')
        # Checks that no test is using `only` or `debug` as it prevents other tests to be run
        self._check_only_call('web.qunit_suite_tests')
        self._check_only_call('web.qunit_mobile_suite_tests')

    def _check_forbidden_statements(self, bundle):
        # As we currently are not in a request context, we cannot render `web.layout`.
        # We then re-define it as a minimal proxy template.
        self.env.ref('web.layout').write({'arch_db': '<t t-name="web.layout"><head><meta charset="utf-8"/><t t-esc="head"/></head></t>'})

        assets = self.env['ir.qweb']._get_asset_content(bundle)[0]
        if len(assets) == 0:
            self.fail("No assets found in the given test bundle")

        for asset in assets:
            filename = asset['filename']
            if not filename.endswith('.test.js'):
                continue
            with suppress(FileNotFoundError):
                with file_open(filename, 'rb', filter_ext=('.js',)) as fp:
                    if RE_FORBIDDEN_STATEMENTS.search(fp.read().decode('utf-8')):
                        self.fail("`only()` or `debug()` used in file %r" % asset['url'])

    def _check_only_call(self, suite):
        # ! DEPRECATED
        # As we currently aren't in a request context, we can't render `web.layout`.
        # redefinied it as a minimal proxy template.
        self.env.ref('web.layout').write({'arch_db': '<t t-name="web.layout"><head><meta charset="utf-8"/><t t-esc="head"/></head></t>'})

        assets = self.env['ir.qweb']._get_asset_content(suite)[0]
        if len(assets) == 0:
            self.fail("No assets found in the given test suite")

        for asset in assets:
            filename = asset['filename']
            if not filename.endswith('.js'):
                continue
            with suppress(FileNotFoundError):
                with file_open(filename, 'rb', filter_ext=('.js',)) as fp:
                    if RE_ONLY.search(fp.read().decode('utf-8')):
                        self.fail("`QUnit.only()` or `QUnit.debug()` used in file %r" % asset['url'])


@odoo.tests.tagged('post_install', '-at_install')
class MobileWebSuite(QunitCommon, HOOTCommon):
    browser_size = '375x667'
    touch_enabled = True

    @odoo.tests.no_retry
    def test_unit_mobile(self):
        # Unit tests suite (mobile)
        self.browser_js(f'/web/tests?headless&loglevel=2&preset=mobile&tag=-headless&timeout=15000{self.hoot_filters}', "", "", login='admin', timeout=1800, success_signal="[HOOT] test suite succeeded", error_checker=unit_test_error_checker)

    def test_qunit_mobile(self):
        # ! DEPRECATED
        self.browser_js(f'/web/tests/legacy/mobile?mod=web{self.qunit_filters}', "", "", login='admin', timeout=1800, success_signal="QUnit test suite done.", error_checker=qunit_error_checker)
