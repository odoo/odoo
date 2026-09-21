from __future__ import annotations

import logging
import os
import socket
import sys

from odoo.libs.debug_log import DebugLog

from ._env import INHERITED_SOCKET_FD, take_inherited_socket
from .settings import SD_LISTEN_FDS_START, adopt_activated_socket

_logger = logging.getLogger("odoo.service.server")
_debug = DebugLog(__name__)

__all__ = ("acquire_listener",)


def acquire_listener(
    interface: str,
    port: int,
    *,
    backlog: int,
    what: str = "HTTP",
    inherited_fd: str = INHERITED_SOCKET_FD,
    activated: bool = False,
    activated_fd: int = SD_LISTEN_FDS_START,
    announce: bool = True,
    logger: logging.Logger = _logger,
) -> tuple[socket.socket, bool]:
    """The one way a server comes by a listening socket.

    Three sources, in the order a deployment offers them: the socket the
    server this one replaces handed over, the one a service manager
    activated, and a fresh bind.  Returns the socket and whether it already
    survives an execve -- the first two do, a fresh bind not until
    `bequeath_socket` marks it inheritable.

    Both flavours and both ports walk this, because they had walked it
    separately and had stopped agreeing: only the threaded server answered a
    taken port with a message instead of a traceback, only it made an
    inherited socket non-blocking where it was acquired, and only the prefork
    master kept an activated socket from leaking into its children.
    """
    if (inherited := take_inherited_socket(inherited_fd)) is not None:
        inherited.setblocking(False)
        if announce:
            logger.info(
                "%s service serving %s:%s on the listening socket inherited "
                "from the server this one replaced; the port was never closed",
                what,
                *inherited.getsockname()[:2],
            )
        _debug.lifecycle(
            "listener.acquired", what=what, source="inherited", fd=inherited.fileno()
        )
        return inherited, True

    if activated:
        sock = adopt_activated_socket(activated_fd)
        # The children get the listener they are meant to have, by fork or by
        # an explicit pass_fds; an activated one inherited by accident would
        # keep the port bound past the death of whoever was serving it.
        os.set_inheritable(sock.fileno(), False)
        sock.setblocking(False)
        if announce:
            logger.info("%s service running through socket activation", what)
        _debug.lifecycle(
            "listener.acquired", what=what, source="socket_activation", fd=activated_fd
        )
        return sock, True

    sock = _bind(interface, port, backlog, what)
    if announce:
        logger.info("%s service running on %s:%s", what, *sock.getsockname()[:2])
    return sock, False


def _bind(interface: str, port: int, backlog: int, what: str) -> socket.socket:
    family = socket.AF_INET6 if ":" in interface else socket.AF_INET
    sock = socket.socket(family, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((interface, port))
    except OSError as exc:
        sock.close()
        _debug.logic(
            "listener.bind_failed",
            what=what,
            interface=interface,
            port=port,
            errno=exc.errno,
            error=type(exc).__name__,
        )
        sys.stderr.write(
            f"{exc.strerror or exc}\nPort {port} is in use by another program. "
            "Either identify and stop that program, or start the server with a "
            "different port.\n"
        )
        raise SystemExit(1) from exc
    sock.listen(backlog)
    sock.setblocking(False)
    _debug.lifecycle(
        "listener.acquired",
        what=what,
        source="bind",
        family=family.name,
        interface=interface,
        port=sock.getsockname()[1],
        backlog=backlog,
    )
    return sock
