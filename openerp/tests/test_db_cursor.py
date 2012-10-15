# -*- coding: utf-8 -*-
# Run with one of these commands:
#    > OPENERP_ADDONS_PATH='../../addons/trunk' OPENERP_PORT=8069 \
#      OPENERP_DATABASE=yy PYTHONPATH=. python tests/test_ir_sequence.py
#    > OPENERP_ADDONS_PATH='../../addons/trunk' OPENERP_PORT=8069 \
#      OPENERP_DATABASE=yy nosetests tests/test_ir_sequence.py
#    > OPENERP_ADDONS_PATH='../../../addons/trunk' OPENERP_PORT=8069 \
#      OPENERP_DATABASE=yy PYTHONPATH=../:. unit2 test_ir_sequence
# This assume an existing database.

import unittest2

import openerp
import common

DB = common.DB
ADMIN_USER_ID = common.ADMIN_USER_ID

def cursor():
    return openerp.modules.registry.RegistryManager.get(DB).db.cursor()


class test_ir_sequence_standard(unittest2.TestCase):
    """ Try cr.execute with wrong parameters """

    def test_execute_bad_params(self):
        """ Try to use non-iterable in query parameters. """
        cr = cursor()
        with self.assertRaises(ValueError):
            cr.execute("SELECT id FROM res_users WHERE login=%s", 'admin')
        with self.assertRaises(ValueError):
            cr.execute("SELECT id FROM res_users WHERE id=%s", 1)
        with self.assertRaises(ValueError):
            cr.execute("SELECT id FROM res_users WHERE id=%s", '1')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
