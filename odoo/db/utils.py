import logging
import os
import warnings
from urllib.parse import parse_qsl, urlsplit

import psycopg

from odoo.libs.debug_log import DebugLog

from .settings import PoolSettings, resolve

_ODOO_PGAPPNAME_WARNED = False
_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


SYSTEM_DBS = frozenset({"postgres", "template0", "template1"})


def is_maintenance_db(db_name: str, settings: PoolSettings | None = None) -> bool:
    if db_name in SYSTEM_DBS:
        return True
    template = resolve(settings).template
    return db_name == template


_HEALTH_PARAMS: dict[str, str] = {
    "connect_timeout": "10",
    "tcp_user_timeout": "30000",
    "keepalives": "1",
    "keepalives_idle": "60",
    "keepalives_interval": "10",
    "keepalives_count": "3",
}


def get_connection_info_for_database(
    db_or_uri: str, readonly: bool = False, settings: PoolSettings | None = None
) -> tuple[str, dict]:
    global _ODOO_PGAPPNAME_WARNED  # noqa: PLW0603  warn-once latch for the whole process
    settings = resolve(settings)
    app_name = settings.app_name
    if "ODOO_PGAPPNAME" in os.environ:
        _debug.logic("db.pgappname_deprecated", warned=_ODOO_PGAPPNAME_WARNED)
        if not _ODOO_PGAPPNAME_WARNED:
            warnings.warn(
                "Since 19.0, use PGAPPNAME instead of ODOO_PGAPPNAME",
                DeprecationWarning,
                stacklevel=2,
            )
            _ODOO_PGAPPNAME_WARNED = True
        app_name = os.environ["ODOO_PGAPPNAME"]
    app_name = app_name.replace("{pid}", str(os.getpid()))[:63]

    if db_or_uri.startswith(("postgresql://", "postgres://")):
        us = urlsplit(db_or_uri)
        if len(us.path) > 1:
            db_name = us.path[1:]
        elif us.username:
            db_name = us.username
        else:
            warnings.warn(
                f"PostgreSQL URI {db_or_uri!r} has no database path and no "
                f"username; using hostname {us.hostname!r} as the database "
                f"name label.  This is likely a misconfiguration.",
                RuntimeWarning,
                stacklevel=2,
            )
            db_name = us.hostname or ""
        uri_keys = {k for k, _ in parse_qsl(us.query)}
        merged = {k: v for k, v in _HEALTH_PARAMS.items() if k not in uri_keys}
        info = {"dsn": db_or_uri, **merged}
        if "application_name" not in uri_keys:
            info["application_name"] = app_name
        _debug.logic(
            "db.connection_info_from_uri",
            db=db_name,
            uri_keys=len(uri_keys),
            health_params_added=len(merged),
        )
        return db_name, info

    connection_info = {"dbname": db_or_uri, "application_name": app_name}
    connection_info.update(settings.connection_keywords(readonly))

    connection_info.update(_HEALTH_PARAMS)
    _debug.logic(
        "db.connection_info",
        db=db_or_uri,
        readonly=readonly,
        app_name=app_name,
        keys=len(connection_info),
    )
    return db_or_uri, connection_info


_SEED_PLANNER_STATS_SQL = """
    SELECT count(*)
      FROM (
        SELECT pg_restore_relation_stats(
                   'schemaname', n.nspname::text,
                   'relname', c.relname::text,
                   'relpages', %s::integer,
                   'reltuples', %s::real
               ) AS ok
          FROM pg_class c
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE c.relkind = 'r'
           AND n.nspname = 'public'
           AND c.reltuples <= 0
           AND c.relowner = quote_ident(current_user)::regrole
      ) AS seeded
     WHERE seeded.ok
"""

PLANNER_STATS_LOCK_TIMEOUT = 2.0


# The seed is an optimisation for the planner, and pg_restore_relation_stats
# locks every relation it touches: behind another session's ALTER TABLE (or a
# test cursor's open transaction) the caller waited without bound -- measured,
# still blocked after 8 s with the lock held. A LockNotAvailable inside the
# savepoint rolls the timeout back with the statement; the success path puts
# the previous value back by hand, because a released savepoint keeps its
# SET LOCAL for the rest of the transaction.
def update_planner_stats(
    cr,
    *,
    reltuples: float = 1000.0,
    relpages: int = 100,
    lock_timeout: float = PLANNER_STATS_LOCK_TIMEOUT,
) -> int:
    with _debug.perf(
        "db.planner_stats_seeded", cr=cr, reltuples=reltuples, relpages=relpages
    ) as span:
        cr.execute("SELECT current_setting('lock_timeout')")
        previous: str = cr.fetchone()[0]
        try:
            with cr.savepoint(flush=False):
                cr.execute(
                    "SET LOCAL lock_timeout = %s", (f"{int(lock_timeout * 1000)}ms",)
                )
                cr.execute(
                    _SEED_PLANNER_STATS_SQL, (relpages, reltuples), log_exceptions=False
                )
                seeded: int = cr.fetchone()[0]
                cr.execute("SET LOCAL lock_timeout = %s", (previous,))
        except psycopg.errors.LockNotAvailable:
            _debug.logic(
                "db.planner_stats_skipped", reason="lock_timeout", timeout=lock_timeout
            )
            _logger.warning(
                "Planner statistics not seeded: a relation stayed locked by "
                "another session for %.1fs; the planner keeps its defaults until "
                "ANALYZE runs",
                lock_timeout,
            )
            return 0
        span.set(tables=seeded)
    return seeded
