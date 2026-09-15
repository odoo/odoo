import binascii
import concurrent.futures
import contextlib
import gc
import itertools
import json
import logging
import os
import pathlib
import platform
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import CancelledError, Future, InvalidStateError, wait
from datetime import datetime
from functools import lru_cache
from itertools import islice, zip_longest
from textwrap import shorten
from typing import TYPE_CHECKING, Any

import psutil
import requests

import odoo.tools
from odoo.libs.debug_log import DebugLog
from odoo.libs.worker_thread import current_worker_thread
from odoo.logutils import RUNBOT
from odoo.tools.misc import get_executable_path

from .utils import HOST, InfrastructureUnavailable, get_db_name, save_test_file

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

    from .common import HttpCase

try:
    import websocket
except ImportError:
    websocket = None  # type: ignore[assignment]

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

CHECK_BROWSER_SLEEP = 0.1
CHECK_BROWSER_ITERATIONS = 100
BROWSER_WAIT = CHECK_BROWSER_SLEEP * CHECK_BROWSER_ITERATIONS
DEFAULT_SUCCESS_SIGNAL = "test successful"

IGNORED_MSGS = re.compile(
    r"""
    failed\ to\ fetch  # base error
  | connectionlosterror:  # conversion by offlineFailToFetchErrorHandler
    # ``ConnectionLostError`` subclasses (web/static/src/core/network/rpc.js).
    # Each overrides ``this.name``, so the bare ``connectionlosterror:`` above
    # never matches their serialized form even though they ARE connection-lost
    # errors -- rpc.js extends the base class precisely so existing handling
    # keeps matching. Tearing the HTTP server down under an in-flight fetch
    # truncates the body, which rpc.js classifies as InvalidResponseError
    # ("empty 200, truncated proxy body"); that surfaced as a spurious ERROR
    # on every mail discuss tour run.
  | serveroverloaderror:
  | invalidresponseerror:
  | assetsloadingerror:  # lazy loaded bundle
""",
    flags=re.VERBOSE | re.IGNORECASE,
).search


TARGET_GONE = re.compile(r"inspected target navigated or closed", re.IGNORECASE).search


class ChromeBrowserException(Exception):
    pass


def run_coroutine(gen_func):
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


