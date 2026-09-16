from __future__ import annotations

import logging
import math
import os
import socket
from collections.abc import Callable, MutableMapping

IS_POSIX = os.name == "posix"
IS_WINDOWS = os.name == "nt"


def get_env_float(
    name: str,
    default: float,
    *,
    minimum: float | None = None,
    logger: logging.Logger | None = None,
) -> float:
    return _parse(name, default, float, "a number", minimum, logger)


def get_env_int(
    name: str,
    default: int,
    *,
    minimum: int | None = None,
    logger: logging.Logger | None = None,
) -> int:
    return _parse(name, default, int, "an integer", minimum, logger)


def get_env_str(name: str, default: str = "") -> str:
    return (os.environ.get(name) or "").strip() or default


def _parse[T: (int, float)](
    name: str,
    default: T,
    conv: Callable[[str], T],
    label: str,
    minimum: T | None,
    logger: logging.Logger | None,
) -> T:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = conv(raw)
    except TypeError, ValueError:
        if logger is not None:
            logger.warning(
                "%s=%r is not %s; using default %s", name, raw, label, default
            )
        return default
    if conv is float and not math.isfinite(value):
        if logger is not None:
            logger.warning("%s=%r is not finite; using default %s", name, raw, default)
        return default
    if minimum is not None and value < minimum:
        if logger is not None:
            logger.warning(
                "%s=%s is below the minimum of %s; clamping to %s",
                name,
                value,
                minimum,
                minimum,
            )
        return minimum
    return value


INHERITED_SOCKET_FD = "ODOO_HTTP_SOCKET_FD"
"""The listening socket a server hands to the process that replaces it.

The prefork master passes it to its reload candidate; a threaded server
leaves it open across its own re-exec.  Either way the port is never
unbound, and the connections that arrive meanwhile wait in the kernel's
backlog instead of being refused."""


def take_inherited_socket() -> socket.socket | None:
    fd = os.environ.pop(INHERITED_SOCKET_FD, None)
    if not fd:
        return None
    sock = socket.socket(fileno=int(fd))
    os.set_inheritable(sock.fileno(), False)
    return sock


def bequeath_socket(sock: socket.socket, env: MutableMapping[str, str]) -> int:
    fd = sock.detach()
    os.set_inheritable(fd, True)
    env[INHERITED_SOCKET_FD] = str(fd)
    return fd


__all__ = (
    "INHERITED_SOCKET_FD",
    "bequeath_socket",
    "get_env_float",
    "get_env_int",
    "get_env_str",
    "take_inherited_socket",
)
