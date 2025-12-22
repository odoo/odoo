# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import threading
from unittest.mock import patch

from odoo.http import Controller, request, route
from odoo.tests.common import ChromeBrowser, HttpCase, tagged
from odoo.tools import config

_logger = logging.getLogger(__name__)


@tagged('-at_install', 'post_install')
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
        self.browser.start_screencast()
        self.browser.navigate_to('about:blank')
        self.browser._wait_ready()
        code = "setTimeout(() => console.log('test successful'), 2000); setInterval(() => document.body.innerText = (new Date()).getTime(), 100);"
        self.browser._wait_code_ok(code, 10)
        self.browser._save_screencast()


@tagged('-at_install', 'post_install')
class TestChromeBrowserOddDimensions(TestChromeBrowser):
    browser_size = "1215x768"


class TestRequestRemaining(HttpCase):
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

    def test_requests_a(self):
        class Dummycontroller(Controller):
            @route('/web/concurrent', type='http', auth='public', sitemap=False)
            def wait(c, **params):
                self.assertEqual(request.env.cr.__class__.__name__, 'TestCursor')
                request.env.cr.execute('SELECT 1')
                request.env.cr.fetchall()
                # not that the previous queries are not really needed since the http stack will check the registry
                # but this makes the test more clear and robust
                _logger.info('B finish')

        self.env.registry.clear_cache('routing')
        self.addCleanup(self.env.registry.clear_cache, 'routing')

        def late_request_thread():
            # In some rare case the request may arrive after _wait_remaining_requests.
            # this thread is trying to reproduce this case.
            _logger.info('Waiting for B to start')
            if self.main_lock.acquire(timeout=10):
                self.url_open("/web/concurrent", timeout=10)
            else:
                _logger.error('Something went wrong and thread was not able to aquire lock')
        TestRequestRemaining.thread_a = threading.Thread(target=late_request_thread)
        self.thread_a.start()

    def test_requests_b(self):
        self.env.cr.execute('SELECT 1')
        with self.assertLogs('odoo.tests.common') as lc:
            self.main_lock.release()
            _logger.info('B started, waiting for A to finish')
            self.thread_a.join()
        self.assertEqual(lc.output[0].split(':', 1)[1], 'odoo.tests.common:Request with path /web/concurrent has been ignored during test as it it does not contain the test_cursor cookie or it is expired. (required "/base/tests/test_http_case.py:TestRequestRemaining.test_requests_b", got "/base/tests/test_http_case.py:TestRequestRemaining.test_requests_a")')
        self.env.cr.fetchall()
