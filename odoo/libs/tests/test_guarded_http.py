import contextlib
import gzip
import http.server
import re
import socket
import socketserver
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

    def do_POST(self):
        self.server.seen.append((self.path, self.headers.get("Host")))
        length = int(self.headers.get("Content-Length") or 0)
        self.body = self.rfile.read(length)
        self.routes[self.path](self)

    def log_message(self, *args):
        pass


def _ok(handler):
    body = b"hello"
    handler.send_response(200)
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _xmlrpc_echo(handler):
    import xmlrpc.client

    params, method = xmlrpc.client.loads(handler.body)
    body = xmlrpc.client.dumps(({"method": method, "params": list(params)},))
    handler.send_response(200)
    handler.send_header("Content-Type", "text/xml")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body.encode())


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


class TestXmlRpcProxy:
    def test_the_proxy_posts_through_the_guarded_session(self, server):
        _Handler.routes["/xmlrpc/2/common"] = _xmlrpc_echo
        session = session_for()
        proxy = guarded_http.xmlrpc_proxy(
            session, f"http://127.0.0.1:{server.server_port}/xmlrpc/2/common"
        )

        result = proxy.version(1, "two")

        assert result == {"method": "version", "params": [1, "two"]}
        assert server.seen == [("/xmlrpc/2/common", f"127.0.0.1:{server.server_port}")]

    def test_url_credentials_are_sent_as_basic_auth(self, server):
        import base64

        seen = []

        def echo_auth(handler):
            seen.append(handler.headers.get("Authorization"))
            _xmlrpc_echo(handler)

        _Handler.routes["/xmlrpc/2/auth"] = echo_auth
        proxy = guarded_http.xmlrpc_proxy(
            session_for(),
            f"http://user:s%40cret@127.0.0.1:{server.server_port}/xmlrpc/2/auth",
        )
        proxy.version()
        assert seen == ["Basic " + base64.b64encode(b"user:s@cret").decode()]

    def test_an_http_error_is_an_xmlrpc_protocol_error(self, server):
        import xmlrpc.client

        def fail(handler):
            handler.send_response(503)
            handler.send_header("Content-Length", "0")
            handler.end_headers()

        _Handler.routes["/xmlrpc/2/fail"] = fail
        proxy = guarded_http.xmlrpc_proxy(
            session_for(), f"http://127.0.0.1:{server.server_port}/xmlrpc/2/fail"
        )
        with pytest.raises(xmlrpc.client.ProtocolError) as info:
            proxy.version()
        assert info.value.errcode == 503
        assert "user" not in info.value.url

    def test_a_refused_destination_never_reaches_the_server(self, server):
        session = session_for(resolver=resolver_for({"evil.test": ["10.0.0.9"]}))
        proxy = guarded_http.xmlrpc_proxy(session, "http://evil.test/xmlrpc/2/common")

        with pytest.raises(netguard.DestinationRefused):
            proxy.version()

        assert server.seen == []


class _ForwardProxy(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True
    request_lines: list[str]
    authorizations: list[str]

    @property
    def server_port(self) -> int:
        return self.server_address[1]


class _ForwardProxyHandler(socketserver.StreamRequestHandler):
    server: _ForwardProxy

    def handle(self):
        request_line = self.rfile.readline().decode("latin-1").strip()
        while (line := self.rfile.readline()) not in (b"\r\n", b"\n", b""):
            name, _, value = line.decode("latin-1").partition(":")
            if name.lower() == "proxy-authorization":
                self.server.authorizations.append(value.strip())
        self.server.request_lines.append(request_line)
        method, target, _version = request_line.split(" ", 2)
        if method != "CONNECT":
            body = b"via proxy"
            self.wfile.write(
                b"HTTP/1.1 200 OK\r\nContent-Length: %d\r\nConnection: close\r\n\r\n%s"
                % (len(body), body)
            )
            return
        host, _, port = target.rpartition(":")
        upstream = socket.create_connection((host.strip("[]"), int(port)), timeout=5)
        self.wfile.write(b"HTTP/1.1 200 Connection established\r\n\r\n")
        self.wfile.flush()

        def pump(source, sink):
            with contextlib.suppress(OSError):
                while chunk := source.recv(65536):
                    sink.sendall(chunk)
            with contextlib.suppress(OSError):
                sink.shutdown(socket.SHUT_WR)

        back = threading.Thread(target=pump, args=(upstream, self.connection))
        back.start()
        pump(self.connection, upstream)
        back.join(5)
        upstream.close()


@pytest.fixture
def forward_proxy():
    proxy = _ForwardProxy(("127.0.0.1", 0), _ForwardProxyHandler)
    proxy.request_lines = []
    proxy.authorizations = []
    thread = threading.Thread(target=proxy.serve_forever, args=(0.05,), daemon=True)
    thread.start()
    try:
        yield proxy
    finally:
        proxy.shutdown()
        proxy.server_close()


@pytest.fixture
def tls_server(tmp_path):
    import datetime
    import ssl

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "service.test")])
    now = datetime.datetime.now(datetime.UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName("service.test")]), critical=False
        )
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    cert_file = tmp_path / "cert.pem"
    key_file = tmp_path / "key.pem"
    cert_file.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    key_file.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_file, key_file)
    server_names = []
    context.sni_callback = lambda sock, server_name, ctx: server_names.append(
        server_name
    )
    httpd = _Server(("127.0.0.1", 0), _Handler)
    httpd.seen = []
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
    httpd.server_names = server_names
    httpd.ca_file = str(cert_file)
    thread = threading.Thread(target=httpd.serve_forever, args=(0.05,), daemon=True)
    thread.start()
    try:
        yield httpd
    finally:
        httpd.shutdown()
        httpd.server_close()


