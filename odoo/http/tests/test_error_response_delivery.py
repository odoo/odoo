import io
from typing import Any
from unittest import mock

import pytest
import werkzeug.exceptions
import werkzeug.wrappers

from odoo.http._session_store import FilesystemSessionStore
from odoo.http.application import Application
from odoo.http.constants import NOT_FOUND_NODB, NOT_FOUND_NODB_TEXT
from odoo.http.dispatcher import Json2Dispatcher
from odoo.http.routing import prepare_routing_map
from odoo.http.session import Session
from odoo.http.wrappers import Response


def _environ(path="/no-such-route", content_type=None, accept="*/*"):
    environ = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": path,
        "QUERY_STRING": "",
        "SERVER_NAME": "localhost",
        "SERVER_PORT": "8069",
        "SERVER_PROTOCOL": "HTTP/1.1",
        "HTTP_HOST": "localhost:8069",
        "HTTP_ACCEPT": accept,
        "wsgi.url_scheme": "http",
        "wsgi.input": io.BytesIO(b""),
        "wsgi.errors": io.BytesIO(),
        "wsgi.multithread": True,
        "wsgi.multiprocess": False,
        "wsgi.run_once": False,
        "wsgi.version": (1, 0),
    }
    if content_type:
        environ["CONTENT_TYPE"] = content_type
        environ["CONTENT_LENGTH"] = "0"
    return environ


@pytest.fixture
def nodb_app(tmp_path):
    app = Application()
    app.__dict__["nodb_routing_map"] = prepare_routing_map([])
    app.__dict__["session_store"] = FilesystemSessionStore(
        str(tmp_path), session_class=Session
    )
    return app


def _serve(app, environ):
    captured: dict[str, Any] = {}

    def start_response(status, headers, exc_info=None):
        captured["status"] = status
        captured["headers"] = {k.lower(): v for k, v in headers}

    with (
        mock.patch.object(app, "get_dbs_served", lambda host: []),
    ):
        body = b"".join(app(environ, start_response))
    return captured["status"], captured["headers"], body


def test_a_browser_gets_the_nodb_not_found_page(nodb_app):
    status, headers, body = _serve(nodb_app, _environ(accept="text/html"))

    assert status.startswith("404")
    assert headers["content-type"].startswith("text/html")
    assert NOT_FOUND_NODB.encode() in body


def test_a_json_client_gets_the_nodb_message_as_json(nodb_app):
    status, headers, body = _serve(nodb_app, _environ(content_type="application/json"))

    assert status.startswith("404")
    assert headers["content-type"].startswith("application/problem+json")
    assert NOT_FOUND_NODB_TEXT.encode() in body
    assert b"<!DOCTYPE html>" not in body


def test_json2_error_responses_are_the_package_response_type():
    exc = werkzeug.exceptions.NotFound()
    exc.response = werkzeug.wrappers.Response(b"raw", status=404)
    dispatcher: Any = Json2Dispatcher.__new__(Json2Dispatcher)
    dispatcher.request = None

    assert isinstance(dispatcher.prepare_error_response(exc), Response)


def test_the_negotiated_nodb_404_is_the_one_that_reaches_the_client(nodb_app):
    from odoo.http.dispatcher import JsonRPCDispatcher

    calls = []
    original = JsonRPCDispatcher.prepare_error_response

    def counted(self, exc):
        calls.append(exc)
        return original(self, exc)

    with mock.patch.object(JsonRPCDispatcher, "prepare_error_response", counted):
        status, headers, body = _serve(
            nodb_app, _environ(content_type="application/json-rpc")
        )

    assert len(calls) == 1
    assert headers["content-type"].startswith("application/json")
    assert NOT_FOUND_NODB_TEXT.encode() in body
    assert status.startswith("200"), "a JSON-RPC fault is a 200 with an error member"
