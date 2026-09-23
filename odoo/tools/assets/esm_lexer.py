import atexit
import contextlib
import hashlib
import json
import logging
import os
import select
import shutil
import subprocess
import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any

import odoo
from odoo.libs.asset_log import get_asset_logger, log_event
from odoo.libs.debug_log import DebugLog

_lexer_log = get_asset_logger("lexer")
_debug = DebugLog(__name__)

_WORKER_SCRIPT = Path(__file__).parent / "js" / "esm_lexer_worker.mjs"

_REQUEST_TIMEOUT_S = 10.0

_MAX_CONSECUTIVE_FAILURES = 2

_DISABLE_COOLDOWN_S = 60.0


class _LexerWorker:
    def __init__(self) -> None:
        self._proc: subprocess.Popen | None = None
        self._counter = 0
        self._disabled_until = 0.0
        self._consec_failures = 0
        self._inbuf = b""
        self._lock = threading.Lock()

    def _disabled(self) -> bool:
        return time.monotonic() < self._disabled_until

    def _disable(self) -> None:
        self._disabled_until = time.monotonic() + _DISABLE_COOLDOWN_S

    def _forget_after_fork(self) -> None:
        # the worker and its pipes belong to the parent: signalling it or
        # reading its replies from here would take them from the parent
        proc, self._proc = self._proc, None
        self._lock = threading.Lock()
        self._inbuf = b""
        if proc is not None:
            for pipe in (proc.stdin, proc.stdout):
                if pipe is not None:
                    with contextlib.suppress(OSError):
                        pipe.close()

    def _spawn(self) -> subprocess.Popen | None:
        node = shutil.which("node")
        if not node:
            return None
        odoo_root = Path(odoo.__path__[0]).parent
        try:
            proc = subprocess.Popen(
                [node, str(_WORKER_SCRIPT)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=0,
                cwd=odoo_root,
            )
        except OSError:
            return None
        if proc.stdin is None or proc.stdout is None:
            return None
        os.set_blocking(proc.stdin.fileno(), False)
        os.set_blocking(proc.stdout.fileno(), False)
        self._inbuf = b""
        _register_worker_cleanup()
        _debug.lifecycle("esm_lexer.worker_spawned", pid=proc.pid, node=node)
        return proc

    def close(self) -> None:
        with self._lock:
            self._kill()
            self._disabled_until = 0.0
            self._consec_failures = 0

    def _kill(self) -> None:
        proc, self._proc = self._proc, None
        self._inbuf = b""
        if proc is not None:
            with contextlib.suppress(OSError):
                proc.kill()
            with contextlib.suppress(subprocess.TimeoutExpired, OSError):
                proc.wait(timeout=5)
            _debug.lifecycle(
                "esm_lexer.worker_killed",
                pid=proc.pid,
                exit_code=proc.returncode,
                requests=self._counter,
            )

    def _write_all(self, proc: subprocess.Popen, data: bytes, deadline: float) -> None:
        assert proc.stdin is not None
        fd = proc.stdin.fileno()
        view = memoryview(data)
        while view:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("lexer worker stdin write timed out")
            _, writable, _ = select.select([], [fd], [], remaining)
            if not writable:
                raise TimeoutError("lexer worker stdin write timed out")
            try:
                written = os.write(fd, view)
            except BlockingIOError:
                continue
            except OSError as exc:
                raise EOFError("lexer worker closed stdin") from exc
            view = view[written:]

    def _read_line(self, proc: subprocess.Popen, deadline: float) -> str:
        assert proc.stdout is not None
        fd = proc.stdout.fileno()
        while True:
            newline = self._inbuf.find(b"\n")
            if newline >= 0:
                line, self._inbuf = self._inbuf[:newline], self._inbuf[newline + 1 :]
                return line.decode("utf-8")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("lexer worker stdout read timed out")
            readable, _, _ = select.select([fd], [], [], remaining)
            if not readable:
                raise TimeoutError("lexer worker stdout read timed out")
            try:
                chunk = os.read(fd, 65536)
            except BlockingIOError:
                continue
            if not chunk:
                raise EOFError("lexer worker closed stdout")
            self._inbuf += chunk

    def request(self, src: str) -> dict[str, Any] | None:
        if self._disabled() or os.name != "posix":
            return None
        with self._lock:
            for _attempt in range(2):
                proc = self._proc
                if proc is None or proc.poll() is not None:
                    proc = self._proc = self._spawn()
                    if proc is None:
                        self._disable()
                        log_event(
                            _lexer_log,
                            logging.INFO,
                            "worker_unavailable",
                            hint="node + `npm install` provide es-module-lexer;"
                            " using the regex extractor",
                            retry_s=_DISABLE_COOLDOWN_S,
                        )
                        return None
                self._counter += 1
                request_id = self._counter
                deadline = time.monotonic() + _REQUEST_TIMEOUT_S
                try:
                    payload = json.dumps({"id": request_id, "src": src}) + "\n"
                    self._write_all(proc, payload.encode("utf-8"), deadline)
                    line = self._read_line(proc, deadline)
                    response = json.loads(line)
                    if response.get("id") != request_id:
                        raise ValueError("lexer worker desynchronized")
                except Exception as exc:
                    self._kill()
                    self._consec_failures += 1
                    disabled = self._consec_failures >= _MAX_CONSECUTIVE_FAILURES
                    log_event(
                        _lexer_log,
                        logging.WARNING if disabled else logging.DEBUG,
                        "worker_request_failed",
                        err=type(exc).__name__,
                        attempt=_attempt + 1,
                        consecutive=self._consec_failures,
                        disabled=disabled,
                        retry_s=_DISABLE_COOLDOWN_S if disabled else 0,
                    )
                    if disabled:
                        self._consec_failures = 0
                        self._disable()
                        return None
                    continue
                self._consec_failures = 0
                if not response.get("ok"):
                    log_event(
                        _lexer_log,
                        logging.DEBUG,
                        "source_unlexable",
                        err=str(response.get("error", ""))[:200],
                    )
                return response
            return None


_worker = _LexerWorker()
_cleanup_registered = False


def _register_worker_cleanup() -> None:
    global _cleanup_registered  # noqa: PLW0603  atexit hook must be registered exactly once
    if _cleanup_registered:
        return
    _cleanup_registered = True
    atexit.register(close_lexer_worker)
    try:
        from odoo.service.server import CommonServer

        CommonServer.register_on_stop_hook(close_lexer_worker)
    except Exception:
        log_event(
            _lexer_log,
            logging.DEBUG,
            "on_stop_registration_failed",
        )


def close_lexer_worker() -> None:
    _debug.lifecycle("esm_lexer.closed", cached=len(_lex_cache))
    _worker.close()
    clear_lex_cache()


_LEX_CACHE_ENTRIES = 4096

# keyed on a digest: the sources themselves (every JS file of a registry) would
# otherwise stay alive as keys for as long as the cache does
_lex_cache: OrderedDict[bytes, dict[str, Any]] = OrderedDict()
_lex_cache_lock = threading.Lock()


def lex_module(src: str) -> dict[str, Any] | None:
    key = hashlib.blake2b(src.encode("utf-8", "surrogatepass"), digest_size=16).digest()
    with _lex_cache_lock:
        response = _lex_cache.get(key)
        if response is not None:
            _lex_cache.move_to_end(key)
    if response is None:
        with _debug.perf("esm_lexer.lex_miss", source_bytes=len(src)) as span:
            response = _worker.request(src)
            span.set(lexed=response is not None and response.get("ok") is not False)
        if response is None:
            # the worker was unreachable: the next call asks again
            return None
        with _lex_cache_lock:
            _lex_cache[key] = response
            if len(_lex_cache) > _LEX_CACHE_ENTRIES:
                _lex_cache.popitem(last=False)
    return None if response.get("ok") is False else response


def clear_lex_cache() -> None:
    with _lex_cache_lock:
        _debug.lifecycle("esm_lexer.cache_cleared", cached=len(_lex_cache))
        _lex_cache.clear()


def _reset_after_fork() -> None:
    global _lex_cache_lock  # noqa: PLW0603  a lock held by another thread at fork stays held in the child
    _lex_cache_lock = threading.Lock()
    _worker._forget_after_fork()


os.register_at_fork(after_in_child=_reset_after_fork)
