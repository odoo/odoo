# -*- coding: utf-8 -*-
"""
The module :mod:`odoo.tests.common` provides unittest test cases and a few
helpers and classes to write tests.

"""
from __future__ import annotations

import base64
import concurrent.futures
import contextlib
import difflib
import importlib
import inspect
import itertools
import json
import logging
import os
import pathlib
import platform
import pprint
import psutil
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import unittest
import warnings
from collections import defaultdict, deque
from concurrent.futures import Future, CancelledError, wait
from contextlib import contextmanager, ExitStack
from copy import deepcopy
from datetime import datetime
from functools import lru_cache, partial
from itertools import zip_longest as izip_longest
from passlib.context import CryptContext
from typing import Optional, Iterable
from unittest.mock import patch, _patch, Mock
from xmlrpc import client as xmlrpclib

try:
    from concurrent.futures import InvalidStateError
except ImportError:
    InvalidStateError = NotImplementedError

import freezegun
import requests
import werkzeug.urls
from lxml import etree, html
from requests import PreparedRequest, Session
from urllib3.util import Url, parse_url

import odoo
from odoo import api
from odoo.exceptions import AccessError
from odoo.fields import Command
from odoo.http import BadRequest
from odoo.modules import module
from odoo.modules.registry import Registry
from odoo.service import security
from odoo.sql_db import BaseCursor, Cursor, TestCursor
from odoo.tools import config, float_compare, mute_logger, profiler, SQL, DotDict
from odoo.tools.mail import single_email_re
from odoo.tools.misc import find_in_path, lower_logging
from odoo.tools.xml_utils import _validate_xml

from . import case

try:
    # the behaviour of decorator changed in 5.0.5 changing the structure of the traceback when
    # an error is raised inside a method using a decorator.
    # this is not a hudge problem for test execution but this makes error message
    # more difficult to read and breaks test_with_decorators
    # This also changes the error format making runbot error matching fail
    # This also breaks the first frame meaning that the module detection will also fail on runbot
    # In 5.1 decoratorx was introduced and it looks like it has the same behaviour of old decorator
    from decorator import decoratorx as decorator
except ImportError:
    from decorator import decorator

try:
    import websocket
except ImportError:
    # chrome headless tests will be skipped
    websocket = None

try:
    import freezegun
except ImportError:
    freezegun = None

_logger = logging.getLogger(__name__)
if odoo.cli.COMMAND in ('server', 'start') and not (config['test_enable'] or config['test_file']):
    _logger.error(
        "Importing test framework"
        ", avoid importing from business modules and when not running in test mode",
        stack_info=True,
    )
else:
    _logger.info("Importing test framework", stack_info=_logger.isEnabledFor(logging.DEBUG))


# backward compatibility: Form was defined in this file
def __getattr__(name):
    # pylint: disable=import-outside-toplevel
    if name != 'Form':
        raise AttributeError(name)

    from .form import Form

    warnings.warn(
        "Since 18.0: odoo.tests.common.Form is deprecated, use odoo.tests.Form",
        category=DeprecationWarning,
        stacklevel=2,
    )
    return Form


# The odoo library is supposed already configured.
ADDONS_PATH = odoo.tools.config['addons_path']
HOST = '127.0.0.1'
# Useless constant, tests are aware of the content of demo data
ADMIN_USER_ID = odoo.SUPERUSER_ID

CHECK_BROWSER_SLEEP = 0.1 # seconds
CHECK_BROWSER_ITERATIONS = 100
BROWSER_WAIT = CHECK_BROWSER_SLEEP * CHECK_BROWSER_ITERATIONS # seconds
DEFAULT_SUCCESS_SIGNAL = 'test successful'
TEST_CURSOR_COOKIE_NAME = 'test_request_key'

def get_db_name():
    db = odoo.tools.config['db_name']
    # If the database name is not provided on the command-line,
    # use the one on the thread (which means if it is provided on
    # the command-line, this will break when installing another
    # database from XML-RPC).
    if not db and hasattr(threading.current_thread(), 'dbname'):
        return threading.current_thread().dbname
    return db


standalone_tests = defaultdict(list)


def standalone(*tags):
    """ Decorator for standalone test functions.  This is somewhat dedicated to
    tests that install, upgrade or uninstall some modules, which is currently
    forbidden in regular test cases.  The function is registered under the given
    ``tags`` and the corresponding Odoo module name.
    """
    def register(func):
        # register func by odoo module name
        if func.__module__.startswith('odoo.addons.'):
            module = func.__module__.split('.')[2]
            standalone_tests[module].append(func)
        # register func with aribitrary name, if any
        for tag in tags:
            standalone_tests[tag].append(func)
        standalone_tests['all'].append(func)
        return func

    return register


def test_xsd(url=None, path=None, skip=False):
    def decorator(func):
        def wrapped_f(self, *args, **kwargs):
            if not skip:
                xmls = func(self, *args, **kwargs)
                _validate_xml(self.env, url, path, xmls)
        return wrapped_f
    return decorator


# For backwards-compatibility - get_db_name() should be used instead
DB = get_db_name()


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

    groups_id = [Command.set(kwargs.pop('groups_id', False) or [env.ref(g.strip()).id for g in groups.split(',')])]
    create_values = dict(kwargs, login=login, groups_id=groups_id)
    # automatically generate a name as "Login (groups)" to ease user comprehension
    if not create_values.get('name'):
        create_values['name'] = '%s (%s)' % (login, groups)
    # automatically give a password equal to login
    if not create_values.get('password'):
        create_values['password'] = login + 'x' * (8 - len(login))
    # generate email if not given as most test require an email
    if 'email' not in create_values:
        if single_email_re.match(login):
            create_values['email'] = login
        else:
            create_values['email'] = '%s.%s@example.com' % (login[0], login[0])
    # ensure company_id + allowed company constraint works if not given at create
    if 'company_id' in create_values and 'company_ids' not in create_values:
        create_values['company_ids'] = [(4, create_values['company_id'])]

    return env['res.users'].with_context(**context).create(create_values)

def loaded_demo_data(env):
    return bool(env.ref('base.user_demo', raise_if_not_found=False))

class RecordCapturer:
    def __init__(self, model, domain):
        self._model = model
        self._domain = domain

    def __enter__(self):
        self._before = self._model.search(self._domain, order='id')
        self._after = None
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if exc_type is None:
            self._after = self._model.search(self._domain, order='id') - self._before

    @property
    def records(self):
        if self._after is None:
            return self._model.search(self._domain, order='id') - self._before
        return self._after


class MetaCase(type):
    """ Metaclass of test case classes to assign default 'test_tags':
        'standard', 'at_install' and the name of the module.
    """
    def __init__(cls, name, bases, attrs):
        super(MetaCase, cls).__init__(name, bases, attrs)
        # assign default test tags
        if cls.__module__.startswith('odoo.addons.'):
            if getattr(cls, 'test_tags', None) is None:
                cls.test_tags = {'standard', 'at_install'}
            cls.test_module = cls.__module__.split('.')[2]
            cls.test_class = cls.__name__
            cls.test_sequence = 0


def _normalize_arch_for_assert(arch_string, parser_method="xml"):
    """Takes some xml and normalize it to make it comparable to other xml
    in particular, blank text is removed, and the output is pretty-printed

    :param str arch_string: the string representing an XML arch
    :param str parser_method: an string representing which lxml.Parser class to use
        when normalizing both archs. Takes either "xml" or "html"
    :return: the normalized arch
    :rtype str:
    """
    Parser = None
    if parser_method == 'xml':
        Parser = etree.XMLParser
    elif parser_method == 'html':
        Parser = etree.HTMLParser
    parser = Parser(remove_blank_text=True)
    arch_string = etree.fromstring(arch_string, parser=parser)
    return etree.tostring(arch_string, pretty_print=True, encoding='unicode')

class BlockedRequest(requests.exceptions.ConnectionError):
    pass
