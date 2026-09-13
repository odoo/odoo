import os
import signal
import threading
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from odoo.service import _process_state, _threaded
from odoo.service import settings as server_settings


@pytest.fixture
def server():
    s = object.__new__(_threaded.ThreadedServer)
    s.pid = os.getpid()
    s.main_thread_id = threading.current_thread().ident
    s.quit_signals_received = 0
    s.httpd = None
    s.limits_reached_threads = set()
    s._overrun_start_times = {}
    s.limit_reached_time = None
    s._stop_after_init = False
    s._process_handle = MagicMock()
    s.logger = MagicMock()
    s.interface, s.port = "127.0.0.1", 8069
    s.app = MagicMock()
    return s


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
            patch.object(_threaded, "_SIGHUP_AVAILABLE", False),
        ):
            server.signal_handler(signal.SIGUSR1, None)

    def test_quit_signals_still_work_without_sighup(self, server, windows_signal):
        with (
            patch.object(_threaded, "signal", windows_signal),
            patch.object(_threaded, "_SIGHUP_AVAILABLE", False),
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
            patch.object(_threaded, "_IS_POSIX", True),
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
            server.httpd = MagicMock()
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

    def test_a_hung_non_daemon_thread_cannot_stall_the_stop_forever(self, stopped):
        hung = MagicMock()
        hung.daemon = False
        hung.ident = -1
        hung.is_alive.return_value = True
        with patch.object(_threaded.threading, "enumerate", return_value=[hung]):
            t0 = time.monotonic()
            stopped()
        assert time.monotonic() - t0 < 5, "stop() did not bound its join loop"


class TestTheFixtureMatchesTheConstructor:
    def test_the_field_sets_agree(self, server):
        with server_settings.override(
            http_interface="", http_port=8069, limit_time_real=120
        ):
            real = _threaded.ThreadedServer(MagicMock())

        missing = sorted(set(vars(real)) - set(vars(server)))
        extra = sorted(set(vars(server)) - set(vars(real)))
        assert not missing and not extra, (
            "the `server` fixture has drifted from the constructor it stands in "
            f"for.\n  set by __init__ but absent from the fixture: {missing}\n"
            f"  in the fixture but never set by __init__:    {extra}\n"
            "Either restate the field, or drop the parity claim from the "
            "fixture's docstring and let it be a minimal stand-in like "
            "test_server.py's prefork_server."
        )
