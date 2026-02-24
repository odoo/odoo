# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import requests
import threading

from odoo.http import route, Controller, request
from odoo.tests.common import HttpCase, tagged, ChromeBrowser, TEST_CURSOR_COOKIE_NAME, Like, SingleTransactionCase, TransactionCase
from odoo.tools import config
from unittest.mock import patch

_logger = logging.getLogger(__name__)


@tagged('at_install', '-post_install')
class TestSingleTransactionCase(SingleTransactionCase):
    """
    Check the whole-class transaction behavior of SingleTransactionCase.
    """

    def test_00(self):
        """ Create a partner. """
        self.env['res.partner'].create({'name': 'test_per_class_teardown_partner'})
        partners = self.env['res.partner'].search([('name', '=', 'test_per_class_teardown_partner')])
        self.assertEqual(1, len(partners), "Test partner not found.")

    def test_01(self):
        """ Find the created partner. """
        partners = self.env['res.partner'].search([('name', '=', 'test_per_class_teardown_partner')])
        self.assertEqual(1, len(partners), "Test partner not found.")

    def test_20a(self):
        """ Create a partner with a XML ID """
        pid, _ = self.env['res.partner'].name_create('Mr Blue')
        self.env['ir.model.data'].create({'name': 'test_partner_blue',
                                          'module': 'base',
                                          'model': 'res.partner',
                                          'res_id': pid})

    def test_20b(self):
        """ Resolve xml id with ref() and browse_ref() """
        xid = 'base.test_partner_blue'
        partner = self.env.ref(xid)
        pid = self.ref(xid)
        self.assertTrue(pid, "ref() should resolve xid to database ID")
        self.assertEqual(pid, partner.id, "ref() is not consistent with env.ref()")
        partner2 = self.browse_ref(xid)
        self.assertEqual(partner, partner2, "browse_ref() should resolve xid to browse records")


@tagged('at_install', '-post_install')
class TestTransactionCase(TransactionCase):
    """
    Check the per-method transaction behavior of TransactionCase.
    """

    def test_00(self):
        """ Create a partner. """
        partners = self.env['res.partner'].search([('name', '=', 'test_per_class_teardown_partner')])
        self.assertEqual(0, len(partners), "Test partner found.")
        self.env['res.partner'].create({'name': 'test_per_class_teardown_partner'})
        partners = self.env['res.partner'].search([('name', '=', 'test_per_class_teardown_partner')])
        self.assertEqual(1, len(partners), "Test partner not found.")

    def test_01(self):
        """ Don't find the created partner. """
        partners = self.env['res.partner'].search([('name', '=', 'test_per_class_teardown_partner')])
        self.assertEqual(0, len(partners), "Test partner found.")

    def test_20a(self):
        """ Create a partner with a XML ID then resolve xml id with ref() and browse_ref() """
        pid, _ = self.env['res.partner'].name_create('Mr Yellow')
        self.env['ir.model.data'].create({'name': 'test_partner_yellow',
                                          'module': 'base',
                                          'model': 'res.partner',
                                          'res_id': pid})
        xid = 'base.test_partner_yellow'
        partner = self.env.ref(xid)
        pid = self.ref(xid)
        self.assertEqual(pid, partner.id, "ref() should resolve xid to database ID")
        partner2 = self.browse_ref(xid)
        self.assertEqual(partner, partner2, "browse_ref() should resolve xid to browse records")


class TestHttpCase(HttpCase):

    def test_console_error_string(self):
        with self.assertLogs(level='ERROR') as log_catcher:
            with self.assertRaises(AssertionError) as error_catcher:
                code = "console.error('test error','message')"
                with patch('odoo.tests.common.ChromeBrowser.take_screenshot', return_value=None):
                    self.browser_js(url_path='about:blank', code=code)
            # second line must contains error message
            self.assertEqual(error_catcher.exception.args[0].splitlines()[-1], "test error message")
        self.assertEqual(len(log_catcher.output), 1)
        self.assertIn('test error message', log_catcher.output[0])

    def test_console_error_object(self):
        with self.assertLogs(level='ERROR') as log_catcher:
            with self.assertRaises(AssertionError) as error_catcher:
                code = "console.error(TypeError('test error message'))"
                with patch('odoo.tests.common.ChromeBrowser.take_screenshot', return_value=None):
                    self.browser_js(url_path='about:blank', code=code)
            # second line must contains error message
            self.assertEqual(error_catcher.exception.args[0].splitlines()[-2:],
            ['TypeError: test error message', '    at <anonymous>:1:15'])
        self.assertEqual(len(log_catcher.output), 1)
        self.assertIn('TypeError: test error message\n    at <anonymous>:1:15', log_catcher.output[0])

    def test_console_log_object(self):
        logger = logging.getLogger('odoo')
        level = logger.level
        logger.setLevel(logging.INFO)
        self.addCleanup(logger.setLevel, level)

        with self.assertLogs() as log_catcher:
            code = "console.log({custom:{1:'test', 2:'a'}, value:1, description:'dummy'});console.log('test successful');"
            self.browser_js(url_path='about:blank', code=code)
        console_log_count = 0
        for log in log_catcher.output:
            if '.browser:' in log:
                text = log.split('.browser:', 1)[1]
                if text == 'test successful':
                    continue
                if text.startswith('heap '):
                    continue
                self.assertEqual(text, "Object(custom=Object, value=1, description='dummy')")
                console_log_count += 1
        self.assertEqual(console_log_count, 1)

