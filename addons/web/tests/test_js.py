# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from contextlib import suppress

import odoo.tests
from odoo.tools.misc import file_open
from werkzeug.urls import url_quote_plus

RE_FORBIDDEN_STATEMENTS = re.compile(r'test.*\.(only|debug)\(')
RE_ONLY = re.compile(r'QUnit\.(only|debug)\(')
RE_ASSET_ADDON = re.compile(r'^/(\w+)/')


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


class HootCommon(odoo.tests.HttpCase):
    def _check_forbidden_statements(self, bundle):
        # As we currently are not in a request context, we cannot render `web.layout`.
        # We then re-define it as a minimal proxy template.
        self.env.ref('web.layout').write({'arch_db': '<t t-name="web.layout"><html><head><meta charset="utf-8"/><link/><script id="web.layout.odooscript"/><meta/><t t-out="head"/></head><body><t t-out="0"/></body></html></t>'})
        for asset in self._get_bundle_assets(bundle):
            filename = asset['filename']
            if not filename.endswith('.test.js'):
                continue
            with suppress(FileNotFoundError):
                with file_open(filename, 'rb', filter_ext=('.js',)) as fp:
                    if RE_FORBIDDEN_STATEMENTS.search(fp.read().decode('utf-8')):
                        self.fail("`only()` or `debug()` used in file %r" % asset['url'])

    def _generate_hash(self, test_string):
        hash = 0
        for char in test_string:
            hash = (hash << 5) - hash + ord(char)
            hash = hash & 0xFFFFFFFF
        return f'{hash:08x}'

    def _get_addons_from_asset_bundle(self, bundle):
        return {
            RE_ASSET_ADDON.match(asset['url'])[1]
            for asset in self._get_bundle_assets(bundle)
            if asset['filename'].endswith('.test.js')
        }

    def _get_bundle_assets(self, bundle):
        assets = self.env['ir.qweb']._get_asset_content(bundle)[0]
        if len(assets) == 0:
            self.fail("No assets found in the given test bundle")
        return assets

    def _get_hoot_module_filters(self, addons_from_asset_bundle, available_modules):
        module_filter = ''
        for module in available_modules:
            if module in addons_from_asset_bundle:
                module_filter += f'&id={self._generate_hash(f'@{module}')}'
        return module_filter

    def _get_hoot_param_filters(self):
        filters = _get_filters(self._test_params)
        result = []
        for sign, f in filters:
            h = self._generate_hash(f)
            if sign == '-':
                h = f'-{h}'
            # Since we don't know if the descriptor we have is a test or a suite, we need to provide the hash for a generic "job"
            result.append(h)
        return result

    def _get_hoot_filters(self, addons_from_asset_bundle, available_modules):
        module_filter = self._get_hoot_module_filters(addons_from_asset_bundle, available_modules)
        if not module_filter:
            return None
        param_filter_elems = self._get_hoot_param_filters()
        if any(not f.startswith('-') for f in param_filter_elems):
            module_filter = ''
            # disable module filter if one of the params selects a test
            # note that this is not 100% correct since in reality we would like to have an AND between module filters and positive param filters, but the current behaviour is an OR by default
        params_filter = ''.join([f'&id={h}' for h in param_filter_elems])
        return module_filter + params_filter


