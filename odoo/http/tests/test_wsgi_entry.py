import io
import typing
from collections.abc import Callable
from typing import Any
from unittest import mock

import pytest

from odoo.http import application
from odoo.http.core import _request_stack
from odoo.http.exceptions import RegistryError


def _environ(path="/x", method="GET"):
    return {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": "",
        "SERVER_NAME": "localhost",
        "SERVER_PORT": "8069",
        "SERVER_PROTOCOL": "HTTP/1.1",
        "HTTP_HOST": "localhost:8069",
        "wsgi.url_scheme": "http",
        "wsgi.input": io.BytesIO(b""),
        "wsgi.errors": io.BytesIO(),
        "wsgi.multithread": True,
        "wsgi.multiprocess": False,
        "wsgi.run_once": False,
        "wsgi.version": (1, 0),
    }


class _FakeRequest:
    def __init__(self, httprequest, app, db=None, serve=None):
        self.httprequest = httprequest
        self.app = app
        self.db = db
        self.id = "fake-request-id"
        self.dispatcher = mock.Mock()
        self.dispatcher.serializes_errors_in_dev_mode = False
        self.dispatcher.prepare_error_response.side_effect = lambda exc: exc
        self._post_init_done = False
        self.session = mock.Mock()
        self.calls: list[str] = []
        self._serve = serve or (lambda name: f"served:{name}")
        self._serve_db: Callable[[], Any] = self._default_serve_db
        self._serve_nodb: Callable[[], Any] = self._default_serve_nodb

    def _post_init(self):
        self._post_init_done = True

    def _profile_request(self):
        import contextlib

        return contextlib.nullcontext()

    def _default_serve_db(self):
        self.calls.append("db")
        return self._serve("db")

    def _default_serve_nodb(self):
        self.calls.append("nodb")
        return self._serve("nodb")

    def _serve_static(self, filepath):
        self.calls.append("static")
        return self._serve("static")


def _run(app, environ, request):
    captured = {}

    def start_response(status, headers, exc_info=None):
        captured["status"] = status
        captured["headers"] = dict(headers)

    def _response(env, sr):
        sr("200 OK", [])
        return [b"body"]

    request._serve = lambda name: (captured.setdefault("served", name), _response)[1]

    def _adopt(httprequest, app):
        request.httprequest = httprequest
        return request

    with mock.patch.object(application, "Request", _adopt):
        body = app(environ, start_response)
    captured["body"] = b"".join(body)
    return captured


@pytest.fixture(autouse=True)
def _stack_is_left_empty():
    yield
    assert _request_stack.top is None, "__call__ leaked a request on the stack"


def test_a_request_with_a_database_is_served_by_serve_db():
    app = application.Application()
    hr = None
    req = _FakeRequest(hr, app, db="db")
    with mock.patch.object(app, "get_static_file_path", return_value=None):
        out = _run(app, _environ(), req)
    assert req.calls == ["db"] and out["served"] == "db"


def test_a_request_without_a_database_is_served_by_serve_nodb():
    app = application.Application()
    req = _FakeRequest(None, app, db=None)
    with mock.patch.object(app, "get_static_file_path", return_value=None):
        _run(app, _environ(), req)
    assert req.calls == ["nodb"]


def test_a_static_path_never_reaches_the_router():
    app = application.Application()
    req = _FakeRequest(None, app, db="db")
    with (
        mock.patch.object(app, "get_static_file_path", return_value="/tmp/asset.js"),
        mock.patch.object(app, "_serve_static_file") as served,
    ):
        served.return_value = lambda env, sr: (sr("200 OK", []), [b""])[1]
        _run(app, _environ("/web/static/asset.js"), req)
    assert req.calls == [], "the database was consulted for a static file"
    served.assert_called_once()


