from __future__ import annotations

import base64
import hashlib
import os
import socket
import subprocess
import sys
import threading
import time

import psutil
import pytest

from .conftest import REPO_ROOT, free_port, requires_pg, requires_posix

STREAM_CHANNEL = "stream_reconcile"

STREAM_HEARTBEAT_S = 15

OPEN_TIMEOUT_S = 45.0

REOPEN_TIMEOUT_S = 2 * STREAM_HEARTBEAT_S + 15.0

_WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


def test_the_channel_and_heartbeat_literals_match_the_source():
    constants = (REPO_ROOT / "odoo" / "tools" / "constants.py").read_text()
    assert f'STREAM_CHANNEL = "{STREAM_CHANNEL}"' in constants
    cron = (REPO_ROOT / "odoo" / "service" / "_cron.py").read_text()
    assert f"STREAM_HEARTBEAT_S = {STREAM_HEARTBEAT_S}\n" in cron


def _connect(dbname="postgres"):
    import psycopg

    return psycopg.connect(dbname=dbname, autocommit=True)


@pytest.fixture(scope="module")
def stream_db():
    name = f"procstream_{os.getpid()}"
    with _connect() as conn:
        conn.execute(f'DROP DATABASE IF EXISTS "{name}"')
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "odoo-bin"),
            "--addons-path",
            f"{REPO_ROOT / 'odoo' / 'addons'},{REPO_ROOT / 'addons'}",
            "-d",
            name,
            "-i",
            "integration_websocket",
            "--stop-after-init",
            "--stream-workers",
            "0",
            "--log-level",
            "warn",
        ],
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
    assert proc.returncode == 0, (
        f"install failed:\n{proc.stdout[-3000:]}{proc.stderr[-3000:]}"
    )
    yield name
    with _connect() as conn:
        conn.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = %s AND pid != pg_backend_pid()",
            (name,),
        )
        conn.execute(f'DROP DATABASE IF EXISTS "{name}"')


class HandshakeServer(threading.Thread):
    """Answers the websocket upgrade and then holds the socket open; every
    accepted connection is recorded, and a closed one is noticed."""

    def __init__(self):
        super().__init__(daemon=True)
        self.port = free_port()
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", self.port))
        self.sock.listen(8)
        self.sock.settimeout(0.5)
        self.connections: list[socket.socket] = []
        self.closed: list[socket.socket] = []
        self.stop_flag = threading.Event()
        self.lock = threading.Lock()

    def run(self):
        while not self.stop_flag.is_set():
            try:
                client, _addr = self.sock.accept()
            except TimeoutError:
                self._notice_closed()
                continue
            threading.Thread(target=self._serve, args=(client,), daemon=True).start()

    def _serve(self, client):
        client.settimeout(10)
        request = b""
        try:
            while b"\r\n\r\n" not in request:
                chunk = client.recv(4096)
                if not chunk:
                    client.close()
                    return
                request += chunk
        except OSError:
            client.close()
            return
        key = ""
        for line in request.decode("latin-1").split("\r\n"):
            if line.lower().startswith("sec-websocket-key:"):
                key = line.split(":", 1)[1].strip()
        accept = base64.b64encode(
            hashlib.sha1((key + _WS_GUID).encode()).digest()
        ).decode()
        client.sendall(
            (
                "HTTP/1.1 101 Switching Protocols\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Accept: {accept}\r\n\r\n"
            ).encode()
        )
        client.settimeout(0.2)
        with self.lock:
            self.connections.append(client)

    def _notice_closed(self):
        with self.lock:
            live = [c for c in self.connections if c not in self.closed]
        for client in live:
            try:
                data = client.recv(1, socket.MSG_PEEK)
            except TimeoutError:
                continue
            except OSError:
                data = b""
            if not data:
                with self.lock:
                    self.closed.append(client)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        self.stop_flag.set()
        self.join(timeout=5)
        for client in self.connections:
            client.close()
        self.sock.close()


