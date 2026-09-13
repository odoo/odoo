import contextlib
import errno
import json
import logging
import os
import socket
import threading
import time
from contextlib import contextmanager
from unittest.mock import patch

import pytest

from odoo.service import httpd
from odoo.service import settings as server_settings


def _app(environ, start_response):
    path = environ["PATH_INFO"]
    if path == "/stream":
        start_response("200 OK", [("Content-Type", "text/plain")])
        return iter([b"a" * 10, b"", b"b" * 5])
    if path == "/boom":
        raise RuntimeError("boom")
    if path == "/reject":
        start_response("413 Content Too Large", [("Content-Length", "0")])
        return [b""]
    if path == "/upgrade":
        sock = environ["socket"]

        class Upgraded(list):
            def close(self):
                name = threading.current_thread().name.encode()
                sock.sendall(b"UPGRADED:" + name)

        start_response(
            "101 Switching Protocols", [("Upgrade", "x"), ("Connection", "Upgrade")]
        )
        return Upgraded()
    if path == "/rpc":
        threading.current_thread().rpc_model_method = "res.users.read"
    body = environ["wsgi.input"].read()
    out = json.dumps(
        {
            "path": path,
            "query": environ["QUERY_STRING"],
            "len": len(body),
            "host": environ.get("HTTP_HOST"),
            "content_length": environ.get("CONTENT_LENGTH"),
            "terminated": environ.get("wsgi.input_terminated"),
            "dup": environ.get("HTTP_X_DUP"),
            "underscore": "HTTP_X_UNDER" in environ,
            "socket": "socket" in environ,
            "thread": threading.current_thread().name,
        }
    ).encode()
    start_response(
        "200 OK",
        [("Content-Type", "application/json"), ("Content-Length", str(len(out)))],
    )
    return [out]


@contextmanager
def _server(**env):
    with (
        patch.dict(os.environ, {"ODOO_MAX_HTTP_THREADS": "4", **env}),
        server_settings.override(
            db_maxconn=64, max_cron_threads=0, job_workers=0, test_enable=False
        ),
    ):
        srv = httpd.ThreadedHTTPServer("127.0.0.1", 0, _app)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        yield srv
    finally:
        srv.shutdown()
        srv.server_close()
        thread.join(5)


@pytest.fixture(scope="module")
def server():
    with _server() as srv:
        yield srv


def _talk(port, payload, timeout=3.0):
    sock = socket.create_connection(("127.0.0.1", port))
    sock.settimeout(timeout)
    sock.sendall(payload)
    buf = b""
    try:
        while chunk := sock.recv(65536):
            buf += chunk
    except TimeoutError:
        buf += b"<still open>"
    sock.close()
    return buf


def _json_body(response):
    return json.loads(response.partition(b"\r\n\r\n")[2])


def test_a_request_reaches_the_application_with_a_wsgi_environ(server):
    raw = _talk(
        server.server_port,
        b"GET /a?x=1 HTTP/1.1\r\nHost: h\r\nX-Dup: 1\r\nX-Dup: 2\r\n"
        b"X_Under: spoof\r\nConnection: close\r\n\r\n",
    )
    assert raw.startswith(b"HTTP/1.1 200 OK")
    body = _json_body(raw)
    assert body["query"] == "x=1"
    assert body["dup"] == "1,2"
    assert body["underscore"] is False
    assert body["socket"] is True
    assert body["thread"].startswith(httpd.REQUEST_THREAD_PREFIX)
    assert b"Connection: close" in raw
    assert b"\r\nServer:" not in raw
    assert b"\r\nDate:" in raw


def test_two_pipelined_requests_share_one_connection(server):
    raw = _talk(
        server.server_port,
        b"GET /a HTTP/1.1\r\nHost: h\r\n\r\n"
        b"GET /b HTTP/1.1\r\nHost: h\r\nConnection: close\r\n\r\n",
    )
    assert raw.count(b"HTTP/1.1 200 OK") == 2
    assert b'"/b"' in raw


def test_an_idle_keep_alive_connection_is_reused(server):
    sock = socket.create_connection(("127.0.0.1", server.server_port))
    sock.settimeout(3)
    sock.sendall(b"GET /one HTTP/1.1\r\nHost: h\r\n\r\n")
    first = sock.recv(65536)
    time.sleep(0.2)
    sock.sendall(b"GET /two HTTP/1.1\r\nHost: h\r\nConnection: close\r\n\r\n")
    second = b""
    while chunk := sock.recv(65536):
        second += chunk
    sock.close()
    assert b'"/one"' in first
    assert b"Connection: close" not in first
    assert b'"/two"' in second


