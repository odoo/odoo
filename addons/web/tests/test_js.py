# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from contextlib import suppress

import odoo.tests
from odoo.tools.misc import file_open
from werkzeug.urls import url_quote_plus

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
class WebsuiteCommon(odoo.tests.HttpCase):
    def get_filter(self, test_params):
        positive = []
        negative = []
        for sign, param in test_params:
            filters = param.split(',')
            for filter in filters:
                filter = filter.strip()
                if not filter:
                    continue
                negate = sign == '-'
                if filter.startswith('-'):
                    negate = not negate
                    filter = filter[1:]
                if negate:
                    negative.append(f'({re.escape(filter)}.*)')
                else:
                    positive.append(f'({re.escape(filter)}.*)')
        filter = ''
        if positive or negative:
            positive_re = '|'.join(positive) or '.*'
            negative_re = '|'.join(negative)
            negative_re = f'(?!{negative_re})' if negative_re else ''
            filter = f'^({negative_re})({positive_re})$'
        return filter

    def test_get_filter(self):
        f1 = self.get_filter([('+', 'utils,mail,-utils > bl1,-utils > bl2')])
        f2 = self.get_filter([('+', 'utils'), ('-', 'utils > bl1,utils > bl2'), ('+', 'mail')])
        for f in (f1, f2):
            self.assertRegex('utils', f)
            self.assertRegex('mail', f)
            self.assertRegex('utils > something', f)

            self.assertNotRegex('utils > bl1', f)
            self.assertNotRegex('utils > bl2', f)
            self.assertNotRegex('web', f)

        f2 = self.get_filter([('+', '-utils > bl1,-utils > bl2')])
        f3 = self.get_filter([('-', 'utils > bl1,utils > bl2')])
        for f in (f2, f3):
            self.assertRegex('utils', f)
            self.assertRegex('mail', f)
            self.assertRegex('utils > something', f)
            self.assertRegex('web', f)

            self.assertNotRegex('utils > bl1', f)
            self.assertNotRegex('utils > bl2', f)

    def get_filter_param(self):
        filter_param = ''
        filter = self.get_filter(self._test_params)
        if filter:
            url_filter = url_quote_plus(filter)
            filter_param = f'&filter=/{url_filter}/'
        return filter_param


@odoo.tests.tagged('post_install', '-at_install')
class WebSuite(WebsuiteCommon):

    @odoo.tests.no_retry
    def test_js(self):
        filter_param = self.get_filter_param()
        # webclient desktop test suite
        self.browser_js('/web/tests?mod=web%s' % filter_param, "", "", login='admin', timeout=1800, error_checker=qunit_error_checker)

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
            if not filename.endswith('.js'):
                continue
            with suppress(FileNotFoundError):
                with file_open(filename, 'rb', filter_ext=('.js',)) as fp:
                    if RE_ONLY.search(fp.read().decode('utf-8')):
                        self.fail("`QUnit.only()` or `QUnit.debug()` used in file %r" % asset['url'])


@odoo.tests.tagged('post_install', '-at_install')
class MobileWebSuite(WebsuiteCommon):
    browser_size = '375x667'
    touch_enabled = True

    def test_mobile_js(self):
        filter_param = self.get_filter_param()
        # webclient mobile test suite
        self.browser_js('/web/tests/mobile?mod=web%s' % filter_param, "", "", login='admin', timeout=1800, error_checker=qunit_error_checker)
