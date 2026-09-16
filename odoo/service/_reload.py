from __future__ import annotations

import contextlib
import os
import selectors
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

from odoo.libs.debug_log import DebugLog
from odoo.tools.misc import stripped_sys_argv

from . import _process_state
from ._env import INHERITED_SOCKET_FD, INHERITED_WEBSOCKET_FD, get_env_float
from ._limits import get_graceful_stop_timeout
from ._sdnotify import notify_ready, notify_reloading

if TYPE_CHECKING:
    from ._prefork import PreforkServer

_debug = DebugLog(__name__)

RELOAD_TIMEOUT_S = 60.0
"""How long a reload waits for the replacement to preload and report ready.

Measured 2026-09-15 on a 217-module database: the candidate answers in
2.7 s, so this is a bound on a hung candidate, not a budget the preload
spends.  The old generation keeps serving throughout the wait, and a
deployment whose preload genuinely needs longer raises `ODOO_RELOAD_TIMEOUT`.
"""


class GenerationHandoff:
    """The prefork master's other generation, across a SIGHUP reload.

    The process systemd started stays the supervisor for its whole life: on
    SIGHUP it spawns a candidate on the inherited listening socket, keeps
    its own workers serving while the candidate preloads, promotes it only
    once every worker of the candidate is ready, and from then on merely
    watches the replacement.  A replacement that receives a SIGHUP asks the
    supervisor to reload, so the chain never grows.  The candidate reports
    readiness through one pipe end it inherits; this object owns that end
    on both sides.
    """

    __slots__ = (
        "candidate",
        "master",
        "reader",
        "ready_fd",
        "replacement",
        "supervisor",
    )

    def __init__(self, master: PreforkServer) -> None:
        self.master = master
        self.supervisor = int(os.environ.pop("ODOO_RELOAD_SUPERVISOR_PID", "0"))
        ready_fd = os.environ.pop("ODOO_RELOAD_READY_FD", None)
        self.ready_fd: int | None = int(ready_fd) if ready_fd else None
        self.candidate: subprocess.Popen | None = None
        self.replacement: subprocess.Popen | None = None
        self.reader: tuple[int, selectors.BaseSelector] | None = None

    @property
    def is_supervised(self) -> bool:
        return bool(self.supervisor)

    @property
    def awaits_ready(self) -> bool:
        return self.ready_fd is not None

    def owns(self, pid: int) -> subprocess.Popen | None:
        for process in (self.candidate, self.replacement):
            if process is not None and process.pid == pid:
                return process
        return None

    def record_exit(self, pid: int, status: int) -> bool:
        process = self.owns(pid)
        if process is None:
            return False
        process.returncode = os.waitstatus_to_exitcode(status)
        _debug.lifecycle(
            "prefork.generation_exited",
            pid=pid,
            returncode=process.returncode,
            candidate=process is self.candidate,
        )
        return True

    def forward(self, sig: int) -> None:
        if self.replacement is not None:
            self.replacement.send_signal(sig)

    def request(self) -> None:
        # A SIGHUP reached this master.  A replacement generation asks the
        # original supervisor to do the reload, so the chain never grows.
        _process_state.set_phoenix(False)
        _debug.lifecycle("prefork.reload_requested", supervisor=self.supervisor)
        if self.supervisor:
            os.kill(self.supervisor, signal.SIGHUP)
            return
        notify_reloading()
        try:
            self.promote()
        except Exception as exc:
            self.master.logger.exception("Reload failed; keeping current generation")
            _debug.logic("prefork.reload.failed", error=type(exc).__name__)
        finally:
            # Serving again either way: on the new generation, or still on
            # the one that was never stopped.
            notify_ready()

    def promote(self) -> bool:
        master = self.master
        master.logger.info("Reloading server")
        read_fd, write_fd = os.pipe2(os.O_CLOEXEC)
        try:
            self.candidate = self._spawn_candidate(write_fd)
            os.close(write_fd)
            write_fd = -1
            timeout = get_env_float(
                "ODOO_RELOAD_TIMEOUT",
                RELOAD_TIMEOUT_S,
                minimum=1.0,
                logger=master.logger,
            )
            _debug.pipeline(
                "prefork.reload.candidate_spawned",
                pid=self.candidate.pid,
                timeout=timeout,
            )
            if not self._await_candidate(self.candidate, read_fd, timeout):
                if master.shutdown_requested:
                    reason = "shutdown_requested"
                    cause = "a shutdown was requested"
                elif self.candidate.poll() is not None:
                    reason = "candidate_exited"
                    cause = (
                        f"the replacement exited with {self.candidate.returncode} "
                        f"before it was ready"
                    )
                else:
                    reason = "timed_out"
                    cause = (
                        f"the replacement was not ready after {timeout:.0f}s "
                        f"(ODOO_RELOAD_TIMEOUT)"
                    )
                master.logger.error(
                    "Reload aborted: %s; keeping current workers", cause
                )
                _debug.logic(
                    "prefork.reload.aborted",
                    reason=reason,
                    returncode=self.candidate.returncode,
                    timeout=timeout,
                )
                return False
            master.logger.info("New server has started")
            _debug.lifecycle(
                "prefork.reload.promoted",
                pid=self.candidate.pid,
                replaced_previous=self.replacement is not None,
            )
            if self.replacement is not None:
                self.stop_generation(self.replacement)
            else:
                master.retire_own_generation()
            self.replacement = self.candidate
            self.candidate = None
            return True
        finally:
            self.reader = None
            os.close(read_fd)
            if write_fd >= 0:
                os.close(write_fd)
            if self.candidate is not None:
                _debug.logic(
                    "prefork.reload.candidate_discarded", pid=self.candidate.pid
                )
                self.stop_generation(self.candidate, graceful=False)
                self.candidate = None

    def _spawn_candidate(self, ready_fd: int) -> subprocess.Popen:
        master = self.master
        env = dict(os.environ)
        env["ODOO_RELOAD_SUPERVISOR_PID"] = str(master.pid)
        env["ODOO_RELOAD_READY_FD"] = str(ready_fd)
        pass_fds = [ready_fd]
        for name, sock in (
            (INHERITED_SOCKET_FD, master.socket),
            (INHERITED_WEBSOCKET_FD, master.websocket_socket),
        ):
            if sock is not None:
                env[name] = str(sock.fileno())
                pass_fds.append(sock.fileno())
        args = stripped_sys_argv()
        if not args or args[0] not in (sys.executable, Path(sys.executable).name):
            args.insert(0, sys.executable)
        return subprocess.Popen(
            args, env=env, pass_fds=pass_fds, start_new_session=True
        )

    def _await_candidate(
        self, candidate: subprocess.Popen, read_fd: int, timeout: float
    ) -> bool:
        master = self.master
        deadline = time.monotonic() + timeout
        with selectors.DefaultSelector() as selector:
            self.reader = (read_fd, selector)
            selector.register(read_fd, selectors.EVENT_READ)
            while time.monotonic() < deadline:
                # Shutdown must not wait for a stuck preload's deadline.
                if master.shutdown_requested:
                    _debug.logic(
                        "prefork.reload.aborted",
                        reason="shutdown_requested",
                        pid=candidate.pid,
                    )
                    return False
                if self.replacement is None:
                    # The first generation still depends on this master
                    # while the candidate preloads: keep it staffed.
                    master.supervise_once()
                if selector.select(min(0.1, max(0, deadline - time.monotonic()))):
                    promoted = os.read(read_fd, 1) == b"1"
                    _debug.pipeline(
                        "prefork.reload.candidate_answered",
                        pid=candidate.pid,
                        promoted=promoted,
                        waited_s=timeout - (deadline - time.monotonic()),
                    )
                    return promoted and candidate.poll() is None
                if candidate.poll() is not None:
                    return False
        return False

    def stop_generation(
        self, process: subprocess.Popen, *, graceful: bool = True
    ) -> None:
        """Bound generation shutdown, including its websocket subprocess."""
        if not graceful:
            # An unready candidate may be stuck in preload and unable to handle
            # queued signals. Do not pause the healthy generation to drain it.
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            _debug.lifecycle(
                "prefork.generation_stopped", pid=process.pid, graceful=False
            )
            return
        with contextlib.suppress(ProcessLookupError):
            process.terminate()
        try:
            process.wait(timeout=get_graceful_stop_timeout(self.master.logger) + 10)
        except subprocess.TimeoutExpired:
            self.master.logger.warning(
                "Generation %s did not stop; killing its process group", process.pid
            )
            _debug.logic("prefork.generation_kill_escalated", pid=process.pid)
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        finally:
            # A crashed master can exit before stopping its descendants.
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            _debug.lifecycle(
                "prefork.generation_stopped",
                pid=process.pid,
                graceful=True,
                returncode=process.returncode,
            )

    def report_ready(self) -> None:
        if self.ready_fd is None:
            return
        fd, self.ready_fd = self.ready_fd, None
        try:
            os.write(fd, b"1")
        finally:
            os.close(fd)
        _debug.lifecycle(
            "prefork.reload_ready_signalled",
            supervisor=self.supervisor,
            workers=len(self.master.workers),
        )

    def close_in_child(self) -> None:
        if self.reader is not None:
            fd, selector = self.reader
            os.close(fd)
            selector.close()
            self.reader = None
        self._close_ready_fd()

    def stop(self) -> None:
        if self.replacement is not None:
            self.stop_generation(self.replacement)
            self.replacement = None
        self._close_ready_fd()

    def _close_ready_fd(self) -> None:
        if self.ready_fd is not None:
            os.close(self.ready_fd)
            self.ready_fd = None
