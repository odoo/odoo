# -*- coding: utf-8 -*-
import os

import openerp

class TestUi(openerp.tests.HttpCase):
    def test_js(self):
        self.phantom_js('/',"console.log('ok')","console", login=None)

    def test_jsfile(self):
        self.phantom_jsfile(os.path.join(os.path.dirname(__file__), 'test_ui_hello.js'))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
