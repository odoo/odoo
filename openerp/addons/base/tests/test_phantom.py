# -*- coding: utf-8 -*-

import openerp
from openerp.tests import common

class test_phantom(common.HttpCase):

    def test_01_dummy(self):
        self.phantomjs(openerp.modules.module.get_module_resource('base','tests','test_phantom_dummy.js'))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
