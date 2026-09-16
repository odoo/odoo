"""Contracts recovered by the adversarial service audit."""

import contextlib
import errno
import logging
import os
import selectors
import signal
import socket
import sys
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from odoo.exceptions import AccessError
from odoo.service import _cron, _prefork, _process_state, _reload, _worker, model
from odoo.service.db import _dump_scanner, dump, lifecycle
from odoo.service.settings import override
from odoo.tools import frozendict, lazy
from odoo.tools.misc import ReadonlyDict

from .conftest import build_worker


@pytest.mark.parametrize("operation", ["setblocking", "settimeout", "setsockopt"])
def test_accepted_socket_setup_failure_still_releases_the_client(
    operation, worker_multi
):
    worker = build_worker(_worker.WorkerHTTP, worker_multi, sock_timeout=5)
    client = MagicMock()
    getattr(client, operation).side_effect = OSError("socket setup failed")
    with (
        patch.object(_worker, "serve_prefork_connection") as serve,
        pytest.raises(OSError, match="socket setup failed"),
    ):
        worker.process_request(client, ("127.0.0.1", 1234))
    client.close.assert_called_once_with()
    serve.assert_not_called()
    assert worker.request_count == 0


@pytest.mark.parametrize("sig", [signal.SIGINT, signal.SIGTERM])
def test_reload_drain_preserves_shutdown_for_the_supervisor(master, sig):
    master.workers = {123: MagicMock()}
    master.queue.append(sig)
    with (
        patch.object(master, "kill_worker"),
        patch.object(master, "_stop_long_polling"),
    ):
        _prefork.PreforkServer.stop_workers_gracefully(master)
    # A reload resumes its outer loop after draining the old generation.
    # That loop must still observe a shutdown consumed by the nested drain.
    with pytest.raises(KeyboardInterrupt):
        master.apply_pending_signals()
    assert not master.queue


@pytest.fixture
def master():
    with override(workers=2, http_enable=False, max_cron_threads=0, job_workers=0):
        srv = _prefork.PreforkServer(None)
        srv.pipe = srv.open_pipe()
        srv.stop_workers_gracefully = MagicMock()
        try:
            yield srv
        finally:
            if srv.handoff.replacement is not None:
                srv.handoff.stop_generation(srv.handoff.replacement)
            srv._close_watchdog_selector()
            for fd in srv.pipe:
                os.close(fd)


def test_reload_signals_are_coalesced_while_pending(master):
    for _ in range(10):
        master.signal_handler(signal.SIGHUP, None)
    assert list(master.queue) == [signal.SIGHUP]
    assert os.read(master.pipe[0], 100) == b"."


def test_drain_defers_reload_without_hiding_shutdown(master, monkeypatch):
    monkeypatch.setattr(_process_state, "server_phoenix", False)
    master.queue.append(signal.SIGHUP)
    try:
        master.apply_pending_signals(draining=True)
    except KeyboardInterrupt:
        pytest.fail("reload interrupted draining instead of remaining queued")
    assert not _process_state.server_phoenix
    master.queue.append(signal.SIGTERM)
    with pytest.raises(KeyboardInterrupt):
        master.apply_pending_signals(draining=True)
    assert list(master.queue) == [signal.SIGTERM, signal.SIGHUP]
    with pytest.raises(KeyboardInterrupt):
        master.apply_pending_signals()
    with pytest.raises(KeyboardInterrupt):
        master.apply_pending_signals()
    assert _process_state.server_phoenix


@pytest.mark.parametrize("sig", [signal.SIGTTIN, signal.SIGTTOU])
def test_drain_defers_scaling_to_the_serving_replacement(master, sig):
    population = master.population
    master.queue.append(sig)
    master.apply_pending_signals(draining=True)
    assert master.population == population
    master.queue.append(signal.SIGTERM)
    with pytest.raises(KeyboardInterrupt):
        master.apply_pending_signals(draining=True)
    assert list(master.queue) == [signal.SIGTERM, sig]
    with pytest.raises(KeyboardInterrupt):
        master.apply_pending_signals()
    replacement = master.handoff.replacement = MagicMock()
    try:
        master.apply_pending_signals()
        replacement.send_signal.assert_called_once_with(sig)
        assert master.population == population + (1 if sig == signal.SIGTTIN else -1)
        assert not master.queue
    finally:
        master.handoff.replacement = None


