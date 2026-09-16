import base64
import contextlib
import inspect
import itertools
import json
import logging
import operator
import threading
import time
from contextlib import ExitStack, contextmanager
from typing import TYPE_CHECKING, Any, ClassVar
from unittest.mock import patch
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
from uuid import uuid4
from xmlrpc import client as xmlrpclib

import requests

import odoo.http
from odoo import api
from odoo.libs.debug_log import DebugLog
from odoo.logutils import RUNBOT
from odoo.service import security
from odoo.service.server import get_server
from odoo.tools import profiler

from . import common
from .browser import DEFAULT_SUCCESS_SIGNAL, ChromeBrowser, ChromeBrowserException
from .transaction_case import (
    TEST_CURSOR_COOKIE_NAME,
    TransactionCase,
    release_test_lock,
)
from .utils import HOST, InfrastructureUnavailable, env_int, get_db_name

if TYPE_CHECKING:
    from collections.abc import Generator

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


def _tag(case: Any) -> str | None:
    return getattr(case, "canonical_tag", None)


class Opener(requests.Session):
    def __init__(self, http_case: HttpCase) -> None:
        super().__init__()
        self.test_case = http_case

    def request(self, *args: Any, **kwargs: Any) -> Any:
        assert self.test_case.opener == self
        self.test_case.cr.flush()
        self.test_case.cr.clear()
        with (
            _debug.perf(
                "test.http.request",
                test=_tag(self.test_case),
                method=args[0] if args else kwargs.get("method"),
                url=args[1] if len(args) > 1 else kwargs.get("url"),
            ) as span,
            self.test_case.allow_requests(),
        ):
            response = super().request(*args, **kwargs)
            span.set(status=response.status_code, history=len(response.history))
            return response


class Transport(xmlrpclib.Transport):
    def __init__(self, http_case: HttpCase) -> None:
        self.test_case = http_case
        super().__init__()

    def request(self, *args: Any, **kwargs: Any) -> Any:
        self.test_case.cr.flush()
        self.test_case.cr.clear()
        with (
            _debug.perf(
                "test.http.xmlrpc",
                test=_tag(self.test_case),
                handler=args[1] if len(args) > 1 else None,
            ),
            self.test_case.allow_requests(all_requests=True),
        ):
            return super().request(*args, **kwargs)


class JsonRpcException(Exception):
    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code


