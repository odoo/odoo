# -*- coding: utf-8 -*-
# Run with one of these commands:
#    > OPENERP_ADDONS_PATH='../../addons/trunk' OPENERP_PORT=8069 \
#      OPENERP_DATABASE=yy PYTHONPATH=. python tests/test_xmlrpc.py
#    > OPENERP_ADDONS_PATH='../../addons/trunk' OPENERP_PORT=8069 \
#      OPENERP_DATABASE=yy nosetests tests/test_xmlrpc.py
#    > OPENERP_ADDONS_PATH='../../../addons/trunk' OPENERP_PORT=8069 \
#      OPENERP_DATABASE=yy PYTHONPATH=../:. unit2 test_xmlrpc
import os
import time
import unittest2
import xmlrpclib

import openerp
import common

DB = common.DB
ADMIN_USER = common.ADMIN_USER
ADMIN_USER_ID = common.ADMIN_USER_ID
ADMIN_PASSWORD = common.ADMIN_PASSWORD

setUpModule = common.setUpModule
tearDownModule = common.tearDownModule

class test_xmlrpc(unittest2.TestCase):

    def test_xmlrpc_create_database_polling(self):
        """
        Simulate a OpenERP client requesting the creation of a database and
        polling the server until the creation is complete.
        """
        progress_id = common.db_proxy_60.create(ADMIN_PASSWORD, DB, True,
            False, ADMIN_PASSWORD)
        while True:
            time.sleep(1)
            progress, users = common.db_proxy_60.get_progress(ADMIN_PASSWORD,
                progress_id)
            if progress == 1.0:
                break

    def test_xmlrpc_login(self):
        """ Try to login on the common service. """
        uid = common.common_proxy_60.login(DB, ADMIN_USER, ADMIN_PASSWORD)
        assert uid == ADMIN_USER_ID

    def test_xmlrpc_ir_model_search(self):
        """ Try a search on the object service. """
        ids = common.object_proxy_60.execute(DB, ADMIN_USER_ID, ADMIN_PASSWORD,
            'ir.model', 'search', [])
        assert ids
        ids = common.object_proxy_60.execute(DB, ADMIN_USER_ID, ADMIN_PASSWORD,
            'ir.model', 'search', [], {})
        assert ids

if __name__ == '__main__':
    unittest2.main()

