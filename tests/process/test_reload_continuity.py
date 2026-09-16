import os
import re
import signal
import socket
import time

import pytest

from .conftest import REPO_ROOT, Poller, is_evented, requires_pg, requires_posix

WORKERS = 2
RELOAD_TIMEOUT_S = 60.0


def _child_pids(srv):
    return {worker.pid for worker in srv.http_workers()}


def _websocket_port(srv):
    found = re.search(
        r"Evented/WebSocket service running on [^:]+:(\d+)", srv.log_text()
    )
    return int(found.group(1)) if found else None


def _evented_child(srv):
    for child in srv.children():
        if is_evented(child):
            return child
    return None


@requires_pg
@requires_posix
def test_source_watcher_survives_successful_and_rejected_reloads(server, tmp_path):
    addon = tmp_path / "addons" / "service_watcher_probe"
    addon.mkdir(parents=True)
    watched = tmp_path / "watched"
    watched.mkdir()
    source = watched / "change.py"
    source.write_text("value = 0\n")
    reject = tmp_path / "reject"
    (addon / "__manifest__.py").write_text(
        "{'name': 'Persistent watcher probe', 'license': 'LGPL-3', 'depends': ['base']}\n"
    )
    (addon / "__init__.py").write_text(
        "import os\nfrom pathlib import Path\n"
        "from odoo.service import _prefork, _watcher\n"
        "_watcher.FSWatcherBase.get_watch_paths = staticmethod(\n"
        "    lambda: [os.environ['SERVICE_WATCH_ROOT']])\n"
        "if Path(os.environ['SERVICE_REJECT_RELOAD']).exists():\n"
        "    _prefork.preload_registries = lambda preload: 3\n"
    )
    paths = f"{REPO_ROOT / 'odoo/addons'},{REPO_ROOT / 'addons'},{addon.parent}"
    srv = server(
        "--workers",
        "2",
        "--dev",
        "reload",
        "--load",
        "web,service_watcher_probe",
        "--addons-path",
        paths,
        env={"SERVICE_WATCH_ROOT": str(watched), "SERVICE_REJECT_RELOAD": str(reject)},
    )
    assert srv.wait_until(lambda: "AutoReload watcher running" in srv.log_text())
    source.write_text("value = 1\n")
    assert srv.wait_until(lambda: "New server has started" in srv.log_text())
    reject.touch()
    source.write_text("value = 2\n")
    assert srv.wait_until(lambda: "Reload aborted" in srv.log_text(), timeout=15), (
        "the source watcher stopped after the first reload"
    )
    reject.unlink()
    source.write_text("value = 3\n")
    assert srv.wait_until(lambda: srv.log_text().count("New server has started") >= 2)
    assert srv.is_serving()
    assert srv.log_text().count("AutoReload watcher running") == 1


@requires_pg
@requires_posix
def test_a_threaded_dev_reload_reexecs_on_a_python_edit_and_refuses_nothing(
    server, tmp_path
):
    addon = tmp_path / "addons" / "service_threaded_watcher_probe"
    addon.mkdir(parents=True)
    watched = tmp_path / "watched"
    watched.mkdir()
    source = watched / "change.py"
    source.write_text("value = 0\n")
    (addon / "__manifest__.py").write_text(
        "{'name': 'Threaded watcher probe', 'license': 'LGPL-3', 'depends': ['base']}\n"
    )
    (addon / "__init__.py").write_text(
        "import os\nfrom odoo.service import _watcher\n"
        "_watcher.FSWatcherBase.get_watch_paths = staticmethod(\n"
        "    lambda: [os.environ['SERVICE_WATCH_ROOT']])\n"
    )
    paths = f"{REPO_ROOT / 'odoo/addons'},{REPO_ROOT / 'addons'},{addon.parent}"
    srv = server(
        "--workers",
        "0",
        "--dev",
        "reload",
        "--load",
        "web,service_threaded_watcher_probe",
        "--addons-path",
        paths,
        env={"SERVICE_WATCH_ROOT": str(watched)},
    )
    assert srv.wait_until(lambda: "AutoReload watcher running" in srv.log_text())
    with Poller(srv.port) as poller:
        time.sleep(0.5)
        source.write_text("value = 1\n")
        assert srv.wait_until(
            lambda: (
                "inherited from the server this one replaced" in srv.log_text()
                and srv.log_text().count("AutoReload watcher running") == 2
                and srv.is_serving(3)
            ),
            timeout=RELOAD_TIMEOUT_S,
        ), srv.log_text()[-2000:]
    assert poller.refused == 0 and not poller.other, (poller.refused, poller.other)
    assert poller.served > 0
    assert srv.proc.poll() is None, "the re-exec keeps the pid the fixture holds"
    assert "Initiating server reload" in srv.log_text()


