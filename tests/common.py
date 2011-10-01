# -*- coding: utf-8 -*-
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

common_proxy_61 = None
db_proxy_61 = None
model_proxy_61 = None

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

    global common_proxy_61
    global db_proxy_61
    global model_proxy_61

    # Use the new (6.1) API.
    url = 'http://%s:%d/openerp/6.1/xmlrpc/' % (HOST, PORT)
    common_proxy_61 = xmlrpclib.ServerProxy(url + 'common')
    db_proxy_61 = xmlrpclib.ServerProxy(url + 'db')
    model_proxy_61 = xmlrpclib.ServerProxy(url + 'model/' + DB)


    # Ugly way to ensure the server is listening.
    time.sleep(2)

def tearDownModule():
    """ Shutdown the OpenERP server similarly to a single ctrl-c. """
    openerp.service.stop_services()
