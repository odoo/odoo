# -*- coding: utf-8 -*-
"""
The module :mod:`odoo.tests.common` provides unittest test cases and a few
helpers and classes to write tests.

"""
import collections
import errno
import glob
import importlib
import itertools
import json
import logging
import operator
import os
import re
import select
import subprocess
import threading
import time
import unittest
from contextlib import contextmanager
from datetime import datetime, timedelta, date
from pprint import pformat

import requests
from decorator import decorator
from lxml import etree, html

from odoo.models import BaseModel
from odoo.tools import pycompat
from odoo.tools.safe_eval import safe_eval

try:
    from itertools import zip_longest as izip_longest
except ImportError:
    from itertools import izip_longest
try:
    from xmlrpc import client as xmlrpclib
except ImportError:
    # pylint: disable=bad-python3-import
    import xmlrpclib

import odoo
from odoo import api


_logger = logging.getLogger(__name__)

# The odoo library is supposed already configured.
ADDONS_PATH = odoo.tools.config['addons_path']
HOST = '127.0.0.1'
PORT = odoo.tools.config['http_port']
# Useless constant, tests are aware of the content of demo data
ADMIN_USER_ID = odoo.SUPERUSER_ID


def get_db_name():
    db = odoo.tools.config['db_name']
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

class TreeCase(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        super(TreeCase, self).__init__(methodName)
        self.addTypeEqualityFunc(etree._Element, self.assertTreesEqual)
        self.addTypeEqualityFunc(html.HtmlElement, self.assertTreesEqual)

    def assertTreesEqual(self, n1, n2, msg=None):
        self.assertEqual(n1.tag, n2.tag, msg)
        # Because lxml.attrib is an ordereddict for which order is important
        # to equality, even though *we* don't care
        self.assertEqual(dict(n1.attrib), dict(n2.attrib), msg)

        self.assertEqual((n1.text or u'').strip(), (n2.text or u'').strip(), msg)
        self.assertEqual((n1.tail or u'').strip(), (n2.tail or u'').strip(), msg)

        for c1, c2 in izip_longest(n1, n2):
            self.assertEqual(c1, c2, msg)


class MetaCase(type):
    """ Metaclass of test case classes to assign default 'test_tags':
        'standard', 'at_install' and the name of the module.
    """
    def __init__(cls, name, bases, attrs):
        super(MetaCase, cls).__init__(name, bases, attrs)
        # assign default test tags
        if cls.__module__.startswith('odoo.addons.'):
            module = cls.__module__.split('.')[2]
            cls.test_tags = {'standard', 'at_install', module}


class BaseCase(TreeCase, MetaCase('DummyCase', (object,), {})):
    """
    Subclass of TestCase for common OpenERP-specific code.

    This class is abstract and expects self.registry, self.cr and self.uid to be
    initialized by subclasses.
    """

    longMessage = True      # more verbose error message by default: https://www.odoo.com/r/Vmh
    warm = True             # False during warm-up phase (see :func:`warmup`)

    def cursor(self):
        return self.registry.cursor()

    @property
    def uid(self):
        """ Get the current uid. """
        return self.env.uid

    @uid.setter
    def uid(self, user):
        """ Set the uid by changing the test's environment. """
        self.env = self.env(user=user)

    def ref(self, xid):
        """ Returns database ID for the provided :term:`external identifier`,
        shortcut for ``get_object_reference``

        :param xid: fully-qualified :term:`external identifier`, in the form
                    :samp:`{module}.{identifier}`
        :raise: ValueError if not found
        :returns: registered id
        """
        return self.browse_ref(xid).id

    def browse_ref(self, xid):
        """ Returns a record object for the provided
        :term:`external identifier`

        :param xid: fully-qualified :term:`external identifier`, in the form
                    :samp:`{module}.{identifier}`
        :raise: ValueError if not found
        :returns: :class:`~odoo.models.BaseModel`
        """
        assert "." in xid, "this method requires a fully qualified parameter, in the following form: 'module.identifier'"
        return self.env.ref(xid)

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

    @contextmanager
    def assertQueryCount(self, default=0, **counters):
        """ Context manager that counts queries. It may be invoked either with
            one value, or with a set of named arguments like ``login=value``::

                with self.assertQueryCount(42):
                    ...

                with self.assertQueryCount(admin=3, demo=5):
                    ...

            The second form is convenient when used with :func:`users`.
        """
        if self.warm:
            login = self.env.user.login
            expected = counters.get(login, default)
            count0 = self.cr.sql_log_count
            yield
            count = self.cr.sql_log_count - count0
            if not count <= expected:
                msg = "Query count for user %s: got %d instead of %d"
                self.fail(msg % (login, count, expected))
            elif count < expected:
                logger = logging.getLogger(type(self).__module__)
                msg = "Query count for user %s: got %d instead of %d"
                logger.info(msg, login, count, expected)
        else:
            yield

    def shortDescription(self):
        doc = self._testMethodDoc
        return doc and ' '.join(l.strip() for l in doc.splitlines() if not l.isspace()) or None

    if not pycompat.PY2:
        # turns out this thing may not be quite as useful as we thought...
        def assertItemsEqual(self, a, b, msg=None):
            self.assertCountEqual(a, b, msg=None)

class TransactionCase(BaseCase):
    """ TestCase in which each test method is run in its own transaction,
    and with its own cursor. The transaction is rolled back and the cursor
    is closed after each test.
    """

    def setUp(self):
        super(TransactionCase, self).setUp()
        self.registry = odoo.registry(get_db_name())
        #: current transaction's cursor
        self.cr = self.cursor()
        #: :class:`~odoo.api.Environment` for the current test case
        self.env = api.Environment(self.cr, odoo.SUPERUSER_ID, {})

        @self.addCleanup
        def reset():
            # rollback and close the cursor, and reset the environments
            self.registry.clear_caches()
            self.registry.reset_changes()
            self.env.reset()
            self.cr.rollback()
            self.cr.close()

        self.patch(type(self.env['res.partner']), '_get_gravatar_image', lambda *a: False)

    def patch(self, obj, key, val):
        """ Do the patch ``setattr(obj, key, val)``, and prepare cleanup. """
        old = getattr(obj, key)
        setattr(obj, key, val)
        self.addCleanup(setattr, obj, key, old)

    def patch_order(self, model, order):
        """ Patch the order of the given model (name), and prepare cleanup. """
        self.patch(type(self.env[model]), '_order', order)


class SingleTransactionCase(BaseCase):
    """ TestCase in which all test methods are run in the same transaction,
    the transaction is started with the first test method and rolled back at
    the end of the last.
    """

    @classmethod
    def setUpClass(cls):
        super(SingleTransactionCase, cls).setUpClass()
        cls.registry = odoo.registry(get_db_name())
        cls.cr = cls.registry.cursor()
        cls.env = api.Environment(cls.cr, odoo.SUPERUSER_ID, {})

    @classmethod
    def tearDownClass(cls):
        # rollback and close the cursor, and reset the environments
        cls.registry.clear_caches()
        cls.env.reset()
        cls.cr.rollback()
        cls.cr.close()
        super(SingleTransactionCase, cls).tearDownClass()


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
        super(SavepointCase, self).setUp()
        self._savepoint_id = next(savepoint_seq)
        self.cr.execute('SAVEPOINT test_%d' % self._savepoint_id)

    def tearDown(self):
        self.cr.execute('ROLLBACK TO SAVEPOINT test_%d' % self._savepoint_id)
        self.env.clear()
        self.registry.clear_caches()
        super(SavepointCase, self).tearDown()


class HttpCase(TransactionCase):
    """ Transactional HTTP TestCase with url_open and phantomjs helpers.
    """
    registry_test_mode = True

    def __init__(self, methodName='runTest'):
        super(HttpCase, self).__init__(methodName)
        # v8 api with correct xmlrpc exception handling.
        self.xmlrpc_url = url_8 = 'http://%s:%d/xmlrpc/2/' % (HOST, PORT)
        self.xmlrpc_common = xmlrpclib.ServerProxy(url_8 + 'common')
        self.xmlrpc_db = xmlrpclib.ServerProxy(url_8 + 'db')
        self.xmlrpc_object = xmlrpclib.ServerProxy(url_8 + 'object')

    def setUp(self):
        super(HttpCase, self).setUp()
        if self.registry_test_mode:
            self.registry.enter_test_mode()
            self.addCleanup(self.registry.leave_test_mode)
        # setup a magic session_id that will be rollbacked
        self.session = odoo.http.root.session_store.new()
        self.session_id = self.session.sid
        self.session.db = get_db_name()
        odoo.http.root.session_store.save(self.session)
        # setup an url opener helper
        self.opener = requests.Session()
        self.opener.cookies['session_id'] = self.session_id

    def url_open(self, url, data=None, timeout=10):
        if url.startswith('/'):
            url = "http://%s:%s%s" % (HOST, PORT, url)
        if data:
            return self.opener.post(url, data=data, timeout=timeout)
        return self.opener.get(url, timeout=timeout)

    def authenticate(self, user, password):
        # stay non-authenticated
        if user is None:
            return

        db = get_db_name()
        uid = self.registry['res.users'].authenticate(db, user, password, None)
        env = api.Environment(self.cr, uid, {})

        # self.session.authenticate(db, user, password, uid=uid)
        # OpenERPSession.authenticate accesses the current request, which we
        # don't have, so reimplement it manually...
        session = self.session

        session.db = db
        session.uid = uid
        session.login = user
        session.password = password
        session.context = env['res.users'].context_get() or {}
        session.context['uid'] = uid
        session._fix_lang(session.context)

        odoo.http.root.session_store.save(session)

    def phantom_poll(self, phantom, timeout):
        """ Phantomjs Test protocol.

        Use console.log in phantomjs to output test results:

        - for a success: console.log("ok")
        - for an error:  console.log("error")

        Other lines are relayed to the test log.

        """
        logger = _logger.getChild('phantomjs')
        t0 = datetime.now()
        td = timedelta(seconds=timeout)
        buf = bytearray()
        pid = phantom.stdout.fileno()
        while True:
            # timeout
            self.assertLess(datetime.now() - t0, td,
                "PhantomJS tests should take less than %s seconds" % timeout)

            # read a byte
            try:
                ready, _, _ = select.select([pid], [], [], 0.5)
            except select.error as e:
                # In Python 2, select.error has no relation to IOError or
                # OSError, and no errno/strerror/filename, only a pair of
                # unnamed arguments (matching errno and strerror)
                err, _ = e.args
                if err == errno.EINTR:
                    continue
                raise

            if not ready:
                continue

            s = os.read(pid, 4096)
            if not s:
                self.fail("Ran out of data to read")
            buf.extend(s)

            # process lines
            while b'\n' in buf and (not buf.startswith(b'<phantomLog>') or b'</phantomLog>' in buf):

                if buf.startswith(b'<phantomLog>'):
                    line, buf = buf[12:].split(b'</phantomLog>\n', 1)
                else:
                    line, buf = buf.split(b'\n', 1)
                line = line.decode('utf-8')

                lline = line.lower()
                if lline.startswith(("error", "server application error")):
                    try:
                        # when errors occur the execution stack may be sent as a JSON
                        prefix = lline.index('error') + 6
                        self.fail(pformat(json.loads(line[prefix:])))
                    except ValueError:
                        self.fail(lline)
                elif lline.startswith("warning"):
                    logger.warn(line)
                else:
                    logger.info(line)

                if line == "ok":
                    return True

    def phantom_run(self, cmd, timeout):
        _logger.info('phantom_run executing %s', ' '.join(cmd))

        ls_glob = os.path.expanduser('~/.qws/share/data/Ofi Labs/PhantomJS/http_%s_%s.*' % (HOST, PORT))
        ls_glob2 = os.path.expanduser('~/.local/share/Ofi Labs/PhantomJS/http_%s_%s.*' % (HOST, PORT))
        for i in (glob.glob(ls_glob) + glob.glob(ls_glob2)):
            _logger.info('phantomjs unlink localstorage %s', i)
            os.unlink(i)
        try:
            phantom = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=None, close_fds=True)
        except OSError:
            raise unittest.SkipTest("PhantomJS not found")
        try:
            result = self.phantom_poll(phantom, timeout)
            self.assertTrue(
                result,
                "PhantomJS test completed without reporting success; "
                "the log may contain errors or hints.")
        finally:
            # kill phantomjs if phantom.exit() wasn't called in the test
            if phantom.poll() is None:
                _logger.info("Terminating phantomjs")
                phantom.terminate()
                phantom.wait()
            else:
                # if we had to terminate phantomjs its return code is
                # always -15 so we don't care
                # check PhantomJS health
                from signal import SIGSEGV
                _logger.info("Phantom JS return code: %d" % phantom.returncode)
                if phantom.returncode == -SIGSEGV:
                    _logger.error("Phantom JS has crashed (segmentation fault) during testing; log may not be relevant")

            self._wait_remaining_requests()

    def _wait_remaining_requests(self):
        t0 = int(time.time())
        for thread in threading.enumerate():
            if thread.name.startswith('odoo.service.http.request.'):
                join_retry_count = 10
                while thread.isAlive():
                    # Need a busyloop here as thread.join() masks signals
                    # and would prevent the forced shutdown.
                    thread.join(0.05)
                    join_retry_count -= 1
                    if join_retry_count < 0:
                        _logger.warning("Stop waiting for thread %s handling request for url %s",
                                        thread.name, thread.url)
                        break
                    time.sleep(0.5)
                    t1 = int(time.time())
                    if t0 != t1:
                        _logger.info('remaining requests')
                        odoo.tools.misc.dumpstacks()
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
            'session_id': self.session_id,
        }
        options.update(kw)

        self.authenticate(login, login)

        phantomtest = os.path.join(os.path.dirname(__file__), 'phantomtest.js')
        cmd = ['phantomjs', phantomtest, json.dumps(options)]
        self.phantom_run(cmd, timeout)


