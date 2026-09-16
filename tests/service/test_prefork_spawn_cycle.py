import contextlib
import json
import os
import signal
import time
from unittest.mock import MagicMock, patch

import pytest

from odoo.service import _census, _prefork
from odoo.service import settings as server_settings

from .conftest import prefork_server


class TestTheWorkerCensusCrossesTheFork:
    """`/web/metrics` is an HTTP route, so under prefork a CHILD always serves it.

    A child cannot count its siblings, so `get_metrics()` short-circuited there and
    the four metrics that exist to describe prefork -- `odoo_workers`,
    `odoo_worker_population`, `odoo_worker_generation`,
    `odoo_long_polling_alive` -- were declared by `render_prometheus_exposition` and could
    never be emitted by the only flavour that has them.  Measured before the
    census: threaded exposed four flavour metrics, prefork exposed none.
    """

    @pytest.fixture
    def master(self, tmp_path):
        obj = _prefork.PreforkServer(None)
        obj.pid = os.getpid()
        obj.logger = MagicMock()
        obj.population = 3
        obj.generation = 7
        obj.long_polling_pid = 4242
        obj.workers_http = dict.fromkeys((1, 2, 3), MagicMock())
        obj.workers_cron = dict.fromkeys((4,), MagicMock())
        obj.workers_job = dict.fromkeys((5, 6), MagicMock())
        obj._census.written_at = float("-inf")
        with server_settings.override(data_dir=str(tmp_path)):
            yield obj

    def _child_of(self, master):
        """A forked child: same `self.pid` (the master's), different os.getpid()."""
        child = _prefork.PreforkServer(None)
        child.pid = master.pid
        child.logger = MagicMock()
        return child

    def test_a_child_reads_the_counts_only_the_master_knows(self, master):
        master._publish_census()
        got = self._child_of(master)._census.read()

        assert got == {
            "workers": {"http": 3, "cron": 1, "job": 2},
            "worker_population": 3,
            "worker_generation": 7,
            "worker_exits": {"clean": 0, "terminated": 0, "timeout": 0, "crash": 0},
            "long_polling_alive": True,
        }, "the census is the child's only route to the master's own numbers"

    def test_metrics_dispatches_on_which_side_of_the_fork_it_is(self, master):
        master._publish_census()
        child = self._child_of(master)

        with patch("odoo.service._prefork.os.getpid", return_value=master.pid + 1):
            from_child = child.get_metrics()

        assert from_child == master.get_metrics() == master._get_census(), (
            "a worker serving /web/metrics must answer with the master's "
            "counts, not with {}"
        )

    def test_the_write_is_throttled_so_a_0_1s_shutdown_beat_is_not_10_writes(
        self, master
    ):
        master._publish_census()
        first = json.loads((master._census.path).read_text())

        master.population = 99
        master._publish_census()
        assert json.loads(master._census.path.read_text()) == first

        master._census.written_at = float("-inf")
        master._publish_census()
        assert json.loads(master._census.path.read_text())["worker_population"] == 99

    def test_a_stale_census_answers_nothing_rather_than_phantom_workers(self, master):
        master._publish_census()
        path = master._census.path
        old = time.time() - _census.CENSUS_MAX_AGE_S - 1
        os.utime(path, (old, old))

        assert self._child_of(master)._census.read() == {}, (
            "the file outlives a master that was killed rather than stopped; "
            "reporting its last counts would show a full complement of workers "
            "for a server that is gone"
        )

    def test_a_missing_or_corrupt_census_is_absent_not_an_error(self, master):
        child = self._child_of(master)
        assert child._census.read() == {}

        master._census.path.write_text("{ this is not json")
        assert child._census.read() == {}

        master._census.path.write_text('"a string, not an object"')
        assert child._census.read() == {}

    def test_publishing_never_raises_even_on_a_half_built_server(self):
        """`run()`'s catch-all turns any raise here into `stop(False)`; return -1.

        This is not hypothetical: the first version of `_publish_census` read
        the throttle stamp OUTSIDE its try, and four `TestRun` cases went red
        because the server they build never sets it -- an AttributeError in
        the loop took the whole master down. A server with no census object at
        all is the same shape of failure.
        """
        bare = prefork_server()
        bare._census = MagicMock()
        bare._census.publish.side_effect = OSError("no census")

        bare._publish_census()

        assert bare.logger.debug.called, (
            "a failure must be swallowed and noted, never propagated"
        )

    def test_publishing_never_raises_into_the_masters_run_loop(self, master):
        """It runs in `run()`'s while-loop; a raise there takes the server down.

        The failure mode must be exactly what it was before the census
        existed: the metrics are absent.
        """
        with server_settings.override(data_dir="/proc/nonexistent-dir"):
            master._census.written_at = float("-inf")
            master._publish_census()

        with server_settings.override(data_dir=""):
            master._census.written_at = float("-inf")
            master._publish_census()
            assert master._census.path is None
            assert master._census.read() == {}
            assert master._census.publish(master._get_census) is False

    def test_stopping_removes_the_file(self, master):
        master._publish_census()
        path = master._census.path
        assert path.exists()
        master._census.discard()
        assert not path.exists()
        master._census.discard()

    def test_both_sides_derive_the_same_path_from_the_masters_pid(self, master):
        assert master._census.path == self._child_of(master)._census.path, (
            "the child names the file without being told where it is, because "
            "it inherited the master's pid in self.pid across the fork"
        )

    def test_startup_collects_what_a_killed_master_left_behind(self, master):
        data_dir = master._census.path.parent
        dead = data_dir / "prefork-census-999999.json"
        dead.write_text("{}")
        old = time.time() - _census.CENSUS_MAX_AGE_S - 1
        os.utime(dead, (old, old))

        live = data_dir / "prefork-census-999998.json"
        live.write_text("{}")

        unrelated = data_dir / "sessions.json"
        unrelated.write_text("{}")
        os.utime(unrelated, (old, old))

        master._census.remove_stale()

        assert not dead.exists(), (
            "_discard_census only runs on a clean stop, so without this sweep "
            "every SIGKILLed master leaves a file in data_dir forever"
        )
        assert live.exists(), "a census still being written belongs to a live master"
        assert unrelated.exists(), "the sweep must only claim its own filenames"

    def test_the_sweep_never_takes_our_own_file(self, master):
        master._publish_census()
        path = master._census.path
        old = time.time() - _census.CENSUS_MAX_AGE_S - 1
        os.utime(path, (old, old))

        master._census.remove_stale()

        assert path.exists(), (
            "the sweep runs at start() before we have written anything, but it "
            "must never be able to delete the file this master owns"
        )