@tagged('-at_install', 'post_install')
class TestRunbotLog(HttpCase):
    def test_runbot_js_log(self):
        """Test that a ChromeBrowser console.dir is handled server side as a log of level RUNBOT."""
        log_message = 'this is a small test'
        with self.assertLogs() as log_catcher:
            self.browser_js("about:blank", f"console.runbot = console.dir; console.runbot('{log_message}'); console.log('test successful');")
        found = False
        for record in log_catcher.records:
            if record.message == log_message:
                self.assertEqual(record.levelno, logging.RUNBOT)
                self.assertTrue(record.name.endswith('browser'))
                found = True
        self.assertTrue(found, "Runbot log not found")


@tagged('-at_install', 'post_install')
class TestChromeBrowser(HttpCase):
    def setUp(self):
        super().setUp()
        screencasts_dir = config['screencasts'] or config['screenshots']
        with patch.dict(config.options, {'screencasts': screencasts_dir, 'screenshots': config['screenshots']}):
            self.browser = ChromeBrowser(self)
        self.addCleanup(self.browser.stop)

    def test_screencasts(self):
        self.browser.screencaster.start()
        self.browser.navigate_to('about:blank')
        self.browser._wait_ready()
        code = "setTimeout(() => console.log('test successful'), 2000); setInterval(() => document.body.innerText = (new Date()).getTime(), 100);"
        self.browser._wait_code_ok(code, 10)
        self.browser.screencaster.save()


@tagged('-at_install', 'post_install')
class TestChromeBrowserOddDimensions(TestChromeBrowser):
    allow_inherited_tests_method = True
    browser_size = "1215x768"


