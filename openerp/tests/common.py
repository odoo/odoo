# -*- coding: utf-8 -*-
"""
The module :mod:`openerp.tests.common` provides a few helpers and classes to write
tests.
"""
import json
import os
import select
import subprocess
import threading
import time
import unittest2
import uuid
import xmlrpclib
import logging

import openerp

_logger = logging.getLogger(__name__)

# The openerp library is supposed already configured.
ADDONS_PATH = openerp.tools.config['addons_path']
HOST = '127.0.0.1'
PORT = openerp.tools.config['xmlrpc_port']
DB = openerp.tools.config['db_name']

# If the database name is not provided on the command-line,
# use the one on the thread (which means if it is provided on
# the command-line, this will break when installing another
# database from XML-RPC).
if not DB and hasattr(threading.current_thread(), 'dbname'):
    DB = threading.current_thread().dbname

ADMIN_USER = 'admin'
ADMIN_USER_ID = openerp.SUPERUSER_ID
ADMIN_PASSWORD = 'admin'

HTTP_SESSION = {}

class BaseCase(unittest2.TestCase):
    """
    Subclass of TestCase for common OpenERP-specific code.
    
    This class is abstract and expects self.cr and self.uid to be initialized by subclasses.
    """

    @classmethod
    def cursor(self):
        return openerp.modules.registry.RegistryManager.get(DB).db.cursor()

    @classmethod
    def registry(self, model):
        return openerp.modules.registry.RegistryManager.get(DB)[model]

    @classmethod
    def ref(self, xid):
        """ Returns database ID corresponding to a given identifier.

            :param xid: fully-qualified record identifier, in the form ``module.identifier``
            :raise: ValueError if not found
        """
        assert "." in xid, "this method requires a fully qualified parameter, in the following form: 'module.identifier'"
        module, xid = xid.split('.')
        _, id = self.registry('ir.model.data').get_object_reference(self.cr, self.uid, module, xid)
        return id

    @classmethod
    def browse_ref(self, xid):
        """ Returns a browsable record for the given identifier.

            :param xid: fully-qualified record identifier, in the form ``module.identifier``
            :raise: ValueError if not found
        """
        assert "." in xid, "this method requires a fully qualified parameter, in the following form: 'module.identifier'"
        module, xid = xid.split('.')
        return self.registry('ir.model.data').get_object(self.cr, self.uid, module, xid)


class TransactionCase(BaseCase):
    """
    Subclass of BaseCase with a single transaction, rolled-back at the end of
    each test (method).
    """

    def setUp(self):
        # Store cr and uid in class variables, to allow ref() and browse_ref to be BaseCase @classmethods
        # and still access them
        TransactionCase.cr = self.cursor()
        TransactionCase.uid = openerp.SUPERUSER_ID

    def tearDown(self):
        self.cr.rollback()
        self.cr.close()


class SingleTransactionCase(BaseCase):
    """
    Subclass of BaseCase with a single transaction for the whole class,
    rolled-back after all the tests.
    """

    @classmethod
    def setUpClass(cls):
        cls.cr = cls.cursor()
        cls.uid = openerp.SUPERUSER_ID

    @classmethod
    def tearDownClass(cls):
        cls.cr.rollback()
        cls.cr.close()


class HttpCase(SingleTransactionCase):
    """ Transactionnal HTTP TestCase with a phantomjs helper.
    """

    def __init__(self, methodName='runTest'):
        super(HttpCase, self).__init__(methodName)
        # v8 api with correct xmlrpc exception handling.
        self.xmlrpc_url = url_8 = 'http://%s:%d/xmlrpc/2/' % (HOST, PORT)
        self.xmlrpc_common = xmlrpclib.ServerProxy(url_8 + 'common')
        self.xmlrpc_db = xmlrpclib.ServerProxy(url_8 + 'db')
        self.xmlrpc_object = xmlrpclib.ServerProxy(url_8 + 'object')

    @classmethod
    def setUpClass(cls):
        super(HttpCase, cls).setUpClass()
        cls.session_id = uuid.uuid4().hex
        HTTP_SESSION[cls.session_id] = cls.cr

    @classmethod
    def tearDownClass(cls):
        del HTTP_SESSION[cls.session_id]
        super(HttpCase, cls).tearDownClass()

    def phantomjs(self, jsfile, timeout=30, options=None):
        """ Phantomjs Test protocol.

        Use console.log in phantomjs to output test results evrey line must be
        a one line JSON message using the following format:

        - for a success: { "event": "success", "message": "Log message" }
        - for an error:  { "event": "error", "message": "Short error description" }

        if a non json parsable line is received the helper will raise an
        exception, the output buffer will be printed and phantom will be
        killed

        """
        self.timeout = timeout
        self.options = {
            'timeout' : timeout,
            'port': PORT,
            'db': DB,
            'user': ADMIN_USER,
            'password': ADMIN_PASSWORD,
            'session_id': self.session_id,
        }
        if options:
            self.options.update(options)

        self.ignore_filters = [
            # Ignore phantomjs warnings
            "*** WARNING:",
            # Fixes an issue with PhantomJS 1.9.2 on OS X 10.9 (Mavericks)
            # cf. https://github.com/ariya/phantomjs/issues/11418
            "CoreText performance note",
        ]

        cmd = ['phantomjs', jsfile, json.dumps(self.options)]
        _logger.info('executing %s', cmd)
        try:
            phantom = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        except OSError:
            _logger.info("phantomjs not found, test %s skipped", jsfile)

        try:
            t0 = time.time()
            buf = ''
            while 1:
                if time.time() > t0 + self.timeout:
                    raise Exception("Phantom js timeout (%ss)" % self.timeout)

                ready, _, _ = select.select([phantom.stdout], [], [], 0.5)
                if ready:
                    s = phantom.stdout.read(4096)
                    if s:
                        buf += s
                    else:
                        break

                # process lines
                if '\n' in buf:
                    line, buf = buf.split('\n', 1)
                    if line not in self.ignore_filters:
                        try:
                            line_json = json.loads(line)
                            if line_json.get('event') == 'success':
                                _logger.info(line_json.get('message','ok'))
                                continue
                            elif line_json.get('event') == 'error':
                                err = line_json.get('message','error')
                                _logger.info(err)
                            else:
                                err = line + buf
                        except ValueError:
                            err = line + buf
                        raise Exception(err)
        finally:
            # kill phantomjs if phantom.exit() wasn't called in the test
            if phantom.poll() is None:
                phantom.terminate()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
