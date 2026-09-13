import os
import warnings
from urllib.parse import parse_qsl, urlsplit

from odoo.libs.debug_log import DebugLog

from .settings import PoolSettings, current

_ODOO_PGAPPNAME_WARNED = False
_debug = DebugLog(__name__)


SYSTEM_DBS = frozenset({"postgres", "template0", "template1"})


def is_maintenance_db(db_name: str, settings: PoolSettings | None = None) -> bool:
    if db_name in SYSTEM_DBS:
        return True
    template = (settings if settings is not None else current()).template
    return db_name == template


def iter_sql_code_ranges(query: str) -> list[tuple[int, int]]:
    ranges = []
    i, n = 0, len(query)
    start = 0
    while i < n:
        c = query[i]
        if c in ("'", '"'):
            if i > start:
                ranges.append((start, i))
            quote = c
            i += 1
            while i < n:
                if query[i] == quote:
                    if i + 1 < n and query[i + 1] == quote:
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            start = i
            continue
        if c == "-" and query[i : i + 2] == "--":
            if i > start:
                ranges.append((start, i))
            nl = query.find("\n", i)
            i = n if nl == -1 else nl
            start = i
            continue
        if c == "/" and query[i : i + 2] == "/*":
            if i > start:
                ranges.append((start, i))
            end_comment = query.find("*/", i + 2)
            i = n if end_comment == -1 else end_comment + 2
            start = i
            continue
        i += 1
    if start < n:
        ranges.append((start, n))
    return ranges


def get_value_marker_positions(query: str) -> list[int]:
    out = []
    for start, end in iter_sql_code_ranges(query):
        i = start
        while i < end - 1:
            if query[i] == "%":
                if query[i + 1] == "s":
                    out.append(i)
                i += 2
            else:
                i += 1
    return out


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
    settings = settings if settings is not None else current()
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


def update_planner_stats(cr, *, reltuples: float = 1000.0, relpages: int = 100) -> int:
    with _debug.perf(
        "db.planner_stats_seeded", cr=cr, reltuples=reltuples, relpages=relpages
    ) as span:
        cr.execute(
            """
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
            """,
            (relpages, reltuples),
        )
        seeded: int = cr.fetchone()[0]
        span.set(tables=seeded)
    return seeded
