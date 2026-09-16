import atexit

from odoo.libs.debug_log import DebugLog

from . import metrics as _metrics
from . import settings as pool_settings
from .budget import ConnectionBudget
from .cursor import BaseCursor, Connection, Cursor, Savepoint
from .endpoints import EndpointRegistry, get_endpoint_key
from .metrics import classify_query
from .pool import ConnectionPool, PoolError
from .replica import get_replica_health
from .savepoint import get_or_create_row
from .settings import PoolSettings
from .schema import FunctionStatus, get_unaccent_status, has_trigram
from .utils import SYSTEM_DBS, get_connection_info_for_database, is_maintenance_db

__all__ = [
    "SYSTEM_DBS",
    "BaseCursor",
    "Connection",
    "ConnectionBudget",
    "ConnectionPool",
    "Cursor",
    "EndpointRegistry",
    "FunctionStatus",
    "PoolError",
    "PoolSettings",
    "Savepoint",
    "cancel_queries_of",
    "classify_query",
    "close_all",
    "close_db",
    "db_connect",
    "drain_all",
    "drain_db",
    "get_connection_info_for_database",
    "get_or_create_row",
    "get_pool_health",
    "get_replica_health",
    "get_unaccent_status",
    "has_trigram",
    "is_maintenance_db",
    "is_pooled",
    "sql_counter",  # noqa: F822  served by the module-level __getattr__ below
]

_debug = DebugLog(__name__)

registry = EndpointRegistry()


def db_connect(to: str, allow_uri: bool = False, readonly: bool = False) -> Connection:
    settings = pool_settings.current()
    db, info = get_connection_info_for_database(to, readonly, settings)
    if not allow_uri and db != to:
        msg = "URI connections not allowed"
        raise ValueError(msg)
    _debug.logic("db.connect", db=db, readonly=readonly, uri=db != to)
    return Connection(
        registry.get_pool_at_endpoint(
            get_endpoint_key(info, settings), readonly, settings
        ),
        db,
        info,
    )


def is_pooled(db_name: str) -> bool:
    return registry.is_pooled(db_name)


def get_pool_health() -> dict:
    return registry.get_health()


def close_db(db_name: str) -> None:
    with _debug.perf("db.close_db", db=db_name):
        registry.close_db(db_name)


def close_all() -> None:
    with _debug.perf("db.close_all"):
        registry.close_all()


def drain_db(db_name: str) -> None:
    with _debug.perf("db.drain_db", db=db_name):
        registry.drain_db(db_name)


def drain_all() -> None:
    with _debug.perf("db.drain_all"):
        registry.drain_all()


def cancel_queries_of(thread_name: str) -> int:
    with _debug.perf("db.cancel_queries_of", thread=thread_name):
        return registry.cancel_queries_of(thread_name)


atexit.register(close_all)


def __getattr__(name: str) -> int:
    if name == "sql_counter":
        return _metrics.sql_counter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
