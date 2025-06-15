from __future__ import annotations

import sys

PLATFORM_WINDOWS = "windows"
PLATFORM_LINUX = "linux"
PLATFORM_BSD = "bsd"
PLATFORM_DARWIN = "darwin"
PLATFORM_UNKNOWN = "unknown"


def get_platform_name() -> str:
    if sys.platform.startswith("win"):
        return PLATFORM_WINDOWS

    if sys.platform.startswith("darwin"):
        return PLATFORM_DARWIN

    if sys.platform.startswith("linux"):
        return PLATFORM_LINUX

    if sys.platform.startswith(("dragonfly", "freebsd", "netbsd", "openbsd", "bsd")):
        return PLATFORM_BSD

    return PLATFORM_UNKNOWN


__platform__ = get_platform_name()


def is_linux() -> bool:
    return __platform__ == PLATFORM_LINUX


def is_bsd() -> bool:
    return __platform__ == PLATFORM_BSD


def is_darwin() -> bool:
    return __platform__ == PLATFORM_DARWIN


def is_windows() -> bool:
    return __platform__ == PLATFORM_WINDOWS