_super_send = requests.Session.send
class BaseCase(case.TestCase, metaclass=MetaCase):
    """ Subclass of TestCase for Odoo-specific code. This class is abstract and
    expects self.registry, self.cr and self.uid to be initialized by subclasses.
    """

    longMessage = True      # more verbose error message by default: https://www.odoo.com/r/Vmh
    warm = True             # False during warm-up phase (see :func:`warmup`)
    _python_version = sys.version_info

    _tests_run_count = int(os.environ.get('ODOO_TEST_FAILURE_RETRIES', 0)) + 1

    def __init__(self, methodName='runTest'):
        super().__init__(methodName)
        self.addTypeEqualityFunc(etree._Element, self.assertTreesEqual)
        self.addTypeEqualityFunc(html.HtmlElement, self.assertTreesEqual)
        if methodName != 'runTest':
            self.test_tags = self.test_tags | set(self.get_method_additional_tags(getattr(self, methodName)))


    @classmethod
    def _request_handler(cls, s: Session, r: PreparedRequest, /, **kw):
        # allow localhost requests
        # TODO: also check port?
        url = werkzeug.urls.url_parse(r.url)
        timeout = kw.get('timeout')
        if timeout and timeout < 10:
            _logger.getChild('requests').info('request %s with timeout %s increased to 10s during tests', url, timeout)
            kw['timeout'] = 10
        if url.host in (HOST, 'localhost'):
            return _super_send(s, r, **kw)
        if url.scheme == 'file':
            return _super_send(s, r, **kw)

        _logger.getChild('requests').info(
            "Blocking un-mocked external HTTP request %s %s", r.method, r.url)
        raise BlockedRequest(f"External requests verboten (was {r.method} {r.url})")

    def run(self, result):
        testMethod = getattr(self, self._testMethodName)

        if getattr(testMethod, '_retry', True) and getattr(self, '_retry', True):
            tests_run_count = self._tests_run_count
        else:
            tests_run_count = 1
            _logger.info('Auto retry disabled for %s', self)

        quiet_log = None
        for retry in range(tests_run_count):
            result.had_failure = False  # reset in case of retry without soft_fail
            if retry:
                _logger.runbot(f'Retrying a failed test: {self}')
            if retry < tests_run_count-1:
                with warnings.catch_warnings(), \
                        result.soft_fail(), \
                        lower_logging(25, logging.INFO) as quiet_log:
                    super().run(result)
                if not (result.had_failure or quiet_log.had_error_log):
                    break
            else:  # last try
                super().run(result)
                if not result.wasSuccessful() and BaseCase._tests_run_count != 1:
                    _logger.runbot('Disabling auto-retry after a failed test')
                    BaseCase._tests_run_count = 1

    @classmethod
    def setUpClass(cls):
        def check_remaining_processes():
            current_process = psutil.Process()
            children = current_process.children(recursive=False)
            for child in children:
                _logger.warning('A child process was found, terminating it: %s', child)
                child.terminate()
            psutil.wait_procs(children, timeout=10)  # mainly to avoid a zombie process that would be logged again at the end.
        cls.addClassCleanup(check_remaining_processes)

        def check_remaining_patchers():
            for patcher in _patch._active_patches:
                _logger.warning("A patcher (targeting %s.%s) was remaining active at the end of %s, disabling it...", patcher.target, patcher.attribute, cls.__name__)
                patcher.stop()
        cls.addClassCleanup(check_remaining_patchers)
        super().setUpClass()
        if 'standard' in cls.test_tags or 'click_all' in cls.test_tags:
            # if the method is passed directly `patch` discards the session
            # object which we need
            # pylint: disable=unnecessary-lambda
            patcher = patch.object(
                requests.sessions.Session,
                'send',
                lambda s, r, **kwargs: cls._request_handler(s, r, **kwargs),
            )
            patcher.start()
            cls.addClassCleanup(patcher.stop)

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
        shortcut for ``_xmlid_lookup``

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

    def patch(self, obj, key, val):
        """ Do the patch ``setattr(obj, key, val)``, and prepare cleanup. """
        patcher = patch.object(obj, key, val)   # this is unittest.mock.patch
        patcher.start()
        self.addCleanup(patcher.stop)

    @classmethod
    def classPatch(cls, obj, key, val):
        """ Do the patch ``setattr(obj, key, val)``, and prepare cleanup. """
        patcher = patch.object(obj, key, val)   # this is unittest.mock.patch
        patcher.start()
        cls.addClassCleanup(patcher.stop)

    def startPatcher(self, patcher):
        mock = patcher.start()
        self.addCleanup(patcher.stop)
        return mock

    @classmethod
    def startClassPatcher(cls, patcher):
        mock = patcher.start()
        cls.addClassCleanup(patcher.stop)
        return mock

    @contextmanager
    def with_user(self, login):
        """ Change user for a given test, like with self.with_user() ... """
        old_uid = self.uid
        try:
            user = self.env['res.users'].sudo().search([('login', '=', login)])
            assert user, "Login %s not found" % login
            # switch user
            self.uid = user.id
            self.env = self.env(user=self.uid)
            yield
        finally:
            # back
            self.uid = old_uid
            self.env = self.env(user=self.uid)

    @contextmanager
    def debug_mode(self):
        """ Enable the effects of debug mode (in particular for group ``base.group_no_one``). """
        request = Mock(
            httprequest=Mock(host='localhost'),
            db=self.env.cr.dbname,
            env=self.env,
            session=DotDict(odoo.http.get_default_session(), debug='1'),
        )
        try:
            self.env.flush_all()
            self.env.invalidate_all()
            odoo.http._request_stack.push(request)
            yield
            self.env.flush_all()
            self.env.invalidate_all()
        finally:
            popped_request = odoo.http._request_stack.pop()
            if popped_request is not request:
                raise Exception('Wrong request stack cleanup.')

    @contextmanager
    def _assertRaises(self, exception, *, msg=None):
        """ Context manager that clears the environment upon failure. """
        with ExitStack() as init:
            if hasattr(self, 'env'):
                init.enter_context(self.env.cr.savepoint())
                if issubclass(exception, AccessError):
                    # The savepoint() above calls flush(), which leaves the
                    # record cache with lots of data.  This can prevent
                    # access errors to be detected. In order to avoid this
                    # issue, we clear the cache before proceeding.
                    self.env.cr.clear()

            with ExitStack() as inner:
                cm = inner.enter_context(super().assertRaises(exception, msg=msg))
                # *moves* the cleanups from init to inner, this ensures the
                # savepoint gets rolled back when `yield` raises `exception`,
                # but still allows the initialisation to be protected *and* not
                # interfered with by `assertRaises`.
                inner.push(init.pop_all())

                yield cm

    def assertRaises(self, exception, func=None, *args, **kwargs):
        if func:
            with self._assertRaises(exception):
                func(*args, **kwargs)
        else:
            return self._assertRaises(exception, **kwargs)

    def _patchExecute(self, actual_queries, flush=True):
        Cursor_execute = Cursor.execute

        def execute(self, query, params=None, log_exceptions=None):
            actual_queries.append(query.code if isinstance(query, SQL) else query)
            return Cursor_execute(self, query, params, log_exceptions)

        if flush:
            self.env.flush_all()
            self.env.cr.flush()

        with (
            patch('odoo.sql_db.Cursor.execute', execute),
            patch.object(self.env.registry, 'unaccent', lambda x: x),
        ):
            yield actual_queries
            if flush:
                self.env.flush_all()
                self.env.cr.flush()

    @contextmanager
    def assertQueries(self, expected, flush=True):
        """ Check the queries made by the current cursor. ``expected`` is a list
        of strings representing the expected queries being made. Query strings
        are matched against each other, ignoring case and whitespaces.
        """
        actual_queries = []

        yield from self._patchExecute(actual_queries, flush)

        if not self.warm:
            return

        self.assertEqual(
            len(actual_queries), len(expected),
            "\n---- actual queries:\n%s\n---- expected queries:\n%s" % (
                "\n".join(actual_queries), "\n".join(expected),
            )
        )
        for actual_query, expect_query in zip(actual_queries, expected):
            self.assertEqual(
                "".join(actual_query.lower().split()),
                "".join(expect_query.lower().split()),
                "\n---- actual query:\n%s\n---- not like:\n%s" % (actual_query, expect_query),
            )

    @contextmanager
    def assertQueriesContain(self, expected, flush=True):
        """ Check the queries made by the current cursor. ``expected`` is a list
        of strings representing the expected queries being made. Query strings
        are matched against each other, ignoring case and whitespaces.
        """
        actual_queries = []

        yield from self._patchExecute(actual_queries, flush)

        if not self.warm:
            return

        self.assertEqual(
            len(actual_queries), len(expected),
            "\n---- actual queries:\n%s\n---- expected queries:\n%s" % (
                "\n".join(actual_queries), "\n".join(expected),
            )
        )
        for actual_query, expect_query in zip(actual_queries, expected):
            self.assertIn(
                "".join(expect_query.lower().split()),
                "".join(actual_query.lower().split()),
                "\n---- actual query:\n%s\n---- doesn't contain:\n%s" % (actual_query, expect_query),
            )

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
            with patch('random.random', lambda: 1):
                login = self.env.user.login
                expected = counters.get(login, default)
                if flush:
                    self.env.flush_all()
                    self.env.cr.flush()
                count0 = self.cr.sql_log_count
                yield
                if flush:
                    self.env.flush_all()
                    self.env.cr.flush()
                count = self.cr.sql_log_count - count0
                if count != expected:
                    # add some info on caller to allow semi-automatic update of query count
                    frame, filename, linenum, funcname, lines, index = inspect.stack()[2]
                    filename = filename.replace('\\', '/')
                    if "/odoo/addons/" in filename:
                        filename = filename.rsplit("/odoo/addons/", 1)[1]
                    if count > expected:
                        msg = "Query count more than expected for user %s: %d > %d in %s at %s:%s"
                        # add a subtest in order to continue the test_method in case of failures
                        with self.subTest():
                            self.fail(msg % (login, count, expected, funcname, filename, linenum))
                    else:
                        logger = logging.getLogger(type(self).__module__)
                        msg = "Query count less than expected for user %s: %d < %d in %s at %s:%s"
                        logger.info(msg, login, count, expected, funcname, filename, linenum)
        else:
            # flush before and after during warmup, in order to reproduce the
            # same operations, otherwise the caches might not be ready!
            if flush:
                self.env.flush_all()
                self.env.cr.flush()
            yield
            if flush:
                self.env.flush_all()
                self.env.cr.flush()

    def assertRecordValues(
            self,
            records: odoo.models.BaseModel,
            expected_values: list[dict],
            *,
            field_names: Optional[Iterable[str]] = None,
    ) -> None:
        ''' Compare a recordset with a list of dictionaries representing the expected results.
        This method performs a comparison element by element based on their index.
        Then, the order of the expected values is extremely important.

        .. note::

            - ``None`` expected values can be used for empty fields.
            - x2many fields are expected by ids (so the expected value should be
              a ``list[int]``
            - many2one fields are expected by id (so the expected value should
              be an ``int``

        :param records: The records to compare.
        :param expected_values: Items to check the ``records`` against.
        :param field_names: list of fields to check during comparison, if
                            unspecified all expected_values must have the same
                            keys and all are checked
        '''
        if not field_names:
            field_names = expected_values[0].keys()
            for i, v in enumerate(expected_values):
                self.assertEqual(
                    v.keys(), field_names,
                    f"All expected values must have the same keys, found differences between records 0 and {i}",
                )

        expected_reformatted = []
        for vs in expected_values:
            r = {}
            for f in field_names:
                t = records._fields[f].type
                if t in ('one2many', 'many2many'):
                    r[f] = sorted(vs[f])
                elif t == 'float':
                    r[f] = float(vs[f])
                elif t == 'integer':
                    r[f] = int(vs[f])
                elif vs[f] is None:
                    r[f] = False
                else:
                    r[f] = vs[f]
            expected_reformatted.append(r)

        record_reformatted = []
        for record in records:
            r = {}
            for field_name in field_names:
                record_value = record[field_name]
                match (field := record._fields[field_name]).type:
                    case 'many2one':
                        record_value = record_value.id
                    case 'one2many' | 'many2many':
                        record_value = sorted(record_value.ids)
                    case 'float' if digits := field.get_digits(record.env):
                        record_value = Approx(record_value, digits[1], decorate=False)
                    case 'monetary' if currency_field_name := field.get_currency_field(record):
                        # don't round if there's no currency set
                        if c := record[currency_field_name]:
                            record_value = Approx(record_value, c, decorate=False)
                r[field_name] = record_value
            record_reformatted.append(r)

        try:
            self.assertSequenceEqual(expected_reformatted, record_reformatted, seq_type=list)
            return
        except AssertionError as e:
            standardMsg, _, diffMsg = str(e).rpartition('\n')
            if 'self.maxDiff' not in diffMsg:
                raise
            # move out of handler to avoid exception chaining

        diffMsg = "".join(difflib.unified_diff(
            pprint.pformat(expected_reformatted).splitlines(keepends=True),
            pprint.pformat(record_reformatted).splitlines(keepends=True),
            fromfile="expected", tofile="records",
        ))
        self.fail(self._formatMessage(None, standardMsg + '\n' + diffMsg))

    # turns out this thing may not be quite as useful as we thought...
    def assertItemsEqual(self, a, b, msg=None):
        self.assertCountEqual(a, b, msg=None)

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

    def _assertXMLEqual(self, original, expected, parser="xml"):
        """Asserts that two xmls archs are equal

        :param original: the xml arch to test
        :type original: str
        :param expected: the xml arch of reference
        :type expected: str
        :param parser: an string representing which lxml.Parser class to use
            when normalizing both archs. Takes either "xml" or "html"
        :type parser: str
        """
        self.maxDiff = 10000
        if original:
            original = _normalize_arch_for_assert(original, parser)
        if expected:
            expected = _normalize_arch_for_assert(expected, parser)
        self.assertEqual(original, expected)

    def assertXMLEqual(self, original, expected):
        return self._assertXMLEqual(original, expected)

    def assertHTMLEqual(self, original, expected):
        return self._assertXMLEqual(original, expected, 'html')

    def profile(self, description='', **kwargs):
        test_method = getattr(self, '_testMethodName', 'Unknown test method')
        if not hasattr(self, 'profile_session'):
            self.profile_session = profiler.make_session(test_method)
        if 'db' not in kwargs:
            kwargs['db'] = self.env.cr.dbname
        return profiler.Profiler(
            description='%s uid:%s %s %s' % (test_method, self.env.user.id, 'warm' if self.warm else 'cold', description),
            profile_session=self.profile_session,
            **kwargs)

    def setUp(self):
        super().setUp()
        self.http_request_key = self.canonical_tag
        self.http_request_strict_check = False  # by default, don't be to strict

        def reset_http_key():
            self.http_request_key = None
            self.http_request_strict_check = True
        self.addCleanup(reset_http_key)  # this should avoid to have a request executing during teardown

    def mandatory_request_route(self, route):
        return route == "/websocket"

    def check_test_cursor(self, operation):
        if odoo.modules.module.current_test != self:
            message = f"Trying to open a test cursor for {self.canonical_tag} while already in a test {odoo.modules.module.current_test.canonical_tag}"
            _logger.runbot(message)
            raise BadRequest(message)
        request = odoo.http.request
        if not request or isinstance(request, Mock):
            return
        if not hasattr(self, 'http_request_key') or not self.http_request_key:
            message = f'Using a test cursor without http_request_key, most likely between two tests on request {request.httprequest.path} in {module.current_test.canonical_tag}'
            _logger.info(message)
            raise BadRequest(message)
        http_request_key = request.httprequest.cookies.get(TEST_CURSOR_COOKIE_NAME)
        if not http_request_key:
            if self.http_request_strict_check or self.mandatory_request_route(request.httprequest.path):
                reason = 'for this path'
                if self.http_request_strict_check:
                    reason = 'after a browser_js call'
                message = f'Using a test cursor without specified test on request {request.httprequest.path} in {module.current_test.canonical_tag} as been ignored since cookie is mandatory {reason}'
                _logger.info(message)
                raise BadRequest(message)
            if operation == '__init__':  # main difference with master, don't fail if no cookie is defined_check
                message = f'Opening a test cursor without specified test on request {request.httprequest.path} in {module.current_test.canonical_tag}'
                _logger.info(message)
            return
        http_request_required_key = self.http_request_key
        if http_request_key != http_request_required_key:
            expected = http_request_required_key
            _logger.runbot(
                'Request with path %s has been ignored during test as it '
                'it does not contain the test_cursor cookie or it is expired.'
                ' (required "%s", got "%s")',
                request.httprequest.path, expected, http_request_key
            )
            raise BadRequest(
                'Request ignored during test as it does not contain the required cookie.'
            )

    def get_method_additional_tags(self, test_method):
        """Guess if the test_methods is a query_count and adds an `is_query_count` tag on the test
        """
        additional_tags = []
        if odoo.tools.config['test_tags'] and 'is_query_count' in odoo.tools.config['test_tags']:
            method_source = inspect.getsource(test_method) if test_method else ''
            if 'self.assertQueryCount' in method_source:
                additional_tags.append('is_query_count')
        return additional_tags

