# -*- coding: utf-8 -*-
"""
The module :mod:`openerp.tests.common` provides unittest2 test cases and a few
helpers and classes to write tests.

"""
import errno
import glob
import json
import logging
import os
import select
import subprocess
import threading
import time
import unittest2
import urllib2
import xmlrpclib
from datetime import datetime, timedelta
from shutil import rmtree
from tempfile import mkdtemp

import werkzeug

import openerp
from openerp import api
from openerp.modules.registry import RegistryManager

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
# Useless constant, tests are aware of the content of demo data
ADMIN_USER_ID = openerp.SUPERUSER_ID

def at_install(flag):
    """ Sets the at-install state of a test, the flag is a boolean specifying
    whether the test should (``True``) or should not (``False``) run during
    module installation.

    By default, tests are run at install.
    """
    def decorator(obj):
        obj.at_install = flag
        return obj
    return decorator

def post_install(flag):
    """ Sets the post-install state of a test. The flag is a boolean
    specifying whether the test should or should not run after a set of
    module installations.

    By default, tests are *not* run after installation.
    """
    def decorator(obj):
        obj.post_install = flag
        return obj
    return decorator

class BaseCase(unittest2.TestCase):
    """
    Subclass of TestCase for common OpenERP-specific code.
    
    This class is abstract and expects self.registry, self.cr and self.uid to be
    initialized by subclasses.
    """

    def cursor(self):
        return self.registry.cursor()

    def ref(self, xid):
        """ Returns database ID corresponding to a given identifier.

            :param xid: fully-qualified record identifier, in the form ``module.identifier``
            :raise: ValueError if not found
        """
        assert "." in xid, "this method requires a fully qualified parameter, in the following form: 'module.identifier'"
        module, xid = xid.split('.')
        _, id = self.registry('ir.model.data').get_object_reference(self.cr, self.uid, module, xid)
        return id

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
        self.registry = RegistryManager.get(DB)
        self.cr = self.cursor()
        self.uid = openerp.SUPERUSER_ID
        self.env = api.Environment(self.cr, self.uid, {})

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
        cls.registry = RegistryManager.get(DB)
        cls.cr = cls.registry.cursor()
        cls.uid = openerp.SUPERUSER_ID
        cls.env = api.Environment(cls.cr, cls.uid, {})

    @classmethod
    def tearDownClass(cls):
        cls.cr.rollback()
        cls.cr.close()

class RedirectHandler(urllib2.HTTPRedirectHandler):
    """
    HTTPRedirectHandler is predicated upon HTTPErrorProcessor being used and
    works by intercepting 3xy "errors".

    Inherit from it to handle 3xy non-error responses instead, as we're not
    using the error processor
    """

    def http_response(self, request, response):
        code, msg, hdrs = response.code, response.msg, response.info()

        if 300 <= code < 400:
            return self.parent.error(
                'http', request, response, code, msg, hdrs)

        return response

    https_response = http_response