def test_idle_connections_never_occupy_a_worker(server):
    idle = [
        socket.create_connection(("127.0.0.1", server.server_port)) for _ in range(40)
    ]
    try:
        time.sleep(0.2)
        raw = _talk(
            server.server_port,
            b"GET /x HTTP/1.1\r\nHost: h\r\nConnection: close\r\n\r\n",
        )
        assert b'"/x"' in raw
        deadline = time.monotonic() + 2
        while server.busy_workers and time.monotonic() < deadline:
            time.sleep(0.01)
        assert server.busy_workers == 0, (
            "a worker counts itself idle just after the response is sent; forty "
            "idle connections must not keep one busy"
        )
    finally:
        for sock in idle:
            sock.close()


def test_a_chunked_upload_is_decoded(server):
    raw = _talk(
        server.server_port,
        b"POST /c HTTP/1.1\r\nHost: h\r\nTransfer-Encoding: chunked\r\n"
        b"Connection: close\r\n\r\n5\r\nhello\r\n0\r\n\r\n",
    )
    body = _json_body(raw)
    assert (body["len"], body["terminated"], body["content_length"]) == (5, True, None)


def test_content_length_with_chunked_is_decoded_as_chunked_and_closed(server):
    raw = _talk(
        server.server_port,
        b"POST /c HTTP/1.1\r\nHost: h\r\nContent-Length: 4\r\n"
        b"Transfer-Encoding: chunked\r\n\r\n5\r\nhello\r\n0\r\n\r\n",
    )
    assert _json_body(raw)["len"] == 5
    assert b"Connection: close" in raw
    assert not raw.endswith(b"<still open>")


def test_100_continue_is_sent_only_when_the_application_reads_the_body(server):
    sock = socket.create_connection(("127.0.0.1", server.server_port))
    sock.settimeout(3)
    sock.sendall(
        b"PUT /c HTTP/1.1\r\nHost: h\r\nExpect: 100-continue\r\n"
        b"Content-Length: 3\r\nConnection: close\r\n\r\n"
    )
    assert sock.recv(1024).startswith(b"HTTP/1.1 100 Continue")
    sock.sendall(b"abc")
    rest = b""
    while chunk := sock.recv(65536):
        rest += chunk
    sock.close()
    assert b'"len": 3' in rest

    sock = socket.create_connection(("127.0.0.1", server.server_port))
    sock.settimeout(3)
    sock.sendall(
        b"PUT /reject HTTP/1.1\r\nHost: h\r\nExpect: 100-continue\r\n"
        b"Content-Length: 3000000\r\n\r\n"
    )
    assert sock.recv(1024).startswith(b"HTTP/1.1 413")
    sock.close()


def test_streamed_responses_are_chunked_for_http11_and_close_delimited_for_http10(
    server,
):
    raw = _talk(
        server.server_port,
        b"GET /stream HTTP/1.1\r\nHost: h\r\nConnection: close\r\n\r\n",
    )
    assert b"Transfer-Encoding: chunked" in raw
    assert raw.endswith(b"a\r\naaaaaaaaaa\r\n5\r\nbbbbb\r\n0\r\n\r\n")
    raw = _talk(server.server_port, b"GET /stream HTTP/1.0\r\n\r\n")
    assert b"Transfer-Encoding" not in raw
    assert raw.endswith(b"aaaaaaaaaabbbbb")


def test_head_sends_no_body(server):
    raw = _talk(
        server.server_port,
        b"HEAD /stream HTTP/1.1\r\nHost: h\r\nConnection: close\r\n\r\n",
    )
    assert raw.endswith(b"\r\n\r\n")


def test_an_application_exception_answers_500_and_closes(server):
    with patch.object(httpd._logger, "exception"):
        raw = _talk(server.server_port, b"GET /boom HTTP/1.1\r\nHost: h\r\n\r\n")
    assert raw.startswith(b"HTTP/1.1 500")
    assert not raw.endswith(b"<still open>")