class Like:
    """
        A string-like object comparable to other strings but where the substring
        '...' can match anything in the other string.

        Example of usage:

            self.assertEqual("SELECT field1, field2, field3 FROM model", Like('SELECT ... FROM model'))
            self.assertIn(Like('Company ... (SF)'), ['TestPartner', 'Company 8 (SF)', 'SomeAdress'])
            self.assertEqual([
                'TestPartner',
                'Company 8 (SF)',
                'Anything else'
            ], [
                'TestPartner',
                Like('Company ... (SF)'),
                Like('...'),
            ])

        In case of mismatch, here is an example of error message

            AssertionError: Lists differ: ['TestPartner', 'Company 8 (LA)', 'Anything else'] != ['TestPartner', ~Company ... (SF), ~...]

            First differing element 1:
            'Company 8 (LA)'
            ~Company ... (SF)~

            - ['TestPartner', 'Company 8 (LA)', 'Anything else']
            + ['TestPartner', ~Company ... (SF), ~...]


        """
    def __init__(self, pattern):
        self.pattern = pattern
        self.regex = '.*'.join([re.escape(part.strip()) for part in self.pattern.split('...')])

    def __eq__(self, other):
        return re.fullmatch(self.regex, other.strip(), re.DOTALL)

    def __repr__(self):
        return repr(self.pattern)


class Approx:  # noqa: PLW1641
    """A wrapper for approximate float comparisons. Uses float_compare under
    the hood.

    Most of the time, :meth:`TestCase.assertAlmostEqual` is more useful, but it
    doesn't work for all helpers.
    """
    def __init__(self, value: float, rounding: int | float | odoo.addons.base.models.res_currency.Currency, /, decorate: bool) -> None:  # noqa: PYI041
        self.value = value
        self.decorate = decorate
        if isinstance(rounding, int):
            self.cmp = partial(float_compare, precision_digits=rounding)
        elif isinstance(rounding, float):
            self.cmp = partial(float_compare, precision_rounding=rounding)
        else:
            self.cmp = rounding.compare_amounts

    def __repr__(self) -> str:
        if self.decorate:
            return f"~{self.value!r}"
        return repr(self.value)

    def __eq__(self, other: object) -> bool | NotImplemented:
        if not isinstance(other, (float, int)):
            return NotImplemented
        return self.cmp(self.value, other) == 0


savepoint_seq = itertools.count()