@pytest.fixture
def prefork():
    obj = _prefork.PreforkServer(None)
    obj.population = 2
    obj.logger = MagicMock()
    obj.workers = {}
    obj.workers_http = {}
    obj.workers_cron = {}
    obj.workers_job = {}
    obj.long_polling_pid = None
    obj._respawn_holds = {}
    obj.queue = []
    obj._selector = None
    obj._census = _census.WorkerCensus(obj.pid)
    obj.pipe = os.pipe2(os.O_NONBLOCK | os.O_CLOEXEC)
    yield obj
    obj._close_watchdog_selector()
    for fd in obj.pipe:
        with contextlib.suppress(OSError):
            os.close(fd)


class TestSignalHandlerCoalescesSigchld:
    def test_repeated_sigchld_enqueues_once(self, prefork):
        for _ in range(5):
            prefork.signal_handler(signal.SIGCHLD, None)
        assert prefork.queue == [signal.SIGCHLD], (
            "SIGCHLD must be coalesced: the master reaps every zombie in one "
            "reap_exited_workers() pass, so N deaths need one queue entry, not N"
        )

    def test_a_second_sigchld_after_the_queue_drains_is_enqueued_again(self, prefork):
        prefork.signal_handler(signal.SIGCHLD, None)
        prefork.queue.clear()
        prefork.signal_handler(signal.SIGCHLD, None)
        assert prefork.queue == [signal.SIGCHLD]

    @pytest.mark.parametrize("sig", [signal.SIGTTIN, signal.SIGTTOU])
    def test_population_signals_are_not_coalesced(self, prefork, sig):
        prefork.signal_handler(sig, None)
        prefork.signal_handler(sig, None)
        assert prefork.queue == [sig, sig], (
            "population changes count each signal, even while another is pending"
        )

    def test_every_signal_wakes_the_select_loop(self, prefork):
        prefork.signal_handler(signal.SIGTERM, None)
        assert os.read(prefork.pipe[0], 8) == b".", (
            "the handler must ping the self-pipe or sleep() blocks until its "
            "next timeout instead of acting on the signal"
        )

    def test_a_full_pipe_is_not_an_error(self, prefork):
        try:
            while True:
                os.write(prefork.pipe[1], b"." * 4096)
        except BlockingIOError:
            pass
        prefork.signal_handler(signal.SIGCHLD, None)
        assert prefork.queue == [signal.SIGCHLD]


