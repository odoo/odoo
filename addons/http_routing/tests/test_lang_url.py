# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch
from odoo.tests import HttpCase


class TestLangUrl(HttpCase):

    # Mock to simulate hr_HR lang is activated
    def _get_language_codes(self):
        return [
            ('en_US', 'English'),
            ('hr_HR', 'Croatian / hrvatski jezik'),
        ]

    # Mock to simulate hr_holidays module is installed
    def _installed(self):
        modules = self.original_installed()
        modules.update(hr_holidays=42)
        return modules

    def test_01_url_module_name(self):
        self.original_installed = self.env['ir.module.module']._installed
        patchers = [
            patch('odoo.addons.http_routing.models.ir_http.IrHttp._get_language_codes', wraps=self._get_language_codes),
            patch('odoo.addons.base.module.module.Module._installed', wraps=self._installed),
        ]
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

        resp = self.url_open('/hr_holidays/static/src/scss/test.scss')
        self.assertTrue(resp.url.endswith('/hr_holidays/static/src/scss/test.scss'), "hr_holidays should not be replaced by hr_HR as hr_holidays is a module name")
        resp = self.url_open('/hr_hoooolidays/static/src/scss/test.scss')
        self.assertTrue(resp.url.endswith('/hr_HR/static/src/scss/test.scss'), "hr_hoooolidays should be replaced by hr_HR as hr_hoooolidays is not a module name and is close to hr_HR")