class ChromeBrowser:
    remote_debugging_port = 0

    def __init__(
        self,
        test_case: HttpCase,
        success_signal: str = DEFAULT_SUCCESS_SIGNAL,
        headless: bool = True,
        debug: bool = False,
    ):
        self.throttling_factor = 1
        self._logger = test_case._logger
        self.test_case = test_case
        self.success_signal = success_signal
        if websocket is None:
            _debug.logic("test.browser.websocket_missing")
            self._logger.warning("websocket-client module is not installed")
            raise InfrastructureUnavailable("websocket-client module is not installed")
        self.user_data_dir = tempfile.mkdtemp(suffix="_chrome_odoo")
        _debug.lifecycle(
            "test.browser.init",
            test=test_case.canonical_tag,
            headless=headless,
            debug=debug is not False,
            screencasts=bool(odoo.tools.config["screencasts"]),
            success_signal=success_signal,
            profile=self.user_data_dir,
        )

        self.screencaster: Screencaster | NoScreencast
        if scs := odoo.tools.config["screencasts"]:
            self.screencaster = Screencaster(self, scs)
        else:
            self.screencaster = NoScreencast()

        self._sigxcpu_installed = False
        self.sigxcpu_handler = None
        if os.name == "posix":
            self.sigxcpu_handler = signal.getsignal(signal.SIGXCPU)
            signal.signal(signal.SIGXCPU, self.signal_handler)
            self._sigxcpu_installed = True

        self._request_id = itertools.count()
        self._result: Future[Any] = Future()
        self.error_checker: Callable | None = None
        self.had_failure = False
        self._responses: dict[int, Future] = {}
        self._frames: dict[str, Any] = {}
        try:
            with _debug.perf("test.browser.start", test=test_case.canonical_tag):
                self.chrome, self.devtools_port = self._chrome_start(
                    user_data_dir=self.user_data_dir,
                    touch_enabled=test_case.touch_enabled,
                    headless=headless,
                    debug=debug,
                )
                self._connect()
        except BaseException as exc:
            _debug.lifecycle("test.browser.start_failed", error=type(exc).__name__)
            self.stop()
            raise

    def _connect(self) -> None:
        self.ws = self._open_websocket()
        self._handlers: dict[str, Callable] = {
            "Fetch.requestPaused": self._handle_request_paused,
            "Runtime.consoleAPICalled": self._handle_console,
            "Runtime.exceptionThrown": self._handle_exception,
            "Page.frameStoppedLoading": self._handle_frame_stopped_loading,
            "Page.screencastFrame": self.screencaster,
            "ServiceWorker.workerErrorReported": self._handle_service_worker_error,
        }
        for attempt in range(5):
            receiver = threading.Thread(
                target=self._receive,
                name="WebSocket events consumer",
                args=(get_db_name(),),
                daemon=True,
            )
            try:
                receiver.start()
            except RuntimeError:
                _debug.logic("test.browser.receiver_retry", attempt=attempt + 1)
                if attempt == 4:
                    raise
                gc.collect()
                time.sleep(0.2 * (attempt + 1))
            else:
                self._receiver = receiver
                _debug.lifecycle("test.browser.receiver_started", attempts=attempt + 1)
                break
        self._logger.info("Enable chrome headless console log notification")
        self._websocket_send("Runtime.enable")
        self._websocket_send("ServiceWorker.enable")
        self._websocket_request("Fetch.enable")
        self._logger.info("Chrome headless enable page notifications")
        self._websocket_send("Page.enable")
        self._websocket_send(
            "Page.setDownloadBehavior",
            params={
                "behavior": "deny",
                "eventsEnabled": False,
            },
        )
        self._websocket_send(
            "Emulation.setFocusEmulationEnabled", params={"enabled": True}
        )
        width, height = (
            int(size) for size in re.split(r"[x,]", self.test_case.browser_size)
        )
        self._websocket_request(
            "Emulation.setDeviceMetricsOverride",
            params={
                "mobile": False,
                "width": width,
                "height": height,
                "deviceScaleFactor": 1,
            },
        )
        _debug.lifecycle(
            "test.browser.connected",
            port=self.devtools_port,
            width=width,
            height=height,
            handlers=len(self._handlers),
        )

    def _settle_exception(self, exc: BaseException) -> None:
        try:
            self._result.set_exception(exc)
        except CancelledError:
            _debug.lifecycle(
                "test.browser.settled", kind="exception", state="cancelled"
            )
        except InvalidStateError:
            _debug.lifecycle("test.browser.settled", kind="exception", state="already")
            self._logger.warning(
                "Trying to set result to failed (%s) but found the future settled (%s)",
                exc,
                self._result,
            )
        else:
            _debug.lifecycle(
                "test.browser.settled",
                kind="exception",
                state="set",
                error=type(exc).__name__,
            )

    def _settle_result(self, value: Any) -> None:
        try:
            self._result.set_result(value)
        except CancelledError:
            _debug.lifecycle("test.browser.settled", kind="result", state="cancelled")
        except InvalidStateError:
            _debug.lifecycle("test.browser.settled", kind="result", state="already")
            self._logger.warning(
                "Trying to set result to %s but found the future settled (%s)",
                value,
                self._result,
            )
        else:
            _debug.lifecycle("test.browser.settled", kind="result", state="set")

    def signal_handler(self, sig: int, frame: Any) -> None:
        if sig == signal.SIGXCPU:
            _debug.lifecycle("test.browser.sigxcpu")
            _logger.info("CPU time limit reached, stopping Chrome and shutting down")
            self.stop()
            sys.exit()

    def throttle(self, factor: int | None) -> None:
        if not factor:
            return

        assert 1 <= factor <= 50
        self.throttling_factor = factor
        _debug.lifecycle("test.browser.throttle", factor=factor)
        self._websocket_request(
            "Emulation.setCPUThrottlingRate", params={"rate": factor}
        )

    def stop(self) -> None:
        if getattr(self, "_stopped", False):
            _debug.logic("test.browser.stop_again")
            return
        self._stopped = True
        _debug.lifecycle(
            "test.browser.stop",
            connected=hasattr(self, "ws"),
            spawned=hasattr(self, "chrome"),
            pending=len(self._responses),
            settled=self._result.done(),
        )
        if hasattr(self, "ws"):
            try:
                self.screencaster.stop()

                self._websocket_request("Page.stopLoading")
                self._websocket_request(
                    "Runtime.evaluate",
                    params={
                        "expression": """
                ('serviceWorker' in navigator) &&
                    navigator.serviceWorker.getRegistrations().then(
                        registrations => Promise.all(registrations.map(r => r.unregister()))
                    )
                """,
                        "awaitPromise": True,
                    },
                )
                wait(self._responses.values(), 10)
                self._result.cancel()

                self._logger.info(
                    "Closing chrome headless with pid %s", self.chrome.pid
                )
                self._websocket_request("Browser.close")
            except ChromeBrowserException as e:
                _debug.logic("test.browser.shutdown_error", kind="websocket")
                _logger.log(RUNBOT, "WS error during browser shutdown: %s", e)
            except Exception as e:
                _debug.logic(
                    "test.browser.shutdown_error",
                    kind="other",
                    error=type(e).__name__,
                )
                _logger.warning("Error during browser shutdown", exc_info=True)
            self._logger.info("Closing websocket connection")
            with contextlib.suppress(AttributeError, OSError):
                self.ws.close()

        if hasattr(self, "chrome"):
            self._terminate_chrome()

        self._logger.info('Removing chrome user profile "%s"', self.user_data_dir)
        _debug.lifecycle("test.browser.stopped", profile=self.user_data_dir)
        shutil.rmtree(self.user_data_dir, ignore_errors=True)

        if self._sigxcpu_installed:
            with contextlib.suppress(ValueError, TypeError):
                signal.signal(signal.SIGXCPU, self.sigxcpu_handler or signal.SIG_DFL)

    def _terminate_chrome(self) -> None:
        self._logger.info("Terminating chrome headless with pid %s", self.chrome.pid)
        try:
            main = psutil.Process(self.chrome.pid)
            procs = [main, *main.children(recursive=True)]
        except psutil.NoSuchProcess:
            procs = []
        self.chrome.terminate()
        _, alive = psutil.wait_procs(procs, 5)
        _debug.lifecycle(
            "test.browser.terminated",
            pid=self.chrome.pid,
            procs=len(procs),
            alive=len(alive),
        )
        if alive:
            self._logger.warning(
                "Killing chrome descendants-or-self of %s: %d remaining%s",
                self.chrome.pid,
                len(alive),
                "".join(f"\n- {p.name()} ({p.status()})" for p in alive),
            )
            for p in alive:
                p.kill()
            psutil.wait_procs(alive, 1)

    @property
    def executable(self):
        try:
            return _get_browser_executable_path()
        except Exception:
            _debug.logic("test.browser.executable_missing")
            self._logger.warning("Chrome executable not found")
            raise

    def _spawn_chrome(self, cmd: list[str]) -> tuple[subprocess.Popen, int]:
        log_path = pathlib.Path(self.user_data_dir, "err.log")
        with log_path.open("wb") as log_file:
            proc = subprocess.Popen(
                cmd,
                stdout=log_file,
                stderr=log_file,
                env={**os.environ, "TMPDIR": self.user_data_dir},
            )

        port_file = pathlib.Path(self.user_data_dir, "DevToolsActivePort")
        died = None
        start = time.monotonic()  # debuglog
        for iteration in range(CHECK_BROWSER_ITERATIONS):
            time.sleep(CHECK_BROWSER_SLEEP)
            if port_file.is_file() and port_file.stat().st_size > 5:
                with port_file.open("r", encoding="utf-8") as f:
                    port = int(f.readline())
                _debug.lifecycle(
                    "test.browser.spawned",
                    pid=proc.pid,
                    port=port,
                    profile=self.user_data_dir,
                    polls=iteration + 1,
                    wait_s=time.monotonic() - start,
                )
                return proc, port
            if (died := proc.poll()) is not None:
                break

        _debug.logic(
            "test.browser.spawn_failed",
            reason="died" if died is not None else "no_port",
            code=died,
            wait_s=time.monotonic() - start,
        )

        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        self._logger.warning(
            "Chrome headless failed to start:\n%s",
            log_path.read_text(encoding="utf-8"),
        )
        shutil.rmtree(self.user_data_dir, ignore_errors=True)

        if died is not None:
            raise InfrastructureUnavailable(
                f"Chrome exited with code {died} before publishing a devtools port."
            )
        raise InfrastructureUnavailable(
            f"Failed to detect chrome devtools port after {BROWSER_WAIT:.1f}s."
        )

    def _chrome_start(
        self,
        user_data_dir: str,
        touch_enabled: bool,
        headless: bool = True,
        debug: bool | str = False,
    ) -> tuple[subprocess.Popen, int]:
        headless_switches = {
            "--headless": "",
            "--disable-extensions": "",
            "--disable-background-networking": "",
            "--disable-background-timer-throttling": "",
            "--disable-backgrounding-occluded-windows": "",
            "--disable-renderer-backgrounding": "",
            "--disable-breakpad": "",
            "--disable-client-side-phishing-detection": "",
            "--disable-crash-reporter": "",
            "--disable-dev-shm-usage": "",
            "--disable-namespace-sandbox": "",
            "--disable-translate": "",
            "--no-sandbox": "",
            "--disable-gpu": "",
            "--enable-unsafe-swiftshader": "",
            "--mute-audio": "",
        }
        switches = {
            "--autoplay-policy": "no-user-gesture-required",
            "--disable-default-apps": "",
            "--disable-device-discovery-notifications": "",
            "--no-default-browser-check": "",
            "--remote-debugging-address": HOST,
            "--remote-debugging-port": str(self.remote_debugging_port),
            "--user-data-dir": user_data_dir,
            "--no-first-run": "",
            "--enable-precise-memory-info": "",
            "--js-flags": "--expose-gc",
        }
        if headless:
            switches.update(headless_switches)
        if touch_enabled:
            switches["--touch-events"] = ""
        if debug is not False:
            switches["--auto-open-devtools-for-tabs"] = ""
            switches["--start-fullscreen"] = ""

        cmd = [self.executable]
        cmd += ["%s=%s" % (k, v) if v else k for k, v in switches.items()]
        url = "about:blank"
        cmd.append(url)
        _debug.logic(
            "test.browser.switches",
            headless=headless,
            touch=touch_enabled,
            debug=debug is not False,
            count=len(switches),
        )
        try:
            proc, devtools_port = self._spawn_chrome(cmd)
        except OSError:
            _debug.logic("test.browser.spawn_failed", reason="oserror")
            raise InfrastructureUnavailable("%s not found" % cmd[0]) from None
        self._logger.info("Chrome pid: %s", proc.pid)
        self._logger.info(
            "Chrome headless temporary user profile dir: %s", self.user_data_dir
        )

        return proc, devtools_port

    def _json_command(self, command: str, timeout: int = 3) -> Any:
        url = f"http://{HOST}:{self.devtools_port}/json/{command}".rstrip("/")
        self._logger.info("Issuing json command %s", url)
        delay = 0.1
        tries = 0
        failure_info = None
        message = None
        deadline = time.monotonic() + timeout
        span = _debug.perf("test.browser.json_command", command=command or "list")
        with span:
            while time.monotonic() < deadline:
                if self.chrome.poll() is not None:
                    message = "Chrome crashed at startup"
                    break
                try:
                    r = requests.get(url, timeout=3)
                    if r.ok:
                        span.set(tries=tries, ok=True)
                        return r.json()
                    message = f"Chrome debugger answered with HTTP {r.status_code}"
                except requests.ConnectionError as e:
                    failure_info = str(e)
                    message = (
                        "Connection Error while trying to connect to Chrome debugger"
                    )
                except requests.exceptions.ReadTimeout as e:
                    failure_info = str(e)
                    message = (
                        "Connection Timeout while trying to connect to Chrome debugger"
                    )
                    break

                time.sleep(delay)
                delay *= 1.5
                tries += 1
            span.set(tries=tries, ok=False, message=message)
        _debug.logic("test.browser.json_command_failed", command=command or "list")
        self._logger.error("%s after %s tries", message, tries)
        if failure_info:
            self._logger.info(failure_info)
        self.stop()
        raise InfrastructureUnavailable("Error during Chrome headless connection")

    def _open_websocket(self) -> Any:
        version = self._json_command("version")
        self._logger.info("Browser version: %s", version["Browser"])

        start = time.monotonic()
        polls = 0  # debuglog
        while (time.monotonic() - start) < 5.0:
            polls += 1  # debuglog
            ws_url = next(
                (
                    target["webSocketDebuggerUrl"]
                    for target in self._json_command("")
                    if target["type"] == "page"
                    if target["url"] == "about:blank"
                ),
                None,
            )
            if ws_url:
                break

            time.sleep(0.1)
        else:
            _debug.logic("test.browser.page_target_missing", polls=polls)
            self.stop()
            raise InfrastructureUnavailable(
                "Error during Chrome connection: never found 'page' target"
            )

        self._logger.info("Websocket url found: %s", ws_url)
        with _debug.perf(
            "test.browser.open_websocket",
            version=version["Browser"],
            polls=polls,
        ) as span:
            ws = websocket.create_connection(
                ws_url, enable_multithread=True, suppress_origin=True
            )
            try:
                span.set(status=ws.getstatus())
                if ws.getstatus() != 101:
                    raise InfrastructureUnavailable(
                        "Cannot connect to chrome dev tools"
                    )
                ws.settimeout(0.01)
            except BaseException:
                ws.close()
                raise
        return ws

    def _receive(self, dbname: str) -> None:
        current_worker_thread().dbname = dbname
        while True:
            try:
                msg = self.ws.recv()
                if not msg:
                    continue
                self._logger.debug("\n<- %s", msg)
            except websocket.WebSocketTimeoutException:
                continue
            except websocket.WebSocketConnectionClosedException as e:
                settled = self._result.done()
                cancelled = 0  # debuglog
                if not settled:
                    del self.ws
                    self._result.set_exception(e)
                    while True:
                        try:
                            _, pending = self._responses.popitem()
                        except KeyError:
                            break
                        else:
                            pending.cancel()
                            cancelled += 1  # debuglog
                _debug.lifecycle(
                    "test.browser.receiver_closed",
                    settled=settled,
                    cancelled=cancelled,
                )
                return
            except Exception as e:
                _debug.logic(
                    "test.browser.receiver_error",
                    error=type(e).__name__,
                    settled=self._result.done(),
                    connected=getattr(getattr(self, "ws", None), "connected", None),
                )
                if isinstance(e, ConnectionResetError) and self._result.done():
                    return
                if self.ws.connected:
                    self._result.set_exception(e)
                    raise
                self._result.cancel()
                return

            res = json.loads(msg)
            request_id = res.get("id")
            try:
                if request_id is None:
                    handler = self._handlers.get(res["method"])
                    _debug.pipeline(
                        "test.browser.event",
                        method=res["method"],
                        handled=handler is not None,
                    )
                    if handler:
                        handler(**res["params"])
                elif f := self._responses.pop(request_id, None):
                    _debug.pipeline(
                        "test.browser.response",
                        id=request_id,
                        error="error" in res,
                        pending=len(self._responses),
                    )
                    if "result" in res:
                        f.set_result(res["result"])
                    else:
                        f.set_exception(ChromeBrowserException(res["error"]["message"]))
                else:
                    _debug.logic("test.browser.response_unclaimed", id=request_id)
            except Exception as e:
                _debug.logic(
                    "test.browser.dispatch_failed",
                    method=res.get("method"),
                    error=type(e).__name__,
                )
                _logger.exception(
                    "While processing message %s",
                    shorten(str(msg), 500, placeholder="..."),
                )

    def _websocket_request(
        self, method: str, *, params: dict | None = None, timeout: float | None = None
    ) -> Any:
        assert threading.get_ident() != self._receiver.ident, (
            "_websocket_request must not be called from the consumer thread"
        )
        if not hasattr(self, "ws"):
            return None

        if timeout is None:
            timeout = 10.0 * self.throttling_factor
        f = self._websocket_send(method, params=params, with_future=True)
        if f is None:
            return None
        with _debug.perf("test.browser.request", method=method, timeout=timeout):
            try:
                return f.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                _debug.logic("test.browser.request_timeout", method=method)
                raise TimeoutError(f"{method}({params or ''})") from None

    def _websocket_requires_result(
        self, method: str, *, params: dict | None = None, timeout: float | None = None
    ) -> Any:
        response = self._websocket_request(method, params=params, timeout=timeout)
        if response is not None:
            return response

        exc = None
        if self._result.done() and not self._result.cancelled():
            exc = self._result.exception()
        _debug.logic(
            "test.browser.no_result",
            method=method,
            settled=self._result.done(),
            error=type(exc).__name__ if exc else None,
        )
        raise exc or ChromeBrowserException(
            f"the devtools websocket closed before {method} answered"
        )

    def _websocket_send(
        self, method: str, *, params: dict | None = None, with_future: bool = False
    ) -> Future | None:
        if not hasattr(self, "ws"):
            _debug.logic("test.browser.send_without_socket", method=method)
            return None

        result = None
        request_id = next(self._request_id)
        if with_future:
            result = self._responses[request_id] = Future()
        payload = {"method": method, "id": request_id}
        if params:
            payload["params"] = params
        self._logger.debug("\n-> %s", payload)
        _debug.pipeline(
            "test.browser.send", method=method, id=request_id, future=with_future
        )
        self.ws.send(json.dumps(payload))
        return result

    def _handle_service_worker_error(self, errorMessage: dict, **kw: Any) -> None:
        source = errorMessage.get("sourceURL") or ""
        if source.startswith("chrome-extension://"):
            _debug.logic("test.browser.sw_error_ignored", source=source)
            return
        _debug.logic("test.browser.sw_error", source=source or None)
        self._logger.getChild("browser").error(
            "Service worker error: %s (%s:%s:%s)",
            errorMessage.get("errorMessage"),
            source or "<no source>",
            errorMessage.get("lineNumber"),
            errorMessage.get("columnNumber"),
        )

    def _handle_request_paused(self, **params: Any) -> None:
        url = params["request"]["url"]
        if url.startswith(f"http://{HOST}"):
            cmd = "Fetch.continueRequest"
            response = {}
        else:
            cmd = "Fetch.fulfillRequest"
            response = self.test_case.prepare_proxy_response(url)
        _debug.pipeline(
            "test.browser.fetch",
            action="continue" if cmd == "Fetch.continueRequest" else "fulfill",
            method=params["request"].get("method"),
            url=url,
        )
        try:
            self._websocket_send(
                cmd, params={"requestId": params["requestId"], **response}
            )
        except websocket.WebSocketConnectionClosedException:
            _debug.logic("test.browser.fetch_socket_closed", url=url)
        except OSError:
            _debug.logic("test.browser.fetch_oserror", url=url)
            _logger.info(
                "Websocket error while handling request %s",
                params["request"]["url"],
            )

    def _handle_console(
        self,
        type: str,
        args: list | None = None,
        stackTrace: dict | None = None,
        **kw: Any,
    ) -> None:
        if args:
            arg0, args = str(self._from_remoteobject(args[0])), args[1:]
        else:
            arg0, args = "", []
        formatted = [re.sub(r"%[%sdfoOc]", self.console_formatter(args), arg0)]
        formatted.extend(str(self._from_remoteobject(arg)) for arg in args)
        message = " ".join(formatted)
        stack = "".join(self._format_stack({"type": type, "stackTrace": stackTrace}))
        if stack:
            message += "\n" + stack

        log_type = type
        _logger = self._logger.getChild("browser")
        if self._result.done() and IGNORED_MSGS(message):
            log_type = "dir"
        _debug.logic(
            "test.browser.console",
            type=type,
            level=log_type,
            after_done=self._result.done(),
            size=len(message),
            stack=bool(stack),
        )
        _logger.log(
            self._TO_LEVEL.get(log_type, logging.INFO),
            "%s%s",
            "Error received after termination: " if self._result.done() else "",
            message,
        )

        if log_type == "error":
            if self.error_checker and not self.error_checker(message):
                # an error the checker waves through is the page's own
                # reporting (a HOOT verdict line, say), not a failure: it
                # must neither settle the run nor poison its success signal
                _debug.logic("test.browser.console_error", outcome="ignored_by_checker")
                return
            self.had_failure = True
            if self._result.done():
                _debug.logic("test.browser.console_error", outcome="after_done")
                return
            _debug.logic(
                "test.browser.console_error",
                outcome="failed",
                checked=self.error_checker is not None,
            )
            self.take_screenshot()
            self._settle_exception(ChromeBrowserException(message))
        elif message == self.success_signal:
            _debug.logic("test.browser.success_signal", signal=self.success_signal)
            self._handle_success_signal(_logger)

    def _handle_success_signal(self, _logger: logging.Logger) -> None:

        @run_coroutine
        def _get_heap():
            yield self._websocket_send("HeapProfiler.collectGarbage", with_future=True)
            r = yield self._websocket_send("Runtime.getHeapUsage", with_future=True)
            _logger.info("heap %d (allocated %d)", r["usedSize"], r["totalSize"])

        @run_coroutine
        def _report_dirty_form():
            node_id = 0

            with contextlib.suppress(Exception):
                d = yield self._websocket_send(
                    "DOM.getDocument", params={"depth": 0}, with_future=True
                )
                form = yield self._websocket_send(
                    "DOM.querySelector",
                    params={
                        "nodeId": d["root"]["nodeId"],
                        "selector": ".o_form_dirty",
                    },
                    with_future=True,
                )
                node_id = form["nodeId"]

            _debug.logic("test.browser.dirty_form", found=bool(node_id))
            if node_id:
                self.take_screenshot("unsaved_form_")
                msg = """\
Tour finished with a dirty form view being open.

Dirty form views are automatically saved when the page is closed, \
which leads to stray network requests and inconsistencies."""
                if self._result.done():
                    _logger.error("%s", msg)
                else:
                    self._settle_exception(ChromeBrowserException(msg))
                return

            if not self._result.done():
                self._settle_result(True)
            elif not self._result.cancelled() and self._result.exception() is None:
                _debug.logic("test.browser.success_twice")
                _logger.error("Tried to make the tour successful twice.")

    def _handle_exception(self, exceptionDetails: dict, timestamp: float) -> None:
        message = exceptionDetails["text"]
        exception = exceptionDetails.get("exception")
        if exception:
            message += str(self._from_remoteobject(exception))
        exceptionDetails["type"] = "trace"
        stack = "".join(self._format_stack(exceptionDetails))
        if stack:
            message += "\n" + stack

        if self._result.done():
            ignored = bool(IGNORED_MSGS(message))
            _debug.logic("test.browser.exception", after_done=True, ignored=ignored)
            if not ignored:
                self._logger.getChild("browser").error(
                    "Exception received after termination: %s", message
                )
            return

        _debug.logic("test.browser.exception", after_done=False, size=len(message))
        self.take_screenshot()
        self._settle_exception(ChromeBrowserException(message))

    def _handle_frame_stopped_loading(self, frameId: str) -> None:
        wait = self._frames.pop(frameId, None)
        _debug.lifecycle(
            "test.browser.frame_stopped", frame=frameId, awaited=wait is not None
        )
        if wait:
            wait()

    _TO_LEVEL = {
        "debug": logging.DEBUG,
        "log": logging.INFO,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "dir": RUNBOT,
    }

    def take_screenshot(self, prefix: str = "sc_") -> Future[dict] | None:
        def handler(f):
            try:
                base_png = f.result(timeout=0)["data"]
            except Exception as e:
                _debug.logic(
                    "test.browser.screenshot_failed",
                    prefix=prefix,
                    error=type(e).__name__,
                )
                self._logger.log(RUNBOT, "Couldn't capture screenshot: %s", e)
                return
            if not base_png:
                _debug.logic(
                    "test.browser.screenshot_failed", prefix=prefix, empty=True
                )
                self._logger.log(
                    RUNBOT,
                    "Couldn't capture screenshot: expected image data, got %r",
                    base_png,
                )
                return
            decoded = binascii.a2b_base64(base_png)
            save_test_file(
                type(self.test_case).__name__,
                decoded,
                prefix,
                logger=self._logger,
            )

        self._logger.info("Asking for screenshot")
        f = self._websocket_send("Page.captureScreenshot", with_future=True)
        _debug.lifecycle("test.browser.screenshot", prefix=prefix, sent=f is not None)
        if f:
            f.add_done_callback(handler)
        return f

    def set_cookie(
        self,
        name: str,
        value: str,
        path: str,
        domain: str,
        *,
        http_only: bool = False,
    ) -> None:
        params: dict[str, Any] = {
            "name": name,
            "value": value,
            "path": path,
            "domain": domain,
        }
        if http_only:
            params["httpOnly"] = True
        _debug.lifecycle(
            "test.browser.cookie_set", name=name, domain=domain, http_only=http_only
        )
        self._websocket_request("Network.setCookie", params=params)

    def remove_cookie(self, name: str, **kwargs: str) -> None:
        params = {k: v for k, v in kwargs.items() if k in ["url", "domain", "path"]}
        params["name"] = name
        _debug.lifecycle("test.browser.cookie_removed", name=name, scope=sorted(params))
        self._websocket_request("Network.deleteCookies", params=params)

    def _wait_ready(self, ready_code: str | None = None, timeout: float = 60) -> bool:
        timeout *= self.throttling_factor
        ready_code = ready_code or "document.readyState === 'complete'"
        self._logger.info('Evaluate ready code "%s"', ready_code)
        start_time = time.monotonic()
        result = None
        polls = 0
        span = _debug.perf("test.browser.wait_ready", timeout=timeout)
        with span:
            while True:
                taken = time.monotonic() - start_time
                if taken > timeout:
                    break

                polls += 1
                try:
                    result = self._websocket_requires_result(
                        "Runtime.evaluate",
                        params={
                            "expression": "try { %s } catch {}" % ready_code,
                            "awaitPromise": True,
                        },
                        timeout=timeout - taken,
                    )["result"]
                except CancelledError:
                    exc = self._result.done() and self._result.exception()
                    if exc:
                        span.set(ready=False, polls=polls, last="settled_exception")
                        raise exc from None
                    result = "cancelled"
                except TimeoutError:
                    result = "evaluate timeout"
                    _debug.logic("test.browser.ready_poll", outcome="evaluate_timeout")
                    continue
                except ChromeBrowserException as evaluate_error:
                    if not TARGET_GONE(str(evaluate_error)):
                        span.set(ready=False, polls=polls, last="evaluate_error")
                        raise
                    result = "target navigated while evaluating"
                    _debug.logic("test.browser.ready_poll", outcome="target_gone")
                    continue

                if result == {"type": "boolean", "value": True}:
                    if taken > 2:
                        self._logger.info(
                            "The ready code took too much time: %.2fs",
                            time.monotonic() - start_time,
                        )
                    span.set(ready=True, polls=polls)
                    return True

                time.sleep(0.05)

            exc = self._result.done() and self._result.exception()
            span.set(ready=False, polls=polls, last=str(result), settled=bool(exc))
        if exc:
            raise exc from None
        self.take_screenshot(prefix="sc_failed_ready_")
        self._logger.info("Ready code last try result: %s", result)
        return False

    def _wait_code_ok(
        self, code: str, timeout: float, error_checker: Callable | None = None
    ) -> None:
        timeout *= self.throttling_factor
        self.error_checker = error_checker
        self._logger.info('Evaluate test code "%s"', code)
        start = time.monotonic()
        span = _debug.perf(
            "test.browser.wait_code",
            timeout=timeout,
            code=bool(code),
            error_checker=error_checker is not None,
        )
        with span:
            try:
                res = self._websocket_requires_result(
                    "Runtime.evaluate",
                    params={
                        "expression": code,
                        "awaitPromise": True,
                    },
                    timeout=timeout,
                )["result"]
            except TimeoutError as evaluate_timeout:
                span.set(outcome="evaluate_timeout")
                self.take_screenshot()
                self.screencaster.save()
                raise ChromeBrowserException(
                    "Script timeout exceeded"
                ) from evaluate_timeout
            span.set(evaluate_ms=(time.monotonic() - start) * 1000.0)
            if res.get("subtype") == "error":
                span.set(outcome="code_error")
                raise ChromeBrowserException("Running code returned an error: %s" % res)

            err: Exception = ChromeBrowserException("failed")
            try:
                if (
                    self._result.result(max(0.0, start + timeout - time.monotonic()))
                    and not self.had_failure
                ):
                    span.set(outcome="success")
                    return
            except CancelledError:
                span.set(outcome="cancelled")
                return
            except ChromeBrowserException:
                span.set(outcome="browser_exception")
                self.screencaster.save()
                raise
            except Exception as e:
                err = e

            span.set(
                outcome="timeout"
                if isinstance(err, concurrent.futures.TimeoutError)
                else "unknown",
                had_failure=self.had_failure,
            )
        self.take_screenshot()
        self.screencaster.save()

        if isinstance(err, concurrent.futures.TimeoutError):
            raise ChromeBrowserException("Script timeout exceeded") from err
        raise ChromeBrowserException("Unknown error") from err

    def navigate_to(self, url: str, wait_stop: bool = False) -> None:
        self._logger.info('Navigating to: "%s"', url)
        with _debug.perf("test.browser.navigate", url=url, wait_stop=wait_stop) as span:
            nav_result = self._websocket_request(
                "Page.navigate",
                params={"url": url},
                timeout=20.0 * self.throttling_factor,
            )
            self._logger.info("Navigation result: %s", nav_result)
            span.set(frame=(nav_result or {}).get("frameId"))
            if wait_stop:
                frame_id = nav_result["frameId"]
                e = threading.Event()
                self._frames[frame_id] = e.set
                self._logger.info("Waiting for frame %r to stop loading", frame_id)
                span.set(stopped=e.wait(10 * self.throttling_factor))

    def _from_remoteobject(self, arg: dict) -> Any:
        objtype = arg["type"]
        subtype = arg.get("subtype")
        if objtype == "undefined":
            return "undefined"
        elif objtype != "object" or subtype not in (None, "array"):
            return arg.get("value", arg.get("description", arg))
        elif subtype == "array":
            return "[%s]" % ", ".join(
                repr(p["value"]) if p["type"] == "string" else str(p["value"])
                for p in arg.get("preview", {}).get("properties", [])
                if re.match(r"\d+", p["name"])
            )
        return "%s(%s)" % (
            arg.get("className") or "object",
            ", ".join(
                "%s=%s"
                % (
                    p["name"],
                    repr(p["value"]) if p["type"] == "string" else p["value"],
                )
                for p in arg.get("preview", {}).get("properties", [])
                if p.get("value") is not None
            ),
        )

    LINE_PATTERN = "\tat %(functionName)s (%(url)s:%(lineNumber)d:%(columnNumber)d)\n"

    def _format_stack(self, logrecord: dict) -> Generator[str]:
        if logrecord["type"] != "trace":
            return

        trace = logrecord.get("stackTrace")
        while trace:
            for f in trace["callFrames"]:
                yield self.LINE_PATTERN % f
            trace = trace.get("parent")

    def console_formatter(self, args: list) -> Callable:
        if not args:
            return lambda m: m[0]

        def replacer(m):
            fmt = m[0][1]
            if fmt == "%":
                return "%"
            if fmt in "sdfoOc":
                if not args:
                    return ""
                repl = args.pop(0)
                if fmt == "c":
                    return ""
                return str(self._from_remoteobject(repl))
            return m[0]

        return replacer


