"""Every worker limit and every signal, driven against real servers.

The unit suites pin the decisions; this pins what a deployment sees: which
request comes back, which worker survives, what the log says, and that no
policy verdict is ever counted as a crash.  The routes come from a
server-wide probe module that answers before dispatch, so no database is
loaded: `/probe/slow/N` sleeps N seconds in Python, `/probe/burn/N` burns N
seconds of CPU, `/probe/query/N` runs `pg_sleep(N)` on a checked-out
connection -- the one shape the budget monitor can cancel -- and
`/probe/hold/N` keeps N MiB allocated so the soft memory limit trips.
"""

import http.client
import os
import signal
import socket
import threading
import time

import pytest

from .conftest import REPO_ROOT, requires_pg, requires_posix

PROBE = """
import time

import odoo.db
from odoo.http import Application

_original = Application.__call__
_held = []


def _burn(seconds):
    deadline = time.process_time() + seconds
    while time.process_time() < deadline:
        sum(range(10000))


def _probe(self, environ, start_response):
    path = environ.get("PATH_INFO", "")
    if not path.startswith("/probe/"):
        return _original(self, environ, start_response)
    kind, _, arg = path[len("/probe/"):].partition("/")
    seconds = float(arg or 1)
    if kind == "slow":
        time.sleep(seconds)
    elif kind == "burn":
        _burn(seconds)
    elif kind == "query":
        with odoo.db.db_connect("postgres").cursor() as cr:
            cr.execute("select pg_sleep(%s)", (seconds,))
    elif kind == "hold":
        _held.append(bytearray(int(seconds) * 1024 * 1024))
    body = f"{kind} {seconds}\\n".encode()
    start_response("200 OK", [("Content-Type", "text/plain"), ("Content-Length", str(len(body)))])
    return [body]


Application.__call__ = _probe
"""


@pytest.fixture
def probe(server, tmp_path):
    addon = tmp_path / "addons" / "service_limit_probe"
    addon.mkdir(parents=True)
    (addon / "__manifest__.py").write_text(
        "{'name': 'Limit probe', 'license': 'LGPL-3', 'depends': ['base']}\n"
    )
    (addon / "__init__.py").write_text(PROBE)
    paths = f"{REPO_ROOT / 'odoo/addons'},{REPO_ROOT / 'addons'},{addon.parent}"

    def _start(*args, **kwargs):
        return server(
            "--load", "web,service_limit_probe", "--addons-path", paths, *args, **kwargs
        )

    return _start


def _get(port, path, timeout=60):
    """(status, seconds) or (None, seconds) when the reply never came."""
    t0 = time.monotonic()
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    try:
        conn.request("GET", path)
        return conn.getresponse().status, time.monotonic() - t0
    except http.client.HTTPException, OSError:
        return None, time.monotonic() - t0
    finally:
        conn.close()


def _in_background(port, path):
    out = {}

    def run():
        out["status"], out["seconds"] = _get(port, path)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t, out


