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
import itertools
import unittest2
import urllib2
import xmlrpclib
from contextlib import contextmanager
from datetime import datetime, timedelta

import werkzeug

import openerp
from openerp import api
from openerp.modules.registry import RegistryManager

_logger = logging.getLogger(__name__)

# The openerp library is supposed already configured.
ADDONS_PATH = openerp.tools.config['addons_path']
HOST = '127.0.0.1'
PORT = openerp.tools.config['xmlrpc_port']
# Useless constant, tests are aware of the content of demo data
ADMIN_USER_ID = openerp.SUPERUSER_ID


def get_db_name():
    db = openerp.tools.config['db_name']
    # If the database name is not provided on the command-line,
    # use the one on the thread (which means if it is provided on
    # the command-line, this will break when installing another
    # database from XML-RPC).
    if not db and hasattr(threading.current_thread(), 'dbname'):
        return threading.current_thread().dbname
    return db


# For backwards-compatibility - get_db_name() should be used instead
DB = get_db_name()


def at_install(flag):
    """ Sets the at-install state of a test, the flag is a boolean specifying
    whether the test should (``True``) or should not (``False``) run during
    module installation.

    By default, tests are run right after installing the module, before
    starting the installation of the next module.
    """
    def decorator(obj):
        obj.at_install = flag
        return obj
    return decorator

def post_install(flag):
    """ Sets the post-install state of a test. The flag is a boolean
    specifying whether the test should or should not run after a set of
    module installations.

    By default, tests are *not* run after installation of all modules in the
    current installation set.
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

    longMessage = True      # more verbose error message by default: https://www.odoo.com/r/Vmh

    def cursor(self):
        return self.registry.cursor()

    def ref(self, xid):
        """ Returns database ID for the provided :term:`external identifier`,
        shortcut for ``get_object_reference``

        :param xid: fully-qualified :term:`external identifier`, in the form
                    :samp:`{module}.{identifier}`
        :raise: ValueError if not found
        :returns: registered id
        """
        assert "." in xid, "this method requires a fully qualified parameter, in the following form: 'module.identifier'"
        module, xid = xid.split('.')
        _, id = self.registry('ir.model.data').get_object_reference(self.cr, self.uid, module, xid)
        return id

    def browse_ref(self, xid):
        """ Returns a record object for the provided
        :term:`external identifier`

        :param xid: fully-qualified :term:`external identifier`, in the form
                    :samp:`{module}.{identifier}`
        :raise: ValueError if not found
        :returns: :class:`~openerp.models.BaseModel`
        """
        assert "." in xid, "this method requires a fully qualified parameter, in the following form: 'module.identifier'"
        module, xid = xid.split('.')
        return self.registry('ir.model.data').get_object(self.cr, self.uid, module, xid)

    @contextmanager
    def _assertRaises(self, exception):
        """ Context manager that clears the environment upon failure. """
        with super(BaseCase, self).assertRaises(exception) as cm:
            with self.env.clear_upon_failure():
                yield cm

    def assertRaises(self, exception, func=None, *args, **kwargs):
        if func:
            with self._assertRaises(exception):
                func(*args, **kwargs)
        else:
            return self._assertRaises(exception)


class TransactionCase(BaseCase):
    """ TestCase in which each test method is run in its own transaction,
    and with its own cursor. The transaction is rolled back and the cursor
    is closed after each test.
    """

    def setUp(self):
        self.registry = RegistryManager.get(get_db_name())
        #: current transaction's cursor
        self.cr = self.cursor()
        self.uid = openerp.SUPERUSER_ID
        #: :class:`~openerp.api.Environment` for the current test case
        self.env = api.Environment(self.cr, self.uid, {})

        @self.addCleanup
        def reset():
            # rollback and close the cursor, and reset the environments
            self.env.reset()
            self.cr.rollback()
            self.cr.close()

    def patch_order(self, model, order):
        m_e = self.env[model]
        m_r = self.registry(model)

        old_order = m_e._order

        @self.addCleanup
        def cleanup():
            m_r._order = type(m_e)._order = old_order

        m_r._order = type(m_e)._order = order


class SingleTransactionCase(BaseCase):
    """ TestCase in which all test methods are run in the same transaction,
    the transaction is started with the first test method and rolled back at
    the end of the last.
    """

    @classmethod
    def setUpClass(cls):
        cls.registry = RegistryManager.get(get_db_name())
        cls.cr = cls.registry.cursor()
        cls.uid = openerp.SUPERUSER_ID
        cls.env = api.Environment(cls.cr, cls.uid, {})

    @classmethod
    def tearDownClass(cls):
        # rollback and close the cursor, and reset the environments
        cls.env.reset()
        cls.cr.rollback()
        cls.cr.close()


savepoint_seq = itertools.count()
class SavepointCase(SingleTransactionCase):
    """ Similar to :class:`SingleTransactionCase` in that all test methods
    are run in a single transaction *but* each test case is run inside a
    rollbacked savepoint (sub-transaction).

    Useful for test cases containing fast tests but with significant database
    setup common to all cases (complex in-db test data): :meth:`~.setUpClass`
    can be used to generate db test data once, then all test cases use the
    same data without influencing one another but without having to recreate
    the test data either.
    """
    def setUp(self):
        self._savepoint_id = next(savepoint_seq)
        self.cr.execute('SAVEPOINT test_%d' % self._savepoint_id)
    def tearDown(self):
        self.cr.execute('ROLLBACK TO SAVEPOINT test_%d' % self._savepoint_id)
        self.env.clear()
        self.registry.clear_caches()


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
    """ Transactional HTTP TestCase with url_open and phantomjs helpers.
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
        self.session.db = get_db_name()
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
            url = '/login?%s' % werkzeug.urls.url_encode({'db': get_db_name(),'login': user, 'key': password})
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
                    return True
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
            phantom = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=None)
        except OSError:
            raise unittest2.SkipTest("PhantomJS not found")
        result = False
        try:
            result = self.phantom_poll(phantom, timeout)
        finally:
            # kill phantomjs if phantom.exit() wasn't called in the test
            if phantom.poll() is None:
                phantom.terminate()
                phantom.wait()
            self._wait_remaining_requests()
            # we ignore phantomjs return code as we kill it as soon as we have ok
            _logger.info("phantom_run execution finished")
            self.assertTrue(
                result,
                "PhantomJS test completed without reporting success; "
                "the log may contain errors or hints.")

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
            'db': get_db_name(),
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
