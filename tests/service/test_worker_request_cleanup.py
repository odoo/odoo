import contextlib
import socket
from unittest.mock import MagicMock, patch

import pytest

from odoo.service import _worker
from odoo.service._worker import WorkerHTTP

from .conftest import build_worker


@pytest.fixture
def worker(worker_multi):
    return build_worker(WorkerHTTP, worker_multi, sock_timeout=5, limits=MagicMock())


def _socketpair():
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        client = socket.create_connection(listener.getsockname())
        accepted, _ = listener.accept()
    finally:
        listener.close()
    return accepted, client


def _serving(failure=None):
    return patch.object(_worker, "serve_prefork_connection", side_effect=failure)


@pytest.mark.parametrize(
    "failure",
    [None, BrokenPipeError("client hung up"), ValueError("handler blew up")],
    ids=["clean", "broken-pipe", "unexpected-error"],
)
def test_accepted_socket_is_always_closed(worker, failure):
    client, peer = _socketpair()
    try:
        with _serving(failure), contextlib.suppress(ValueError):
            worker.process_request(client, ("127.0.0.1", 1234))
        assert client.fileno() == -1, "socket left open -- this is the fd leak"
    finally:
        peer.close()
        if client.fileno() != -1:
            client.close()


def test_broken_pipe_is_still_swallowed(worker):
    client, peer = _socketpair()
    try:
        with _serving(BrokenPipeError()):
            worker.process_request(client, ("127.0.0.1", 1234))
        assert worker.request_count == 1
    finally:
        peer.close()


def test_unexpected_errors_still_propagate(worker):
    client, peer = _socketpair()
    try:
        with _serving(ValueError("boom")), pytest.raises(ValueError, match="boom"):
            worker.process_request(client, ("127.0.0.1", 1234))
        assert worker.request_count == 0
    finally:
        peer.close()


def test_request_count_advances_only_on_a_completed_request(worker):
    client, peer = _socketpair()
    try:
        with _serving():
            worker.process_request(client, ("127.0.0.1", 1234))
        assert worker.request_count == 1
    finally:
        peer.close()


def test_socket_options_are_applied_before_handling(worker):
    client, peer = _socketpair()
    try:
        client_spy = MagicMock(wraps=client)
        client_spy.fileno.return_value = client.fileno()
        client_spy.getsockname.return_value = client.getsockname()
        seen = {}

        def serve(sock, *args):
            seen["timeout"] = sock.settimeout.call_args
            seen["nodelay"] = sock.setsockopt.call_args

        with _serving(serve):
            worker.process_request(client_spy, ("127.0.0.1", 1234))
        assert seen["timeout"].args == (worker.sock_timeout,)
        assert seen["nodelay"].args == (socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    finally:
        peer.close()
        client.close()


def test_a_prefork_worker_never_exposes_the_socket_for_hijacking(worker):
    client, peer = _socketpair()
    try:
        with _serving() as serve:
            worker.process_request(client, ("127.0.0.1", 1234))
        identity = serve.call_args.args[3]
        assert identity.exposes_socket is False
        assert identity.multiprocess is True
    finally:
        peer.close()


def test_an_upgraded_connection_keeps_its_socket(worker):
    """The upgrade thread owns the socket from the 101 on; closing it here
    would cut the websocket under it."""
    client, peer = _socketpair()
    try:
        with patch.object(
            _worker, "serve_prefork_connection", return_value=_worker.Outcome.UPGRADED
        ):
            worker.process_request(client, ("127.0.0.1", 1234))
        assert client.fileno() != -1
        assert worker.request_count == 1
    finally:
        peer.close()
        client.close()
