import errno
import os
import pathlib
import resource
import select
import selectors
import socket
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from odoo.service import _cron, _worker
from odoo.service import settings as server_settings

from .conftest import build_worker


def _open_fds() -> set[int]:
    return {
        int(entry.name)
        for entry in pathlib.Path("/proc/self/fd").iterdir()
        if entry.name.isdigit()
    }


@pytest.fixture
def multi(worker_multi):
    return worker_multi


class TestWorkerConstructionIsAllOrNothing:
    def test_a_failed_second_pipe_closes_the_first(self, multi):
        opened = []

        def one_then_fail():
            if opened:
                raise OSError(errno.EMFILE, "too many open files")
            pipe = os.pipe2(os.O_NONBLOCK | os.O_CLOEXEC)
            opened.append(pipe)
            return pipe

        multi.open_pipe.side_effect = one_then_fail
        before = _open_fds()

        with pytest.raises(OSError):
            _worker.Worker(multi)

        assert _open_fds() <= before, (
            f"the watchdog pipe survived a failed construction: "
            f"{sorted(_open_fds() - before)}. The master retries the spawn, so "
            f"this leaks two descriptors per attempt — under EMFILE, which is "
            f"the condition that caused it"
        )

    def test_a_successful_construction_keeps_both_pipes(self, multi):
        worker = _worker.Worker(multi)
        assert len(set(worker.watchdog_pipe) | set(worker.wakeup_pipe)) == 4
        assert worker.wakeup_pipe[0], worker.wakeup_pipe[1] == worker.wakeup_pipe
        worker.close()

    def test_close_releases_every_descriptor_it_took(self, multi):
        before = _open_fds()
        worker = _worker.Worker(multi)
        assert len(_open_fds() - before) == 4
        worker.close()
        assert _open_fds() <= before

    def test_close_is_idempotent(self, multi):
        worker = _worker.Worker(multi)
        worker.close()
        worker.close()


class TestWorkerSignalDispositions:
    def test_a_quit_signal_only_clears_alive(self, multi):
        worker = _worker.Worker(multi)
        worker.alive = True
        worker.signal_handler(2, None)
        assert worker.alive is False, (
            "the handler must not do the teardown itself: it runs on whatever "
            "stack the signal interrupted"
        )
        worker.close()

    def test_the_cpu_alarm_raises_and_names_the_limit(self, multi):
        worker = _worker.Worker(multi)
        with (
            server_settings.override(limit_time_cpu=77),
            pytest.raises(_worker.CpuTimeLimitExceeded, match="77"),
        ):
            worker.signal_time_expired_handler(24, None)
        worker.close()


class TestCpuRlimitClamp:
    def _apply(self, multi, *, hard, cpu_used=10.0, limit=60):
        worker = _worker.Worker(multi)
        worker.ppid = os.getppid()
        worker.alive = True
        worker.request_max = 0
        worker.request_count = 0
        worker._process_handle = MagicMock()
        res = MagicMock()
        res.RLIM_INFINITY = resource.RLIM_INFINITY
        res.getrusage.return_value = MagicMock(ru_utime=cpu_used, ru_stime=0.0)
        res.getrlimit.return_value = (resource.RLIM_INFINITY, hard)
        with (
            patch.object(_worker, "resource", res),
            server_settings.override(limit_memory_soft=0, limit_time_cpu=limit),
            patch.object(_worker, "get_memory_over_soft_limit", return_value=None),
        ):
            worker.check_limits()
        worker.close()
        return res.setrlimit.call_args.args[1]

    def test_the_soft_limit_is_now_plus_the_budget(self, multi):
        soft, _hard = self._apply(multi, hard=resource.RLIM_INFINITY)
        assert soft == 70, "10s already burned plus a 60s budget"

    def test_it_is_clamped_to_the_hard_ceiling(self, multi):
        soft, hard = self._apply(multi, hard=65)
        assert (soft, hard) == (65, 65), (
            "setrlimit raises ValueError when soft exceeds hard, and this runs "
            "on every check_limits pass — so an unclamped value does not cap "
            "CPU, it kills the worker with a traceback"
        )

    def test_an_infinite_ceiling_is_not_treated_as_a_small_number(self, multi):
        soft, _hard = self._apply(multi, hard=resource.RLIM_INFINITY, cpu_used=1e6)
        assert soft == 1e6 + 60, (
            "RLIM_INFINITY is -1 on Linux, so comparing against it numerically "
            "would clamp every worker to a soft limit of -1"
        )