@pytest.mark.parametrize(
    ("raw", "status"),
    [
        (
            b"POST / HTTP/1.1\r\nHost: h\r\nContent-Length: 5\r\nContent-Length: 3\r\n\r\nhello",
            b"400",
        ),
        (b"GET / HTTP/1.1\r\nHost: h\r\nX-Bad : 1\r\n\r\n", b"400"),
        (b"GET / HTTP/1.1\r\n\r\n", b"400"),
        (b"GET / HTTP/1.1\r\nHost: a\r\nHost: b\r\n\r\n", b"400"),
        (
            b"POST / HTTP/1.1\r\nHost: h\r\nTransfer-Encoding: gzip, chunked\r\n\r\n",
            b"501",
        ),
        (b"GET / HTTP/2.0\r\nHost: h\r\n\r\n", b"505"),
    ],
)
def test_malformed_framing_is_rejected_and_the_connection_closed(server, raw, status):
    response = _talk(server.server_port, raw)
    assert response.startswith(b"HTTP/1.1 " + status)
    assert b"Connection: close" in response
    assert not response.endswith(b"<still open>")


def test_an_upgrade_hands_the_socket_to_a_request_named_thread(server):
    raw = _talk(server.server_port, b"GET /upgrade HTTP/1.1\r\nHost: h\r\n\r\n")
    assert raw.startswith(b"HTTP/1.1 101")
    assert b"UPGRADED:" + httpd.REQUEST_THREAD_PREFIX.encode() in raw


def test_idle_pool_threads_are_not_named_as_requests(server):
    _talk(
        server.server_port, b"GET /x HTTP/1.1\r\nHost: h\r\nConnection: close\r\n\r\n"
    )
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline and any(
        t.name.startswith(httpd.REQUEST_THREAD_PREFIX) for t in threading.enumerate()
    ):
        time.sleep(0.01)
    assert not any(
        t.name.startswith(httpd.REQUEST_THREAD_PREFIX) for t in threading.enumerate()
    ), (
        "the test harness joins request-named threads; an idle worker must not look like one"
    )


def test_a_partial_head_times_out_with_408_without_a_worker():
    with _server(ODOO_HTTP_HEAD_TIMEOUT="0.3") as srv:
        sock = socket.create_connection(("127.0.0.1", srv.server_port))
        sock.settimeout(3)
        sock.sendall(b"GET / HTTP/1.1\r\nHo")
        started = time.monotonic()
        buf = b""
        while chunk := sock.recv(1024):
            buf += chunk
        sock.close()
        assert buf.startswith(b"HTTP/1.1 408")
        assert time.monotonic() - started < 2
        assert srv.busy_workers == 0


def test_a_stream_of_empty_lines_is_answered_400_and_closed(server):
    sock = socket.create_connection(("127.0.0.1", server.server_port))
    sock.settimeout(3)
    started = time.monotonic()
    response = b""
    try:
        for _ in range(256):
            sock.sendall(b"\r\n" * 32768)
    except OSError:
        pass
    with contextlib.suppress(OSError):
        while chunk := sock.recv(65536):
            response += chunk
    sock.close()
    assert response.startswith(b"HTTP/1.1 400")
    assert time.monotonic() - started < 3
    after = _talk(
        server.server_port,
        b"GET /after HTTP/1.1\r\nHost: h\r\nConnection: close\r\n\r\n",
    )
    assert _json_body(after)["path"] == "/after"


class _StarvedListener:
    def __init__(self, sock):
        self.sock = sock
        self.accepts = 0

    def accept(self):
        self.accepts += 1
        raise OSError(errno.EMFILE, "Too many open files")

    def __getattr__(self, name):
        return getattr(self.sock, name)


@contextmanager
def _starved_server():
    with (
        patch.dict(os.environ, {"ODOO_MAX_HTTP_THREADS": "4"}),
        server_settings.override(
            db_maxconn=64, max_cron_threads=0, job_workers=0, test_enable=False
        ),
    ):
        srv = httpd.ThreadedHTTPServer("127.0.0.1", 0, _app)
    real = srv.socket
    srv.socket = _StarvedListener(real)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    try:
        yield srv, thread
    finally:
        srv.shutdown()
        if thread.ident is not None:
            thread.join(5)
        srv.socket = real
        srv.server_close()


