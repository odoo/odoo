from __future__ import annotations

import dataclasses
import threading
from typing import Any

from odoo.service._stream import RUNTIME

from .stream_protocol import StreamProtocol, StreamSnapshot


@dataclasses.dataclass(slots=True)
class OpenStream:
    protocol: StreamProtocol
    handle: Any
    snapshot: StreamSnapshot


_lock = threading.RLock()
_open: dict[tuple[str, int], OpenStream] = {}


def get(db_name: str, stream_id: int) -> OpenStream | None:
    with _lock:
        return _open.get((db_name, stream_id))


def hold(db_name: str, stream: OpenStream) -> None:
    key = (db_name, stream.snapshot.id)
    with _lock:
        _open[key] = stream

    def close() -> None:
        with _lock:
            _open.pop(key, None)
        stream.protocol.close(stream.handle)

    RUNTIME.hold(db_name, stream.snapshot.id, close)


def drop(db_name: str, stream_id: int) -> None:
    RUNTIME.drop(db_name, stream_id)
    with _lock:
        _open.pop((db_name, stream_id), None)


def held(db_name: str) -> set[int]:
    return RUNTIME.held(db_name)