class NoScreencast:
    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def save(self) -> None:
        pass

    def __call__(self, sessionId: str, data: str, metadata: dict) -> None:
        pass


class Screencaster:
    def __init__(self, browser: ChromeBrowser, directory: str):
        self.stopped = False
        self.browser: ChromeBrowser = browser
        self._logger: logging.Logger = browser._logger
        self.directory = pathlib.Path(directory, get_db_name(), "screencasts")
        ts = datetime.now()
        self.frames_dir = self.directory / f"frames-{ts:%Y%m%dT%H%M%S.%f}"
        self.frames: list[dict[str, Any]] = []

    def start(self) -> None:
        self._logger.info("Starting screencast")
        _debug.lifecycle("test.screencast.start", dir=str(self.frames_dir))
        self.frames_dir.mkdir(parents=True, exist_ok=True)
        self.browser._websocket_send("Page.startScreencast")

    def __call__(self, sessionId: str, data: str, metadata: dict) -> None:
        self.browser._websocket_send(
            "Page.screencastFrameAck", params={"sessionId": sessionId}
        )
        if self.stopped:
            return
        outfile = self.frames_dir / f"frame_{len(self.frames):05d}.png"
        try:
            outfile.write_bytes(binascii.a2b_base64(data.encode()))
        except FileNotFoundError:
            return
        self.frames.append(
            {"file_path": outfile, "timestamp": metadata.get("timestamp")}
        )

    def stop(self) -> None:
        if self.stopped:
            return
        self.browser._websocket_send("Page.stopScreencast")
        self.stopped = True
        _debug.lifecycle("test.screencast.stop", frames=len(self.frames), saved=False)
        if self.frames_dir.is_dir():
            shutil.rmtree(self.frames_dir, ignore_errors=True)

    def save(self) -> None:
        if self.stopped:
            _debug.logic("test.screencast.save_after_stop")
            return
        self.browser._websocket_send("Page.stopScreencast")
        deadline = time.monotonic() + 5
        frame_count = -1
        while time.monotonic() < deadline and len(self.frames) != frame_count:
            frame_count = len(self.frames)
            time.sleep(0.5)
        self.stopped = True
        _debug.lifecycle("test.screencast.stop", frames=len(self.frames), saved=True)
        if not self.frames:
            self._logger.debug("No screencast frames to encode")
            return

        frames, self.frames = self.frames, []
        t = time.time()
        duration = 1 / 24
        concat_script_path = self.frames_dir.with_suffix(".txt")
        with concat_script_path.open("w") as concat_file:
            for f, next_frame in zip_longest(frames, islice(frames, 1, None)):
                if f["timestamp"] is not None:
                    end_time = next_frame["timestamp"] if next_frame else t
                    duration = end_time - f["timestamp"]
                concat_file.write(f"file '{f['file_path']}'\nduration {duration}\n")
            concat_file.write(f"file '{frames[-1]['file_path']}'\n")

        try:
            ffmpeg_path = get_executable_path("ffmpeg")
        except OSError:
            _debug.logic("test.screencast.ffmpeg_missing", frames=len(frames))
            self._logger.log(RUNBOT, "Screencast frames in: %s", self.frames_dir)
            return

        outfile = self.frames_dir.with_suffix(".mp4")
        span = _debug.perf("test.screencast.encode", frames=len(frames))
        try:
            with span:
                subprocess.run(
                    [
                        ffmpeg_path,
                        "-y",
                        "-loglevel",
                        "warning",
                        "-f",
                        "concat",
                        "-safe",
                        "0",
                        "-i",
                        concat_script_path,
                        "-vf",
                        "pad=ceil(iw/2)*2:ceil(ih/2)*2",
                        "-c:v",
                        "libx265",
                        "-x265-params",
                        "lossless=1",
                        outfile,
                    ],
                    check=True,
                )
        except subprocess.CalledProcessError:
            self._logger.error(
                "Failed to encode screencast, screencast frames in %s",
                self.frames_dir,
            )
        else:
            concat_script_path.unlink()
            shutil.rmtree(self.frames_dir, ignore_errors=True)
            self._logger.log(RUNBOT, "Screencast in: %s", outfile)