def _parked(srv, *, requests, head_started, name):
    left, right = socket.socketpair()
    conn = httpd.Connection(left, (name, 0))
    conn.requests = requests
    if head_started:
        conn.source.buffer += b"GET / HTTP/1.1\r\n"
    srv._park(conn, time.monotonic())
    return conn, right


def test_idle_eviction_takes_a_kept_alive_connection_before_older_silent_ones():
    with _starved_server() as (srv, _):
        pairs = [
            _parked(srv, requests=0, head_started=True, name="partial"),
            _parked(srv, requests=0, head_started=False, name="fresh"),
            _parked(srv, requests=3, head_started=False, name="kept-alive"),
        ]
        try:
            order = []
            while srv._evict_oldest_idle():
                closed = {c.addr[0] for c, _ in pairs if c.sock.fileno() == -1}
                order.extend(sorted(closed - set(order)))
            assert order == ["kept-alive", "partial", "fresh"]
        finally:
            for conn, peer in pairs:
                conn.sock.close()
                peer.close()


def test_running_out_of_descriptors_closes_an_idle_connection_to_make_room(caplog):
    with _starved_server() as (srv, thread):
        _conn, peer = _parked(srv, requests=1, head_started=False, name="kept-alive")
        client = socket.create_connection(srv.server_address)
        try:
            with caplog.at_level(logging.WARNING, logger="odoo.service.server"):
                thread.start()
                peer.settimeout(2)
                assert peer.recv(1) == b""
            assert "cannot accept HTTP connections" in caplog.text
        finally:
            client.close()
            peer.close()


def test_running_out_of_descriptors_with_nothing_to_close_does_not_spin():
    with _starved_server() as (srv, thread):
        client = socket.create_connection(srv.server_address)
        try:
            started = time.process_time()
            thread.start()
            time.sleep(0.5)
            cpu = time.process_time() - started
            accepts = srv.socket.accepts
        finally:
            client.close()
    assert 1 <= accepts <= 15
    assert cpu < 0.25


def test_the_access_log_line_keeps_its_shape(server, caplog):
    with caplog.at_level(logging.INFO, logger="odoo.service.http.access"):
        _talk(
            server.server_port,
            b"POST /rpc HTTP/1.1\r\nHost: h\r\nContent-Length: 0\r\nConnection: close\r\n\r\n",
        )
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline and not caplog.records:
            time.sleep(0.01)
    [record] = [r for r in caplog.records if r.name == "odoo.service.http.access"]
    message = record.getMessage()
    assert '"POST /rpc#res.users.read HTTP/1.1" 200' in message
    assert message.startswith("127.0.0.1 - - [")


def test_static_requests_are_logged_at_debug_outside_dev_mode(caplog):
    conn = httpd.Connection(socket.socket(), ("127.0.0.1", 1))
    try:
        with (
            server_settings.override(dev_mode=[]),
            caplog.at_level(logging.DEBUG, logger="odoo.service.http.access"),
        ):
            httpd.log_access(
                conn, "GET /web/static/x.js HTTP/1.1", "/web/static/x.js", 200, 1
            )
    finally:
        conn.sock.close()
    assert [r.levelno for r in caplog.records] == [logging.DEBUG]


def test_access_records_carry_the_request_line_first_for_filters(caplog):
    conn = httpd.Connection(socket.socket(), ("127.0.0.1", 1))
    try:
        with caplog.at_level(logging.INFO, logger="odoo.service.http.access"):
            httpd.log_access(conn, "GET /hw_proxy/hello HTTP/1.1", "/hw", 200, 7)
    finally:
        conn.sock.close()
    [record] = caplog.records
    assert record.args == ("GET /hw_proxy/hello HTTP/1.1", 200, 7)


def test_a_filter_on_the_access_logger_rewrites_the_line(caplog):
    class Mask(logging.Filter):
        def filter(self, record):
            record.args = tuple(
                a.replace("s3cr3t", "***") if isinstance(a, str) else a
                for a in record.args
            )
            return True

    logger = logging.getLogger("odoo.service.http.access")
    mask = Mask()
    logger.addFilter(mask)
    conn = httpd.Connection(socket.socket(), ("127.0.0.1", 1))
    try:
        with caplog.at_level(logging.INFO, logger="odoo.service.http.access"):
            httpd.log_access(conn, "POST /hook/s3cr3t HTTP/1.1", "/hook", 200, 0)
    finally:
        logger.removeFilter(mask)
        conn.sock.close()
    assert "s3cr3t" not in caplog.text
    assert '"POST /hook/*** HTTP/1.1" 200 0' in caplog.text


