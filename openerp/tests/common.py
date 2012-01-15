# -*- coding: utf-8 -*-
import os
import time
import xmlrpclib

import openerp

# The openerp library is supposed already configured.
ADDONS_PATH = openerp.tools.config['addons_path']
PORT = openerp.tools.config['xmlrpc_port']
DB = openerp.tools.config['db_name']

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
model_uri_61 = None

def start_openerp():
    """
    Start the OpenERP server similary to the openerp-server script.
    """
    openerp.service.start_services()

    # Ugly way to ensure the server is listening.
    time.sleep(2)

def create_xmlrpc_proxies():
    """
    setup some xmlrpclib proxies.
    """
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
    global model_uri_61

    # Use the new (6.1) API.
    model_uri_61 = 'http://%s:%d/openerp/xmlrpc/1/' % (HOST, PORT)
    common_proxy_61 = xmlrpclib.ServerProxy(model_uri_61 + 'common')
    db_proxy_61 = xmlrpclib.ServerProxy(model_uri_61 + 'db')
    model_proxy_61 = xmlrpclib.ServerProxy(model_uri_61 + 'model/' + DB)

def tearDownModule():
    """ Shutdown the OpenERP server similarly to a single ctrl-c. """
    openerp.service.stop_services()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