@pytest.mark.parametrize(
    ("signals", "population"),
    [((signal.SIGTTIN, signal.SIGTTOU), 0), ((signal.SIGTTOU, signal.SIGTTIN), 1)],
)
def test_drain_preserves_scaling_order_at_zero_workers(master, signals, population):
    master.population = 0
    master.queue.extend(signals)
    for _ in range(3):
        master.apply_pending_signals(draining=True)
        assert tuple(master.queue) == signals
    master.apply_pending_signals()
    assert master.population == population


@pytest.mark.parametrize("failure", ["arguments", "spawn"])
def test_reload_preparation_failure_releases_its_pipe(master, monkeypatch, failure):
    allocated = []
    pipe2 = os.pipe2

    def open_pipe(flags):
        pipe = pipe2(flags)
        allocated.extend(pipe)
        return pipe

    monkeypatch.setattr(os, "pipe2", open_pipe)
    target = _reload if failure == "arguments" else _reload.subprocess
    name = "stripped_sys_argv" if failure == "arguments" else "Popen"
    try:
        with patch.object(
            target, name, side_effect=OSError("reload preparation failed")
        ):
            with pytest.raises(OSError, match="reload preparation failed"):
                master.reload()
        for fd in allocated:
            with pytest.raises(OSError) as error:
                os.fstat(fd)
            assert error.value.errno == errno.EBADF
        assert master.handoff.candidate is None
    finally:
        for fd in allocated:
            with contextlib.suppress(OSError):
                os.close(fd)


def test_exited_candidate_is_not_promoted_even_if_it_wrote_ready(master, monkeypatch):
    monkeypatch.setattr(
        _reload,
        "stripped_sys_argv",
        lambda: [
            sys.executable,
            "-c",
            'import os; os.write(int(os.environ["ODOO_RELOAD_READY_FD"]), b"1"); raise SystemExit(3)',
        ],
    )
    monkeypatch.setattr(
        master, "sleep", lambda **kw: master.handoff.candidate.wait(timeout=5)
    )
    assert not master.reload()
    master.stop_workers_gracefully.assert_not_called()
    assert master.handoff.replacement is None


def test_a_replacement_reaped_by_the_master_keeps_its_real_exit_code(master):
    """`waitpid(-1)` in `reap_exited_workers` takes the replacement's status
    before `Popen` can; on this interpreter a later `poll()` then answers 0,
    not None, so without `_record_worker_exit` a crashed replacement would
    end the supervisor with a success code."""
    import subprocess

    master.handoff.replacement = subprocess.Popen(
        [sys.executable, "-c", "raise SystemExit(7)"]
    )
    deadline = time.monotonic() + 10
    while master.handoff.replacement.returncode is None and time.monotonic() < deadline:
        master.reap_exited_workers()
        time.sleep(0.02)
    assert master.handoff.replacement.poll() == 7
    master.handoff.replacement = None


def test_unready_candidate_cancellation_does_not_wait_for_graceful_shutdown(
    master, monkeypatch
):
    monkeypatch.setenv("ODOO_RELOAD_TIMEOUT", "1")
    monkeypatch.setattr(_reload, "get_graceful_stop_timeout", lambda logger: 0)
    monkeypatch.setattr(
        _reload,
        "stripped_sys_argv",
        lambda: [
            sys.executable,
            "-c",
            "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)",
        ],
    )
    started = time.monotonic()
    assert not master.reload()
    assert time.monotonic() - started < 5, (
        "unready candidate cancellation blocked the healthy generation's supervision"
    )
    master.stop_workers_gracefully.assert_not_called()


@pytest.mark.parametrize("failure", ["thread_start", "signal_mask"])
def test_worker_startup_failure_cannot_publish_readiness(master, monkeypatch, failure):
    worker = _worker.Worker(master)
    monkeypatch.setattr(worker, "start", lambda: None)
    monkeypatch.setattr(worker, "stop", lambda: None)
    target = _worker.threading.Thread if failure == "thread_start" else _worker.signal
    name = "start" if failure == "thread_start" else "pthread_sigmask"
    try:
        with patch.object(target, name, side_effect=RuntimeError("startup failure")):
            expected = RuntimeError if failure == "thread_start" else SystemExit
            with pytest.raises(expected) as error:
                worker.run()
        if failure == "signal_mask":
            assert error.value.code == 1
            assert str(worker._runloop_exc) == "startup failure"
        with pytest.raises(BlockingIOError):
            os.read(worker.watchdog_pipe[0], 100)
    finally:
        worker.close()


