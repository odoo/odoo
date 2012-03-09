# -*- coding: utf-8 -*-
# Run with one of these commands:
#    > OPENERP_ADDONS_PATH='../../addons/trunk' OPENERP_PORT=8069 \
#      OPENERP_DATABASE=yy PYTHONPATH=. python tests/test_xmlrpc.py
#    > OPENERP_ADDONS_PATH='../../addons/trunk' OPENERP_PORT=8069 \
#      OPENERP_DATABASE=yy nosetests tests/test_xmlrpc.py
#    > OPENERP_ADDONS_PATH='../../../addons/trunk' OPENERP_PORT=8069 \
#      OPENERP_DATABASE=yy PYTHONPATH=../:. unit2 test_xmlrpc
import time
import unittest2
import xmlrpclib

import openerp
import common

DB = None
ADMIN_USER = common.ADMIN_USER
ADMIN_USER_ID = common.ADMIN_USER_ID
ADMIN_PASSWORD = common.ADMIN_PASSWORD

def setUpModule():
    common.start_openerp()
    global DB
    DB = common.RpcCase.generate_database_name()

tearDownModule = common.stop_openerp

class test_xmlrpc(common.RpcCase):

    def test_00_xmlrpc_create_database_polling(self):
        """
        Simulate a OpenERP client requesting the creation of a database and
        polling the server until the creation is complete.
        """
        progress_id = self.proxy.db_60.create(ADMIN_PASSWORD,DB, True, False,
            ADMIN_PASSWORD)
        while True:
            time.sleep(1)
            progress, users = self.proxy.db_60.get_progress(ADMIN_PASSWORD,
                progress_id)
            if progress == 1.0:
                break

    def test_xmlrpc_login(self):
        """ Try to login on the common service. """
        uid = self.proxy.common_60.login(DB, ADMIN_USER, ADMIN_PASSWORD)
        assert uid == ADMIN_USER_ID

    def test_xmlrpc_ir_model_search(self):
        """ Try a search on the object service. """
        ids = self.proxy.object_60.execute(DB, ADMIN_USER_ID, ADMIN_PASSWORD,
            'ir.model', 'search', [])
        assert ids
        ids = self.proxy.object_60.execute(DB, ADMIN_USER_ID, ADMIN_PASSWORD,
            'ir.model', 'search', [], {})
        assert ids

    def test_xmlrpc_61_ir_model_search(self):
        """ Try a search on the object service. """

        proxy = xmlrpclib.ServerProxy(self.proxy.url_61 + 'model/' + DB +
            '/ir.model')
        ids = proxy.execute(ADMIN_USER_ID, ADMIN_PASSWORD, 'search', [])
        assert ids
        ids = proxy.execute(ADMIN_USER_ID, ADMIN_PASSWORD, 'search', [], {})
        assert ids

    def test_zz_xmlrpc_drop_database(self):
        """
        Simulate a OpenERP client requesting the deletion of a database.
        """
        assert self.proxy.db_60.drop(ADMIN_PASSWORD, DB) is True

if __name__ == '__main__':
    unittest2.main()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