class TestRequestRemainingCommon(HttpCase):
    # This test case tries to reproduce the case where a request is lost between two test and is execute during the secone one.
    #
    # - Test A browser js finishes with a pending request
    # - _wait_remaining_requests misses the request since the thread may not be totally spawned (or correctly named)
    # - Test B starts and a SELECT is executed
    # - The request is executed and makes a concurrent fetchall
    # - The test B tries to fetchall and fails since the cursor is already used by the request
    #
    # Note that similar cases can also consume savepoint, make the main cursor readonly, ...

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.thread_a = None
        # this lock is used to ensure the request is executed after test b starts
        cls.main_lock = threading.Lock()
        cls.main_lock.acquire()

        class Dummycontroller(Controller):
            @route('/web/concurrent', type='http', auth='public', sitemap=False)
            def wait(c, **params):
                assert request.env.cr.__class__.__name__ == 'TestCursor'
                request.env.cr.execute('SELECT 1')
                request.env.cr.fetchall()
                # not that the previous queries are not really needed since the http stack will check the registry
                # but this makes the test more clear and robust
                _logger.info('B finish')

        cls.env.registry.clear_cache('routing')
        cls.addClassCleanup(cls.env.registry.clear_cache, 'routing')

    def _test_requests_a(self, cookie=False):

        def late_request_thread():
            # In some rare case the request may arrive after _wait_remaining_requests.
            # this thread is trying to reproduce this case.
            _logger.info('Waiting for B to start')
            if self.main_lock.acquire(timeout=10):
                _logger.info('Opening url')
                # don't use url_open since it simulates a lost request from chrome and url_open would wait to aquire the lock
                s = requests.Session()
                if cookie:
                    s.cookies.set(TEST_CURSOR_COOKIE_NAME, self.canonical_tag)
                s.get(self.base_url() + "/web/concurrent", timeout=10)
            else:
                _logger.error('Something went wrong and thread was not able to aquire lock')

        type(self).thread_a = threading.Thread(target=late_request_thread)
        self.thread_a.start()

    def _test_requests_b(self):
        self.env.cr.execute('SELECT 1')
        self.main_lock.release()
        _logger.info('B started, waiting for A to finish')
        self.thread_a.join()
        self.env.cr.fetchall()


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestRequestRemainingNoCookie(TestRequestRemainingCommon):
    def test_requests_a(self):
        self._test_requests_a()

    def test_requests_b(self):
        with self.assertLogs('odoo.tests.common') as log_catcher:
            self._test_requests_b()
        self.assertEqual(
            log_catcher.output,
            [Like('... odoo.tests.common:Request with path /web/concurrent has been ignored during test as it it does not contain the test_cursor cookie or it is expired. '
             '(required "None (request are not enabled)", got "None")')],
        )


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestRequestRemainingNotEnabled(TestRequestRemainingCommon):
    def test_requests_a(self):
        self._test_requests_a(cookie=True)

    def test_requests_b(self):
        with self.assertLogs('odoo.tests.common') as log_catcher:
            self._test_requests_b()
        self.assertEqual(
            log_catcher.output,
            [Like('... odoo.tests.common:Request with path /web/concurrent has been ignored during test as it it does not contain the test_cursor cookie or it is expired. '
             '(required "None (request are not enabled)", got "/test_tests/tests/test_cases.py:TestRequestRemainingNotEnabled.test_requests_a")')],
        )


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestRequestRemainingStartDuringNext(TestRequestRemainingCommon):
    def test_requests_a(self):
        self._test_requests_a(cookie=True)

    def test_requests_b(self):
        with self.assertLogs('odoo.tests.common') as log_catcher, self.allow_requests():
            self._test_requests_b()
        self.assertEqual(
            log_catcher.output,
            [Like('... odoo.tests.common:Request with path /web/concurrent has been ignored during test as it it does not contain the test_cursor cookie or it is expired. '
             '(required "/test_tests/tests/test_cases.py:TestRequestRemainingStartDuringNext.test_requests_b__0", got "/test_tests/tests/test_cases.py:TestRequestRemainingStartDuringNext.test_requests_a")')],
        )


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestRequestRemainingAfterFirstCheck(TestRequestRemainingCommon):
    """
    This test is more specific to the current implem and check what happens if the lock is aquired after the next thread
    Scenario:
        - test_requests_a closes browser js, aquire the lock
        - a ghost request tries to open a test curso, makes the first check (assertCanOpenTestCursor)
        - the next test enables resquest (here using url_open) releasing the lock
        - the pending request is executed but detects the test change
    """
    def test_requests_a(self, cookie=False):
        self.http_request_key = self.canonical_tag

        def late_request_thread():
            _logger.info('Opening url')
            # don't use url_open since it simulates a lost request from chrome and url_open would wait to aquire the lock
            s = requests.Session()
            s.cookies.set(TEST_CURSOR_COOKIE_NAME, self.http_request_key)
            # we exceptc the request to be stuck when aquiring the registry lock
            s.get(self.base_url() + "/web/concurrent", timeout=10)

        type(self).thread_a = threading.Thread(target=late_request_thread)
        main_lock = self.main_lock
        self.thread_a.start()
        # we need to ensure that the first check is made and that we are aquiring the lock
        main_lock.acquire()

    def assertCanOpenTestCursor(self):
        super().assertCanOpenTestCursor()
        # the first time we check assertCanOpenTestCursor we need release the lock (lowks ensure we are still inside test_requests_a)
        if self.main_lock:
            self.main_lock.release()
            self.main_lock = None

    def test_requests_b(self):
        _logger.info('B started, waiting for A to finish')
        # url_open will simulate a enabled request
        with self.assertLogs('odoo.tests.common') as log_catcher, self.allow_requests():
            self.thread_a.join()
        self.assertEqual(
            log_catcher.output,
            [Like('... Trying to open a test cursor for /test_tests/tests/test_cases.py:TestRequestRemainingAfterFirstCheck.test_requests_a while already in a test /test_tests/tests/test_cases.py:TestRequestRemainingAfterFirstCheck.test_requests_b')],
        )


@tagged('at_install', '-post_install')
class TestEnv(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestEnv, cls).setUpClass()
        user = cls.env['res.users'].create({
            'name': 'superuser',
            'login': 'superuser',
            'password': 'superuser',
            'group_ids': [(6, 0, cls.env.user.group_ids.ids)],
        })
        cls.env = cls.env(user=user)

        # make sure there is at least another environment in the current transaction
        cls.sudo_env = cls.env(su=True)

    def test_env_company_part_01(self):
        """
        The main goal of the test is actually to check the values of the
        environment after this test execution (see test_env_company_part_02)
        """
        company = self.env['res.company'].create({
            "name": "Test Company",
        })
        self.env.user.write({
            'company_id': company.id,
            'company_ids': [(4, company.id), (4, self.env.company.id)],
        })
        self.assertEqual(self.env.company, self.env.user.company_id)
        self.assertTrue(self.env.company.exists())
        self.assertEqual(self.sudo_env.company, self.env.user.company_id)
        self.assertTrue(self.sudo_env.company.exists())

    def test_env_company_part_02(self):
        self.assertEqual(self.env.company, self.env.user.company_id)
        self.assertTrue(self.env.company.exists())
        self.assertEqual(self.sudo_env.company, self.env.user.company_id)
        self.assertTrue(self.sudo_env.company.exists())
