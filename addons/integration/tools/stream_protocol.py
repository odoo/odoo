from __future__ import annotations

import dataclasses
import logging
import ssl
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, ClassVar

_logger = logging.getLogger(__name__)

STREAM_PROTOCOLS: dict[str, type[StreamProtocol]] = {}

OnFrame = Callable[[bytes, Mapping[str, Any]], None]
OnState = Callable[[str, str], None]


@dataclasses.dataclass(frozen=True, slots=True)
class TlsMaterial:
    certificate: str | None = None
    key: str | None = None
    ca: str | None = None


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
    tls: TlsMaterial | None = None


def tls_context(stream: StreamSnapshot) -> ssl.SSLContext:
    material = stream.tls or TlsMaterial()
    context = ssl.create_default_context(cadata=material.ca or None)
    if material.certificate and material.key:
        with tempfile.TemporaryDirectory(prefix="odoo-stream-tls-") as folder:
            certificate = Path(folder, "client.crt")
            key = Path(folder, "client.key")
            certificate.write_text(material.certificate, encoding="ascii")
            key.write_text(material.key, encoding="ascii")
            context.load_cert_chain(certificate, key)
    return context


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