@pytest.fixture
def started(multi):
    worker = _worker.Worker(multi)
    signal_mod, selectors_mod, psutil_mod, fcntl_mod = (MagicMock() for _ in range(4))
    signal_mod.SIG_DFL = "SIG_DFL"
    with (
        patch.object(_worker, "signal", signal_mod),
        patch.object(_worker, "selectors", selectors_mod),
        patch.object(_worker, "psutil", psutil_mod),
        patch.object(_worker, "fcntl", fcntl_mod),
    ):
        worker.logger = MagicMock()
        worker.start()
        yield worker, signal_mod, selectors_mod, fcntl_mod
    worker.close()


class TestWorkerStart:
    def test_the_quit_and_cpu_signals_get_handlers(self, started):
        worker, signal_mod, _, _ = started
        installed = {
            call.args[0]: call.args[1] for call in signal_mod.signal.call_args_list
        }
        assert installed[signal_mod.SIGINT] == worker.signal_handler
        assert installed[signal_mod.SIGXCPU] == worker.signal_time_expired_handler

    def test_the_masters_own_signals_are_reset_to_default(self, started):
        _, signal_mod, _, _ = started
        installed = {
            call.args[0]: call.args[1] for call in signal_mod.signal.call_args_list
        }
        for name in ("SIGTERM", "SIGHUP", "SIGCHLD", "SIGTTIN", "SIGTTOU"):
            assert installed[getattr(signal_mod, name)] == "SIG_DFL", (
                f"the child inherited the master's {name} disposition; a "
                f"worker that handles SIGCHLD or SIGHUP acts on events meant "
                f"for the master"
            )

    def test_the_wakeup_fd_is_the_workers_own_eintr_pipe(self, started):
        worker, signal_mod, _, _ = started
        signal_mod.set_wakeup_fd.assert_called_once_with(worker.wakeup_pipe[1])

    def test_the_selector_watches_that_pipe(self, started):
        worker, _, selectors_mod, _ = started
        selector = selectors_mod.DefaultSelector.return_value
        assert selector.register.call_args.args[0] == worker.wakeup_pipe[0]

    def test_a_listening_socket_is_marked_cloexec_and_non_blocking(self, multi):
        sock = socket.socket()
        sock.set_inheritable(True)
        multi.socket = sock
        worker = _worker.Worker(multi)
        worker.logger = MagicMock()
        with (
            patch.object(_worker, "signal", MagicMock()),
            patch.object(_worker, "selectors", MagicMock()),
            patch.object(_worker, "psutil", MagicMock()),
        ):
            worker.start()
        assert sock.getblocking() is False, (
            "a blocking accept() in a worker cannot be interrupted by the "
            "watchdog, so the master can only SIGKILL it"
        )
        assert os.get_inheritable(sock.fileno()) is False, (
            "without FD_CLOEXEC the listen socket survives into every "
            "subprocess the worker spawns, which keeps the port bound after a "
            "shutdown"
        )
        worker.close()
        sock.close()


class TestWorkerStop:
    def test_it_closes_the_selector(self, started):
        worker, _, selectors_mod, _ = started
        worker.stop()
        selectors_mod.DefaultSelector.return_value.close.assert_called_once()

    def test_stopping_a_worker_that_never_started_is_not_an_error(self, multi):
        worker = _worker.Worker(multi)
        worker.stop()
        worker.close()


class TestWorkerHttpAcceptErrors:
    def _process(self, multi, exc):
        worker = build_worker(_worker.WorkerHTTP, multi)
        multi.socket = MagicMock()
        multi.socket.accept.side_effect = exc
        worker.process_request = MagicMock()
        return worker

    @pytest.mark.parametrize("code", [errno.EAGAIN, errno.ECONNABORTED])
    def test_routine_accept_failures_are_swallowed(self, multi, code):
        worker = self._process(multi, OSError(code, "transient"))
        worker.process_work()
        worker.process_request.assert_not_called()

    def test_anything_else_propagates(self, multi):
        worker = self._process(multi, OSError(errno.EMFILE, "too many open files"))
        with pytest.raises(OSError, match="too many open files"):
            worker.process_work()

    def test_a_successful_accept_is_handed_on(self, multi):
        worker = build_worker(_worker.WorkerHTTP, multi)
        client, addr = MagicMock(), ("127.0.0.1", 5555)
        multi.socket = MagicMock()
        multi.socket.accept.return_value = (client, addr)
        worker.process_request = MagicMock()
        worker.process_work()
        worker.process_request.assert_called_once_with(client, addr)


