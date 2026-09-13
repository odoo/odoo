import logging
import pathlib
import shutil
import threading
import time
import unittest
from unittest.mock import Mock, patch

import requests
from werkzeug.exceptions import BadRequest

import odoo.http
import odoo.tests.browser as browser_module
from odoo.http import Controller, request, route
from odoo.tests.common import (
    TEST_CURSOR_COOKIE_NAME,
    ChromeBrowser,
    ChromeBrowserException,
    HttpCase,
    Like,
    tagged,
)
from odoo.tools import config

_logger = logging.getLogger(__name__)


@tagged("-at_install", "post_install")
class TestHttpCase(HttpCase):
    def test_console_error_string(self):
        with self.assertLogs(level="ERROR") as log_catcher:
            with self.assertRaises(AssertionError) as error_catcher:
                code = "console.error('test error','message')"
                with patch(
                    "odoo.tests.common.ChromeBrowser.take_screenshot",
                    return_value=None,
                ):
                    self.browser_js(url_path="about:blank", code=code)
            self.assertEqual(
                error_catcher.exception.args[0].splitlines()[-1],
                "test error message",
            )
        self.assertEqual(len(log_catcher.output), 1)
        self.assertIn("test error message", log_catcher.output[0])

    def test_console_error_object(self):
        with self.assertLogs(level="ERROR") as log_catcher:
            with self.assertRaises(AssertionError) as error_catcher:
                code = "console.error(TypeError('test error message'))"
                with patch(
                    "odoo.tests.common.ChromeBrowser.take_screenshot",
                    return_value=None,
                ):
                    self.browser_js(url_path="about:blank", code=code)
            self.assertEqual(
                error_catcher.exception.args[0].splitlines()[-2:],
                ["TypeError: test error message", "    at <anonymous>:1:15"],
            )
        self.assertEqual(len(log_catcher.output), 1)
        self.assertIn(
            "TypeError: test error message\n    at <anonymous>:1:15",
            log_catcher.output[0],
        )

    def test_console_error_waved_through_by_the_checker_does_not_fail_the_run(self):
        # the page reports its own verdict through the success signal; an error
        # the checker ignores must not settle the run, nor poison that signal
        code = "console.error('[probe] not a failure'); console.log('test successful')"
        with self.assertLogs(level="ERROR"):
            self.browser_js(
                url_path="about:blank",
                code=code,
                error_checker=lambda message: "[probe]" not in message,
            )

    def test_console_log_object(self):
        logger = logging.getLogger("odoo")
        level = logger.level
        logger.setLevel(logging.INFO)
        self.addCleanup(logger.setLevel, level)

        with self.assertLogs() as log_catcher:
            code = "console.log({custom:{1:'test', 2:'a'}, value:1, description:'dummy'});console.log('test successful');"
            self.browser_js(url_path="about:blank", code=code)
        console_log_count = 0
        for log in log_catcher.output:
            if ".browser:" in log:
                text = log.split(".browser:", 1)[1]
                if text == "test successful":
                    continue
                if text.startswith("heap "):
                    continue
                self.assertEqual(
                    text, "Object(custom=Object, value=1, description='dummy')"
                )
                console_log_count += 1
        self.assertEqual(console_log_count, 1)


@tagged("-at_install", "post_install")
class TestRunbotLog(HttpCase):
    def test_runbot_js_log(self):
        log_message = "this is a small test"
        with self.assertLogs(self._logger, level=logging.RUNBOT) as log_catcher:
            self.browser_js(
                "about:blank",
                f"console.runbot = console.dir; console.runbot('{log_message}'); console.log('test successful');",
            )
        found = False
        for record in log_catcher.records:
            if record.message == log_message:
                self.assertEqual(record.levelno, logging.RUNBOT)
                self.assertTrue(record.name.endswith("browser"))
                found = True
        self.assertTrue(found, "Runbot log not found")