def _fake_worker():
    w = MagicMock()
    w.watchdog_pipe = os.pipe()
    w.wakeup_pipe = os.pipe()
    return w


def _is_open(fd):
    try:
        os.fstat(fd)
        return True
    except OSError:
        return False


class TestChildClosesInheritedFds:
    def test_a_sibling_worker_pipes_are_closed(self, prefork):
        sibling = _fake_worker()
        newborn = _fake_worker()
        prefork.workers = {111: sibling}
        prefork._close_inherited_pipe_fds_in_child(newborn)
        sibling_fds = [*sibling.watchdog_pipe, *sibling.wakeup_pipe]
        assert not any(_is_open(fd) for fd in sibling_fds), (
            f"the child kept a sibling's pipe fds open {sibling_fds}: the "
            "sibling's reader never sees EOF when that worker dies"
        )
        for fd in (*newborn.watchdog_pipe, *newborn.wakeup_pipe):
            assert _is_open(fd), "the child closed its OWN watchdog/eintr pipe"
            os.close(fd)

    def test_the_masters_own_self_pipe_is_closed(self, prefork):
        newborn = _fake_worker()
        master_pipe = prefork.pipe
        prefork._close_inherited_pipe_fds_in_child(newborn)
        assert not any(_is_open(fd) for fd in master_pipe), (
            "the child inherited the master's signal self-pipe; a signal "
            "delivered to the child would ping the master's select loop"
        )
        prefork.pipe = os.pipe2(os.O_NONBLOCK)
        for fd in (*newborn.watchdog_pipe, *newborn.wakeup_pipe):
            os.close(fd)

    def test_closing_an_already_closed_fd_is_tolerated(self, prefork):
        sibling = _fake_worker()
        prefork.workers = {111: sibling}
        os.close(sibling.watchdog_pipe[0])
        newborn = _fake_worker()
        prefork._close_inherited_pipe_fds_in_child(newborn)
        for fd in (*newborn.watchdog_pipe, *newborn.wakeup_pipe):
            os.close(fd)


