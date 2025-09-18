"""
Database connectivity layer for Odoo.

This package provides the PostgreSQL connectivity layer including:
- Connection pooling (ConnectionPool, Connection)
- Cursor management (BaseCursor, Cursor, Savepoint)
- Utility functions (connection_info_for, categorize_query)

Usage:
    from odoo.db import db_connect, close_db, close_all

    # Get a connection
    conn = db_connect('mydb')

    # Create a cursor for transactions
    with conn.cursor() as cr:
        cr.execute("SELECT * FROM res_users")
        rows = cr.fetchall()
"""

import logging
import threading

import odoo
from odoo import tools

from .cursor import BaseCursor, Cursor, Savepoint
from .pool import Connection, ConnectionPool, PoolError
from .utils import categorize_query, connection_info_for

__all__ = [
    # Cursor classes
    "BaseCursor",
    # Connection classes
    "Connection",
    "ConnectionPool",
    "Cursor",
    "PoolError",
    "Savepoint",
    # Utility functions
    "categorize_query",
    "close_all",
    "close_db",
    "connection_info_for",
    # Connection management
    "db_connect",
    "drain_all",
    # Global counter
    "sql_counter",
]

_logger = logging.getLogger(__name__)

# Connection pools (lazily initialized, protected by _pool_lock)
_Pool: ConnectionPool | None = None
_Pool_readonly: ConnectionPool | None = None
_pool_lock = threading.Lock()


def db_connect(to: str, allow_uri: bool = False, readonly: bool = False) -> Connection:
    """Connect to a PostgreSQL database.

    Returns a Connection object that can be used to create cursors.

    :param to: Database name or PostgreSQL URI
    :param allow_uri: If True, allows PostgreSQL URI connections
    :param readonly: If True, use the read-only replica pool
    :return: Connection object
    :raises ValueError: If URI provided but allow_uri is False
    """
    global _Pool, _Pool_readonly  # noqa: PLW0603

    # NB: hasattr(odoo, "evented") is the standard pattern for detecting
    # gevent mode — set once at startup, never changes.  Config is also
    # immutable post-startup, so no lock is needed around maxconn reads.
    maxconn = (
        tools.config["db_maxconn_gevent"]
        if hasattr(odoo, "evented") and odoo.evented
        else 0
    ) or tools.config["db_maxconn"]

    if readonly:
        if _Pool_readonly is None:
            with _pool_lock:
                if _Pool_readonly is None:
                    _Pool_readonly = ConnectionPool(int(maxconn), readonly=True)
        pool = _Pool_readonly
    else:
        if _Pool is None:
            with _pool_lock:
                if _Pool is None:
                    _Pool = ConnectionPool(int(maxconn), readonly=False)
        pool = _Pool

    db, info = connection_info_for(to, readonly)
    if not allow_uri and db != to:
        raise ValueError("URI connections not allowed")
    return Connection(pool, db, info)


def close_db(db_name: str) -> None:
    """Close all connections to a specific database.

    You might want to call odoo.modules.registry.Registry.delete(db_name)
    along with this function.

    :param db_name: Name of the database to close connections for
    """
    if _Pool:
        _Pool.close_all(connection_info_for(db_name)[1])
    if _Pool_readonly:
        _Pool_readonly.close_all(connection_info_for(db_name, readonly=True)[1])


def close_all() -> None:
    """Close all database connections in all pools."""
    if _Pool:
        _Pool.close_all()
    if _Pool_readonly:
        _Pool_readonly.close_all()


def drain_all() -> None:
    """Drain all pools — replace idle connections with fresh ones.

    Call after module upgrades to discard connections with stale
    prepared statement caches from before the schema change.
    Also clears the column type cache used by binary COPY, since
    schema changes (e.g. ALTER COLUMN TYPE) make cached types stale.
    """
    from .cursor import _column_type_cache, _id_sequence_cache

    _column_type_cache.clear()
    _id_sequence_cache.clear()
    if _Pool:
        _Pool.drain()
    if _Pool_readonly:
        _Pool_readonly.drain()


# Dynamic attribute access for mutable globals like sql_counter.
# This ensures db.sql_counter always returns the current value
# from the cursor module, not a stale copy from import time.
# Cost: ~100ns per access (string compare + cached module lookup).
# Called ~1/request for metrics — negligible vs query time.
def __getattr__(name):
    if name == "sql_counter":
        from . import cursor

        return cursor.sql_counter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