@requires_pg
@requires_posix
def test_worker_respawn_continues_while_replacement_preload_waits(server, tmp_path):
    addon = tmp_path / "addons" / "service_waiting_preload_probe"
    addon.mkdir(parents=True)
    hold = tmp_path / "hold-preload"
    waiting = tmp_path / "waiting"
    (addon / "__manifest__.py").write_text(
        "{'name': 'Waiting preload probe', 'license': 'LGPL-3', 'depends': ['base']}\n"
    )
    (addon / "__init__.py").write_text(
        "import os, time\nfrom pathlib import Path\nfrom odoo.service import _prefork\n"
        "original = _prefork.preload_registries\n"
        "def preload(preload):\n"
        "    hold = Path(os.environ['SERVICE_HOLD_PRELOAD'])\n"
        "    if hold.exists():\n"
        "        Path(os.environ['SERVICE_WAITING']).write_text(str(os.getpid()))\n"
        "        while hold.exists():\n"
        "            time.sleep(0.05)\n"
        "    return original(preload)\n"
        "_prefork.preload_registries = preload\n"
    )
    paths = f"{REPO_ROOT / 'odoo/addons'},{REPO_ROOT / 'addons'},{addon.parent}"
    srv = server(
        "--workers",
        "2",
        "--load",
        "web,service_waiting_preload_probe",
        "--addons-path",
        paths,
        env={"SERVICE_HOLD_PRELOAD": str(hold), "SERVICE_WAITING": str(waiting)},
    )
    assert srv.wait_until(lambda: len(_child_pids(srv)) == 2)
    original = _child_pids(srv)
    hold.touch()
    try:
        os.kill(srv.proc.pid, signal.SIGHUP)
        assert srv.wait_until(waiting.exists)
        candidate = int(waiting.read_text())
        for pid in original:
            os.kill(pid, signal.SIGKILL)

        def recovered():
            workers = _child_pids(srv) - {candidate}
            return len(workers) == 2 and not original.intersection(workers)

        assert srv.wait_until(recovered, timeout=10), (
            "old generation stopped respawning workers during replacement preload"
        )
        assert hold.exists() and "New server has started" not in srv.log_text()
        assert srv.is_serving(), "service did not recover while preload was held"
    finally:
        hold.unlink(missing_ok=True)
    assert srv.wait_until(lambda: "New server has started" in srv.log_text())


