# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from contextlib import suppress

import odoo.tests
from odoo.tools.misc import file_open

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


@odoo.tests.tagged('post_install', '-at_install')
class WebSuite(odoo.tests.HttpCase):

    @odoo.tests.no_retry
    def test_unit_desktop(self):
        # Unit tests suite (desktop)
        self.browser_js('/web/tests?headless&loglevel=2&preset=desktop&timeout=15000', "", "", login='admin', timeout=1800, success_signal="[HOOT] test suite succeeded", error_checker=unit_test_error_checker)

    @odoo.tests.no_retry
    def test_hoot(self):
        # HOOT tests suite
        self.browser_js('/web/static/lib/hoot/tests/index.html?headless&loglevel=2', "", "", login='admin', timeout=1800, success_signal="[HOOT] test suite succeeded", error_checker=unit_test_error_checker)

    @odoo.tests.no_retry
    def test_qunit_desktop(self):
        # ! DEPRECATED
        self.browser_js('/web/tests/legacy?mod=web', "", "", login='admin', timeout=1800, success_signal="QUnit test suite done.", error_checker=qunit_error_checker)

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
class MobileWebSuite(odoo.tests.HttpCase):
    browser_size = '375x667'
    touch_enabled = True

    @odoo.tests.no_retry
    def test_unit_mobile(self):
        # Unit tests suite (mobile)
        self.browser_js('/web/tests?headless&loglevel=2&preset=mobile&tag=-headless&timeout=15000', "", "", login='admin', timeout=1800, success_signal="[HOOT] test suite succeeded", error_checker=unit_test_error_checker)

    def test_qunit_mobile(self):
        # ! DEPRECATED
        self.browser_js('/web/tests/legacy/mobile?mod=web', "", "", login='admin', timeout=1800, success_signal="QUnit test suite done.", error_checker=qunit_error_checker)