class TransactionCase(BaseCase):
    """ Test class in which all test methods are run in a single transaction,
    but each test method is run in a sub-transaction managed by a savepoint.
    The transaction's cursor is always closed without committing.

    The data setup common to all methods should be done in the class method
    `setUpClass`, so that it is done once for all test methods. This is useful
    for test cases containing fast tests but with significant database setup
    common to all cases (complex in-db test data).

    After being run, each test method cleans up the record cache and the
    registry cache. However, there is no cleanup of the registry models and
    fields. If a test modifies the registry (custom models and/or fields), it
    should prepare the necessary cleanup (`self.registry.reset_changes()`).
    """
    registry: Registry = None
    env: api.Environment = None
    cr: Cursor = None
    muted_registry_logger = mute_logger(odoo.modules.registry._logger.name)
    freeze_time = None

    @classmethod
    def _gc_filestore(cls):
        # attachment can be created or unlink during the tests.
        # they can addup during test and take some disc space.
        # since cron are not running during tests, we need to gc manually
        # We need to check the status of the file system outside of the test cursor
        with Registry(get_db_name()).cursor() as cr:
            gc_env = api.Environment(cr, odoo.SUPERUSER_ID, {})
            gc_env['ir.attachment']._gc_file_store_unsafe()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.addClassCleanup(cls._gc_filestore)
        cls.registry = Registry(get_db_name())
        cls.registry_start_invalidated = cls.registry.registry_invalidated
        cls.registry_start_sequence = cls.registry.registry_sequence
        cls.registry_cache_sequences = dict(cls.registry.cache_sequences)

        def reset_changes():
            if (cls.registry_start_sequence != cls.registry.registry_sequence) or cls.registry.registry_invalidated:
                with cls.registry.cursor() as cr:
                    cls.registry.setup_models(cr)
            cls.registry.registry_invalidated = cls.registry_start_invalidated
            cls.registry.registry_sequence = cls.registry_start_sequence
            with cls.muted_registry_logger:
                cls.registry.clear_all_caches()
            cls.registry.cache_invalidated.clear()
            cls.registry.cache_sequences = cls.registry_cache_sequences
        cls.addClassCleanup(reset_changes)

        def signal_changes():
            if not cls.registry.ready:
                _logger.info('Skipping signal changes during tests')
                return
            if cls.registry.registry_invalidated or cls.registry.cache_invalidated:
                _logger.info('Simulating signal changes during tests')
            if cls.registry.registry_invalidated:
                cls.registry.registry_sequence += 1
            for cache_name in cls.registry.cache_invalidated or ():
                cls.registry.cache_sequences[cache_name] += 1
            cls.registry.registry_invalidated = False
            cls.registry.cache_invalidated.clear()

        cls._signal_changes_patcher = patch.object(cls.registry, 'signal_changes', signal_changes)
        cls.startClassPatcher(cls._signal_changes_patcher)

        cls.cr = cls.registry.cursor()
        cls.addClassCleanup(cls.cr.close)

        def check_cursor_stack():
            for cursor in TestCursor._cursors_stack:
                _logger.info('One curor was remaining in the TestCursor stack at the end of the test')
                cursor._closed = True
            TestCursor._cursors_stack = []

        cls.addClassCleanup(check_cursor_stack)

        if cls.freeze_time:
            cls.startClassPatcher(freezegun.freeze_time(cls.freeze_time))

        def forbidden(*args, **kwars):
            traceback.print_stack()
            raise AssertionError('Cannot commit or rollback a cursor from inside a test, this will lead to a broken cursor when trying to rollback the test. Please rollback to a specific savepoint instead or open another cursor if really necessary')

        cls.commit_patcher = patch.object(cls.cr, 'commit', forbidden)
        cls.startClassPatcher(cls.commit_patcher)
        cls.rollback_patcher = patch.object(cls.cr, 'rollback', forbidden)
        cls.startClassPatcher(cls.rollback_patcher)
        cls.close_patcher = patch.object(cls.cr, 'close', forbidden)
        cls.startClassPatcher(cls.close_patcher)


        cls.env = api.Environment(cls.cr, odoo.SUPERUSER_ID, {})

        # speedup CryptContext. Many user an password are done during tests, avoid spending time hasing password with many rounds
        def _crypt_context(self):  # noqa: ARG001
            return CryptContext(
                ['pbkdf2_sha512', 'plaintext'],
                pbkdf2_sha512__rounds=1,
            )
        cls._crypt_context_patcher = patch('odoo.addons.base.models.res_users.Users._crypt_context', _crypt_context)
        cls.startClassPatcher(cls._crypt_context_patcher)

    def setUp(self):
        super().setUp()
        # restore environments after the test to avoid invoking flush() with an
        # invalid environment (inexistent user id) from another test
        envs = self.env.transaction.envs
        for env in list(envs):
            self.addCleanup(env.clear)
        # restore the set of known environments as it was at setUp
        self.addCleanup(envs.update, list(envs))
        self.addCleanup(envs.clear)

        self.addCleanup(self.muted_registry_logger(self.registry.clear_all_caches))

        # This prevents precommit functions and data from piling up
        # until cr.flush is called in 'assertRaises' clauses
        # (these are not cleared in self.env.clear or envs.clear)
        cr = self.env.cr

        def _reset(cb, funcs, data):
            cb._funcs = funcs
            cb.data = data
        for callback in [cr.precommit, cr.postcommit, cr.prerollback, cr.postrollback]:
            self.addCleanup(_reset, callback, deque(callback._funcs), deepcopy(callback.data))

        # flush everything in setUpClass before introducing a savepoint
        self.env.flush_all()

        self._savepoint_id = next(savepoint_seq)
        self.cr.execute('SAVEPOINT test_%d' % self._savepoint_id)
        self.addCleanup(self.cr.execute, 'ROLLBACK TO SAVEPOINT test_%d' % self._savepoint_id)


class SingleTransactionCase(BaseCase):
    """ TestCase in which all test methods are run in the same transaction,
    the transaction is started with the first test method and rolled back at
    the end of the last.
    """
    @classmethod
    def __init_subclass__(cls):
        super().__init_subclass__()
        if issubclass(cls, TransactionCase):
            _logger.warning("%s inherits from both TransactionCase and SingleTransactionCase")

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.registry = Registry(get_db_name())
        cls.addClassCleanup(cls.registry.reset_changes)
        cls.addClassCleanup(cls.registry.clear_all_caches)

        cls.cr = cls.registry.cursor()
        cls.addClassCleanup(cls.cr.close)

        cls.env = api.Environment(cls.cr, odoo.SUPERUSER_ID, {})

    def setUp(self):
        super(SingleTransactionCase, self).setUp()
        self.env.flush_all()


class ChromeBrowserException(Exception):
    pass

def run(gen_func):
    def done(f):
        try:
            try:
                r = f.result()
            except Exception as e:
                f = coro.throw(e)
            else:
                f = coro.send(r)
        except StopIteration:
            return

        assert isinstance(f, Future), f"coroutine must yield futures, got {f}"
        f.add_done_callback(done)

    coro = gen_func()
    try:
        next(coro).add_done_callback(done)
    except StopIteration:
        return

def save_test_file(test_name, content, prefix, extension='png', logger=_logger, document_type='Screenshot', date_format="%Y%m%d_%H%M%S_%f"):
    assert re.fullmatch(r'\w*_', prefix)
    assert re.fullmatch(r'[a-z]+', extension)
    assert re.fullmatch(r'\w+', test_name)
    now = datetime.now().strftime(date_format)
    screenshots_dir = pathlib.Path(odoo.tools.config['screenshots']) / get_db_name() / 'screenshots'
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    fname = f'{prefix}{now}_{test_name}.{extension}'
    full_path = screenshots_dir / fname

    with full_path.open('wb') as f:
        f.write(content)
    logger.runbot(f'{document_type} in: {full_path}')