class HttpCase(TransactionCase):
    registry_test_mode = True
    browser = None
    browser_size = "1366x768"
    touch_enabled = False
    session: odoo.http.Session

    xmlrpc_url: ClassVar[str]
    _logger: logging.Logger

    @classmethod
    def setUpClass(cls) -> None:
        if cls.http_port() is None:
            _debug.logic("test.http.no_server", cls=cls.__qualname__)
            raise InfrastructureUnavailable(
                f"{cls.__name__} requires a running HTTP server (--no-http?)"
            )
        super().setUpClass()
        if cls.registry_test_mode:
            cls.registry_enter_test_mode_cls()

        ICP = cls.env["ir.config_parameter"]
        ICP.set_param("web.base.url", cls.base_url())  # type: ignore[attr-defined]  # ir.config_parameter is an addon model
        cls.env.flush_all()
        cls.xmlrpc_url = f"{cls.base_url()}/xmlrpc/2/"
        cls._logger = logging.getLogger("%s.%s" % (cls.__module__, cls.__name__))
        _debug.lifecycle(
            "test.http.class_ready",
            cls=cls.__qualname__,
            port=cls.http_port(),
            test_mode=cls.registry_test_mode,
            browser_size=cls.browser_size,
            touch=cls.touch_enabled,
        )

    @classmethod
    def base_url(cls) -> str:
        return f"http://{HOST}:{cls.http_port():d}"

    @classmethod
    def http_port(cls) -> int | None:
        httpd = getattr(get_server(), "httpd", None)
        return httpd.server_port if httpd is not None else None

    def setUp(self) -> None:
        super().setUp()

        self._logger = type(self)._logger.getChild(self._testMethodName)

        self.xmlrpc_common = xmlrpclib.ServerProxy(
            self.xmlrpc_url + "common", transport=Transport(self)
        )
        self.xmlrpc_db = xmlrpclib.ServerProxy(
            self.xmlrpc_url + "db", transport=Transport(self)
        )
        self.xmlrpc_object = xmlrpclib.ServerProxy(
            self.xmlrpc_url + "object",
            transport=Transport(self),
            use_datetime=True,
        )
        for proxy in (self.xmlrpc_common, self.xmlrpc_db, self.xmlrpc_object):
            self.addCleanup(proxy("close"))
        self.opener = Opener(self)
        self.addCleanup(self._close_opener)
        self.http_key_sequence = itertools.count()
        _debug.lifecycle("test.http.setup", test=_tag(self))

    def _close_opener(self) -> None:
        _debug.lifecycle("test.http.opener_closed", test=_tag(self))
        self.opener.close()

    @contextmanager
    def enter_registry_test_mode(self) -> Generator[None]:
        _debug.logic("test.registry.test_mode_redundant", test=_tag(self))
        _logger.warning("HTTPCase is already in test mode")
        yield

    @contextmanager
    def allow_pdf_render(self) -> Generator[None]:
        _debug.logic("test.registry.pdf_render_redundant", test=_tag(self))
        _logger.warning("HTTPCase does not require calling allow_pdf_render")
        yield

    @contextmanager
    def allow_requests(self, browser: ChromeBrowser | None = None, all_requests=False):
        with ExitStack() as defer:
            defer.enter_context(release_test_lock())
            if all_requests:
                defer.enter_context(patch.object(self, "http_request_allow_all", True))
            new_key = f"{self.canonical_tag}__{next(self.http_key_sequence)}"
            defer.enter_context(patch.object(self, "http_request_key", new_key))
            old_cookie = self.opener.cookies.get(TEST_CURSOR_COOKIE_NAME)
            if old_cookie:
                defer.callback(
                    self.opener.cookies.set, TEST_CURSOR_COOKIE_NAME, old_cookie
                )
            else:
                defer.callback(self.opener.cookies.pop, TEST_CURSOR_COOKIE_NAME, None)
            self.opener.cookies[TEST_CURSOR_COOKIE_NAME] = new_key
            if browser:
                browser.set_cookie(
                    TEST_CURSOR_COOKIE_NAME,
                    self.http_request_key,
                    "/",
                    HOST,
                    http_only=True,
                )
            _debug.lifecycle(
                "test.http.requests_allowed",
                key=new_key,
                all=all_requests,
                browser=browser is not None,
                had_cookie=bool(old_cookie),
            )
            defer.callback(_debug.lifecycle, "test.http.requests_closed", key=new_key)
            yield

    def parse_http_location(self, location: str | None) -> Any:
        if not location:
            return urlsplit("")
        s = urlsplit(urljoin(self.base_url(), location))
        params = sorted(parse_qsl(s.query), key=operator.itemgetter(0))
        return s._replace(query=urlencode(params))

    def assertURLEqual(
        self, test_url: str, truth_url: str, message: str | None = None
    ) -> None:
        self.assertEqual(
            self.parse_http_location(test_url),
            self.parse_http_location(truth_url),
            message,
        )

    def prepare_rpc_payload(self, params: dict | None = None) -> dict:
        return {
            "jsonrpc": "2.0",
            "method": "call",
            "id": str(uuid4()),
            "params": params or {},
        }

    def url_open(
        self,
        url: str,
        data: Any = None,
        files: Any = None,
        timeout: int = 12,
        headers: dict | None = None,
        json: Any = None,
        params: dict | None = None,
        allow_redirects: bool = True,
        cookies: dict | None = None,
        method: str | None = None,
    ) -> Any:
        if not method and (data or files or json):
            method = "POST"
        method = method or "GET"
        if url.startswith("/"):
            url = self.base_url() + url
        _debug.pipeline(
            "test.http.url_open",
            method=method,
            url=url,
            timeout=timeout,
            redirects=allow_redirects,
            cookies=bool(cookies),
        )
        return self.opener.request(
            method,
            url,
            params=params,
            data=data,
            json=json,
            files=files,
            timeout=timeout,
            headers=headers,
            cookies=cookies,
            allow_redirects=allow_redirects,
        )

    def _wait_remaining_requests(
        self, timeout: int = 10, *, strict: bool = True
    ) -> None:

        def get_http_request_threads() -> list[threading.Thread]:
            return [
                t
                for t in threading.enumerate()
                if t.name.startswith("odoo.service.http.request.")
            ]

        start_time = time.monotonic()
        request_threads = get_http_request_threads()
        if not request_threads:
            return

        self._logger.info("waiting for threads: %s", request_threads)

        # A pooled worker outlives its request and is renamed when it goes back
        # to idle, so joining it would wait out the whole timeout: poll instead.
        deadline = start_time + timeout
        with _debug.perf(
            "test.http.wait_requests",
            test=_tag(self),
            threads=len(request_threads),
            timeout=timeout,
        ) as span:
            while request_threads and time.monotonic() < deadline:
                for thread in request_threads:
                    thread.join(min(0.05, max(deadline - time.monotonic(), 0)))
                request_threads = get_http_request_threads()
            span.set(remaining=len(request_threads))
        if not request_threads:
            return

        _debug.logic(
            "test.http.request_threads_leaked",
            test=_tag(self),
            count=len(request_threads),
            strict=strict,
        )
        odoo.tools.misc.dumpstacks()
        leaked = ", ".join(
            f"{thread.name} ({getattr(thread, 'url', '<UNKNOWN>')})"
            for thread in request_threads
        )
        message = (
            f"{len(request_threads)} request thread(s) still running {timeout}s "
            f"after {self.canonical_tag}: {leaked}. A request that outlives its "
            f"test can still hold the registry lock through its TestCursor, "
            f"which costs every later test the full re-acquisition timeout."
        )
        if strict:
            raise AssertionError(message)
        self._logger.warning("%s", message)

    def _wait_for_requests_unless_already_failing(
        self, exc_type: type[BaseException] | None, exc: object, tb: object
    ) -> None:
        self._wait_remaining_requests(strict=exc_type is None)

    def logout(self, keep_db: bool = True) -> None:
        # The browser may have followed a rotation since authenticate().
        sid = self.opener.cookies.get("session_id", self.session.sid)
        _debug.lifecycle(
            "test.http.logout",
            test=_tag(self),
            rotated=sid != self.session.sid,
            keep_db=keep_db,
        )
        self.session = odoo.http.root.session_store.get(sid)
        self.session.logout(keep_db=keep_db)
        odoo.http.root.session_store.save(self.session)

    def authenticate(
        self,
        user: str | None,
        password: str | None,
        *,
        browser: ChromeBrowser | None = None,
        session_extra: dict | None = None,
    ) -> Any:
        if getattr(self, "session", None):
            _debug.logic("test.http.session_replaced", test=_tag(self))
            odoo.http.root.session_store.delete(self.session)

        _debug.pipeline(
            "test.http.authenticate",
            test=_tag(self),
            user=user,
            browser=browser is not None,
            extra=sorted(session_extra) if session_extra else [],
        )
        self.session = session = odoo.http.root.session_store.new()
        session.update(
            odoo.http.prepare_default_session(),
            db=get_db_name(),
            _trace_disable=True,
        )
        session.context["lang"] = odoo.http.DEFAULT_LANG

        if session_extra:
            if extra_ctx := session_extra.pop("context", None):
                session.context.update(extra_ctx)
            session.update(session_extra)

        if user:
            self.cr.flush()
            self.cr.clear()

            def patched_check_credentials(self, credential, env):
                return {
                    "uid": self.id,
                    "auth_method": "password",
                    "mfa": "default",
                }

            with (
                patch(
                    "odoo.addons.base.models.res_users.ResUsersPatchedInTest._check_credentials",
                    new=patched_check_credentials,
                ),
                _debug.perf("test.http.authenticate_user", cr=self.cr, user=user),
            ):
                credential = {
                    "login": user,
                    "password": password,
                    "type": "password",
                }
                auth_info = self.env["res.users"].authenticate(
                    credential, {"interactive": False}
                )
            uid = auth_info["uid"]
            env = api.Environment(self.cr, uid, {})
            session.uid = uid
            session.login = user
            session.session_token = uid and security.get_session_token(session, env)
            session.context = dict(env["res.users"].context_get())

        odoo.http.root.session_store.save(session)
        old_opener = getattr(self, "opener", None)
        if old_opener is not None:
            old_opener.close()
        self.opener = Opener(self)
        self.opener.cookies.set("session_id", session.sid, domain=HOST)
        if browser:
            self._logger.info("Setting session cookie in browser")
            browser.set_cookie("session_id", session.sid, "/", HOST, http_only=True)
        _debug.lifecycle(
            "test.http.authenticated",
            test=_tag(self),
            uid=session.uid,
            opener_replaced=old_opener is not None,
            browser=browser is not None,
        )

        return session

    def prepare_proxy_response(self, url: str) -> dict:

        if "https://fonts.googleapis.com/css" in url:
            _debug.logic("test.http.proxy", kind="fonts", url=url)
            _logger.info(
                "External chrome request during tests: Return empty file for %s",
                url,
            )
            return self.prepare_proxy_response_from_content("")

        _debug.logic("test.http.proxy", kind="404", url=url)
        _logger.info("External chrome request during tests: returning 404 for %s", url)
        return {
            "body": "",
            "responseCode": 404,
            "responseHeaders": [],
        }

    def prepare_proxy_response_from_content(
        self, content: str | bytes, code: int = 200
    ) -> dict:
        if isinstance(content, str):
            content = content.encode()
        return {
            "body": base64.b64encode(content).decode(),
            "responseCode": code,
            "responseHeaders": [
                {"name": "access-control-allow-origin", "value": "*"},
                {"name": "cache-control", "value": "public, max-age=10000"},
            ],
        }

    def _browser_js_budget(
        self, timeout: float, watch: bool, debug: Any
    ) -> tuple[float, bool]:
        if not self.env.registry.loaded:
            self._logger.warning("HttpCase test should be in post_install only")

        if any(
            f.filename.endswith("/coverage/execfile.py")
            for f in inspect.stack()
            if f.filename
        ):
            timeout *= 1.5

        if debug is not False:
            watch = True
            timeout = 1e6
        if watch:
            self._logger.warning("watch mode is only suitable for local testing")
        _debug.logic(
            "test.browser.budget",
            test=_tag(self),
            timeout=timeout,
            watch=watch,
            debug=debug is not False,
            registry_loaded=self.env.registry.loaded,
        )
        return timeout, watch

    def _browser_js_patch_bus(self, atexit: contextlib.ExitStack) -> None:
        if "bus.bus" not in self.env.registry:
            _debug.logic("test.browser.bus_patched", present=False)
            return
        _debug.logic("test.browser.bus_patched", present=True)

        from odoo.addons.bus.models.bus import BusBus
        from odoo.addons.bus.websocket import (
            CloseCode,
            WebsocketConnectionHandler,
            _kick_all,
        )

        atexit.callback(_kick_all, CloseCode.KILL_NOW)
        original_send_one = BusBus._sendone

        def sendone_wrapper(self, target, notification_type, message):
            original_send_one(self, target, notification_type, message)
            self.env.cr.precommit.run()
            self.env.cr.postcommit.run()

        atexit.enter_context(patch.object(BusBus, "_sendone", sendone_wrapper))
        atexit.enter_context(
            patch.object(
                WebsocketConnectionHandler,
                "websocket_allowed",
                return_value=True,
            )
        )

    def _browser_js_url(self, url_path: str, *, watch: bool, debug: Any) -> str:
        url = urljoin(self.base_url(), url_path)
        if not watch:
            return url
        parsed = urlsplit(url)
        qs = dict(parse_qsl(parsed.query))
        qs["watch"] = "1"
        if debug is not False:
            qs["debug"] = "assets"
        return urlunsplit(parsed._replace(query=urlencode(qs)))

    def browser_js(
        self,
        url_path,
        code,
        ready="",
        login=None,
        timeout=60,
        cookies=None,
        error_checker=None,
        watch=False,
        success_signal=DEFAULT_SUCCESS_SIGNAL,
        debug=False,
        cpu_throttling=None,
        **kw,
    ):
        timeout, watch = self._browser_js_budget(timeout, watch, debug)

        _debug.pipeline(
            "test.browser.js_start",
            test=_tag(self),
            url=url_path,
            login=login,
            ready=bool(ready),
            code=bool(code),
            success_signal=success_signal,
            cookies=len(cookies or ()),
            error_checker=error_checker is not None,
        )
        browser = common.ChromeBrowser(
            self, headless=not watch, success_signal=success_signal, debug=debug
        )
        with (
            _debug.perf(
                "test.browser.js", cr=self.cr, test=_tag(self), url=url_path
            ) as span,
            contextlib.ExitStack() as atexit,
        ):
            atexit.enter_context(self.allow_requests(browser=browser))
            atexit.push(self._wait_for_requests_unless_already_failing)
            # Registered last so it runs first: the browser is gone before the
            # wait for its requests starts, and before the cookie is withdrawn.
            atexit.callback(browser.stop)
            self._browser_js_patch_bus(atexit)

            self.authenticate(login, login, browser=browser)
            self.cr.flush()
            self.cr.clear()
            url = self._browser_js_url(url_path, watch=watch, debug=debug)
            self._logger.info('Open "%s" in browser', url)

            browser.screencaster.start()
            if cookies:
                for name, value in cookies.items():
                    browser.set_cookie(name, value, "/", HOST)

            cpu_throttling_os = env_int("ODOO_BROWSER_CPU_THROTTLING", 0)
            cpu_throttling = cpu_throttling_os or cpu_throttling

            if cpu_throttling:
                _debug.logic(
                    "test.browser.throttled",
                    factor=cpu_throttling,
                    source="env" if cpu_throttling_os else "arg",
                    timeout=timeout * cpu_throttling,
                )
                _logger.log(
                    logging.INFO if cpu_throttling_os else logging.WARNING,
                    "CPU throttling mode is only suitable for local testing - "
                    "Throttling browser CPU to %sx slowdown and extending timeout to %s sec",
                    cpu_throttling,
                    timeout * cpu_throttling,
                )
                browser.throttle(cpu_throttling)

            browser.navigate_to(url, wait_stop=not bool(ready))

            ready_ok = browser._wait_ready(ready, timeout)
            span.set(ready=ready_ok)
            if not ready_ok:
                _debug.logic("test.browser.ready_failed", test=_tag(self))
            self.assertTrue(
                ready_ok,
                'The ready "%s" code was always falsy' % ready,
            )

            error: ChromeBrowserException | None = None
            try:
                browser._wait_code_ok(code, timeout, error_checker=error_checker)
            except ChromeBrowserException as chrome_browser_exception:
                error = chrome_browser_exception
            span.set(failed=error is not None)
            if error:
                if code:
                    message = 'The test code "%s" failed' % code
                else:
                    message = "Some js test failed"
                self.fail("%s\n\n%s" % (message, error))

    def start_tour(
        self,
        url_path: str,
        tour_name: str,
        step_delay: int | None = None,
        **kwargs: Any,
    ) -> None:
        options = {
            "stepDelay": step_delay or 0,
            "keepWatchBrowser": kwargs.get("watch", False),
            "debug": kwargs.get("debug", False),
            "startUrl": url_path,
            "delayToCheckUndeterminisms": kwargs.pop(
                "delay_to_check_undeterminisms",
                env_int("ODOO_TOUR_DELAY_TO_CHECK_UNDETERMINISMS", 0),
            ),
        }
        code = kwargs.pop(
            "code", f"odoo.startTour({tour_name!r}, {json.dumps(options)})"
        )
        ready = kwargs.pop("ready", f"odoo.isTourReady({tour_name!r})")
        timeout = kwargs.pop("timeout", 60)

        if step_delay is not None:
            self._logger.warning("step_delay is only suitable for local testing")
        if options["delayToCheckUndeterminisms"] > 0:
            timeout += 1000 * options["delayToCheckUndeterminisms"]
            _logger.log(
                RUNBOT,
                "Tour %s is launched with mode: check for undeterminisms.",
                tour_name,
            )
        _debug.pipeline(
            "test.browser.tour",
            test=_tag(self),
            tour=tour_name,
            url=url_path,
            step_delay=options["stepDelay"],
            undeterminisms=options["delayToCheckUndeterminisms"],
            timeout=timeout,
            watch=options["keepWatchBrowser"],
        )
        Users = self.registry["res.users"]

        def setup(_):
            Users.tour_enabled = False  # type: ignore[attr-defined]  # res.users is an addon model

        with (
            patch.object(Users, "tour_enabled", False),
            patch.object(Users, "_post_model_setup__", setup),
            patch.object(Users, "_compute_tour_enabled", lambda _: None),
        ):
            self.browser_js(
                url_path=url_path,
                code=code,
                ready=ready,
                timeout=timeout,
                success_signal="tour succeeded",
                **kwargs,
            )

    def profile(self, description: str = "", **kwargs: Any) -> Any:
        make_profiler = super().profile
        _profiler = make_profiler(description, **kwargs)

        def route_profiler(request):
            _route_profiler = make_profiler(
                description=request.httprequest.full_path, db=_profiler.db
            )
            _profiler.sub_profilers.append(_route_profiler)
            _debug.lifecycle(
                "test.profile.route",
                path=request.httprequest.path,
                sub_profilers=len(_profiler.sub_profilers),
            )
            return _route_profiler

        return profiler.Nested(
            _profiler,
            patch(
                "odoo.http.Request._profile_request",
                route_profiler,
            ),
        )

    _SOURCE_TAGS = {
        **TransactionCase._SOURCE_TAGS,
        "is_tour": "self.start_tour",
    }

    def call_jsonrpc(
        self,
        route: str,
        params: dict | None = None,
        headers: dict | None = None,
        cookies: dict | None = None,
        timeout: int = 12,
    ) -> Any:
        response = self.opener.post(
            urljoin(self.base_url(), route),
            json=self.prepare_rpc_payload(params),
            headers=headers,
            cookies=cookies,
            timeout=timeout,
        )
        response.raise_for_status()
        decoded_response = response.json()
        if "error" in decoded_response:
            _debug.logic(
                "test.http.jsonrpc_error",
                route=route,
                code=decoded_response["error"]["code"],
                name=decoded_response["error"]["data"]["name"],
            )
            raise JsonRpcException(
                code=decoded_response["error"]["code"],
                message=decoded_response["error"]["data"]["name"],
            )
        _debug.pipeline("test.http.jsonrpc", route=route, params=sorted(params or ()))
        return decoded_response.get("result")