@requires_pg
@requires_posix
@pytest.mark.parametrize(("sig", "population"), [("SIGTTIN", 3), ("SIGTTOU", 1)])
def test_scaling_during_first_reload_reaches_the_replacement(
    server, tmp_path, sig, population
):
    addon = tmp_path / "addons" / "service_scale_probe"
    addon.mkdir(parents=True)
    injected = tmp_path / "injected"
    (addon / "__manifest__.py").write_text(
        "{'name': 'Service scaling probe', 'license': 'LGPL-3', 'depends': ['base']}\n"
    )
    (addon / "__init__.py").write_text(
        "import os, signal\nfrom pathlib import Path\n"
        "from odoo.service._prefork import PreforkServer\n"
        "original = PreforkServer.stop_workers_gracefully\n"
        "def stop_workers_gracefully(self):\n"
        "    if not self.handoff.is_supervised and self.workers:\n"
        "        os.kill(os.getpid(), getattr(signal, os.environ['SERVICE_SCALE_SIGNAL']))\n"
        "        Path(os.environ['SERVICE_SCALE_INJECTED']).touch()\n"
        "    return original(self)\n"
        "PreforkServer.stop_workers_gracefully = stop_workers_gracefully\n"
    )
    paths = f"{REPO_ROOT / 'odoo/addons'},{REPO_ROOT / 'addons'},{addon.parent}"
    srv = server(
        "--workers",
        "2",
        "--load",
        "web,service_scale_probe",
        "--addons-path",
        paths,
        env={"SERVICE_SCALE_SIGNAL": sig, "SERVICE_SCALE_INJECTED": str(injected)},
    )
    assert srv.wait_until(lambda: len(_child_pids(srv)) == 2)
    original = _child_pids(srv)
    os.kill(srv.proc.pid, signal.SIGHUP)
    assert srv.wait_until(injected.exists)
    assert srv.wait_until(
        lambda: (
            len(_child_pids(srv)) == population
            and not original.intersection(_child_pids(srv))
        ),
        timeout=15,
    ), srv.log_text()
    assert srv.is_serving()
    reverse = signal.SIGTTOU if sig == "SIGTTIN" else signal.SIGTTIN
    os.kill(srv.proc.pid, reverse)
    assert srv.wait_until(lambda: len(_child_pids(srv)) == 2)
    assert srv.is_serving()


@requires_pg
@requires_posix
def test_shutdown_during_reload_drain_reaches_the_supervisor(server, tmp_path):
    addon = tmp_path / "addons" / "service_shutdown_probe"
    addon.mkdir(parents=True)
    (addon / "__manifest__.py").write_text(
        "{'name': 'Service shutdown probe', 'license': 'LGPL-3', 'depends': ['base']}\n"
    )
    (addon / "__init__.py").write_text(
        "import os, signal\nfrom odoo.service._prefork import PreforkServer\n"
        "original = PreforkServer.stop_workers_gracefully\n"
        "def stop_workers_gracefully(self):\n"
        "    if not self.handoff.is_supervised and self.workers:\n"
        "        os.kill(os.getpid(), signal.SIGTERM)\n"
        "    return original(self)\n"
        "PreforkServer.stop_workers_gracefully = stop_workers_gracefully\n"
    )
    paths = f"{REPO_ROOT / 'odoo/addons'},{REPO_ROOT / 'addons'},{addon.parent}"
    srv = server(
        "--workers",
        "2",
        "--load",
        "web,service_shutdown_probe",
        "--addons-path",
        paths,
    )
    assert srv.wait_until(lambda: len(_child_pids(srv)) == 2)
    os.kill(srv.proc.pid, signal.SIGHUP)
    assert srv.wait_until(lambda: srv.proc.poll() is not None, timeout=60), (
        "shutdown was consumed while draining; the replacement kept serving"
    )
    assert srv.proc.returncode == 0, srv.log_text()
    assert "New server has started" in srv.log_text(), srv.log_text()
    assert "Forced shutdown" in srv.log_text(), srv.log_text()


