"""Re-derive the figures odoo/db/README.md cites.

    PYTHONPATH=odoo p314o19m/bin/python -m odoo.db.tests.bench -c p314o19m.conf -d <db>

Every number the README states next to a decision came from one of these
measurements; run this before believing them and after touching the path they
describe. Wire-stubbed rows measure Python only; the others include the
server round trips of a local socket.
"""

from __future__ import annotations

import sys
import threading
import time
import timeit
from time import perf_counter

_ROWS: list[tuple[str, str]] = []


def _report(label: str, value: float, unit: str) -> None:
    _ROWS.append((label, f"{value:9.1f} {unit}"))


def _ns(label: str, fn, number: int = 200_000) -> None:
    _report(label, min(timeit.repeat(fn, number=number, repeat=5)) / number * 1e9, "ns")


def _us(label: str, fn, number: int = 3000) -> None:
    for _ in range(100):
        fn()
    _report(label, min(timeit.repeat(fn, number=number, repeat=3)) / number * 1e6, "us")


class _NoWire:
    description = None
    rowcount = -1

    def execute(self, query, params=None, prepare=None):
        pass

    def executemany(self, query, rows, returning=False):
        pass

    def fetchone(self):
        return (1,)


def _cursor_paths(db_name: str) -> None:
    import psycopg

    from odoo import db
    from odoo.db import ConnectionPool, Cursor
    from odoo.db.ddl import classify_statement
    from odoo.db.lifecycle import (
        _RESET_SESSION_STATE_SQL,
        _probe_liveness,
        _reset_connection,
    )
    from odoo.db.utils import get_connection_info_for_database
    from odoo.libs.sql import SQL

    conn = db.db_connect(db_name)

    def cycle():
        cr = conn.cursor()
        cr.execute("SELECT 1")
        cr.fetchone()
        cr.close()

    _us("cursor cycle: open, SELECT 1, close", cycle)

    cr = conn.cursor()
    cr.execute("SELECT 1")
    cr.fetchone()
    wire, cr._obj = cr._obj, _NoWire()
    _ns(
        "execute() SELECT, wire stubbed",
        lambda: cr.execute("SELECT id, name FROM res_partner WHERE id = %s", (1,)),
    )
    _ns(
        "execute() UPDATE, wire stubbed",
        lambda: cr.execute("UPDATE res_partner SET name = %s WHERE id = %s", ("x", 1)),
    )
    stmt = SQL("SELECT id FROM res_partner WHERE id = %s", 1)
    _ns("execute() SQL object, wire stubbed", lambda: cr.execute(stmt))
    _ns("fetchone(), wire stubbed", cr.fetchone)
    cr._obj = wire
    cr.close()

    for label, q in (
        ("classify_statement SELECT", "SELECT id FROM t"),
        ("classify_statement UPDATE", "UPDATE t SET a = 1"),
        ("classify_statement CREATE", "CREATE TABLE t (a int)"),
        ("classify_statement comment-led", "-- c\nSELECT 1"),
    ):
        _ns(label, lambda q=q: classify_statement(q))

    raw = psycopg.connect(f"dbname={db_name}")
    _us(
        "_reset_connection (pgconn.exec_)",
        lambda: _reset_connection(raw, discard=False),
    )
    _us("_probe_liveness (empty query)", lambda: _probe_liveness(raw))
    raw.autocommit = True
    _us(
        "bare reset string round trip",
        lambda: raw.pgconn.exec_(_RESET_SESSION_STATE_SQL.encode()),
    )
    _us("bare DISCARD ALL round trip", lambda: raw.pgconn.exec_(b"DISCARD ALL"))
    _us(
        "bare SELECT 1 round trip",
        lambda: raw.execute("SELECT 1", prepare=False).fetchone(),
    )
    raw.autocommit = False
    cur = raw.cursor()
    q = "SELECT id, name, active, company_id FROM res_partner WHERE id = ANY(%s)"
    for _ in range(20):
        cur.execute(q, ([1, 2, 3],))
        cur.fetchall()

    def prepared():
        cur.execute(q, ([1, 2, 3],))
        cur.fetchall()

    def unprepared():
        cur.execute(q, ([1, 2, 3],), prepare=False)
        cur.fetchall()

    _us("statement, auto-prepared (warm plan)", prepared)
    _us("statement, prepare=False (parse+plan)", unprepared)
    raw.rollback()
    raw.close()

    _, info = get_connection_info_for_database(db_name)
    pool = ConnectionPool(maxconn=64)

    def storm(threads: int, per: int) -> tuple[float, int]:
        def worker():
            for _ in range(per):
                c = Cursor(pool, db_name, info)
                c.execute("SELECT 1")
                c.fetchone()
                c.close()

        ts = [threading.Thread(target=worker) for _ in range(threads)]
        t0 = perf_counter()
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        return threads * per / (perf_counter() - t0), pool.get_stats()[db_name][
            "pool_size"
        ]

    for threads in (8, 16, 32):
        rate, backends = storm(threads, 300)
        _report(f"{threads:2d} threads x 300 cycles: cycles/s", rate, "1/s")
        _report(f"{threads:2d} threads x 300 cycles: backends held", backends, "")
    pool.close_all()


def _pure_paths() -> None:
    from odoo.db.budget import ConnectionBudget
    from odoo.db.dsn import _get_dsn_key, _get_key_dbname
    from odoo.db.probe import ReachabilityProbe
    from odoo.db.stats import PoolStats

    key = _get_dsn_key({"dbname": "x", "host": "h", "user": "u", "password": "p"})
    _ns("_get_dsn_key", lambda: _get_dsn_key({"dbname": "x", "host": "h", "user": "u"}))
    _ns("_get_key_dbname", lambda: _get_key_dbname(key))
    probe = ReachabilityProbe(PoolStats())
    probe.mark_proven(key)
    _ns("mark_proven (already proven)", lambda: probe.mark_proven(key))
    budget = ConnectionBudget(4)

    def permit():
        budget.acquire(1.0)
        budget.release()

    _ns("budget acquire + release", permit, number=100_000)
    stats = PoolStats()
    _ns(
        "stats.record_borrow",
        lambda: stats.record_borrow(time.monotonic()),
        number=100_000,
    )


def main(argv: list[str]) -> int:
    from odoo.tools import config

    config.parse_config(argv, setup_logging=True)
    import logging

    logging.getLogger().setLevel(logging.ERROR)
    db_name = (config["db_name"] or [None])[0]
    _pure_paths()
    if db_name:
        _cursor_paths(db_name)
    else:
        _report("(pass -d <db> for the cursor and pool rows)", 0.0, "")
    width = max(len(label) for label, _ in _ROWS)
    for label, value in _ROWS:
        print(f"{label:{width}s} {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
