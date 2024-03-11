# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import odoo.tests

RE_ONLY = re.compile(r'QUnit\.(only|debug)\(')


def qunit_error_checker(message):
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
    def test_js(self):
        # webclient desktop test suite
        self.browser_js('/web/tests?mod=web', "", "", login='admin', timeout=1800, error_checker=qunit_error_checker)

    def test_check_suite(self):
        # verify no js test is using `QUnit.only` as it forbid any other test to be executed
        self._check_only_call('web.qunit_suite_tests')
        self._check_only_call('web.qunit_mobile_suite_tests')

    def _check_only_call(self, suite):
        # As we currently aren't in a request context, we can't render `web.layout`.
        # redefinied it as a minimal proxy template.
        self.env.ref('web.layout').write({'arch_db': '<t t-name="web.layout"><head><meta charset="utf-8"/><t t-esc="head"/></head></t>'})

        assets = self.env['ir.qweb']._get_asset_content(suite)[0]
        if len(assets) == 0:
            self.fail("No assets found in the given test suite")

        for asset in assets:
            filename = asset['filename']
            if not filename or asset['atype'] != 'text/javascript':
                continue
            with open(filename, 'rb') as fp:
                if RE_ONLY.search(fp.read().decode('utf-8')):
                    self.fail("`QUnit.only()` or `QUnit.debug()` used in file %r" % asset['url'])


@odoo.tests.tagged('post_install', '-at_install')
class MobileWebSuite(odoo.tests.HttpCase):
    browser_size = '375x667'
    touch_enabled = True

    def test_mobile_js(self):
        # webclient mobile test suite
        self.browser_js('/web/tests/mobile?mod=web', "", "", login='admin', timeout=1800, error_checker=qunit_error_checker)