def test_a_percent_in_the_peer_address_is_not_a_format_directive(caplog):
    conn = httpd.Connection(socket.socket(), ("fe80::1%eth0", 1))
    try:
        with caplog.at_level(logging.INFO, logger="odoo.service.http.access"):
            httpd.log_access(conn, "GET / HTTP/1.1", "/", 200, 0)
    finally:
        conn.sock.close()
    assert caplog.records[0].getMessage().startswith("fe80::1%eth0 - - [")


def test_control_characters_are_escaped_in_the_access_log(caplog):
    conn = httpd.Connection(socket.socket(), ("127.0.0.1", 1))
    try:
        with (
            server_settings.override(dev_mode=[]),
            caplog.at_level(logging.INFO, logger="odoo.service.http.access"),
        ):
            httpd.log_access(conn, "GET /a\x1b[31m HTTP/1.1", "/a", 200, 1)
    finally:
        conn.sock.close()
    assert "\\x1b[31m" in caplog.records[0].getMessage()


def test_a_prefork_connection_answers_http11_closes_and_never_exposes_the_socket():
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]
    identity = httpd.ServerIdentity("127.0.0.1", port, False, True, False)
    with server_settings.override(test_enable=False):
        limits = httpd.TransportLimits.from_environment()

    def serve():
        client, addr = listener.accept()
        httpd.serve_prefork_connection(client, addr, _app, identity, limits)

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    started = time.monotonic()
    raw = _talk(port, b"GET /p HTTP/1.1\r\nHost: h\r\n\r\n")
    elapsed = time.monotonic() - started
    thread.join(5)
    listener.close()
    assert raw.startswith(b"HTTP/1.1 200")
    assert b"Connection: close" in raw
    assert _json_body(raw)["socket"] is False
    assert elapsed < 0.5, "a sized response must not wait on the client to close"


def test_shutdown_before_serve_forever_does_not_hang():
    with (
        patch.dict(os.environ, {"ODOO_MAX_HTTP_THREADS": "1"}),
        server_settings.override(db_maxconn=8, max_cron_threads=0, job_workers=0),
    ):
        srv = httpd.ThreadedHTTPServer("127.0.0.1", 0, _app)
    done = threading.Event()
    threading.Thread(target=lambda: (srv.shutdown(), done.set()), daemon=True).start()
    assert done.wait(5)
    srv.server_close()


def test_a_busy_port_exits_with_the_operator_message(capsys):
    taken = socket.socket()
    taken.bind(("127.0.0.1", 0))
    taken.listen(1)
    port = taken.getsockname()[1]
    try:
        with (
            server_settings.override(db_maxconn=8, max_cron_threads=0, job_workers=0),
            pytest.raises(SystemExit) as info,
        ):
            httpd.ThreadedHTTPServer("127.0.0.1", port, _app)
    finally:
        taken.close()
    assert info.value.code == 1
    assert f"Port {port} is in use" in capsys.readouterr().err


def test_socket_activation_adopts_only_a_handover_meant_for_this_process():
    with patch.dict(
        os.environ, {"LISTEN_FDS": "1", "LISTEN_PID": str(os.getpid() + 1)}
    ):
        sock, adopted = httpd.ThreadedHTTPServer._bind("127.0.0.1", 0)
    sock.close()
    assert adopted is False
    passed = socket.socket()
    passed.bind(("127.0.0.1", 0))
    passed.listen(1)
    with (
        patch.dict(os.environ, {"LISTEN_FDS": "1", "LISTEN_PID": str(os.getpid())}),
        patch.object(httpd.socket, "socket", return_value=passed) as make,
    ):
        sock, adopted = httpd.ThreadedHTTPServer._bind("127.0.0.1", 0)
    assert adopted is True
    make.assert_called_once_with(fileno=3)
    passed.close()


def test_a_refused_worker_thread_answers_503_instead_of_silence():
    with _server() as srv:
        with patch.object(srv._pool, "submit", return_value=False):
            raw = _talk(srv.server_port, b"GET / HTTP/1.1\r\nHost: h\r\n\r\n")
    assert raw.startswith(b"HTTP/1.1 503")