class HttpCase(TransactionCase):
    """ Transactionnal HTTP TestCase with url_open and phantomjs helpers.
    """

    def __init__(self, methodName='runTest'):
        super(HttpCase, self).__init__(methodName)
        # v8 api with correct xmlrpc exception handling.
        self.xmlrpc_url = url_8 = 'http://%s:%d/xmlrpc/2/' % (HOST, PORT)
        self.xmlrpc_common = xmlrpclib.ServerProxy(url_8 + 'common')
        self.xmlrpc_db = xmlrpclib.ServerProxy(url_8 + 'db')
        self.xmlrpc_object = xmlrpclib.ServerProxy(url_8 + 'object')

    def setUp(self):
        super(HttpCase, self).setUp()
        self.registry.enter_test_mode()
        # setup a magic session_id that will be rollbacked
        self.session = openerp.http.root.session_store.new()
        self.session_id = self.session.sid
        self.session.db = DB
        openerp.http.root.session_store.save(self.session)
        # setup an url opener helper
        self.opener = urllib2.OpenerDirector()
        self.opener.add_handler(urllib2.UnknownHandler())
        self.opener.add_handler(urllib2.HTTPHandler())
        self.opener.add_handler(urllib2.HTTPSHandler())
        self.opener.add_handler(urllib2.HTTPCookieProcessor())
        self.opener.add_handler(RedirectHandler())
        self.opener.addheaders.append(('Cookie', 'session_id=%s' % self.session_id))

    def tearDown(self):
        self.registry.leave_test_mode()
        super(HttpCase, self).tearDown()

    def url_open(self, url, data=None, timeout=10):
        if url.startswith('/'):
            url = "http://localhost:%s%s" % (PORT, url)
        return self.opener.open(url, data, timeout)

    def authenticate(self, user, password):
        if user is not None:
            url = '/login?%s' % werkzeug.urls.url_encode({'db': DB,'login': user, 'key': password})
            auth = self.url_open(url)
            assert auth.getcode() < 400, "Auth failure %d" % auth.getcode()

    def phantom_poll(self, phantom, timeout):
        """ Phantomjs Test protocol.

        Use console.log in phantomjs to output test results:

        - for a success: console.log("ok")
        - for an error:  console.log("error")

        Other lines are relayed to the test log.

        """
        t0 = datetime.now()
        td = timedelta(seconds=timeout)
        buf = bytearray()
        while True:
            # timeout
            self.assertLess(datetime.now() - t0, td,
                "PhantomJS tests should take less than %s seconds" % timeout)

            # read a byte
            try:
                ready, _, _ = select.select([phantom.stdout], [], [], 0.5)
            except select.error, e:
                # In Python 2, select.error has no relation to IOError or
                # OSError, and no errno/strerror/filename, only a pair of
                # unnamed arguments (matching errno and strerror)
                err, _ = e.args
                if err == errno.EINTR:
                    continue
                raise

            if ready:
                s = phantom.stdout.read(1)
                if not s:
                    break
                buf.append(s)

            # process lines
            if '\n' in buf:
                line, buf = buf.split('\n', 1)
                line = str(line)

                # relay everything from console.log, even 'ok' or 'error...' lines
                _logger.info("phantomjs: %s", line)

                if line == "ok":
                    break
                if line.startswith("error"):
                    line_ = line[6:]
                    # when error occurs the execution stack may be sent as as JSON
                    try:
                        line_ = json.loads(line_)
                    except ValueError: 
                        pass
                    self.fail(line_ or "phantomjs test failed")

    def phantom_run(self, cmd, timeout):
        _logger.info('phantom_run executing %s', ' '.join(cmd))

        ls_glob = os.path.expanduser('~/.qws/share/data/Ofi Labs/PhantomJS/http_localhost_%s.*'%PORT)
        for i in glob.glob(ls_glob):
            _logger.info('phantomjs unlink localstorage %s', i)
            os.unlink(i)
        try:
            phantom = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        except OSError:
            raise unittest2.SkipTest("PhantomJS not found")
        try:
            self.phantom_poll(phantom, timeout)
        finally:
            # kill phantomjs if phantom.exit() wasn't called in the test
            if phantom.poll() is None:
                phantom.terminate()
                phantom.wait()
            self._wait_remaining_requests()
            _logger.info("phantom_run execution finished")

    def _wait_remaining_requests(self):
        t0 = int(time.time())
        for thread in threading.enumerate():
            if thread.name.startswith('openerp.service.http.request.'):
                while thread.isAlive():
                    # Need a busyloop here as thread.join() masks signals
                    # and would prevent the forced shutdown.
                    thread.join(0.05)
                    time.sleep(0.05)
                    t1 = int(time.time())
                    if t0 != t1:
                        _logger.info('remaining requests')
                        openerp.tools.misc.dumpstacks()
                        t0 = t1

    def phantom_jsfile(self, jsfile, timeout=60, **kw):
        options = {
            'timeout' : timeout,
            'port': PORT,
            'db': DB,
            'session_id': self.session_id,
        }
        options.update(kw)
        phantomtest = os.path.join(os.path.dirname(__file__), 'phantomtest.js')
        # phantom.args[0] == phantomtest path
        # phantom.args[1] == options
        cmd = [
            'phantomjs',
            jsfile, phantomtest, json.dumps(options)
        ]
        self.phantom_run(cmd, timeout)

    def phantom_js(self, url_path, code, ready="window", login=None, timeout=60, **kw):
        """ Test js code running in the browser
        - optionnally log as 'login'
        - load page given by url_path
        - wait for ready object to be available
        - eval(code) inside the page

        To signal success test do:
        console.log('ok')

        To signal failure do:
        console.log('error')

        If neither are done before timeout test fails.
        """
        options = {
            'port': PORT,
            'db': DB,
            'url_path': url_path,
            'code': code,
            'ready': ready,
            'timeout' : timeout,
            'login' : login,
            'session_id': self.session_id,
        }
        options.update(kw)
        options.setdefault('password', options.get('login'))
        phantomtest = os.path.join(os.path.dirname(__file__), 'phantomtest.js')
        cmd = ['phantomjs', phantomtest, json.dumps(options)]
        self.phantom_run(cmd, timeout)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
