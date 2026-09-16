from __future__ import annotations

import threading

from odoo.libs.debug_log import DebugLog

from .budget import ConnectionBudget
from .dsn import _expand_conninfo
from .pool import ConnectionPool
from .settings import PoolSettings, resolve
from .utils import get_connection_info_for_database

DEFAULT_PG_PORT = 5432
_debug = DebugLog(__name__)


def _coerce_port(port: object) -> int:
    try:
        return int(port)  # type: ignore[call-overload]
    except TypeError, ValueError:
        return DEFAULT_PG_PORT


def get_endpoint_key(
    info: dict, settings: PoolSettings | None = None
) -> tuple[str | None, int]:
    if not info.get("dsn"):
        return (info.get("host") or None, _coerce_port(info.get("port")))
    settings = resolve(settings)
    expanded = _expand_conninfo(info)
    host = expanded.get("host") or settings.host or None
    port = expanded.get("port") or settings.port
    _debug.logic(
        "endpoints.key_from_uri",
        host=host,
        port=_coerce_port(port),
        host_from_uri="host" in expanded,
        port_from_uri="port" in expanded,
    )
    return (host, _coerce_port(port))


class EndpointRegistry:
    def __init__(self) -> None:
        self._pools: dict[tuple, ConnectionPool] = {}
        self._budgets: dict[tuple, ConnectionBudget] = {}
        self._lock = threading.RLock()

    def get_endpoint_for_readonly(
        self, readonly: bool, settings: PoolSettings | None = None
    ) -> tuple:
        settings = resolve(settings)
        _, info = get_connection_info_for_database("", readonly, settings)
        return get_endpoint_key(info, settings)

    def get_maxconn_at_endpoint(
        self, endpoint: tuple, settings: PoolSettings | None = None
    ) -> int:
        settings = resolve(settings)
        base = settings.maxconn
        primary = self.get_endpoint_for_readonly(False, settings)
        replica = self.get_endpoint_for_readonly(True, settings)
        if endpoint != primary and endpoint == replica:
            _debug.logic(
                "endpoints.replica_maxconn",
                endpoint=endpoint,
                maxconn=settings.maxconn_replica or base,
                own_ceiling=bool(settings.maxconn_replica),
            )
            return settings.maxconn_replica or base
        return base

    def get_budget_at_endpoint(
        self, endpoint: tuple, settings: PoolSettings | None = None
    ) -> ConnectionBudget:
        with self._lock:
            budget = self._budgets.get(endpoint)
            if budget is None:
                budget = self._budgets[endpoint] = ConnectionBudget(
                    self.get_maxconn_at_endpoint(endpoint, settings)
                )
                _debug.lifecycle(
                    "endpoints.budget_created",
                    endpoint=endpoint,
                    maxconn=budget.maxconn,
                    budgets=len(self._budgets),
                )
            return budget

    def get_budget_for_readonly(
        self, readonly: bool, settings: PoolSettings | None = None
    ) -> ConnectionBudget:
        settings = resolve(settings)
        return self.get_budget_at_endpoint(
            self.get_endpoint_for_readonly(readonly, settings), settings
        )

    def get_pool_at_endpoint(
        self, endpoint: tuple, readonly: bool, settings: PoolSettings | None = None
    ) -> ConnectionPool:
        key = (endpoint, readonly)
        pool = self._pools.get(key)
        if pool is not None:
            return pool
        settings = resolve(settings)
        with self._lock:
            pool = self._pools.get(key)
            if pool is None:
                budget = self.get_budget_at_endpoint(endpoint, settings)
                _debug.lifecycle(
                    "endpoints.pool_created",
                    endpoint=endpoint,
                    readonly=readonly,
                    maxconn=budget.maxconn,
                    pools=len(self._pools) + 1,
                )
                pool = self._pools[key] = ConnectionPool(
                    budget.maxconn, readonly=readonly, budget=budget, settings=settings
                )
            return pool

    def get_pool_for_readonly(
        self, readonly: bool, settings: PoolSettings | None = None
    ) -> ConnectionPool:
        settings = resolve(settings)
        return self.get_pool_at_endpoint(
            self.get_endpoint_for_readonly(readonly, settings), readonly, settings
        )

    def get_all_pools(self) -> list[ConnectionPool]:
        with self._lock:
            return list(self._pools.values())

    def is_pooled(self, db_name: str) -> bool:
        pools = self.get_all_pools()
        pooled = any(pool.has_database(db_name) for pool in pools)
        _debug.logic("endpoints.is_pooled", db=db_name, pooled=pooled, pools=len(pools))
        return pooled

    def get_health(self, settings: PoolSettings | None = None) -> dict:
        settings = resolve(settings)
        configured = {
            False: self.get_endpoint_for_readonly(False, settings),
            True: self.get_endpoint_for_readonly(True, settings),
        }
        health: dict = {"read_write": None, "read_only": None}
        with self._lock:
            items = list(self._pools.items())
        with _debug.perf("endpoints.health", pools=len(items)):
            for (endpoint, readonly), pool in items:
                mode = "read_only" if readonly else "read_write"
                if endpoint == configured[readonly]:
                    health[mode] = pool.get_health()
                else:
                    host, port = endpoint
                    health[f"uri:{host}:{port}:{mode}"] = pool.get_health()
        return health

    def close_db(self, db_name: str) -> None:
        pools = self.get_all_pools()
        _debug.lifecycle("endpoints.close_db", db=db_name, pools=len(pools))
        for pool in pools:
            pool.close_database(db_name)

    def close_all(self) -> None:
        pools = self.get_all_pools()
        _debug.lifecycle("endpoints.close_all", pools=len(pools))
        for pool in pools:
            pool.close_all()

    def drain_db(self, db_name: str) -> None:
        pools = self.get_all_pools()
        _debug.lifecycle("endpoints.drain_db", db=db_name, pools=len(pools))
        for pool in pools:
            pool.drain_database(db_name)

    def cancel_queries_of(self, thread_name: str) -> int:
        return sum(pool.cancel_queries_of(thread_name) for pool in self.get_all_pools())

    def drain_all(self) -> None:
        pools = self.get_all_pools()
        _debug.lifecycle("endpoints.drain_all", pools=len(pools))
        for pool in pools:
            pool.drain_all()
