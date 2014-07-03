# -*- coding: utf-8 -*-
import os

import openerp.tests

class TestUi(openerp.tests.HttpCase):
    def test_01_jsfile_ui_hello(self):
        self.phantom_jsfile(os.path.join(os.path.dirname(__file__), 'test_ui_hello.js'))
    def test_02_jsfile_ui_load(self):
        self.phantom_jsfile(os.path.join(os.path.dirname(__file__), 'test_ui_load.js'))
    def test_03_js_public(self):
        self.phantom_js('/',"console.log('ok')","console")
    def test_04_js_admin(self):
        self.phantom_js('/web',"console.log('ok')","openerp.client.action_manager.inner_widget", login='admin')

@openerp.tests.common.at_install(False)
@openerp.tests.common.post_install(True)
class TestMenuItems(openerp.tests.HttpCase):
    def test_01_menuitems(self):
        self.phantom_js("/web", "openerp.Tour.run('test_menu', 'test')", "openerp.Tour.tours.test_menu", login="admin")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
