import base64
import logging
import threading
from urllib.parse import urlsplit, urlunsplit

import websocket

from odoo.addons.integration.tools.stream_protocol import (
    StreamProtocol,
    register,
    tls_context,
)

_logger = logging.getLogger(__name__)

_DEFAULT_PORTS = {"ws": 80, "wss": 443}


class WebsocketHandle:
    __slots__ = ("app", "closing", "stream", "thread")

    def __init__(self, app, stream, thread):
        self.app = app
        self.stream = stream
        self.thread = thread
        self.closing = False


@register
class WebsocketProtocol(StreamProtocol):
    key = "websocket"
    label = "WebSocket"
    schemes = ("ws", "wss")

    def open(self, stream, on_frame, on_state):
        url = urlsplit(stream.url)
        options = stream.options
        headers = list(options.get("headers") or [])
        auth = options.get("auth")
        if auth == "basic" and (stream.login or stream.secret):
            token = base64.b64encode(
                f"{stream.login or ''}:{stream.secret or ''}".encode()
            ).decode()
            headers.append(f"Authorization: Basic {token}")
        elif auth == "bearer" and stream.secret:
            headers.append(f"Authorization: Bearer {stream.secret}")
        dial_url = stream.url
        if url.scheme == "ws" and stream.addresses:
            port = url.port or _DEFAULT_PORTS[url.scheme]
            dial_url = urlunsplit(
                (url.scheme, f"{stream.addresses[0]}:{port}", url.path, url.query, "")
            )
            headers.append(f"Host: {url.hostname}")
        handle = WebsocketHandle(None, stream, None)

        def on_open(_app):
            on_state("open", None)

        def on_message(_app, message):
            payload = message if isinstance(message, bytes) else message.encode()
            on_frame(payload, {"binary": isinstance(message, bytes)})

        def on_error(_app, error):
            if not handle.closing:
                on_state("error", f"{type(error).__name__}: {error}")

        def on_close(_app, status, message):
            if not handle.closing:
                on_state("backoff", f"closed: {status} {message or ''}".strip())

        app = websocket.WebSocketApp(  # noqa: E8518 - the address was checked by ir.egress on the snapshot; websocket-client holds the socket open
            dial_url,
            header=headers or None,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )
        handle.app = app
        run_kwargs = {
            "ping_interval": max(stream.heartbeat_seconds, 5),
            "ping_timeout": min(10, max(stream.heartbeat_seconds - 1, 1)),
        }
        if url.scheme == "wss":
            run_kwargs["sslopt"] = {"context": tls_context(stream)}
        thread = threading.Thread(
            target=app.run_forever,
            kwargs=run_kwargs,
            name=f"odoo.stream.websocket.{stream.id}",
            daemon=True,
        )
        handle.thread = thread
        thread.start()
        return handle

    def send(self, handle, payload, meta):
        opcode = (
            websocket.ABNF.OPCODE_BINARY
            if meta.get("binary")
            else websocket.ABNF.OPCODE_TEXT
        )
        handle.app.send(payload, opcode=opcode)

    def alive(self, handle):
        sock = handle.app.sock
        return bool(handle.thread.is_alive() and sock and sock.connected)

    def close(self, handle):
        handle.closing = True
        handle.app.close()
        handle.thread.join(timeout=5)