@tagged("-at_install", "post_install")
class TestAllowRequests(HttpCase):
    def test_allow_all_requests_flag_scoped(self):
        self.assertFalse(self.http_request_allow_all)
        with self.allow_requests(all_requests=True):
            self.assertTrue(self.http_request_allow_all)
        self.assertFalse(self.http_request_allow_all)

    def test_allow_all_requests_flag_restored_after_xmlrpc(self):
        self.assertFalse(self.http_request_allow_all)
        self.xmlrpc_common.version()
        self.assertFalse(self.http_request_allow_all)

    def test_cookieless_request_refused_after_xmlrpc(self):
        session = self.authenticate("admin", "admin@odoo")
        self.xmlrpc_common.version()
        with self.allow_requests():
            response = requests.get(
                self.base_url() + "/odoo/tests/no/such/route",
                cookies={"session_id": session.sid},
                timeout=30,
                allow_redirects=False,
            )
        self.assertEqual(response.status_code, 400)

    def test_cookie_guard_unit(self):
        fake_request = Mock(cookies={}, httprequest=Mock(path="/probe"))
        server_thread = threading.Thread()
        with (
            patch.object(odoo.http, "request", fake_request),
            patch.object(self, "_test_thread", server_thread),
        ):
            with self.assertRaises(BadRequest):
                self.assertCanOpenTestCursor()
            with patch.object(self, "http_request_allow_all", True):
                self.assertCanOpenTestCursor()


@tagged("-at_install", "post_install")
class TestChromeBrowser(HttpCase):
    def setUp(self):
        super().setUp()
        screencasts_dir = config["screencasts"] or config["screenshots"]
        with config.patch(
            screencasts=screencasts_dir,
            screenshots=config["screenshots"],
        ):
            self.browser = ChromeBrowser(self)
        self.addCleanup(self.browser.stop)

    def test_screencasts(self):
        self.browser.screencaster.start()
        self.browser.navigate_to("about:blank")
        self.browser._wait_ready()
        code = "setTimeout(() => console.log('test successful'), 2000); setInterval(() => document.body.innerText = (new Date()).getTime(), 100);"
        self.browser._wait_code_ok(code, 10)
        self.browser.screencaster.save()

    def test_wait_ready_pending_promise_returns_false(self):
        self.browser.navigate_to("about:blank")
        self.browser._wait_ready()
        start = time.monotonic()
        with patch.object(ChromeBrowser, "take_screenshot", return_value=None):
            ok = self.browser._wait_ready("new Promise(() => {})", timeout=1)
        self.assertFalse(ok)
        self.assertLess(time.monotonic() - start, 10)

    def test_wait_ready_throttling_applied_once(self):
        self.browser.navigate_to("about:blank")
        self.browser._wait_ready()
        self.browser.throttling_factor = 3
        try:
            start = time.monotonic()
            with patch.object(ChromeBrowser, "take_screenshot", return_value=None):
                ok = self.browser._wait_ready("new Promise(() => {})", timeout=1)
            elapsed = time.monotonic() - start
        finally:
            self.browser.throttling_factor = 1
        self.assertFalse(ok)
        self.assertGreater(elapsed, 2.5)
        self.assertLess(elapsed, 7)

    def test_wait_code_ok_wraps_evaluate_timeout(self):
        self.browser.navigate_to("about:blank")
        self.browser._wait_ready()
        with patch.object(ChromeBrowser, "take_screenshot", return_value=None):
            with self.assertRaises(ChromeBrowserException):
                self.browser._wait_code_ok("new Promise(() => {})", timeout=1)

    def test_wait_code_ok_budget_not_extended(self):
        self.browser.navigate_to("about:blank")
        self.browser._wait_ready()
        start = time.monotonic()
        with patch.object(ChromeBrowser, "take_screenshot", return_value=None):
            with self.assertRaises(ChromeBrowserException):
                self.browser._wait_code_ok(
                    "new Promise(r => setTimeout(r, 2000))", timeout=3
                )
        elapsed = time.monotonic() - start
        self.assertGreater(elapsed, 2.5)
        self.assertLess(elapsed, 5.5)


