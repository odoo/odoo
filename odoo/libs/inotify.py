from __future__ import annotations

import ctypes
import ctypes.util
import errno
import os
import select
import struct
import sys
from pathlib import Path
from typing import NamedTuple, Self

__all__ = [
    "AVAILABLE",
    "IN_CLOSE_WRITE",
    "IN_CREATE",
    "IN_DELETE",
    "IN_ISDIR",
    "IN_MODIFY",
    "IN_MOVED_FROM",
    "IN_MOVED_TO",
    "IN_Q_OVERFLOW",
    "Event",
    "Inotify",
    "InotifyError",
    "QueueOverflow",
]

IN_MODIFY = 0x00000002
IN_CLOSE_WRITE = 0x00000008
IN_MOVED_FROM = 0x00000040
IN_MOVED_TO = 0x00000080
IN_CREATE = 0x00000100
IN_DELETE = 0x00000200
IN_Q_OVERFLOW = 0x00004000
IN_IGNORED = 0x00008000
IN_ISDIR = 0x40000000

_IN_CLOEXEC = os.O_CLOEXEC
_IN_NONBLOCK = os.O_NONBLOCK

_EVENT_HEADER = struct.Struct("iIII")
_READ_SIZE = 64 * 1024

AVAILABLE = sys.platform.startswith("linux")


class InotifyError(OSError):
    pass


class QueueOverflow(Exception):
    """The kernel dropped events: every watch has to be re-derived."""


class Event(NamedTuple):
    path: str
    name: str
    mask: int

    @property
    def full_path(self) -> str:
        return str(Path(self.path, self.name)) if self.name else self.path

    @property
    def is_dir(self) -> bool:
        return bool(self.mask & IN_ISDIR)

    @property
    def is_creation(self) -> bool:
        return bool(self.mask & (IN_CREATE | IN_MOVED_TO))

    @property
    def is_deletion(self) -> bool:
        return bool(self.mask & (IN_DELETE | IN_MOVED_FROM))


def _load_libc() -> ctypes.CDLL:
    name = ctypes.util.find_library("c") or "libc.so.6"
    libc = ctypes.CDLL(name, use_errno=True)
    libc.inotify_init1.argtypes = [ctypes.c_int]
    libc.inotify_init1.restype = ctypes.c_int
    libc.inotify_add_watch.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32]
    libc.inotify_add_watch.restype = ctypes.c_int
    libc.inotify_rm_watch.argtypes = [ctypes.c_int, ctypes.c_int]
    libc.inotify_rm_watch.restype = ctypes.c_int
    return libc


_libc: ctypes.CDLL | None = None


def _get_libc() -> ctypes.CDLL:
    global _libc  # noqa: PLW0603  one handle on libc per process
    if _libc is None:
        _libc = _load_libc()
    return _libc


def _errno_error(what: str) -> InotifyError:
    code = ctypes.get_errno()
    return InotifyError(code, f"{what}: {os.strerror(code)}")


class Inotify:
    """One inotify instance: watches by path, events read in one non-blocking
    sweep per `read`, both descriptors close-on-exec from birth."""

    def __init__(self) -> None:
        if not AVAILABLE:
            raise InotifyError(errno.ENOSYS, "inotify is a Linux facility")
        libc = _get_libc()
        fd = libc.inotify_init1(_IN_CLOEXEC | _IN_NONBLOCK)
        if fd < 0:
            raise _errno_error("inotify_init1")
        self._fd = fd
        self._wd_by_path: dict[str, int] = {}
        self._path_by_wd: dict[int, str] = {}
        self._pending = b""
        self._epoll = select.epoll()
        try:
            self._epoll.register(fd, select.EPOLLIN)
        except BaseException:
            self.close()
            raise

    @property
    def closed(self) -> bool:
        return self._fd < 0

    @property
    def watched(self) -> frozenset[str]:
        return frozenset(self._wd_by_path)

    def fileno(self) -> int:
        return self._fd

    def descriptors(self) -> tuple[int, ...]:
        if self.closed:
            return ()
        return (self._fd, self._epoll.fileno())

    def add_watch(self, path: str | os.PathLike[str], mask: int) -> int:
        path = os.fspath(path)
        wd = _get_libc().inotify_add_watch(self._fd, os.fsencode(path), mask)
        if wd < 0:
            raise _errno_error(f"inotify_add_watch({path!r})")
        # The kernel hands the same descriptor back for a path already
        # watched, so a re-add is a no-op on both sides.
        self._wd_by_path[path] = wd
        self._path_by_wd[wd] = path
        return wd

    def remove_watch(self, path: str | os.PathLike[str]) -> bool:
        wd = self._wd_by_path.pop(os.fspath(path), None)
        if wd is None:
            return False
        self._path_by_wd.pop(wd, None)
        if _get_libc().inotify_rm_watch(self._fd, wd) < 0:
            code = ctypes.get_errno()
            # A watch the kernel dropped itself (the directory is gone) is
            # already removed; anything else is a real fault.
            if code != errno.EINVAL:
                raise InotifyError(code, f"inotify_rm_watch: {os.strerror(code)}")
        return True

    def read(self, timeout_s: float | None) -> list[Event]:
        """Wait up to `timeout_s` for activity, then drain every queued event.

        Raises `QueueOverflow` once the drained batch carried the kernel's
        overflow marker; the events read before it are lost with the rest.
        """
        if self.closed:
            raise InotifyError(errno.EBADF, "inotify instance is closed")
        try:
            ready = self._epoll.poll(timeout_s if timeout_s is not None else -1)
        except InterruptedError:
            ready = []
        if not ready:
            return []
        data = self._pending
        while True:
            try:
                chunk = os.read(self._fd, _READ_SIZE)
            except BlockingIOError:
                break
            if not chunk:
                break
            data += chunk
        events, self._pending, overflowed = self._parse(data)
        if overflowed:
            raise QueueOverflow
        return events

    def _parse(self, data: bytes) -> tuple[list[Event], bytes, bool]:
        events: list[Event] = []
        overflowed = False
        offset = 0
        size = _EVENT_HEADER.size
        while len(data) - offset >= size:
            wd, mask, _cookie, length = _EVENT_HEADER.unpack_from(data, offset)
            end = offset + size + length
            if end > len(data):
                break
            name = data[offset + size : end].split(b"\0", 1)[0]
            offset = end
            if mask & IN_Q_OVERFLOW:
                overflowed = True
                continue
            path = self._path_by_wd.get(wd)
            if mask & IN_IGNORED:
                if path is not None:
                    self._wd_by_path.pop(path, None)
                    self._path_by_wd.pop(wd, None)
                continue
            if path is None:
                continue
            events.append(Event(path, os.fsdecode(name), mask))
        return events, data[offset:], overflowed

    def close(self) -> None:
        fd, self._fd = self._fd, -1
        try:
            self._epoll.close()
        finally:
            if fd >= 0:
                os.close(fd)
        self._wd_by_path.clear()
        self._path_by_wd.clear()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def __del__(self) -> None:
        if getattr(self, "_fd", -1) >= 0:
            self.close()