class TestProcessSpawnChecksSignallingOncePerCycle:
    def _run(self, prefork, registries, cfg):
        spawned = []

        def fake_spawn(klass, registry):
            worker = MagicMock()
            pid = 1000 + len(spawned)
            spawned.append(klass.__name__)
            registry[pid] = worker
            prefork.workers[pid] = worker
            return worker

        snapshot = MagicMock()
        snapshot.snapshot = registries
        with (
            server_settings.override(**cfg),
            patch.object(_prefork.Registry, "registries", snapshot),
            patch.object(_prefork, "db") as fake_db,
            patch.object(prefork, "spawn_worker", side_effect=fake_spawn),
            patch.object(prefork, "spawn_long_polling_process"),
        ):
            prefork.spawn_missing_workers()
        return spawned, fake_db

    def test_signalling_is_checked_once_no_matter_how_many_workers_spawn(self, prefork):
        checks = []
        registry = MagicMock()
        registry.check_signaling.side_effect = checks.append
        cfg = {"http_enable": True, "max_cron_threads": 2, "job_workers": 2}
        prefork.population = 4

        spawned, _ = self._run(prefork, {"db1": registry}, cfg)

        assert len(spawned) == 8, spawned
        assert len(checks) == 1, (
            f"check_signaling ran {len(checks)} times for one spawn cycle that "
            f"forked {len(spawned)} workers; it must run once, before the first "
            "fork, so no child inherits a stale registry and none pays for a "
            "redundant round trip"
        )

    def test_the_live_registry_cache_is_never_emptied(self, prefork):
        registries = {"db1": MagicMock()}
        cfg = {"http_enable": False, "max_cron_threads": 1, "job_workers": 0}
        self._run(prefork, registries, cfg)
        assert registries == {"db1": registries["db1"]}, (
            "spawn_missing_workers mutated the registry mapping it was handed; the "
            "snapshot is a copy today, but clearing it is the shape of the bug "
            "that made this read as emptying the server's live cache"
        )

    def test_no_registries_means_no_check_and_still_spawns(self, prefork):
        cfg = {"http_enable": False, "max_cron_threads": 1, "job_workers": 0}
        spawned, fake_db = self._run(prefork, {}, cfg)
        assert spawned == ["WorkerCron"]
        fake_db.close_all.assert_not_called()

    def test_a_registry_that_raises_does_not_abort_the_cycle(self, prefork):
        bad = MagicMock()
        bad.cursor.side_effect = RuntimeError("db gone")
        good = MagicMock()
        cfg = {"http_enable": False, "max_cron_threads": 2, "job_workers": 0}

        spawned, _ = self._run(prefork, {"bad": bad, "good": good}, cfg)

        assert spawned == ["WorkerCron", "WorkerCron"], (
            "one unreachable database stopped the master from spawning workers"
        )
        good.cursor.assert_called_once()

    def test_the_spawn_hold_suppresses_the_whole_cycle(self, prefork):
        cfg = {"http_enable": True, "max_cron_threads": 2, "job_workers": 2}
        with patch.object(_prefork.time, "monotonic", return_value=100.0):
            prefork._get_respawn_hold(_prefork.SPAWN_HOLD).not_before = 200.0
            spawned, _ = self._run(prefork, {"db1": MagicMock()}, cfg)
        assert spawned == [], (
            "spawn_missing_workers forked inside the respawn backoff window; a "
            "fork that failed would be retried as fast as it fails"
        )

    def test_a_crash_loop_in_one_kind_holds_only_that_kind(self, prefork):
        """One population's early deaths do not delay another's replacements."""
        cfg = {"http_enable": True, "max_cron_threads": 1, "job_workers": 1}
        with patch.object(_prefork.time, "monotonic", return_value=100.0):
            prefork._get_respawn_hold("WorkerCron").not_before = 200.0
            spawned, _ = self._run(prefork, {"db1": MagicMock()}, cfg)
        assert "WorkerCron" not in spawned
        assert "WorkerHTTP" in spawned and "WorkerJob" in spawned

    def test_a_failed_spawn_stops_the_cycle_instead_of_looping(self, prefork):
        cfg = {"http_enable": False, "max_cron_threads": 3, "job_workers": 2}
        with (
            server_settings.override(**cfg),
            patch.object(_prefork.Registry, "registries", MagicMock(snapshot={})),
            patch.object(_prefork, "db"),
            patch.object(prefork, "spawn_worker", return_value=None) as spawn,
        ):
            prefork.spawn_missing_workers()
        assert spawn.call_count == 1, (
            f"spawn_worker returned None (fork failed) and spawn_missing_workers called "
            f"it {spawn.call_count} times in the same cycle. A fork that failed "
            f"with EAGAIN fails for every later class too, so the cycle must be "
            f"abandoned (return), not merely the current loop (break)."
        )