@tagged("-at_install", "post_install")
class TestChromeBrowserOddDimensions(TestChromeBrowser):
    allow_inherited_tests_method = True
    browser_size = "1215x768"


class TestRequestRemainingCommon(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.thread_a = None
        cls.main_lock = threading.Lock()
        cls.main_lock.acquire()

        class Dummycontroller(Controller):
            @route("/web/concurrent", type="http", auth="public", sitemap=False)
            def wait(self, **params):
                assert request.env.cr.__class__.__name__ == "TestCursor"
                request.env.cr.execute("SELECT 1")
                request.env.cr.fetchall()
                _logger.info("B finish")

        cls.env.registry.clear_cache("routing")
        cls.addClassCleanup(cls.env.registry.clear_cache, "routing")

    def _test_requests_a(self, cookie=False):

        def late_request_thread():
            _logger.info("Waiting for B to start")
            if self.main_lock.acquire(timeout=10):
                _logger.info("Opening url")
                s = requests.Session()
                if cookie:
                    s.cookies.set(TEST_CURSOR_COOKIE_NAME, self.canonical_tag)
                s.get(self.base_url() + "/web/concurrent", timeout=10)
            else:
                _logger.error(
                    "Something went wrong and thread was not able to aquire lock"
                )

        type(self).thread_a = threading.Thread(target=late_request_thread)
        self.thread_a.start()

    def _test_requests_b(self):
        self.env.cr.execute("SELECT 1")
        self.main_lock.release()
        _logger.info("B started, waiting for A to finish")
        self.thread_a.join()
        self.env.cr.fetchall()


class TestRequestRemainingNoCookie(TestRequestRemainingCommon):
    def test_requests_a(self):
        self._test_requests_a()

    def test_requests_b(self):
        with self.assertLogs("odoo.tests.transaction_case") as log_catcher:
            self._test_requests_b()
        self.assertEqual(
            log_catcher.output,
            [
                Like(
                    "... odoo.tests.transaction_case:Request with path /web/concurrent has been ignored during test as it does not contain the test_cursor cookie or it is expired. "
                    '(required "None (request are not enabled)", got "None")'
                )
            ],
        )


class TestRequestRemainingNotEnabled(TestRequestRemainingCommon):
    def test_requests_a(self):
        self._test_requests_a(cookie=True)

    def test_requests_b(self):
        with self.assertLogs("odoo.tests.transaction_case") as log_catcher:
            self._test_requests_b()
        self.assertEqual(
            log_catcher.output,
            [
                Like(
                    "... odoo.tests.transaction_case:Request with path /web/concurrent has been ignored during test as it does not contain the test_cursor cookie or it is expired. "
                    '(required "None (request are not enabled)", got "/base/tests/test_http_case.py:TestRequestRemainingNotEnabled.test_requests_a")'
                )
            ],
        )


class TestRequestRemainingStartDuringNext(TestRequestRemainingCommon):
    def test_requests_a(self):
        self._test_requests_a(cookie=True)

    def test_requests_b(self):
        with (
            self.assertLogs("odoo.tests.transaction_case") as log_catcher,
            self.allow_requests(),
        ):
            self._test_requests_b()
        self.assertEqual(
            log_catcher.output,
            [
                Like(
                    "... odoo.tests.transaction_case:Request with path /web/concurrent has been ignored during test as it does not contain the test_cursor cookie or it is expired. "
                    '(required "/base/tests/test_http_case.py:TestRequestRemainingStartDuringNext.test_requests_b__0", got "/base/tests/test_http_case.py:TestRequestRemainingStartDuringNext.test_requests_a")'
                )
            ],
        )


class TestRequestRemainingAfterFirstCheck(TestRequestRemainingCommon):
    def test_requests_a(self, cookie=False):
        self.http_request_key = self.canonical_tag

        def late_request_thread():
            _logger.info("Opening url")
            s = requests.Session()
            s.cookies.set(TEST_CURSOR_COOKIE_NAME, self.http_request_key)
            s.get(self.base_url() + "/web/concurrent", timeout=10)

        type(self).thread_a = threading.Thread(target=late_request_thread)
        main_lock = self.main_lock
        self.thread_a.start()
        main_lock.acquire()

    def assertCanOpenTestCursor(self):
        super().assertCanOpenTestCursor()
        if self.main_lock:
            self.main_lock.release()
            self.main_lock = None

    def test_requests_b(self):
        _logger.info("B started, waiting for A to finish")
        with (
            self.assertLogs("odoo.tests.transaction_case") as log_catcher,
            self.allow_requests(),
        ):
            self.thread_a.join()
        self.assertEqual(
            log_catcher.output,
            [
                Like(
                    "... Trying to open a test cursor for /base/tests/test_http_case.py:TestRequestRemainingAfterFirstCheck.test_requests_a while already in a test /base/tests/test_http_case.py:TestRequestRemainingAfterFirstCheck.test_requests_b"
                )
            ],
        )


@tagged("-at_install", "post_install")
class TestChromeBrowserConstructionFailure(HttpCase):
    def _assert_failed_construction_cleans_up(self, break_it, expected_exception):
        spawned = []
        real_chrome_start = ChromeBrowser._chrome_start

        def recording_chrome_start(browser, *args, **kwargs):
            spawned.append(browser)
            return real_chrome_start(browser, *args, **kwargs)

        with (
            patch.object(ChromeBrowser, "_chrome_start", recording_chrome_start),
            break_it,
            self.assertRaises(expected_exception),
        ):
            ChromeBrowser(self)

        self.assertEqual(len(spawned), 1, "Chrome was never spawned")
        browser = spawned[0]
        self.addCleanup(shutil.rmtree, browser.user_data_dir, True)
        self.assertIsNotNone(
            browser.chrome.poll(), "the chrome process is still running"
        )
        self.assertFalse(
            pathlib.Path(browser.user_data_dir).exists(),
            "the chrome profile directory was left behind",
        )

    def test_failed_websocket_handshake_leaves_nothing_behind(self):
        real_create_connection = browser_module.websocket.create_connection

        def refused(*args, **kwargs):
            connection = real_create_connection(*args, **kwargs)
            connection.getstatus = lambda: 500
            return connection

        self._assert_failed_construction_cleans_up(
            patch.object(browser_module.websocket, "create_connection", refused),
            unittest.SkipTest,
        )

    def test_failed_cdp_command_leaves_nothing_behind(self):
        real_request = ChromeBrowser._websocket_request

        def flaky(browser, method, **kwargs):
            if method == "Emulation.setDeviceMetricsOverride":
                raise TimeoutError(method)
            return real_request(browser, method, **kwargs)

        self._assert_failed_construction_cleans_up(
            patch.object(ChromeBrowser, "_websocket_request", flaky),
            TimeoutError,
        )


@tagged("-at_install", "post_install")
class TestWaitReadyNavigation(TestChromeBrowser):
    def test_navigation_during_polling_is_retried(self):
        self.browser.navigate_to("about:blank")
        real_request = ChromeBrowser._websocket_request
        raised = []

        def navigate_away_once(browser, method, **kwargs):
            if method == "Runtime.evaluate" and not raised:
                raised.append(method)
                raise ChromeBrowserException("Inspected target navigated or closed")
            return real_request(browser, method, **kwargs)

        with patch.object(ChromeBrowser, "_websocket_request", navigate_away_once):
            self.assertTrue(self.browser._wait_ready(timeout=10))
        self.assertTrue(raised, "the race was never injected")

    def test_other_cdp_errors_still_propagate(self):
        self.browser.navigate_to("about:blank")

        def broken(browser, method, **kwargs):
            raise ChromeBrowserException("Some other protocol error")

        with (
            patch.object(ChromeBrowser, "_websocket_request", broken),
            self.assertRaises(ChromeBrowserException),
        ):
            self.browser._wait_ready(timeout=10)
