import base64
import hashlib
import json
import os
import socket
import ssl
import struct
from contextlib import suppress
from urllib.parse import urlencode, urlparse

import gevent
import requests
from gevent import event as gevent_event
from gevent import socket as gevent_socket

from odoo import http
from odoo.addons.bus.websocket import CloseCode, Websocket, WebsocketConnectionHandler
from odoo.http import Response, request


class ReverseWebsocketClient:
    _GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

    def __init__(self, url):
        self._parsed = urlparse(url)
        self._socket = None
        self._buffer = bytearray()
        self._closed = False
        self._close_sent = False

    def connect(self):
        if self._parsed.scheme not in {"ws", "wss"}:
            raise ValueError(f"Unsupported websocket scheme: {self._parsed.scheme}")

        port = self._parsed.port or (443 if self._parsed.scheme == "wss" else 80)
        raw_socket = gevent_socket.create_connection((self._parsed.hostname, port), timeout=10)
        if self._parsed.scheme == "wss":
            raw_socket = ssl.create_default_context().wrap_socket(
                raw_socket,
                server_hostname=self._parsed.hostname,
            )

        path = self._parsed.path or "/"
        if self._parsed.query:
            path = f"{path}?{self._parsed.query}"

        websocket_key = base64.b64encode(os.urandom(16)).decode("ascii")
        host_header = self._parsed.hostname or "localhost"
        if self._parsed.port:
            host_header = f"{host_header}:{self._parsed.port}"

        handshake = "\r\n".join(
            [
                f"GET {path} HTTP/1.1",
                f"Host: {host_header}",
                "Upgrade: websocket",
                "Connection: Upgrade",
                f"Sec-WebSocket-Key: {websocket_key}",
                "Sec-WebSocket-Version: 13",
                "\r\n",
            ]
        ).encode("ascii")
        raw_socket.sendall(handshake)

        status_line, headers = self._read_http_headers(raw_socket)
        if "101" not in status_line:
            raise RuntimeError(f"Forge engine terminal rejected websocket upgrade: {status_line}")

        expected_accept = base64.b64encode(
            hashlib.sha1(f"{websocket_key}{self._GUID}".encode("ascii")).digest()
        ).decode("ascii")
        actual_accept = headers.get("sec-websocket-accept")
        if actual_accept != expected_accept:
            raise RuntimeError("Forge engine terminal returned an invalid websocket handshake")

        self._socket = raw_socket

    def send(self, message):
        if self._closed or self._socket is None:
            raise RuntimeError("Upstream websocket is closed")
        if isinstance(message, str):
            opcode = 0x1
            payload = message.encode("utf-8")
        else:
            opcode = 0x2
            payload = bytes(message)
        self._send_frame(opcode, payload)

    def recv(self):
        while not self._closed:
            opcode, payload, fin = self._recv_frame()
            if opcode == 0x8:
                self.close()
                return None
            if opcode == 0x9:
                self._send_frame(0xA, payload)
                continue
            if opcode == 0xA:
                continue
            if opcode not in {0x1, 0x2, 0x0}:
                continue

            message_opcode = opcode
            fragments = [payload]
            while not fin:
                continuation_opcode, continuation_payload, fin = self._recv_frame()
                if continuation_opcode == 0x9:
                    self._send_frame(0xA, continuation_payload)
                    continue
                if continuation_opcode == 0xA:
                    continue
                if continuation_opcode == 0x8:
                    self.close()
                    return None
                if continuation_opcode != 0x0:
                    raise RuntimeError("Invalid fragmented websocket message received from forge engine")
                fragments.append(continuation_payload)

            message = b"".join(fragments)
            if message_opcode == 0x1:
                return message.decode("utf-8", errors="replace")
            return message
        return None

    def close(self):
        if self._closed:
            return
        self._closed = True
        with suppress(Exception):
            if self._socket is not None and not self._close_sent:
                self._send_frame(0x8, b"")
        with suppress(Exception):
            if self._socket is not None:
                self._socket.close()
        self._socket = None

    def _read_http_headers(self, raw_socket):
        while b"\r\n\r\n" not in self._buffer:
            chunk = raw_socket.recv(4096)
            if not chunk:
                raise RuntimeError("Forge engine terminal closed before websocket handshake completed")
            self._buffer.extend(chunk)
        header_bytes, _, remaining = self._buffer.partition(b"\r\n\r\n")
        self._buffer = bytearray(remaining)
        header_lines = header_bytes.decode("utf-8").split("\r\n")
        status_line = header_lines[0]
        headers = {}
        for line in header_lines[1:]:
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            headers[key.strip().lower()] = value.strip()
        return status_line, headers

    def _recv_exact(self, size):
        while len(self._buffer) < size:
            chunk = self._socket.recv(4096)
            if not chunk:
                raise ConnectionError("Forge engine terminal websocket disconnected")
            self._buffer.extend(chunk)
        data = bytes(self._buffer[:size])
        del self._buffer[:size]
        return data

    def _recv_frame(self):
        first_byte, second_byte = self._recv_exact(2)
        fin = bool(first_byte & 0x80)
        opcode = first_byte & 0x0F
        masked = bool(second_byte & 0x80)
        payload_length = second_byte & 0x7F
        if payload_length == 126:
            payload_length = struct.unpack("!H", self._recv_exact(2))[0]
        elif payload_length == 127:
            payload_length = struct.unpack("!Q", self._recv_exact(8))[0]

        mask = self._recv_exact(4) if masked else b""
        payload = bytearray(self._recv_exact(payload_length))
        if masked:
            for index in range(payload_length):
                payload[index] ^= mask[index % 4]
        return opcode, bytes(payload), fin

    def _send_frame(self, opcode, payload):
        if self._socket is None:
            raise RuntimeError("Upstream websocket is not connected")

        first_byte = 0x80 | opcode
        payload_length = len(payload)
        header = bytearray([first_byte])
        if payload_length < 126:
            header.append(0x80 | payload_length)
        elif payload_length < (1 << 16):
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", payload_length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", payload_length))

        mask = os.urandom(4)
        header.extend(mask)
        masked_payload = bytearray(payload)
        for index in range(payload_length):
            masked_payload[index] ^= mask[index % 4]
        self._socket.sendall(bytes(header) + bytes(masked_payload))
        if opcode == 0x8:
            self._close_sent = True


