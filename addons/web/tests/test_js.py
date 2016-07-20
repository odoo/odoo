# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import openerp.tests


class WebSuite(openerp.tests.HttpCase):
    def test_01_js(self):
        self.phantom_js('/web/tests?mod=web',"","", login='admin')