def users(*logins):
    """ Decorate a method to execute it once for each given user. """
    @decorator
    def wrapper(func, *args, **kwargs):
        self = args[0]
        old_uid = self.uid
        try:
            # retrieve users
            user_id = {
                user.login: user.id
                for user in self.env['res.users'].search([('login', 'in', list(logins))])
            }
            for login in logins:
                # switch user
                self.uid = user_id[login]
                # execute func
                func(*args, **kwargs)
        finally:
            self.uid = old_uid

    return wrapper


@decorator
def warmup(func, *args, **kwargs):
    """ Decorate a test method to run it twice: once for a warming up phase, and
        a second time for real.  The test attribute ``warm`` is set to ``False``
        during warm up, and ``True`` once the test is warmed up.  Note that the
        effects of the warmup phase are rolled back thanks to a savepoint.
    """
    self = args[0]
    # run once to warm up the caches
    self.warm = False
    self.cr.execute('SAVEPOINT test_warmup')
    func(*args, **kwargs)
    self.cr.execute('ROLLBACK TO SAVEPOINT test_warmup')
    self.env.cache.invalidate()
    # run once for real
    self.warm = True
    func(*args, **kwargs)


def can_import(module):
    """ Checks if <module> can be imported, returns ``True`` if it can be,
    ``False`` otherwise.

    To use with ``unittest.skipUnless`` for tests conditional on *optional*
    dependencies, which may or may be present but must still be tested if
    possible.
    """
    try:
        importlib.import_module(module)
    except ImportError:
        return False
    else:
        return True

