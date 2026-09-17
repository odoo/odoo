from __future__ import annotations

import os
import socket
from dataclasses import dataclass
from typing import Self

from odoo.libs.debug_log import DebugLog
from odoo.libs.settings import OptionSource, SettingsSlot

_debug = DebugLog(__name__)

__all__ = [
    "INHERIT_FROM_CRON",
    "SD_LISTEN_FDS_START",
    "ServerSettings",
    "adopt_activated_socket",
    "current",
    "installed",
    "override",
    "slot",
]

INHERIT_FROM_CRON = -1

SD_LISTEN_FDS_START = 3


def adopt_activated_socket(fileno: int) -> socket.socket:
    """Adopt a systemd socket-activation fd, rejecting non-TCP sockets.

    The server serves TCP: it reads ``getsockname()[:2]`` as (host, port) and
    sets ``TCP_NODELAY`` on every connection.  A unit configured with
    ``ListenStream=/path.sock`` hands over an ``AF_UNIX`` socket instead, which
    survives adoption but fails cryptically at the first accept (``TCP_NODELAY``
    raises ``OSError 95``, taking the accept loop or the worker down) after
    producing a garbage server identity.  Reject it here, where the cause is
    still nameable.
    """
    sock = socket.socket(fileno=fileno)
    if sock.family not in (socket.AF_INET, socket.AF_INET6):
        family = getattr(sock.family, "name", sock.family)
        # Release the wrapper without closing the fd (the process exits below,
        # which reclaims it); closing here would fight the fd's real owner.
        sock.detach()
        raise SystemExit(
            f"Socket activation passed a {family} socket on fd {fileno}; the "
            "server needs a TCP socket. Configure the unit with "
            "ListenStream=<port> (or <address>:<port>), not a filesystem path."
        )
    return sock


def _is_inherited(limit: int) -> bool:
    return limit <= INHERIT_FROM_CRON


def _get_first_owned_limit(*limits: int) -> int:
    return next((limit for limit in limits if not _is_inherited(limit)), limits[-1])


def _count_activated_sockets(config: OptionSource) -> int:
    # sd_listen_fds(3): the unit's sockets arrive as fds 3.. in the order
    # its [Socket] section lists them -- the HTTP port first, the websocket
    # port second when the unit has one -- and only for the pid named.
    listen_fds = os.getenv("LISTEN_FDS") or "0"
    count = (
        int(listen_fds)
        if config["http_enable"]
        and listen_fds.isdigit()
        and os.getenv("LISTEN_PID") == str(os.getpid())
        else 0
    )
    if _debug.logic.enabled and os.getenv("LISTEN_FDS"):
        _debug.logic(
            "settings.socket_activation",
            activated=count > 0,
            sockets=count,
            http_enable=bool(config["http_enable"]),
            listen_fds=listen_fds,
            pid_matches=os.getenv("LISTEN_PID") == str(os.getpid()),
        )
    return count


