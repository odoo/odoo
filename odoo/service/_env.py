from __future__ import annotations

import logging
import math
import os
from collections.abc import Callable

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


__all__ = ("get_env_float", "get_env_int", "get_env_str")
