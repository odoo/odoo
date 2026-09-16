import os
import pathlib
import shutil
import subprocess
import tempfile
import time

import psycopg
import pytest

from .conftest import requires_pg


def _pg_bin(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    candidates = sorted(pathlib.Path("/usr/lib/postgresql").glob(f"*/bin/{name}"))
    return str(candidates[-1]) if candidates else None


def _primary_socket_dir() -> str | None:
    try:
        with psycopg.connect("dbname=postgres", connect_timeout=3) as conn:
            row = conn.execute("SHOW unix_socket_directories").fetchone()
    except Exception:
        return None
    return row[0].split(",")[0].strip() if row else None


@pytest.fixture(scope="module")
def standby(scratch_db):
    basebackup, pg_ctl = _pg_bin("pg_basebackup"), _pg_bin("pg_ctl")
    if not basebackup or not pg_ctl:
        pytest.skip("pg_basebackup/pg_ctl not found")
    socket_dir = _primary_socket_dir()
    if not socket_dir:
        pytest.skip("primary socket directory unknown")
    root = pathlib.Path(tempfile.mkdtemp(prefix="odoo_standby_"))
    data, sock = root / "data", root / "sock"
    sock.mkdir()
    port = 54000 + (os.getpid() % 1000)
    taken = subprocess.run(
        [basebackup, "-D", data, "-R", "-X", "stream", "-c", "fast", "-h", socket_dir],
        capture_output=True,
        text=True,
        check=False,
    )
    if taken.returncode != 0:
        shutil.rmtree(root, ignore_errors=True)
        pytest.skip(f"pg_basebackup refused: {taken.stderr.strip()[:200]}")
    (data / "postgresql.conf").write_text(
        f"port = {port}\nunix_socket_directories = '{sock}'\n"
        "listen_addresses = ''\nhot_standby = on\nlogging_collector = off\n",
        encoding="utf-8",
    )
    (data / "pg_hba.conf").write_text(
        "local all all peer\nlocal replication all peer\n", encoding="utf-8"
    )
    (data / "pg_ident.conf").write_text("", encoding="utf-8")
    started = subprocess.run(
        [pg_ctl, "-D", data, "-l", root / "log", "-w", "start"],
        capture_output=True,
        text=True,
        check=False,
    )
    if started.returncode != 0:
        shutil.rmtree(root, ignore_errors=True)
        pytest.skip(f"standby did not start: {started.stderr.strip()[:200]}")
    try:
        deadline = time.monotonic() + 20
        while True:
            try:
                with psycopg.connect(
                    f"host={sock} port={port} dbname={scratch_db}", connect_timeout=2
                ) as conn:
                    if conn.execute("SELECT pg_is_in_recovery()").fetchone()[0]:
                        break
            except psycopg.OperationalError:
                if time.monotonic() > deadline:
                    pytest.skip("standby never came up in recovery")
                time.sleep(0.2)
        yield {"host": sock, "port": port}
    finally:
        subprocess.run(
            [pg_ctl, "-D", data, "-m", "immediate", "stop"],
            capture_output=True,
            check=False,
        )
        shutil.rmtree(root, ignore_errors=True)


@pytest.fixture
def router(scratch_db, standby):
    from odoo.db import Connection, ConnectionPool
    from odoo.db import settings as pool_settings
    from odoo.db.replica import ReplicaRouter
    from odoo.db.utils import get_connection_info_for_database

    with pool_settings.override(
        replica_host=standby["host"], replica_port=standby["port"]
    ) as settings:
        _, primary_info = get_connection_info_for_database(
            scratch_db, settings=settings
        )
        _, replica_info = get_connection_info_for_database(
            scratch_db, readonly=True, settings=settings
        )
        primary_pool = ConnectionPool(maxconn=4, settings=settings)
        replica_pool = ConnectionPool(maxconn=4, readonly=True, settings=settings)
        try:
            yield ReplicaRouter(
                Connection(primary_pool, scratch_db, primary_info),
                Connection(replica_pool, scratch_db, replica_info),
                max_lag=1.0,
                write_pin=2.0,
            )
        finally:
            primary_pool.close_all()
            replica_pool.close_all()


def _standby_sql(standby, scratch_db, sql):
    with psycopg.connect(
        f"host={standby['host']} port={standby['port']} dbname={scratch_db}",
        autocommit=True,
    ) as conn:
        return conn.execute(sql).fetchone()


@requires_pg
class TestAgainstARealStandby:
    def test_a_read_only_cursor_lands_on_the_standby(self, router):
        cr, mode = router.cursor(readonly=True)
        try:
            cr.execute("SELECT pg_is_in_recovery()")
            assert mode == "ro"
            assert cr.fetchone() == (True,)
        finally:
            cr.close()

    def test_a_write_on_the_standby_is_refused(self, router):
        cr, _mode = router.cursor(readonly=True)
        try:
            with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
                cr.execute("CREATE TABLE never (id int)")
        finally:
            cr.close()

    def test_apply_lag_past_the_ceiling_demotes_and_catching_up_restores(
        self, router, standby, scratch_db
    ):
        _standby_sql(standby, scratch_db, "SELECT pg_wal_replay_pause()")
        try:
            # pg_wal_replay_pause() only requests; recovery honours it on its
            # next check, and a commit sent before that is replayed anyway.
            deadline = time.monotonic() + 10
            while _standby_sql(
                standby, scratch_db, "SELECT pg_get_wal_replay_pause_state()"
            ) != ("paused",):
                assert time.monotonic() < deadline, "replay never paused"
                time.sleep(0.05)
            cr, _mode = router.cursor(readonly=False)
            cr.execute("CREATE TABLE lagged (id int)")
            cr.commit()
            cr.close()
            time.sleep(1.6)
            router.lag._last_sample = 0.0
            cr, mode = router.cursor(readonly=True)
            cr.close()
            assert mode == "ro->rw", router.lag.get_snapshot()
            assert not router.lag.is_replica_usable()
        finally:
            _standby_sql(standby, scratch_db, "SELECT pg_wal_replay_resume()")
        time.sleep(0.5)
        router.lag._last_sample = 0.0
        cr, mode = router.cursor(readonly=True)
        cr.close()
        assert mode == "ro", router.lag.get_snapshot()

    def test_a_session_that_wrote_reads_from_the_primary_for_the_pin_window(
        self, router
    ):
        cr, mode = router.cursor(readonly=False, pin_key="sid")
        assert mode == "rw"
        cr.execute("CREATE TABLE pinned (id int)")
        cr.commit()
        cr.close()
        assert router.pins.is_pinned("sid")
        cr, mode = router.cursor(readonly=True, pin_key="sid")
        try:
            cr.execute("SELECT pg_is_in_recovery()")
            assert (mode, cr.fetchone()) == ("ro->rw", (False,))
        finally:
            cr.close()
        cr, mode = router.cursor(readonly=True, pin_key="other")
        cr.close()
        assert mode == "ro"

    def test_a_session_that_only_read_keeps_the_replica(self, router):
        cr, _mode = router.cursor(readonly=False, pin_key="reader")
        cr.execute("SELECT 1")
        cr.commit()
        cr.close()
        assert not router.pins.is_pinned("reader")