@pytest.mark.parametrize("supervisor", [None, "0", "42"])
def test_only_the_supervisor_owns_pidfile_cleanup(tmp_path, monkeypatch, supervisor):
    import odoo
    from odoo.cli import server as cli_server
    from odoo.tools import config

    pidfile = tmp_path / "server.pid"
    pidfile.write_text("original supervisor")
    monkeypatch.setattr(odoo, "evented", False)
    if supervisor is None:
        monkeypatch.delenv("ODOO_RELOAD_SUPERVISOR_PID", raising=False)
    else:
        monkeypatch.setenv("ODOO_RELOAD_SUPERVISOR_PID", supervisor)
    with (
        config.patch(pidfile=str(pidfile)),
        patch.object(cli_server.atexit, "register") as register,
    ):
        cli_server.write_pid_file()
    if supervisor == "42":
        assert pidfile.read_text() == "original supervisor"
        register.assert_not_called()
    else:
        assert pidfile.read_text() == str(os.getpid())
        register.assert_called_once_with(cli_server.remove_pid_file, os.getpid())


@pytest.mark.parametrize("evented", [False, True])
def test_only_the_master_creates_the_configured_databases(monkeypatch, evented):
    import odoo
    from odoo.cli import server as cli_server
    from odoo.tools import config

    monkeypatch.setattr(odoo, "evented", evented)
    calls = []
    init = {}
    with (
        config.patch(db_name=["one", "two"], init=init, stop_after_init=True),
        patch.object(cli_server, "warn_running_as_root"),
        patch.object(cli_server, "check_db_user_not_postgres"),
        patch.object(cli_server, "report_configuration"),
        patch.object(cli_server, "check_db_not_maintenance"),
        patch.object(cli_server, "write_pid_file"),
        patch.object(cli_server.config, "parse_config"),
        patch.object(cli_server.db, "_create_empty_database", calls.append),
        patch.object(cli_server.server, "start", return_value=0),
        pytest.raises(SystemExit) as exit_info,
    ):
        cli_server.run_server([])
    assert exit_info.value.code == 0
    assert calls == ([] if evented else ["one", "two"])
    assert init.get("base") is (None if evented else True)


def test_a_forked_worker_closes_the_websocket_listener(master):
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    master.websocket_socket = listener
    worker = _worker.Worker(master)
    try:
        master._close_inherited_pipe_fds_in_child(worker)
        assert master.websocket_socket is None
        assert listener.fileno() == -1, "the child's copy of the listener is closed"
    finally:
        # This exercises child cleanup in-process, so replace its closed pipe.
        worker.close()
        listener.close()
        master.pipe = master.open_pipe()


def test_respawned_worker_closes_inherited_reload_reader(master):
    read_fd, write_fd = master.open_pipe()
    selector = selectors.DefaultSelector()
    selector.register(read_fd, selectors.EVENT_READ)
    master.handoff.reader = (read_fd, selector)
    worker = _worker.Worker(master)
    try:
        master._close_inherited_pipe_fds_in_child(worker)
        with pytest.raises(OSError) as error:
            os.fstat(read_fd)
        assert error.value.errno == errno.EBADF
        assert selector.get_map() is None
        for fd in (*worker.watchdog_pipe, *worker.wakeup_pipe):
            os.fstat(fd)
    finally:
        # This exercises child cleanup in-process, so replace its closed pipe.
        worker.close()
        selector.close()
        master.handoff.reader = None
        for fd in (read_fd, write_fd):
            with contextlib.suppress(OSError):
                os.close(fd)
        master.pipe = master.open_pipe()


@pytest.mark.parametrize("heartbeat", [False, True])
def test_reload_keeps_reading_heartbeats_and_enforcing_timeouts(
    master, monkeypatch, heartbeat
):
    read_fd, write_fd = master.open_pipe()
    worker = SimpleNamespace(
        watchdog_pipe=(read_fd, write_fd),
        watchdog_time=float("-inf"),
        watchdog_timeout=60,
        ready=True,
    )
    master.workers = {123: worker}
    monkeypatch.setattr(
        _reload,
        "stripped_sys_argv",
        lambda: [
            sys.executable,
            "-c",
            'import os,time; time.sleep(0.2); os.write(int(os.environ["ODOO_RELOAD_READY_FD"]), b"1"); time.sleep(60)',
        ],
    )
    if heartbeat:
        os.write(write_fd, b".")
    try:
        with patch.object(
            master, "kill_worker", side_effect=lambda pid, sig: master.workers.pop(pid)
        ) as kill:
            assert master.reload()
        if heartbeat:
            kill.assert_not_called()
            assert worker.watchdog_time > 0
        else:
            kill.assert_called_once_with(123, signal.SIGKILL)
    finally:
        os.close(read_fd)
        os.close(write_fd)