class TestTheWatchdogSelectorIsReused:
    """`sleep()` runs once per beat, and graceful stop drops the beat to 0.1s."""

    @pytest.fixture
    def master(self, prefork):
        prefork.beat = 0
        made = []

        def _add():
            w = MagicMock()
            w.watchdog_pipe = os.pipe2(os.O_NONBLOCK | os.O_CLOEXEC)
            w.watchdog_time = 0.0
            pid = len(made) + 1
            prefork.workers[pid] = w
            made.append(w)
            return pid, w

        yield prefork, _add
        for w in made:
            for fd in w.watchdog_pipe:
                with contextlib.suppress(OSError):
                    os.close(fd)

    def test_the_same_selector_serves_every_beat(self, master):
        prefork, add = master
        add()
        prefork.sleep()
        first = prefork._selector
        prefork.sleep()
        prefork.sleep()
        assert prefork._selector is first, (
            "a new epoll instance per beat; at the 0.1s shutdown beat that is "
            "ten create/teardown pairs a second"
        )

    def test_a_new_worker_is_picked_up_without_rebuilding(self, master):
        prefork, add = master
        prefork.sleep()
        first = prefork._selector
        _, w = add()
        prefork.sleep()
        assert prefork._selector is first
        assert w.watchdog_pipe[0] in set(prefork._selector.get_map())

    def test_a_reaped_worker_is_unregistered(self, master):
        prefork, add = master
        pid, w = add()
        prefork.sleep()
        del prefork.workers[pid]
        prefork.sleep()
        assert w.watchdog_pipe[0] not in set(prefork._selector.get_map())

    def test_the_masters_pipe_is_always_registered(self, master):
        prefork, add = master
        add()
        prefork.sleep()
        assert prefork.pipe[0] in set(prefork._selector.get_map())

    def test_the_forked_child_does_not_inherit_the_epoll_instance(self, master):
        prefork, _add = master
        prefork.sleep()
        assert prefork._selector is not None
        newborn = MagicMock()
        newborn.watchdog_pipe = os.pipe2(os.O_NONBLOCK | os.O_CLOEXEC)
        newborn.wakeup_pipe = os.pipe2(os.O_NONBLOCK | os.O_CLOEXEC)
        try:
            prefork._close_inherited_pipe_fds_in_child(newborn)
        finally:
            for fds in (newborn.watchdog_pipe, newborn.wakeup_pipe):
                for fd in fds:
                    with contextlib.suppress(OSError):
                        os.close(fd)
        assert prefork._selector is None, (
            "a worker never polls the master's watchdog set; carrying the "
            "epoll fd into the fork is one more descriptor per worker"
        )