# TODO: sub-views (o2m, m2m) -> sub-form?
# TODO: domains
ref_re = re.compile("""
# first match 'form_view_ref' key, backrefs are used to handle single or
# double quoting of the value
(['"])(?P<view_type>\w+)_view_ref\1
# colon separator (with optional spaces around)
\s*:\s*
# open quote for value
(['"])
(?P<view_id>
    # we'll just match stuff which is normally part of an xid:
    # word and "." characters
    [.\w]+
)
# close with same quote as opening
\2
""", re.VERBOSE)
class Form(object):
    """ Server-side form view implementation (partial)

    Implements much of the "form view" manipulation flow, such that
    server-side tests can more properly reflect the behaviour which would be
    observed when manipulating the interface:

    * call default_get and the relevant onchanges on "creation"
    * call the relevant onchanges on setting fields
    * properly handle defaults & onchanges around x2many fields

    Saving the form returns the created record if in creation mode.

    Regular fields can just be assigned directly to the form, for
    :class:`~odoo.fields.Many2one` fields assign a singleton recordset::

        # empty recordset => creation mode
        f = Form(self.env['sale.order'])
        f.partner_id = a_partner
        so = f.save()

    When editing a record, using the form as a context manager to
    automatically save it at the end of the scope::

        with Form(so) as f2:
            f2.payment_term_id = env.ref('account.account_payment_term_15days')
            # f2 is saved here

    For :class:`~odoo.fields.Many2many` fields, the field itself is a
    :class:`~odoo.tests.common.M2MProxy` and can be altered by adding or
    removing records::

        with Form(user) as u:
            u.groups_id.add(env.ref('account.group_account_manager'))
            u.groups_id.remove(id=env.ref('base.group_portal').id)

    Finally :class:`~odoo.fields.One2many` are reified as
    :class:`~odoo.tests.common.O2MProxy`.

    Because the :class:`~odoo.fields.One2many` only exists through its
    parent, it is manipulated more directly by creating "sub-forms"
    with the :meth:`~odoo.tests.common.O2MProxy.new` and
    :meth:`~odoo.tests.common.O2MProxy.edit` methods. These would
    normally be used as context managers since they get saved in the
    parent record::

        with Form(so) as f3:
            # add support
            with f3.order_line.new() as line:
                line.product_id = env.ref('product.product_product_2')
            # add a computer
            with f3.order_line.new() as line:
                line.product_id = env.ref('product.product_product_3')
            # we actually want 5 computers
            with f3.order_line.edit(1) as line:
                line.product_uom_qty = 5
            # remove support
            f3.order_line.remove(index=0)
            # SO is saved here

    :param recordp: empty or singleton recordset. An empty recordset will
                    put the view in "creation" mode and trigger calls to
                    default_get and on-load onchanges, a singleton will
                    put it in "edit" mode and only load the view's data.
    :type recordp: odoo.models.Model
    :param view: the id, xmlid or actual view object to use for
                    onchanges and view constraints. If none is provided,
                    simply loads the default view for the model.
    :type view: int | str | odoo.model.Model

    .. versionadded:: 12.0
    """
    def __init__(self, recordp, view=None):
        # necessary as we're overriding setattr
        assert isinstance(recordp, BaseModel)
        env = recordp.env
        object.__setattr__(self, '_env', env)

        # store model bit only
        object.__setattr__(self, '_model', recordp.browse(()))
        if isinstance(view, BaseModel):
            assert view._name == 'ir.ui.view', "the view parameter must be a view id, xid or record, got %s" % view
            view_id = view.id
        elif isinstance(view, pycompat.string_types):
            view_id = env.ref(view).id
        else:
            view_id = view or False
        fvg = recordp.fields_view_get(view_id, 'form')
        arch = etree.fromstring(fvg['arch'])

        object.__setattr__(self, '_view', fvg)
        # TODO: make this less crappy?
        # look up edition view for the O2M
        for f, descr in fvg['fields'].items():
            if descr['type'] != 'one2many':
                continue

            node = next(n for n in arch.iter('field') if n.get('name') == f)
            default_view = next(
                (m for m in node.get('mode', 'tree').split(',') if m != 'form'),
                'tree'
            )

            refs = {
                m.group('view_type'): m.group('view_id')
                for m in ref_re.finditer(node.get('context', ''))
            }
            # always fetch for simplicity, ensure we always have a tree and
            # a form view
            submodel = env[descr['relation']]
            views = submodel.with_context(**refs) \
                .load_views([(False, 'tree'), (False, 'form')])['fields_views']
            # embedded views should take the priority on externals
            views.update(descr['views'])

            # if the default view is a kanban or a non-editable list, the
            # "edition controller" is the form view
            edition = views['form']
            if default_view == 'tree':
                subarch = etree.fromstring(views['tree']['arch'])
                if subarch.get('editable'):
                    edition = views['tree']

            self._process_fvg(submodel, edition)
            descr['views']['edition'] = edition

        self._process_fvg(recordp, fvg)

        # ordered?
        vals = dict.fromkeys(fvg['fields'], False)
        object.__setattr__(self, '_values', vals)
        object.__setattr__(self, '_changed', set())
        if recordp:
            assert recordp['id'], "editing unstored records is not supported"
            # always load the id
            vals['id'] = recordp['id']

            self._init_from_values(recordp)
        else:
            self._init_from_defaults(self._model)

    def __str__(self):
        return "<%s %s(%s)>" % (
            type(self).__name__,
            self._model._name,
            self._values.get('id', False),
        )

    def _process_fvg(self, model, fvg):
        """ Post-processes to augment the fields_view_get with:

        * an id field (may not be present if not in the view but needed)
        * pre-processed modifiers (map of modifier name to json-loaded domain)
        * pre-processed onchanges list
        """
        fvg['fields']['id'] = {'type': 'id'}
        # pre-resolve modifiers & bind to arch toplevel
        modifiers = fvg['modifiers'] = {}
        contexts = fvg['contexts'] = {}
        for f in etree.fromstring(fvg['arch']).iter('field'):
            fname = f.get('name')
            modifiers[fname] = json.loads(f.get('modifiers', '{}'))
            ctx = f.get('context')
            if ctx:
                contexts[fname] = ctx
        fvg['modifiers']['id'] = {'required': False, 'readonly': True}
        fvg['onchange'] = model._onchange_spec(fvg)

    def _init_from_defaults(self, model):
        vals = self._values
        fields = self._view['fields']
        def cleanup(k, v):
            if fields[k]['type'] == 'one2many':
                # o2m default gets a (6) at the start, makes no sense
                return [c for c in v if c[0] != 6]
            return v
        defaults = {
            k: cleanup(k, v)
            for k, v in model.default_get(list(fields)).items()
            if k in fields
        }
        vals.update(defaults)
        # m2m should all be rep'd as command list
        for k, v in vals.items():
            if not v:
                type_ = fields[k]['type']
                if type_ == 'many2many':
                    vals[k] = [(6, False, [])]
                elif type_ == 'one2many':
                    vals[k] = []

        # TODO: check that only fields with default values should be sent
        self._perform_onchange(list(defaults.keys()))

    def _init_from_values(self, values):
        self._values.update(
            record_to_values(self._view['fields'], values))

    def __getattr__(self, field):
        descr = self._view['fields'].get(field)
        assert descr is not None, "%s was not found in the view" % field

        v = self._values[field]
        if descr['type'] == 'many2one':
            Model = self._env[descr['relation']]
            if not v:
                return Model
            return Model.browse(v)
        elif descr['type'] == 'many2many':
            return M2MProxy(self, field)
        elif descr['type'] == 'one2many':
            return O2MProxy(self, field)
        return v

    def _get_modifier(self, field, modifier, default=False):
        d = self._view['modifiers'][field].get(modifier, default)
        if isinstance(d, bool):
            return d

        vals = self._values
        stack = []
        for it in reversed(d):
            if it == '!':
                stack.append(not stack.pop())
            elif it == '&':
                e1 = stack.pop()
                e2 = stack.pop()
                stack.append(e1 and e2)
            elif it == '|':
                e1 = stack.pop()
                e2 = stack.pop()
                stack.append(e1 or e2)
            elif isinstance(it, list):
                f, op, val = it
                field_val = vals[f]
                stack.append(self._OPS[op](field_val, val))
            else:
                raise ValueError("Unknown domain element %s" % it)
        [result] = stack
        return result
    _OPS = {
        '=': operator.eq,
        '==': operator.eq,
        '!=': operator.ne,
        '<': operator.lt,
        '<=': operator.le,
        '>=': operator.ge,
        '>': operator.gt,
        'in': lambda a, b: a in b,
        'not in': lambda a, b: a not in b
    }
    def _get_context(self, field):
        c = self._view['contexts'].get(field)
        if not c:
            return {}

        # see _getEvalContext
        # the context for a field's evals (of domain/context) is the composition of:
        # * the parent's values
        # * ??? element.context ???
        # * the environment's context (?)
        # * a few magic values
        record_id = self._values.get('id') or False
        ctx = dict(self._values)
        ctx.update(self._env.context)
        ctx.update(
            id=record_id,
            active_id=record_id,
            active_ids=[record_id] if record_id else [],
            active_model=self._model._name,
            current_date=date.today().strftime("%Y-%m-%d"),
        )
        return safe_eval(c, ctx, {'context': ctx})

    def __setattr__(self, field, value):
        descr = self._view['fields'].get(field)
        assert descr is not None, "%s was not found in the view" % field
        assert descr['type'] not in ('many2many', 'one2many'), \
            "Can't set an o2m or m2m field, manipulate the corresponding proxies"

        # TODO: consider invisible to be the same as readonly?
        assert not self._get_modifier(field, 'readonly'), \
            "can't write on readonly field {}".format(field)

        if descr['type'] == 'many2one':
            assert isinstance(value, BaseModel) and value._name == descr['relation']
            # store just the id: that's the output of default_get & (more
            # or less) onchange.
            value = value.id

        self._values[field] = value
        self._perform_onchange([field])

    # enables with Form(...) as f: f.a = 1; f.b = 2; f.c = 3
    # q: how to get recordset?
    def __enter__(self):
        return self
    def __exit__(self, etype, _evalue, _etb):
        if not etype:
            self.save()

    def save(self):
        """ Saves the form, returns the created record if applicable

        * does not save ``readonly`` fields
        * does not save unmodified fields (during edition) — any assignment
          or onchange return marks the field as modified, even if set to its
          current value

        :raises AssertionError: if the form has any unfilled required field
        """
        id_ = self._values.get('id')
        values = self._values_to_save()
        if id_:
            r = self._model.browse(id_)
            if values:
                r.write(values)
        else:
            r = self._model.create(values)
        [data] = r.read(list(self._view['fields']))
        # FIXME: process relational fields
        # alternative: iterate on record & read from it directly? pb: would
        # provide recordsets for relational fields which may or may not be
        # what we ultimately want, but we've got to re-process them anyway so...?
        self._values.update(data)
        self._changed.clear()
        return r

    def _values_to_save(self):
        """ Validates values and returns only fields modified since
        load/save
        """
        values = {}
        for f in self._view['fields']:
            v = self._values[f]
            if self._get_modifier(f, 'required'):
                assert v is not False, "{} is a required field".format(f)

            # skip unmodified fields
            if f not in self._changed:
                continue
            if self._get_modifier(f, 'readonly'):
                continue
            # TODO: filter out (1, _, {}) from o2m values
            values[f] = v
        return values

    def _perform_onchange(self, fields):
        assert isinstance(fields, list)

        # marks any onchange source as changed (default_get or explicit set)
        self._changed.update(fields)

        result = self._model.onchange(
            self._onchange_values(),
            fields,
            self._view['onchange'],
        )
        if result.get('warning'):
            _logger.getChild('onchange').warn("%(title)s %(message)s" % result.get('warning'))
        values = result.get('value', {})
        # mark onchange output as changed
        self._changed.update(values.keys())
        self._values.update(
            (k, self._cleanup_onchange(
                self._view['fields'][k],
                v, self._values[k],
            ))
            for k, v in values.items()
            if k in self._view['fields']
        )

    def _onchange_values(self):
        return dict(self._values)

    def _cleanup_onchange(self, descr, value, current):
        if descr['type'] == 'many2one':
            if not value:
                return False
            # out of onchange, m2o are name-gotten
            return value[0]
        elif descr['type'] == 'one2many':
            # ignore o2ms nested in o2ms
            if not descr['views']:
                return []

            v = []
            # which view should this be???
            subfields = descr['views']['edition']['fields']
            for command in value:
                # TODO: get existing sub-values so we can pass them along?
                if command[0] in (0, 1):
                    v.append((command[0], command[1], {
                        k: self._cleanup_onchange(
                            subfields[k], v, None
                        )
                        for k, v in command[2].items()
                        if k in subfields
                    }))
                    # TODO: should reuse existing values if not 5?
            return v
        elif descr['type'] == 'many2many':
            # onchange result is a bunch of commands, normalize to single 6
            if current is None:
                ids = []
            else:
                ids = list(current[0][2])
            for command in value:
                if command[0] == 3:
                    ids.remove(command[1])
                elif command[0] == 4:
                    ids.append(command[1])
                elif command[0] == 5:
                    del ids[:]
                elif command[0] == 6:
                    ids[:] = command[2]
                else:
                    raise ValueError(
                        "Unsupported M2M command %d" % command[0])
            return [(6, 0, ids)]

        return value

