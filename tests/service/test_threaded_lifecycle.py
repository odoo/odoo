import os
import signal
import threading
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from odoo.service import _process_state, _threaded
from odoo.service import settings as server_settings

from .conftest import threaded_server


@pytest.fixture
def server():
    return threaded_server(_process_handle=MagicMock())


class TestWindowsConsoleEventsAreSignals:
    @pytest.mark.parametrize(
        ("event", "sig"),
        [
            (0, signal.SIGINT),
            (1, signal.SIGINT),
            (2, signal.SIGTERM),
            (6, signal.SIGTERM),
        ],
    )
    def test_a_known_event_reaches_the_signal_handler_as_a_signal(
        self, server, event, sig
    ):
        with patch.object(server, "signal_handler") as handler:
            assert server._handle_console_event(event) is True
        handler.assert_called_once_with(sig, None)

    def test_an_unknown_event_is_left_to_the_next_handler(self, server):
        with patch.object(server, "signal_handler") as handler:
            assert server._handle_console_event(99) is False
        handler.assert_not_called()


class TestSignalHandlerBehaviour:
    @pytest.mark.parametrize("sig", [signal.SIGINT, signal.SIGTERM])
    def test_first_quit_signal_unwinds_the_main_loop(self, server, sig):
        with pytest.raises(KeyboardInterrupt):
            server.signal_handler(sig, None)
        assert server.quit_signals_received == 1

    def test_second_quit_signal_forces_the_exit(self, server):
        server.quit_signals_received = 1
        with patch.object(_threaded.os, "_exit", side_effect=SystemExit) as hard_exit:
            with pytest.raises(SystemExit):
                server.signal_handler(signal.SIGTERM, None)
        hard_exit.assert_called_once_with(0)

    def test_sighup_arms_phoenix_before_unwinding(self, server):
        with patch.object(_process_state, "server_phoenix", False):
            with pytest.raises(KeyboardInterrupt):
                server.signal_handler(signal.SIGHUP, None)
            assert _process_state.server_phoenix is True

    def test_sigxcpu_exits_immediately(self, server):
        with patch.object(_threaded.os, "_exit", side_effect=SystemExit) as hard_exit:
            with pytest.raises(SystemExit):
                server.signal_handler(signal.SIGXCPU, None)
        hard_exit.assert_called_once_with(_threaded._SIGXCPU_EXIT_CODE)

    def test_sigxcpu_exits_nonzero_so_a_supervisor_restarts(self, server):
        code = _threaded._SIGXCPU_EXIT_CODE
        assert code != 0, (
            "exiting 0 after a CPU-limit kill tells systemd/Docker the process "
            "stopped cleanly, so Restart=on-failure never fires"
        )
        assert code == 128 + int(signal.SIGXCPU), (
            "the shell convention for 'killed by signal N' is 128+N; keeping it "
            "makes the exit code self-describing in a supervisor's log"
        )


class TestSignalHandlerOnAPlatformWithoutSighup:
    @pytest.fixture
    def windows_signal(self):
        return SimpleNamespace(SIGINT=signal.SIGINT, SIGTERM=signal.SIGTERM)

    def test_an_unrelated_signal_does_not_touch_signal_sighup(
        self, server, windows_signal
    ):
        with (
            patch.object(_threaded, "signal", windows_signal),
            patch.object(_threaded, "SIGHUP_AVAILABLE", False),
        ):
            server.signal_handler(signal.SIGUSR1, None)

    def test_quit_signals_still_work_without_sighup(self, server, windows_signal):
        with (
            patch.object(_threaded, "signal", windows_signal),
            patch.object(_threaded, "SIGHUP_AVAILABLE", False),
        ):
            with pytest.raises(KeyboardInterrupt):
                server.signal_handler(signal.SIGTERM, None)
        assert server.quit_signals_received == 1