@pytest.mark.parametrize("outcome", ["ready", "exit", "timeout"])
def test_reload_promotes_only_a_ready_process(master, monkeypatch, outcome):
    monkeypatch.setenv("ODOO_RELOAD_TIMEOUT", "1")
    code = {
        "ready": 'import os,time; os.write(int(os.environ["ODOO_RELOAD_READY_FD"]), b"1"); time.sleep(60)',
        "exit": "raise SystemExit(3)",
        "timeout": "import time; time.sleep(60)",
    }[outcome]
    monkeypatch.setattr(
        _reload, "stripped_sys_argv", lambda: [sys.executable, "-c", code]
    )
    assert master.reload() is (outcome == "ready")
    assert master.stop_workers_gracefully.call_count == (outcome == "ready")
    assert master.handoff.candidate is None
    if outcome == "ready":
        assert master.handoff.replacement.poll() is None
    else:
        assert master.handoff.replacement is None


def test_failed_second_reload_keeps_the_running_generation(master, monkeypatch):
    ready = 'import os,time; os.write(int(os.environ["ODOO_RELOAD_READY_FD"]), b"1"); time.sleep(60)'
    monkeypatch.setattr(
        _reload, "stripped_sys_argv", lambda: [sys.executable, "-c", ready]
    )
    assert master.reload()
    first = master.handoff.replacement
    monkeypatch.setattr(
        _reload,
        "stripped_sys_argv",
        lambda: [sys.executable, "-c", "raise SystemExit(3)"],
    )
    assert not master.reload()
    assert master.handoff.replacement is first
    assert first.poll() is None
    monkeypatch.setattr(
        _reload, "stripped_sys_argv", lambda: [sys.executable, "-c", ready]
    )
    assert master.reload()
    assert first.poll() is not None
    assert master.handoff.replacement.poll() is None
    assert master.stop_workers_gracefully.call_count == 1


def test_scale_down_does_not_signal_a_draining_worker_twice(master):
    master.workers_http = dict.fromkeys((11, 12, 13), MagicMock())
    with patch.object(master, "kill_worker") as kill:
        master._retire_excess_workers()
        master._retire_excess_workers()
        kill.assert_called_once_with(11, signal.SIGINT)
        master.population = 1
        master._retire_excess_workers()
        assert kill.call_args.args == (12, signal.SIGINT)
    assert set(master.workers_http) == {11, 12, 13}


def test_respawn_delay_remains_bounded_after_thousands_of_failures(master):
    with (
        patch.object(_prefork.time, "monotonic", return_value=100),
        patch.object(master.logger, "warning"),
    ):
        for _ in range(2048):
            master._record_spawn_failure()
    assert master._get_respawn_hold(_prefork.SPAWN_HOLD).not_before == 130


def test_selector_allocation_failure_closes_the_acquired_cursor():
    cursor = MagicMock()
    listener = _cron.CronListener("test", logging.getLogger(__name__))
    with (
        patch.object(_cron, "open_cron_listener", return_value=cursor),
        patch.object(
            _cron.selectors,
            "DefaultSelector",
            side_effect=OSError(errno.EMFILE, "FD limit"),
        ),
    ):
        with pytest.raises(OSError):
            listener.connect()
    cursor.close.assert_called_once()
    assert not listener.connected


def test_schedule_bounds_first_and_overdue_waits():
    clock = SimpleNamespace(now=100)
    schedule = _cron.CronSchedule(lambda: ["owned"], clock=lambda: clock.now)
    assert schedule.polling_delay == 0
    assert schedule.get_due_databases([]) == ["owned"]
    assert schedule.polling_delay == 60
    clock.now += 59
    assert schedule.polling_delay == 1
    clock.now += 2
    assert schedule.polling_delay == 0


@pytest.mark.parametrize(
    ("version", "expected"), [(180006, "18.6"), (180000, "18.0"), (170012, "17.12")]
)
def test_manifest_records_the_postgresql_release(version, expected):
    cr = MagicMock()
    cr.connection.info.server_version = version
    cr.fetchall.return_value = []
    assert dump.dump_db_manifest(cr)["pg_version"] == expected