if os.name == 'posix' and platform.system() != 'Darwin':
    # since the introduction of pointer compression in Chrome 80 (v8 v8.0),
    # the memory reservation algorithm requires more than 8GiB of
    # virtual mem for alignment this exceeds our default memory limits.
    def _preexec():
        import resource  # noqa: PLC0415
        resource.setrlimit(resource.RLIMIT_AS, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
else:
    _preexec = None


class ChromeBrowser:
    """ Helper object to control a Chrome headless process. """
    remote_debugging_port = 0  # 9222, change it in a non-git-tracked file

    def __init__(self, test_case: HttpCase, success_signal: str = DEFAULT_SUCCESS_SIGNAL, headless: bool = True, debug: bool = False):
        self._logger = test_case._logger
        self.test_case = test_case
        self.success_signal = success_signal
        if websocket is None:
            self._logger.warning("websocket-client module is not installed")
            raise unittest.SkipTest("websocket-client module is not installed")
        self.user_data_dir = tempfile.mkdtemp(suffix='_chrome_odoo')

        otc = odoo.tools.config
        self.screencasts_dir = None
        self.screencast_frames = []
        if otc['screencasts']:
            self.screencasts_dir = os.path.join(otc['screencasts'], get_db_name(), 'screencasts')
            os.makedirs(self.screencasts_frames_dir, exist_ok=True)

        if os.name == 'posix':
            self.sigxcpu_handler = signal.getsignal(signal.SIGXCPU)
            signal.signal(signal.SIGXCPU, self.signal_handler)
        else:
            self.sigxcpu_handler = None

        test_case.browser_size = test_case.browser_size.replace('x', ',')

        self.chrome, self.devtools_port = self._chrome_start(
            user_data_dir=self.user_data_dir,
            touch_enabled=test_case.touch_enabled,
            headless=headless,
            debug=debug,
        )
        self.ws = self._open_websocket()
        self._request_id = itertools.count()
        self._result = Future()
        self.error_checker = None
        self.had_failure = False
        # maps request_id to Futures
        self._responses = {}
        # maps frame ids to callbacks
        self._frames = {}
        self._handlers = {
            'Fetch.requestPaused': self._handle_request_paused,
            'Runtime.consoleAPICalled': self._handle_console,
            'Runtime.exceptionThrown': self._handle_exception,
            'Page.frameStoppedLoading': self._handle_frame_stopped_loading,
            'Page.screencastFrame': self._handle_screencast_frame,
        }
        self._receiver = threading.Thread(
            target=self._receive,
            name="WebSocket events consumer",
            args=(get_db_name(),)
        )
        self._receiver.start()
        self._logger.info('Enable chrome headless console log notification')
        self._websocket_send('Runtime.enable')
        self._websocket_request('Fetch.enable')
        self._logger.info('Chrome headless enable page notifications')
        self._websocket_send('Page.enable')
        self._websocket_send('Page.setDownloadBehavior', params={
            'behavior': 'deny',
            'eventsEnabled': False,
        })
        self._websocket_send('Emulation.setFocusEmulationEnabled', params={'enabled': True})
        emulated_device = {
            'mobile': False,
            'width': None,
            'height': None,
            'deviceScaleFactor': 1,
        }
        emulated_device['width'], emulated_device['height'] = [int(size) for size in test_case.browser_size.split(",")]
        self._websocket_request('Emulation.setDeviceMetricsOverride', params=emulated_device)

    @property
    def screencasts_frames_dir(self):
        if screencasts_dir := self.screencasts_dir:
            return os.path.join(screencasts_dir, 'frames')
        else:
            return None

    def signal_handler(self, sig, frame):
        if sig == signal.SIGXCPU:
            _logger.info('CPU time limit reached, stopping Chrome and shutting down')
            self.stop()
            os._exit(0)

    def stop(self):
        if hasattr(self, 'ws'):
            try:
                self._websocket_send('Page.stopScreencast')
                if screencasts_frames_dir := self.screencasts_frames_dir:
                    self.screencasts_dir = None
                    if os.path.isdir(screencasts_frames_dir):
                        shutil.rmtree(screencasts_frames_dir, ignore_errors=True)

                self._websocket_request('Page.stopLoading')
                self._websocket_request('Runtime.evaluate', params={'expression': """
                ('serviceWorker' in navigator) &&
                    navigator.serviceWorker.getRegistrations().then(
                        registrations => Promise.all(registrations.map(r => r.unregister()))
                    )
                """, 'awaitPromise': True})
                # wait for the screenshot or whatever
                wait(self._responses.values(), 10)
                self._result.cancel()

                self._logger.info("Closing chrome headless with pid %s", self.chrome.pid)
                self._websocket_request('Browser.close')
            except ChromeBrowserException as e:
                _logger.runbot("WS error during browser shutdown: %s", e)
            except Exception:  # noqa: BLE001
                _logger.warning("Error during browser shutdown", exc_info=True)
            self._logger.info("Closing websocket connection")
            self.ws.close()
        if self.chrome:
            self._logger.info("Terminating chrome headless with pid %s", self.chrome.pid)
            self.chrome.terminate()
            try:
                self.chrome.wait(15)
            except subprocess.TimeoutExpired:
                self._logger.warning("Killing chrome headless with pid %s: still alive", self.chrome.pid)
                self.chrome.kill()

        if self.user_data_dir and os.path.isdir(self.user_data_dir) and self.user_data_dir != '/':
            self._logger.info('Removing chrome user profile "%s"', self.user_data_dir)
            shutil.rmtree(self.user_data_dir, ignore_errors=True)

        # Restore previous signal handler
        if self.sigxcpu_handler and os.name == 'posix':
            signal.signal(signal.SIGXCPU, self.sigxcpu_handler)

    @property
    def executable(self):
        try:
            return _find_executable()
        except Exception:
            self._logger.warning('Chrome executable not found')
            raise

    def _spawn_chrome(self, cmd):
        log_path = pathlib.Path(self.user_data_dir, 'err.log')
        with log_path.open('wb') as log_file:
            # pylint: disable=subprocess-popen-preexec-fn
            proc = subprocess.Popen(cmd, stderr=log_file, preexec_fn=_preexec)  # noqa: PLW1509

        port_file = pathlib.Path(self.user_data_dir, 'DevToolsActivePort')
        for _ in range(CHECK_BROWSER_ITERATIONS):
            time.sleep(CHECK_BROWSER_SLEEP)
            if port_file.is_file() and port_file.stat().st_size > 5:
                with port_file.open('r', encoding='utf-8') as f:
                    return proc, int(f.readline())

        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        self._logger.warning('Chrome headless failed to start:\n%s', log_path.read_text(encoding="utf-8"))
        # since the chrome never started, it's not going to be `stop`-ed so we
        # need to cleanup the directory here
        shutil.rmtree(self.user_data_dir, ignore_errors=True)

        raise unittest.SkipTest(f'Failed to detect chrome devtools port after {BROWSER_WAIT :.1f}s.')

    def _chrome_start(
            self,
            user_data_dir: str,
            touch_enabled: bool,
            headless=True,
            debug=False,
    ):
        headless_switches = {
            '--headless': '',
            '--disable-extensions': '',
            '--disable-background-networking' : '',
            '--disable-background-timer-throttling' : '',
            '--disable-backgrounding-occluded-windows': '',
            '--disable-renderer-backgrounding' : '',
            '--disable-breakpad': '',
            '--disable-client-side-phishing-detection': '',
            '--disable-crash-reporter': '',
            '--disable-dev-shm-usage': '',
            '--disable-namespace-sandbox': '',
            '--disable-translate': '',
            '--no-sandbox': '',
            '--disable-gpu': '',
            '--mute-audio': '',
        }
        switches = {
            # required for tours that use Youtube autoplay conditions (namely website_slides' "course_tour")
            '--autoplay-policy': 'no-user-gesture-required',
            '--disable-default-apps': '',
            '--disable-device-discovery-notifications': '',
            '--no-default-browser-check': '',
            '--remote-debugging-address': HOST,
            '--remote-debugging-port': str(self.remote_debugging_port),
            '--user-data-dir': user_data_dir,
            '--no-first-run': '',
            # FIXME: these next 2 flags are temporarily uncommented to allow client
            # code to manually run garbage collection. This is done as currently
            # the Chrome unit test process doesn't have access to its available
            # memory, so it cannot run the GC efficiently and may run out of memory
            # and crash. These should be re-commented when the process is correctly
            # configured.
            '--enable-precise-memory-info': '',
            '--js-flags': '--expose-gc',
        }
        if headless:
            switches.update(headless_switches)
        if touch_enabled:
            # enable Chrome's Touch mode, useful to detect touch capabilities using
            # "'ontouchstart' in window"
            switches['--touch-events'] = ''
        if debug is not False:
            switches['--auto-open-devtools-for-tabs'] = ''
            switches['--start-fullscreen'] = ''

        cmd = [self.executable]
        cmd += ['%s=%s' % (k, v) if v else k for k, v in switches.items()]
        url = 'about:blank'
        cmd.append(url)
        try:
            proc, devtools_port = self._spawn_chrome(cmd)
        except OSError:
            raise unittest.SkipTest("%s not found" % cmd[0])
        self._logger.info('Chrome pid: %s', proc.pid)
        self._logger.info('Chrome headless temporary user profile dir: %s', self.user_data_dir)

        return proc, devtools_port

    def _json_command(self, command, timeout=3):
        """Queries browser state using JSON

        Available commands:

        ``''``
            return list of tabs with their id
        ``list`` (or ``json/``)
            list tabs
        ``new``
            open a new tab
        :samp:`activate/{id}`
            activate a tab
        :samp:`close/{id}`
            close a tab
        ``version``
            get chrome and dev tools version
        ``protocol``
            get the full protocol
        """
        command = '/'.join(['json', command]).strip('/')
        url = werkzeug.urls.url_join('http://%s:%s/' % (HOST, self.devtools_port), command)
        self._logger.info("Issuing json command %s", url)
        delay = 0.1
        tries = 0
        failure_info = None
        message = None
        while timeout > 0:
            try:
                self.chrome.send_signal(0)
            except ProcessLookupError:
                message = 'Chrome crashed at startup'
                break
            try:
                r = requests.get(url, timeout=3)
                if r.ok:
                    return r.json()
            except requests.ConnectionError as e:
                failure_info = str(e)
                message = 'Connection Error while trying to connect to Chrome debugger'
            except requests.exceptions.ReadTimeout as e:
                failure_info = str(e)
                message = 'Connection Timeout while trying to connect to Chrome debugger'
                break

            time.sleep(delay)
            timeout -= delay
            delay = delay * 1.5
            tries += 1
        self._logger.error("%s after %s tries" % (message, tries))
        if failure_info:
            self._logger.info(failure_info)
        self.stop()
        raise unittest.SkipTest("Error during Chrome headless connection")

    def _open_websocket(self):
        version = self._json_command('version')
        self._logger.info('Browser version: %s', version['Browser'])

        start = time.time()
        while (time.time() - start) < 5.0:
            ws_url = next((
                target['webSocketDebuggerUrl']
                for target in self._json_command('')
                if target['type'] == 'page'
                if target['url'] == 'about:blank'
            ), None)
            if ws_url:
                break

            time.sleep(0.1)
        else:
            self.stop()
            raise unittest.SkipTest("Error during Chrome connection: never found 'page' target")

        self._logger.info('Websocket url found: %s', ws_url)
        ws = websocket.create_connection(ws_url, enable_multithread=True, suppress_origin=True)
        if ws.getstatus() != 101:
            raise unittest.SkipTest("Cannot connect to chrome dev tools")
        ws.settimeout(0.01)
        return ws

    def _receive(self, dbname):
        threading.current_thread().dbname = dbname
        # So CDT uses a streamed JSON-RPC structure, meaning a request is
        # {id, method, params} and eventually a {id, result | error} should
        # arrive the other way, however for events it uses "notifications"
        # meaning request objects without an ``id``, but *coming from the server
        while True: # or maybe until `self._result` is `done()`?
            try:
                msg = self.ws.recv()
                if not msg:
                    continue
                self._logger.debug('\n<- %s', msg)
            except websocket.WebSocketTimeoutException:
                continue
            except websocket.WebSocketConnectionClosedException as e:
                if not self._result.done():
                    del self.ws
                    self._result.set_exception(e)
                    for f in self._responses.values():
                        f.cancel()
                return
            except Exception as e:
                if isinstance(e, ConnectionResetError) and self._result.done():
                    return
                # if the socket is still connected something bad happened,
                # otherwise the client was just shut down
                if self.ws.connected:
                    self._result.set_exception(e)
                    raise
                self._result.cancel()
                return

            res = json.loads(msg)
            request_id = res.get('id')
            try:
                if request_id is None:
                    handler = self._handlers.get(res['method'])
                    if handler:
                        handler(**res['params'])
                else:
                    f = self._responses.pop(request_id, None)
                    if f:
                        if 'result' in res:
                            f.set_result(res['result'])
                        else:
                            f.set_exception(ChromeBrowserException(res['error']['message']))
            except Exception:
                msg = str(msg)
                if msg and len(msg) > 500:
                    msg = msg[:500] + '...'
                _logger.exception("While processing message %s", msg)

    def _websocket_request(self, method, *, params=None, timeout=10.0):
        assert threading.get_ident() != self._receiver.ident,\
            "_websocket_request must not be called from the consumer thread"
        if not hasattr(self, 'ws'):
            return None

        f = self._websocket_send(method, params=params, with_future=True)
        try:
            return f.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            raise TimeoutError(f'{method}({params or ""})')

    def _websocket_send(self, method, *, params=None, with_future=False):
        """send chrome devtools protocol commands through websocket

        If ``with_future`` is set, returns a ``Future`` for the operation.
        """
        if not hasattr(self, 'ws'):
            return None

        result = None
        request_id = next(self._request_id)
        if with_future:
            result = self._responses[request_id] = Future()
        payload = {'method': method, 'id': request_id}
        if params:
            payload['params'] = params
        self._logger.debug('\n-> %s', payload)
        self.ws.send(json.dumps(payload))
        return result

    def _handle_request_paused(self, **params):
        url = params['request']['url']
        if url.startswith(f'http://{HOST}'):
            cmd = 'Fetch.continueRequest'
            response = {}
        else:
            cmd = 'Fetch.fulfillRequest'
            response = self.test_case.fetch_proxy(url)
        try:
            self._websocket_send(cmd, params={'requestId': params['requestId'], **response})
        except websocket.WebSocketConnectionClosedException:
            pass
        except (BrokenPipeError, ConnectionResetError, OSError):
            # this can happen if the browser is closed. Just ignore it.
            _logger.info("Websocket error while handling request %s", params['request']['url'])

    def _handle_console(self, type, args=None, stackTrace=None, **kw): # pylint: disable=redefined-builtin
        # console formatting differs somewhat from Python's, if args[0] has
        # format modifiers that many of args[1:] get formatted in, missing
        # args are replaced by empty strings and extra args are concatenated
        # (space-separated)
        #
        # current version modifies the args in place which could and should
        # probably be improved
        if args:
            arg0, args = str(self._from_remoteobject(args[0])), args[1:]
        else:
            arg0, args = '', []
        formatted = [re.sub(r'%[%sdfoOc]', self.console_formatter(args), arg0)]
        # formatter consumes args it uses, leaves unformatted args untouched
        formatted.extend(str(self._from_remoteobject(arg)) for arg in args)
        message = ' '.join(formatted)
        stack = ''.join(self._format_stack({'type': type, 'stackTrace': stackTrace}))
        if stack:
            message += '\n' + stack

        log_type = type
        _logger = self._logger.getChild('browser')
        if self._result.done() and 'failed to fetch' in message.casefold():
            log_type = 'dir'
        _logger.log(
            self._TO_LEVEL.get(log_type, logging.INFO),
            "%s%s",
            "Error received after termination: " if self._result.done() else "",
            message # might still have %<x> characters
        )

        if log_type == 'error':
            self.had_failure = True
            if self._result.done():
                return
            if not self.error_checker or self.error_checker(message):
                self.take_screenshot()
                self._save_screencast()
                try:
                    self._result.set_exception(ChromeBrowserException(message))
                except CancelledError:
                    ...
                except InvalidStateError:
                    self._logger.warning(
                        "Trying to set result to failed (%s) but found the future settled (%s)",
                        message, self._result
                    )
        elif message == self.success_signal:
            @run
            def _get_heap():
                yield self._websocket_send("HeapProfiler.collectGarbage", with_future=True)
                r = yield self._websocket_send("Runtime.getHeapUsage", with_future=True)
                _logger.info("heap %d (allocated %d)", r['usedSize'], r['totalSize'])

            if self.test_case.allow_end_on_form:
                self._result.set_result(True)
                return

            @run
            def _check_form():
                node_id = 0

                with contextlib.suppress(Exception):
                    d = yield self._websocket_send('DOM.getDocument', params={'depth': 0}, with_future=True)
                    form = yield self._websocket_send("DOM.querySelector", params={
                        'nodeId': d['root']['nodeId'],
                        'selector': '.o_form_dirty',
                    }, with_future=True)
                    node_id = form['nodeId']

                if node_id:
                    self.take_screenshot("unsaved_form_")
                    msg = """\
Tour finished with an open form view in edition mode.

Form views in edition mode are automatically saved when the page is closed, \
which leads to stray network requests and inconsistencies."""
                    if self._result.done():
                        _logger.error("%s", msg)
                    else:
                        self._result.set_exception(ChromeBrowserException(msg))
                    return

                if not self._result.done():
                    self._result.set_result(True)
                elif self._result.exception() is None:
                    # if the future was already failed, we're happy,
                    # otherwise swap for a new failed
                    _logger.error("Tried to make the tour successful twice.")


    def _handle_exception(self, exceptionDetails, timestamp):
        message = exceptionDetails['text']
        exception = exceptionDetails.get('exception')
        if exception:
            message += str(self._from_remoteobject(exception))
        exceptionDetails['type'] = 'trace'  # fake this so _format_stack works
        stack = ''.join(self._format_stack(exceptionDetails))
        if stack:
            message += '\n' + stack

        if self._result.done():
            if 'failed to fetch' not in message.casefold():
                self._logger.getChild('browser').error(
                    "Exception received after termination: %s", message)
            return

        self.take_screenshot()
        self._save_screencast()
        try:
            self._result.set_exception(ChromeBrowserException(message))
        except CancelledError:
            ...
        except InvalidStateError:
            self._logger.warning(
                "Trying to set result to failed (%s) but found the future settled (%s)",
                message, self._result
            )

    def _handle_frame_stopped_loading(self, frameId):
        wait = self._frames.pop(frameId, None)
        if wait:
            wait()

    def _handle_screencast_frame(self, sessionId, data, metadata):
        frames_dir = self.screencasts_frames_dir
        if not frames_dir:
            return
        self._websocket_send('Page.screencastFrameAck', params={'sessionId': sessionId})
        outfile = os.path.join(frames_dir, 'frame_%05d.b64' % len(self.screencast_frames))
        try:
            with open(outfile, 'w') as f:
                f.write(data)
                self.screencast_frames.append({
                    'file_path': outfile,
                    'timestamp': metadata.get('timestamp')
                })
        except FileNotFoundError:
            self._logger.debug('Useless screencast frame skipped: %s', outfile)

    _TO_LEVEL = {
        'debug': logging.DEBUG,
        'log': logging.INFO,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'dir': logging.RUNBOT,
        # TODO: what do with
        # dir, dirxml, table, trace, clear, startGroup, startGroupCollapsed,
        # endGroup, assert, profile, profileEnd, count, timeEnd
    }

    def take_screenshot(self, prefix='sc_'):
        def handler(f):
            try:
                base_png = f.result(timeout=0)['data']
            except Exception as e:
                self._logger.runbot("Couldn't capture screenshot: %s", e)
                return
            if not base_png:
                self._logger.runbot("Couldn't capture screenshot: expected image data, got %r", base_png)
                return
            decoded = base64.b64decode(base_png, validate=True)
            save_test_file(type(self.test_case).__name__, decoded, prefix, logger=self._logger)

        self._logger.info('Asking for screenshot')
        f = self._websocket_send('Page.captureScreenshot', with_future=True)
        if f:
            f.add_done_callback(handler)
        return f

    def _save_screencast(self, prefix='failed'):
        # could be encododed with something like that
        #  ffmpeg -framerate 3 -i frame_%05d.png  output.mp4
        if not self.screencast_frames:
            self._logger.debug('No screencast frames to encode')
            return None

        self.stop_screencast()

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
            nb_frames = len(self.screencast_frames)
            concat_script_path = os.path.join(self.screencasts_dir, fname.replace('.mp4', '.txt'))
            with open(concat_script_path, 'w') as concat_file:
                for i in range(nb_frames):
                    frame_file_path = os.path.join(self.screencasts_frames_dir, self.screencast_frames[i]['file_path'])
                    end_time = time.time() if i == nb_frames - 1 else self.screencast_frames[i+1]['timestamp']
                    duration = end_time - self.screencast_frames[i]['timestamp']
                    concat_file.write("file '%s'\nduration %s\n" % (frame_file_path, duration))
                concat_file.write("file '%s'" % frame_file_path)  # needed by the concat plugin
            try:
                subprocess.run([ffmpeg_path, '-f', 'concat', '-safe', '0', '-i', concat_script_path, '-vf', 'pad=ceil(iw/2)*2:ceil(ih/2)*2', '-pix_fmt', 'yuv420p', '-g', '0', outfile], check=True)
            except subprocess.CalledProcessError:
                self._logger.error('Failed to encode screencast.')
                return
            self._logger.log(25, 'Screencast in: %s', outfile)
        else:
            outfile = outfile.strip('.mp4')
            shutil.move(self.screencasts_frames_dir, outfile)
            self._logger.runbot('Screencast frames in: %s', outfile)

    def start_screencast(self):
        assert self.screencasts_dir
        self._websocket_send('Page.startScreencast')

    def stop_screencast(self):
        self._websocket_send('Page.stopScreencast')

    def set_cookie(self, name, value, path, domain):
        params = {'name': name, 'value': value, 'path': path, 'domain': domain}
        self._websocket_request('Network.setCookie', params=params)
        return

    def delete_cookie(self, name, **kwargs):
        params = {k: v for k, v in kwargs.items() if k in ['url', 'domain', 'path']}
        params['name'] = name
        self._websocket_request('Network.deleteCookies', params=params)
        return

    def _wait_ready(self, ready_code=None, timeout=60):
        ready_code = ready_code or "document.readyState === 'complete'"
        self._logger.info('Evaluate ready code "%s"', ready_code)
        start_time = time.time()
        result = None
        while True:
            taken = time.time() - start_time
            if taken > timeout:
                break

            result = self._websocket_request('Runtime.evaluate', params={
                'expression': "try { %s } catch {}" % ready_code,
                'awaitPromise': True,
            }, timeout=timeout-taken)['result']

            if result == {'type': 'boolean', 'value': True}:
                time_to_ready = time.time() - start_time
                if taken > 2:
                    self._logger.info('The ready code tooks too much time : %s', time_to_ready)
                return True

        self.take_screenshot(prefix='sc_failed_ready_')
        self._logger.info('Ready code last try result: %s', result)
        return False

    def _wait_code_ok(self, code, timeout, error_checker=None):
        self.error_checker = error_checker
        self._logger.info('Evaluate test code "%s"', code)
        start = time.time()
        res = self._websocket_request('Runtime.evaluate', params={
            'expression': code,
            'awaitPromise': True,
        }, timeout=timeout)['result']
        if res.get('subtype') == 'error':
            raise ChromeBrowserException("Running code returned an error: %s" % res)

        err = ChromeBrowserException("failed")
        try:
            # if the runcode was a promise which took some time to execute,
            # discount that from the timeout
            if self._result.result(time.time() - start + timeout) and not self.had_failure:
                return
        except CancelledError:
            # regular-ish shutdown
            return
        except Exception as e:
            err = e

        self.take_screenshot()
        self._save_screencast()
        if isinstance(err, ChromeBrowserException):
            raise err

        if isinstance(err, concurrent.futures.TimeoutError):
            raise ChromeBrowserException('Script timeout exceeded') from err
        raise ChromeBrowserException("Unknown error") from err

    def navigate_to(self, url, wait_stop=False):
        self._logger.info('Navigating to: "%s"', url)
        nav_result = self._websocket_request('Page.navigate', params={'url': url}, timeout=20.0)
        self._logger.info("Navigation result: %s", nav_result)
        if wait_stop:
            frame_id = nav_result['frameId']
            e = threading.Event()
            self._frames[frame_id] = e.set
            self._logger.info('Waiting for frame %r to stop loading', frame_id)
            e.wait(10)

    def _from_remoteobject(self, arg):
        """ attempts to make a CDT RemoteObject comprehensible
        """
        objtype = arg['type']
        subtype = arg.get('subtype')
        if objtype == 'undefined':
            # the undefined remoteobject is literally just {type: undefined}...
            return 'undefined'
        elif objtype != 'object' or subtype not in (None, 'array'):
            # value is the json representation for json object
            # otherwise fallback on the description which is "a string
            # representation of the object" e.g. the traceback for errors, the
            # source for functions, ... finally fallback on the entire arg mess
            return arg.get('value', arg.get('description', arg))
        elif subtype == 'array':
            # apparently value is *not* the JSON representation for arrays
            # instead it's just Array(3) which is useless, however the preview
            # properties are the same as object which is useful (just ignore the
            # name which is the index)
            return '[%s]' % ', '.join(
                repr(p['value']) if p['type'] == 'string' else str(p['value'])
                for p in arg.get('preview', {}).get('properties', [])
                if re.match(r'\d+', p['name'])
            )
        # all that's left is type=object, subtype=None aka custom or
        # non-standard objects, print as TypeName(param=val, ...), sadly because
        # of the way Odoo widgets are created they all appear as Class(...)
        # nb: preview properties are *not* recursive, the value is *all* we get
        return '%s(%s)' % (
            arg.get('className') or 'object',
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

@lru_cache(1)
def _find_executable():
    system = platform.system()
    if system == 'Linux':
        for bin_ in ['google-chrome', 'chromium', 'chromium-browser', 'google-chrome-stable']:
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
        bins = [
            '%ProgramFiles%\\Google\\Chrome\\Application\\chrome.exe',
            '%ProgramFiles(x86)%\\Google\\Chrome\\Application\\chrome.exe',
            '%LocalAppData%\\Google\\Chrome\\Application\\chrome.exe',
        ]
        for bin_ in bins:
            bin_ = os.path.expandvars(bin_)
            if os.path.exists(bin_):
                return bin_

    raise unittest.SkipTest("Chrome executable not found")

class Opener(requests.Session):
    """
    Flushes and clears the current transaction when starting a request.

    This is likely necessary when we make a request to the server, as the
    request is made with a test cursor, which uses a different cache than this
    transaction.
    """
    def __init__(self, cr: BaseCursor):
        super().__init__()
        self.cr = cr

    def request(self, *args, **kwargs):
        self.cr.flush()
        self.cr.clear()
        return super().request(*args, **kwargs)


class Transport(xmlrpclib.Transport):
    """ see :class:`Opener` """
    def __init__(self, cr: BaseCursor):
        self.cr = cr
        super().__init__()

    def request(self, *args, **kwargs):
        self.cr.flush()
        self.cr.clear()
        test = module.current_test
        if test:
            check = test.http_request_strict_check
            test.http_request_strict_check = False
        res = super().request(*args, **kwargs)
        if test:
            test.http_request_strict_check = check
        return res


class JsonRpcException(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class HttpCase(TransactionCase):
    """ Transactional HTTP TestCase with url_open and Chrome headless helpers. """
    registry_test_mode = True
    browser = None
    browser_size = '1366x768'
    touch_enabled = False
    allow_end_on_form = False

    _logger: logging.Logger = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if cls.registry_test_mode:
            cls.registry.enter_test_mode(cls.cr, not hasattr(cls, 'readonly_enabled') or cls.readonly_enabled)
            cls.addClassCleanup(cls.registry.leave_test_mode)

        ICP = cls.env['ir.config_parameter']
        ICP.set_param('web.base.url', cls.base_url())
        ICP.env.flush_all()
        # v8 api with correct xmlrpc exception handling.
        cls.xmlrpc_url = f'{cls.base_url()}/xmlrpc/2/'
        cls._logger = logging.getLogger('%s.%s' % (cls.__module__, cls.__name__))

    @classmethod
    def base_url(cls):
        return f"http://{HOST}:{cls.http_port():d}"

    @classmethod
    def http_port(cls):
        if odoo.service.server.server is None:
            return None
        return odoo.service.server.server.httpd.server_port

    def setUp(self):
        super().setUp()

        self._logger = self._logger.getChild(self._testMethodName)

        self.xmlrpc_common = xmlrpclib.ServerProxy(self.xmlrpc_url + 'common', transport=Transport(self.cr))
        self.xmlrpc_db = xmlrpclib.ServerProxy(self.xmlrpc_url + 'db', transport=Transport(self.cr))
        self.xmlrpc_object = xmlrpclib.ServerProxy(self.xmlrpc_url + 'object', transport=Transport(self.cr), use_datetime=True)
        # setup an url opener helper
        self.opener = Opener(self.cr)
        self.opener.cookies[TEST_CURSOR_COOKIE_NAME] = self.canonical_tag
        # some test like test_webhook_send_and_receive may have a request that timeout, is not waited and causes errors in following tests.
        # this shouldn't be possible in master thanks to the global lock but lets wait for remaining requests in all cases in stable.
        self.addCleanup(self._wait_remaining_requests)

    def parse_http_location(self, location):
        """ Parse a Location http header typically found in 201/3xx
        responses, return the corresponding Url object. The scheme/host
        are taken from ``base_url()`` in case they are missing from the
        header.

        https://urllib3.readthedocs.io/en/stable/reference/urllib3.util.html#urllib3.util.Url
        """
        if not location:
            return Url()
        base_url = parse_url(self.base_url())
        url = parse_url(location)
        return Url(
            scheme=url.scheme or base_url.scheme,
            auth=url.auth or base_url.auth,
            host=url.host or base_url.host,
            port=url.port or base_url.port,
            path=url.path,
            query=url.query,
            fragment=url.fragment,
        )

    def assertURLEqual(self, test_url, truth_url, message=None):
        """ Assert that two URLs are equivalent. If any URL is missing
        a scheme and/or host, assume the same scheme/host as base_url()
        """
        self.assertEqual(
            self.parse_http_location(test_url).url,
            self.parse_http_location(truth_url).url,
            message,
        )

    def url_open(self, url, data=None, files=None, timeout=12, headers=None, allow_redirects=True, head=False):
        if url.startswith('/'):
            url = self.base_url() + url
        if head:
            return self.opener.head(url, data=data, files=files, timeout=timeout, headers=headers, allow_redirects=False)
        if data or files:
            return self.opener.post(url, data=data, files=files, timeout=timeout, headers=headers, allow_redirects=allow_redirects)
        return self.opener.get(url, timeout=timeout, headers=headers, allow_redirects=allow_redirects)

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

    def logout(self, keep_db=True):
        self.session.logout(keep_db=keep_db)
        odoo.http.root.session_store.save(self.session)

    def authenticate(self, user, password, browser: ChromeBrowser = None):
        if getattr(self, 'session', None):
            odoo.http.root.session_store.delete(self.session)

        self.session = session = odoo.http.root.session_store.new()
        session.update(odoo.http.get_default_session(), db=get_db_name())
        session.context['lang'] = odoo.http.DEFAULT_LANG

        if user: # if authenticated
            # Flush and clear the current transaction.  This is useful, because
            # the call below opens a test cursor, which uses a different cache
            # than this transaction.
            self.cr.flush()
            self.cr.clear()

            def patched_check_credentials(self, credential, env):
                return {'uid': self.id, 'auth_method': 'password', 'mfa': 'default'}

            # patching to speedup the check in case the password is hashed with many hashround + avoid to update the password
            with patch('odoo.addons.base.models.res_users.Users._check_credentials', new=patched_check_credentials):
                credential = {'login': user, 'password': password, 'type': 'password'}
                auth_info = self.registry['res.users'].authenticate(session.db, credential, {'interactive': False})
            uid = auth_info['uid']
            env = api.Environment(self.cr, uid, {})
            session.uid = uid
            session.login = user
            session.session_token = uid and security.compute_session_token(session, env)
            session.context = dict(env['res.users'].context_get())

        odoo.http.root.session_store.save(session)
        # Reset the opener: turns out when we set cookies['foo'] we're really
        # setting a cookie on domain='' path='/'.
        #
        # But then our friendly neighborhood server might set a cookie for
        # domain='localhost' path='/' (with the same value) which is considered
        # a *different* cookie following ours rather than the same.
        #
        # When we update our cookie, it's done in-place, so the server-set
        # cookie is still present and (as it follows ours and is more precise)
        # very likely to still be used, therefore our session change is ignored.
        #
        # An alternative would be to set the cookie to None (unsetting it
        # completely) or clear-ing session.cookies.
        self.opener = Opener(self.cr)
        self.opener.cookies['session_id'] = session.sid
        self.opener.cookies[TEST_CURSOR_COOKIE_NAME] = self.http_request_key
        if browser:
            self._logger.info('Setting session cookie in browser')
            browser.set_cookie('session_id', session.sid, '/', HOST)
            browser.set_cookie(TEST_CURSOR_COOKIE_NAME, self.http_request_key, '/', HOST)

        return session

    def fetch_proxy(self, url):
        """
            This method is called every time a request is made from the chrome browser outside the local network
            Returns a response that will be sent to the browser to simulate the external request.
        """

        if 'https://fonts.googleapis.com/css' in url:
            _logger.info('External chrome request during tests: Return empty file for %s', url)
            return self.make_fetch_proxy_response('')  # return empty css file, we don't care

        _logger.info('External chrome request during tests: returning 404 for %s', url)
        return {
                'body': '',
                'responseCode': 404,
                'responseHeaders': [],
            }

    def make_fetch_proxy_response(self, content, code=200):
        if isinstance(content, str):
            content = content.encode()
        return {
                'body': base64.b64encode(content).decode(),
                'responseCode': code,
                'responseHeaders': [
                    {'name': 'access-control-allow-origin', 'value': '*'},
                    {'name': 'cache-control', 'value': 'public, max-age=10000'},
                ],
            }

    def browser_js(self, url_path, code, ready='', login=None, timeout=60, cookies=None, error_checker=None, watch=False, success_signal=DEFAULT_SUCCESS_SIGNAL, debug=False, cpu_throttling=None, **kw):
        """ Test JavaScript code running in the browser.

        To signal success test do: `console.log()` with the expected `success_signal`. Default is "test successful"
        To signal test failure raise an exception or call `console.error` with a message.
        Test will stop when a failure occurs if `error_checker` is not defined or returns `True` for this message

        :param string url_path: URL path to load the browser page on
        :param string code: JavaScript code to be executed
        :param string ready: JavaScript object to wait for before proceeding with the test
        :param string login: logged in user which will execute the test. e.g. 'admin', 'demo'
        :param int timeout: maximum time to wait for the test to complete (in seconds). Default is 60 seconds
        :param dict cookies: dictionary of cookies to set before loading the page
        :param error_checker: function to filter failures out.
            If provided, the function is called with the error log message, and if it returns `False` the log is ignored and the test continue
            If not provided, every error log triggers a failure
        :param bool watch: open a new browser window to watch the test execution
        :param string success_signal: string signal to wait for to consider the test successful
        :param bool debug: automatically open a fullscreen Chrome window with opened devtools and a debugger breakpoint set at the start of the tour.
            The tour is ran with the `debug=assets` query parameter. When an error is thrown, the debugger stops on the exception.
        :param int cpu_throttling: CPU throttling rate as a slowdown factor (1 is no throttle, 2 is 2x slowdown, etc)
        """
        if not self.env.registry.loaded:
            self._logger.warning('HttpCase test should be in post_install only')

        # increase timeout if coverage is running
        if any(f.filename.endswith('/coverage/execfile.py') for f in inspect.stack()  if f.filename):
            timeout = timeout * 1.5

        if debug is not False:
            watch = True
            timeout = 1e6
        if watch:
            self._logger.warning('watch mode is only suitable for local testing')

        browser = ChromeBrowser(self, headless=not watch, success_signal=success_signal, debug=debug)
        try:
            self.http_request_key = self.canonical_tag + '_browser_js'
            self.authenticate(login, login, browser=browser)
            self.http_request_strict_check = True
            # Flush and clear the current transaction.  This is useful in case
            # we make requests to the server, as these requests are made with
            # test cursors, which uses different caches than this transaction.
            self.cr.flush()
            self.cr.clear()
            url = werkzeug.urls.url_join(self.base_url(), url_path)
            if watch:
                parsed = werkzeug.urls.url_parse(url)
                qs = parsed.decode_query()
                qs['watch'] = '1'
                if debug is not False:
                    qs['debug'] = "assets"
                url = parsed.replace(query=werkzeug.urls.url_encode(qs)).to_url()
            self._logger.info('Open "%s" in browser', url)

            if browser.screencasts_dir:
                self._logger.info('Starting screencast')
                browser.start_screencast()
            if cookies:
                for name, value in cookies.items():
                    browser.set_cookie(name, value, '/', HOST)

            cpu_throttling_os = os.environ.get('ODOO_BROWSER_CPU_THROTTLING') # used by dedicated runbot builds
            cpu_throttling = int(cpu_throttling_os) if cpu_throttling_os else cpu_throttling

            if cpu_throttling:
                assert 1 <= cpu_throttling <= 50  # arbitrary upper limit
                timeout *= cpu_throttling  # extend the timeout as test will be slower to execute
                _logger.log(
                    logging.INFO if cpu_throttling_os else logging.WARNING,
                    'CPU throttling mode is only suitable for local testing - ' \
                    'Throttling browser CPU to %sx slowdown and extending timeout to %s sec', cpu_throttling, timeout)
                browser._websocket_request('Emulation.setCPUThrottlingRate', params={'rate': cpu_throttling})

            browser.navigate_to(url, wait_stop=not bool(ready))

            # Needed because tests like test01.js (qunit tests) are passing a ready
            # code = ""
            self.assertTrue(browser._wait_ready(ready), 'The ready "%s" code was always falsy' % ready)

            error = False
            try:
                browser._wait_code_ok(code, timeout, error_checker=error_checker)
            except ChromeBrowserException as chrome_browser_exception:
                error = chrome_browser_exception
            if error:  # dont keep initial traceback, keep that outside of except
                if code:
                    message = 'The test code "%s" failed' % code
                else:
                    message = "Some js test failed"
                self.fail('%s\n\n%s' % (message, error))

        finally:
            browser.stop()
            self._wait_remaining_requests()
            self.http_request_key = self.canonical_tag
            self.opener.cookies[TEST_CURSOR_COOKIE_NAME] = self.http_request_key

    def start_tour(self, url_path, tour_name, step_delay=None, **kwargs):
        """Wrapper for `browser_js` to start the given `tour_name` with the
        optional delay between steps `step_delay`. Other arguments from
        `browser_js` can be passed as keyword arguments."""
        options = {
            'stepDelay': step_delay or 0,
            'keepWatchBrowser': kwargs.get('watch', False),
            'debug': kwargs.get('debug', False),
            'startUrl': url_path,
            'delayToCheckUndeterminisms': kwargs.pop('delay_to_check_undeterminisms', int(os.getenv("ODOO_TOUR_DELAY_TO_CHECK_UNDETERMINISMS", "0")) or 0),
        }
        code = kwargs.pop('code', f"odoo.startTour({tour_name!r}, {json.dumps(options)})")
        ready = kwargs.pop('ready', f"odoo.isTourReady({tour_name!r})")
        timeout = kwargs.pop('timeout', 60)

        if options["delayToCheckUndeterminisms"] > 0:
            timeout = timeout + 1000 * options["delayToCheckUndeterminisms"]
            _logger.runbot("Tour %s is launched with mode: check for undeterminisms.", tour_name)
        return self.browser_js(url_path=url_path, code=code, ready=ready, timeout=timeout, success_signal="tour succeeded", **kwargs)

    def profile(self, **kwargs):
        """
        for http_case, also patch _get_profiler_context_manager in order to profile all requests
        """
        sup = super()
        _profiler = sup.profile(**kwargs)
        def route_profiler(request):
            _route_profiler = sup.profile(description=request.httprequest.full_path, db=_profiler.db)
            _profiler.sub_profilers.append(_route_profiler)
            return _route_profiler
        return profiler.Nested(_profiler, patch('odoo.http.Request._get_profiler_context_manager', route_profiler))

    def get_method_additional_tags(self, test_method):
        """
        guess if the test_methods is a tour and adds an `is_tour` tag on the test
        """
        additional_tags = super().get_method_additional_tags(test_method)
        if odoo.tools.config['test_tags'] and 'is_tour' in odoo.tools.config['test_tags']:
            method_source = inspect.getsource(test_method)
            if 'self.start_tour' in method_source:
                additional_tags.append('is_tour')
        return additional_tags

    def make_jsonrpc_request(self, route, params=None, headers=None):
        """Make a JSON-RPC request to the server.

        :param str route: the route to request
        :param dict params: the parameters to send
        :raises requests.HTTPError: if one occurred
        :raises JsonRpcException: if the response contains an error
        :return: The 'result' key from the response if any.
        """
        data = json.dumps({
            'id': 0,
            'jsonrpc': '2.0',
            'method': 'call',
            'params': params or {},
        }).encode()
        headers = headers or {}
        headers['Content-Type'] = 'application/json'
        response = self.url_open(route, data, headers=headers)
        response.raise_for_status()
        decoded_response = response.json()
        if 'result' in decoded_response:
            return decoded_response['result']
        if 'error' in decoded_response:
            raise JsonRpcException(
                code=decoded_response['error']['code'],
                message=decoded_response['error']['data']['name']
            )


def no_retry(arg):
    """Disable auto retry on decorated test method or test class"""
    arg._retry = False
    return arg


def users(*logins):
    """ Decorate a method to execute it once for each given user. """
    @decorator
    def _users(func, *args, **kwargs):
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
                self.env.invalidate_all()
        finally:
            self.uid = old_uid

    return _users


@decorator
def warmup(func, *args, **kwargs):
    """
    Stabilize assertQueries and assertQueryCount assertions.

    Reset the cache to a stable state by flushing pending changes and
    invalidating the cache.

    Warmup the ormcaches by running the decorated function an extra time
    before the actual test runs. The extra execution ignores
    assertQueries and assertQueryCount assertions, it also discardes all
    changes but the ormcaches ones.
    """
    self = args[0]
    self.env.flush_all()
    self.env.invalidate_all()
    # run once to warm up the caches
    self.warm = False
    with contextlib.closing(self.cr.savepoint(flush=False)):
        func(*args, **kwargs)
        self.env.flush_all()
    # run once for real
    self.env.invalidate_all()
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


def tagged(*tags):
    """A decorator to tag BaseCase objects.

    Tags are stored in a set that can be accessed from a 'test_tags' attribute.

    A tag prefixed by '-' will remove the tag e.g. to remove the 'standard' tag.

    By default, all Test classes from odoo.tests.common have a test_tags
    attribute that defaults to 'standard' and 'at_install'.

    When using class inheritance, the tags ARE inherited.
    """
    include = {t for t in tags if not t.startswith('-')}
    exclude = {t[1:] for t in tags if t.startswith('-')}

    def tags_decorator(obj):
        obj.test_tags = (getattr(obj, 'test_tags', set()) | include) - exclude
        at_install = 'at_install' in obj.test_tags
        post_install = 'post_install' in obj.test_tags
        if not (at_install ^ post_install):
            _logger.warning('A tests should be either at_install or post_install, which is not the case of %r', obj)
        return obj
    return tags_decorator


class freeze_time:
    """ Object to replace the freezegun in Odoo test suites
        It properly handles the test classes decoration
        Also, it can be used like the usual method decorator or context manager
    """

    def __init__(self, time_to_freeze):
        self.freezer = None
        self.time_to_freeze = time_to_freeze

    def __call__(self, func):
        if isinstance(func, MetaCase):
            func.freeze_time = self.time_to_freeze
            return func
        else:
            if freezegun:
                return freezegun.freeze_time(self.time_to_freeze)(func)
            else:
                _logger.warning("freezegun package missing")

    def __enter__(self):
        if freezegun:
            self.freezer = freezegun.freeze_time(self.time_to_freeze)
            return self.freezer.start()
        else:
            _logger.warning("freezegun package missing")

    def __exit__(self, *args):
        if self.freezer:
            self.freezer.stop()