def _row(dbname, stream_id):
    with _connect(dbname) as conn:
        return conn.execute(
            "SELECT state, owner, attempts, state_message FROM integration_stream "
            "WHERE id = %s",
            (stream_id,),
        ).fetchone()


def _create_stream(dbname, url):
    with _connect(dbname) as conn:
        (stream_id,) = conn.execute(
            "INSERT INTO integration_stream "
            "(name, active, protocol, url, heartbeat_seconds, backoff_seconds, "
            "backoff_max_seconds, state, attempts, frames_in, frames_out, "
            "create_date, write_date) "
            "VALUES ('SIGKILL probe', true, 'websocket', %s, 600, 1, 5, "
            "'stopped', 0, 0, 0, now(), now()) RETURNING id",
            (url,),
        ).fetchone()
        conn.execute("SELECT pg_notify(%s, %s)", (STREAM_CHANNEL, dbname))
    return stream_id


def _owner_pid(owner):
    return int(owner.rsplit(":", 1)[1]) if owner else None


def _wait_for(predicate, timeout, interval=0.25):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(interval)
    return predicate()


@requires_pg
@requires_posix
def test_a_stream_survives_its_worker_s_sigkill_and_reopens_on_the_next_leader(
    server, stream_db
):
    with HandshakeServer() as wire:
        srv = server(
            "--workers",
            "1",
            "--stream-workers",
            "1",
            "--db-filter",
            f"^{stream_db}$",
        )
        stream_id = _create_stream(stream_db, f"ws://127.0.0.1:{wire.port}/probe")

        opened = _wait_for(lambda: len(wire.connections) >= 1, OPEN_TIMEOUT_S)
        assert opened, (
            f"no stream worker dialled the wire within {OPEN_TIMEOUT_S:.0f}s; "
            f"row={_row(stream_db, stream_id)}; log tail:\n"
            + "\n".join(srv.log_text().splitlines()[-15:])
        )
        row = _wait_for(
            lambda: (r := _row(stream_db, stream_id)) and r[0] == "open" and r,
            10,
        )
        assert row and row[0] == "open", (
            f"the wire was dialled but the row reads {_row(stream_db, stream_id)}; "
            "log tail:\n" + "\n".join(srv.log_text().splitlines()[-15:])
        )
        first_pid = _owner_pid(row[1])
        assert first_pid in {child.pid for child in srv.children()}, (
            f"the row's owner {row[1]} is not a child of the server"
        )
        first_connection = wire.connections[0]

        os.kill(first_pid, 9)
        killed_at = time.monotonic()

        reopened = _wait_for(
            lambda: (
                len(wire.connections) >= 2
                and first_connection in wire.closed
                and (r := _row(stream_db, stream_id))
                and r[0] == "open"
                and _owner_pid(r[1]) not in (None, first_pid)
                and r
            ),
            REOPEN_TIMEOUT_S,
        )
        elapsed = time.monotonic() - killed_at
        print(f"reopened {elapsed:.1f}s after SIGKILL")
        assert reopened, (
            f"the stream did not reopen on a new leader within "
            f"{REOPEN_TIMEOUT_S:.0f}s of SIGKILL (connections="
            f"{len(wire.connections)}, first closed="
            f"{first_connection in wire.closed}, row={_row(stream_db, stream_id)}); "
            "log tail:\n" + "\n".join(srv.log_text().splitlines()[-20:])
        )
        second_pid = _owner_pid(reopened[1])
        assert (
            not psutil.pid_exists(first_pid)
            or psutil.Process(first_pid).status() == psutil.STATUS_ZOMBIE
        )
        assert second_pid in {child.pid for child in srv.children()}
        assert elapsed <= STREAM_HEARTBEAT_S + 15.0, (
            f"reopened after {elapsed:.1f}s, more than one heartbeat plus the respawn"
        )
        assert srv.log_text().count("leads the streams of") >= 2