def test_failed_compensation_reports_the_database_without_masking_original(caplog):
    with patch.object(lifecycle, "drop_database", side_effect=OSError("drop denied")):
        lifecycle._rollback_new_database("owned_db", "RESTORE DB")
    assert "owned_db" in caplog.text and "manual cleanup required" in caplog.text
    assert any(record.exc_info for record in caplog.records)


@pytest.mark.parametrize(
    "setting", ["off", "false", "0", "'off'", "'false'", "'0'", "default"]
)
@pytest.mark.parametrize("prefix", ["SET", "SET LOCAL", "SET SESSION"])
def test_scanner_rejects_executable_setting_across_lines_and_comments(setting, prefix):
    sql = f'{prefix} "standard_conforming_strings" /* comment */\n TO\n {setting};\n'
    assert _dump_scanner._get_disallowed_psql_meta_command(sql) is not None


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 'standard_conforming_strings = off';\n",
        "CREATE FUNCTION f() RETURNS text LANGUAGE sql AS $$ SELECT 'standard_conforming_strings = off' $$;\n",
        "-- SET standard_conforming_strings=off;\nSELECT 1;\n",
        "/* SET standard_conforming_strings=off; */ SELECT 1;\n",
        "COPY t FROM stdin;\nstandard_conforming_strings = off\n\\.\n",
        "SET standard_conforming_strings /* c */ TO\n'on';\n",
    ],
)
def test_scanner_accepts_quoted_data_and_explicit_enable(sql):
    assert _dump_scanner._get_disallowed_psql_meta_command(sql) is None


def test_private_metadata_is_rechecked_on_an_inherited_method(monkeypatch):
    class Parent:
        _name = "probe"

        def method(self):
            return 1

    class Child(Parent):
        pass

    monkeypatch.setattr(model, "BaseModel", Parent)
    obj = Child()
    model.get_public_method(obj, "method")
    monkeypatch.setattr(Parent.method, "_api_private", True, raising=False)
    with pytest.raises(AccessError):
        model.get_public_method(obj, "method")


def test_a_rebound_static_descriptor_is_rejected(monkeypatch):
    class Model:
        _name = "probe"

        def method(self):
            return 1

    monkeypatch.setattr(model, "BaseModel", Model)
    obj = Model()
    function = model.get_public_method(obj, "method")
    monkeypatch.setattr(Model, "method", staticmethod(function))
    assert Model.method is function  # The resolved function alone did not change.
    with pytest.raises(AccessError):
        model.get_public_method(obj, "method")


def test_deferred_work_finishes_before_the_retry_boundary_commits(monkeypatch):
    import threading

    events = []
    env = MagicMock()
    monkeypatch.setattr(model.api, "Environment", lambda *a: env)
    monkeypatch.setattr(
        threading.current_thread(), "rpc_model_method", "", raising=False
    )
    monkeypatch.setattr(
        model, "call_kw", lambda *a: lazy(lambda: events.append("deferred") or 42)
    )

    def retry(fn, *args):
        result = fn()
        events.append("commit")
        return result

    monkeypatch.setattr(model, "retrying", retry)
    assert model.execute_cr(MagicMock(), 2, "probe", "method", [], {}) == 42
    assert events == ["deferred", "commit"]


@pytest.mark.parametrize("mapping_type", [dict, frozendict, ReadonlyDict])
@pytest.mark.parametrize("deferred_type", [iter, lazy])
def test_deferred_mapping_values_survive_xmlrpc_materialization(
    mapping_type, deferred_type
):
    from xmlrpc.client import dumps, loads

    def values():
        yield 7
        yield 9

    deferred = lazy(values) if deferred_type is lazy else iter(values())
    original = mapping_type({"values": deferred, "label": "probe"})
    result = model._force_lazy_values(original)
    assert result == {"values": [7, 9], "label": "probe"}
    assert loads(dumps((result,)))[0] == ({"values": [7, 9], "label": "probe"},)
    assert original["values"] is deferred


@pytest.mark.parametrize("mapping_type", [dict, frozendict, ReadonlyDict])
def test_mapping_without_replaced_values_keeps_its_identity(mapping_type):
    original = mapping_type({"value": lazy(lambda: 7), "label": "probe"})
    assert model._force_lazy_values(original) is original
    assert original["value"] == 7


def test_lazy_mapping_callback_can_add_metadata_to_its_source():
    original = {}

    def value():
        original["label"] = "evaluated"
        return 7

    original["value"] = lazy(value)
    assert model._force_lazy_values(original) is original
    assert original == {"value": 7, "label": "evaluated"}