class TestStartInstallsTheHandlers:
    @pytest.fixture
    def wired(self, server):
        seen = {}
        cfg = {"http_enable": False, "test_enable": False, "limit_time_cpu": 0}
        with (
            server_settings.override(**cfg),
            patch.object(_threaded.signal, "signal", side_effect=seen.__setitem__),
            patch.object(_threaded, "IS_POSIX", True),
        ):
            server.start()
        return seen, server

    @pytest.mark.parametrize(
        "sig", [signal.SIGINT, signal.SIGTERM, signal.SIGHUP, signal.SIGXCPU]
    )
    def test_quit_and_reload_signals_route_to_the_handler(self, wired, sig):
        seen, server = wired
        assert seen.get(sig) == server.signal_handler, (
            f"{sig!r} is not wired to signal_handler; the process would take the "
            f"OS default action for it — for SIGTERM that is immediate death "
            f"with no shutdown, measured as exit -15 against a real server"
        )

    def test_sigchld_is_not_installed(self, wired):
        seen, _ = wired
        assert signal.SIGCHLD not in seen

    def test_http_is_not_spawned_when_disabled(self, server):
        cfg = {"http_enable": False, "test_enable": False, "limit_time_cpu": 0}
        with (
            server_settings.override(**cfg),
            patch.object(_threaded.signal, "signal"),
            patch.object(server, "spawn_http_server") as spawn,
        ):
            server.start()
        spawn.assert_not_called()

    def test_http_is_spawned_under_test_enable_even_when_stopping(self, server):
        cfg = {"http_enable": True, "test_enable": True, "limit_time_cpu": 0}
        with (
            server_settings.override(**cfg),
            patch.object(_threaded.signal, "signal"),
            patch.object(server, "spawn_http_server") as spawn,
        ):
            server.start(stop=True)
        spawn.assert_called_once()


