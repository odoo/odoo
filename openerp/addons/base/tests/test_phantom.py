# -*- coding: utf-8 -*-

import os
import glob

import openerp

class test_phantom(openerp.tests.HttpCase):
    def test_phantom(self):
        fname, _ = os.path.splitext(__file__)
        for i in glob.glob('%s*.js' % fname):
            self.phantomjs(openerp.modules.module.get_module_resource('base','tests', i))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
