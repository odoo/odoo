import psycopg
import psycopg_pool
import pytest

from .conftest import requires_pg


@pytest.fixture
def real_pool(scratch_db):
    pool = psycopg_pool.ConnectionPool(
        f"dbname={scratch_db}",
        min_size=0,
        max_size=4,
        open=True,
        connection_class=psycopg.Connection,
    )
    try:
        yield pool
    finally:
        pool.close()


def _hold(pool, n):
    return [pool.getconn(timeout=5) for _ in range(n)]


@requires_pg
class TestCloseIdleConnectionsAgainstTheInstalledPool:
    def test_the_attributes_the_trim_reads_exist_and_mean_what_it_assumes(
        self, real_pool
    ):
        held = _hold(real_pool, 3)
        for conn in held:
            real_pool.putconn(conn)
        assert real_pool._nconns == 3, "every connection ever made, idle or out"
        assert len(real_pool._pool) == 3, "the idle deque"
        assert real_pool._nconns_min <= 3, "the shrink task's low-water mark"
        assert real_pool.min_size == 0
        assert callable(real_pool._close_connection)
        assert real_pool.get_stats()["pool_size"] == real_pool._nconns

    def test_trimming_closes_the_oldest_idle_and_the_pool_keeps_serving(
        self, real_pool
    ):
        from odoo.db.reaper import close_idle_connections

        held = _hold(real_pool, 3)
        pids = [c.info.backend_pid for c in held]
        for conn in held:
            real_pool.putconn(conn)
        assert close_idle_connections(real_pool, 2) == 2
        stats = real_pool.get_stats()
        assert (stats["pool_size"], stats["pool_available"]) == (1, 1)
        with real_pool.connection(timeout=5) as conn:
            assert conn.info.backend_pid == pids[2], (
                "the two oldest went; the newest idle connection survived"
            )
            assert conn.execute("SELECT 1").fetchone() == (1,)
        with psycopg.connect(real_pool.conninfo) as raw:
            alive = {
                row[0]
                for row in raw.execute(
                    "SELECT pid FROM pg_stat_activity WHERE pid = ANY(%s)", (pids,)
                ).fetchall()
            }
        assert alive == {pids[2]}, "the trimmed backends are gone on the server"

    def test_a_trim_never_leaves_the_pool_below_min_size(self, scratch_db):
        from odoo.db.reaper import close_idle_connections

        pool = psycopg_pool.ConnectionPool(
            f"dbname={scratch_db}", min_size=2, max_size=4, open=True
        )
        try:
            pool.wait(timeout=10)
            assert close_idle_connections(pool, 5) == 0
            assert pool.get_stats()["pool_size"] == 2
        finally:
            pool.close()
