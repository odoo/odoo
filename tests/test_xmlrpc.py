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

ADDONS_PATH = os.environ['OPENERP_ADDONS_PATH']
PORT = int(os.environ['OPENERP_PORT'])
DB = os.environ['OPENERP_DATABASE']

HOST = '127.0.0.1'

ADMIN_USER = 'admin'
ADMIN_USER_ID = 1
ADMIN_PASSWORD = 'admin'

common_proxy_60 = None
db_proxy_60 = None
object_proxy_60 = None

def setUpModule():
    """
    Start the OpenERP server similary to the openerp-server script and
    setup some xmlrpclib proxies.
    """
    openerp.tools.config['addons_path'] = ADDONS_PATH
    openerp.tools.config['xmlrpc_port'] = PORT
    openerp.service.start_services()

    global common_proxy_60
    global db_proxy_60
    global object_proxy_60

    # Use the old (pre 6.1) API.
    url = 'http://%s:%d/xmlrpc/' % (HOST, PORT)
    common_proxy_60 = xmlrpclib.ServerProxy(url + 'common')
    db_proxy_60 = xmlrpclib.ServerProxy(url + 'db')
    object_proxy_60 = xmlrpclib.ServerProxy(url + 'object')

def tearDownModule():
    """ Shutdown the OpenERP server similarly to a single ctrl-c. """
    openerp.service.stop_services()

class test_xmlrpc(unittest2.TestCase):

    def test_xmlrpc_create_database_polling(self):
        """
        Simulate a OpenERP client requesting the creation of a database and
        polling the server until the creation is complete.
        """
        progress_id = db_proxy_60.create(ADMIN_PASSWORD, DB, True, False,
            ADMIN_PASSWORD)
        while True:
            time.sleep(1)
            progress, users = db_proxy_60.get_progress(ADMIN_PASSWORD,
                progress_id)
            if progress == 1.0:
                break

    def test_xmlrpc_login(self):
        """ Try to login on the common service. """
        uid = common_proxy_60.login(DB, ADMIN_USER, ADMIN_PASSWORD)
        assert uid == ADMIN_USER_ID

    def test_xmlrpc_ir_model_search(self):
        """ Try a search on the object service. """
        ids = object_proxy_60.execute(DB, ADMIN_USER_ID, ADMIN_PASSWORD,
            'ir.model', 'search', [])
        assert ids
        ids = object_proxy_60.execute(DB, ADMIN_USER_ID, ADMIN_PASSWORD,
            'ir.model', 'search', [], {})
        assert ids

if __name__ == '__main__':
    unittest2.main()

