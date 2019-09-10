# -*- coding: utf-8 -*-
import os

import openerp.tests

class TestUi(openerp.tests.HttpCase):
    def test_03_js_public(self):
        self.phantom_js('/',"console.log('ok')","console")
    def test_04_js_admin(self):
        self.phantom_js('/web',"console.log('ok')","openerp.client.action_manager.inner_widget", login='admin')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
