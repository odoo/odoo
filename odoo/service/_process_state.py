from __future__ import annotations

from typing import TYPE_CHECKING

from odoo.libs.debug_log import DebugLog

if TYPE_CHECKING:
    from ._base_server import CommonServer

_debug = DebugLog(__name__)

server: CommonServer | None = None

server_phoenix = False


def get_server() -> CommonServer | None:
    return server


def set_server(value: CommonServer | None) -> None:
    global server  # noqa: PLW0603  the running server IS a process singleton

    _debug.lifecycle(
        "server.registered",
        flavor=getattr(value, "flavor", None),
        replaced=server is not None,
    )
    server = value


def set_phoenix(value: bool) -> None:
    global server_phoenix  # noqa: PLW0603  one re-exec decision per process

    _debug.lifecycle("server.phoenix", value=value, was=server_phoenix)
    server_phoenix = value