@pytest.mark.parametrize("deferred_type", ["iterator", "lazy"])
def test_shared_deferred_rpc_values_are_materialized_once(deferred_type):
    from xmlrpc.client import dumps, loads

    events = []

    def values():
        events.append("evaluated")
        yield 7
        yield 9

    shared = lazy(values) if deferred_type == "lazy" else values()
    result = model._force_lazy_values({"first": shared, "second": (shared,)})
    assert result == {"first": [7, 9], "second": ([7, 9],)}
    assert result["first"] is result["second"][0]
    assert events == ["evaluated"]
    assert loads(dumps((result,)))[0] == ({"first": [7, 9], "second": [[7, 9]]},)


def test_shared_mapping_replacement_keeps_all_aliases():
    shared = ReadonlyDict({"values": iter((7, 9))})
    result = model._force_lazy_values([shared, shared])
    assert result == [{"values": [7, 9]}, {"values": [7, 9]}]
    assert result[0] is result[1]


def test_rpc_materialization_cache_does_not_escape_one_walk():
    value = {"item": lazy(lambda: 7)}
    assert model._force_lazy_values(value)["item"] == 7
    value["item"] = lazy(lambda: 9)
    assert model._force_lazy_values(value)["item"] == 9


def test_materialization_releases_consumed_iterator_inputs():
    import weakref

    source = (value for value in (7, 9))
    reference = weakref.ref(source)
    result = model._force_lazy_values([source, source])
    del source
    assert reference() is None
    assert result == [[7, 9], [7, 9]]


def test_shared_mapping_graph_does_not_repeat_every_path():
    reads = []

    class CountingMapping(ReadonlyDict):
        def __getitem__(self, key):
            reads.append(key)
            return super().__getitem__(key)

    value = CountingMapping({"value": 7})
    depth = 12
    for _ in range(depth):
        value = CountingMapping({"left": value, "right": value})
    assert model._force_lazy_values(value) is value
    assert len(reads) <= 2 * depth + 1
    assert reads.count("value") == 1


def test_self_yielding_iterator_is_rejected_before_returning_a_result():
    def values():
        yield shared

    shared = values()
    with pytest.raises(ValueError, match="cyclic"):
        model._force_lazy_values(shared)


@pytest.mark.parametrize("mapping_type", [frozendict, ReadonlyDict])
def test_deferred_mapping_failure_retries_before_commit(mapping_type):
    from psycopg.errors import SerializationFailure

    from .conftest import retrying_env

    events = []
    env = retrying_env(on_commit=lambda env: events.append("commit"))

    def invoke():
        attempt = len(events)
        events.append("attempt")

        def values():
            if attempt == 0:
                raise SerializationFailure("deferred conflict")
            yield 7

        return model._force_lazy_values(mapping_type({"values": values()}))

    with patch("odoo.service.transaction.time.sleep"):
        result = model.retrying(invoke, env)
    assert result == {"values": [7]}
    assert events == ["attempt", "attempt", "commit"]
    env.cr.rollback.assert_called_once()


def test_reload_readiness_requires_worker_startup_not_just_a_pid(master):
    import os

    read_fd, write_fd = os.pipe2(os.O_NONBLOCK | os.O_CLOEXEC)
    master.handoff.ready_fd = write_fd
    worker = SimpleNamespace(ready=False)
    master.workers = {123: worker}
    try:
        master._notify_reload_ready()
        with pytest.raises(BlockingIOError):
            os.read(read_fd, 1)
        worker.ready = True
        master._notify_reload_ready()
        assert os.read(read_fd, 1) == b"1"
        assert os.read(read_fd, 1) == b""
    finally:
        os.close(read_fd)
        if master.handoff.ready_fd is not None:
            os.close(write_fd)
            master.handoff.ready_fd = None


def test_scale_up_replaces_capacity_still_draining(master):
    master.workers_http = dict.fromkeys((11, 12, 13), MagicMock())
    master._retiring_workers = {11}
    master.population = 3
    master.long_polling_pid = 99

    def spawn(klass, registry):
        worker = registry[14] = MagicMock()
        return worker

    with (
        override(http_enable=True),
        patch.object(master, "spawn_worker", side_effect=spawn) as spawning,
        patch.object(_prefork.Registry, "registries", MagicMock(snapshot={})),
        patch.object(_prefork, "db"),
    ):
        master.spawn_missing_workers()
    spawning.assert_called_once()
    assert set(master.workers_http) == {11, 12, 13, 14}
    assert master._retiring_workers == {11}
