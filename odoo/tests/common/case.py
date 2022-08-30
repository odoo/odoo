import difflib
import inspect
import itertools
import logging
import os
import pprint
import sys
import threading
import time
import unittest
import warnings
from abc import abstractmethod
from contextlib import contextmanager, ExitStack
from itertools import zip_longest as izip_longest
from unittest.mock import patch
from xmlrpc import client as xmlrpclib

import werkzeug.urls
import werkzeug.wrappers
from lxml import etree, html

import odoo
from odoo import api
from odoo.exceptions import AccessError
from odoo.models import BaseModel
from odoo.modules.registry import Registry
from odoo.service import security
from odoo.sql_db import Cursor
from odoo.tools import float_compare, profiler, lower_logging

from .cdp import ChromeBrowser, ChromeBrowserException
from .openers import RequestsOpener, TestClientOpener, Transport
from .utils import base_url, get_db_name, HOST
from ..runner import OdooTestResult

_logger = logging.getLogger(__name__)
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


class BaseCase(unittest.TestCase):
    """ Subclass of TestCase for Odoo-specific code. This class is abstract and
    expects self.registry, self.cr and self.uid to be initialized by subclasses.
    """
    # TODO: these are required by some methods, but not required by them,
    #       shouldn't these methods be moved down the inheritance tree?
    registry: Registry = None
    env: api.Environment = None
    cr: Cursor = None

    if sys.version_info < (3, 8):
        # Partial backport of bpo-24412, merged in CPython 3.8
        _class_cleanups = []

        @classmethod
        def addClassCleanup(cls, function, *args, **kwargs):
            """Same as addCleanup, except the cleanup items are called even if
            setUpClass fails (unlike tearDownClass). Backport of bpo-24412."""
            cls._class_cleanups.append((function, args, kwargs))

        @classmethod
        def doClassCleanups(cls):
            """Execute all class cleanup functions. Normally called for you after tearDownClass.
            Backport of bpo-24412."""
            cls.tearDown_exceptions = []
            while cls._class_cleanups:
                function, args, kwargs = cls._class_cleanups.pop()
                try:
                    function(*args, **kwargs)
                except Exception as exc:
                    cls.tearDown_exceptions.append(sys.exc_info())

    longMessage = True      # more verbose error message by default: https://www.odoo.com/r/Vmh
    warm = True             # False during warm-up phase (see :func:`warmup`)

    def __init_subclass__(cls):
        super().__init_subclass__()
        if cls.__module__.startswith('odoo.addons.'):
            cls.test_tags = {'standard', 'at_install'}
            cls.test_module = cls.__module__.split('.')[2]
            cls.test_class = cls.__name__
            cls.test_sequence = 0

    def __init__(self, methodName='runTest'):
        super().__init__(methodName)
        self.addTypeEqualityFunc(etree._Element, self.assertTreesEqual)
        self.addTypeEqualityFunc(html.HtmlElement, self.assertTreesEqual)

    def run(self, result: OdooTestResult = None):
        testMethod = getattr(self, self._testMethodName)

        if getattr(testMethod, '_retry', True) and getattr(self, '_retry', True):
            tests_run_count = int(os.environ.get('ODOO_TEST_FAILURE_RETRIES', 0)) + 1
        else:
            tests_run_count = 1
            _logger.info('Auto retry disabled for %s', self)

        failure = False
        for retry in range(tests_run_count):
            if retry:
                _logger.runbot(f'Retrying a failed test: {self}')
            if retry < tests_run_count-1:
                with warnings.catch_warnings(), \
                        result.soft_fail(), \
                        lower_logging(25, logging.INFO) as quiet_log:
                    super().run(result)
                    failure = result.had_failure or quiet_log.had_error_log
            else:  # last try
                super().run(result)
            if not failure:
                break

    def shortDescription(self):
        return None

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
        """ Enable the effects of group 'base.group_no_one'; mainly useful with :class:`Form`. """
        origin_user_has_groups = BaseModel.user_has_groups

        def user_has_groups(self, groups):
            group_set = set(groups.split(','))
            if '!base.group_no_one' in group_set:
                return False
            elif 'base.group_no_one' in group_set:
                group_set.remove('base.group_no_one')
                return not group_set or origin_user_has_groups(self, ','.join(group_set))
            return origin_user_has_groups(self, groups)

        with patch('odoo.models.BaseModel.user_has_groups', user_has_groups):
            yield

    @contextmanager
    def _assertRaises(self, exception, *, msg=None):
        """ Context manager that clears the environment upon failure. """
        with ExitStack() as init:
            if self.env:
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

    if sys.version_info < (3, 10):
        # simplified backport of assertNoLogs()
        @contextmanager
        def assertNoLogs(self, logger: str, level: str):
            # assertLogs ensures there is at least one log record when
            # exiting the context manager. We insert one dummy record just
            # so we pass that silly test while still capturing the logs.
            with self.assertLogs(logger, level) as capture:
                logging.getLogger(logger).log(getattr(logging, level), "Dummy log record")
                yield
                if len(capture.output) > 1:
                    raise self.failureException(f"Unexpected logs found: {capture.output[1:]}")

    @contextmanager
    def assertQueries(self, expected, flush=True):
        """ Check the queries made by the current cursor. ``expected`` is a list
        of strings representing the expected queries being made. Query strings
        are matched against each other, ignoring case and whitespaces.
        """
        Cursor_execute = Cursor.execute
        actual_queries = []

        def execute(self, query, params=None, log_exceptions=None):
            actual_queries.append(query)
            return Cursor_execute(self, query, params, log_exceptions)

        def get_unaccent_wrapper(cr):
            return lambda x: x

        if flush:
            self.env.flush_all()
            self.env.cr.flush()

        with patch('odoo.sql_db.Cursor.execute', execute):
            with patch('odoo.osv.expression.get_unaccent_wrapper', get_unaccent_wrapper):
                yield actual_queries
                if flush:
                    self.env.flush_all()
                    self.env.cr.flush()

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
            # flush before and after during warmup, in order to reproduce the
            # same operations, otherwise the caches might not be ready!
            if flush:
                self.env.flush_all()
                self.env.cr.flush()
            yield
            if flush:
                self.env.flush_all()
                self.env.cr.flush()

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
                    currency_field_name = record._fields[field_name].get_currency_field(record)
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
        if original:
            original = _normalize_arch_for_assert(original, parser)
        if expected:
            expected = _normalize_arch_for_assert(expected, parser)
        self.assertEqual(original, expected)

    def assertXMLEqual(self, original, expected):
        return self._assertXMLEqual(original, expected)

    def assertHTMLEqual(self, original, expected):
        return self._assertXMLEqual(original, expected, 'html')

    def profile(self, **kwargs):
        test_method = getattr(self, '_testMethodName', 'Unknown test method')
        if not hasattr(self, 'profile_session'):
            self.profile_session = profiler.make_session(test_method)
        return profiler.Profiler(
            description='%s uid:%s %s' % (test_method, self.env.user.id, 'warm' if self.warm else 'cold'),
            db=self.env.cr.dbname,
            profile_session=self.profile_session,
            **kwargs)

