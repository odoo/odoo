# -*- coding: utf-8 -*-
# Run with one of these commands:
#    > OPENERP_ADDONS_PATH='../../addons/trunk' OPENERP_PORT=8069 \
#      OPENERP_DATABASE=yy PYTHONPATH=. python tests/test_ir_sequence.py
#    > OPENERP_ADDONS_PATH='../../addons/trunk' OPENERP_PORT=8069 \
#      OPENERP_DATABASE=yy nosetests tests/test_ir_sequence.py
#    > OPENERP_ADDONS_PATH='../../../addons/trunk' OPENERP_PORT=8069 \
#      OPENERP_DATABASE=yy PYTHONPATH=../:. unit2 test_ir_sequence
import os
import time
import unittest2
import xmlrpclib

import openerp
import common

DB = common.DB
ADMIN_USER_ID = common.ADMIN_USER_ID

setUpModule = common.setUpModule
tearDownModule = common.tearDownModule

def registry(model):
    return openerp.modules.registry.RegistryManager.get(DB)[model]

def cursor():
    return openerp.modules.registry.RegistryManager.get(DB).db.cursor()

class test_ir_sequence(unittest2.TestCase):

    def test_ir_sequence_create(self):
        """ Try to create a sequence object. """
        cr = cursor()
        try:
            d = dict(code='test_sequence_type', name='Test sequence type')
            c = registry('ir.sequence.type').create(cr, ADMIN_USER_ID, d, {})
            assert c
            d = dict(code='test_sequence_type', name='Test sequence')
            c = registry('ir.sequence').create(cr, ADMIN_USER_ID, d, {})
            assert c
            cr.commit()
        finally:
            cr.close()

    def test_ir_sequence_search(self):
        """ Try a search. """
        cr = cursor()
        try:
            ids = registry('ir.sequence').search(cr, ADMIN_USER_ID, [], {})
            assert ids
            cr.commit()
        finally:
            cr.close()

if __name__ == '__main__':
    unittest2.main()