@dataclass(frozen=True, slots=True)
class ServerSettings:
    workers: int = 0
    http_enable: bool = True
    http_interface: str = "0.0.0.0"
    http_port: int = 8069
    gevent_port: int = 8072
    http_socket_activation: bool = False
    websocket_socket_activation: bool = False
    max_cron_threads: int = 2
    job_workers: int = 1
    limit_request: int = 2**16
    limit_time_real: int = 120
    limit_time_real_cron: int = INHERIT_FROM_CRON
    limit_time_real_job: int = INHERIT_FROM_CRON
    limit_time_cpu: int = 60
    limit_time_worker_cron: int = 0
    limit_time_worker_job: int = INHERIT_FROM_CRON
    limit_memory_soft: int = 2048 * 1024 * 1024
    limit_memory_soft_gevent: int = 0
    dev_mode: tuple[str, ...] = ()
    test_enable: bool = False
    test_tags: str = ""
    db_name: tuple[str, ...] = ()
    dbfilter: str = ""
    data_dir: str = ""
    server_wide_modules: tuple[str, ...] = ()
    init: tuple[str, ...] = ()
    update: tuple[str, ...] = ()
    reinit: tuple[str, ...] = ()
    db_maxconn: int = 64
    db_maxconn_gevent: int = 0
    db_port: int | None = None
    registry_idle_timeout: int = 0

    @classmethod
    def from_config(cls, config: OptionSource) -> Self:
        activated_sockets = _count_activated_sockets(config)
        return cls(
            workers=int(config["workers"] or 0),
            http_enable=bool(config["http_enable"]),
            http_interface=config["http_interface"] or "0.0.0.0",
            http_port=int(config["http_port"]),
            gevent_port=int(config["gevent_port"]),
            http_socket_activation=activated_sockets >= 1,
            websocket_socket_activation=activated_sockets >= 2,
            max_cron_threads=int(config["max_cron_threads"] or 0),
            job_workers=int(config["job_workers"] or 0),
            limit_request=int(config["limit_request"] or 0),
            limit_time_real=int(config["limit_time_real"]),
            limit_time_real_cron=int(config["limit_time_real_cron"]),
            limit_time_real_job=int(config["limit_time_real_job"]),
            limit_time_cpu=int(config["limit_time_cpu"]),
            limit_time_worker_cron=int(config["limit_time_worker_cron"]),
            limit_time_worker_job=int(config["limit_time_worker_job"]),
            limit_memory_soft=int(config["limit_memory_soft"] or 0),
            limit_memory_soft_gevent=int(config["limit_memory_soft_gevent"] or 0),
            dev_mode=tuple(config["dev_mode"] or ()),
            test_enable=bool(config["test_enable"]),
            test_tags=str(config["test_tags"] or ""),
            db_name=tuple(config["db_name"] or ()),
            dbfilter=config["dbfilter"] or "",
            data_dir=str(config["data_dir"] or ""),
            server_wide_modules=tuple(config["server_wide_modules"] or ()),
            init=tuple(config["init"] or ()),
            update=tuple(config["update"] or ()),
            reinit=tuple(config["reinit"] or ()),
            db_maxconn=int(config["db_maxconn"]),
            db_maxconn_gevent=int(config["db_maxconn_gevent"] or 0),
            db_port=int(config["db_port"]) if config["db_port"] else None,
            registry_idle_timeout=int(config["registry_idle_timeout"] or 0),
        )

    @property
    def job_max_age(self) -> int:
        return _get_first_owned_limit(
            self.limit_time_worker_job, self.limit_time_worker_cron
        )

    @property
    def cron_real_time_budget(self) -> float:
        return max(
            _get_first_owned_limit(self.limit_time_real_cron, self.limit_time_real), 0
        )

    @property
    def job_real_time_budget(self) -> float:
        return max(
            _get_first_owned_limit(
                self.limit_time_real_job,
                self.limit_time_real_cron,
                self.limit_time_real,
            ),
            0,
        )

    def get_real_time_budget(self, kind: str) -> float:
        if kind == "job":
            return self.job_real_time_budget
        if kind == "cron":
            return self.cron_real_time_budget
        return max(self.limit_time_real, 0)

    @property
    def update_module(self) -> bool:
        return bool(self.init or self.update or self.reinit)


_last_seen: ServerSettings | None = None  # debuglog


def _get_settings_from_live_config() -> ServerSettings:
    global _last_seen  # debuglog

    import odoo.tools

    settings = ServerSettings.from_config(odoo.tools.config)
    # Derived once per config change; the event names the fields that moved.
    previous, _last_seen = _last_seen, settings  # debuglog
    if _debug.lifecycle.enabled and settings != previous:
        _debug.lifecycle(
            "settings.changed",
            first=previous is None,
            changed=sorted(
                name
                for name in ServerSettings.__dataclass_fields__
                if previous is None
                or getattr(previous, name) != getattr(settings, name)
            ),
            workers=settings.workers,
            http_port=settings.http_port,
            max_cron_threads=settings.max_cron_threads,
            job_workers=settings.job_workers,
            db_maxconn=settings.db_maxconn,
            test_enable=settings.test_enable,
        )
    return settings


def _get_live_inputs_version() -> object:
    import odoo.tools

    # Socket activation is read from the environment, not the option dict, so
    # the two variables that decide it are part of the key.
    return (
        odoo.tools.config.generation,
        os.getenv("LISTEN_FDS"),
        os.getenv("LISTEN_PID"),
    )


# Derived once per change of its inputs, not per read; a key written after
# boot still reaches the tier on the next read, and a test's override() or
# installed() still wins.
slot: SettingsSlot[ServerSettings] = SettingsSlot(
    "odoo.service",
    _get_settings_from_live_config,
    version=_get_live_inputs_version,
)
current = slot.current
installed = slot.installed
override = slot.override