class TestARecycledFdIsRegisteredForItsNewOwner:
    """`remove_worker` closes the pipe; `open_pipe` hands the same number straight back.

    This is the whole reason the watchdog set is diffed by owner rather than by
    descriptor number.  A master that diffs numbers sees no change across a
    worker replacement, skips the re-register, and keeps a map entry for a
    descriptor epoll dropped when it was closed -- so the replacement is never
    selected on, its `watchdog_time` never advances, and `kill_timed_out_workers`
    SIGKILLs it one `limit_time_real` after it started.  Measured end to end
    before the fix: every replacement worker killed at its timeout while idle,
    respawned, and killed again, indefinitely.

    `TestTheWatchdogSelectorIsReused` cannot see this: it retires a worker with
    `del prefork.workers[pid]`, which leaves the descriptors open, so no number
    is ever recycled.
    """

    @pytest.fixture
    def master(self, prefork):
        prefork.beat = 0
        prefork.logger = MagicMock()
        made = []

        def _spawn(pid):
            w = MagicMock()
            w.watchdog_pipe = os.pipe2(os.O_NONBLOCK | os.O_CLOEXEC)
            w.wakeup_pipe = os.pipe2(os.O_NONBLOCK | os.O_CLOEXEC)
            w.watchdog_time = 0.0
            w.watchdog_timeout = None
            w.close = lambda w=w: [
                os.close(fd)
                for fd in (*w.watchdog_pipe, *w.wakeup_pipe)
                if _still_open(fd)
            ]
            prefork.workers[pid] = w
            prefork.workers_http[pid] = w
            made.append(w)
            return w

        yield prefork, _spawn
        for w in made:
            for fd in (*w.watchdog_pipe, *w.wakeup_pipe):
                with contextlib.suppress(OSError):
                    os.close(fd)

    def test_the_replacement_worker_is_still_watched(self, master):
        prefork, spawn = master

        dying = spawn(101)
        prefork.sleep()

        prefork.remove_worker(101)
        replacement = spawn(102)

        assert replacement.watchdog_pipe[0] == dying.watchdog_pipe[0], (
            "this test is only meaningful when the descriptor is recycled, "
            "which is what pipe2 does with the lowest free numbers"
        )

        os.write(replacement.watchdog_pipe[1], b".")
        prefork.sleep()

        assert replacement.watchdog_time > 0.0, (
            "the replacement's watchdog ping was not observed: the selector "
            "still holds the dead worker's registration for this descriptor "
            "number, so kill_timed_out_workers will SIGKILL a healthy idle worker "
            "one limit_time_real after it spawned"
        )

    def test_kill_timed_out_workers_spares_the_healthy_replacement(self, master):
        """The symptom the operator sees, rather than the mechanism."""
        prefork, spawn = master

        dying = spawn(201)
        prefork.sleep()
        prefork.remove_worker(201)

        replacement = spawn(202)
        assert replacement.watchdog_pipe[0] == dying.watchdog_pipe[0]
        replacement.watchdog_timeout = 0.05
        replacement.watchdog_time = time.monotonic()

        killed = []
        with patch.object(prefork, "kill_worker", lambda pid, sig: killed.append(pid)):
            for _ in range(8):
                prefork.ping_pipe(replacement.watchdog_pipe)
                prefork.sleep()
                time.sleep(0.02)
                prefork.kill_timed_out_workers()

        assert killed == [], (
            f"the master SIGKILLed {killed} — a worker that pinged its "
            f"watchdog pipe on every beat. Left unfixed this is a permanent "
            f"kill/respawn loop: every replacement dies one limit_time_real "
            f"after it spawns, while idle."
        )


def _still_open(fd):
    try:
        os.fstat(fd)
    except OSError:
        return False
    return True


class TestWatchdogSleep:
    @pytest.fixture
    def master(self, prefork):
        prefork.beat = 0
        made = []

        def _worker():
            w = MagicMock()
            w.watchdog_pipe = os.pipe2(os.O_NONBLOCK | os.O_CLOEXEC)
            w.watchdog_time = 0.0
            made.append(w)
            return w

        yield prefork, _worker
        for w in made:
            for fd in w.watchdog_pipe:
                with contextlib.suppress(OSError):
                    os.close(fd)

    def test_a_worker_that_pinged_has_its_clock_refreshed(self, master):
        prefork, make = master
        alive, quiet = make(), make()
        prefork.workers = {1: alive, 2: quiet}
        os.write(alive.watchdog_pipe[1], b".")

        prefork.sleep()

        assert alive.watchdog_time > 0.0, (
            "the worker said it was alive and the master did not record it; "
            "kill_timed_out_workers will SIGKILL it once the beat elapses"
        )
        assert quiet.watchdog_time == 0.0, "a silent worker must not be credited"

    def test_the_ping_is_drained_so_the_next_select_blocks(self, master):
        prefork, make = master
        worker = make()
        prefork.workers = {1: worker}
        os.write(worker.watchdog_pipe[1], b"...")

        prefork.sleep()

        with pytest.raises(BlockingIOError):
            os.read(worker.watchdog_pipe[0], 8)

    def test_the_masters_own_pipe_is_watched_too(self, master):
        prefork, _ = master
        prefork.workers = {}
        os.write(prefork.pipe[1], b".")

        prefork.sleep()

        with pytest.raises(BlockingIOError):
            os.read(prefork.pipe[0], 8)

    def test_a_quiet_beat_credits_nobody(self, master):
        prefork, make = master
        worker = make()
        prefork.workers = {1: worker}
        prefork.sleep()
        assert worker.watchdog_time == 0.0