class O2MForm(Form):
    # noinspection PyMissingConstructor
    def __init__(self, proxy, index=None):
        m = proxy._model
        object.__setattr__(self, '_proxy', proxy)
        object.__setattr__(self, '_index', index)

        object.__setattr__(self, '_env', m.env)
        object.__setattr__(self, '_model', m)

        # copy so we don't risk breaking it too much (?)
        fvg = dict(proxy._descr['views']['edition'])
        object.__setattr__(self, '_view', fvg)
        self._process_fvg(m, fvg)

        vals = dict.fromkeys(fvg['fields'], False)
        object.__setattr__(self, '_values', vals)
        object.__setattr__(self, '_changed', set())
        if index is None:
            self._init_from_defaults(m)
        else:
            self._values.update(proxy._records[index])

    def _onchange_values(self):
        values = super(O2MForm, self)._onchange_values()
        # computed o2m may not have a relation_field(?)
        descr = self._proxy._descr
        if 'relation_field' in descr:
            values[descr['relation_field']] = self._proxy._parent._values
        return values

    def save(self):
        proxy = self._proxy
        commands = proxy._parent._values[proxy._field]
        values = self._values_to_save()
        if self._index is None:
            commands.append((0, 0, values))
        else:
            (c, _, vs) = commands[proxy._command_index(self._index)]
            assert c in (0, 1)
            vs.update(values)

        # FIXME: should be called when performing on change => value needs to be serialised into parent every time?
        proxy._parent._perform_onchange([proxy._field])

