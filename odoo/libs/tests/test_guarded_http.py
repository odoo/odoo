import gzip
import http.server
import re
import socket
import threading
import time
from collections.abc import Callable

import pytest
import requests

from odoo.libs import guarded_http, netguard

LOOPBACK_ONLY = netguard.PUBLIC_ONLY.with_networks("127.0.0.0/8", "::1/128")


class _Server(http.server.ThreadingHTTPServer):
    seen: list[tuple[str, str | None]]


class _Handler(http.server.BaseHTTPRequestHandler):
    routes: dict[str, Callable[[_Handler], None]] = {}
    server: _Server

    def do_GET(self):
        self.server.seen.append((self.path, self.headers.get("Host")))
        self.routes[self.path](self)

    do_HEAD = do_GET

    def log_message(self, *args):
        pass


def _ok(handler):
    body = b"hello"
    handler.send_response(200)
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _redirect_to(location):
    def respond(handler):
        handler.send_response(302)
        handler.send_header("Location", location)
        handler.send_header("Content-Length", "0")
        handler.end_headers()

    return respond


def _large(handler):
    handler.send_response(200)
    handler.send_header("Content-Length", str(64 * 1024))
    handler.end_headers()
    handler.wfile.write(b"x" * 64 * 1024)


def _large_unannounced(handler):
    handler.send_response(200)
    handler.send_header("Connection", "close")
    handler.end_headers()
    handler.wfile.write(b"x" * 64 * 1024)
    handler.close_connection = True


def _gzip_bomb(handler):
    body = gzip.compress(b"\0" * 1024 * 1024)
    handler.send_response(200)
    handler.send_header("Content-Encoding", "gzip")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _dribble(handler):
    handler.send_response(200)
    handler.send_header("Content-Length", "40")
    handler.end_headers()
    for _ in range(40):
        handler.wfile.write(b"x")
        handler.wfile.flush()
        time.sleep(0.05)


_Handler.routes = {
    "/ok": _ok,
    "/to-private": _redirect_to("http://10.0.0.1/ok"),
    "/loop": _redirect_to("/loop"),
    "/large": _large,
    "/large-unannounced": _large_unannounced,
    "/bomb": _gzip_bomb,
    "/dribble": _dribble,
}


@pytest.fixture
def server():
    httpd = _Server(("127.0.0.1", 0), _Handler)
    httpd.seen = []
    thread = threading.Thread(target=httpd.serve_forever, args=(0.05,), daemon=True)
    thread.start()
    try:
        yield httpd
    finally:
        httpd.shutdown()
        httpd.server_close()


def resolver_for(mapping):
    def resolve(host, port, *args, **kwargs):
        if host not in mapping:
            raise socket.gaierror(socket.EAI_NONAME, "no such host")
        return [
            (
                socket.AF_INET6 if ":" in address else socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                (address, port),
            )
            for address in mapping[host]
        ]

    return resolve


def session_for(policy=LOOPBACK_ONLY, resolver=None, **kwargs):
    return guarded_http.guarded_session(
        policy,
        resolver=resolver or resolver_for({"service.test": ["127.0.0.1"]}),
        **kwargs,
    )


