import os
import socket
from unittest.mock import patch

import pytest

from odoo.service import _sdnotify


@pytest.fixture
def listener(tmp_path, monkeypatch):
    path = str(tmp_path / "notify.sock")
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    sock.bind(path)
    sock.settimeout(2)
    monkeypatch.setenv("NOTIFY_SOCKET", path)
    try:
        yield sock
    finally:
        sock.close()


class TestNotify:
    def test_the_state_reaches_the_socket(self, listener):
        assert _sdnotify.notify("READY=1") is True
        assert listener.recv(64) == b"READY=1"

    def test_ready_and_reloading_are_the_documented_lines(self, listener):
        assert _sdnotify.notify_ready()
        assert listener.recv(64) == b"READY=1"
        assert _sdnotify.notify_reloading()
        lines = listener.recv(128).decode().split("\n")
        assert lines[0] == "RELOADING=1"
        assert lines[1].startswith("MONOTONIC_USEC=") and lines[1][15:].isdigit()

    def test_no_socket_means_no_send_and_no_error(self, monkeypatch):
        monkeypatch.delenv("NOTIFY_SOCKET", raising=False)
        assert _sdnotify.notify("READY=1") is False

    def test_an_unreachable_socket_is_reported_not_raised(self, tmp_path, monkeypatch):
        monkeypatch.setenv("NOTIFY_SOCKET", str(tmp_path / "gone.sock"))
        assert _sdnotify.notify("READY=1") is False

    def test_an_abstract_socket_name_is_translated(self, monkeypatch):
        seen = []

        class _Sock:
            def __init__(self, *a, **k):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def connect(self, path):
                seen.append(path)

            def sendall(self, data):
                seen.append(data)

        monkeypatch.setenv("NOTIFY_SOCKET", "@systemd-notify")
        with patch.object(_sdnotify.socket, "socket", _Sock):
            assert _sdnotify.notify("STOPPING=1")
        assert seen == ["\0systemd-notify", b"STOPPING=1"]


class TestWatchdog:
    def test_unset_means_disabled(self, monkeypatch):
        monkeypatch.delenv("WATCHDOG_USEC", raising=False)
        assert _sdnotify.get_watchdog_interval() is None
        assert _sdnotify.Watchdog().enabled is False
        assert _sdnotify.Watchdog().bound(5.0) == 5.0

    def test_half_the_unit_interval_for_this_pid(self, monkeypatch):
        monkeypatch.setenv("WATCHDOG_USEC", "10000000")
        monkeypatch.setenv("WATCHDOG_PID", str(os.getpid()))
        assert _sdnotify.get_watchdog_interval() == 5.0

    def test_another_pids_watchdog_is_not_ours(self, monkeypatch):
        monkeypatch.setenv("WATCHDOG_USEC", "10000000")
        monkeypatch.setenv("WATCHDOG_PID", str(os.getpid() + 1))
        assert _sdnotify.get_watchdog_interval() is None

    def test_beats_are_spaced_and_bound_the_sleep(self, monkeypatch, listener):
        monkeypatch.setenv("WATCHDOG_USEC", "4000000")
        monkeypatch.delenv("WATCHDOG_PID", raising=False)
        clock = iter([100.0, 100.0, 101.0, 101.0, 102.5, 102.5])
        with patch.object(_sdnotify.time, "monotonic", lambda: next(clock)):
            watchdog = _sdnotify.Watchdog()
            assert watchdog.beat() is True
            assert listener.recv(64) == b"WATCHDOG=1"
            assert watchdog.bound(5.0) == 2.0
            assert watchdog.beat() is False
            assert watchdog.bound(5.0) == 1.0
            assert watchdog.beat() is True