class X2MProxy(object):
    _parent = None
    _field = None
    def _assert_editable(self):
        assert not self._parent._get_modifier(self._field, 'readonly'),\
            'field %s is not editable' % self._field

class O2MProxy(X2MProxy):
    """ O2MProxy()
    """
    def __init__(self, parent, field):
        self._parent = parent
        self._field = field
        # reify records to a list so they can be manipulated easily?
        self._records = []
        model = self._model
        fields = self._descr['views']['edition']['fields']
        for (command, rid, values) in self._parent._values[self._field]:
            if command == 0:
                self._records.append(values)
            elif command == 1:
                # read based on view info
                r = model.browse(rid)
                record = record_to_values(fields, r)
                record.update(values)
                self._records.append(record)
            elif command == 2:
                pass
            else:
                raise AssertionError("O2M proxy only supports commands 0, 1 and 2")

    @property
    def _model(self):
        model = self._parent._env[self._descr['relation']]
        ctx = self._parent._get_context(self._field)
        if ctx:
            model = model.with_context(**ctx)
        return model

    @property
    def _descr(self):
        return self._parent._view['fields'][self._field]

    def _command_index(self, for_record):
        """ Takes a record index and finds the corresponding record index
        (skips all 2s, basically)

        :param int for_record:
        """
        commands = self._parent._values[self._field]
        return next(
            cidx
            for ridx, cidx in enumerate(
                cidx for cidx, (c, _1, _2) in enumerate(commands)
                if c in (0, 1)
            )
            if ridx == for_record
        )

    def new(self):
        """ Returns a :class:`Form` for a new
        :class:`~odoo.fields.One2many` record, properly initialised.

        The form is created from the list view if editable, or the field's
        form view otherwise.

        :raises AssertionError: if the field is not editable
        """
        self._assert_editable()
        return O2MForm(self)

    def edit(self, index):
        """ Returns a :class:`Form` to edit the pre-existing
        :class:`~odoo.fields.One2many` record.

        The form is created from the list view if editable, or the field's
        form view otherwise.

        :raises AssertionError: if the field is not editable
        """
        self._assert_editable()
        return O2MForm(self, index)

    def remove(self, index):
        """ Removes the record at ``index`` from the parent form.

        :raises AssertionError: if the field is not editable
        """
        self._assert_editable()
        # remove reified record from local list & either remove 0 from
        # commands list or replace 1 (update) by 2 (remove)
        cidx = self._command_index(index)
        commands = self._parent._values[self._field]
        (command, rid, _) = commands[cidx]
        if command == 0:
            # record not saved yet -> just remove the command
            del commands[cidx]
        elif command == 1:
            # record already saved, replace by 2
            commands[cidx] = (2, rid, 0)
        else:
            raise AssertionError("Expected command 0 or 1, got %s" % commands[cidx])
        # remove reified record
        del self._records[index]
        self._parent._perform_onchange([self._field])

