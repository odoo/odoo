# -*- coding: utf-8 -*-
"""
The module :mod:`odoo.tests.common` provides unittest test cases and a few
helpers and classes to write tests.

"""
import base64
import collections
import importlib
import inspect
import itertools
import json
import logging
import operator
import os
import platform
import re
import requests
import shutil
import signal
import socket
import subprocess
import tempfile
import threading
import time
import unittest
import difflib
import werkzeug.urls
from contextlib import contextmanager
from datetime import datetime, date
from unittest.mock import patch

from decorator import decorator
from lxml import etree, html

from odoo.models import BaseModel
from odoo.osv.expression import normalize_domain, TRUE_LEAF, FALSE_LEAF
from odoo.tools import float_compare, single_email_re
from odoo.tools.misc import find_in_path
from odoo.tools.safe_eval import safe_eval

try:
    from itertools import zip_longest as izip_longest
except ImportError:
    from itertools import izip_longest

try:
    import websocket
except ImportError:
    # chrome headless tests will be skipped
    websocket = None

try:
    from xmlrpc import client as xmlrpclib
except ImportError:
    # pylint: disable=bad-python3-import
    import xmlrpclib

import odoo
import pprint
from odoo import api
from odoo.service import security



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

    .. deprecated:: 12.0

        ``at_install`` is now a flag, you can use :func:`tagged` to
        add/remove it, although ``tagged`` only works on test classes
    """
    return tagged('at_install' if flag else '-at_install')

def post_install(flag):
    """ Sets the post-install state of a test. The flag is a boolean
    specifying whether the test should or should not run after a set of
    module installations.

    By default, tests are *not* run after installation of all modules in the
    current installation set.

    .. deprecated:: 12.0

        ``post_install`` is now a flag, you can use :func:`tagged` to
        add/remove it, although ``tagged`` only works on test classes
    """
    return tagged('post_install' if flag else '-post_install')


def new_test_user(env, login='', groups='base.group_user', context=None, **kwargs):
    """ Helper function to create a new test user. It allows to quickly create
    users given its login and groups (being a comma separated list of xml ids).
    Kwargs are directly propagated to the create to further customize the
    created user.

    User creation uses a potentially customized environment using the context
    parameter allowing to specify a custom context. It can be used to force a
    specific behavior and/or simplify record creation. An example is to use
    mail-related context keys in mail tests to speedup record creation.

    Some specific fields are automatically filled to avoid issues

     * groups_id: it is filled using groups function parameter;
     * name: "login (groups)" by default as it is required;
     * email: it is either the login (if it is a valid email) or a generated
       string 'x.x@example.com' (x being the first login letter). This is due
       to email being required for most odoo operations;
    """
    if not login:
        raise ValueError('New users require at least a login')
    if not groups:
        raise ValueError('New users require at least user groups')
    if context is None:
        context = {}

    groups_id = [(6, 0, [env.ref(g).id for g in groups.split(',')])]
    create_values = dict(kwargs, login=login, groups_id=groups_id)
    if not create_values.get('name'):
        create_values['name'] = '%s (%s)' % (login, groups)
    if not create_values.get('email'):
        if single_email_re.match(login):
            create_values['email'] = login
        else:
            create_values['email'] = '%s.%s@example.com' % (login[0], login[0])

    return env['res.users'].with_context(**context).create(create_values)

# ------------------------------------------------------------
# Main classes
# ------------------------------------------------------------


class TreeCase(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        super(TreeCase, self).__init__(methodName)
        self.addTypeEqualityFunc(etree._Element, self.assertTreesEqual)
        self.addTypeEqualityFunc(html.HtmlElement, self.assertTreesEqual)

    def assertTreesEqual(self, n1, n2, msg=None):
        self.assertIsNotNone(n1, msg)
        self.assertIsNotNone(n2, msg)
        self.assertEqual(n1.tag, n2.tag, msg)
        # Because lxml.attrib is an ordereddict for which order is important
        # to equality, even though *we* don't care
        self.assertEqual(dict(n1.attrib), dict(n2.attrib), msg)

        self.assertEqual((n1.text or u'').strip(), (n2.text or u'').strip(), msg)
        self.assertEqual((n1.tail or u'').strip(), (n2.tail or u'').strip(), msg)

        for c1, c2 in izip_longest(n1, n2):
            self.assertTreesEqual(c1, c2, msg)


class MetaCase(type):
    """ Metaclass of test case classes to assign default 'test_tags':
        'standard', 'at_install' and the name of the module.
    """
    def __init__(cls, name, bases, attrs):
        super(MetaCase, cls).__init__(name, bases, attrs)
        # assign default test tags
        if cls.__module__.startswith('odoo.addons.'):
            cls.test_tags = {'standard', 'at_install'}
            cls.test_module = cls.__module__.split('.')[2]
            cls.test_class = cls.__name__


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
            if hasattr(self, 'env'):
                with self.env.clear_upon_failure():
                    yield cm
            else:
                yield cm

    def assertRaises(self, exception, func=None, *args, **kwargs):
        if func:
            with self._assertRaises(exception):
                func(*args, **kwargs)
        else:
            return self._assertRaises(exception)

    @contextmanager
    def assertQueryCount(self, default=0, flush=True, **counters):
        """ Context manager that counts queries. It may be invoked either with
            one value, or with a set of named arguments like ``login=value``::

                with self.assertQueryCount(42):
                    ...

                with self.assertQueryCount(admin=3, demo=5):
                    ...

            The second form is convenient when used with :func:`users`.
        """
        if self.warm:
            # mock random in order to avoid random bus gc
            with self.subTest(), patch('random.random', lambda: 1):
                login = self.env.user.login
                expected = counters.get(login, default)
                if flush:
                    self.env.user.flush()
                count0 = self.cr.sql_log_count
                yield
                if flush:
                    self.env.user.flush()
                count = self.cr.sql_log_count - count0
                if count != expected:
                    # add some info on caller to allow semi-automatic update of query count
                    frame, filename, linenum, funcname, lines, index = inspect.stack()[2]
                    if "/odoo/addons/" in filename:
                        filename = filename.rsplit("/odoo/addons/", 1)[1]
                    if count > expected:
                        msg = "Query count more than expected for user %s: %d > %d in %s at %s:%s"
                        self.fail(msg % (login, count, expected, funcname, filename, linenum))
                    else:
                        logger = logging.getLogger(type(self).__module__)
                        msg = "Query count less than expected for user %s: %d < %d in %s at %s:%s"
                        logger.info(msg, login, count, expected, funcname, filename, linenum)
        else:
            yield
            if flush:
                self.env.user.flush()

    def assertRecordValues(self, records, expected_values):
        ''' Compare a recordset with a list of dictionaries representing the expected results.
        This method performs a comparison element by element based on their index.
        Then, the order of the expected values is extremely important.

        Note that:
          - Comparison between falsy values is supported: False match with None.
          - Comparison between monetary field is also treated according the currency's rounding.
          - Comparison between x2many field is done by ids. Then, empty expected ids must be [].
          - Comparison between many2one field id done by id. Empty comparison can be done using any falsy value.

        :param records:               The records to compare.
        :param expected_values:       List of dicts expected to be exactly matched in records
        '''

        def _compare_candidate(record, candidate, field_names):
            ''' Compare all the values in `candidate` with a record.
            :param record:      record being compared
            :param candidate:   dict of values to compare
            :return:            A dictionary will encountered difference in values.
            '''
            diff = {}
            for field_name in field_names:
                record_value = record[field_name]
                field = record._fields[field_name]
                field_type = field.type
                if field_type == 'monetary':
                    # Compare monetary field.
                    currency_field_name = record._fields[field_name].currency_field
                    record_currency = record[currency_field_name]
                    if field_name not in candidate:
                        diff[field_name] = (record_value, None)
                    elif record_currency:
                        if record_currency.compare_amounts(candidate[field_name], record_value):
                            diff[field_name] = (record_value, record_currency.round(candidate[field_name]))
                    elif candidate[field_name] != record_value:
                        diff[field_name] = (record_value, candidate[field_name])
                elif field_type == 'float' and field.get_digits(record.env):
                    prec = field.get_digits(record.env)[1]
                    if float_compare(candidate[field_name], record_value, precision_digits=prec) != 0:
                        diff[field_name] = (record_value, candidate[field_name])
                elif field_type in ('one2many', 'many2many'):
                    # Compare x2many relational fields.
                    # Empty comparison must be an empty list to be True.
                    if field_name not in candidate:
                        diff[field_name] = (sorted(record_value.ids), None)
                    elif set(record_value.ids) != set(candidate[field_name]):
                        diff[field_name] = (sorted(record_value.ids), sorted(candidate[field_name]))
                elif field_type == 'many2one':
                    # Compare many2one relational fields.
                    # Every falsy value is allowed to compare with an empty record.
                    if field_name not in candidate:
                        diff[field_name] = (record_value.id, None)
                    elif (record_value or candidate[field_name]) and record_value.id != candidate[field_name]:
                        diff[field_name] = (record_value.id, candidate[field_name])
                else:
                    # Compare others fields if not both interpreted as falsy values.
                    if field_name not in candidate:
                        diff[field_name] = (record_value, None)
                    elif (candidate[field_name] or record_value) and record_value != candidate[field_name]:
                        diff[field_name] = (record_value, candidate[field_name])
            return diff

        # Compare records with candidates.
        different_values = []
        field_names = list(expected_values[0].keys())
        for index, record in enumerate(records):
            is_additional_record = index >= len(expected_values)
            candidate = {} if is_additional_record else expected_values[index]
            diff = _compare_candidate(record, candidate, field_names)
            if diff:
                different_values.append((index, 'additional_record' if is_additional_record else 'regular_diff', diff))
        for index in range(len(records), len(expected_values)):
            diff = {}
            for field_name in field_names:
                diff[field_name] = (None, expected_values[index][field_name])
            different_values.append((index, 'missing_record', diff))

        # Build error message.
        if not different_values:
            return

        errors = ['The records and expected_values do not match.']
        if len(records) != len(expected_values):
            errors.append('Wrong number of records to compare: %d records versus %d expected values.' % (len(records), len(expected_values)))

        for index, diff_type, diff in different_values:
            if diff_type == 'regular_diff':
                errors.append('\n==== Differences at index %s ====' % index)
                record_diff = ['%s:%s' % (k, v[0]) for k, v in diff.items()]
                candidate_diff = ['%s:%s' % (k, v[1]) for k, v in diff.items()]
                errors.append('\n'.join(difflib.unified_diff(record_diff, candidate_diff)))
            elif diff_type == 'additional_record':
                errors += [
                    '\n==== Additional record ====',
                    pprint.pformat(dict((k, v[0]) for k, v in diff.items())),
                ]
            elif diff_type == 'missing_record':
                errors += [
                    '\n==== Missing record ====',
                    pprint.pformat(dict((k, v[1]) for k, v in diff.items())),
                ]

        self.fail('\n'.join(errors))

    def shortDescription(self):
        return None

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
        self.addCleanup(self.registry.reset_changes)
        self.addCleanup(self.registry.clear_caches)

        #: current transaction's cursor
        self.cr = self.cursor()
        self.addCleanup(self.cr.close)

        #: :class:`~odoo.api.Environment` for the current test case
        self.env = api.Environment(self.cr, odoo.SUPERUSER_ID, {})
        self.addCleanup(self.env.reset)

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

    def setUp(self):
        super(SingleTransactionCase, self).setUp()
        self.env.user.flush()

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
        # restore environments after the test to avoid invoking flush() with an
        # invalid environment (inexistent user id) from another test
        envs = self.env.all.envs
        self.addCleanup(envs.update, list(envs))
        self.addCleanup(envs.clear)

    def tearDown(self):
        self.cr.execute('ROLLBACK TO SAVEPOINT test_%d' % self._savepoint_id)
        self.env.clear()
        self.registry.clear_caches()
        super(SavepointCase, self).tearDown()


class ChromeBrowserException(Exception):
    pass


class ChromeBrowser():
    """ Helper object to control a Chrome headless process. """

    def __init__(self, logger, window_size, test_class):
        self._logger = logger
        self.test_class = test_class
        if websocket is None:
            self._logger.warning("websocket-client module is not installed")
            raise unittest.SkipTest("websocket-client module is not installed")
        self.devtools_port = None
        self.ws_url = ''  # WebSocketUrl
        self.ws = None  # websocket
        self.request_id = 0
        self.user_data_dir = tempfile.mkdtemp(suffix='_chrome_odoo')
        self.chrome_process = None

        otc = odoo.tools.config
        self.screenshots_dir = os.path.join(otc['screenshots'], get_db_name(), 'screenshots')
        self.screencasts_dir = None
        if otc['screencasts']:
            if otc['screencasts'] in ('1', 'true', 't'):
                self.screencasts_dir = os.path.join(otc['screenshots'], get_db_name(), 'screencasts')
            else:
                self.screencasts_dir =os.path.join(otc['screencasts'], get_db_name(), 'screencasts')

        self.screencast_frames = []
        os.makedirs(self.screenshots_dir, exist_ok=True)

        self.window_size = window_size
        self._chrome_start()
        self._find_websocket()
        self._logger.info('Websocket url found: %s', self.ws_url)
        self._open_websocket()
        self._logger.info('Enable chrome headless console log notification')
        self._websocket_send('Runtime.enable')
        self._logger.info('Chrome headless enable page notifications')
        self._websocket_send('Page.enable')
        self.sigxcpu_handler = None
        if os.name == 'posix':
            self.sigxcpu_handler = signal.getsignal(signal.SIGXCPU)
            signal.signal(signal.SIGXCPU, self.signal_handler)

    def signal_handler(self, sig, frame):
        if sig == signal.SIGXCPU:
            _logger.info('CPU time limit reached, stopping Chrome and shutting down')
            self.stop()
            os._exit(0)

    def stop(self):
        if self.chrome_process is not None:
            self._logger.info("Closing chrome headless with pid %s", self.chrome_process.pid)
            self._websocket_send('Browser.close')
            if self.chrome_process.poll() is None:
                self._logger.info("Terminating chrome headless with pid %s", self.chrome_process.pid)
                self.chrome_process.terminate()
                self.chrome_process.wait()
        if self.user_data_dir and os.path.isdir(self.user_data_dir) and self.user_data_dir != '/':
            self._logger.info('Removing chrome user profile "%s"', self.user_data_dir)
            shutil.rmtree(self.user_data_dir, ignore_errors=True)
        # Restore previous signal handler
        if self.sigxcpu_handler and os.name == 'posix':
            signal.signal(signal.SIGXCPU, self.sigxcpu_handler)

    @property
    def executable(self):
        system = platform.system()
        if system == 'Linux':
            for bin_ in ['google-chrome', 'chromium', 'chromium-browser']:
                try:
                    return find_in_path(bin_)
                except IOError:
                    continue

        elif system == 'Darwin':
            bins = [
                '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                '/Applications/Chromium.app/Contents/MacOS/Chromium',
            ]
            for bin_ in bins:
                if os.path.exists(bin_):
                    return bin_

        elif system == 'Windows':
            # TODO: handle windows platform: https://stackoverflow.com/a/40674915
            pass

        raise unittest.SkipTest("Chrome executable not found")

    def _chrome_start(self):
        if self.chrome_process is not None:
            return
        with socket.socket() as s:
            s.bind(('localhost', 0))
            if hasattr(socket, 'SO_REUSEADDR'):
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            _, self.devtools_port = s.getsockname()

        switches = {
            '--headless': '',
            '--enable-logging': 'stderr',
            '--no-default-browser-check': '',
            '--no-first-run': '',
            '--disable-extensions': '',
            '--disable-background-networking' : '',
            '--disable-background-timer-throttling' : '',
            '--disable-backgrounding-occluded-windows': '',
            '--disable-renderer-backgrounding' : '',
            '--disable-breakpad': '',
            '--disable-client-side-phishing-detection': '',
            '--disable-crash-reporter': '',
            '--disable-default-apps': '',
            '--disable-dev-shm-usage': '',
            '--disable-device-discovery-notifications': '',
            '--disable-namespace-sandbox': '',
            '--user-data-dir': self.user_data_dir,
            '--disable-translate': '',
            # required for tours that use Youtube autoplay conditions (namely website_slides' "course_tour")
            '--autoplay-policy': 'no-user-gesture-required',
            '--window-size': self.window_size,
            '--remote-debugging-address': HOST,
            '--remote-debugging-port': str(self.devtools_port),
            '--no-sandbox': '',
        }
        cmd = [self.executable]
        cmd += ['%s=%s' % (k, v) if v else k for k, v in switches.items()]
        url = 'about:blank'
        cmd.append(url)
        self._logger.info('chrome_run executing %s', ' '.join(cmd))
        try:
            self.chrome_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            raise unittest.SkipTest("%s not found" % cmd[0])
        self._logger.info('Chrome pid: %s', self.chrome_process.pid)

    def _find_websocket(self):
        version = self._json_command('version')
        self._logger.info('Browser version: %s', version['Browser'])
        try:
            infos = self._json_command('')[0]  # Infos about the first tab
        except IndexError:
            self._logger.warning('No tab found in Chrome')
            self.stop()
            raise unittest.SkipTest('No tab found in Chrome')
        self.ws_url = infos['webSocketDebuggerUrl']
        self._logger.info('Chrome headless temporary user profile dir: %s', self.user_data_dir)

    def _json_command(self, command, timeout=3):
        """
        Inspect dev tools with get
        Available commands:
            '' : return list of tabs with their id
            list (or json/): list tabs
            new : open a new tab
            activate/ + an id: activate a tab
            close/ + and id: close a tab
            version : get chrome and dev tools version
            protocol : get the full protocol
        """
        command = os.path.join('json', command).strip('/')
        url = werkzeug.urls.url_join('http://%s:%s/' % (HOST, self.devtools_port), command)
        self._logger.info("Issuing json command %s", url)
        delay = 0.1
        tries = 0
        failure_info = None
        while tries * delay < timeout:
            if self.chrome_process.poll() is not None:
                self._logger.error('Chrome crashed at startup with return code', self.chrome_process.returncode)
                break
            try:
                r = requests.get(url, timeout=3)
                if r.ok:
                    self._logger.info("Json command result in %s", tries * delay)
                    return r.json()
                return {'status_code': r.status_code}
            except requests.ConnectionError as e:
                failure_info = str(e)
                time.sleep(delay)
                tries+=1
            except requests.exceptions.ReadTimeout as e:
                failure_info = str(e)
                break
        self._logger.error('Could not connect to chrome debugger after %s tries, %ss' % (tries, delay))
        if failure_info:
            self._logger.info(failure_info)
        raise unittest.SkipTest("Cannot connect to chrome headless")

    def _open_websocket(self):
        self.ws = websocket.create_connection(self.ws_url)
        if self.ws.getstatus() != 101:
            raise unittest.SkipTest("Cannot connect to chrome dev tools")
        self.ws.settimeout(0.01)

    def _websocket_send(self, method, params=None):
        """
        send chrome devtools protocol commands through websocket
        """
        sent_id = self.request_id
        payload = {
            'method': method,
            'id':  sent_id,
        }
        if params:
            payload.update({'params': params})
        self.ws.send(json.dumps(payload))
        self.request_id += 1
        return sent_id

    def _get_message(self, raise_log_error=True):
        """
        :param bool raise_log_error:

            by default, error logging messages reported by the browser are
            converted to exception in order to fail the current test.

            This is undersirable for *some* message loops, mostly when waiting
            for a response to a command we've sent (wait_id): we do want to
            properly handle exceptions and to forward the browser logs in order
            to avoid losing information, but e.g. if the client generates two
            console.error() we don't want the first call to take_screenshot to
            trip up on the second console.error message and throw a second
            exception. At the same time we don't want to *lose* the second
            console.error as it might provide useful information.
        """
        try:
            res = json.loads(self.ws.recv())
        except websocket.WebSocketTimeoutException:
            res = {}

        if res.get('method') == 'Runtime.consoleAPICalled':
            params = res['params']

            # console formatting differs somewhat from Python's, if args[0] has
            # format modifiers that many of args[1:] get formatted in, missing
            # args are replaced by empty strings and extra args are concatenated
            # (space-separated)
            #
            # current version modifies the args in place which could and should
            # probably be improved
            arg0, args = '', []
            if params.get('args'):
                arg0 = str(self._from_remoteobject(params['args'][0]))
                args = params['args'][1:]
            formatted = [re.sub(r'%[%sdfoOc]', self.console_formatter(args), arg0)]
            # formatter consumes args it uses, leaves unformatted args untouched
            formatted.extend(str(self._from_remoteobject(arg)) for arg in args)
            message = ' '.join(formatted)
            stack = ''.join(self._format_stack(params))
            if stack:
                message += '\n' + stack

            log_type = params['type']
            if raise_log_error and log_type == 'error':
                self.take_screenshot()
                self._save_screencast()
                raise ChromeBrowserException(message)

            self._logger.getChild('browser').log(
                self._TO_LEVEL.get(log_type, logging.INFO),
                "%s", message # might still have %<x> characters
            )
            res['success'] = 'test successful' in message

        if res.get('method') == 'Runtime.exceptionThrown':
            exception_details = res['params']['exceptionDetails']
            descr = exception_details.get('exception', {}).get('description')
            self.take_screenshot()
            self._save_screencast()
            raise ChromeBrowserException(descr or pprint.pformat(exception_details))

        return res

    _TO_LEVEL = {
        'debug': logging.DEBUG,
        'log': logging.INFO,
        'info': logging.INFO,
        'warning': logging.INFO, # logging.WARNING,
        'error': logging.ERROR,
        # TODO: what do with
        # dir, dirxml, table, trace, clear, startGroup, startGroupCollapsed,
        # endGroup, assert, profile, profileEnd, count, timeEnd
    }

    def _websocket_wait_id(self, awaited_id, timeout=10):
        """
        blocking wait for a certain id in a response
        warning other messages are discarded
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            res = self._get_message(raise_log_error=False)
            if res.get('id') == awaited_id:
                return res
        self._logger.info('timeout exceeded while waiting for id : %d', awaited_id)
        return {}

    def _websocket_wait_event(self, method, params=None, timeout=10):
        """
        blocking wait for a particular event method and eventually a dict of params
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            res = self._get_message()
            if res.get('method', '') == method:
                if params:
                    if set(params).issubset(set(res.get('params', {}))):
                        return res
                else:
                    return res
            elif res:
                self._logger.debug('chrome devtools protocol event: %s', res)
        self._logger.info('timeout exceeded while waiting for : %s', method)

    def take_screenshot(self, prefix='sc_', suffix=None):
        if suffix is None:
            suffix = '_%s' % self.test_class
        ss_id = self._websocket_send('Page.captureScreenshot')
        self._logger.info('Asked for screenshot (id: %s)', ss_id)
        res = self._websocket_wait_id(ss_id)
        base_png = res.get('result', {}).get('data')
        if not base_png:
            self._logger.warning("Couldn't capture screenshot: expected image data, got %s", res)
            return

        decoded = base64.b64decode(base_png, validate=True)
        fname = '{}{:%Y%m%d_%H%M%S_%f}{}.png'.format(prefix, datetime.now(), suffix)
        full_path = os.path.join(self.screenshots_dir, fname)
        with open(full_path, 'wb') as f:
            f.write(decoded)
        self._logger.log(25, 'Screenshot in: %s', full_path)

    def _save_screencast(self, prefix='failed'):
        # could be encododed with something like that
        #  ffmpeg -framerate 3 -i frame_%05d.png  output.mp4
        if not self.screencast_frames:
            self._logger.debug('No screencast frames to encode')
            return None

        for f in self.screencast_frames:
            with open(f['file_path'], 'rb') as b64_file:
                frame = base64.decodebytes(b64_file.read())
            os.unlink(f['file_path'])
            f['file_path'] = f['file_path'].replace('.b64', '.png')
            with open(f['file_path'], 'wb') as png_file:
                png_file.write(frame)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        fname = '%s_screencast_%s.mp4' % (prefix, timestamp)
        outfile = os.path.join(self.screencasts_dir, fname)
        
        try:
            ffmpeg_path = find_in_path('ffmpeg')
        except IOError:
            ffmpeg_path = None

        if ffmpeg_path:
            framerate = int(len(self.screencast_frames) / (self.screencast_frames[-1].get('timestamp') - self.screencast_frames[0].get('timestamp')))
            r = subprocess.run([ffmpeg_path, '-framerate', str(framerate), '-i', '%s/frame_%%05d.png' % self.screencasts_dir, outfile])
            self._logger.log(25, 'Screencast in: %s', outfile)
        else:
            outfile = outfile.strip('.mp4')
            shutil.move(self.screencasts_frames_dir, outfile)
            self._logger.log(25, 'Screencast frames in: %s', outfile)

    def start_screencast(self):
        if self.screencasts_dir:
            os.makedirs(self.screencasts_dir, exist_ok=True)
            self.screencasts_frames_dir = os.path.join(self.screencasts_dir, 'frames')
            os.makedirs(self.screencasts_frames_dir, exist_ok=True)
        self._websocket_send('Page.startScreencast', params={'maxWidth': 1024, 'maxHeight': 576})

    def set_cookie(self, name, value, path, domain):
        params = {'name': name, 'value': value, 'path': path, 'domain': domain}
        _id = self._websocket_send('Network.setCookie', params=params)
        return self._websocket_wait_id(_id)

    def delete_cookie(self, name, **kwargs):
        params = {kw:kwargs[kw] for kw in kwargs if kw in ['url', 'domain', 'path']}
        params.update({'name': name})
        _id = self._websocket_send('Network.deleteCookies', params=params)
        return self._websocket_wait_id(_id)

    def _wait_ready(self, ready_code, timeout=60):
        self._logger.info('Evaluate ready code "%s"', ready_code)
        awaited_result = {'result': {'type': 'boolean', 'value': True}}
        ready_id = self._websocket_send('Runtime.evaluate', params={'expression': ready_code})
        last_bad_res = ''
        start_time = time.time()
        tdiff = time.time() - start_time
        has_exceeded = False
        while tdiff < timeout:
            res = self._get_message()

            if res.get('id') == ready_id:
                if res.get('result') == awaited_result:
                    if has_exceeded:
                        self._logger.info('The ready code tooks too much time : %s', tdiff)
                    return True
                else:
                    last_bad_res = res
                    ready_id = self._websocket_send('Runtime.evaluate', params={'expression': ready_code})
            tdiff = time.time() - start_time
            if tdiff >= 2 and not has_exceeded:
                has_exceeded = True

        self.take_screenshot(prefix='sc_failed_ready_')
        self._logger.info('Ready code last try result: %s', last_bad_res or res)
        return False

    def _wait_code_ok(self, code, timeout):
        self._logger.info('Evaluate test code "%s"', code)
        code_id = self._websocket_send('Runtime.evaluate', params={'expression': code})
        start_time = time.time()
        logged_error = False
        nb_frame = 0
        while time.time() - start_time < timeout:
            res = self._get_message()

            if res.get('id', -1) == code_id:
                self._logger.info('Code start result: %s', res)
                if res.get('result', {}).get('result').get('subtype', '') == 'error':
                    raise ChromeBrowserException("Running code returned an error: %s" % res)
            elif res.get('success'):
                return True
            elif res.get('method') == 'Page.screencastFrame':
                session_id = res.get('params').get('sessionId')
                self._websocket_send('Page.screencastFrameAck', params={'sessionId': int(session_id)})
                outfile = os.path.join(self.screencasts_frames_dir, 'frame_%05d.b64' % nb_frame)
                frame = res.get('params')
                with open(outfile, 'w') as f:
                    f.write(frame.get('data'))
                    nb_frame += 1
                    self.screencast_frames.append({
                        'file_path': outfile,
                        'timestamp': frame.get('metadata').get('timestamp')
                    })
            elif res:
                self._logger.debug('chrome devtools protocol event: %s', res)
        self.take_screenshot()
        raise ChromeBrowserException('Script timeout exceeded : %s' % (time.time() - start_time))


    def navigate_to(self, url, wait_stop=False):
        self._logger.info('Navigating to: "%s"', url)
        nav_id = self._websocket_send('Page.navigate', params={'url': url})
        nav_result = self._websocket_wait_id(nav_id)
        self._logger.info("Navigation result: %s", nav_result)
        frame_id = nav_result.get('result', {}).get('frameId', '')
        if wait_stop and frame_id:
            self._logger.info('Waiting for frame "%s" to stop loading', frame_id)
            self._websocket_wait_event('Page.frameStoppedLoading', params={'frameId': frame_id})

    def clear(self):
        self._websocket_send('Page.stopScreencast')
        if self.screencasts_dir and os.path.isdir(self.screencasts_frames_dir):
            shutil.rmtree(self.screencasts_frames_dir)
        self.screencast_frames = []
        sl_id = self._websocket_send('Page.stopLoading')
        self._websocket_wait_id(sl_id)
        self._logger.info('Deleting cookies and clearing local storage')
        dc_id = self._websocket_send('Network.clearBrowserCache')
        self._websocket_wait_id(dc_id)
        dc_id = self._websocket_send('Network.clearBrowserCookies')
        self._websocket_wait_id(dc_id)
        cl_id = self._websocket_send('Runtime.evaluate', params={'expression': 'localStorage.clear()'})
        self._websocket_wait_id(cl_id)
        self.navigate_to('about:blank', wait_stop=True)

    def _from_remoteobject(self, arg):
        """ attempts to make a CDT RemoteObject comprehensible
        """
        objtype = arg['type']
        klass = arg.get('className', '')
        subtype = arg.get('subtype')
        if objtype == 'undefined':
            # the undefined remoteobject is literally just {type: undefined}...
            return 'undefined'
        elif objtype != 'object' or subtype:
            # value is the json representation for json object
            # otherwise fallback on the description which is "a string
            # representation of the object" e.g. the traceback for errors, the
            # source for functions, ... finally fallback on the entire arg mess
            return arg.get('value', arg.get('description', arg))

        # all that's left is type=object, subtype=None aka custom or
        # non-standard objects, print as TypeName(param=val, ...), sadly because
        # of the way Odoo widgets are created they all appear as Class(...)
        return '%s(%s)' % (
            klass or objtype,
            ', '.join(
                '%s=%s' % (p['name'], repr(p['value']) if p['type'] == 'string' else p['value'])
                for p in arg.get('preview', {}).get('properties', [])
                if p.get('value') is not None
            )
        )

    LINE_PATTERN = '\tat %(functionName)s (%(url)s:%(lineNumber)d:%(columnNumber)d)\n'
    def _format_stack(self, logrecord):
        if logrecord['type'] not in ['trace']:
            return

        trace = logrecord.get('stackTrace')
        while trace:
            for f in trace['callFrames']:
                yield self.LINE_PATTERN % f
            trace = trace.get('parent')

    def console_formatter(self, args):
        """ Formats similarly to the console API:

        * if there are no args, don't format (return string as-is)
        * %% -> %
        * %c -> replace by styling directives (ignore for us)
        * other known formatters -> replace by corresponding argument
        * leftover known formatters (args exhausted) -> replace by empty string
        * unknown formatters -> return as-is
        """
        if not args:
            return lambda m: m[0]

        def replacer(m):
            fmt = m[0][1]
            if fmt == '%':
                return '%'
            if fmt in 'sdfoOc':
                if not args:
                    return ''
                repl = args.pop(0)
                if fmt == 'c':
                    return ''
                return str(self._from_remoteobject(repl))
            return m[0]
        return replacer

class HttpCase(TransactionCase):
    """ Transactional HTTP TestCase with url_open and Chrome headless helpers.
    """
    registry_test_mode = True
    browser = None
    browser_size = '1366x768'

    def __init__(self, methodName='runTest'):
        super(HttpCase, self).__init__(methodName)
        # v8 api with correct xmlrpc exception handling.
        self.xmlrpc_url = url_8 = 'http://%s:%d/xmlrpc/2/' % (HOST, PORT)
        self.xmlrpc_common = xmlrpclib.ServerProxy(url_8 + 'common')
        self.xmlrpc_db = xmlrpclib.ServerProxy(url_8 + 'db')
        self.xmlrpc_object = xmlrpclib.ServerProxy(url_8 + 'object')
        cls = type(self)
        cls._logger = logging.getLogger('%s.%s' % (cls.__module__, cls.__name__))

    @classmethod
    def start_browser(cls):
        # start browser on demand
        if cls.browser is None:
            cls.browser = ChromeBrowser(cls._logger, cls.browser_size, cls.__name__)

    @classmethod
    def terminate_browser(cls):
        if cls.browser:
            cls.browser.stop()
            cls.browser = None

    @classmethod
    def tearDownClass(cls):
        cls.terminate_browser()
        super(HttpCase, cls).tearDownClass()

    def setUp(self):
        super(HttpCase, self).setUp()

        if self.registry_test_mode:
            self.registry.enter_test_mode(self.cr)
            self.addCleanup(self.registry.leave_test_mode)
        # setup a magic session_id that will be rollbacked
        self.session = odoo.http.root.session_store.new()
        self.session_id = self.session.sid
        self.session.db = get_db_name()
        odoo.http.root.session_store.save(self.session)
        # setup an url opener helper
        self.opener = requests.Session()
        self.opener.cookies['session_id'] = self.session_id

    def url_open(self, url, data=None, files=None, timeout=10, headers=None):
        self.env['base'].flush()
        if url.startswith('/'):
            url = "http://%s:%s%s" % (HOST, PORT, url)
        if data or files:
            return self.opener.post(url, data=data, files=files, timeout=timeout, headers=headers)
        return self.opener.get(url, timeout=timeout, headers=headers)

    def _wait_remaining_requests(self, timeout=10):

        def get_http_request_threads():
            return [t for t in threading.enumerate() if t.name.startswith('odoo.service.http.request.')]

        start_time = time.time()
        request_threads = get_http_request_threads()
        self._logger.info('waiting for threads: %s', request_threads)

        for thread in request_threads:
            thread.join(timeout - (time.time() - start_time))

        request_threads = get_http_request_threads()
        for thread in request_threads:
            self._logger.info("Stop waiting for thread %s handling request for url %s",
                                    thread.name, getattr(thread, 'url', '<UNKNOWN>'))

        if request_threads:
            self._logger.info('remaining requests')
            odoo.tools.misc.dumpstacks()

    def authenticate(self, user, password):
        # stay non-authenticated
        if user is None:
            if self.session:
                odoo.http.root.session_store.delete(self.session)
            self.browser.delete_cookie('session_id', domain=HOST)
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
        session.session_token = uid and security.compute_session_token(session, env)
        session.context = dict(env['res.users'].context_get() or {})
        session.context['uid'] = uid
        session._fix_lang(session.context)

        odoo.http.root.session_store.save(session)
        if self.browser:
            self._logger.info('Setting session cookie in browser')
            self.browser.set_cookie('session_id', self.session_id, '/', HOST)

    def browser_js(self, url_path, code, ready='', login=None, timeout=60, **kw):
        """ Test js code running in the browser
        - optionnally log as 'login'
        - load page given by url_path
        - wait for ready object to be available
        - eval(code) inside the page

        To signal success test do: console.log('test successful')
        To signal test failure raise an exception or call console.error
        """
        # increase timeout if coverage is running
        if any(f.filename.endswith('/coverage/execfile.py') for f in inspect.stack()  if f.filename):
            timeout = timeout * 1.5

        self.start_browser()

        try:
            self.authenticate(login, login)
            base_url = "http://%s:%s" % (HOST, PORT)
            ICP = self.env['ir.config_parameter']
            ICP.set_param('web.base.url', base_url)
            # flush updates to the database before launching the client side,
            # otherwise they simply won't be visible
            ICP.flush()
            url = "%s%s" % (base_url, url_path or '/')
            self._logger.info('Open "%s" in browser', url)

            if self.browser.screencasts_dir:
                self._logger.info('Starting screencast')
                self.browser.start_screencast()
            self.browser.navigate_to(url, wait_stop=not bool(ready))

            # Needed because tests like test01.js (qunit tests) are passing a ready
            # code = ""
            ready = ready or "document.readyState === 'complete'"
            self.assertTrue(self.browser._wait_ready(ready), 'The ready "%s" code was always falsy' % ready)

            error = False
            try:
                self.browser._wait_code_ok(code, timeout)
            except ChromeBrowserException as chrome_browser_exception:
                error = chrome_browser_exception
            if error:  # dont keep initial traceback, keep that outside of except
                if code:
                    message = 'The test code "%s" failed' % code
                else:
                    message = "Some js test failed"
                self.fail('%s\n%s' % (message, error))

        finally:
            # clear browser to make it stop sending requests, in case we call
            # the method several times in a test method
            self.browser.delete_cookie('session_id', domain=HOST)
            self.browser.clear()
            self._wait_remaining_requests()

    def start_tour(self, url_path, tour_name, step_delay=None, **kwargs):
        """Wrapper for `browser_js` to start the given `tour_name` with the
        optional delay between steps `step_delay`. Other arguments from
        `browser_js` can be passed as keyword arguments."""
        step_delay = ', %s' % step_delay if step_delay else ''
        code = kwargs.pop('code', "odoo.startTour('%s'%s)" % (tour_name, step_delay))
        ready = kwargs.pop('ready', "odoo.__DEBUG__.services['web_tour.tour'].tours.%s.ready" % tour_name)
        res = self.browser_js(url_path=url_path, code=code, ready=ready, **kwargs)
        # some tests read the result after the tour, and as  the tour does not
        # use this environment's cache, invalidate it to fetch the data from the
        # database
        self.env.cache.invalidate()
        return res

    phantom_js = browser_js


def users(*logins):
    """ Decorate a method to execute it once for each given user. """
    @decorator
    def wrapper(func, *args, **kwargs):
        self = args[0]
        old_uid = self.uid
        try:
            # retrieve users
            Users = self.env['res.users'].with_context(active_test=False)
            user_id = {
                user.login: user.id
                for user in Users.search([('login', 'in', list(logins))])
            }
            for login in logins:
                with self.subTest(login=login):
                    # switch user and execute func
                    self.uid = user_id[login]
                    func(*args, **kwargs)
                # Invalidate the cache between subtests, in order to not reuse
                # the former user's cache (`test_read_mail`, `test_write_mail`)
                self.env.cache.invalidate()
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
    self.env['base'].flush()
    self.env.cache.invalidate()
    # run once to warm up the caches
    self.warm = False
    self.cr.execute('SAVEPOINT test_warmup')
    func(*args, **kwargs)
    self.env['base'].flush()
    # run once for real
    self.cr.execute('ROLLBACK TO SAVEPOINT test_warmup')
    self.env.cache.invalidate()
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
ref_re = re.compile(r"""
# first match 'form_view_ref' key, backrefs are used to handle single or
# double quoting of the value
(['"])(?P<view_type>\w+_view_ref)\1
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
\3
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
        elif isinstance(view, str):
            view_id = env.ref(view).id
        else:
            view_id = view or False
        fvg = recordp.fields_view_get(view_id, 'form')
        fvg['tree'] = etree.fromstring(fvg['arch'])

        object.__setattr__(self, '_view', fvg)

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

    def _o2m_set_edition_view(self, descr, node, level):
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
        submodel = self._env[descr['relation']]
        views = submodel.with_context(**refs) \
            .load_views([(False, 'tree'), (False, 'form')])['fields_views']
        # embedded views should take the priority on externals
        views.update(descr['views'])
        # re-set all resolved views on the descriptor
        descr['views'] = views
        # if the default view is a kanban or a non-editable list, the
        # "edition controller" is the form view
        edition = views['form']
        edition['tree'] = etree.fromstring(edition['arch'])
        if default_view == 'tree':
            subarch = etree.fromstring(views['tree']['arch'])
            if subarch.get('editable'):
                edition = views['tree']
                edition['tree'] = subarch

        # don't recursively process o2ms in o2ms
        self._process_fvg(submodel, edition, level=level-1)
        descr['views']['edition'] = edition

    def __str__(self):
        return "<%s %s(%s)>" % (
            type(self).__name__,
            self._model._name,
            self._values.get('id', False),
        )

    def _process_fvg(self, model, fvg, level=2):
        """ Post-processes to augment the fields_view_get with:

        * an id field (may not be present if not in the view but needed)
        * pre-processed modifiers (map of modifier name to json-loaded domain)
        * pre-processed onchanges list
        """
        fvg['fields'].setdefault('id', {'type': 'id'})
        # pre-resolve modifiers & bind to arch toplevel
        modifiers = fvg['modifiers'] = {'id': {'required': False, 'readonly': True}}
        contexts = fvg['contexts'] = {}
        order = fvg['fields_ordered'] = []
        for f in fvg['tree'].xpath('//field[not(ancestor::field)]'):
            fname = f.get('name')
            order.append(fname)

            modifiers[fname] = {
                modifier: domain if isinstance(domain, bool) else normalize_domain(domain)
                for modifier, domain in json.loads(f.get('modifiers', '{}')).items()
            }
            ctx = f.get('context')
            if ctx:
                contexts[fname] = ctx

            descr = fvg['fields'].get(fname) or {'type': None}
            # FIXME: better widgets support
            # NOTE: selection breaks because of m2o widget=selection
            if f.get('widget') in ['many2many']:
                descr['type'] = f.get('widget')
            if level and descr['type'] == 'one2many':
                self._o2m_set_edition_view(descr, f, level)

        fvg['onchange'] = model._onchange_spec(fvg)

    def _init_from_defaults(self, model):
        vals = self._values
        fields = self._view['fields']
        def cleanup(k, v):
            if fields[k]['type'] == 'one2many':
                return [
                    # use None as "empty" value for UPDATE instead of {}
                    (1, c[1], None) if c[0] == 1 and not c[2] else c
                    for c in v
                    if c[0] != 6 # o2m default gets a (6) at the start, nonsensical
                ]
            elif fields[k]['type'] == 'datetime' and isinstance(v, datetime):
                return odoo.fields.Datetime.to_string(v)
            elif fields[k]['type'] == 'date' and isinstance(v, date):
                return odoo.fields.Datetime.to_string(v)

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
                elif type_ in ('integer', 'float'):
                    vals[k] = 0

        # on creation, every field is considered changed by the client
        # apparently
        # and fields should be sent in view order, not whatever fields_view_get['fields'].keys() is
        self._perform_onchange(self._view['fields_ordered'])

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

    def _get_modifier(self, field, modifier, default=False, modmap=None, vals=None):
        d = (modmap or self._view['modifiers'])[field].get(modifier, default)
        if isinstance(d, bool):
            return d

        if vals is None:
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
            elif isinstance(it, tuple):
                if it == TRUE_LEAF:
                    stack.append(True)
                    continue
                elif it == FALSE_LEAF:
                    stack.append(False)
                    continue
                f, op, val = it
                # hack-ish handling of parent.<field> modifiers
                f, n = re.subn(r'^parent\.', '', f, 1)
                if n:
                    field_val = vals['•parent•'][f]
                else:
                    field_val = vals[f]
                    # apparent artefact of JS data representation: m2m field
                    # values are assimilated to lists of ids?
                    # FIXME: SSF should do that internally, but the requirement
                    #        of recursively post-processing to generate lists of
                    #        commands on save (e.g. m2m inside an o2m) means the
                    #        data model needs proper redesign
                    # we're looking up the "current view" so bits might be
                    # missing when processing o2ms in the parent (see
                    # values_to_save:1450 or so)
                    f_ = self._view['fields'].get(f, {'type': None})
                    if f_['type'] == 'many2many':
                        # field value should be [(6, _, ids)], we want just the ids
                        field_val = field_val[0][2] if field_val else []

                stack.append(self._OPS[op](field_val, val))
            else:
                raise ValueError("Unknown domain element %s" % [it])
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

        ctx = dict(self._values_to_save(all_fields=True))
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
        self._values.update(
            record_to_values(self._view['fields'], r)
        )
        self._changed.clear()
        self._model.flush()
        self._model.invalidate_cache()
        return r

    def _values_to_save(self, all_fields=False):
        """ Validates values and returns only fields modified since
        load/save

        :param bool all_fields: if False (the default), checks for required
                                fields and only save fields which are changed
                                and not readonly
        """
        values = {}
        fields = self._view['fields']
        for f in fields:
            descr = fields[f]
            v = self._values[f]
            # note: maybe `invisible` should not skip `required` if model attribute
            if not all_fields and self._get_modifier(f, 'required') and not (descr['type'] == 'boolean' or self._get_modifier(f, 'invisible')):
                assert v is not False, "{} is a required field".format(f)
            # skip unmodified fields unless all_fields (also always ignore id)
            if f == 'id' or not (all_fields or f in self._changed):
                continue

            if self._get_modifier(f, 'readonly'):
                node = _get_node(self._view, f)
                if not (all_fields or node.get('force_save')):
                    continue

            if descr['type'] == 'one2many':
                view = descr['views']['edition']
                modifiers = view['modifiers']
                oldvals = v
                v = []

                nodes = {
                    n.get('name'): n
                    for n in view['tree'].iter('field')
                }
                nodes['id'] = etree.Element('field', attrib={'name': 'id'})

                for (c, rid, vs) in oldvals:
                    if c in (0, 1):
                        vs = vs or {}
                        if all_fields:
                            items = list(vs.items())
                        else:
                            items = list(getattr(vs, 'changed_items', vs.items)())
                        fields_ = view['fields']
                        missing = fields_.keys() - vs.keys()
                        if missing: # FIXME: maaaybe this should be done at the start?
                            Model = self._env[descr['relation']]
                            if c == 0:
                                vs.update(dict.fromkeys(missing, False))
                                vs.update(
                                    (k, _cleanup_from_default(fields_[k], v))
                                    for k, v in Model.default_get(list(missing)).items()
                                )
                            else:
                                vs.update(record_to_values(
                                    {k: v for k, v in fields_.items() if k not in vs},
                                    Model.browse(rid)
                                ))
                        context = dict(vs)
                        context.setdefault('id', False)
                        context['•parent•'] = self._values
                        vs = {
                            k: v for k, v in items
                            if all_fields or nodes[k].get('force_save') or not self._get_modifier(k, 'readonly', modmap=modifiers, vals=context)
                        }
                    v.append((c, rid, vs))

            values[f] = v
        return values

    def _perform_onchange(self, fields):
        assert isinstance(fields, list)
        # marks any onchange source as changed
        self._changed.update(fields)

        # skip calling onchange() if there's no trigger on any of the changed
        # fields
        spec = self._view['onchange']
        if not any(spec[f] for f in fields):
            return

        record = self._model.browse(self._values.get('id'))
        result = record.onchange(self._onchange_values(), fields, spec)
        self._model.flush()
        self._model.invalidate_cache()
        if result.get('warning'):
            _logger.getChild('onchange').warning("%(title)s %(message)s" % result.get('warning'))
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
        f = self._view['fields']
        values = {}
        for k, v in self._values.items():
            if f[k]['type'] == 'one2many':
                it = values[k] = []
                for (c, rid, vs) in v:
                    if c == 1 and not vs:
                        # web client sends a 4 for unmodified o2m rows
                        it.append((4, rid, False))
                    elif c == 1 and isinstance(vs, UpdateDict):
                        it.append((1, rid, dict(vs.changed_items())))
                    else:
                        it.append((c, rid, vs))
            else:
                values[k] = v
        return values

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

            if current is None:
                current = []
            v = []
            c = {t[1] for t in current if t[0] in (1, 2)}
            current_values = {c[1]: c[2] for c in current if c[0] == 1}
            # which view should this be???
            subfields = descr['views']['edition']['fields']
            # TODO: simplistic, unlikely to work if e.g. there's a 5 inbetween other commands
            for command in value:
                if command[0] == 0:
                    v.append((0, 0, {
                        k: self._cleanup_onchange(subfields[k], v, None)
                        for k, v in command[2].items()
                        if k in subfields
                    }))
                elif command[0] == 1:
                    record_id = command[1]
                    c.discard(record_id)
                    stored = current_values.get(record_id)
                    if stored is None:
                        record = self._env[descr['relation']].browse(record_id)
                        stored = UpdateDict(record_to_values(subfields, record))

                    updates = (
                        (k, self._cleanup_onchange(subfields[k], v, None))
                        for k, v in command[2].items()
                        if k in subfields
                    )
                    for field, value in updates:
                        # if there are values from the onchange which differ
                        # from current values, update & mark field as changed
                        if stored.get(field, value) != value:
                            stored._changed.add(field)
                            stored[field] = value

                    v.append((1, record_id, stored))
                elif command[0] == 2:
                    c.discard(command[1])
                    v.append((2, command[1], False))
                elif command[0] == 4:
                    c.discard(command[1])
                    v.append((1, command[1], None))
                elif command[0] == 5:
                    v = []
            # explicitly mark all non-relinked (or modified) records as deleted
            for id_ in c: v.append((2, id_, False))
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
            return [(6, False, ids)]

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
            vals = proxy._records[index]
            self._values.update(vals)
            if hasattr(vals, '_changed'):
                self._changed.update(vals._changed)

    def _get_modifier(self, field, modifier, default=False, modmap=None, vals=None):
        if vals is None:
            vals = {**self._values, '•parent•': self._proxy._parent._values}

        return super()._get_modifier(field, modifier, default=default, modmap=modmap, vals=vals)

    def _onchange_values(self):
        values = super(O2MForm, self)._onchange_values()
        # computed o2m may not have a relation_field(?)
        descr = self._proxy._descr
        if 'relation_field' in descr: # note: should be fine because not recursive
            values[descr['relation_field']] = self._proxy._parent._onchange_values()
        return values

    def save(self):
        proxy = self._proxy
        commands = proxy._parent._values[proxy._field]
        values = self._values_to_save()
        if self._index is None:
            commands.append((0, 0, values))
        else:
            index = proxy._command_index(self._index)
            (c, id_, vs) = commands[index]
            if c == 0:
                vs.update(values)
            elif c == 1:
                if vs is None:
                    vs = UpdateDict()
                assert isinstance(vs, UpdateDict), type(vs)
                vs.update(values)
                commands[index] = (1, id_, vs)
            else:
                raise AssertionError("Expected command type 0 or 1, found %s" % c)

        # FIXME: should be called when performing on change => value needs to be serialised into parent every time?
        proxy._parent._perform_onchange([proxy._field])

    def _values_to_save(self, all_fields=False):
        """ Validates values and returns only fields modified since
        load/save
        """
        values = UpdateDict(self._values)
        values._changed.update(self._changed)
        if all_fields:
            return values

        for f in self._view['fields']:
            if self._get_modifier(f, 'required') and not (self._get_modifier(f, 'column_invisible') or self._get_modifier(f, 'invisible')):
                assert self._values[f] is not False, "{} is a required field".format(f)

        return values

class UpdateDict(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._changed = set()
        if args and isinstance(args[0], UpdateDict):
            self._changed.update(args[0]._changed)

    def changed_items(self):
        return (
            (k, v) for k, v in self.items()
            if k in self._changed
        )

    def update(self, *args, **kw):
        super().update(*args, **kw)
        if args and isinstance(args[0], UpdateDict):
            self._changed.update(args[0]._changed)

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
                if values is None:
                    # read based on view info
                    r = model.browse(rid)
                    values = UpdateDict(record_to_values(fields, r))
                self._records.append(values)
            elif command == 2:
                pass
            else:
                raise AssertionError("O2M proxy only supports commands 0, 1 and 2, found %s" % command)

    def __len__(self):
        return len(self._records)

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
            v = [(1, r.id, None) for r in v]
        elif descr['type'] == 'datetime' and isinstance(v, datetime):
            v = odoo.fields.Datetime.to_string(v)
        elif descr['type'] == 'date' and isinstance(v, date):
            v = odoo.fields.Date.to_string(v)
        r[f] = v
    return r

def _cleanup_from_default(type_, value):
    if not value:
        if type_ == 'many2many':
            return [(6, False, [])]
        elif type_ == 'one2many':
            return []
        elif type_ in ('integer', 'float'):
            return 0
        return value

    if type_ == 'one2many':
        return [c for c in value if c[0] != 6]
    elif type_ == 'datetime' and isinstance(value, datetime):
        return odoo.fields.Datetime.to_string(value)
    elif type_ == 'date' and isinstance(value, date):
        return odoo.fields.Date.to_string(value)

def _get_node(view, f, *arg):
    """ Find etree node for the field ``f`` in the view's arch
    """
    return next((
        n for n in view['tree'].iter('field')
        if n.get('name') == f
    ), *arg)

def tagged(*tags):
    """
    A decorator to tag BaseCase objects
    Tags are stored in a set that can be accessed from a 'test_tags' attribute
    A tag prefixed by '-' will remove the tag e.g. to remove the 'standard' tag
    By default, all Test classes from odoo.tests.common have a test_tags
    attribute that defaults to 'standard' and also the module technical name
    When using class inheritance, the tags are NOT inherited.
    """
    def tags_decorator(obj):
        include = {t for t in tags if not t.startswith('-')}
        exclude = {t[1:] for t in tags if t.startswith('-')}
        obj.test_tags = (getattr(obj, 'test_tags', set()) | include) - exclude # todo remove getattr in master since we want to limmit tagged to BaseCase and always have +standard tag
        return obj
    return tags_decorator


class TagsSelector(object):
    """ Test selector based on tags. """
    filter_spec_re = re.compile(r'^([+-]?)(\*|\w*)(?:/(\w*))?(?::(\w*))?(?:\.(\w*))?$')  # [-][tag][/module][:class][.method]

    def __init__(self, spec):
        """ Parse the spec to determine tags to include and exclude. """
        filter_specs = {t.strip() for t in spec.split(',') if t.strip()}
        self.exclude = set()
        self.include = set()

        for filter_spec in filter_specs:
            match = self.filter_spec_re.match(filter_spec)
            if not match:
                _logger.error('Invalid tag %s', filter_spec)
                continue

            sign, tag, module, klass, method = match.groups()
            is_include = sign != '-'

            if not tag and is_include:
                # including /module:class.method implicitly requires 'standard'
                tag = 'standard'
            elif not tag or tag == '*':
                # '*' indicates all tests (instead of 'standard' tests only)
                tag = None
            test_filter = (tag, module, klass, method)

            if is_include:
                self.include.add(test_filter)
            else:
                self.exclude.add(test_filter)

        if self.exclude and not self.include:
            self.include.add(('standard', None, None, None))

    def check(self, test):
        """ Return whether ``arg`` matches the specification: it must have at
            least one tag in ``self.include`` and none in ``self.exclude`` for each tag category.
        """
        if not hasattr(test, 'test_tags'): # handle the case where the Test does not inherit from BaseCase and has no test_tags
            _logger.debug("Skipping test '%s' because no test_tag found.", test)
            return False

        test_module = getattr(test, 'test_module', None)
        test_class = getattr(test, 'test_class', None)
        test_tags = test.test_tags | {test_module}  # module as test_tags deprecated, keep for retrocompatibility, 
        test_method = getattr(test, '_testMethodName', None)

        def _is_matching(test_filter):
            (tag, module, klass, method) = test_filter
            if tag and tag not in test_tags:
                return False
            elif module and module != test_module:
                return False
            elif klass and klass != test_class:
                return False
            elif method and test_method and method != test_method:
                return False
            return True

        if any(_is_matching(test_filter) for test_filter in self.exclude):
            return False

        if any(_is_matching(test_filter) for test_filter in self.include):
            return True

        return False