class TestAcceptWaitsForTheListenerToBeReadable:
    """A beat that merely timed out, or a signal on the wakeup pipe, is not a
    connection.  Before the gate every idle worker called `accept()` once per
    beat and logged the EAGAIN as a lost race."""

    def _worker(self, multi, ready_fds):
        worker = build_worker(_worker.WorkerHTTP, multi, wakeup_pipe=(40, 41))
        worker._selector = MagicMock()
        worker._selector.select.return_value = [
            (MagicMock(fd=fd), selectors.EVENT_READ) for fd in ready_fds
        ]
        multi.socket = MagicMock()
        multi.socket.accept.return_value = (MagicMock(), ("127.0.0.1", 1))
        worker.process_request = MagicMock()
        return worker

    def test_a_timed_out_beat_does_not_accept(self, multi):
        worker = self._worker(multi, [])
        with patch.object(_worker, "empty_pipe"):
            worker.sleep()
        worker.process_work()
        multi.socket.accept.assert_not_called()

    def test_a_wakeup_pipe_wake_does_not_accept(self, multi):
        worker = self._worker(multi, [40])
        with patch.object(_worker, "empty_pipe"):
            worker.sleep()
        worker.process_work()
        multi.socket.accept.assert_not_called()

    def test_a_readable_listener_accepts(self, multi):
        worker = self._worker(multi, [40, 7])
        with patch.object(_worker, "empty_pipe"):
            worker.sleep()
        worker.process_work()
        multi.socket.accept.assert_called_once()
        worker.process_request.assert_called_once()

    def test_a_direct_call_still_accepts(self, multi):
        worker = self._worker(multi, [])
        worker.process_work()
        multi.socket.accept.assert_called_once()


class TestTheCursorIsReleasedAndTheConnectionIsLeftAlone:
    """Close the cursor.  Do not touch the connection under it.

    Two defects sat here, and the first fix for the first one carried the
    second along:

      1. The connection was closed FIRST.  `BaseCursor._close` rolls back
         before releasing, so on a closed connection that rollback raises and
         the cursor logs "Failed to roll back on cursor close; discarding
         connection" at ERROR with a traceback -- before re-raising, so the
         `suppress(Exception)` at the call site hid the exception and not the
         log.  A real prefork SIGTERM printed two, one per cron/job worker;
         with the cursor closed first, none.
      2. There should be no second close at all.  `_close` ends in
         `pool.give_back(self._cnx, ...)`.  Measured: for `postgres` -- a
         maintenance database, which is what both cron loops connect to --
         `give_back` takes its direct branch and closes the connection itself,
         so `connection.closed` is already True and a second close is dead.
         For a pooled DSN the connection comes back with `closed` False
         because the pool is holding it open for the next borrower, and
         closing it there destroys a live connection.
    """

    @staticmethod
    def _recording_cursor():
        order = []
        cursor = MagicMock()
        cursor.close.side_effect = lambda: order.append("cursor")
        cursor.connection.close.side_effect = lambda: order.append("connection")
        return cursor, order

    def test_the_helper_closes_only_the_cursor(self):
        cursor, order = self._recording_cursor()
        _cron.close_cron_cursor(cursor)
        assert order == ["cursor"]

    def test_a_raising_cursor_close_does_not_escape(self):
        cursor, order = self._recording_cursor()
        cursor.close.side_effect = RuntimeError("already closed")
        _cron.close_cron_cursor(cursor)
        assert order == []

    def test_worker_stop_releases_through_it(self, multi):
        """The clean-teardown site: this is the one that printed on SIGTERM."""
        worker = build_worker(_worker.WorkerCron, multi)
        cursor, order = self._recording_cursor()
        worker.listener = _cron.CronListener("ch", _cron._logger)
        worker.listener._cursor = cursor
        worker.stop()
        assert order == ["cursor"]

    def test_a_failed_listener_open_releases_the_cursor(self):
        """`open_cron_listener` must not leak the cursor when arming fails."""
        cursor, order = self._recording_cursor()
        conn = MagicMock()
        conn.cursor.return_value = cursor
        with (
            patch.object(_cron.db, "db_connect", return_value=conn),
            patch.object(_cron, "arm_cron_listen", side_effect=RuntimeError("boom")),
            pytest.raises(RuntimeError, match="boom"),
        ):
            _cron.open_cron_listener("ch", _cron._logger)
        assert order == ["cursor"]


class TestTheListeningSocketIsWatchedExclusively:
    @staticmethod
    def _epoll_events(epoll_fd, target_fd):
        text = pathlib.Path(f"/proc/self/fdinfo/{epoll_fd}").read_text(encoding="ascii")
        for line in text.splitlines():
            if line.startswith("tfd:") and int(line.split()[1]) == target_fd:
                return int(line.split()[3], 16)
        return None

    @pytest.mark.skipif(not hasattr(select, "EPOLLEXCLUSIVE"), reason="Linux only")
    def test_the_accept_registration_carries_epollexclusive(self):
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        selector = selectors.DefaultSelector()
        try:
            assert _worker.watch_accept(selector, sock) is True
            assert sock in {k.fileobj for k in selector.get_map().values()}
            events = self._epoll_events(selector._selector.fileno(), sock.fileno())
            assert events is not None and events & select.EPOLLEXCLUSIVE, hex(events)
            # The selector still resolves readiness to the socket's key.
            client = socket.create_connection(sock.getsockname())
            try:
                ready = selector.select(timeout=1)
                assert [key.fileobj for key, _ in ready] == [sock]
            finally:
                client.close()
        finally:
            selector.close()
            sock.close()

    def test_a_selector_without_epoll_falls_back_to_a_plain_registration(self):
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        selector = selectors.PollSelector()
        try:
            assert _worker.watch_accept(selector, sock) is False
            assert sock in {k.fileobj for k in selector.get_map().values()}
        finally:
            selector.close()
            sock.close()