class M2MProxy(X2MProxy, collections.Sequence):
    """ M2MProxy()

    Behaves as a :class:`~collection.Sequence` of recordsets, can be
    indexed or sliced to get actual underlying recordsets.
    """
    def __init__(self, parent, field):
        self._parent = parent
        self._field = field

    def __getitem__(self, it):
        p = self._parent
        model = p._view['fields'][self._field]['relation']
        return p._env[model].browse(self._get_ids()[it])

    def __len__(self):
        return len(self._get_ids())

    def __iter__(self):
        return iter(self[:])

    def __contains__(self, record):
        relation_ = self._parent._view['fields'][self._field]['relation']
        assert isinstance(record, BaseModel)\
           and record._name == relation_

        return record.id in self._get_ids()


    def add(self, record):
        """ Adds ``record`` to the field, the record must already exist.

        The addition will only be finalized when the parent record is saved.
        """
        self._assert_editable()
        parent = self._parent
        relation_ = parent._view['fields'][self._field]['relation']
        assert isinstance(record, BaseModel) and record._name == relation_,\
            "trying to assign a '{}' object to a '{}' field".format(
                record._name,
                relation_,
            )
        self._get_ids().append(record.id)

        parent._perform_onchange([self._field])

    def _get_ids(self):
        return self._parent._values[self._field][0][2]

    def remove(self, id=None, index=None):
        """ Removes a record at a certain index or with a provided id from
        the field.
        """

        self._assert_editable()
        assert (id is None) ^ (index is None), \
            "can remove by either id or index"

        if id is None:
            # remove by index
            del self._get_ids()[index]
        else:
            self._get_ids().remove(id)

        self._parent._perform_onchange([self._field])

    def clear(self):
        """ Removes all existing records in the m2m
        """
        self._assert_editable()
        self._get_ids()[:] = []
        self._parent._perform_onchange([self._field])