@odoo.tests.tagged('post_install', '-at_install')
class HootSuite(HootCommon):
    def test_check_suite(self):
        self._check_forbidden_statements('web.assets_unit_tests')

    def test_generate_hoot_hash(self):
        self.assertEqual(self._generate_hash('@web/core'), 'e39ce9ba')
        self.assertEqual(self._generate_hash('@web/core/autocomplete'), '69a6561d') # suite
        self.assertEqual(self._generate_hash('@web/core/autocomplete/open dropdown on input'), 'ee565d54') # test

    def test_get_hoot_module_filters(self):
        self.assertEqual(self._get_hoot_module_filters(['account', 'mail', 'web'], []), '')
        self.assertEqual(self._get_hoot_module_filters(['account', 'mail', 'web'], ['account']), '&id=b21ec1ed')
        self.assertEqual(self._get_hoot_module_filters(['account', 'mail', 'web'], ['mail']), '&id=03b8e5f7')
        self.assertEqual(self._get_hoot_module_filters(['account', 'mail', 'web'], ['web']), '&id=001ee314')
        self.assertEqual(self._get_hoot_module_filters(['account', 'mail', 'web'], ['account', 'web']), '&id=b21ec1ed&id=001ee314')
        self.assertEqual(self._get_hoot_module_filters(['account', 'mail', 'web'], ['account', 'mail', 'web']), '&id=b21ec1ed&id=03b8e5f7&id=001ee314')
        self.assertEqual(self._get_hoot_module_filters(['account', 'mail', 'web'], ['project']), '')
        self.assertEqual(self._get_hoot_module_filters(['account', 'mail', 'web'], ['project', 'web']), '&id=001ee314')

    def test_get_hoot_param_filters(self):
        self._test_params = []
        self.assertEqual(self._get_hoot_param_filters(), [])
        expected = ['e39ce9ba', '-69a6561d']
        self._test_params = [('+', '@web/core,-@web/core/autocomplete')]
        self.assertEqual(self._get_hoot_param_filters(), expected)
        self._test_params = [('+', '@web/core'), ('-', '@web/core/autocomplete')]
        self.assertEqual(self._get_hoot_param_filters(), expected)
        self._test_params = [('+', '-@web/core/autocomplete,-@web/core/autocomplete2')]
        self.assertEqual(self._get_hoot_param_filters(), ['-69a6561d', '-cb246db5'])
        self._test_params = [('-', '-@web/core/autocomplete,-@web/core/autocomplete2')]
        self.assertEqual(self._get_hoot_param_filters(), ['69a6561d', 'cb246db5'])

    def test_get_hoot_filters(self):
        addons_from_asset_bundle = self._get_addons_from_asset_bundle('web.assets_unit_tests')
        self.assertEqual(self._get_hoot_filters(addons_from_asset_bundle, ['web']), '&id=001ee314', 'Web module should be tested')
        self._test_params = [('+', '@web/core')]
        self.assertEqual(self._get_hoot_filters(addons_from_asset_bundle, ['web']), '&id=e39ce9ba', '@web/core eplicitly selected')
        self._test_params = [('-', '@web/core')]
        self.assertEqual(self._get_hoot_filters(addons_from_asset_bundle, ['web']), '&id=001ee314&id=-e39ce9ba', '@web/core explicitly excluded')

    @odoo.tests.no_retry
    def test_hoot(self):
        # HOOT tests suite
        self.browser_js('/web/static/lib/hoot/tests/index.html?headless&loglevel=2', "", "", login='admin', timeout=1800, success_signal="[HOOT] Test suite succeeded", error_checker=unit_test_error_checker)


@odoo.tests.tagged('hoot', 'post_install', '-at_install')
class WebSuite(HootCommon, odoo.tests.CrossModule):
    @odoo.tests.no_retry
    def test_unit_desktop(self, modules):
        # Unit tests suite (desktop)
        addons_from_asset_bundle = self._get_addons_from_asset_bundle('web.assets_unit_tests')
        filters = self._get_hoot_filters(addons_from_asset_bundle, modules)
        if not filters:
            return
        self.browser_js(f'/web/tests?&headless&loglevel=2&preset=desktop&timeout=15000{filters}', "", "", login='admin', timeout=3000, success_signal="[HOOT] Test suite succeeded", error_checker=unit_test_error_checker)


@odoo.tests.tagged('hoot', 'post_install', '-at_install')
class MobileWebSuite(HootCommon, odoo.tests.CrossModule):
    browser_size = '375x667'
    touch_enabled = True

    @odoo.tests.no_retry
    def test_unit_mobile(self, modules):
        # Unit tests suite (mobile)
        addons_from_asset_bundle = self._get_addons_from_asset_bundle('web.assets_unit_tests')
        filters = self._get_hoot_filters(addons_from_asset_bundle, modules)
        if not filters:
            return
        self.browser_js(f'/web/tests?&headless&loglevel=2&preset=mobile&tag=-headless&timeout=15000{filters}', "", "", login='admin', timeout=2100, success_signal="[HOOT] Test suite succeeded", error_checker=unit_test_error_checker)


@odoo.tests.tagged('post_install', '-at_install')
class LegacyWebSuite(odoo.tests.HttpCase):
    def setUp(self):
        super().setUp()
        self.qunit_filters = self.get_qunit_filters()

    def _check_only_call(self, suite):
        # ! DEPRECATED
        # As we currently aren't in a request context, we can't render `web.layout`.
        # redefinied it as a minimal proxy template.
        self.env.ref('web.layout').write({'arch_db': '<t t-name="web.layout"><html><head><meta charset="utf-8"/><link/><script id="web.layout.odooscript"/><meta/><t t-out="head"/></head><body><t t-out="0"/></body></html></t>'})

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

    def test_check_suite(self):
        # Checks that no test is using `only` or `debug` as it prevents other tests to be run
        self._check_only_call('web.qunit_suite_tests')

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

    @odoo.tests.no_retry
    def test_qunit(self):
        # ! DEPRECATED
        self.browser_js(f'/web/tests/legacy?mod=web{self.qunit_filters}', "", "", login='admin', timeout=1800, success_signal="QUnit test suite done.", error_checker=qunit_error_checker)
