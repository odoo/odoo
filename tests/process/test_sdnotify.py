"""The service manager protocol, against real servers.

A unit whose Type=notify waits for READY=1 before it considers the service
started, restarts it when WATCHDOG=1 stops coming, and reads STOPPING=1 as
the beginning of an orderly stop.  This drives both flavours through a
datagram socket standing in for systemd's.
"""

import os
import signal
import socket
import time

import pytest

from .conftest import requires_pg, requires_posix


@pytest.fixture
def notify_socket(tmp_path):
    path = str(tmp_path / "notify.sock")
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    sock.bind(path)
    sock.settimeout(30)
    try:
        yield path, sock
    finally:
        sock.close()


def _drain(sock, until, timeout=30):
    seen = []
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            sock.settimeout(max(0.1, deadline - time.monotonic()))
            seen.append(sock.recv(256).decode())
        except TimeoutError:
            break
        if until(seen):
            break
    return seen


@requires_pg
@requires_posix
@pytest.mark.parametrize("workers", ["0", "1"], ids=["threaded", "prefork"])
def test_ready_watchdog_and_stopping_reach_the_manager(server, notify_socket, workers):
    path, sock = notify_socket
    srv = server(
        "--workers",
        workers,
        env={
            "NOTIFY_SOCKET": path,
            "WATCHDOG_USEC": "2000000",  # a beat every second
        },
    )
    seen = _drain(sock, lambda s: "READY=1" in s)
    assert "READY=1" in seen, seen
    seen = _drain(sock, lambda s: s.count("WATCHDOG=1") >= 2, timeout=10)
    assert seen.count("WATCHDOG=1") >= 2, seen
    os.kill(srv.proc.pid, signal.SIGTERM)
    seen = _drain(sock, lambda s: "STOPPING=1" in s)
    assert "STOPPING=1" in seen, seen
    assert srv.wait_until(lambda: srv.proc.poll() is not None, timeout=30)


@requires_pg
@requires_posix
def test_a_reload_announces_reloading_then_ready_again(server, notify_socket):
    path, sock = notify_socket
    srv = server("--workers", "1", env={"NOTIFY_SOCKET": path})
    assert "READY=1" in _drain(sock, lambda s: "READY=1" in s)
    os.kill(srv.proc.pid, signal.SIGHUP)
    seen = _drain(sock, lambda s: any(m.startswith("RELOADING=1") for m in s))
    reloading = next(m for m in seen if m.startswith("RELOADING=1"))
    assert "MONOTONIC_USEC=" in reloading
    seen += _drain(sock, lambda s: "READY=1" in s, timeout=90)
    assert "READY=1" in seen, seen
    assert srv.wait_until(lambda: "New server has started" in srv.log_text(), 90)
    assert srv.is_serving()