@requires_pg
@requires_posix
class TestPreforkLimits:
    def test_limit_request_recycles_cleanly(self, probe):
        srv = probe("--workers", "1", "--limit-request", "2")
        assert srv.wait_until(lambda: len(srv.http_workers()) == 1, timeout=60)
        first = srv.http_workers()[0].pid
        assert [_get(srv.port, "/probe/slow/0")[0] for _ in range(3)] == [200, 200, 200]
        assert srv.wait_until(
            lambda: srv.http_workers() and srv.http_workers()[0].pid != first, 30
        )
        assert "Max request (2) reached" in srv.log_text()
        assert "holding respawn" not in srv.log_text()

    def test_cpu_limit_recycles_without_a_back_off(self, probe):
        srv = probe("--workers", "1", "--limit-time-cpu", "2")
        assert srv.wait_until(lambda: len(srv.http_workers()) == 1, timeout=60)
        status, seconds = _get(srv.port, "/probe/burn/6")
        assert status is None and seconds < 6
        assert srv.wait_until(lambda: "CPU time limit (2s) exceeded" in srv.log_text())
        assert srv.wait_until(lambda: len(srv.http_workers()) == 1, timeout=30)
        assert _get(srv.port, "/probe/slow/0")[0] == 200
        text = srv.log_text()
        assert "uncaught error" not in text
        assert "holding respawn" not in text

    def test_a_query_over_the_wall_clock_budget_is_cancelled_not_killed(self, probe):
        srv = probe("--workers", "1", "--limit-time-real", "5")
        assert srv.wait_until(lambda: len(srv.http_workers()) == 1, timeout=60)
        pid = srv.http_workers()[0].pid
        status, seconds = _get(srv.port, "/probe/query/30")
        assert status == 500 and seconds < 10, (status, seconds)
        assert srv.wait_until(lambda: "cancelled 1 running query" in srv.log_text())
        assert srv.http_workers()[0].pid == pid, "the worker itself survived"
        assert "timeout after" not in srv.log_text()

    def test_a_python_stall_recycles_the_worker_after_the_grace(self, probe):
        srv = probe("--workers", "1", "--limit-time-real", "5")
        assert srv.wait_until(lambda: len(srv.http_workers()) == 1, timeout=60)
        pid = srv.http_workers()[0].pid
        status, seconds = _get(srv.port, "/probe/slow/30")
        assert status is None and seconds < 20, (status, seconds)
        assert srv.wait_until(lambda: "did not return" in srv.log_text())
        assert srv.wait_until(
            lambda: srv.http_workers() and srv.http_workers()[0].pid != pid, 30
        )
        assert _get(srv.port, "/probe/slow/0")[0] == 200
        assert "holding respawn" not in srv.log_text()

    def test_memory_soft_limit_recycles_cleanly(self, probe):
        srv = probe("--workers", "1", "--limit-memory-soft", str(256 * 1024 * 1024))
        assert srv.wait_until(lambda: len(srv.http_workers()) == 1, timeout=60)
        assert "memory soft-limit" not in srv.log_text(), (
            "the limit sits above boot RSS"
        )
        assert _get(srv.port, "/probe/hold/200")[0] == 200
        assert srv.wait_until(lambda: "memory soft-limit reached" in srv.log_text(), 30)
        assert srv.wait_until(lambda: "Exiting cleanly" in srv.log_text(), 30)
        assert "holding respawn" not in srv.log_text()

    def test_ttin_and_ttou_move_the_population(self, probe):
        srv = probe("--workers", "1")
        assert srv.wait_until(lambda: len(srv.http_workers()) == 1, timeout=60)
        os.kill(srv.proc.pid, signal.SIGTTIN)
        assert srv.wait_until(lambda: len(srv.http_workers()) == 2, timeout=30)
        os.kill(srv.proc.pid, signal.SIGTTOU)
        assert srv.wait_until(lambda: len(srv.http_workers()) == 1, timeout=30)
        assert _get(srv.port, "/probe/slow/0")[0] == 200

    def test_a_request_in_flight_survives_a_reload(self, probe):
        srv = probe("--workers", "1")
        assert srv.wait_until(lambda: len(srv.http_workers()) == 1, timeout=60)
        thread, out = _in_background(srv.port, "/probe/slow/4")
        time.sleep(1)
        os.kill(srv.proc.pid, signal.SIGHUP)
        thread.join(60)
        assert out["status"] == 200 and out["seconds"] >= 4
        assert srv.wait_until(lambda: "New server has started" in srv.log_text(), 90)


@requires_pg
@requires_posix
class TestThreadedLimits:
    def test_a_query_over_budget_is_cancelled_and_the_process_kept(self, probe):
        srv = probe("--workers", "0", "--limit-time-real", "3")
        status, seconds = _get(srv.port, "/probe/query/30")
        assert status == 500 and seconds < 12, (status, seconds)
        assert srv.wait_until(lambda: "cancelled 1 running query" in srv.log_text())
        assert _get(srv.port, "/probe/slow/0")[0] == 200
        assert srv.log_text().count("Odoo version") == 1, "no reload"

    def test_a_python_stall_reloads_the_process(self, probe):
        srv = probe("--workers", "0", "--limit-time-real", "3")
        status, seconds = _get(srv.port, "/probe/slow/30")
        assert status is None and seconds < 20, (status, seconds)
        assert srv.wait_until(lambda: srv.log_text().count("Odoo version") == 2, 60)
        assert "Initiating server reload" in srv.log_text()

    def test_stop_drains_an_in_flight_request(self, probe):
        srv = probe("--workers", "0")
        thread, out = _in_background(srv.port, "/probe/slow/4")
        time.sleep(1)
        os.kill(srv.proc.pid, signal.SIGTERM)
        thread.join(60)
        assert out["status"] == 200 and out["seconds"] >= 4
        assert srv.wait_until(lambda: srv.proc.poll() is not None, 30)
        assert "Waiting up to" in srv.log_text()

    def test_a_second_signal_forces_the_stop(self, probe):
        srv = probe("--workers", "0")
        thread, out = _in_background(srv.port, "/probe/slow/30")
        time.sleep(1)
        os.kill(srv.proc.pid, signal.SIGTERM)
        time.sleep(1)
        os.kill(srv.proc.pid, signal.SIGTERM)
        assert srv.wait_until(lambda: srv.proc.poll() is not None, 10)
        thread.join(10)
        assert out["status"] is None


def _port_is_open(port):
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) == 0