@pytest.mark.parametrize(
    ("raw", "expected"), [("0", 0.1), ("-3", 0.1), ("not-a-number", 2.0), ("30", 30.0)]
)
def test_the_socket_timeout_knob_is_clamped_and_degrades_safely(
    monkeypatch, raw, expected
):
    monkeypatch.setenv("ODOO_HTTP_SOCKET_TIMEOUT", raw)
    assert httpd.get_http_socket_timeout() == expected


@pytest.mark.parametrize("test_enable", [False, True])
def test_test_mode_keeps_the_longer_socket_timeout(monkeypatch, test_enable):
    monkeypatch.setenv("ODOO_HTTP_SOCKET_TIMEOUT", "2.5")
    with server_settings.override(test_enable=test_enable):
        limits = httpd.TransportLimits.from_environment()
    assert limits.socket_timeout == (5.0 if test_enable else 2.5)


def test_the_thread_budget_is_derived_from_the_pool_size(monkeypatch):
    monkeypatch.delenv("ODOO_MAX_HTTP_THREADS", raising=False)
    with server_settings.override(db_maxconn=64, max_cron_threads=2, job_workers=1):
        limit, auto_limit = httpd.compute_http_thread_limit(server_settings.current())
    assert limit == auto_limit == 30


def test_a_connection_finishing_after_shutdown_is_closed_not_queued():
    with (
        patch.dict(os.environ, {"ODOO_MAX_HTTP_THREADS": "1"}),
        server_settings.override(db_maxconn=8, max_cron_threads=0, job_workers=0),
    ):
        srv = httpd.ThreadedHTTPServer("127.0.0.1", 0, _app)
    left, right = socket.socketpair()
    conn = httpd.Connection(left, ("127.0.0.1", 1))
    try:
        assert srv._stopped.is_set(), "a server that is not serving counts as stopped"
        with patch.object(httpd, "serve_one", return_value=httpd.Outcome.PERSIST):
            srv._serve_connection(conn)
        assert not srv._returned, "nobody would ever park or close it"
        assert left.fileno() == -1
    finally:
        right.close()
        srv.server_close()


def test_a_saturated_pool_wakes_the_selector_when_it_drains():
    release = threading.Event()
    started = threading.Event()
    woken = threading.Event()

    def target(conn):
        started.set()
        release.wait(5)

    pool = httpd.WorkerPool(1, target, woken.set)
    try:
        assert pool.submit(object())
        assert started.wait(5)
        woken.clear()
        assert pool.submit(object())
        assert pool.saturated
        assert not woken.is_set()
        release.set()
        assert woken.wait(5), (
            "the selector stops listening while the pool is saturated; without a "
            "wake-up it resumes only at its select timeout, stalling every "
            "connection-per-request client by up to half a second"
        )
    finally:
        release.set()
        pool.close()


def test_connection_per_request_clients_are_not_stalled_by_saturation():
    def slow(environ, start_response):
        time.sleep(0.02)
        start_response("200 OK", [("Content-Length", "2")])
        return [b"ok"]

    with (
        patch.dict(os.environ, {"ODOO_MAX_HTTP_THREADS": "1"}),
        server_settings.override(db_maxconn=8, max_cron_threads=0, job_workers=0),
    ):
        srv = httpd.ThreadedHTTPServer("127.0.0.1", 0, slow)
    loop = threading.Thread(target=srv.serve_forever, daemon=True)
    loop.start()
    try:
        latencies = []
        lock = threading.Lock()

        def client():
            for _ in range(4):
                started = time.monotonic()
                _talk(
                    srv.server_port,
                    b"GET / HTTP/1.1\r\nHost: h\r\nConnection: close\r\n\r\n",
                )
                with lock:
                    latencies.append(time.monotonic() - started)

        clients = [threading.Thread(target=client) for _ in range(6)]
        started = time.monotonic()
        for thread in clients:
            thread.start()
        for thread in clients:
            thread.join(30)
        elapsed = time.monotonic() - started
        assert len(latencies) == 24
        assert elapsed < 3.0, (
            f"24 requests of 20 ms through one worker took {elapsed:.1f}s; a "
            f"selector that waits out its timeout after each saturation takes ~7s"
        )
    finally:
        srv.shutdown()
        srv.server_close()
        loop.join(5)