class SingleTransactionCase(BaseCase):
    """ TestCase in which all test methods are run in the same transaction,
    but the tests are not isolated: the transaction is started with the first
    test method and rolled back at the end of the last.
    """
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.registry = odoo.registry(get_db_name())
        cls.addClassCleanup(cls.registry.reset_changes)
        cls.addClassCleanup(cls.registry.clear_caches)

        cls.cr = cls.registry.cursor()
        cls.addClassCleanup(cls.cr.close)

        cls.env = api.Environment(cls.cr, odoo.SUPERUSER_ID, {})

    def setUp(self):
        super().setUp()
        self.env.flush_all()


savepoint_seq = itertools.count()
class TransactionCase(SingleTransactionCase):
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
    def setUp(self):
        super().setUp()

        # restore environments after the test to avoid invoking flush() with an
        # invalid environment (inexistent user id) from another test
        envs = self.env.all.envs
        self.addCleanup(envs.update, list(envs))
        self.addCleanup(envs.clear)

        self.addCleanup(self.registry.clear_caches)
        self.addCleanup(self.env.clear)

        self._savepoint_id = next(savepoint_seq)
        self.cr.execute('SAVEPOINT test_%d' % self._savepoint_id)
        self.addCleanup(self.cr.execute, 'ROLLBACK TO SAVEPOINT test_{0}; RELEASE SAVEPOINT test_{0}'.format(self._savepoint_id))

        self.patch(self.registry['res.partner'], '_get_gravatar_image', lambda *a: False)


class SavepointCase(TransactionCase):
    @classmethod
    def __init_subclass__(cls):
        super().__init_subclass__()
        warnings.warn(
            "15.0: deprecated class SavepointCase has been merged into TransactionCase",
            DeprecationWarning, stacklevel=2,
        )