def rebinding_resolver(first, then):
    answers = [first]

    def resolve(host, port, *args, **kwargs):
        address = answers.pop() if answers else then
        return resolver_for({host: [address]})(host, port)

    return resolve


class TestEgressProxy:
    def test_https_through_the_proxy_tunnels_to_the_checked_address(
        self, forward_proxy, tls_server
    ):
        session = session_for(
            resolver=rebinding_resolver("127.0.0.1", then="10.0.0.9"),
            proxy=f"http://127.0.0.1:{forward_proxy.server_port}",
        )
        response = session.get(
            f"https://service.test:{tls_server.server_port}/ok",
            verify=tls_server.ca_file,
        )
        assert response.content == b"hello"
        assert forward_proxy.request_lines == [
            f"CONNECT 127.0.0.1:{tls_server.server_port} HTTP/1.1"
        ]
        assert tls_server.server_names == ["service.test"]
        assert tls_server.seen == [("/ok", f"service.test:{tls_server.server_port}")]

    def test_http_through_the_proxy_names_the_checked_address(self, forward_proxy):
        session = session_for(
            resolver=rebinding_resolver("127.0.0.1", then="10.0.0.9"),
            proxy=f"http://127.0.0.1:{forward_proxy.server_port}",
        )
        response = session.get("http://service.test:8080/x?q=1")
        assert response.content == b"via proxy"
        assert forward_proxy.request_lines == [
            "GET http://127.0.0.1:8080/x?q=1 HTTP/1.1"
        ]

    def test_a_refused_destination_never_reaches_the_proxy(self, forward_proxy):
        session = session_for(
            resolver=resolver_for({"service.test": ["10.0.0.9"]}),
            proxy=f"http://127.0.0.1:{forward_proxy.server_port}",
        )
        with pytest.raises(guarded_http.RefusedDestination):
            session.get("http://service.test/x")
        assert forward_proxy.request_lines == []

    def test_credentials_in_the_proxy_url_authenticate_both_schemes(
        self, forward_proxy, tls_server
    ):
        session = session_for(
            proxy=f"http://user:pw@127.0.0.1:{forward_proxy.server_port}"
        )
        session.get("http://service.test:8080/x")
        session.get(
            f"https://service.test:{tls_server.server_port}/ok",
            verify=tls_server.ca_file,
        )
        assert forward_proxy.authorizations == ["Basic dXNlcjpwdw=="] * 2

    @pytest.mark.parametrize("variable", ["HTTP_PROXY", "http_proxy", "ALL_PROXY"])
    def test_the_environment_proxy_is_not_used(self, server, monkeypatch, variable):
        monkeypatch.setenv(variable, "http://127.0.0.1:9")
        response = session_for().get(f"http://service.test:{server.server_port}/ok")
        assert response.content == b"hello"

    def test_a_plain_session_mounting_the_adapter_ignores_the_environment_proxy(
        self, server, monkeypatch
    ):
        monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9")
        session = requests.Session()
        session.mount(
            "http://",
            guarded_http.GuardedAdapter(
                LOOPBACK_ONLY, resolver=resolver_for({"service.test": ["127.0.0.1"]})
            ),
        )
        response = session.get(f"http://service.test:{server.server_port}/ok")
        assert response.content == b"hello"

    def test_the_process_proxy_is_the_default_route(self, forward_proxy, monkeypatch):
        monkeypatch.setattr(guarded_http, "_egress_proxy", None)
        guarded_http.configure_egress_proxy(
            f"http://127.0.0.1:{forward_proxy.server_port}"
        )
        session_for().get("http://service.test:8080/x")
        assert forward_proxy.request_lines == ["GET http://127.0.0.1:8080/x HTTP/1.1"]

    @pytest.mark.parametrize(
        "url", ["socks5://p:1080", "proxy.example:3128", "http://"]
    )
    def test_a_proxy_that_is_not_an_http_url_is_refused(self, url):
        with pytest.raises(ValueError, match="egress proxy"):
            guarded_http.configure_egress_proxy(url)