def test_serving_a_request_leaves_no_cyclic_garbage(server):
    import gc

    request = b"POST /c HTTP/1.1\r\nHost: h\r\nContent-Length: 5\r\nConnection: close\r\n\r\nhello"
    for _ in range(20):
        _talk(server.server_port, request)
    time.sleep(0.2)
    gc.collect()
    gc.disable()
    try:
        for _ in range(200):
            _talk(server.server_port, request)
        deadline = time.monotonic() + 2
        while server.busy_workers and time.monotonic() < deadline:
            time.sleep(0.01)
        time.sleep(0.1)
        found = gc.collect()
    finally:
        gc.enable()
    assert found < 50, (
        f"{found} cyclic objects over 200 requests; every one waits for a gen-1 "
        f"collection, and those already pause the whole server for ~250 ms"
    )


def _pipeline(port, n, timeout=3.0):
    payload = b"".join(
        f"GET /r{i} HTTP/1.1\r\nHost: h\r\n\r\n".encode() for i in range(n)
    )
    sock = socket.create_connection(("127.0.0.1", port))
    sock.settimeout(timeout)
    sock.sendall(payload)
    buf = b""
    try:
        while buf.count(b"HTTP/1.1 200 OK") < n:
            chunk = sock.recv(65536)
            if not chunk:
                break
            buf += chunk
    except TimeoutError:
        pass
    sock.close()
    return buf


def test_a_pipeline_longer_than_the_inline_cap_is_answered_in_full():
    """Request _MAX_PIPELINED + 1 sits fully buffered when the worker hands the
    connection back; nothing else will ever arrive to wake the selector for
    it, so it must be resubmitted, not parked until the head timeout."""
    n = httpd._MAX_PIPELINED + 1
    with _server(ODOO_HTTP_HEAD_TIMEOUT="0.5") as srv:
        raw = _pipeline(srv.server_port, n)
    assert raw.count(b"HTTP/1.1 200 OK") == n
    assert b"408" not in raw
    assert f'"/r{n - 1}"'.encode() in raw


def test_junk_after_a_served_request_is_a_400_not_a_worker_crash(caplog):
    payload = b"GET /ok HTTP/1.1\r\nHost: h\r\n\r\n" + b"\r\n" * 100
    with _server() as srv, caplog.at_level(logging.ERROR, "odoo.service.server"):
        raw = _talk(srv.server_port, payload)
    assert raw.count(b"HTTP/1.1 200 OK") == 1
    assert b"HTTP/1.1 400 Bad Request" in raw
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]


class TestAccessLogStyling:
    @pytest.fixture
    def styled(self, monkeypatch):
        def run(*, colors: bool, tty: bool) -> str:
            monkeypatch.setattr(httpd, "root_handler_uses_colors", lambda: colors)
            monkeypatch.setattr(httpd.sys.stderr, "isatty", lambda: tty, raising=False)
            return httpd._style("GET / HTTP/1.1", "bold", "red")

        return run

    def test_follows_the_root_handler_not_stderr(self, styled):
        assert styled(colors=False, tty=True) == "GET / HTTP/1.1"
        assert styled(colors=True, tty=False) == "\x1b[1;31mGET / HTTP/1.1\x1b[0m"


def test_close_is_idempotent_and_logged_once():
    a, b = socket.socketpair()
    try:
        conn = httpd.Connection(a, ("127.0.0.1", 1))
        conn.close()
        assert conn.closed
        conn.close()
        assert a.fileno() == -1
    finally:
        b.close()


def test_a_malformed_head_request_gets_a_bodiless_error(server):
    raw = _talk(
        server.server_port, b"HEAD /x HTTP/1.1\r\nHost: h\r\nBad Header: x\r\n\r\n"
    )
    head, _, body = raw.partition(b"\r\n\r\n")
    assert head.startswith(b"HTTP/1.1 400 Bad Request")
    assert b"Content-Length: 45" in head
    assert body == b""


def test_the_application_failing_on_a_head_request_gets_a_bodiless_500(server):
    raw = _talk(server.server_port, b"HEAD /boom HTTP/1.1\r\nHost: h\r\n\r\n")
    head, _, body = raw.partition(b"\r\n\r\n")
    assert head.startswith(b"HTTP/1.1 500 Internal Server Error")
    assert body == b""