def test_trace_is_refused_before_anything_else_runs():
    app = application.Application()
    req = _FakeRequest(None, app, db="db")
    with mock.patch.object(app, "get_static_file_path") as static:
        out = _run(app, _environ(method="TRACE"), req)
    assert out["status"].startswith("405")
    assert req.calls == []
    static.assert_not_called()
    assert not req._post_init_done, "a refused method loads no session"
    assert out["headers"]["X-Content-Type-Options"] == "nosniff", (
        "a refusal that skips post_dispatch still carries the security headers"
    )


def test_a_nul_in_the_path_is_a_404_and_never_reaches_the_resolver():
    app = application.Application()
    req = _FakeRequest(None, app, db="db")
    with mock.patch.object(app, "get_static_file_path") as static:
        out = _run(app, _environ("/web/static/\x00.js"), req)
    assert out["status"].startswith("404")
    static.assert_not_called(), "get_static_file_path must not be handed a NUL path"
    assert not req._post_init_done, "a refused path loads no session"
    assert out["headers"]["X-Content-Type-Options"] == "nosniff"


def test_a_registry_error_falls_back_to_serving_without_a_database():
    app = application.Application()
    req: Any = _FakeRequest(None, app, db="db")

    def boom():
        req.calls.append("db")
        raise RegistryError("registry is unusable")

    req._serve_db = boom
    with (
        mock.patch.object(app, "get_static_file_path", return_value=None),
        mock.patch.object(app, "_recover_from_registry_error") as recover,
    ):
        recover.return_value = lambda env, sr: (sr("200 OK", []), [b""])[1]
        _run(app, _environ(), req)
    assert req.calls == ["db"]
    recover.assert_called_once()


def test_a_failure_still_answers_and_empties_the_stack():
    app = application.Application()
    req: Any = _FakeRequest(None, app, db="db")
    req._serve_db = mock.Mock(side_effect=ValueError("boom"))
    req.dispatcher.prepare_error_response.side_effect = RuntimeError(
        "and the handler too"
    )
    req.dispatcher.post_dispatch.side_effect = None

    with mock.patch.object(app, "get_static_file_path", return_value=None):
        out = _run(app, _environ(), req)
    assert out["status"].startswith("500")


def test_a_rerouted_request_has_its_second_httprequest_closed():
    app = application.Application()
    req: Any = _FakeRequest(None, app, db=None)
    rerouted = mock.Mock()

    def serve_nodb():
        req.httprequest = rerouted
        return lambda env, sr: (sr("200 OK", []), [b""])[1]

    req._serve_nodb = serve_nodb
    with mock.patch.object(app, "get_static_file_path", return_value=None):
        _run(app, _environ(), req)
    rerouted.close.assert_called_once()


def test_a_memoised_singleton_shadows_a_class_level_replacement():
    from odoo.libs.func import reset_cached_properties

    app = application.Application()
    app.__dict__["session_store"] = "memoised"

    with mock.patch.object(application.Application, "session_store", "patched"):
        assert app.session_store == "memoised"
        reset_cached_properties(app)
        assert app.session_store == "memoised", (
            "reset after the patch clears nothing: the name no longer resolves "
            "to a cached_property, so reset_cached_properties skips it"
        )

    reset_cached_properties(app)
    assert "session_store" not in app.__dict__, "reset first, patch second"


def test_the_request_stays_open_until_the_response_iterable_is_consumed():
    closed = []

    class _TrackingHTTPRequest(application.HTTPRequest):
        def close(self):
            closed.append(True)
            super().close()

    app = application.Application()
    req = _FakeRequest(None, app, db=None)

    def _response(env, sr):
        sr("200 OK", [])
        return [b"body"]

    req._serve = lambda name: _response

    def _adopt(httprequest, app):
        req.httprequest = httprequest
        return req

    with (
        mock.patch.object(application, "HTTPRequest", _TrackingHTTPRequest),
        mock.patch.object(application, "Request", _adopt),
        mock.patch.object(app, "get_static_file_path", return_value=None),
    ):
        iterable = app(_environ(), lambda *a, **kw: None)
    assert not closed, "the request must stay open while the body streams"
    assert b"".join(iterable) == b"body"
    typing.cast("typing.Any", iterable).close()
    assert closed, "closing the iterable closes the request"