class TestGracefulStop:
    @pytest.fixture
    def stopped(self, server):
        def _run(**attrs):
            server.__dict__.update(attrs)
            server.httpd = MagicMock(busy_workers=0)
            with (
                patch.object(_threaded.db, "close_all") as close_all,
                patch.object(_threaded, "logging") as log_mod,
                patch.object(_threaded.psutil, "Process") as proc,
            ):
                proc.return_value.children.return_value = []
                super_stop = MagicMock()
                with patch.object(_threaded.CommonServer, "stop", super_stop):
                    server.stop()
            return server, close_all, log_mod, super_stop

        return _run

    def test_wsgi_server_is_shut_down(self, stopped):
        server, _, _, _ = stopped()
        server.httpd.shutdown.assert_called_once_with()

    def test_wsgi_server_is_released_after_shutdown(self, stopped):
        server, _, _, _ = stopped()
        server.httpd.server_close.assert_called_once_with()
        assert server.httpd.mock_calls.index(
            ("shutdown", (), {})
        ) < server.httpd.mock_calls.index(("server_close", (), {}))

    def test_database_connections_are_closed(self, stopped):
        _, close_all, _, _ = stopped()
        close_all.assert_called_once_with()

    def test_registered_stop_hooks_run(self, stopped):
        _, _, _, super_stop = stopped()
        super_stop.assert_called_once()

    def test_logging_is_shut_down(self, stopped):
        _, _, log_mod, _ = stopped()
        log_mod.shutdown.assert_called_once_with()

    def test_reload_announces_a_reload_not_a_shutdown(self, stopped):
        with patch.object(_process_state, "server_phoenix", True):
            server, _, _, _ = stopped()
        said = " ".join(str(c) for c in server.logger.info.call_args_list)
        assert "reload" in said.lower()
        assert "Initiating shutdown" not in said

    def test_stop_after_init_announces_initialization_done(self, stopped):
        server, _, _, _ = stopped(_stop_after_init=True)
        said = " ".join(str(c) for c in server.logger.info.call_args_list)
        assert "Initialization done" in said

    def test_plain_shutdown_tells_the_operator_how_to_force_it(self, stopped):
        server, _, _, _ = stopped()
        said = " ".join(str(c) for c in server.logger.info.call_args_list)
        assert "Initiating shutdown" in said
        assert "again" in said, (
            "the second-signal hint is the only place an operator learns the "
            "shutdown can be forced"
        )

    def test_stop_drains_the_http_server_before_closing_it(self, stopped):
        server, _, _, _ = stopped()
        names = [call[0] for call in server.httpd.mock_calls]
        assert (
            names.index("shutdown") < names.index("drain") < names.index("server_close")
        )

    def test_a_request_over_its_time_limit_is_given_up_on(self, stopped):
        stuck = MagicMock()
        stuck.type = "http"
        stuck.is_alive.return_value = True
        finished = MagicMock()
        finished.type = "http_idle"
        finished.is_alive.return_value = True
        server, _, _, _ = stopped(limits_reached_threads={stuck, finished})
        assert server.httpd.drain.call_args.kwargs == {"stuck": 1}

    def test_the_drain_bound_is_the_graceful_stop_timeout(self, stopped, monkeypatch):
        monkeypatch.setenv("ODOO_GRACEFUL_STOP_TIMEOUT", "7")
        server, _, _, _ = stopped()
        assert server.httpd.drain.call_args.args == (7.0,)

    def test_a_listener_thread_mid_job_gets_the_graceful_bound_then_is_left(
        self, stopped, monkeypatch
    ):
        monkeypatch.setenv("ODOO_GRACEFUL_STOP_TIMEOUT", "1")
        busy = threading.Event()
        released = threading.Event()
        thread = threading.Thread(
            target=lambda: (busy.set(), released.wait(10)), daemon=True
        )
        thread.start()
        busy.wait(1)
        t0 = time.monotonic()
        server, _, _, _ = stopped(_listener_threads=[thread])
        elapsed = time.monotonic() - t0
        released.set()
        assert server._listener_stop.is_set()
        assert _threaded.LISTENER_JOIN_TIMEOUT_S <= elapsed < 3
        said = " ".join(str(c) for c in server.logger.warning.call_args_list)
        assert "still mid-job at shutdown" in said
        assert "ODOO_GRACEFUL_STOP_TIMEOUT" in said

    def test_a_listener_thread_over_its_limit_gets_the_floor_not_the_bound(
        self, stopped, monkeypatch
    ):
        monkeypatch.setenv("ODOO_GRACEFUL_STOP_TIMEOUT", "5")
        released = threading.Event()
        thread = threading.Thread(target=lambda: released.wait(10), daemon=True)
        thread.start()
        t0 = time.monotonic()
        server, _, _, _ = stopped(
            _listener_threads=[thread], limits_reached_threads={thread}
        )
        elapsed = time.monotonic() - t0
        released.set()
        assert _threaded.LISTENER_JOIN_TIMEOUT_S <= elapsed < 3
        server.logger.info.assert_any_call(
            "Initiating shutdown"
        )  # no "Waiting up to" line for a thread the reload is leaving behind
        assert not any(
            "Waiting up to" in str(c) for c in server.logger.info.call_args_list
        )

    def test_a_listener_thread_that_finishes_its_job_in_time_is_joined(
        self, stopped, monkeypatch
    ):
        monkeypatch.setenv("ODOO_GRACEFUL_STOP_TIMEOUT", "5")
        released = threading.Event()
        thread = threading.Thread(target=lambda: released.wait(10), daemon=True)
        thread.start()
        threading.Timer(0.3, released.set).start()
        t0 = time.monotonic()
        server, _, _, _ = stopped(_listener_threads=[thread])
        elapsed = time.monotonic() - t0
        assert 0.2 < elapsed < 3
        assert not thread.is_alive()
        server.logger.warning.assert_not_called()

    def test_the_listener_wakeup_pipe_is_written_and_closed(self, stopped):
        pipe = os.pipe2(os.O_NONBLOCK | os.O_CLOEXEC)
        with patch.object(_threaded.os, "close") as close:
            server, _, _, _ = stopped(_listener_stop_pipe=pipe)
        assert os.read(pipe[0], 8) == b"."
        assert sorted(c.args[0] for c in close.call_args_list) == sorted(pipe)
        assert server._listener_stop_pipe is None
        for fd in pipe:
            os.close(fd)


class TestAReloadKeepsTheListeningSocket:
    @pytest.fixture
    def stopped(self, server):
        def _run(*, phoenix):
            server.httpd = MagicMock(busy_workers=0)
            with (
                patch.object(_threaded.db, "close_all"),
                patch.object(_threaded, "logging"),
                patch.object(_threaded.psutil, "Process") as proc,
                patch.object(_threaded.CommonServer, "stop"),
                patch.object(_process_state, "server_phoenix", phoenix),
            ):
                proc.return_value.children.return_value = []
                server.stop()
            return server.httpd

        return _run

    def test_a_reload_bequeaths_the_listener_after_the_drain_and_before_the_close(
        self, stopped
    ):
        httpd = stopped(phoenix=True)
        names = [name for name, _, _ in httpd.mock_calls]
        assert (
            names.index("drain")
            < names.index("bequeath_listener")
            < names.index("server_close")
        )

    def test_a_shutdown_closes_the_listener_outright(self, stopped):
        httpd = stopped(phoenix=False)
        httpd.bequeath_listener.assert_not_called()
        httpd.server_close.assert_called_once_with()