class TestTheWorkerCancelsItsOwnOverrun:
    """The main thread only waited on the work thread; now it is the budget
    monitor the master used to be, with SIGKILL as the fallback."""

    def _worker(self, multi, budget):
        worker = build_worker(_worker.WorkerHTTP, multi, pid=4242)
        worker.watchdog_timeout = budget
        multi.beat = 0.05
        return worker

    def _thread(self, alive_for):
        thread = MagicMock()
        thread.name = "Worker WorkerHTTP (4242) workthread"
        thread.start_time = None
        polls = {"n": 0}

        def is_alive():
            polls["n"] += 1
            return polls["n"] <= alive_for

        thread.is_alive.side_effect = is_alive
        thread.join.side_effect = lambda timeout=None: None
        return thread

    def test_work_over_budget_is_cancelled_once_and_the_watchdog_fed(self, multi):
        worker = self._worker(multi, budget=2)
        thread = self._thread(alive_for=4)
        thread.start_time = time.monotonic() - 10
        pings = []
        multi.ping_pipe.side_effect = pings.append
        with patch("odoo.db.cancel_queries_of", return_value=2) as cancel:
            assert worker._supervise_work_thread(thread) is False
        cancel.assert_called_once_with(thread.name)
        assert len(pings) == 4, (
            "the cancel and then the grace feed the master's watchdog"
        )
        assert worker.alive
        message, budget, elapsed, _doing, count, plural = (
            worker.logger.warning.call_args.args
        )
        assert "cancelled %d running quer%s" in message
        assert (budget, count, plural) == (2, 2, "ies") and elapsed > 9

    def test_work_still_stuck_after_the_grace_ends_the_worker(self, multi):
        worker = self._worker(multi, budget=2)
        worker._CANCEL_GRACE_S = 0.0
        thread = self._thread(alive_for=10)
        thread.start_time = time.monotonic() - 10
        with patch("odoo.db.cancel_queries_of", return_value=0):
            assert worker._supervise_work_thread(thread) is True
        assert not worker.alive
        multi.ping_pipe.assert_called_once()

    def test_work_within_budget_is_left_alone(self, multi):
        worker = self._worker(multi, budget=60)
        thread = self._thread(alive_for=3)
        thread.start_time = time.monotonic() - 1
        with patch("odoo.db.cancel_queries_of") as cancel:
            worker._supervise_work_thread(thread)
        cancel.assert_not_called()
        multi.ping_pipe.assert_not_called()

    def test_no_budget_means_no_monitor(self, multi):
        worker = self._worker(multi, budget=None)
        thread = self._thread(alive_for=2)
        thread.start_time = time.monotonic() - 10_000
        with patch("odoo.db.cancel_queries_of") as cancel:
            worker._supervise_work_thread(thread)
        cancel.assert_not_called()

    def test_a_new_unit_of_work_gets_its_own_verdict(self, multi):
        worker = self._worker(multi, budget=2)
        thread = self._thread(alive_for=3)
        first = time.monotonic() - 10
        starts = iter([first, first, None])
        type(thread).start_time = property(lambda self: next(starts, None))
        with patch("odoo.db.cancel_queries_of", return_value=1) as cancel:
            worker._supervise_work_thread(thread)
        assert cancel.call_count == 1

    def test_the_work_loop_stamps_start_time_around_each_unit(self, multi, monkeypatch):
        monkeypatch.setattr(
            threading.current_thread(), "start_time", None, raising=False
        )
        worker = build_worker(_worker.WorkerHTTP, multi, pid=4242)
        seen = []

        def work():
            seen.append(threading.current_thread().start_time is not None)
            worker.alive = False

        worker.check_limits = MagicMock()
        worker.sleep = MagicMock()
        worker.process_work = work
        worker._runloop_exc = None
        with patch.object(_worker.signal, "pthread_sigmask"):
            worker._run_work_loop()
        assert worker._runloop_exc is None, worker._runloop_exc
        assert seen == [True]
        assert threading.current_thread().start_time is None
