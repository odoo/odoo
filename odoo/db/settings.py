from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Self

from odoo.libs.debug_log import DebugLog
from odoo.libs.settings import OptionSource, SettingsSlot

__all__ = [
    "PoolSettings",
    "current",
    "installed",
    "override",
    "provide",
    "resolve",
    "slot",
]

_debug = DebugLog(__name__)

REPLICA_OVERRIDABLE: tuple[tuple[str, str], ...] = (
    ("host", "replica_host"),
    ("port", "replica_port"),
    ("user", "replica_user"),
    ("password", "replica_password"),
    ("sslmode", "replica_sslmode"),
)


def _coerce_optional_int(value: object) -> int | None:
    if value is None or value == "" or value is False:
        return None
    return int(value)  # type: ignore[call-overload]


@dataclass(frozen=True, slots=True)
class PoolSettings:
    host: str | None = None
    port: int | None = None
    user: str | None = None
    password: str | None = None
    sslmode: str | None = "prefer"
    replica_host: str | None = None
    replica_port: int | None = None
    replica_user: str | None = None
    replica_password: str | None = None
    replica_sslmode: str | None = None
    app_name: str = "odoo-{pid}"
    template: str = "template0"
    db_names: tuple[str, ...] = ()
    maxconn: int = 64
    maxconn_replica: int = 0
    minconn: int = 0
    borrow_timeout: float = 30.0
    conn_max_lifetime: int = 3600
    conn_max_idle: int = 600
    pool_reap_idle: float = 300.0
    pool_workers: int = 1
    discard_on_return: bool = False
    healthcheck_grace: float = 1.0
    leak_detection: float = 0.0
    idle_in_transaction_timeout: float = 0.0
    replica_write_pin: float = 2.0
    replica_max_lag: float = 0.0
    session_gucs: str = "jit=off,work_mem=16MB"
    readonly_cursors: bool = False

    @classmethod
    def from_config(cls, config: OptionSource, *, evented: bool = False) -> Self:
        replica_host = config["db_replica_host"] or None
        _debug.lifecycle(
            "settings.built",
            evented=evented,
            maxconn=config["db_maxconn"],
            maxconn_gevent=config["db_maxconn_gevent"],
            maxconn_replica=config["db_maxconn_replica"],
            replica=replica_host is not None,
            test_enable=bool(config["test_enable"]),
            session_gucs=config["db_session_gucs"],
            leak_detection=config["db_leak_detection"],
        )
        return cls(
            host=config["db_host"] or None,
            port=_coerce_optional_int(config["db_port"]),
            user=config["db_user"] or None,
            password=config["db_password"] or None,
            sslmode=config["db_sslmode"] or None,
            replica_host=replica_host,
            replica_port=_coerce_optional_int(config["db_replica_port"]),
            replica_user=config["db_replica_user"] or None,
            replica_password=config["db_replica_password"] or None,
            replica_sslmode=config["db_replica_sslmode"] or None,
            app_name=config["db_app_name"] or "",
            template=config["db_template"] or "",
            db_names=tuple(config["db_name"] or ()),
            maxconn=int(
                (config["db_maxconn_gevent"] if evented else 0) or config["db_maxconn"]
            ),
            maxconn_replica=int(config["db_maxconn_replica"] or 0),
            minconn=int(config["db_minconn"] or 0),
            borrow_timeout=float(config["db_borrow_timeout"]),
            conn_max_lifetime=int(config["db_conn_max_lifetime"]),
            conn_max_idle=int(config["db_conn_max_idle"]),
            pool_reap_idle=float(config["db_pool_reap_idle"]),
            pool_workers=int(config["db_pool_workers"] or 1),
            discard_on_return=bool(config["db_discard_on_return"]),
            healthcheck_grace=float(config["db_healthcheck_grace"] or 0.0),
            leak_detection=float(config["db_leak_detection"] or 0.0),
            idle_in_transaction_timeout=float(
                config["db_idle_in_transaction_timeout"] or 0.0
            ),
            replica_write_pin=float(config["db_replica_write_pin"] or 0.0),
            replica_max_lag=float(config["db_replica_max_lag"] or 0.0),
            session_gucs=config["db_session_gucs"] or "",
            readonly_cursors=bool(
                replica_host
                or config["test_enable"]
                or "replica" in (config["dev_mode"] or ())
            ),
        )

    def connection_keywords(self, readonly: bool = False) -> dict[str, Any]:
        keywords: dict[str, Any] = {}
        overrides = 0  # debuglog
        for name, replica_name in REPLICA_OVERRIDABLE:
            value = getattr(self, name)
            if readonly:
                replica_value = getattr(self, replica_name)
                overrides += bool(replica_value)  # debuglog
                value = replica_value or value
            if value:
                keywords[name] = value
        _debug.logic(
            "settings.connection_keywords",
            readonly=readonly,
            keywords=len(keywords),
            replica_overrides=overrides,
            host=keywords.get("host"),
        )
        return keywords


slot: SettingsSlot[PoolSettings] = SettingsSlot("odoo.db")
provide = slot.provide
current = slot.current
installed = slot.installed
override = slot.override


def resolve(settings: PoolSettings | None) -> PoolSettings:
    return settings if settings is not None else current()