@requires_pg
@requires_posix
class TestSighupReloadKeepsServing:
    def test_no_connection_is_refused_across_a_reload(self, server):
        srv = server("--workers", str(WORKERS))
        assert srv.wait_until(lambda: len(_child_pids(srv)) == WORKERS, timeout=60), (
            "master never reached its worker population"
        )
        original = _child_pids(srv)

        with Poller(srv.port) as poller:
            time.sleep(1.0)
            baseline = poller.served
            assert baseline > 0, "the poller never reached the server before the reload"

            os.kill(srv.proc.pid, signal.SIGHUP)

            def reload_complete():
                current = _child_pids(srv)
                return bool(current) and not (original & current) and srv.is_serving(3)

            done = srv.wait_until(
                reload_complete, timeout=RELOAD_TIMEOUT_S, interval=0.5
            )

        assert poller.refused == 0, (
            f"{poller.refused} connection(s) REFUSED during the reload "
            f"({poller.served} served, other errors: {set(poller.other)}). The "
            f"listen socket was not carried across the re-exec, so the port was "
            f"unbound for the length of a server boot."
        )
        assert done, (
            f"reload did not complete within {RELOAD_TIMEOUT_S:.0f}s; original "
            f"workers still alive: {sorted(original & _child_pids(srv))}, "
            f"current children: {sorted(_child_pids(srv))}"
        )
        assert poller.served > baseline, (
            "no request was served after the reload started; the test proves "
            "nothing about continuity"
        )
        assert srv.is_serving(), "server is not serving after the reload"
        log = srv.log_text()
        assert "Reloading server" in log and "New server has started" in log, (
            "SIGHUP did not drive the reload handshake; this test is "
            "no longer exercising the socket handoff"
        )

    def test_the_websocket_port_is_never_unbound_either(self, server):
        srv = server("--workers", str(WORKERS))
        assert srv.wait_until(lambda: _websocket_port(srv) is not None, timeout=60)
        port = _websocket_port(srv)
        with Poller(port) as poller:
            time.sleep(1.0)
            baseline = poller.served
            assert baseline > 0
            os.kill(srv.proc.pid, signal.SIGHUP)
            done = srv.wait_until(
                lambda: (
                    "New server has started" in srv.log_text()
                    and srv.log_text().count("Evented/WebSocket service running") == 2
                ),
                timeout=RELOAD_TIMEOUT_S,
                interval=0.5,
            )
            time.sleep(2.0)
        assert poller.refused == 0 and not poller.other, (
            f"{poller.refused} refused, other errors {set(poller.other)}: the "
            f"replacement's evented child bound the websocket port itself instead "
            f"of adopting the master's"
        )
        assert done, srv.log_text()[-2000:]
        assert poller.served > baseline

    def test_a_threaded_reexec_refuses_no_connection_either(self, server):
        srv = server("--workers", "0")
        assert srv.is_serving()
        with Poller(srv.port) as poller:
            time.sleep(1.0)
            baseline = poller.served
            assert baseline > 0

            os.kill(srv.proc.pid, signal.SIGHUP)
            done = srv.wait_until(
                lambda: (
                    "inherited from the server this one replaced" in srv.log_text()
                    and srv.is_serving(3)
                ),
                timeout=RELOAD_TIMEOUT_S,
                interval=0.5,
            )

        assert poller.refused == 0, (
            f"{poller.refused} connection(s) REFUSED across the threaded re-exec "
            f"({poller.served} served, other errors: {set(poller.other)}); the "
            f"listening socket was closed before execve instead of bequeathed"
        )
        assert done, srv.log_text()[-2000:]
        assert poller.served > baseline
        assert srv.proc.poll() is None, "a re-exec keeps the pid"

    def test_the_poller_would_notice_a_dead_port(self, server):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            dead_port = s.getsockname()[1]
        with Poller(dead_port) as poller:
            time.sleep(0.5)
        assert poller.refused > 0, (
            "the poller does not detect a closed port, so the continuity "
            "assertion above would pass no matter what the server did"
        )