class StudioController(http.Controller):
    def _get_engine_url(self):
        return request.env["ir.config_parameter"].sudo().get_param(
            "kodoo.forge.engine_url",
            "http://localhost:8765",
        )

    def _ensure_authenticated(self):
        if not request.session.uid:
            return request.make_json_response(
                {"error": "Authentication required"},
                status=401,
            )
        return None

    def _build_proxy_url(self, path=""):
        base_url = self._get_engine_url().rstrip("/")
        clean_path = path.lstrip("/")
        return f"{base_url}/{clean_path}" if clean_path else base_url

    def _get_terminal_secret(self):
        secret = os.environ.get("TERMINAL_SECRET")
        if secret:
            return secret
        secret = request.env["ir.config_parameter"].sudo().get_param("kodoo.forge.terminal_secret")
        if secret:
            return secret
        raise RuntimeError("TERMINAL_SECRET is not configured for Kodoo Studio")

    def _make_upstream_ws_url(self, token):
        engine_url = self._get_engine_url().rstrip("/")
        query = urlencode({"token": token})
        if engine_url.startswith("https://"):
            return f"wss://{engine_url.removeprefix('https://')}/ws/terminal?{query}"
        return f"ws://{engine_url.removeprefix('http://')}/ws/terminal?{query}"

    @http.route(
        ["/kodoo/studio/api", "/kodoo/studio/api/", "/kodoo/studio/api/<path:path>"],
        type="http",
        auth="public",
        methods=["GET", "POST"],
        csrf=False,
    )
    def studio_api(self, path="", **_kwargs):
        auth_error = self._ensure_authenticated()
        if auth_error:
            return auth_error

        target_url = self._build_proxy_url(path)
        query_string = request.httprequest.query_string.decode("utf-8")
        if query_string:
            target_url = f"{target_url}?{query_string}"

        body = request.httprequest.get_data()
        headers = {
            header: value
            for header, value in request.httprequest.headers.items()
            if header.lower() in {"accept", "content-type"}
        }
        if path.strip("/") == "terminal/token":
            headers["X-Forge-Internal"] = self._get_terminal_secret()
            headers["Content-Type"] = "application/json"
            payload = {}
            if body:
                with suppress(ValueError, TypeError):
                    payload = json.loads(body.decode("utf-8")) or {}
            if not isinstance(payload, dict):
                payload = {}
            payload["uid"] = request.session.uid
            body = json.dumps(payload).encode("utf-8")

        try:
            upstream_response = requests.request(
                method=request.httprequest.method,
                url=target_url,
                data=body or None,
                headers=headers,
                timeout=120,
            )
        except requests.RequestException as exc:
            return request.make_json_response(
                {"error": f"Could not reach forge engine: {exc}"},
                status=502,
            )

        response_headers = []
        content_type = upstream_response.headers.get("content-type")
        if content_type:
            response_headers.append(("Content-Type", content_type))
        return request.make_response(
            upstream_response.content,
            headers=response_headers,
            status=upstream_response.status_code,
        )

    @http.route(
        "/kodoo/studio/ws/terminal",
        type="http",
        auth="public",
        websocket=True,
    )
    def studio_terminal(self):
        if not request.session.uid:
            return Response("Unauthorized", status=401)

        terminal_token = request.httprequest.args.get("token") or request.params.get("token")
        if not terminal_token:
            return Response("Missing terminal token", status=400)

        try:
            response = WebsocketConnectionHandler._get_handshake_response(
                request.httprequest.headers
            )
            socket_handle = request.httprequest._HTTPRequest__environ["socket"]
        except KeyError as exc:
            raise RuntimeError("Kodoo Studio terminal requires the gevent websocket worker") from exc

        browser_ws = Websocket(socket_handle, request.session, request.httprequest.cookies)
        upstream_url = self._make_upstream_ws_url(terminal_token)
        response.call_on_close(lambda: self._bridge_terminal(browser_ws, upstream_url))
        request.session.is_dirty = True
        return response

    def _bridge_terminal(self, browser_ws, upstream_url):
        upstream_ws = ReverseWebsocketClient(upstream_url)
        stop_event = gevent_event.Event()

        try:
            upstream_ws.connect()
        except Exception as exc:
            with suppress(Exception):
                browser_ws._send(
                    {
                        "type": "error",
                        "message": f"Could not connect to forge terminal: {exc}",
                    }
                )
            with suppress(Exception):
                browser_ws.close(CloseCode.BAD_GATEWAY, "FORGE_ENGINE_UNAVAILABLE")
            return

        def browser_to_upstream():
            try:
                for message in browser_ws.get_messages():
                    if stop_event.is_set():
                        break
                    upstream_ws.send(message)
            except Exception:
                pass
            finally:
                stop_event.set()
                upstream_ws.close()

        def upstream_to_browser():
            try:
                while not stop_event.is_set():
                    message = upstream_ws.recv()
                    if message is None:
                        break
                    browser_ws._send(message)
            except (ConnectionError, OSError, socket.error):
                pass
            except Exception as exc:
                with suppress(Exception):
                    browser_ws._send(
                        {
                            "type": "error",
                            "message": f"Forge terminal bridge error: {exc}",
                        }
                    )
            finally:
                stop_event.set()
                with suppress(Exception):
                    browser_ws.close(CloseCode.GOING_AWAY, "TERMINAL_BRIDGE_CLOSED")

        greenlets = [
            gevent.spawn(browser_to_upstream),
            gevent.spawn(upstream_to_browser),
        ]
        gevent.joinall(greenlets, raise_error=False)
        for greenlet in greenlets:
            greenlet.kill()
        upstream_ws.close()
