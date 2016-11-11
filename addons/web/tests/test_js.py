# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import unittest
import odoo.tests

class WebSuite(odoo.tests.HttpCase):
    @unittest.skip('Memory leak in this test lead to phantomjs crash, making it unreliable')
    def test_01_js(self):
        self.phantom_js('/web/tests?mod=web',"","", login='admin')
