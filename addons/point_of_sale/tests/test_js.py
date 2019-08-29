# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.addons.web.tests.test_js
import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
class WebSuite(odoo.tests.HttpCase):
    def test_pos_js(self):
        # point_of_sale desktop test suite
        self.phantom_js('/pos/web/tests?mod=web&failfast',"","", login='admin', timeout=1800)


@odoo.tests.tagged('post_install', '-at_install')
class MobileWebSuite(odoo.tests.HttpCase):
    browser_size = odoo.addons.web.tests.test_js.MobileWebSuite.browser_size

    def test_pos_mobile_js(self):
        # point_of_sale mobile test suite
        self.phantom_js('/pos/web/tests/mobile?mod=web&failfast', "", "", login='admin', timeout=1800)