class TestDestination:
    def test_a_refused_destination_is_never_connected(self, server):
        resolver = resolver_for({"service.test": ["127.0.0.1"]})
        with pytest.raises(guarded_http.RefusedDestination) as caught:
            session_for(netguard.PUBLIC_ONLY, resolver).get(
                f"http://service.test:{server.server_port}/ok"
            )
        assert isinstance(caught.value, requests.RequestException)
        assert isinstance(caught.value, netguard.DestinationRefused)
        assert not caught.value.unresolvable
        assert server.seen == []

    def test_an_unresolvable_name_is_told_apart_from_a_refused_one(self):
        with pytest.raises(guarded_http.RefusedDestination) as caught:
            session_for(resolver=resolver_for({})).get("http://service.test/ok")
        assert caught.value.unresolvable

    def test_the_refusal_comes_before_anything_wrapping_session_send(
        self, server, monkeypatch
    ):
        def wrapped(*args, **kwargs):
            raise AssertionError("the wrapper ran before the check")

        monkeypatch.setattr(requests.Session, "send", wrapped)
        with pytest.raises(guarded_http.RefusedDestination):
            session_for(netguard.PUBLIC_ONLY).get(
                f"http://service.test:{server.server_port}/ok"
            )

    def test_the_connection_goes_to_the_checked_address_under_the_original_name(
        self, server
    ):
        response = session_for().get(f"http://service.test:{server.server_port}/ok")
        assert response.content == b"hello"
        assert server.seen == [("/ok", f"service.test:{server.server_port}")]

    def test_a_name_is_resolved_once_per_request(self, server):
        calls = []
        resolve = resolver_for({"service.test": ["127.0.0.1"]})

        def counting(*args, **kwargs):
            calls.append(args[0])
            return resolve(*args, **kwargs)

        session_for(resolver=counting).get(
            f"http://service.test:{server.server_port}/ok"
        )
        assert calls == ["service.test"]

    def test_an_address_that_refuses_the_connection_falls_through_to_the_next(
        self, server
    ):
        resolver = resolver_for({"service.test": ["127.0.0.3", "127.0.0.1"]})
        response = session_for(resolver=resolver).get(
            f"http://service.test:{server.server_port}/ok"
        )
        assert response.status_code == 200

    def test_the_pool_key_carries_the_name_for_tls(self):
        adapter = guarded_http.GuardedAdapter(LOOPBACK_ONLY)
        request = requests.Request("GET", "https://service.test/x").prepare()
        request.netguard_address = "127.0.0.1"
        pool = adapter.get_connection_with_tls_context(request, verify=True)
        assert pool.host == "127.0.0.1"
        assert pool.conn_kw.get("server_hostname") == "service.test"
        assert pool.assert_hostname == "service.test"

    def test_a_scheme_other_than_http_is_refused(self):
        adapter = guarded_http.GuardedAdapter(LOOPBACK_ONLY)
        request = requests.Request("GET", "ftp://service.test/x").prepare()
        with pytest.raises(guarded_http.RefusedDestination, match="scheme"):
            adapter.send(request)


class TestRedirects:
    def test_every_hop_is_checked(self, server):
        with pytest.raises(
            guarded_http.RefusedDestination, match=re.escape("10.0.0.1")
        ):
            session_for().get(f"http://service.test:{server.server_port}/to-private")
        assert [path for path, _host in server.seen] == ["/to-private"]

    def test_a_redirect_chain_is_bounded(self, server):
        with pytest.raises(requests.TooManyRedirects):
            session_for(max_redirects=3).get(
                f"http://service.test:{server.server_port}/loop"
            )
        assert len(server.seen) == 4


class TestCaps:
    def test_an_announced_body_over_the_cap_is_refused_before_reading(self, server):
        with pytest.raises(guarded_http.ResponseTooLarge):
            session_for(max_bytes=1024).get(
                f"http://service.test:{server.server_port}/large"
            )

    def test_an_unannounced_body_is_cut_at_the_cap(self, server):
        with pytest.raises(guarded_http.ResponseTooLarge):
            session_for(max_bytes=1024).get(
                f"http://service.test:{server.server_port}/large-unannounced"
            )

    def test_a_streamed_body_is_cut_at_the_cap(self, server):
        response = session_for(max_bytes=1024).get(
            f"http://service.test:{server.server_port}/large-unannounced",
            stream=True,
        )
        with pytest.raises(guarded_http.ResponseTooLarge):
            b"".join(response.iter_content(512))

    def test_the_cap_counts_decoded_bytes(self, server):
        with pytest.raises(guarded_http.ResponseTooLarge):
            session_for(max_bytes=64 * 1024).get(
                f"http://service.test:{server.server_port}/bomb"
            )

    def test_a_body_under_the_cap_is_returned_whole(self, server):
        response = session_for(max_bytes=64 * 1024).get(
            f"http://service.test:{server.server_port}/large"
        )
        assert len(response.content) == 64 * 1024

    def test_a_head_request_is_not_judged_by_its_announced_length(self, server):
        response = session_for(max_bytes=1024).head(
            f"http://service.test:{server.server_port}/large"
        )
        assert response.status_code == 200

    def test_a_body_that_trickles_past_the_deadline_is_abandoned(self, server):
        started = time.monotonic()
        with pytest.raises(guarded_http.ResponseTooSlow):
            session_for(max_seconds=0.5).get(
                f"http://service.test:{server.server_port}/dribble"
            )
        assert time.monotonic() - started < 1.5