@requires_pg
@requires_posix
@pytest.mark.parametrize("failure", ["preload", "worker_start"])
def test_failed_replacements_leave_the_same_generation_serving(
    server, tmp_path, failure
):
    addon = tmp_path / "addons" / "service_preload_probe"
    addon.mkdir(parents=True)
    marker = tmp_path / "reject-preload"
    pidfile = tmp_path / "supervisor.pid"
    (addon / "__manifest__.py").write_text(
        "{'name': 'Service preload probe', 'license': 'LGPL-3', 'depends': ['base']}\n"
    )
    (addon / "__init__.py").write_text(
        "import os, time\nfrom pathlib import Path\nfrom odoo.service import _prefork, _worker\n"
        "if Path(os.environ['SERVICE_PRELOAD_MARKER']).exists():\n"
        "    if os.environ['SERVICE_FAILURE_KIND'] == 'preload':\n"
        "        _prefork.preload_registries = lambda preload: 3\n"
        "    else:\n"
        "        original_start = _worker.threading.Thread.start\n"
        "        def start(thread):\n"
        "            if thread.name.startswith('Worker WorkerHTTP '):\n"
        "                time.sleep(1)\n"
        "                raise RuntimeError('injected work-thread startup failure')\n"
        "            return original_start(thread)\n"
        "        _worker.threading.Thread.start = start\n"
    )
    paths = f"{REPO_ROOT / 'odoo/addons'},{REPO_ROOT / 'addons'},{addon.parent}"
    srv = server(
        "--workers",
        "2",
        "--pidfile",
        str(pidfile),
        "--load",
        "web,service_preload_probe",
        "--addons-path",
        paths,
        env={
            "SERVICE_PRELOAD_MARKER": str(marker),
            "SERVICE_FAILURE_KIND": failure,
            "ODOO_RELOAD_TIMEOUT": "4",
        },
    )
    assert srv.wait_until(lambda: len(_child_pids(srv)) == 2)
    original = _child_pids(srv)
    assert pidfile.read_text() == str(srv.proc.pid)
    marker.touch()
    with Poller(srv.port) as poller:
        for attempt in range(2):
            os.kill(srv.proc.pid, signal.SIGHUP)
            assert srv.wait_until(
                lambda attempt=attempt: (
                    srv.log_text().count("Reload aborted") > attempt
                ),
                timeout=30,
            )
            assert srv.wait_until(lambda: _child_pids(srv) == original)
            assert srv.proc.poll() is None and srv.is_serving()
            if failure == "worker_start":
                assert "injected work-thread startup failure" in srv.log_text()
            assert pidfile.is_file(), (
                "a rejected candidate removed the supervisor PID file"
            )
            assert pidfile.read_text() == str(srv.proc.pid)
    assert poller.refused == 0
    marker.unlink()
    os.kill(srv.proc.pid, signal.SIGHUP)
    assert srv.wait_until(
        lambda: (
            len(_child_pids(srv)) == 2 and not original.intersection(_child_pids(srv))
        ),
        timeout=60,
    )
    assert srv.is_serving()
    assert pidfile.read_text() == str(srv.proc.pid)


@requires_pg
@requires_posix
def test_an_evented_child_restart_refuses_no_websocket_connection(server):
    srv = server("--workers", "1")
    assert srv.wait_until(lambda: _websocket_port(srv) is not None, timeout=60)
    port = _websocket_port(srv)
    first = _evented_child(srv)
    assert first is not None
    with Poller(port) as poller:
        time.sleep(0.5)
        first.send_signal(signal.SIGTERM)
        assert srv.wait_until(
            lambda: (
                (child := _evented_child(srv)) is not None and child.pid != first.pid
            ),
            timeout=30,
        )
        assert srv.wait_until(
            lambda: srv.log_text().count("Evented/WebSocket service running") == 2, 30
        )
        time.sleep(1.0)
    assert poller.refused == 0 and not poller.other, (
        f"{poller.refused} refused, other errors {set(poller.other)}: the "
        f"websocket port went away with the evented child instead of staying "
        f"bound in the master"
    )
    assert poller.served > 0
    assert "holding respawn" not in srv.log_text()