class TestRun:
    @pytest.fixture
    def running(self, prefork, monkeypatch):
        def _go(
            *,
            stop=False,
            preload_rc=0,
            ready_pid=None,
            loop_raises=None,
            kill_raises=None,
        ):
            calls = []
            for name in (
                "start",
                "apply_pending_signals",
                "reap_exited_workers",
                "kill_timed_out_workers",
                "spawn_missing_workers",
            ):
                setattr(
                    prefork, name, MagicMock(side_effect=lambda n=name: calls.append(n))
                )
            prefork.stop = MagicMock(side_effect=lambda *a: calls.append("stop"))
            prefork.sleep = MagicMock(side_effect=loop_raises or KeyboardInterrupt)
            monkeypatch.delenv("ODOO_READY_SIGHUP_PID", raising=False)
            if ready_pid is not None:
                monkeypatch.setenv("ODOO_READY_SIGHUP_PID", ready_pid)
            with (
                patch.object(_prefork, "preload_registries", return_value=preload_rc),
                patch.object(_prefork, "db") as fake_db,
                patch.object(_prefork.os, "kill", side_effect=kill_raises) as kill,
            ):
                rc = prefork.run(["db"], stop=stop)
            return rc, calls, kill, fake_db

        return _go

    def test_stop_after_init_returns_the_preload_code_without_serving(self, running):
        rc, calls, _, fake_db = running(stop=True, preload_rc=3)
        assert rc == 3
        assert calls == ["start", "stop"], calls
        assert not fake_db.close_all.called, (
            "closing the pools is preparation for forking workers; there are "
            "none on this path"
        )

    def test_serving_closes_the_pools_before_forking(self, running):
        _, calls, _, fake_db = running(stop=False)
        (
            fake_db.close_all.assert_called_once(),
            (
                "a connection open across fork() is shared by parent and child and "
                "corrupts both"
            ),
        )
        assert calls[0] == "start"

    def test_the_loop_runs_the_supervision_pass(self, running):
        _, calls, _, _ = running(stop=False)
        assert calls[1:5] == [
            "apply_pending_signals",
            "reap_exited_workers",
            "kill_timed_out_workers",
            "spawn_missing_workers",
        ], calls

    def test_a_keyboard_interrupt_is_a_clean_stop(self, running):
        rc, calls, _, _ = running(stop=False)
        assert rc is None
        assert calls[-1] == "stop"

    def test_an_uncaught_error_stops_forcefully_and_reports_minus_one(self, running):
        rc, calls, _, _ = running(stop=False, loop_raises=RuntimeError("boom"))
        assert rc == -1, "the master died; a zero exit tells the supervisor it meant to"
        assert calls[-1] == "stop"

    def test_a_system_exit_is_not_swallowed_by_the_catch_all(self, running):
        with pytest.raises(SystemExit):
            running(stop=False, loop_raises=SystemExit(2))

    def test_failed_preload_never_enters_the_supervisor_loop(self, running):
        rc, calls, kill, _ = running(stop=False, preload_rc=3)
        assert rc == 3
        assert calls == ["start", "stop"]
        kill.assert_not_called()