class QueryCase(TransactionCase):
    _logger: logging.Logger = None
    session = None

    @abstractmethod
    def Opener(self, cr: Cursor):
        raise NotImplementedError

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ICP = cls.env['ir.config_parameter']
        ICP.set_param('web.base.url', cls.base_url())
        ICP.env.flush_all()

        cls._logger = logging.getLogger('%s.%s' % (cls.__module__, cls.__name__))

    def setUp(self):
        super().setUp()
        self.registry.enter_test_mode(self.cr)
        self.addCleanup(self.registry.leave_test_mode)

        # setup an url opener helper
        self.opener = self.Opener(self.cr)

    def url_open(self, url, data=None, files=None, timeout=12, headers=None, allow_redirects=True, head=False):
        if url.startswith('/'):
            url = self.base_url() + url
        if head:
            return self.opener.head(url, timeout=timeout, headers=headers, allow_redirects=False)
        if data or files:
            return self.opener.post(url, data=data, files=files, timeout=timeout, headers=headers, allow_redirects=allow_redirects)
        return self.opener.get(url, timeout=timeout, headers=headers, allow_redirects=allow_redirects)

    def logout(self, keep_db=True):
        if self.session:
            self.session.logout(keep_db=keep_db)
            odoo.http.root.session_store.save(self.session)

    def authenticate(self, user, password):
        if self.session:
            odoo.http.root.session_store.delete(self.session)

        self.session = session = odoo.http.root.session_store.new()
        session.update(odoo.http.DEFAULT_SESSION, db=get_db_name())
        session.context['lang'] = odoo.http.DEFAULT_LANG

        if user: # if authenticated
            # Flush and clear the current transaction.  This is useful, because
            # the call below opens a test cursor, which uses a different cache
            # than this transaction.
            self.cr.flush()
            self.cr.clear()
            uid = self.registry['res.users'].authenticate(session.db, user, password, {'interactive': False})
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
        self.opener = self.Opener(self.cr)
        self.opener.cookies['session_id'] = session.sid

        return session

    @classmethod
    def base_url(cls):
        return base_url().to_url()

class WsgiCase(QueryCase):
    Opener = TestClientOpener

class HttpCase(QueryCase):
    """ Transactional HTTP TestCase with url_open and Chrome headless helpers. """
    browser = None
    browser_size = '1366x768'
    touch_enabled = False
    allow_end_on_form = False

    Opener = RequestsOpener

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # v8 api with correct xmlrpc exception handling.
        cls.xmlrpc_url = f'{cls.base_url()}/xmlrpc/2/'

    def setUp(self):
        super().setUp()
        self.xmlrpc_common = xmlrpclib.ServerProxy(self.xmlrpc_url + 'common', transport=Transport(self.cr))
        self.xmlrpc_db = xmlrpclib.ServerProxy(self.xmlrpc_url + 'db', transport=Transport(self.cr))
        self.xmlrpc_object = xmlrpclib.ServerProxy(self.xmlrpc_url + 'object', transport=Transport(self.cr))

    def authenticate(self, user, password):
        session = super().authenticate(user, password)
        if self.browser:
            self._logger.info('Setting session cookie in browser')
            self.browser.set_cookie('session_id', session.sid, '/', HOST)
        return session

    @classmethod
    def start_browser(cls):
        # start browser on demand
        if cls.browser is None:
            cls.browser = ChromeBrowser(cls)
            cls.addClassCleanup(cls.terminate_browser)

    @classmethod
    def terminate_browser(cls):
        if cls.browser:
            cls.browser.stop()
            cls.browser = None

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

    def browser_js(self, url_path, code, ready='', login=None, timeout=60, cookies=None, watch=False, **kw):
        """ Test js code running in the browser
        - optionnally log as 'login'
        - load page given by url_path
        - wait for ready object to be available
        - eval(code) inside the page
        - open another chrome window to watch code execution if watch is True

        To signal success test do: console.log('test successful')
        To signal test failure raise an exception or call console.error
        """

        if not self.env.registry.loaded:
            self._logger.warning('HttpCase test should be in post_install only')

        # increase timeout if coverage is running
        if any(f.filename.endswith('/coverage/execfile.py') for f in inspect.stack()  if f.filename):
            timeout = timeout * 1.5

        self.start_browser()
        if watch and self.browser.dev_tools_frontend_url:
            _logger.warning('watch mode is only suitable for local testing - increasing tour timeout to 3600')
            timeout = max(timeout*10, 3600)
            debug_front_end = f'http://127.0.0.1:{self.browser.devtools_port}{self.browser.dev_tools_frontend_url}'
            self.browser._chrome_without_limit([self.browser.executable, debug_front_end])
            time.sleep(3)
        try:
            self.authenticate(login, login)
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
                url = parsed.replace(query=werkzeug.urls.url_encode(qs)).to_url()
            self._logger.info('Open "%s" in browser', url)

            if self.browser.screencasts_dir:
                self._logger.info('Starting screencast')
                self.browser.start_screencast()
            if cookies:
                for name, value in cookies.items():
                    self.browser.set_cookie(name, value, '/', HOST)
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
                self.fail('%s\n\n%s' % (message, error))

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
        ready = kwargs.pop('ready', "odoo.__DEBUG__.services['web_tour.tour'].tours['%s'].ready" % tour_name)
        return self.browser_js(url_path=url_path, code=code, ready=ready, **kwargs)


# kept for backward compatibility
class HttpSavepointCase(HttpCase):
    @classmethod
    def __init_subclass__(cls):
        super().__init_subclass__()
        warnings.warn(
            "15.0: deprecated class HttpSavepointCase has been merged into HttpCase",
            DeprecationWarning, stacklevel=2,
        )