def record_to_values(fields, record):
    r = {}
    for f, descr in fields.items():
        v = record[f]
        if descr['type'] == 'many2one':
            assert v._name == descr['relation']
            v = v.id
        elif descr['type'] == 'many2many':
            assert v._name == descr['relation']
            v = [(6, 0, v.ids)]
        elif descr['type'] == 'one2many':
            v = [(1, r.id, {}) for r in v]
        r[f] = v
    return r


def tagged(*tags):
    """
    A decorator to tag TestCase objects
    Tags are stored in a set that can be accessed from a 'test_tags' attribute
    A tag prefixed by '-' will remove the tag e.g. to remove the 'standard' tag
    By default, all Test classes from odoo.tests.common have a test_tags
    attribute that defaults to 'standard' and also the module technical name
    When using class inheritance, the tags are NOT inherited.
    """
    def tags_decorator(obj):
        include = {t for t in tags if not t.startswith('-')}
        exclude = {t[1:] for t in tags if t.startswith('-')}
        obj.test_tags = (getattr(obj, 'test_tags', set()) | include) - exclude
        return obj
    return tags_decorator


class TagsSelector(object):
    """ Test selector based on tags. """

    def __init__(self, spec):
        """ Parse the spec to determine tags to include and exclude. """
        clean_tags = {t.strip() for t in spec.split(',') if t.strip() != ''}
        self.exclude = {t[1:] for t in clean_tags if t.startswith('-')}
        self.include = {t.replace('+', '') for t in clean_tags if not t.startswith('-')}

    def check(self, arg):
        """ Return whether ``arg`` matches the specification: it must have at
            least one tag in ``self.include`` and none in ``self.exclude``.
        """
        # handle the case where the Test does not inherit from TransactionCase
        tags = getattr(arg, 'test_tags', set())
        inter_no_test = self.exclude.intersection(tags)
        if inter_no_test:
            _logger.debug("Test '%s' not selected because of following tag(s): '%s'", arg, inter_no_test)
            return False
        inter_to_test = self.include.intersection(tags)
        if not inter_to_test:
            _logger.debug("Test '%s' not selected because it was not tagged with '%s'", arg, self.include)
            return False
        return True
