from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

from odoo.libs.debug_log import DebugLog

if TYPE_CHECKING:
    from collections.abc import Iterator

    from ._base_server import CommonServer

_debug = DebugLog(__name__)

server: CommonServer | None = None

server_phoenix = False

preloading: set[str] = set()
"""Databases whose registry `preload_registries` is building right now.

A request for one of them would block on the registry lock until the
load ends; a readiness probe answers 503 while any is here."""


def get_server() -> CommonServer | None:
    return server


def is_ready() -> bool:
    return server is not None and not preloading


def set_server(value: CommonServer | None) -> None:
    global server  # noqa: PLW0603  the running server IS a process singleton

    _debug.lifecycle(
        "server.registered",
        flavor=getattr(value, "flavor", None),
        replaced=server is not None,
    )
    server = value


@contextmanager
def preloading_database(db_name: str) -> Iterator[None]:
    preloading.add(db_name)
    _debug.lifecycle("server.preloading", db=db_name, pending=len(preloading))
    try:
        yield
    finally:
        preloading.discard(db_name)
        _debug.lifecycle("server.preloaded", db=db_name, pending=len(preloading))


def set_phoenix(value: bool) -> None:
    global server_phoenix  # noqa: PLW0603  one re-exec decision per process

    _debug.lifecycle("server.phoenix", value=value, was=server_phoenix)
    server_phoenix = value
