from __future__ import annotations

import dataclasses
import logging
from collections.abc import Callable, Mapping
from typing import Any, ClassVar

_logger = logging.getLogger(__name__)

STREAM_PROTOCOLS: dict[str, type[StreamProtocol]] = {}

OnFrame = Callable[[bytes, Mapping[str, Any]], None]
OnState = Callable[[str, str], None]


@dataclasses.dataclass(frozen=True, slots=True)
class StreamSnapshot:
    id: int
    db_name: str
    name: str
    protocol: str
    url: str
    secret: str | None
    login: str | None
    subscriptions: Mapping[str, Any]
    heartbeat_seconds: int
    options: Mapping[str, Any]
    addresses: tuple[str, ...] = ()


class StreamProtocol:
    key: ClassVar[str] = ""
    label: ClassVar[str] = ""
    schemes: ClassVar[tuple[str, ...]] = ()

    def open(self, stream: StreamSnapshot, on_frame: OnFrame, on_state: OnState) -> Any:
        raise NotImplementedError

    def send(self, handle: Any, payload: bytes, meta: Mapping[str, Any]) -> None:
        raise NotImplementedError

    def alive(self, handle: Any) -> bool:
        return True

    def close(self, handle: Any) -> None:
        raise NotImplementedError


def register(protocol: type[StreamProtocol]) -> type[StreamProtocol]:
    if not protocol.key:
        raise ValueError(f"{protocol.__name__} declares no key")
    existing = STREAM_PROTOCOLS.get(protocol.key)
    if existing is not None and existing is not protocol:
        _logger.warning(
            "stream protocol %r: %s replaces %s", protocol.key, protocol, existing
        )
    STREAM_PROTOCOLS[protocol.key] = protocol
    return protocol


def get(key: str) -> StreamProtocol:
    try:
        return STREAM_PROTOCOLS[key]()
    except KeyError:
        raise LookupError(
            f"no stream protocol {key!r} is loaded; its module is not installed"
        ) from None