@lru_cache(1)
def _get_browser_executable_path():
    browser_bin_path = os.environ.get("ODOO_BROWSER_BIN")
    if browser_bin_path and pathlib.Path(browser_bin_path).exists():
        _debug.logic("test.browser.executable", source="env", path=browser_bin_path)
        return browser_bin_path
    system = platform.system()
    if system == "Linux":
        for bin_ in [
            "google-chrome",
            "chromium",
            "chromium-browser",
            "google-chrome-stable",
        ]:
            try:
                path = get_executable_path(bin_)
            except OSError:
                continue
            _debug.logic("test.browser.executable", source="linux", path=path)
            return path

    elif system == "Darwin":
        bins = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
        for bin_ in bins:
            if pathlib.Path(bin_).exists():
                return bin_

    elif system == "Windows":
        bins = [
            "%ProgramFiles%\\Google\\Chrome\\Application\\chrome.exe",
            "%ProgramFiles(x86)%\\Google\\Chrome\\Application\\chrome.exe",
            "%LocalAppData%\\Google\\Chrome\\Application\\chrome.exe",
        ]
        for bin_ in bins:
            bin_ = os.path.expandvars(bin_)
            if pathlib.Path(bin_).exists():
                return bin_

    raise InfrastructureUnavailable("Chrome executable not found")
