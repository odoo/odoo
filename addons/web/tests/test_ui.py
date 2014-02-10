# -*- coding: utf-8 -*-
import openerp.tests

class TestUi(openerp.tests.HttpCase):
    def test(self):
        self.phantom_js("/", "console.log('ok')", "console")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
